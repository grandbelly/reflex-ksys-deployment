"""
Feature Configuration Service V2 (Simplified JSONB)

단순화된 JSONB 기반 feature configuration 관리
8개 테이블 대신 1개 테이블로 모든 설정 관리

Usage:
    service = FeatureConfigServiceV2(session)

    # Get complete config
    config = await service.get_config('INLET_PRESSURE', 'default_arima')

    # Add lag feature
    await service.add_lag_feature(
        config_id=1,
        periods=12,
        unit='rows',
        name='lag_2h'
    )

    # Toggle feature
    await service.toggle_lag_feature(config_id=1, index=0, enabled=False)

    # Get all lag features
    lags = await service.get_lag_features(config_id=1)
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
from reflex.utils import console


class FeatureConfigServiceV2:
    """Simplified feature configuration service using JSONB"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ========================================================================
    # Main Config Operations
    # ========================================================================

    async def create_config(
        self,
        config_name: str,
        tag_name: str,
        model_type: Optional[str] = None,
        features: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> int:
        """Create new feature configuration"""
        default_features = {
            "lag": [],
            "rolling": [],
            "temporal": [],
            "seasonal": [],
            "fourier": [],
            "diff": [],
            "interaction": []
        }

        query = text("""
            INSERT INTO feature_config (config_name, tag_name, model_type, features, notes)
            VALUES (:config_name, :tag_name, :model_type, :features AS jsonbAS jsonb), :notes)
            RETURNING config_id
        """)

        result = await self.session.execute(query, {
            "config_name": config_name,
            "tag_name": tag_name,
            "model_type": model_type,
            "features": json.dumps(features or default_features),
            "notes": notes
        })

        await self.session.commit()
        row = result.fetchone()
        return row[0] if row else None

    async def get_config(
        self,
        tag_name: str,
        config_name: str = "default_arima"
    ) -> Optional[Dict[str, Any]]:
        """Get complete feature configuration"""
        query = text("""
            SELECT
                config_id,
                config_name,
                tag_name,
                model_type,
                features,
                is_active,
                notes
            FROM feature_config
            WHERE tag_name = :tag_name
              AND config_name = :config_name
              AND is_active = true
        """)

        result = await self.session.execute(query, {
            "tag_name": tag_name,
            "config_name": config_name
        })

        row = result.fetchone()
        if not row:
            return None

        return {
            "config_id": row[0],
            "config_name": row[1],
            "tag_name": row[2],
            "model_type": row[3],
            "features": dict(row[4]),  # JSONB → dict
            "is_active": row[5],
            "notes": row[6]
        }

    async def list_configs(
        self,
        tag_name: Optional[str] = None,
        model_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all feature configurations"""
        conditions = ["is_active = true"]
        params = {}

        if tag_name:
            conditions.append("tag_name = :tag_name")
            params["tag_name"] = tag_name

        if model_type:
            conditions.append("model_type = :model_type")
            params["model_type"] = model_type

        where_clause = " AND ".join(conditions)

        query = text(f"""
            SELECT * FROM feature_config_summary
            WHERE {where_clause}
            ORDER BY created_at DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.mappings().all()

        return [dict(r) for r in rows]

    async def update_features(
        self,
        config_id: int,
        features: Dict[str, Any]
    ) -> bool:
        """Update entire features JSONB"""
        query = text("""
            UPDATE feature_config
            SET features = :features AS jsonbAS jsonb)
            WHERE config_id = :config_id
            RETURNING config_id
        """)

        result = await self.session.execute(query, {
            "config_id": config_id,
            "features": json.dumps(features)
        })

        await self.session.commit()
        return result.fetchone() is not None

    # ========================================================================
    # Lag Features
    # ========================================================================

    async def get_lag_features(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all lag features"""
        query = text("""
            SELECT features->'lag' as lag_features
            FROM feature_config
            WHERE config_id = :config_id
        """)

        result = await self.session.execute(query, {"config_id": config_id})
        row = result.fetchone()

        return list(row[0]) if row and row[0] else []

    async def add_lag_feature(
        self,
        config_id: int,
        periods: int,
        unit: str = "rows",
        name: Optional[str] = None,
        enabled: bool = True
    ) -> bool:
        """Add lag feature to configuration"""
        new_lag = {
            "periods": periods,
            "unit": unit,
            "name": name or f"lag_{periods}{unit}",
            "enabled": enabled
        }

        query = text("""
            UPDATE feature_config
            SET features = jsonb_set(
                features,
                '{lag}',
                COALESCE(features->'lag', '[]') || CAST(:new_lag AS jsonb)
            )
            WHERE config_id = :config_id
            RETURNING config_id
        """)

        result = await self.session.execute(query, {
            "config_id": config_id,
            "new_lag": json.dumps(new_lag)
        })

        await self.session.commit()
        return result.fetchone() is not None

    async def toggle_lag_feature(
        self,
        config_id: int,
        index: int,
        enabled: bool
    ) -> bool:
        """Toggle lag feature enabled/disabled"""
        query = text(f"""
            UPDATE feature_config
            SET features = jsonb_set(
                features,
                '{{lag,{index},enabled}}',
                :enabled AS jsonbAS jsonb)
            )
            WHERE config_id = :config_id
            RETURNING config_id
        """)

        result = await self.session.execute(query, {
            "config_id": config_id,
            "enabled": json.dumps(enabled)
        })

        await self.session.commit()
        return result.fetchone() is not None

    async def remove_lag_feature(self, config_id: int, index: int) -> bool:
        """Remove lag feature by index"""
        # JSONB array element removal (PostgreSQL 12+)
        query = text(f"""
            UPDATE feature_config
            SET features = jsonb_set(
                features,
                '{{lag}}',
                (features->'lag') - {index}
            )
            WHERE config_id = :config_id
            RETURNING config_id
        """)

        result = await self.session.execute(query, {"config_id": config_id})
        await self.session.commit()
        return result.fetchone() is not None

    # ========================================================================
    # Rolling Window Features
    # ========================================================================

    async def get_rolling_features(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all rolling window features"""
        query = text("""
            SELECT features->'rolling' as rolling_features
            FROM feature_config
            WHERE config_id = :config_id
        """)

        result = await self.session.execute(query, {"config_id": config_id})
        row = result.fetchone()

        return list(row[0]) if row and row[0] else []

    async def add_rolling_feature(
        self,
        config_id: int,
        window: int,
        agg: str,  # 'mean', 'std', 'min', 'max', 'sum'
        unit: str = "rows",
        name: Optional[str] = None,
        enabled: bool = True
    ) -> bool:
        """Add rolling window feature"""
        new_rolling = {
            "window": window,
            "agg": agg,
            "unit": unit,
            "name": name or f"rolling_{agg}_{window}{unit}",
            "enabled": enabled
        }

        query = text("""
            UPDATE feature_config
            SET features = jsonb_set(
                features,
                '{rolling}',
                COALESCE(features->'rolling', '[]'AS jsonb)) || :new_rolling AS jsonbAS jsonb)
            )
            WHERE config_id = :config_id
            RETURNING config_id
        """)

        result = await self.session.execute(query, {
            "config_id": config_id,
            "new_rolling": json.dumps(new_rolling)
        })

        await self.session.commit()
        return result.fetchone() is not None

    # ========================================================================
    # Temporal Features
    # ========================================================================

    async def get_temporal_features(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all temporal features"""
        query = text("""
            SELECT features->'temporal' as temporal_features
            FROM feature_config
            WHERE config_id = :config_id
        """)

        result = await self.session.execute(query, {"config_id": config_id})
        row = result.fetchone()

        return list(row[0]) if row and row[0] else []

    async def add_temporal_feature(
        self,
        config_id: int,
        feature_type: str,  # 'hour', 'dayofweek', 'month', 'is_weekend'
        cyclical: bool = False,
        enabled: bool = True
    ) -> bool:
        """Add temporal feature"""
        new_temporal = {
            "type": feature_type,
            "cyclical": cyclical,
            "enabled": enabled
        }

        query = text("""
            UPDATE feature_config
            SET features = jsonb_set(
                features,
                '{temporal}',
                COALESCE(features->'temporal', '[]'AS jsonb)) || :new_temporal AS jsonbAS jsonb)
            )
            WHERE config_id = :config_id
            RETURNING config_id
        """)

        result = await self.session.execute(query, {
            "config_id": config_id,
            "new_temporal": json.dumps(new_temporal)
        })

        await self.session.commit()
        return result.fetchone() is not None

    # ========================================================================
    # Get All Features (for Pipeline V2)
    # ========================================================================

    async def get_all_enabled_features(
        self,
        tag_name: str,
        config_name: str = "default_arima"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all enabled features ready for Pipeline V2
        Returns only enabled features in each category
        """
        config = await self.get_config(tag_name, config_name)
        if not config:
            return {}

        features = config["features"]
        result = {}

        # Filter enabled features for each category
        for category in ["lag", "rolling", "temporal", "seasonal", "fourier", "diff", "interaction"]:
            category_features = features.get(category, [])
            enabled_features = [
                f for f in category_features
                if f.get("enabled", True)  # Default to enabled if not specified
            ]
            result[category] = enabled_features

        return result

    # ========================================================================
    # Bulk Operations
    # ========================================================================

    async def clone_config(
        self,
        source_config_id: int,
        new_config_name: str
    ) -> int:
        """Clone existing configuration"""
        query = text("""
            INSERT INTO feature_config (config_name, tag_name, model_type, features, notes)
            SELECT
                :new_config_name,
                tag_name,
                model_type,
                features,
                'Cloned from ' || config_name
            FROM feature_config
            WHERE config_id = :source_config_id
            RETURNING config_id
        """)

        result = await self.session.execute(query, {
            "source_config_id": source_config_id,
            "new_config_name": new_config_name
        })

        await self.session.commit()
        row = result.fetchone()
        return row[0] if row else None

    async def delete_config(self, config_id: int, soft_delete: bool = True) -> bool:
        """Delete configuration (soft or hard)"""
        if soft_delete:
            query = text("""
                UPDATE feature_config
                SET is_active = false
                WHERE config_id = :config_id
                RETURNING config_id
            """)
        else:
            query = text("""
                DELETE FROM feature_config
                WHERE config_id = :config_id
                RETURNING config_id
            """)

        result = await self.session.execute(query, {"config_id": config_id})
        await self.session.commit()
        return result.fetchone() is not None

    # ========================================================================
    # Validation
    # ========================================================================

    async def validate_config(self, config_id: int) -> tuple[bool, List[str]]:
        """Validate feature configuration"""
        config = await self.get_config_by_id(config_id)
        if not config:
            return False, ["Config not found"]

        errors = []
        features = config["features"]

        # Validate lag features
        for i, lag in enumerate(features.get("lag", [])):
            if not isinstance(lag.get("periods"), int) or lag["periods"] <= 0:
                errors.append(f"Lag feature {i}: periods must be positive integer")

        # Validate rolling features
        for i, rolling in enumerate(features.get("rolling", [])):
            if not isinstance(rolling.get("window"), int) or rolling["window"] <= 0:
                errors.append(f"Rolling feature {i}: window must be positive integer")
            if rolling.get("agg") not in ["mean", "std", "min", "max", "sum", "skew", "kurt"]:
                errors.append(f"Rolling feature {i}: invalid aggregation type")

        return len(errors) == 0, errors

    async def get_config_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """Get config by ID"""
        query = text("""
            SELECT config_id, config_name, tag_name, model_type, features, is_active, notes
            FROM feature_config
            WHERE config_id = :config_id
        """)

        result = await self.session.execute(query, {"config_id": config_id})
        row = result.fetchone()

        if not row:
            return None

        return {
            "config_id": row[0],
            "config_name": row[1],
            "tag_name": row[2],
            "model_type": row[3],
            "features": dict(row[4]),
            "is_active": row[5],
            "notes": row[6]
        }


# Example usage
async def example_usage():
    """Example usage of FeatureConfigServiceV2"""
    from ksys_app.db_orm import get_async_session

    async with get_async_session() as session:
        service = FeatureConfigServiceV2(session)

        # 1. Get config
        config = await service.get_config("INLET_PRESSURE", "default_arima")
        console.log("Config:", config)

        # 2. Get all enabled features
        features = await service.get_all_enabled_features("INLET_PRESSURE", "default_arima")
        console.log("Enabled features:", features)

        # 3. Add new lag feature
        await service.add_lag_feature(
            config_id=config["config_id"],
            periods=48,
            unit="rows",
            name="lag_8h"
        )

        # 4. Toggle feature
        await service.toggle_lag_feature(
            config_id=config["config_id"],
            index=0,
            enabled=False
        )

        # 5. Clone config
        new_id = await service.clone_config(
            source_config_id=config["config_id"],
            new_config_name="experimental_v2"
        )
        console.log(f"Cloned config: {new_id}")
