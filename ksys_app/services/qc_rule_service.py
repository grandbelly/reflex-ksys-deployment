"""
QC Rule Service - Alarm threshold management
- CRUD operations for influx_qc_rule
- ISA-18.2 compliant rule management
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from reflex.utils import console


class QCRuleService:
    """QC Rule data service using raw SQL"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_rules(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all QC rules

        Args:
            enabled_only: If True, return only enabled rules

        Returns:
            List of rule dicts
        """
        try:
            await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

            where_clause = "WHERE enabled = true" if enabled_only else ""

            query = text(f"""
                SELECT
                    r.tag_name,
                    r.min_val,
                    r.max_val,
                    r.warning_low,
                    r.warning_high,
                    r.critical_low,
                    r.critical_high,
                    r.enabled,
                    r.description,
                    r.updated_at,
                    COALESCE(t.unit, t.meta->>'unit', '') as unit,
                    COALESCE(t.description, t.meta->>'description', r.tag_name) as sensor_description
                FROM influx_qc_rule r
                LEFT JOIN influx_tag t ON r.tag_name = t.tag_name
                {where_clause}
                ORDER BY r.tag_name
            """)

            result = await self.session.execute(query)
            rows = result.mappings().all()

            rules = []
            for row in rows:
                rules.append({
                    "tag_name": row["tag_name"],
                    "min_val": float(row["min_val"]) if row["min_val"] is not None else None,
                    "max_val": float(row["max_val"]) if row["max_val"] is not None else None,
                    "warning_low": float(row["warning_low"]) if row["warning_low"] is not None else None,
                    "warning_high": float(row["warning_high"]) if row["warning_high"] is not None else None,
                    "critical_low": float(row["critical_low"]) if row["critical_low"] is not None else None,
                    "critical_high": float(row["critical_high"]) if row["critical_high"] is not None else None,
                    "enabled": bool(row["enabled"]),
                    "description": row["description"] or "",
                    "unit": row["unit"] or "",
                    "sensor_description": row["sensor_description"] or row["tag_name"],
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else "",
                })

            console.info(f"Loaded {len(rules)} QC rules")
            return rules

        except Exception as e:
            console.error(f"Failed to load QC rules: {e}")
            return []

    async def get_rule(self, tag_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a single QC rule by tag_name

        Args:
            tag_name: Sensor tag name

        Returns:
            Rule dict or None
        """
        try:
            await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

            query = text("""
                SELECT
                    r.tag_name,
                    r.min_val,
                    r.max_val,
                    r.warning_low,
                    r.warning_high,
                    r.critical_low,
                    r.critical_high,
                    r.enabled,
                    r.description,
                    r.updated_at,
                    COALESCE(t.unit, t.meta->>'unit', '') as unit,
                    COALESCE(t.description, t.meta->>'description', r.tag_name) as sensor_description
                FROM influx_qc_rule r
                LEFT JOIN influx_tag t ON r.tag_name = t.tag_name
                WHERE r.tag_name = :tag_name
            """)

            result = await self.session.execute(query, {"tag_name": tag_name})
            row = result.mappings().first()

            if not row:
                return None

            return {
                "tag_name": row["tag_name"],
                "min_val": float(row["min_val"]) if row["min_val"] is not None else None,
                "max_val": float(row["max_val"]) if row["max_val"] is not None else None,
                "warning_low": float(row["warning_low"]) if row["warning_low"] is not None else None,
                "warning_high": float(row["warning_high"]) if row["warning_high"] is not None else None,
                "critical_low": float(row["critical_low"]) if row["critical_low"] is not None else None,
                "critical_high": float(row["critical_high"]) if row["critical_high"] is not None else None,
                "enabled": bool(row["enabled"]),
                "description": row["description"] or "",
                "unit": row["unit"] or "",
                "sensor_description": row["sensor_description"] or row["tag_name"],
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else "",
            }

        except Exception as e:
            console.error(f"Failed to load QC rule for {tag_name}: {e}")
            return None

    async def upsert_rule(self, rule_data: Dict[str, Any]) -> bool:
        """
        Insert or update a QC rule

        Args:
            rule_data: Rule dictionary with fields

        Returns:
            True if successful
        """
        try:
            await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

            query = text("""
                INSERT INTO influx_qc_rule (
                    tag_name,
                    min_val,
                    max_val,
                    warning_low,
                    warning_high,
                    critical_low,
                    critical_high,
                    enabled,
                    description,
                    updated_at
                ) VALUES (
                    :tag_name,
                    :min_val,
                    :max_val,
                    :warning_low,
                    :warning_high,
                    :critical_low,
                    :critical_high,
                    :enabled,
                    :description,
                    NOW()
                )
                ON CONFLICT (tag_name) DO UPDATE SET
                    min_val = EXCLUDED.min_val,
                    max_val = EXCLUDED.max_val,
                    warning_low = EXCLUDED.warning_low,
                    warning_high = EXCLUDED.warning_high,
                    critical_low = EXCLUDED.critical_low,
                    critical_high = EXCLUDED.critical_high,
                    enabled = EXCLUDED.enabled,
                    description = EXCLUDED.description,
                    updated_at = NOW()
            """)

            await self.session.execute(query, rule_data)
            await self.session.commit()

            console.info(f"Upserted QC rule for {rule_data['tag_name']}")
            return True

        except Exception as e:
            console.error(f"Failed to upsert QC rule: {e}")
            await self.session.rollback()
            return False

    async def toggle_rule(self, tag_name: str, enabled: bool) -> bool:
        """
        Enable/disable a QC rule

        Args:
            tag_name: Sensor tag name
            enabled: New enabled state

        Returns:
            True if successful
        """
        try:
            await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

            query = text("""
                UPDATE influx_qc_rule
                SET enabled = :enabled, updated_at = NOW()
                WHERE tag_name = :tag_name
            """)

            await self.session.execute(query, {"tag_name": tag_name, "enabled": enabled})
            await self.session.commit()

            console.info(f"Toggled QC rule for {tag_name}: enabled={enabled}")
            return True

        except Exception as e:
            console.error(f"Failed to toggle QC rule: {e}")
            await self.session.rollback()
            return False

    async def delete_rule(self, tag_name: str) -> bool:
        """
        Delete a QC rule

        Args:
            tag_name: Sensor tag name

        Returns:
            True if successful
        """
        try:
            await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

            query = text("""
                DELETE FROM influx_qc_rule
                WHERE tag_name = :tag_name
            """)

            await self.session.execute(query, {"tag_name": tag_name})
            await self.session.commit()

            console.info(f"Deleted QC rule for {tag_name}")
            return True

        except Exception as e:
            console.error(f"Failed to delete QC rule: {e}")
            await self.session.rollback()
            return False
