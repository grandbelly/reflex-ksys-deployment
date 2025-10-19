"""
Feature Configuration Service

Manages ALL feature engineering configurations from database tables.
NO hardcoding - everything is stored in:
- feature_config (main config)
- feature_lag_config (lag features)
- feature_rolling_config (rolling window features)
- feature_temporal_config (temporal features)
- feature_seasonal_config (seasonal decomposition)
- feature_fourier_config (Fourier features)
- feature_diff_config (differencing)
- feature_interaction_config (feature interactions)

Usage:
    service = FeatureConfigService(session)

    # Get all lag features for a config
    lags = await service.get_lag_features(config_id=1)

    # Add new rolling feature
    await service.add_rolling_feature(
        config_id=1,
        window_size=12,
        aggregation='mean',
        time_unit='rows'
    )

    # Get complete feature config for training
    config = await service.get_complete_config(
        tag_name='INLET_PRESSURE',
        config_name='default_arima'
    )
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from reflex.utils import console


class FeatureConfigService:
    """Service for managing feature engineering configurations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ========================================================================
    # Main Config Management
    # ========================================================================

    async def create_feature_config(
        self,
        config_name: str,
        tag_name: str,
        model_type: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """Create new feature configuration"""
        query = text("""
            INSERT INTO feature_config (config_name, tag_name, model_type, notes)
            VALUES (:config_name, :tag_name, :model_type, :notes)
            RETURNING config_id
        """)

        result = await self.session.execute(query, {
            "config_name": config_name,
            "tag_name": tag_name,
            "model_type": model_type,
            "notes": notes
        })

        await self.session.commit()
        row = result.fetchone()
        return row[0] if row else None

    async def get_config_id(self, tag_name: str, config_name: str) -> Optional[int]:
        """Get config_id for tag + config_name"""
        query = text("""
            SELECT config_id FROM feature_config
            WHERE tag_name = :tag_name AND config_name = :config_name AND is_active = true
        """)

        result = await self.session.execute(query, {
            "tag_name": tag_name,
            "config_name": config_name
        })

        row = result.fetchone()
        return row[0] if row else None

    async def list_configs(
        self,
        tag_name: Optional[str] = None,
        model_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all feature configurations"""
        conditions = ["is_active = true"]

        if tag_name:
            conditions.append("tag_name = :tag_name")
        if model_type:
            conditions.append("model_type = :model_type")

        where_clause = " AND ".join(conditions)

        query = text(f"""
            SELECT * FROM feature_config_summary
            WHERE {where_clause}
            ORDER BY created_at DESC
        """)

        params = {}
        if tag_name:
            params["tag_name"] = tag_name
        if model_type:
            params["model_type"] = model_type

        result = await self.session.execute(query, params)
        rows = result.mappings().all()

        return [dict(r) for r in rows]

    # ========================================================================
    # Lag Features
    # ========================================================================

    async def add_lag_feature(
        self,
        config_id: int,
        lag_periods: int,
        time_unit: str = "rows",
        feature_name: Optional[str] = None
    ) -> int:
        """Add lag feature to configuration"""
        query = text("""
            INSERT INTO feature_lag_config (config_id, lag_periods, time_unit, feature_name)
            VALUES (:config_id, :lag_periods, :time_unit, :feature_name)
            RETURNING lag_id
        """)

        result = await self.session.execute(query, {
            "config_id": config_id,
            "lag_periods": lag_periods,
            "time_unit": time_unit,
            "feature_name": feature_name
        })

        await self.session.commit()
        row = result.fetchone()
        return row[0] if row else None

    async def get_lag_features(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all lag features for a configuration"""
        query = text("""
            SELECT lag_id, lag_periods, time_unit, feature_name, is_enabled
            FROM feature_lag_config
            WHERE config_id = :config_id
            ORDER BY lag_periods
        """)

        result = await self.session.execute(query, {"config_id": config_id})
        rows = result.mappings().all()

        return [dict(r) for r in rows]

    # ========================================================================
    # Rolling Window Features
    # ========================================================================

    async def add_rolling_feature(
        self,
        config_id: int,
        window_size: int,
        aggregation: str,  # 'mean', 'std', 'min', 'max', 'sum', 'skew', 'kurt'
        time_unit: str = "rows",
        center: bool = False,
        min_periods: Optional[int] = None,
        feature_name: Optional[str] = None
    ) -> int:
        """Add rolling window feature"""
        query = text("""
            INSERT INTO feature_rolling_config
            (config_id, window_size, time_unit, aggregation, center, min_periods, feature_name)
            VALUES (:config_id, :window_size, :time_unit, :aggregation, :center, :min_periods, :feature_name)
            RETURNING rolling_id
        """)

        result = await self.session.execute(query, {
            "config_id": config_id,
            "window_size": window_size,
            "time_unit": time_unit,
            "aggregation": aggregation,
            "center": center,
            "min_periods": min_periods,
            "feature_name": feature_name
        })

        await self.session.commit()
        row = result.fetchone()
        return row[0] if row else None

    async def get_rolling_features(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all rolling window features"""
        query = text("""
            SELECT rolling_id, window_size, time_unit, aggregation, center, min_periods, feature_name, is_enabled
            FROM feature_rolling_config
            WHERE config_id = :config_id
            ORDER BY window_size, aggregation
        """)

        result = await self.session.execute(query, {"config_id": config_id})
        rows = result.mappings().all()

        return [dict(r) for r in rows]

    # ========================================================================
    # Temporal Features
    # ========================================================================

    async def add_temporal_feature(
        self,
        config_id: int,
        feature_type: str,  # 'hour', 'dayofweek', 'month', 'season', 'is_weekend', 'is_holiday'
        cyclical_encoding: bool = False,
        feature_name: Optional[str] = None
    ) -> int:
        """Add temporal feature"""
        query = text("""
            INSERT INTO feature_temporal_config (config_id, feature_type, cyclical_encoding, feature_name)
            VALUES (:config_id, :feature_type, :cyclical_encoding, :feature_name)
            RETURNING temporal_id
        """)

        result = await self.session.execute(query, {
            "config_id": config_id,
            "feature_type": feature_type,
            "cyclical_encoding": cyclical_encoding,
            "feature_name": feature_name
        })

        await self.session.commit()
        row = result.fetchone()
        return row[0] if row else None

    async def get_temporal_features(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all temporal features"""
        query = text("""
            SELECT temporal_id, feature_type, cyclical_encoding, feature_name, is_enabled
            FROM feature_temporal_config
            WHERE config_id = :config_id
            ORDER BY feature_type
        """)

        result = await self.session.execute(query, {"config_id": config_id})
        rows = result.mappings().all()

        return [dict(r) for r in rows]

    # ========================================================================
    # Seasonal Decomposition Features
    # ========================================================================

    async def add_seasonal_feature(
        self,
        config_id: int,
        decomposition_method: str,  # 'stl', 'seasonal_decompose', 'mstl'
        extract_component: str,  # 'trend', 'seasonal', 'residual', 'all'
        period: Optional[int] = None,
        robust: bool = False,
        feature_name: Optional[str] = None
    ) -> int:
        """Add seasonal decomposition feature"""
        query = text("""
            INSERT INTO feature_seasonal_config
            (config_id, decomposition_method, period, extract_component, robust, feature_name)
            VALUES (:config_id, :decomposition_method, :period, :extract_component, :robust, :feature_name)
            RETURNING seasonal_id
        """)

        result = await self.session.execute(query, {
            "config_id": config_id,
            "decomposition_method": decomposition_method,
            "period": period,
            "extract_component": extract_component,
            "robust": robust,
            "feature_name": feature_name
        })

        await self.session.commit()
        row = result.fetchone()
        return row[0] if row else None

    async def get_seasonal_features(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all seasonal decomposition features"""
        query = text("""
            SELECT seasonal_id, decomposition_method, period, extract_component, robust, feature_name, is_enabled
            FROM feature_seasonal_config
            WHERE config_id = :config_id
            ORDER BY decomposition_method, extract_component
        """)

        result = await self.session.execute(query, {"config_id": config_id})
        rows = result.mappings().all()

        return [dict(r) for r in rows]

    # ========================================================================
    # Fourier Features
    # ========================================================================

    async def add_fourier_feature(
        self,
        config_id: int,
        n_terms: int,
        period: int,
        feature_name: Optional[str] = None
    ) -> int:
        """Add Fourier feature"""
        query = text("""
            INSERT INTO feature_fourier_config (config_id, n_terms, period, feature_name)
            VALUES (:config_id, :n_terms, :period, :feature_name)
            RETURNING fourier_id
        """)

        result = await self.session.execute(query, {
            "config_id": config_id,
            "n_terms": n_terms,
            "period": period,
            "feature_name": feature_name
        })

        await self.session.commit()
        row = result.fetchone()
        return row[0] if row else None

    async def get_fourier_features(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all Fourier features"""
        query = text("""
            SELECT fourier_id, n_terms, period, feature_name, is_enabled
            FROM feature_fourier_config
            WHERE config_id = :config_id
            ORDER BY period, n_terms
        """)

        result = await self.session.execute(query, {"config_id": config_id})
        rows = result.mappings().all()

        return [dict(r) for r in rows]

    # ========================================================================
    # Differencing Features
    # ========================================================================

    async def add_diff_feature(
        self,
        config_id: int,
        diff_order: int,
        periods: int = 1,
        feature_name: Optional[str] = None
    ) -> int:
        """Add differencing feature"""
        query = text("""
            INSERT INTO feature_diff_config (config_id, diff_order, periods, feature_name)
            VALUES (:config_id, :diff_order, :periods, :feature_name)
            RETURNING diff_id
        """)

        result = await self.session.execute(query, {
            "config_id": config_id,
            "diff_order": diff_order,
            "periods": periods,
            "feature_name": feature_name
        })

        await self.session.commit()
        row = result.fetchone()
        return row[0] if row else None

    async def get_diff_features(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all differencing features"""
        query = text("""
            SELECT diff_id, diff_order, periods, feature_name, is_enabled
            FROM feature_diff_config
            WHERE config_id = :config_id
            ORDER BY diff_order, periods
        """)

        result = await self.session.execute(query, {"config_id": config_id})
        rows = result.mappings().all()

        return [dict(r) for r in rows]

    # ========================================================================
    # Interaction Features
    # ========================================================================

    async def add_interaction_feature(
        self,
        config_id: int,
        feature1: str,
        feature2: str,
        interaction_type: str,  # 'multiply', 'divide', 'add', 'subtract', 'ratio'
        feature_name: Optional[str] = None
    ) -> int:
        """Add interaction feature"""
        query = text("""
            INSERT INTO feature_interaction_config
            (config_id, feature1, feature2, interaction_type, feature_name)
            VALUES (:config_id, :feature1, :feature2, :interaction_type, :feature_name)
            RETURNING interaction_id
        """)

        result = await self.session.execute(query, {
            "config_id": config_id,
            "feature1": feature1,
            "feature2": feature2,
            "interaction_type": interaction_type,
            "feature_name": feature_name
        })

        await self.session.commit()
        row = result.fetchone()
        return row[0] if row else None

    async def get_interaction_features(self, config_id: int) -> List[Dict[str, Any]]:
        """Get all interaction features"""
        query = text("""
            SELECT interaction_id, feature1, feature2, interaction_type, feature_name, is_enabled
            FROM feature_interaction_config
            WHERE config_id = :config_id
            ORDER BY feature1, feature2
        """)

        result = await self.session.execute(query, {"config_id": config_id})
        rows = result.mappings().all()

        return [dict(r) for r in rows]

    # ========================================================================
    # Complete Configuration
    # ========================================================================

    async def get_complete_config(
        self,
        tag_name: str,
        config_name: str = "default_arima"
    ) -> Dict[str, Any]:
        """
        Get complete feature configuration for a tag
        Returns all enabled features in format ready for training pipeline
        """
        config_id = await self.get_config_id(tag_name, config_name)
        if not config_id:
            return {}

        return {
            "config_id": config_id,
            "tag_name": tag_name,
            "config_name": config_name,
            "lag": await self.get_lag_features(config_id),
            "rolling": await self.get_rolling_features(config_id),
            "temporal": await self.get_temporal_features(config_id),
            "seasonal": await self.get_seasonal_features(config_id),
            "fourier": await self.get_fourier_features(config_id),
            "diff": await self.get_diff_features(config_id),
            "interaction": await self.get_interaction_features(config_id)
        }

    # ========================================================================
    # Toggle Enable/Disable
    # ========================================================================

    async def toggle_feature(
        self,
        feature_type: str,  # 'lag', 'rolling', 'temporal', etc.
        feature_id: int,
        is_enabled: bool
    ) -> bool:
        """Enable/disable a specific feature"""
        table_map = {
            "lag": "feature_lag_config",
            "rolling": "feature_rolling_config",
            "temporal": "feature_temporal_config",
            "seasonal": "feature_seasonal_config",
            "fourier": "feature_fourier_config",
            "diff": "feature_diff_config",
            "interaction": "feature_interaction_config"
        }

        id_column_map = {
            "lag": "lag_id",
            "rolling": "rolling_id",
            "temporal": "temporal_id",
            "seasonal": "seasonal_id",
            "fourier": "fourier_id",
            "diff": "diff_id",
            "interaction": "interaction_id"
        }

        if feature_type not in table_map:
            raise ValueError(f"Unknown feature type: {feature_type}")

        table = table_map[feature_type]
        id_column = id_column_map[feature_type]

        query = text(f"""
            UPDATE {table}
            SET is_enabled = :is_enabled
            WHERE {id_column} = :feature_id
            RETURNING {id_column}
        """)

        result = await self.session.execute(query, {
            "is_enabled": is_enabled,
            "feature_id": feature_id
        })

        await self.session.commit()
        return result.fetchone() is not None

    # ========================================================================
    # Delete Features
    # ========================================================================

    async def delete_feature(
        self,
        feature_type: str,
        feature_id: int
    ) -> bool:
        """Delete a specific feature"""
        table_map = {
            "lag": ("feature_lag_config", "lag_id"),
            "rolling": ("feature_rolling_config", "rolling_id"),
            "temporal": ("feature_temporal_config", "temporal_id"),
            "seasonal": ("feature_seasonal_config", "seasonal_id"),
            "fourier": ("feature_fourier_config", "fourier_id"),
            "diff": ("feature_diff_config", "diff_id"),
            "interaction": ("feature_interaction_config", "interaction_id")
        }

        if feature_type not in table_map:
            raise ValueError(f"Unknown feature type: {feature_type}")

        table, id_column = table_map[feature_type]

        query = text(f"""
            DELETE FROM {table}
            WHERE {id_column} = :feature_id
            RETURNING {id_column}
        """)

        result = await self.session.execute(query, {"feature_id": feature_id})
        await self.session.commit()
        return result.fetchone() is not None


# Example usage
async def example_usage():
    """Example usage of FeatureConfigService"""
    from ksys_app.db_orm import get_async_session

    async with get_async_session() as session:
        service = FeatureConfigService(session)

        # 1. List all configs
        configs = await service.list_configs(tag_name="INLET_PRESSURE")
        console.log(f"Found {len(configs)} configs")

        # 2. Get complete config
        config = await service.get_complete_config(
            tag_name="INLET_PRESSURE",
            config_name="default_arima"
        )
        console.log("Complete config:", config)

        # 3. Add new lag feature
        lag_id = await service.add_lag_feature(
            config_id=config["config_id"],
            lag_periods=24,  # 4 hours at 10-min intervals
            time_unit="rows"
        )
        console.log(f"Added lag feature: {lag_id}")

        # 4. Toggle feature enable/disable
        success = await service.toggle_feature("lag", lag_id, False)
        console.log(f"Disabled lag feature: {success}")
