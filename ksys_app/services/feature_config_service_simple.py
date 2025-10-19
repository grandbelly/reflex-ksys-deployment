"""
Feature Configuration Service - Simple & Working Version

간단하고 확실히 작동하는 버전
PostgreSQL 함수 사용으로 SQL 문법 문제 없음

Usage:
    service = FeatureConfigService(session)
    config = await service.get_config('INLET_PRESSURE', 'default_arima')
    await service.add_lag(config_id, periods=12, unit='rows')
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
from reflex.utils import console


class FeatureConfigService:
    """Simple feature configuration service"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ========================================================================
    # Config CRUD
    # ========================================================================

    async def get_config(
        self,
        tag_name: str,
        config_name: str = "default_arima"
    ) -> Optional[Dict[str, Any]]:
        """Get feature configuration"""
        query = text("""
            SELECT config_id, config_name, tag_name, model_type, features, notes
            FROM feature_config
            WHERE tag_name = :tag_name AND config_name = :config_name AND is_active = true
        """)

        result = await self.session.execute(query, {"tag_name": tag_name, "config_name": config_name})
        row = result.fetchone()

        if not row:
            return None

        return {
            "config_id": row[0],
            "config_name": row[1],
            "tag_name": row[2],
            "model_type": row[3],
            "features": dict(row[4]) if row[4] else {},
            "notes": row[5]
        }

    async def list_configs(self, tag_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all configurations"""
        if tag_name:
            query = text("SELECT * FROM feature_config_summary WHERE tag_name = :tag_name")
            result = await self.session.execute(query, {"tag_name": tag_name})
        else:
            query = text("SELECT * FROM feature_config_summary")
            result = await self.session.execute(query)

        return [dict(r) for r in result.mappings().all()]

    async def create_config(
        self,
        config_name: str,
        tag_name: str,
        model_type: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """Create new configuration"""
        query = text("""
            INSERT INTO feature_config (config_name, tag_name, model_type, features, notes)
            VALUES (:name, :tag, :model, '{}'::jsonb, :notes)
            RETURNING config_id
        """)

        result = await self.session.execute(query, {
            "name": config_name,
            "tag": tag_name,
            "model": model_type,
            "notes": notes
        })

        await self.session.commit()
        return result.scalar()

    # ========================================================================
    # Lag Features
    # ========================================================================

    async def add_lag(
        self,
        config_id: int,
        periods: int,
        unit: str = "rows",
        name: Optional[str] = None,
        enabled: bool = True
    ) -> bool:
        """Add lag feature using PostgreSQL function"""
        name = name or f"lag_{periods}{unit}"

        # Use PostgreSQL jsonb_build_object function
        query = text("""
            UPDATE feature_config
            SET features = jsonb_set(
                features,
                '{lag}',
                COALESCE(features->'lag', '[]'::jsonb) ||
                jsonb_build_array(
                    jsonb_build_object(
                        'periods', :periods,
                        'unit', :unit,
                        'name', :name,
                        'enabled', :enabled
                    )
                )
            )
            WHERE config_id = :config_id
        """)

        await self.session.execute(query, {
            "config_id": config_id,
            "periods": periods,
            "unit": unit,
            "name": name,
            "enabled": enabled
        })

        await self.session.commit()
        return True

    async def get_lags(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all lag features"""
        query = text("SELECT features->'lag' as lags FROM feature_config WHERE config_id = :id")
        result = await self.session.execute(query, {"id": config_id})
        row = result.fetchone()
        return list(row[0]) if row and row[0] else []

    async def toggle_lag(self, config_id: int, index: int, enabled: bool) -> bool:
        """Toggle lag feature enabled/disabled"""
        query = text(f"""
            UPDATE feature_config
            SET features = jsonb_set(
                features,
                '{{lag,{index},enabled}}',
                to_jsonb(:enabled::boolean)
            )
            WHERE config_id = :config_id
        """)

        await self.session.execute(query, {"config_id": config_id, "enabled": enabled})
        await self.session.commit()
        return True

    # ========================================================================
    # Rolling Features
    # ========================================================================

    async def add_rolling(
        self,
        config_id: int,
        window: int,
        agg: str,
        unit: str = "rows",
        name: Optional[str] = None,
        enabled: bool = True
    ) -> bool:
        """Add rolling feature"""
        name = name or f"rolling_{agg}_{window}{unit}"

        query = text("""
            UPDATE feature_config
            SET features = jsonb_set(
                features,
                '{rolling}',
                COALESCE(features->'rolling', '[]'::jsonb) ||
                jsonb_build_array(
                    jsonb_build_object(
                        'window', :window,
                        'agg', :agg,
                        'unit', :unit,
                        'name', :name,
                        'enabled', :enabled
                    )
                )
            )
            WHERE config_id = :config_id
        """)

        await self.session.execute(query, {
            "config_id": config_id,
            "window": window,
            "agg": agg,
            "unit": unit,
            "name": name,
            "enabled": enabled
        })

        await self.session.commit()
        return True

    async def get_rollings(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all rolling features"""
        query = text("SELECT features->'rolling' as rolling FROM feature_config WHERE config_id = :id")
        result = await self.session.execute(query, {"id": config_id})
        row = result.fetchone()
        return list(row[0]) if row and row[0] else []

    # ========================================================================
    # Temporal Features
    # ========================================================================

    async def add_temporal(
        self,
        config_id: int,
        feature_type: str,
        cyclical: bool = False,
        enabled: bool = True
    ) -> bool:
        """Add temporal feature"""
        query = text("""
            UPDATE feature_config
            SET features = jsonb_set(
                features,
                '{temporal}',
                COALESCE(features->'temporal', '[]'::jsonb) ||
                jsonb_build_array(
                    jsonb_build_object(
                        'type', :type,
                        'cyclical', :cyclical,
                        'enabled', :enabled
                    )
                )
            )
            WHERE config_id = :config_id
        """)

        await self.session.execute(query, {
            "config_id": config_id,
            "type": feature_type,
            "cyclical": cyclical,
            "enabled": enabled
        })

        await self.session.commit()
        return True

    async def get_temporals(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all temporal features"""
        query = text("SELECT features->'temporal' as temporal FROM feature_config WHERE config_id = :id")
        result = await self.session.execute(query, {"id": config_id})
        row = result.fetchone()
        return list(row[0]) if row and row[0] else []

    # ========================================================================
    # Get All Enabled Features (for Pipeline)
    # ========================================================================

    async def get_enabled_features(
        self,
        tag_name: str,
        config_name: str = "default_arima"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all enabled features ready for Pipeline V2"""
        config = await self.get_config(tag_name, config_name)
        if not config:
            return {}

        features = config["features"]
        result = {}

        # Filter enabled features
        for category in ["lag", "rolling", "temporal", "seasonal", "fourier"]:
            all_features = features.get(category, [])
            enabled = [f for f in all_features if f.get("enabled", True)]
            result[category] = enabled

        return result

    # ========================================================================
    # Bulk Operations
    # ========================================================================

    async def clone_config(self, source_id: int, new_name: str) -> int:
        """Clone configuration"""
        query = text("""
            INSERT INTO feature_config (config_name, tag_name, model_type, features, notes)
            SELECT :new_name, tag_name, model_type, features, 'Cloned from ' || config_name
            FROM feature_config
            WHERE config_id = :source_id
            RETURNING config_id
        """)

        result = await self.session.execute(query, {"source_id": source_id, "new_name": new_name})
        await self.session.commit()
        return result.scalar()

    async def delete_config(self, config_id: int) -> bool:
        """Soft delete configuration"""
        query = text("UPDATE feature_config SET is_active = false WHERE config_id = :id")
        await self.session.execute(query, {"id": config_id})
        await self.session.commit()
        return True

    async def update_features_bulk(self, config_id: int, features: Dict[str, Any]) -> bool:
        """Update entire features object"""
        query = text("""
            UPDATE feature_config
            SET features = :features::jsonb
            WHERE config_id = :config_id
        """)

        await self.session.execute(query, {
            "config_id": config_id,
            "features": json.dumps(features)
        })

        await self.session.commit()
        return True
