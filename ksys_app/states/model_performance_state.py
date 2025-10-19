"""Model Performance State - Track and visualize model performance metrics."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

import reflex as rx

from ..db_orm import get_async_session
from .model_recommendation import ModelRecommender

logger = logging.getLogger(__name__)


class ModelPerformanceState(rx.State):
    """State management for model performance dashboard."""

    # Sensor selection
    available_sensors: List[str] = []
    selected_sensor: str = ""

    # Time range selection
    time_range: str = "7d"  # '7d', '30d', '90d'

    # Model selection
    selected_model_type: str = "all"  # 'all', 'ARIMA', 'Prophet', 'XGBoost'

    # Performance data
    performance_history: List[Dict[str, Any]] = []
    drift_history: List[Dict[str, Any]] = []
    model_comparison: List[Dict[str, Any]] = []

    # Summary statistics
    current_models: List[Dict[str, Any]] = []
    total_predictions: int = 0
    avg_mae: float = 0.0
    drift_count: int = 0

    # UI state
    is_loading: bool = False
    error_message: str = ""
    last_update: str = ""

    @rx.event
    async def on_mount(self):
        """Initialize when page loads."""
        return ModelPerformanceState.load_available_sensors

    @rx.event(background=True)
    async def load_available_sensors(self):
        """Load list of sensors that have saved models."""
        try:
            async with get_async_session() as session:
                from sqlalchemy import select, distinct
                from ..models.forecasting_orm import ModelRegistry

                # Get only sensors that have saved models
                query = select(distinct(ModelRegistry.tag_name)).where(
                    ModelRegistry.is_active == True,
                    ModelRegistry.tag_name.isnot(None),
                    ModelRegistry.tag_name != ""
                ).order_by(ModelRegistry.tag_name)
                result = await session.execute(query)
                sensors = [row[0] for row in result.all() if row[0]]  # Filter out empty strings

            async with self:
                self.available_sensors = sensors
                # Auto-select first sensor if available
                if sensors:
                    self.selected_sensor = sensors[0]

            # Load models for selected sensor
            if sensors:
                yield ModelPerformanceState.load_all_saved_models

        except Exception as e:
            logger.error(f"Failed to load sensors: {e}", exc_info=True)
            async with self:
                self.error_message = f"센서 로드 실패: {str(e)}"

    @rx.event(background=True)
    async def load_performance_data(self):
        """Load all performance data for selected sensor."""
        async with self:
            self.is_loading = True
            self.error_message = ""

        try:
            async with get_async_session() as session:
                # Load model registry data
                models = await self._load_model_history(session)

                # Load drift history
                drift = await self._load_drift_history(session)

                # Calculate comparison metrics
                comparison = await self._calculate_model_comparison(session)

                # Get current models
                current = await self._get_current_models(session)

                # Calculate summary stats
                total_preds, avg_mae_val, drift_cnt = await self._calculate_summary(
                    session
                )

            async with self:
                self.performance_history = models
                self.drift_history = drift
                self.model_comparison = comparison
                self.current_models = current
                self.total_predictions = total_preds
                self.avg_mae = avg_mae_val
                self.drift_count = drift_cnt
                self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.is_loading = False

        except Exception as e:
            logger.error(f"Failed to load performance data: {e}", exc_info=True)
            async with self:
                self.error_message = f"데이터 로드 실패: {str(e)}"
                self.is_loading = False

    async def _load_model_history(self, session) -> List[Dict[str, Any]]:
        """Load model training history."""
        from sqlalchemy import select
        from ..models.forecasting_orm import ModelRegistry

        # Calculate date range
        days_map = {'7d': 7, '30d': 30, '90d': 90}
        days = days_map.get(self.time_range, 7)
        start_date = datetime.now() - timedelta(days=days)

        query = select(ModelRegistry).where(
            ModelRegistry.tag_name == self.selected_sensor,
            ModelRegistry.created_at >= start_date,
        )

        if self.selected_model_type != "all":
            query = query.where(ModelRegistry.model_type == self.selected_model_type)

        query = query.order_by(ModelRegistry.created_at.desc())

        result = await session.execute(query)
        records = result.scalars().all()

        return [
            {
                'model_id': rec.model_id,
                'model_type': rec.model_type,
                'version': rec.version,
                'train_mae': float(rec.train_mae) if rec.train_mae else None,
                'validation_mae': float(rec.validation_mae) if rec.validation_mae else None,
                'train_rmse': float(rec.train_rmse) if rec.train_rmse else None,
                'validation_rmse': float(rec.validation_rmse) if rec.validation_rmse else None,
                'train_mape': float(rec.train_mape) if rec.train_mape else None,
                'validation_mape': float(rec.validation_mape) if rec.validation_mape else None,
                'pipeline_config': rec.pipeline_config if rec.pipeline_config else {},
                'created_at': rec.created_at.isoformat() if rec.created_at else None,
            }
            for rec in records
        ]

    async def _load_drift_history(self, session) -> List[Dict[str, Any]]:
        """Load drift detection history."""
        from sqlalchemy import select
        from ..models.forecasting_orm import DriftMonitoring

        days_map = {'7d': 7, '30d': 30, '90d': 90}
        days = days_map.get(self.time_range, 7)
        start_date = datetime.now() - timedelta(days=days)

        query = select(DriftMonitoring).where(
            DriftMonitoring.tag_name == self.selected_sensor,
            DriftMonitoring.monitoring_time >= start_date,
        ).order_by(DriftMonitoring.monitoring_time.desc())

        result = await session.execute(query)
        records = result.scalars().all()

        return [
            {
                'drift_type': rec.drift_type,
                'psi_value': float(rec.psi_score) if rec.psi_score else None,
                'ks_pvalue': float(rec.ks_pvalue) if rec.ks_pvalue else None,
                'severity': rec.drift_severity,
                'detected_at': rec.monitoring_time.isoformat() if rec.monitoring_time else None,
            }
            for rec in records
        ]

    async def _calculate_model_comparison(self, session) -> List[Dict[str, Any]]:
        """Compare performance across model types."""
        from sqlalchemy import select, func
        from ..models.forecasting_orm import ModelRegistry

        query = select(
            ModelRegistry.model_type,
            func.avg(ModelRegistry.validation_mae).label('avg_mae'),
            func.avg(ModelRegistry.validation_rmse).label('avg_rmse'),
            func.count(ModelRegistry.model_id).label('count'),
        ).where(
            ModelRegistry.tag_name == self.selected_sensor
        ).group_by(
            ModelRegistry.model_type
        )

        result = await session.execute(query)
        rows = result.all()

        return [
            {
                'model_type': row[0],
                'avg_mae': float(row[1]) if row[1] else 0.0,
                'avg_rmse': float(row[2]) if row[2] else 0.0,
                'count': int(row[3]),
            }
            for row in rows
        ]

    async def _get_current_models(self, session) -> List[Dict[str, Any]]:
        """Get currently active models."""
        from sqlalchemy import select
        from ..models.forecasting_orm import ModelRegistry

        # Get latest model for each type
        model_types = ['ARIMA', 'Prophet', 'XGBoost']
        models = []

        for model_type in model_types:
            query = select(ModelRegistry).where(
                ModelRegistry.tag_name == self.selected_sensor,
                ModelRegistry.model_type == model_type,
            ).order_by(ModelRegistry.created_at.desc()).limit(1)

            result = await session.execute(query)
            rec = result.scalars().first()

            if rec:
                models.append({
                    'model_type': rec.model_type,
                    'version': rec.version,
                    'validation_mae': float(rec.validation_mae) if rec.validation_mae else None,
                    'validation_rmse': float(rec.validation_rmse) if rec.validation_rmse else None,
                    'trained_at': rec.created_at.isoformat() if rec.created_at else None,
                })

        return models

    async def _calculate_summary(self, session) -> tuple:
        """Calculate summary statistics."""
        from sqlalchemy import select, func
        from ..models.forecasting_orm import ModelRegistry, DriftMonitoring

        # Total predictions (approximate from model count)
        query1 = select(func.count(ModelRegistry.model_id)).where(
            ModelRegistry.tag_name == self.selected_sensor
        )
        result1 = await session.execute(query1)
        total_preds = result1.scalar() or 0

        # Average MAE
        query2 = select(func.avg(ModelRegistry.validation_mae)).where(
            ModelRegistry.tag_name == self.selected_sensor
        )
        result2 = await session.execute(query2)
        avg_mae_val = float(result2.scalar() or 0.0)

        # Drift count
        query3 = select(func.count(DriftMonitoring.drift_id)).where(
            DriftMonitoring.tag_name == self.selected_sensor,
            DriftMonitoring.drift_severity.in_(['high', 'critical'])
        )
        result3 = await session.execute(query3)
        drift_cnt = result3.scalar() or 0

        return total_preds, avg_mae_val, drift_cnt

    @rx.event
    def set_selected_sensor(self, sensor: str):
        """Update selected sensor and reload data."""
        self.selected_sensor = sensor
        return [
            ModelPerformanceState.load_all_saved_models,
            ModelPerformanceState.load_performance_data
        ]

    @rx.event
    def set_time_range(self, time_range: str | list[str]):
        """Update time range and reload data."""
        # segmented_control can pass str or list[str]
        self.time_range = time_range if isinstance(time_range, str) else time_range[0]
        return ModelPerformanceState.load_performance_data

    @rx.event
    def set_model_type(self, model_type: str | list[str]):
        """Update model type filter and reload data."""
        # segmented_control can pass str or list[str]
        self.selected_model_type = model_type if isinstance(model_type, str) else model_type[0]
        return ModelPerformanceState.load_performance_data

    @rx.event
    def refresh_data(self):
        """Refresh performance data."""
        return [
            ModelPerformanceState.load_all_saved_models,
            ModelPerformanceState.load_performance_data
        ]

    @rx.var
    def time_range_label(self) -> str:
        """Get human-readable time range label."""
        labels = {
            '7d': '최근 7일',
            '30d': '최근 30일',
            '90d': '최근 90일',
        }
        return labels.get(self.time_range, self.time_range)

    @rx.var
    def has_data(self) -> bool:
        """Check if any data is available."""
        return len(self.performance_history) > 0

    @rx.var
    def chart_data(self) -> List[Dict[str, Any]]:
        """Prepare data for performance chart."""
        # Group by date and calculate daily averages
        from collections import defaultdict

        daily_metrics = defaultdict(lambda: {'mae': [], 'rmse': [], 'mape': []})

        for record in self.performance_history:
            if record.get('created_at'):
                date = record['created_at'][:10]  # YYYY-MM-DD
                if record.get('mae'):
                    daily_metrics[date]['mae'].append(record['mae'])
                if record.get('rmse'):
                    daily_metrics[date]['rmse'].append(record['rmse'])
                if record.get('mape'):
                    daily_metrics[date]['mape'].append(record['mape'])

        # Calculate averages
        chart_points = []
        for date in sorted(daily_metrics.keys()):
            metrics = daily_metrics[date]
            chart_points.append({
                'date': date,
                'mae': sum(metrics['mae']) / len(metrics['mae']) if metrics['mae'] else None,
                'rmse': sum(metrics['rmse']) / len(metrics['rmse']) if metrics['rmse'] else None,
                'mape': sum(metrics['mape']) / len(metrics['mape']) if metrics['mape'] else None,
            })

        return chart_points

    @rx.var
    def needs_retraining(self) -> bool:
        """Check if model needs retraining."""
        # Simple heuristic: high drift count or degrading performance
        if self.drift_count > 3:
            return True

        if len(self.performance_history) >= 2:
            latest = self.performance_history[0]
            previous = self.performance_history[1]

            # Check if MAE increased by more than 20%
            if latest.get('mae') and previous.get('mae'):
                if latest['mae'] > previous['mae'] * 1.2:
                    return True

        return False

    @rx.var
    def best_model_type(self) -> str:
        """Get best performing model type."""
        if not self.model_comparison:
            return "N/A"

        best = min(self.model_comparison, key=lambda x: x.get('avg_mae', float('inf')))
        return best.get('model_type', 'N/A')

    # ============================================================
    # Model Deployment Methods
    # ============================================================

    saved_models: List[Dict[str, Any]] = []  # All saved models for comparison
    selected_model_id: int = 0  # Currently selected model for actions

    @rx.event(background=True)
    async def load_all_saved_models(self):
        """Load latest model per type (avoid duplicates) + deployed models."""
        try:
            async with get_async_session() as session:
                from sqlalchemy import select
                from ..models.forecasting_orm import ModelRegistry

                # Get all models sorted by created_at desc
                query = select(ModelRegistry).where(
                    ModelRegistry.tag_name == self.selected_sensor,
                    ModelRegistry.is_active == True
                ).order_by(ModelRegistry.created_at.desc())

                result = await session.execute(query)
                all_records = result.scalars().all()

                # Keep only latest per model_type + all deployed models
                seen_types = set()
                records = []

                for rec in all_records:
                    # Always include deployed models
                    if rec.is_deployed:
                        records.append(rec)
                        seen_types.add(rec.model_type)
                    # For non-deployed, keep only first (latest) of each type
                    elif rec.model_type not in seen_types:
                        records.append(rec)
                        seen_types.add(rec.model_type)

                models_list = []
                for rec in records:
                    # Parse hyperparameters to get preprocessing info
                    import json
                    hyperparams = {}
                    if rec.hyperparameters:
                        if isinstance(rec.hyperparameters, str):
                            try:
                                hyperparams = json.loads(rec.hyperparameters)
                            except:
                                hyperparams = {}
                        elif isinstance(rec.hyperparameters, dict):
                            hyperparams = rec.hyperparameters

                    # Parse pipeline_config to get model-specific parameters
                    pipeline_config = {}
                    if rec.pipeline_config:
                        if isinstance(rec.pipeline_config, str):
                            try:
                                pipeline_config = json.loads(rec.pipeline_config)
                            except:
                                pipeline_config = {}
                        elif isinstance(rec.pipeline_config, dict):
                            pipeline_config = rec.pipeline_config

                    # Extract forecast config
                    forecast_config = pipeline_config.get('forecast_config', {})

                    # Extract training info
                    training_info = pipeline_config.get('training_info', {})

                    # Get model-specific parameters
                    # For forecast_horizon, use forecast_config first, then hyperparams
                    forecast_horizon_hours = forecast_config.get('forecast_horizon_hours')
                    if forecast_horizon_hours is None:
                        forecast_horizon_hours = hyperparams.get('forecast_horizon', 24)

                    # Flatten hyperparameters for easy access in components
                    models_list.append({
                        'model_id': rec.model_id,
                        'model_name': rec.model_name,
                        'model_type': rec.model_type,
                        'version': rec.version,
                        'train_mae': float(rec.train_mae) if rec.train_mae else None,
                        'train_rmse': float(rec.train_rmse) if rec.train_rmse else None,
                        'train_mape': float(rec.train_mape) if rec.train_mape else None,
                        'validation_mae': float(rec.validation_mae) if rec.validation_mae else None,
                        'validation_rmse': float(rec.validation_rmse) if rec.validation_rmse else None,
                        'validation_mape': float(rec.validation_mape) if rec.validation_mape else None,
                        'training_duration': float(rec.training_duration_seconds) if rec.training_duration_seconds else None,
                        'training_samples': int(rec.training_samples) if rec.training_samples else None,
                        'model_size': int(rec.model_size_bytes) if rec.model_size_bytes else None,
                        'created_at': rec.created_at.isoformat() if rec.created_at else None,
                        'is_deployed': rec.is_deployed,
                        'deployed_at': rec.deployed_at.isoformat() if rec.deployed_at else None,
                        'pipeline_config': rec.pipeline_config if rec.pipeline_config else {},
                        # Flatten hyperparameters for component access
                        'enable_preprocessing': hyperparams.get('enable_preprocessing', False),
                        'outlier_threshold': float(hyperparams.get('outlier_threshold', 3.0)),
                        'training_days': int(hyperparams.get('training_days', 7)),
                        'forecast_horizon': int(forecast_horizon_hours),  # From forecast_config
                        'season_length': int(hyperparams.get('season_length', 1)),
                        'feature_config_id': hyperparams.get('feature_config_id'),
                        'feature_config_name': hyperparams.get('feature_config_name', ''),
                        'feature_config': rec.feature_config if rec.feature_config else "",
                        # Additional info from pipeline_config
                        'forecast_interval_minutes': forecast_config.get('forecast_interval_minutes', 10),
                        'total_forecast_steps': forecast_config.get('total_steps', 0),
                        'preprocessing_steps': training_info.get('preprocessing_steps', []),
                    })

            async with self:
                self.saved_models = models_list

        except Exception as e:
            logger.error(f"Failed to load saved models: {e}", exc_info=True)
            async with self:
                self.error_message = f"저장된 모델 로드 실패: {str(e)}"

    @rx.event(background=True)
    async def deploy_model(self, model_id: int):
        """Deploy a specific model for real-time forecasting."""
        async with self:
            self.is_loading = True
            self.error_message = ""

        try:
            async with get_async_session() as session:
                from sqlalchemy import select, update
                from ..models.forecasting_orm import ModelRegistry

                # First, undeploy any currently deployed models for this sensor
                undeploy_query = update(ModelRegistry).where(
                    ModelRegistry.tag_name == self.selected_sensor,
                    ModelRegistry.is_deployed == True
                ).values(
                    is_deployed=False,
                    deployed_at=None,
                    deployed_by=None
                )
                await session.execute(undeploy_query)

                # Deploy the selected model
                deploy_query = update(ModelRegistry).where(
                    ModelRegistry.model_id == model_id
                ).values(
                    is_deployed=True,
                    deployed_at=datetime.now(),
                    deployed_by="user"
                )
                await session.execute(deploy_query)
                await session.commit()

                logger.info(f"Model {model_id} deployed for sensor {self.selected_sensor}")

            async with self:
                self.is_loading = False
                self.error_message = ""
                yield

            # Reload data to reflect changes
            yield ModelPerformanceState.load_all_saved_models
            yield ModelPerformanceState.load_performance_data

        except Exception as e:
            logger.error(f"Failed to deploy model: {e}", exc_info=True)
            async with self:
                self.error_message = f"모델 배포 실패: {str(e)}"
                self.is_loading = False

    def set_selected_model_for_deploy(self, model_id: int):
        """Set the selected model and trigger deployment."""
        self.selected_model_id = model_id
        return ModelPerformanceState.deploy_model(model_id)

    def undeploy_current_model(self):
        """Undeploy the currently deployed model."""
        deployed = self.deployed_model_info
        if deployed:
            return ModelPerformanceState.undeploy_model(deployed.get("model_id"))

    @rx.event(background=True)
    async def delete_model(self, model_id: int):
        """Delete a model from the database."""
        async with self:
            self.is_loading = True
            self.error_message = ""

        try:
            async with get_async_session() as session:
                from sqlalchemy import delete
                from ..models.forecasting_orm import ModelRegistry, Prediction

                # Delete predictions first (foreign key constraint)
                delete_preds = delete(Prediction).where(
                    Prediction.model_id == model_id
                )
                await session.execute(delete_preds)

                # Delete model
                delete_model = delete(ModelRegistry).where(
                    ModelRegistry.model_id == model_id
                )
                await session.execute(delete_model)
                await session.commit()

                logger.info(f"Model {model_id} deleted")

            async with self:
                self.is_loading = False
                self.error_message = ""
                yield

            # Reload data to reflect changes
            yield ModelPerformanceState.load_all_saved_models
            yield ModelPerformanceState.load_performance_data

        except Exception as e:
            logger.error(f"Failed to delete model: {e}", exc_info=True)
            async with self:
                self.error_message = f"모델 삭제 실패: {str(e)}"
                self.is_loading = False

    def set_selected_model_for_delete(self, model_id: int):
        """Set the selected model and trigger deletion."""
        self.selected_model_id = model_id
        return ModelPerformanceState.delete_model(model_id)

    @rx.event(background=True)
    async def undeploy_model(self, model_id: int):
        """Undeploy a model (stop real-time forecasting)."""
        async with self:
            self.is_loading = True
            self.error_message = ""

        try:
            async with get_async_session() as session:
                from sqlalchemy import update
                from ..models.forecasting_orm import ModelRegistry

                undeploy_query = update(ModelRegistry).where(
                    ModelRegistry.model_id == model_id
                ).values(
                    is_deployed=False,
                    deployed_at=None,
                    deployed_by=None
                )
                await session.execute(undeploy_query)
                await session.commit()

                logger.info(f"Model {model_id} undeployed")

            async with self:
                self.is_loading = False
                self.error_message = ""
                yield

            yield ModelPerformanceState.load_all_saved_models
            yield ModelPerformanceState.load_performance_data

        except Exception as e:
            logger.error(f"Failed to undeploy model: {e}", exc_info=True)
            async with self:
                self.error_message = f"모델 배포 해제 실패: {str(e)}"
                self.is_loading = False

    @rx.var
    def deployed_model_info(self) -> Dict[str, Any]:
        """Get currently deployed model information."""
        for model in self.saved_models:
            if model.get('is_deployed'):
                return model
        return {}

    @rx.var
    def has_deployed_model(self) -> bool:
        """Check if there is a deployed model."""
        return bool(self.deployed_model_info)

    @rx.var
    def recommended_models(self) -> Dict[str, Dict[str, Any]]:
        """Get recommended models for different scenarios"""
        recommender = ModelRecommender()
        return {
            'accuracy': recommender.get_best_for_accuracy(self.saved_models),
            'speed': recommender.get_best_for_speed(self.saved_models),
            'balanced': recommender.get_balanced(self.saved_models),
        }

    @rx.var
    def model_insights(self) -> Dict[int, str]:
        """Get insights for each model"""
        recommender = ModelRecommender()
        return recommender.get_insights(self.saved_models)

    # ============================================================
    # Algorithm Comparison (Prophet, Auto-ARIMA, XGBoost)
    # ============================================================

    @rx.var
    def algorithm_comparison_data(self) -> List[Dict[str, Any]]:
        """
        Compare the 3 main algorithms: Prophet, Auto-ARIMA, XGBoost.

        Returns list of dicts with:
        - model_name: Algorithm name
        - validation_mape: MAPE from validation
        - validation_points: Number of validation points
        - training_samples: Number of training samples
        - created_at: Training timestamp
        - rank: Performance rank (1 = best)
        """
        # Get latest model for each algorithm type
        algo_models = {}

        for model in self.saved_models:
            model_type = model.get('model_type', '').lower()

            # Map model types to display names
            if 'prophet' in model_type:
                algo_name = 'Prophet'
            elif 'arima' in model_type or 'autoarima' in model_type:
                algo_name = 'Auto-ARIMA'
            elif 'xgboost' in model_type or 'xgb' in model_type:
                algo_name = 'XGBoost'
            else:
                continue  # Skip unknown types

            # Keep only the latest (first in list since sorted by created_at desc)
            # BUT: only if it has validation_mape or validation_data
            if algo_name not in algo_models:
                val_mape = model.get('validation_mape')
                pipeline_config = model.get('pipeline_config', {})

                # Handle both dict and string (JSON text)
                if isinstance(pipeline_config, str):
                    import json
                    try:
                        pipeline_config = json.loads(pipeline_config)
                    except:
                        pipeline_config = {}

                metrics = pipeline_config.get('metrics', {})
                validation_data = metrics.get('validation_data', [])

                # Only include if has validation data
                # 0.0 is a valid value (perfect prediction or constant values)
                if val_mape is not None or len(validation_data) > 0:
                    algo_models[algo_name] = model

        # Build comparison data
        comparison = []
        for algo_name, model in algo_models.items():
            val_mape = model.get('validation_mape', 0.0)
            val_points = self._extract_validation_points(model)
            training_samples = model.get('training_samples', 0)
            created_at = model.get('created_at', '')

            # Extract training period from pipeline_config
            pipeline_config = model.get('pipeline_config', {})

            # Handle both dict and string (JSON text)
            if isinstance(pipeline_config, str):
                import json
                try:
                    pipeline_config = json.loads(pipeline_config)
                except:
                    pipeline_config = {}

            training_info = pipeline_config.get('training_info', {})
            data_start = training_info.get('data_start', '')
            data_end = training_info.get('data_end', '')

            # Extract train_mae and validation_mae
            train_mae = model.get('train_mae')
            val_mae = model.get('validation_mae')

            comparison.append({
                'model_id': model.get('model_id'),  # Add model_id for tracking
                'model_name': algo_name,
                'train_mae': float(train_mae) if train_mae else None,
                'validation_mae': float(val_mae) if val_mae else None,
                'validation_mape': float(val_mape) if val_mape else 0.0,
                'validation_points': int(val_points),
                'training_samples': int(training_samples) if training_samples else 0,
                'created_at': created_at,
                'data_start': data_start,
                'data_end': data_end,
                'rank': 0,  # Will be calculated below
            })

        # Sort by validation_mape first (most reliable metric), then validation_mae
        # Lower is better for both metrics
        # Handle None values by treating them as worst (infinity)
        comparison.sort(key=lambda x: (
            float('inf') if x['validation_mape'] is None else x['validation_mape'],
            float('inf') if x['validation_mae'] is None else x['validation_mae']
        ))
        for i, item in enumerate(comparison, start=1):
            item['rank'] = i

        return comparison

    def _extract_validation_points(self, model: Dict[str, Any]) -> int:
        """
        Extract number of validation points from model's pipeline_config.

        Looks for validation_data in metrics.
        """
        pipeline_config = model.get('pipeline_config', {})

        # Handle both dict and string (JSON text)
        if isinstance(pipeline_config, str):
            import json
            try:
                pipeline_config = json.loads(pipeline_config)
            except:
                pipeline_config = {}

        # Check if metrics contains validation_data
        metrics = pipeline_config.get('metrics', {})
        validation_data = metrics.get('validation_data', [])

        return len(validation_data)

    @rx.var
    def best_algorithm(self) -> str:
        """Get the name of the best performing algorithm."""
        comparison = self.algorithm_comparison_data
        if not comparison:
            return ""

        # Rank 1 is the best
        for algo in comparison:
            if algo.get('rank') == 1:
                return algo.get('model_name', '')

        return ""

    @rx.var
    def best_algorithm_mape(self) -> str:
        """Get MAPE of the best algorithm."""
        comparison = self.algorithm_comparison_data
        if not comparison:
            return "N/A"

        for algo in comparison:
            if algo.get('rank') == 1:
                mape = algo.get('validation_mape', 0.0)
                return f"{mape:.2f}"

        return "N/A"

    @rx.var
    def best_algorithm_points(self) -> str:
        """Get validation points of the best algorithm."""
        comparison = self.algorithm_comparison_data
        if not comparison:
            return "0"

        for algo in comparison:
            if algo.get('rank') == 1:
                points = algo.get('validation_points', 0)
                return str(points)

        return "0"

    @rx.var
    def training_conditions_match(self) -> bool:
        """Check if all 3 algorithms were trained under similar conditions."""
        comparison = self.algorithm_comparison_data
        if len(comparison) < 3:
            return True  # Cannot compare with less than 3

        # Extract training samples
        samples = [algo.get('training_samples', 0) for algo in comparison]

        # Check if all have similar sample counts (within 10% tolerance)
        if any(s == 0 for s in samples):
            return False  # Missing data

        min_samples = min(samples)
        max_samples = max(samples)

        # Allow 10% variance
        if max_samples > min_samples * 1.1:
            return False

        # Check training time difference
        timestamps = []
        for algo in comparison:
            created_at = algo.get('created_at', '')
            if created_at:
                try:
                    from datetime import datetime
                    # Parse ISO format timestamp
                    if 'T' in created_at:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = datetime.fromisoformat(created_at)
                    timestamps.append(dt)
                except:
                    pass

        if len(timestamps) == 3:
            # Check if all trained within 5 minutes of each other
            time_diffs = [
                abs((timestamps[i] - timestamps[j]).total_seconds())
                for i in range(len(timestamps))
                for j in range(i+1, len(timestamps))
            ]
            max_diff = max(time_diffs)
            if max_diff > 300:  # 5 minutes
                return False

        return True

    @rx.var
    def training_condition_warnings(self) -> List[str]:
        """Get list of warnings about training condition mismatches."""
        warnings = []
        comparison = self.algorithm_comparison_data

        if len(comparison) < 3:
            return warnings

        # Check sample count variance
        samples = [algo.get('training_samples', 0) for algo in comparison]
        if any(s == 0 for s in samples):
            warnings.append("⚠️ 훈련 샘플 불일치")
        elif max(samples) > min(samples) * 1.1:
            warnings.append(f"⚠️ 샘플 수: {min(samples)}-{max(samples)}")

        # Check time difference
        timestamps = []
        for algo in comparison:
            created_at = algo.get('created_at', '')
            if created_at:
                try:
                    from datetime import datetime
                    if 'T' in created_at:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = datetime.fromisoformat(created_at)
                    timestamps.append((algo['model_name'], dt))
                except:
                    pass

        if len(timestamps) == 3:
            time_diffs = []
            for i in range(len(timestamps)):
                for j in range(i+1, len(timestamps)):
                    diff_seconds = abs((timestamps[i][1] - timestamps[j][1]).total_seconds())
                    time_diffs.append(diff_seconds)

            max_diff = max(time_diffs)
            if max_diff > 300:  # 5 minutes
                hours = int(max_diff // 3600)
                minutes = int((max_diff % 3600) // 60)
                if hours > 0:
                    warnings.append(f"⚠️ 시간 차이: {hours}h {minutes}m")
                else:
                    warnings.append(f"⚠️ 시간 차이: {minutes}분")

        if not warnings:
            warnings.append("✅ 동일 조건 훈련")

        return warnings

    @rx.var
    def pipeline_display_models(self) -> List[Dict[str, Any]]:
        """Get models to display pipeline cards for (deployed + top 3 by performance)."""
        if not self.saved_models:
            return []

        # Always include deployed model
        deployed = [m for m in self.saved_models if m.get('is_deployed')]

        # Get top 3 non-deployed models by validation_mae (lower is better)
        non_deployed = [m for m in self.saved_models if not m.get('is_deployed')]

        # Sort by validation_mae (None last)
        non_deployed.sort(key=lambda x: (
            float('inf') if x.get('validation_mae') is None else x.get('validation_mae')
        ))

        # Take top 3
        top_3 = non_deployed[:3]

        # Combine deployed + top 3 (remove duplicates by model_id)
        seen_ids = set()
        result = []

        for model in deployed + top_3:
            model_id = model.get('model_id')
            if model_id not in seen_ids:
                result.append(model)
                seen_ids.add(model_id)

        return result

    # ============================================================
    # Navigation Methods
    # ============================================================

    def navigate_to_forecast_player(self):
        """Navigate to Forecast Player with deployed model's sensor."""
        if not self.selected_sensor:
            return rx.window_alert("센서를 먼저 선택하세요.")

        from reflex.utils import console
        console.log(f"Navigating to forecast player with sensor: {self.selected_sensor}")

        # ✅ FIX: Use correct route /forecast-player-fixed
        return rx.redirect(f"/forecast-player-fixed?sensor={self.selected_sensor}")
