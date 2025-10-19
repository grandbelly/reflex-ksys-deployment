"""
Virtual Tag Service - Calculate derived metrics from sensor data based on formula definitions

This service:
1. Reads Virtual Tag definitions from virtual_tag_definitions table
2. Parses formulas (arithmetic, conditional, aggregation)
3. Fetches source sensor data from influx_agg_10m
4. Calculates Virtual Tag values
5. Stores results in virtual_tag_values table
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from reflex.utils import console


class FormulaParser:
    """Parse and evaluate Virtual Tag formulas"""

    def __init__(self, sensor_data: Dict[str, float]):
        """
        Initialize parser with current sensor values

        Args:
            sensor_data: Dict mapping tag_name → value
        """
        self.sensor_data = sensor_data

    def parse_arithmetic(self, formula: str) -> Optional[float]:
        """
        Parse and evaluate arithmetic formula

        Examples:
            "INLET_PRESSURE - OUTLET_PRESSURE" → 3500.0
            "ABS(PRODUCT_COND - FEED_COND)" → 5.2
            "(PRODUCT_FLOW / FEED_FLOW) * 100" → 85.5

        Args:
            formula: Arithmetic expression with sensor tag names

        Returns:
            Calculated value or None if error
        """
        try:
            # Replace sensor tag names with values
            expression = formula
            for tag_name, value in self.sensor_data.items():
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(tag_name) + r'\b'
                expression = re.sub(pattern, str(value), expression)

            # Evaluate the expression (supports ABS, +, -, *, /, **, ())
            # Security: Only allow safe math operations
            allowed_names = {"__builtins__": None, "abs": abs, "ABS": abs}
            result = eval(expression, allowed_names, {})

            return float(result)
        except ZeroDivisionError:
            # Handle division by zero gracefully
            console.warn(f"Division by zero in formula: {formula}")
            return 0.0
        except Exception as e:
            console.error(f"Arithmetic formula error: {formula} → {e}")
            return None

    def parse_conditional(self, condition: str, true_value: str,
                         false_value: str, time_delta: float = 1.0) -> Optional[float]:
        """
        Parse and evaluate conditional formula (IF-THEN logic)

        Examples:
            condition="FEED_FLOW > 1.0", true_value="1", false_value="0"
            condition="INLET_PRESSURE > 4500 OR OUTLET_PRESSURE < 500", true_value="1", false_value="0"

        Args:
            condition: Boolean expression
            true_value: Value if condition is true (can be "time_delta")
            false_value: Value if condition is false
            time_delta: Time interval in minutes (for OPERATING_TIME calculations)

        Returns:
            Evaluated value or None if error
        """
        try:
            # Replace sensor tag names with values in condition
            expression = condition
            for tag_name, value in self.sensor_data.items():
                pattern = r'\b' + re.escape(tag_name) + r'\b'
                expression = re.sub(pattern, str(value), expression)

            # Replace logical operators
            expression = expression.replace(" OR ", " or ")
            expression = expression.replace(" AND ", " and ")

            # Evaluate condition
            allowed_names = {"__builtins__": None}
            is_true = eval(expression, allowed_names, {})

            # Return appropriate value
            if is_true:
                if true_value == "time_delta":
                    return time_delta
                else:
                    return float(true_value)
            else:
                if false_value == "time_delta":
                    return time_delta
                else:
                    return float(false_value)
        except Exception as e:
            console.error(f"Conditional formula error: {condition} → {e}")
            return None


class VirtualTagService:
    """Service for calculating Virtual Tag values"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_virtual_tags(self) -> List[Dict[str, Any]]:
        """
        Get all active Virtual Tag definitions

        Returns:
            List of Virtual Tag definition dicts
        """
        query = text("""
            SELECT
                tag_name,
                formula_type,
                formula,
                source_tags,
                aggregation_function,
                aggregation_window,
                condition,
                true_value,
                false_value,
                unit,
                description
            FROM virtual_tag_definitions
            WHERE is_active = true
            ORDER BY formula_type, tag_name
        """)

        result = await self.session.execute(query)
        rows = result.mappings().all()

        return [dict(row) for row in rows]

    async def get_sensor_latest_values(self, tag_names: List[str]) -> Dict[str, float]:
        """
        Get latest values for specified sensor tags

        Args:
            tag_names: List of sensor tag names

        Returns:
            Dict mapping tag_name → value
        """
        if not tag_names:
            return {}

        # Convert list to PostgreSQL array format
        tags_param = tag_names

        query = text("""
            SELECT tag_name, value
            FROM influx_latest
            WHERE tag_name = ANY(:tag_names)
        """)

        result = await self.session.execute(query, {"tag_names": tags_param})
        rows = result.mappings().all()

        return {row["tag_name"]: float(row["value"]) for row in rows}

    async def get_sensor_aggregated_values(self, tag_name: str,
                                          agg_function: str,
                                          time_window: timedelta,
                                          end_time: Optional[datetime] = None,
                                          multiply_by_time_delta: bool = False) -> Optional[float]:
        """
        Get aggregated sensor value over time window

        Args:
            tag_name: Sensor tag name
            agg_function: Aggregation function (SUM, AVG, MAX, MIN, STDDEV, COUNT)
            time_window: Time window for aggregation
            end_time: End time (defaults to now)
            multiply_by_time_delta: If True, multiply value by time interval (for flow → volume)

        Returns:
            Aggregated value or None
        """
        if end_time is None:
            end_time = datetime.now()

        start_time = end_time - time_window

        if multiply_by_time_delta and agg_function.upper() == "SUM":
            # For flow-to-volume calculation: SUM(flow × time_interval)
            # Use LAG to calculate time difference between consecutive readings
            query = text("""
                WITH time_deltas AS (
                    SELECT
                        value,
                        EXTRACT(EPOCH FROM (ts - LAG(ts) OVER (ORDER BY ts))) / 60.0 AS delta_minutes
                    FROM influx_hist
                    WHERE tag_name = :tag_name
                      AND ts >= :start_time
                      AND ts <= :end_time
                    ORDER BY ts
                )
                SELECT SUM(value * COALESCE(delta_minutes, 10.0)) as agg_value
                FROM time_deltas
            """)
        else:
            # Standard aggregation
            agg_sql = {
                "SUM": "SUM(value)",
                "AVG": "AVG(value)",
                "MAX": "MAX(value)",
                "MIN": "MIN(value)",
                "STDDEV": "STDDEV(value)",
                "COUNT": "COUNT(*)"
            }.get(agg_function.upper(), "AVG(value)")

            query = text(f"""
                SELECT {agg_sql} as agg_value
                FROM influx_hist
                WHERE tag_name = :tag_name
                  AND ts >= :start_time
                  AND ts <= :end_time
            """)

        result = await self.session.execute(query, {
            "tag_name": tag_name,
            "start_time": start_time,
            "end_time": end_time
        })

        row = result.mappings().first()
        if row and row["agg_value"] is not None:
            return float(row["agg_value"])
        return None

    async def calculate_arithmetic_tag(self, tag_def: Dict[str, Any]) -> Optional[float]:
        """
        Calculate arithmetic Virtual Tag

        Args:
            tag_def: Virtual Tag definition dict

        Returns:
            Calculated value or None
        """
        source_tags = tag_def["source_tags"]
        formula = tag_def["formula"]

        # Get latest values for source tags
        sensor_data = await self.get_sensor_latest_values(source_tags)

        # Check if all source tags have values
        if len(sensor_data) < len(source_tags):
            console.warn(f"Missing sensor data for {tag_def['tag_name']}: {set(source_tags) - set(sensor_data.keys())}")
            return None

        # Parse and calculate
        parser = FormulaParser(sensor_data)
        return parser.parse_arithmetic(formula)

    async def calculate_conditional_tag(self, tag_def: Dict[str, Any],
                                       time_delta: float = 10.0) -> Optional[float]:
        """
        Calculate conditional Virtual Tag

        Args:
            tag_def: Virtual Tag definition dict
            time_delta: Time interval in minutes (for OPERATING_TIME calculations)

        Returns:
            Calculated value or None
        """
        source_tags = tag_def["source_tags"]
        condition = tag_def["condition"]
        true_value = tag_def["true_value"]
        false_value = tag_def["false_value"]

        # Get latest values for source tags
        sensor_data = await self.get_sensor_latest_values(source_tags)

        if len(sensor_data) < len(source_tags):
            console.warn(f"Missing sensor data for {tag_def['tag_name']}")
            return None

        # Parse and evaluate
        parser = FormulaParser(sensor_data)
        return parser.parse_conditional(condition, true_value, false_value, time_delta)

    async def calculate_aggregation_tag(self, tag_def: Dict[str, Any],
                                       end_time: Optional[datetime] = None) -> Optional[float]:
        """
        Calculate aggregation Virtual Tag

        Args:
            tag_def: Virtual Tag definition dict
            end_time: End time for aggregation window (defaults to now)

        Returns:
            Calculated value or None
        """
        source_tag = tag_def["source_tags"][0]  # Aggregations use single source
        agg_function = tag_def["aggregation_function"]
        agg_window = tag_def["aggregation_window"]
        formula = tag_def["formula"]

        # Check if formula involves time_delta multiplication (for flow → volume conversion)
        # e.g., "SUM(PRODUCT_FLOW * time_delta) OVER (1 hour)"
        multiply_by_time = "time_delta" in formula and agg_function.upper() == "SUM"

        # Get aggregated value
        value = await self.get_sensor_aggregated_values(
            source_tag, agg_function, agg_window, end_time,
            multiply_by_time_delta=multiply_by_time
        )

        return value

    async def calculate_all_virtual_tags(self, time_delta: float = 10.0) -> List[Dict[str, Any]]:
        """
        Calculate all active Virtual Tags

        Args:
            time_delta: Time interval in minutes (for conditional tags)

        Returns:
            List of dicts with tag_name, value, formula_type
        """
        virtual_tags = await self.get_active_virtual_tags()
        results = []

        for tag_def in virtual_tags:
            tag_name = tag_def["tag_name"]
            formula_type = tag_def["formula_type"]

            try:
                value = None

                if formula_type == "arithmetic":
                    value = await self.calculate_arithmetic_tag(tag_def)
                elif formula_type == "conditional":
                    value = await self.calculate_conditional_tag(tag_def, time_delta)
                elif formula_type == "aggregation":
                    value = await self.calculate_aggregation_tag(tag_def)

                if value is not None:
                    results.append({
                        "tag_name": tag_name,
                        "value": value,
                        "formula_type": formula_type,
                        "unit": tag_def["unit"],
                        "description": tag_def["description"]
                    })
                    console.log(f"✅ {tag_name} = {value:.2f} {tag_def['unit'] or ''}")
                else:
                    console.warn(f"⚠️  {tag_name}: calculation returned None")

            except Exception as e:
                console.error(f"❌ {tag_name}: {e}")

        return results

    async def store_virtual_tag_values(self, results: List[Dict[str, Any]],
                                      timestamp: Optional[datetime] = None):
        """
        Store calculated Virtual Tag values to influx_hist (same table as real sensors!)

        This allows Virtual Tags to be used by:
        - Node-RED (reads from influx_hist)
        - Dashboards (query influx_hist)
        - Feature Engineering (treats Virtual Tags like sensors)

        Args:
            results: List of dicts with tag_name, value
            timestamp: Timestamp for the values (defaults to now)
        """
        if not results:
            return

        if timestamp is None:
            timestamp = datetime.now()

        # Insert into influx_hist (same as real sensors)
        query = text("""
            INSERT INTO influx_hist (ts, tag_name, value, quality)
            VALUES (:ts, :tag_name, :value, :quality)
            ON CONFLICT (ts, tag_name) DO UPDATE
            SET value = EXCLUDED.value
        """)

        for r in results:
            await self.session.execute(query, {
                "ts": timestamp,
                "tag_name": r["tag_name"],
                "value": r["value"],
                "quality": 0  # 0 = GOOD quality
            })

        await self.session.commit()
        console.info(f"💾 Stored {len(results)} Virtual Tag values to influx_hist at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

    async def calculate_and_store(self, time_delta: float = 10.0):
        """
        Calculate all Virtual Tags and store results

        This is the main method called by the scheduler

        Args:
            time_delta: Time interval in minutes
        """
        console.info("🔄 Starting Virtual Tag calculation...")

        results = await self.calculate_all_virtual_tags(time_delta)

        if results:
            await self.store_virtual_tag_values(results)
            console.info(f"✅ Virtual Tag calculation complete: {len(results)} tags calculated")
        else:
            console.warn("⚠️  No Virtual Tags calculated")
