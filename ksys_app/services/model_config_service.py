"""
Model Configuration Service

Manages model hyperparameters stored in model_registry table.
Provides CRUD operations for model configurations without hardcoding.

Usage:
    service = ModelConfigService(session)

    # Get default config for model type
    config = await service.get_default_config("auto_arima")

    # Save custom config
    await service.save_model_config(
        model_id=1,
        hyperparameters={"seasonal": True, "m": 24}
    )

    # Get config for specific model
    config = await service.get_model_config(model_id=1)
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
from datetime import datetime
import pytz

KST = pytz.timezone('Asia/Seoul')


class ModelConfigService:
    """Service for managing model hyperparameters"""

    # Model type schemas (NOT hardcoded values, just structure definitions)
    MODEL_SCHEMAS = {
        "auto_arima": {
            "seasonal": {
                "type": "boolean",
                "default": False,
                "description": "Enable seasonal component"
            },
            "m": {
                "type": "integer",
                "default": 144,  # 24 hours at 10-min intervals
                "min": 1,
                "max": 288,
                "description": "Seasonality period (144 = daily for 10-min data)"
            },
            "max_p": {
                "type": "integer",
                "default": 5,
                "min": 0,
                "max": 10,
                "description": "Maximum AR order"
            },
            "max_d": {
                "type": "integer",
                "default": 2,
                "min": 0,
                "max": 3,
                "description": "Maximum differencing order"
            },
            "max_q": {
                "type": "integer",
                "default": 5,
                "min": 0,
                "max": 10,
                "description": "Maximum MA order"
            },
            "stepwise": {
                "type": "boolean",
                "default": True,
                "description": "Use stepwise search (faster)"
            }
        },
        "prophet": {
            "changepoint_prior_scale": {
                "type": "float",
                "default": 0.05,
                "min": 0.001,
                "max": 0.5,
                "description": "Flexibility of trend changes"
            },
            "seasonality_prior_scale": {
                "type": "float",
                "default": 10.0,
                "min": 0.01,
                "max": 100.0,
                "description": "Strength of seasonality"
            },
            "holidays_prior_scale": {
                "type": "float",
                "default": 10.0,
                "min": 0.01,
                "max": 100.0,
                "description": "Strength of holiday effects"
            },
            "seasonality_mode": {
                "type": "select",
                "options": ["additive", "multiplicative"],
                "default": "additive",
                "description": "Seasonality mode"
            },
            "daily_seasonality": {
                "type": "boolean",
                "default": True,
                "description": "Enable daily seasonality"
            },
            "weekly_seasonality": {
                "type": "boolean",
                "default": True,
                "description": "Enable weekly seasonality"
            }
        },
        "xgboost": {
            "n_estimators": {
                "type": "integer",
                "default": 100,
                "min": 10,
                "max": 1000,
                "description": "Number of boosting rounds"
            },
            "max_depth": {
                "type": "integer",
                "default": 6,
                "min": 1,
                "max": 15,
                "description": "Maximum tree depth"
            },
            "learning_rate": {
                "type": "float",
                "default": 0.1,
                "min": 0.001,
                "max": 1.0,
                "description": "Step size shrinkage"
            },
            "subsample": {
                "type": "float",
                "default": 0.8,
                "min": 0.1,
                "max": 1.0,
                "description": "Subsample ratio"
            },
            "colsample_bytree": {
                "type": "float",
                "default": 0.8,
                "min": 0.1,
                "max": 1.0,
                "description": "Column subsample ratio"
            },
            "gamma": {
                "type": "float",
                "default": 0.0,
                "min": 0.0,
                "max": 10.0,
                "description": "Minimum loss reduction"
            }
        },
        "ensemble": {
            "strategy": {
                "type": "select",
                "options": ["simple_average", "weighted_average", "stacking"],
                "default": "weighted_average",
                "description": "Ensemble strategy"
            },
            "models": {
                "type": "multiselect",
                "options": ["auto_arima", "prophet", "xgboost"],
                "default": ["auto_arima", "prophet"],
                "description": "Base models to combine"
            },
            "weights": {
                "type": "json",
                "default": {"auto_arima": 0.6, "prophet": 0.4},
                "description": "Model weights (for weighted_average)"
            }
        }
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_model_schema(self, model_type: str) -> Dict[str, Any]:
        """Get parameter schema for model type"""
        return self.MODEL_SCHEMAS.get(model_type, {})

    async def get_default_config(self, model_type: str) -> Dict[str, Any]:
        """Get default hyperparameters for model type"""
        schema = await self.get_model_schema(model_type)
        return {
            param: info["default"]
            for param, info in schema.items()
        }

    async def get_model_config(self, model_id: int) -> Optional[Dict[str, Any]]:
        """Get hyperparameters for specific model"""
        query = text("""
            SELECT hyperparameters
            FROM model_registry
            WHERE model_id = :model_id
        """)

        result = await self.session.execute(query, {"model_id": model_id})
        row = result.fetchone()

        if row and row[0]:
            return dict(row[0])  # JSONB → dict
        return None

    async def save_model_config(
        self,
        model_id: int,
        hyperparameters: Dict[str, Any]
    ) -> bool:
        """Update hyperparameters for existing model"""
        query = text("""
            UPDATE model_registry
            SET hyperparameters = :hyperparameters::jsonb
            WHERE model_id = :model_id
            RETURNING model_id
        """)

        result = await self.session.execute(query, {
            "model_id": model_id,
            "hyperparameters": json.dumps(hyperparameters)
        })

        await self.session.commit()
        return result.fetchone() is not None

    async def create_model_config(
        self,
        tag_name: str,
        model_type: str,
        version: str,
        hyperparameters: Dict[str, Any],
        model_path: str = "",
        **kwargs
    ) -> int:
        """Create new model config in registry"""
        query = text("""
            INSERT INTO model_registry (
                model_name,
                model_type,
                version,
                tag_name,
                hyperparameters,
                model_path,
                created_at
            )
            VALUES (
                :model_name,
                :model_type,
                :version,
                :tag_name,
                :hyperparameters::jsonb,
                :model_path,
                :created_at
            )
            RETURNING model_id
        """)

        result = await self.session.execute(query, {
            "model_name": f"{tag_name}_{model_type}",
            "model_type": model_type,
            "version": version,
            "tag_name": tag_name,
            "hyperparameters": json.dumps(hyperparameters),
            "model_path": model_path or f"models/{tag_name}_{model_type}_{version}.pkl",
            "created_at": datetime.now(KST)
        })

        await self.session.commit()
        row = result.fetchone()
        return row[0] if row else None

    async def list_model_configs(
        self,
        tag_name: Optional[str] = None,
        model_type: Optional[str] = None,
        is_active: bool = True
    ) -> List[Dict[str, Any]]:
        """List all model configurations"""
        conditions = ["is_active = :is_active"] if is_active else []

        if tag_name:
            conditions.append("tag_name = :tag_name")
        if model_type:
            conditions.append("model_type = :model_type")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = text(f"""
            SELECT
                model_id,
                model_name,
                model_type,
                version,
                tag_name,
                hyperparameters,
                train_mape,
                train_rmse,
                created_at
            FROM model_registry
            WHERE {where_clause}
            ORDER BY created_at DESC
        """)

        params = {"is_active": is_active}
        if tag_name:
            params["tag_name"] = tag_name
        if model_type:
            params["model_type"] = model_type

        result = await self.session.execute(query, params)
        rows = result.mappings().all()

        return [
            {
                "model_id": r["model_id"],
                "model_name": r["model_name"],
                "model_type": r["model_type"],
                "version": r["version"],
                "tag_name": r["tag_name"],
                "hyperparameters": dict(r["hyperparameters"]) if r["hyperparameters"] else {},
                "train_mape": float(r["train_mape"]) if r["train_mape"] else None,
                "train_rmse": float(r["train_rmse"]) if r["train_rmse"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None
            }
            for r in rows
        ]

    async def delete_model_config(self, model_id: int, soft_delete: bool = True) -> bool:
        """Delete model configuration (soft or hard delete)"""
        if soft_delete:
            # Mark as inactive
            query = text("""
                UPDATE model_registry
                SET is_active = false
                WHERE model_id = :model_id
                RETURNING model_id
            """)
        else:
            # Hard delete (will cascade to predictions, performance, drift)
            query = text("""
                DELETE FROM model_registry
                WHERE model_id = :model_id
                RETURNING model_id
            """)

        result = await self.session.execute(query, {"model_id": model_id})
        await self.session.commit()
        return result.fetchone() is not None

    async def clone_model_config(
        self,
        source_model_id: int,
        new_version: str,
        hyperparameters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Clone existing model config with optional parameter changes"""
        # Get source model
        query = text("""
            SELECT tag_name, model_type, hyperparameters
            FROM model_registry
            WHERE model_id = :model_id
        """)

        result = await self.session.execute(query, {"model_id": source_model_id})
        row = result.fetchone()

        if not row:
            raise ValueError(f"Model {source_model_id} not found")

        # Use provided hyperparameters or copy from source
        new_hyperparameters = hyperparameters or dict(row[2] or {})

        # Create new model
        return await self.create_model_config(
            tag_name=row[0],
            model_type=row[1],
            version=new_version,
            hyperparameters=new_hyperparameters
        )

    async def validate_config(
        self,
        model_type: str,
        hyperparameters: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """Validate hyperparameters against schema"""
        schema = await self.get_model_schema(model_type)
        errors = []

        for param, value in hyperparameters.items():
            if param not in schema:
                errors.append(f"Unknown parameter: {param}")
                continue

            param_schema = schema[param]
            param_type = param_schema["type"]

            # Type validation
            if param_type == "integer" and not isinstance(value, int):
                errors.append(f"{param}: must be integer, got {type(value).__name__}")
            elif param_type == "float" and not isinstance(value, (int, float)):
                errors.append(f"{param}: must be float, got {type(value).__name__}")
            elif param_type == "boolean" and not isinstance(value, bool):
                errors.append(f"{param}: must be boolean, got {type(value).__name__}")

            # Range validation
            if "min" in param_schema and value < param_schema["min"]:
                errors.append(f"{param}: must be >= {param_schema['min']}, got {value}")
            if "max" in param_schema and value > param_schema["max"]:
                errors.append(f"{param}: must be <= {param_schema['max']}, got {value}")

            # Options validation
            if "options" in param_schema and value not in param_schema["options"]:
                errors.append(f"{param}: must be one of {param_schema['options']}, got {value}")

        return len(errors) == 0, errors


# Example usage
async def example_usage():
    """Example usage of ModelConfigService"""
    from ksys_app.db_orm import get_async_session

    async with get_async_session() as session:
        service = ModelConfigService(session)

        # 1. Get default config for AutoARIMA
        default_config = await service.get_default_config("auto_arima")
        print("Default AutoARIMA config:", default_config)

        # 2. Get schema (for UI rendering)
        schema = await service.get_model_schema("auto_arima")
        print("AutoARIMA schema:", schema)

        # 3. Create new model config
        model_id = await service.create_model_config(
            tag_name="INLET_PRESSURE",
            model_type="auto_arima",
            version="v2.0",
            hyperparameters={
                "seasonal": True,
                "m": 144,
                "max_p": 5,
                "max_d": 2,
                "max_q": 5,
                "stepwise": True
            }
        )
        print(f"Created model: {model_id}")

        # 4. Update existing model config
        success = await service.save_model_config(
            model_id=model_id,
            hyperparameters={
                "seasonal": False,
                "m": 72,
                "max_p": 3
            }
        )
        print(f"Updated: {success}")

        # 5. List all configs for a tag
        configs = await service.list_model_configs(tag_name="INLET_PRESSURE")
        print(f"Found {len(configs)} configs")

        # 6. Validate config
        is_valid, errors = await service.validate_config(
            "auto_arima",
            {"seasonal": "yes"}  # Invalid: should be boolean
        )
        print(f"Valid: {is_valid}, Errors: {errors}")
