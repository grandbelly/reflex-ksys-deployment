"""
Alarm Service - Rule-based alarm management
- Uses raw SQL with AsyncSession (matches alarm_history schema)
- Returns dict (not ORM objects)
- Follows Dashboard/Communication service pattern
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import pytz
from reflex.utils import console
from ..utils.isa_standard import get_isa_priority


class AlarmService:
    """Alarm data service using raw SQL - matches real alarm_history schema"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_rule_based_alarms(
        self,
        hours: int = 24,
        limit: int = 100,
        scenario_filter: str = "RULE_BASE",
        page: int = 1,
        page_size: int = 20,
        severity_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get RULE_BASE alarms from recent hours (with pagination)

        Args:
            hours: Look back hours (default 24)
            limit: Max results for backward compatibility (default 100)
            scenario_filter: Scenario filter (default RULE_BASE)
            page: Page number (1-indexed, default 1)
            page_size: Items per page (default 20)
            severity_filter: Filter by severity (CRITICAL, WARNING, INFO)
            status_filter: Filter by status (UNACKNOWLEDGED, ACKNOWLEDGED)

        Returns:
            Dict with:
                - alarms: List of alarm dicts
                - total: Total count
                - page: Current page
                - page_size: Items per page
                - total_pages: Total pages
        """
        try:
            await self.session.execute(text("SET LOCAL statement_timeout = '10s'"))

            # Build WHERE clause dynamically
            # Match all RULE-based scenarios (RULE_BASE, D100_RULE, D101_RULE, DYNAMIC_RULE, etc.)
            where_clauses = [
                "(scenario_id LIKE '%%_P1_%%' OR scenario_id LIKE '%%_P2_%%' OR scenario_id LIKE '%%_P3_%%' OR scenario_id LIKE '%%_P4_%%' OR scenario_id LIKE '%%RULE%%' OR scenario_id = 'RULE_BASE')",
                "triggered_at >= NOW() - :hours * INTERVAL '1 hour'"
            ]

            # Add severity filter (map level to severity)
            if severity_filter:
                severity_map = {
                    "CRITICAL": 5,
                    "ERROR": 4,
                    "WARNING": 3,
                    "INFO": 2,
                    "CAUTION": 1,
                }
                if severity_filter.upper() in severity_map:
                    where_clauses.append(f"level = {severity_map[severity_filter.upper()]}")

            # Add status filter
            if status_filter:
                if status_filter.upper() == "UNACKNOWLEDGED":
                    where_clauses.append("acknowledged = false")
                elif status_filter.upper() == "ACKNOWLEDGED":
                    where_clauses.append("acknowledged = true")
                elif status_filter.upper() == "RESOLVED":
                    where_clauses.append("resolved = true")
                elif status_filter.upper() == "ACTIVE":
                    where_clauses.append("resolved = false")

            where_sql = " AND ".join(where_clauses)

            # Count total first
            count_q = text(f"""
                SELECT COUNT(*) as total
                FROM alarm_history
                WHERE {where_sql}
            """)

            count_result = await self.session.execute(count_q, {
                "hours": hours,
            })
            total = count_result.scalar() or 0

            # Calculate pagination
            offset = (page - 1) * page_size
            total_pages = (total + page_size - 1) // page_size if total > 0 else 1

            # Fetch paginated data
            q = text(f"""
                SELECT
                    event_id,
                    scenario_id,
                    level,
                    triggered_at,
                    message,
                    sensor_data->>'tag_name' as tag_name,
                    sensor_data->>'sensor_type' as sensor_type,
                    (sensor_data->>'value')::numeric as value,
                    sensor_data->>'unit' as unit,
                    (sensor_data->>'threshold_low')::numeric as threshold_low,
                    (sensor_data->>'threshold_high')::numeric as threshold_high,
                    sensor_data->>'cause' as cause,
                    acknowledged,
                    acknowledged_by,
                    acknowledged_at,
                    resolved,
                    resolved_at
                FROM alarm_history
                WHERE {where_sql}
                ORDER BY triggered_at DESC
                LIMIT :limit OFFSET :offset
            """)

            result = await self.session.execute(q, {
                "hours": hours,
                "limit": page_size,
                "offset": offset,
            })
            rows = result.mappings().all()

            # Convert to KST and format
            kst = pytz.timezone('Asia/Seoul')
            alarms = []

            for row in rows:
                triggered_at = row["triggered_at"]
                triggered_at_kst = triggered_at.astimezone(kst) if triggered_at else None

                resolved_at = row.get("resolved_at")
                resolved_at_kst = resolved_at.astimezone(kst) if resolved_at else None

                # Get ISA-18.2 info
                level_int = int(row["level"])
                isa_info = get_isa_priority(level_int)
                
                alarms.append({
                    "event_id": row["event_id"],
                    "scenario_id": row["scenario_id"],
                    "level": level_int,
                    "level_name": self._get_level_name(level_int),
                    "isa_priority": isa_info["priority"],
                    "isa_name": isa_info["isa_name"],
                    "isa_display": isa_info["display_name"],
                    "isa_color": isa_info["color"],
                    "triggered_at": triggered_at_kst.strftime("%Y-%m-%d %H:%M:%S") if triggered_at_kst else "",
                    "triggered_at_short": triggered_at_kst.strftime("%m-%d %H:%M") if triggered_at_kst else "",
                    "message": row["message"],
                    "tag_name": row["tag_name"],
                    "sensor_type": row["sensor_type"],
                    "value": float(row["value"]) if row["value"] else 0.0,
                    "value_formatted": f"{float(row.get('value', 0)):.2f}" if row.get("value") else "0.00",
                    "unit": row["unit"] or "",
                    "threshold_low": float(row["threshold_low"]) if row["threshold_low"] else None,
                    "threshold_high": float(row["threshold_high"]) if row["threshold_high"] else None,
                    "cause": row["cause"] or "",
                    "acknowledged": bool(row["acknowledged"]),
                    "acknowledged_by": row["acknowledged_by"] or "",
                    "resolved": bool(row["resolved"]),

                    # VTScada History format
                    "triggered_at_full": triggered_at_kst.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] if triggered_at_kst else "",
                    "triggered_time": triggered_at_kst.strftime("%H:%M:%S") if triggered_at_kst else "",
                    "resolved_time": resolved_at_kst.strftime("%H:%M:%S") if resolved_at_kst else "-",
                })

            console.info(f"Loaded {len(alarms)} / {total} RULE_BASE alarms (page {page}/{total_pages})")

            # Return paginated result
            return {
                "alarms": alarms,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }

        except Exception as e:
            console.error(f"Failed to load rule-based alarms: {e}")
            return {
                "alarms": [],
                "total": 0,
                "page": 1,
                "page_size": page_size,
                "total_pages": 1,
            }

    async def get_active_sensor_alarms(
        self,
        hours: int = 24,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Get sensor-level active alarms (one latest alarm per sensor)
        Matches Dashboard behavior - shows current status of each sensor

        Args:
            hours: Look back hours (default 24)
            page: Page number (1-indexed, default 1)
            page_size: Items per page (default 20)

        Returns:
            Dict with:
                - alarms: List of alarm dicts (one per sensor)
                - total: Total sensor count
                - page: Current page
                - page_size: Items per page
                - total_pages: Total pages
        """
        try:
            await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))
            kst = pytz.timezone("Asia/Seoul")

            # Count total sensors with alarms
            count_query = text("""
                SELECT COUNT(DISTINCT sensor_data->>'tag_name') as total
                FROM alarm_history
                WHERE (scenario_id LIKE :p1 OR scenario_id LIKE :p2 OR scenario_id LIKE :p3 OR scenario_id LIKE :p4 OR scenario_id LIKE :rule)
                AND triggered_at > (NOW() - INTERVAL '1 hour' * :hours)
            """)
            count_result = await self.session.execute(
                count_query,
                {"p1": "%_P1_%", "p2": "%_P2_%", "p3": "%_P3_%", "p4": "%_P4_%", "rule": "%RULE%", "hours": hours}
            )
            total = count_result.scalar() or 0

            # Get latest alarm per sensor (DISTINCT ON)
            offset = (page - 1) * page_size
            query = text("""
                SELECT DISTINCT ON (sensor_data->>'tag_name')
                    event_id,
                    sensor_data->>'tag_name' as tag_name,
                    scenario_id,
                    level,
                    message,
                    (sensor_data->>'value')::numeric as current_value,
                    sensor_data->>'unit' as unit,
                    triggered_at,
                    resolved,
                    resolved_at,
                    acknowledged,
                    acknowledged_at,
                    acknowledged_by
                FROM alarm_history
                WHERE (scenario_id LIKE :p1 OR scenario_id LIKE :p2 OR scenario_id LIKE :p3 OR scenario_id LIKE :p4 OR scenario_id LIKE :rule)
                AND triggered_at > (NOW() - INTERVAL '1 hour' * :hours)
                ORDER BY sensor_data->>'tag_name', triggered_at DESC
                LIMIT :limit OFFSET :offset
            """)

            result = await self.session.execute(
                query,
                {
                    "p1": "%_P1_%",
                    "p2": "%_P2_%",
                    "p3": "%_P3_%",
                    "p4": "%_P4_%",
                    "rule": "%RULE%",
                    "hours": hours,
                    "limit": page_size,
                    "offset": offset,
                }
            )
            rows = result.mappings().all()

            alarms = []
            for row in rows:
                triggered_at = row["triggered_at"]
                triggered_at_kst = triggered_at.astimezone(kst) if triggered_at else None

                resolved_at = row.get("resolved_at")
                resolved_at_kst = resolved_at.astimezone(kst) if resolved_at else None

                acknowledged_at = row.get("acknowledged_at")
                acknowledged_at_kst = acknowledged_at.astimezone(kst) if acknowledged_at else None

                # Get ISA-18.2 info
                level_int = int(row["level"])
                isa_info = get_isa_priority(level_int)
                
                alarms.append({
                    "event_id": row["event_id"],
                    "tag_name": row["tag_name"],
                    "scenario_id": row["scenario_id"],
                    "level": level_int,
                    "level_name": self._get_level_name(level_int),
                    "isa_priority": isa_info["priority"],
                    "isa_name": isa_info["isa_name"],
                    "isa_display": isa_info["display_name"],
                    "isa_color": isa_info["color"],
                    "message": row["message"],
                    "current_value": round(float(row["current_value"]), 2) if row["current_value"] else 0.0,
                    "value": round(float(row["current_value"]), 2) if row["current_value"] else 0.0,  # For compatibility
                    "unit": row.get("unit", ""),
                    "triggered_at": triggered_at_kst.strftime("%Y-%m-%d %H:%M:%S") if triggered_at_kst else "",
                    "triggered_at_short": triggered_at_kst.strftime("%m-%d %H:%M") if triggered_at_kst else "",
                    "resolved": bool(row["resolved"]),
                    "resolved_at": resolved_at_kst.strftime("%Y-%m-%d %H:%M:%S") if resolved_at_kst else "",
                    "acknowledged": bool(row["acknowledged"]),
                    "acknowledged_at": acknowledged_at_kst.strftime("%Y-%m-%d %H:%M:%S") if acknowledged_at_kst else "",
                    "acknowledged_by": row.get("acknowledged_by", ""),

                    # VTScada format
                    "triggered_at_full": triggered_at_kst.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] if triggered_at_kst else "",
                    "triggered_time": triggered_at_kst.strftime("%H:%M:%S") if triggered_at_kst else "",
                    "resolved_time": resolved_at_kst.strftime("%H:%M:%S") if resolved_at_kst else "-",
                })

            total_pages = max(1, (total + page_size - 1) // page_size)

            console.log(f"Loaded {len(alarms)} sensor-level alarms (page {page}/{total_pages})")

            return {
                "alarms": alarms,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }

        except Exception as e:
            console.error(f"Failed to load sensor-level alarms: {e}")
            return {
                "alarms": [],
                "total": 0,
                "page": 1,
                "page_size": page_size,
                "total_pages": 1,
            }

    async def get_alarm_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get alarm statistics for dashboard

        Args:
            hours: Look back hours (default 24)

        Returns:
            Dict with counts by level and status
        """
        try:
            await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

            q = text("""
                SELECT
                    level,
                    COUNT(*) as count,
                    COUNT(*) FILTER (WHERE acknowledged = false) as unacknowledged,
                    COUNT(*) FILTER (WHERE resolved = false) as unresolved
                FROM alarm_history
                WHERE triggered_at >= NOW() - :hours * INTERVAL '1 hour'
                  AND (scenario_id LIKE '%%_P1_%%' OR scenario_id LIKE '%%_P2_%%' OR scenario_id LIKE '%%_P3_%%' OR scenario_id LIKE '%%_P4_%%' OR scenario_id LIKE '%%RULE%%' OR scenario_id = 'RULE_BASE')
                GROUP BY level
                ORDER BY level DESC
            """)

            result = await self.session.execute(q, {"hours": hours})
            rows = result.mappings().all()

            # Aggregate statistics
            stats = {
                "total": 0,
                # ISA-18.2 Priority levels
                "priority_1_low": 0,        # Level 1-2
                "priority_2_medium": 0,     # Level 3
                "priority_3_high": 0,       # Level 4
                "priority_4_critical": 0,   # Level 5
                # Legacy compatibility
                "critical": 0,      # level 5
                "error": 0,         # level 4
                "warning": 0,       # level 3
                "info": 0,          # level 2
                "caution": 0,       # level 1
                "unacknowledged": 0,
                "unresolved": 0,
            }

            for row in rows:
                level = int(row["level"])
                count = int(row["count"])

                stats["total"] += count
                stats["unacknowledged"] += int(row["unacknowledged"])
                stats["unresolved"] += int(row["unresolved"])

                # Map to ISA-18.2 priorities
                isa_info = get_isa_priority(level)
                priority = isa_info["priority"]
                
                if priority == 1:
                    stats["priority_1_low"] += count
                elif priority == 2:
                    stats["priority_2_medium"] += count
                elif priority == 3:
                    stats["priority_3_high"] += count
                elif priority == 4:
                    stats["priority_4_critical"] += count

                # Legacy mapping (for backward compatibility)
                if level == 5:
                    stats["critical"] += count
                elif level == 4:
                    stats["error"] += count
                elif level == 3:
                    stats["warning"] += count
                elif level == 2:
                    stats["info"] += count
                elif level == 1:
                    stats["caution"] += count

            console.info(f"Alarm stats: {stats['total']} total, {stats['critical']} critical, {stats['warning']} warning")
            return stats

        except Exception as e:
            console.error(f"Failed to get alarm statistics: {e}")
            return {
                "total": 0,
                "critical": 0,
                "error": 0,
                "warning": 0,
                "info": 0,
                "caution": 0,
                "unacknowledged": 0,
                "unresolved": 0,
            }

    async def acknowledge_alarm(
        self,
        event_id: str,
        acknowledged_by: str = "system"
    ) -> bool:
        """
        Acknowledge an alarm

        Args:
            event_id: Alarm event ID (primary key)
            acknowledged_by: User who acknowledged

        Returns:
            True if successful
        """
        try:
            await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

            q = text("""
                UPDATE alarm_history
                SET
                    acknowledged = true,
                    acknowledged_by = :acknowledged_by,
                    acknowledged_at = NOW()
                WHERE event_id = :event_id
            """)

            await self.session.execute(q, {
                "event_id": event_id,
                "acknowledged_by": acknowledged_by
            })
            await self.session.commit()

            console.info(f"Acknowledged alarm {event_id} by {acknowledged_by}")
            return True

        except Exception as e:
            console.error(f"Failed to acknowledge alarm {event_id}: {e}")
            await self.session.rollback()
            return False

    @staticmethod
    def _get_level_name(level: int) -> str:
        """Convert level number to name"""
        level_map = {
            5: "CRITICAL",
            4: "ERROR",
            3: "WARNING",
            2: "INFO",
            1: "CAUTION"
        }
        return level_map.get(level, "UNKNOWN")