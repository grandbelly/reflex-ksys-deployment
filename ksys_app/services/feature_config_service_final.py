"""
Feature Configuration Service - Final Working Version

PostgreSQL stored functions 사용으로 간단명료하게

Usage:
    service = FeatureConfigService(session)
    await service.add_lag(config_id, periods=12)
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json


class FeatureConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_config(self, tag_name: str, config_name: str = "default_arima") -> Optional[Dict]:
        query = text("""
            SELECT config_id, config_name, tag_name, model_type, features, notes
            FROM feature_config
            WHERE tag_name = :tag AND config_name = :name AND is_active = true
        """)
        result = await self.session.execute(query, {"tag": tag_name, "name": config_name})
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

    async def list_configs(self, tag_name: Optional[str] = None) -> List[Dict]:
        if tag_name:
            query = text("SELECT * FROM feature_config_summary WHERE tag_name = :tag")
            result = await self.session.execute(query, {"tag": tag_name})
        else:
            query = text("SELECT * FROM feature_config_summary")
            result = await self.session.execute(query)
        return [dict(r) for r in result.mappings().all()]

    async def add_lag(self, config_id: int, periods: int, unit: str = "rows", 
                      name: Optional[str] = None, enabled: bool = True) -> bool:
        query = text("SELECT add_lag_feature(:id, :periods, :unit, :name, :enabled)")
        await self.session.execute(query, {
            "id": config_id, "periods": periods, "unit": unit, "name": name, "enabled": enabled
        })
        await self.session.commit()
        return True

    async def add_rolling(self, config_id: int, window: int, agg: str, unit: str = "rows",
                          name: Optional[str] = None, enabled: bool = True) -> bool:
        query = text("SELECT add_rolling_feature(:id, :window, :agg, :unit, :name, :enabled)")
        await self.session.execute(query, {
            "id": config_id, "window": window, "agg": agg, "unit": unit, "name": name, "enabled": enabled
        })
        await self.session.commit()
        return True

    async def add_temporal(self, config_id: int, feature_type: str,
                           cyclical: bool = False, enabled: bool = True) -> bool:
        query = text("SELECT add_temporal_feature(:id, :type, :cyclical, :enabled)")
        await self.session.execute(query, {
            "id": config_id, "type": feature_type, "cyclical": cyclical, "enabled": enabled
        })
        await self.session.commit()
        return True

    async def toggle_lag(self, config_id: int, index: int, enabled: bool) -> bool:
        query = text("SELECT toggle_lag_feature(:id, :index, :enabled)")
        await self.session.execute(query, {"id": config_id, "index": index, "enabled": enabled})
        await self.session.commit()
        return True

    async def get_lags(self, config_id: int) -> List[Dict]:
        query = text("SELECT features->'lag' as lags FROM feature_config WHERE config_id = :id")
        result = await self.session.execute(query, {"id": config_id})
        row = result.fetchone()
        return list(row[0]) if row and row[0] else []

    async def get_enabled_features(self, tag_name: str, config_name: str = "default_arima") -> Dict[str, List]:
        config = await self.get_config(tag_name, config_name)
        if not config:
            return {}
        features = config["features"]
        result = {}
        for category in ["lag", "rolling", "temporal", "seasonal", "fourier"]:
            all_features = features.get(category, [])
            enabled = [f for f in all_features if f.get("enabled", True)]
            result[category] = enabled
        return result
    async def create_config(
        self,
        tag_name: str,
        config_name: str,
        model_type: str = "auto_arima",
        lag_features: Optional[List[Dict]] = None,
        rolling_features: Optional[List[Dict]] = None,
        temporal_features: Optional[List[Dict]] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Create a new feature configuration
        
        Args:
            tag_name: Sensor tag name
            config_name: Configuration name
            model_type: Model type (default: auto_arima)
            lag_features: List of {"periods": int, "enabled": bool}
            rolling_features: List of {"window": int, "enabled": bool}
            temporal_features: List of {"type": str, "enabled": bool}
            notes: Optional notes
            
        Returns:
            config_id of created configuration
        """
        # Build features JSON
        features = {}
        
        if lag_features:
            features["lag"] = [
                {
                    "periods": f["periods"],
                    "unit": "rows",
                    "name": f"lag_{f['periods']}h",
                    "enabled": f.get("enabled", True)
                }
                for f in lag_features
            ]
        
        if rolling_features:
            features["rolling"] = [
                {
                    "window": f["window"],
                    "agg": "mean",
                    "unit": "rows",
                    "name": f"rolling_mean_{f['window']}h",
                    "enabled": f.get("enabled", True)
                }
                for f in rolling_features
            ]
        
        if temporal_features:
            features["temporal"] = [
                {
                    "type": f["type"],
                    "name": f"temporal_{f['type']}",
                    "enabled": f.get("enabled", True)
                }
                for f in temporal_features
            ]
        
        # Insert into database
        query = text("""
            INSERT INTO feature_config (tag_name, config_name, model_type, features, notes, created_by)
            VALUES (:tag_name, :config_name, :model_type, CAST(:features AS jsonb), :notes, :created_by)
            RETURNING config_id
        """)
        
        result = await self.session.execute(query, {
            "tag_name": tag_name,
            "config_name": config_name,
            "model_type": model_type,
            "features": json.dumps(features),
            "notes": notes,
            "created_by": "wizard"
        })
        
        await self.session.commit()
        
        row = result.fetchone()
        return row[0] if row else None
