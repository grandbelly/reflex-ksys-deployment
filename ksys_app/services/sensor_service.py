"""
Sensor Service with Eager SQL (greenlet-safe)
- raw SQL + dict rows
- single roundtrip for charts (window function)
- SET LOCAL statement_timeout
"""
from typing import List, Dict
from datetime import datetime
import pytz
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from reflex.utils import console


class SensorService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_sensors_with_latest(self) -> List[Dict]:
        """Get all sensors with latest values - greenlet safe"""
        try:
            # 쿼리 타임아웃(예: 5초)
            await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

            q = text("""
                SELECT
                  l.tag_name,
                  l.value,
                  l.ts AS ts_utc,
                  COALESCE(l.quality, 0) AS quality,
                  q.min_val,
                  q.max_val,
                  q.warning_low,
                  q.warning_high,
                  q.critical_low,
                  q.critical_high,
                  COALESCE(t.description, t.meta->>'description', '') AS description,
                  COALESCE(t.unit, t.meta->>'unit', '') AS unit,
                  CASE
                    WHEN l.value IS NULL OR q.min_val IS NULL THEN 0
                    WHEN l.value < q.min_val OR l.value > q.max_val THEN 2
                    WHEN l.value < q.warning_low OR l.value > q.warning_high THEN 1
                    ELSE 0
                  END AS status
                FROM influx_latest l
                LEFT JOIN influx_qc_rule q ON l.tag_name = q.tag_name
                LEFT JOIN influx_tag t ON l.tag_name = t.tag_name
                ORDER BY l.tag_name
            """)

            rows = (await self.session.execute(q)).mappings().all()

            # UTC를 KST로 변환
            kst = pytz.timezone('Asia/Seoul')
            result = []

            for r in rows:
                # timestamp 변환
                timestamp_str = None
                if r["ts_utc"]:
                    # UTC datetime을 KST로 변환
                    if r["ts_utc"].tzinfo is None:
                        # naive datetime이면 UTC로 간주
                        ts_utc = pytz.UTC.localize(r["ts_utc"])
                    else:
                        ts_utc = r["ts_utc"]
                    ts_kst = ts_utc.astimezone(kst)
                    timestamp_str = ts_kst.strftime("%Y-%m-%d %H:%M:%S")

                result.append({
                    "tag_name": r["tag_name"],
                    "description": r.get("description") or r["tag_name"],
                    "unit": r.get("unit") or "",
                    "value": round(float(r["value"]), 2) if r["value"] is not None else 0.0,
                    "timestamp": timestamp_str,
                    "quality": int(r["quality"]),
                    "status": int(r["status"]),
                    "qc_rule": {
                        "min_val": round(float(r["min_val"]), 2) if r["min_val"] is not None else None,
                        "max_val": round(float(r["max_val"]), 2) if r["max_val"] is not None else None,
                        "warning_low": round(float(r["warning_low"]), 2) if r["warning_low"] is not None else None,
                        "warning_high": round(float(r["warning_high"]), 2) if r["warning_high"] is not None else None,
                        "critical_low": round(float(r["critical_low"]), 2) if r["critical_low"] is not None else None,
                        "critical_high": round(float(r["critical_high"]), 2) if r["critical_high"] is not None else None,
                    },
                })

            console.info(f"Loaded {len(result)} sensors with raw SQL")
            return result

        except Exception as e:
            console.error(f"Error fetching sensors: {e}")
            return []

    async def get_aggregated_chart_data(self, tag_names: List[str]) -> Dict[str, List[Dict]]:
        """Get chart data with single roundtrip - window function"""
        try:
            # 쿼리 타임아웃
            await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

            # 한 번의 라운드트립: 태그별 최근 20개 버킷만 남기고 오름차순으로 정렬
            # Use influx_agg_1m view - get LAST value instead of average
            q = text("""
                WITH ranked AS (
                  SELECT
                    tag_name,
                    bucket AS time,
                    last AS value,
                    row_number() OVER (PARTITION BY tag_name ORDER BY bucket DESC) AS rn
                  FROM influx_agg_1m
                  WHERE tag_name = ANY(:tags)
                )
                SELECT tag_name, time, value
                FROM ranked
                WHERE rn <= :limit
                ORDER BY tag_name, time ASC
            """)

            params = {"tags": tag_names, "limit": 20}
            rows = (await self.session.execute(q, params)).mappings().all()

            out: Dict[str, List[Dict]] = {}
            kst = pytz.timezone('Asia/Seoul')
            for r in rows:
                # Convert UTC to KST for display
                if r["time"]:
                    if r["time"].tzinfo is None:
                        time_utc = pytz.UTC.localize(r["time"])
                    else:
                        time_utc = r["time"]
                    time_kst = time_utc.astimezone(kst)
                    time_str = time_kst.strftime("%H:%M")
                else:
                    time_str = ""

                out.setdefault(r["tag_name"], []).append({
                    "time": time_str,
                    "timestamp": time_kst.strftime("%m-%d %H:%M") if r["time"] else "",  # Format: MM-DD HH:MM
                    "value": round(float(r["value"]), 2) if r["value"] is not None else 0.0,
                })

            return out

        except Exception as e:
            console.error(f"Error fetching chart data: {e}")
            return {}

    async def get_sensor_statistics(self) -> Dict[str, int]:
        """Get sensor statistics with optimized query"""
        try:
            await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

            q = text("""
                WITH status_calc AS (
                  SELECT
                    CASE
                      WHEN l.value IS NULL OR q.min_val IS NULL THEN 0
                      WHEN l.value < q.min_val OR l.value > q.max_val THEN 2
                      WHEN l.value < q.warning_low OR l.value > q.warning_high THEN 1
                      ELSE 0
                    END AS status
                  FROM influx_latest l
                  LEFT JOIN influx_qc_rule q ON l.tag_name = q.tag_name
                )
                SELECT
                  COUNT(*) FILTER (WHERE status = 0) AS normal,
                  COUNT(*) FILTER (WHERE status = 1) AS warning,
                  COUNT(*) FILTER (WHERE status = 2) AS critical
                FROM status_calc
            """)

            row = (await self.session.execute(q)).mappings().one()

            return {
                "normal": int(row["normal"] or 0),
                "warning": int(row["warning"] or 0),
                "critical": int(row["critical"] or 0),
            }

        except Exception as e:
            console.error(f"Error fetching statistics: {e}")
            return {"normal": 0, "warning": 0, "critical": 0}

    async def get_sensor_chart_data(
        self,
        tag_name: str,
        minutes: int = 5,
        limit: int = 10,
        hours: int = None
    ) -> List[Dict]:
        """
        Get recent historical data for chart using continuous aggregate

        Args:
            tag_name: Sensor tag name (e.g., "FEED_COND")
            minutes: Time window in minutes (default: 5, not used for limit-based query)
            limit: Maximum data points (default: 10, used when hours is None)
            hours: Time window in hours (optional, overrides limit-based query)

        Returns:
            List of dicts with timestamp and value
        """
        try:
            await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

            if hours:
                # Time-based query for full-screen dialog (last N hours)
                # Use f-string for INTERVAL since it can't be a bind parameter
                query = text(f"""
                    SELECT
                        TO_CHAR(bucket AT TIME ZONE 'Asia/Seoul', 'MM-DD HH24:MI') as timestamp,
                        avg as value
                    FROM influx_agg_1m
                    WHERE tag_name = :tag_name
                      AND bucket >= NOW() - INTERVAL '{hours} hours'
                    ORDER BY bucket ASC
                """)
                rows = (await self.session.execute(
                    query,
                    {"tag_name": tag_name}
                )).mappings().all()
            else:
                # Limit-based query for mini charts (latest N points)
                query = text("""
                    WITH ranked AS (
                        SELECT
                            TO_CHAR(bucket AT TIME ZONE 'Asia/Seoul', 'HH24:MI') as timestamp,
                            avg as value,
                            row_number() OVER (ORDER BY bucket DESC) as rn
                        FROM influx_agg_1m
                        WHERE tag_name = :tag_name
                    )
                    SELECT timestamp, value
                    FROM ranked
                    WHERE rn <= :limit
                    ORDER BY timestamp ASC
                """)
                rows = (await self.session.execute(
                    query,
                    {"tag_name": tag_name, "limit": limit}
                )).mappings().all()

            return [
                {
                    "timestamp": r["timestamp"],
                    "value": round(float(r["value"]), 2) if r["value"] else 0.0
                }
                for r in rows
            ]

        except Exception as e:
            console.error(f"Error fetching chart data for {tag_name}: {e}")
            return []

    def _get_chart_color(self, level: int) -> str:
        """Get chart color based on alarm level"""
        if level >= 4:
            return "#ef4444"  # Red (critical)
        elif level >= 2:
            return "#f59e0b"  # Orange (warning)
        else:
            return "#10b981"  # Green (normal)

    async def get_realtime_alarms_with_charts(self) -> List[Dict]:
        """
        Get real-time sensor data WITH mini chart data
        Enhanced version that includes chart_points for each sensor
        """
        try:
            # Get basic sensor data
            sensors = await self.get_all_sensors_with_latest()

            # Fetch chart data for each sensor
            for sensor in sensors:
                chart_data = await self.get_sensor_chart_data(sensor["tag_name"])
                sensor["chart_points"] = chart_data

                # Determine chart color based on status (0=normal, 1=warning, 2=critical)
                # Map to level (1=normal, 2-3=warning, 4-5=critical)
                status = sensor.get("status", 0)
                level = 1 if status == 0 else 2 if status == 1 else 4
                sensor["chart_color"] = self._get_chart_color(level)

            return sensors

        except Exception as e:
            console.error(f"Error fetching sensors with charts: {e}")
            return []

    async def get_dashboard_statistics(self) -> Dict:
        """
        Calculate dashboard summary statistics
        Returns KPI metrics for the statistics summary bar
        """
        try:
            await self.session.execute(text("SET LOCAL statement_timeout = '3s'"))

            query = text("""
                WITH sensor_stats AS (
                    SELECT
                        l.tag_name,
                        l.value,
                        q.min_val,
                        q.max_val,
                        CASE
                            WHEN l.value IS NULL OR q.min_val IS NULL THEN 0
                            WHEN l.value < q.min_val OR l.value > q.max_val THEN 2
                            WHEN l.value < q.warning_low OR l.value > q.warning_high THEN 1
                            ELSE 0
                        END as status,
                        CASE
                            WHEN l.value > q.max_val THEN
                                ROUND((((l.value - q.max_val) / NULLIF(q.max_val, 0)) * 100)::numeric, 0)
                            WHEN l.value < q.min_val THEN
                                ROUND((((q.min_val - l.value) / NULLIF(q.min_val, 0)) * 100)::numeric, 0)
                            ELSE 0
                        END as deviation_pct
                    FROM influx_latest l
                    LEFT JOIN influx_qc_rule q ON l.tag_name = q.tag_name
                    WHERE l.value IS NOT NULL
                )
                SELECT
                    COUNT(*) as total_devices,
                    COUNT(*) FILTER (WHERE status = 2) as critical_count,
                    COUNT(*) FILTER (WHERE status = 1) as warning_count,
                    COUNT(*) FILTER (WHERE status = 0) as normal_count,
                    ROUND(
                        (COUNT(*) FILTER (WHERE status = 2)::numeric / NULLIF(COUNT(*), 0)) * 100,
                        1
                    ) as critical_percentage,
                    COALESCE(ROUND((AVG(deviation_pct) FILTER (WHERE status = 2))::numeric, 0), 0) as avg_critical_deviation,
                    (
                        SELECT tag_name
                        FROM sensor_stats
                        WHERE status = 2
                        ORDER BY deviation_pct DESC NULLS LAST
                        LIMIT 1
                    ) as max_alarm_sensor,
                    (
                        SELECT value
                        FROM sensor_stats
                        WHERE status = 2
                        ORDER BY deviation_pct DESC NULLS LAST
                        LIMIT 1
                    ) as max_alarm_value
                FROM sensor_stats
            """)

            row = (await self.session.execute(query)).mappings().first()

            if not row:
                return {
                    "total_devices": 0,
                    "critical_count": 0,
                    "warning_count": 0,
                    "normal_count": 0,
                    "critical_percentage": 0.0,
                    "avg_critical_deviation": 0.0,
                    "max_alarm_sensor": "",
                    "max_alarm_value": 0.0
                }

            return {
                "total_devices": int(row["total_devices"]) if row["total_devices"] else 0,
                "critical_count": int(row["critical_count"]) if row["critical_count"] else 0,
                "warning_count": int(row["warning_count"]) if row["warning_count"] else 0,
                "normal_count": int(row["normal_count"]) if row["normal_count"] else 0,
                "critical_percentage": round(float(row["critical_percentage"]), 2) if row["critical_percentage"] else 0.0,
                "avg_critical_deviation": round(float(row["avg_critical_deviation"]), 2) if row["avg_critical_deviation"] else 0.0,
                "max_alarm_sensor": row["max_alarm_sensor"] or "",
                "max_alarm_value": round(float(row["max_alarm_value"]), 2) if row["max_alarm_value"] else 0.0
            }

        except Exception as e:
            console.error(f"Error calculating dashboard statistics: {e}")
            return {
                "total_devices": 0,
                "critical_count": 0,
                "warning_count": 0,
                "normal_count": 0,
                "critical_percentage": 0.0,
                "avg_critical_deviation": 0.0,
                "max_alarm_sensor": "",
                "max_alarm_value": 0.0
            }

    async def update_sensor_metadata(
        self,
        tag_name: str,
        description: str = "",
        unit: str = "",
        min_val: float = 0.0,
        max_val: float = 100.0,
        warning_low: float = None,
        warning_high: float = None,
        critical_low: float = None,
        critical_high: float = None
    ):
        """Update sensor metadata (description, unit) and QC rules (min/max + warning + critical thresholds)
        Uses raw SQL with text() - asyncpg compatible

        ISA-18.2 Threshold mapping:
        - critical_low/high: Level 5 (CRITICAL)
        - min_val/max_val: Level 4 (ERROR)
        - warning_low/high: Level 3 (WARNING)
        """
        try:
            from sqlalchemy import bindparam

            # Calculate default warning values if not provided
            if warning_low is None:
                warning_low = min_val + (max_val - min_val) * 0.2
            if warning_high is None:
                warning_high = min_val + (max_val - min_val) * 0.8

            # Calculate default critical values if not provided
            # Critical should be OUTSIDE warning range (more extreme)
            if critical_low is None:
                critical_low = min_val * 0.5  # 50% of min_val
            if critical_high is None:
                critical_high = max_val * 1.2  # 120% of max_val

            # Update influx_tag - both direct columns and meta JSON field
            stmt = text("""
                UPDATE influx_tag
                SET
                    unit = :unit,
                    description = :description,
                    meta = jsonb_set(
                        jsonb_set(
                            COALESCE(meta, '{}'::jsonb),
                            '{description}', to_jsonb(CAST(:description AS text))
                        ),
                        '{unit}', to_jsonb(CAST(:unit AS text))
                    )
                WHERE tag_name = :tag_name
            """).bindparams(
                bindparam('description', value=description),
                bindparam('unit', value=unit),
                bindparam('tag_name', value=tag_name)
            )
            await self.session.execute(stmt)

            # Check if QC rule exists
            result = await self.session.execute(
                text("SELECT COUNT(*) as cnt FROM influx_qc_rule WHERE tag_name = :tag_name").bindparams(
                    bindparam('tag_name', value=tag_name)
                )
            )
            row = result.first()

            if row and row[0] > 0:
                # Update existing rule
                stmt = text("""
                    UPDATE influx_qc_rule
                    SET min_val = :min_val, max_val = :max_val,
                        warning_low = :warning_low, warning_high = :warning_high,
                        critical_low = :critical_low, critical_high = :critical_high
                    WHERE tag_name = :tag_name
                """).bindparams(
                    bindparam('min_val', value=min_val),
                    bindparam('max_val', value=max_val),
                    bindparam('warning_low', value=warning_low),
                    bindparam('warning_high', value=warning_high),
                    bindparam('critical_low', value=critical_low),
                    bindparam('critical_high', value=critical_high),
                    bindparam('tag_name', value=tag_name)
                )
                await self.session.execute(stmt)
            else:
                # Insert new rule
                stmt = text("""
                    INSERT INTO influx_qc_rule (tag_name, min_val, max_val, warning_low, warning_high, critical_low, critical_high)
                    VALUES (:tag_name, :min_val, :max_val, :warning_low, :warning_high, :critical_low, :critical_high)
                """).bindparams(
                    bindparam('tag_name', value=tag_name),
                    bindparam('min_val', value=min_val),
                    bindparam('max_val', value=max_val),
                    bindparam('warning_low', value=warning_low),
                    bindparam('warning_high', value=warning_high),
                    bindparam('critical_low', value=critical_low),
                    bindparam('critical_high', value=critical_high)
                )
                await self.session.execute(stmt)

            await self.session.commit()
            console.info(f"Updated metadata for {tag_name}: desc={description}, unit={unit}, range=[{min_val}, {max_val}], warning=[{warning_low}, {warning_high}], critical=[{critical_low}, {critical_high}]")

        except Exception as e:
            console.error(f"Error updating sensor metadata: {e}")
            await self.session.rollback()
            raise