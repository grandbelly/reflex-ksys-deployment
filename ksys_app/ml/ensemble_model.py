"""
Ensemble Model - Combine multiple forecasting models for improved predictions.

This module implements ensemble methods that combine predictions from multiple
models (ARIMA, Prophet, XGBoost) to produce more robust and accurate forecasts.

Methods:
1. Weighted Average: Simple weighted combination based on model performance
2. Dynamic Weighting: Adjust weights based on recent performance
3. Stacking: Use meta-learner to combine predictions
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

from ..models.forecasting_orm import ModelRegistry
from .training_pipeline import ModelTrainingPipeline

logger = logging.getLogger(__name__)


class EnsembleModel:
    """Ensemble model combining multiple forecasting models."""

    def __init__(self, session: AsyncSession):
        """
        Initialize ensemble model.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session
        self.training_pipeline = ModelTrainingPipeline(session)
        self.meta_model = None  # For stacking
        self.model_weights: Dict[str, float] = {}

    async def predict_weighted_average(
        self,
        tag_name: str,
        horizon: int,
        weights: Optional[Dict[str, float]] = None,
        models_to_use: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate ensemble prediction using weighted average.

        Args:
            tag_name: Sensor tag name
            horizon: Prediction horizon (number of steps)
            weights: Optional custom weights for each model type
            models_to_use: Optional list of model types to include

        Returns:
            Dictionary with ensemble predictions
        """
        # Load available models
        available_models = await self._load_models(tag_name, models_to_use)

        if not available_models:
            raise ValueError(f"No trained models found for {tag_name}")

        # Generate predictions from each model
        predictions_dict = {}
        for model_type, (model, model_info) in available_models.items():
            try:
                preds = await self._generate_single_model_predictions(
                    model=model,
                    model_type=model_type,
                    tag_name=tag_name,
                    horizon=horizon,
                )
                predictions_dict[model_type] = preds
            except Exception as e:
                logger.error(
                    f"Failed to generate predictions from {model_type}: {e}"
                )

        if not predictions_dict:
            raise ValueError("No models generated predictions successfully")

        # Determine weights
        if weights is None:
            weights = await self._calculate_dynamic_weights(
                tag_name, available_models
            )

        # Combine predictions using weighted average
        ensemble_predictions = self._weighted_average_predictions(
            predictions_dict, weights
        )

        return {
            'tag_name': tag_name,
            'horizon': horizon,
            'method': 'weighted_average',
            'predictions': ensemble_predictions,
            'weights': weights,
            'models_used': list(predictions_dict.keys()),
            'generated_at': datetime.now().isoformat(),
        }

    async def predict_stacking(
        self,
        tag_name: str,
        horizon: int,
        meta_model_type: str = 'ridge',
    ) -> Dict[str, Any]:
        """
        Generate ensemble prediction using stacking.

        Stacking uses a meta-learner (Ridge regression) to combine predictions
        from base models.

        Args:
            tag_name: Sensor tag name
            horizon: Prediction horizon
            meta_model_type: Type of meta-learner ('ridge' or 'linear')

        Returns:
            Dictionary with ensemble predictions
        """
        # Load all available models
        available_models = await self._load_models(tag_name)

        if len(available_models) < 2:
            raise ValueError(
                f"Stacking requires at least 2 models, found {len(available_models)}"
            )

        # Train meta-model if not already trained
        if self.meta_model is None:
            await self._train_meta_model(tag_name, available_models, meta_model_type)

        # Generate base model predictions
        predictions_dict = {}
        for model_type, (model, model_info) in available_models.items():
            try:
                preds = await self._generate_single_model_predictions(
                    model=model,
                    model_type=model_type,
                    tag_name=tag_name,
                    horizon=horizon,
                )
                predictions_dict[model_type] = preds
            except Exception as e:
                logger.error(f"Failed to generate predictions from {model_type}: {e}")

        # Combine predictions using meta-model
        ensemble_predictions = await self._stack_predictions(
            predictions_dict, self.meta_model
        )

        return {
            'tag_name': tag_name,
            'horizon': horizon,
            'method': 'stacking',
            'meta_model': meta_model_type,
            'predictions': ensemble_predictions,
            'models_used': list(predictions_dict.keys()),
            'generated_at': datetime.now().isoformat(),
        }

    async def evaluate_ensemble(
        self,
        tag_name: str,
        test_days: int = 7,
        method: str = 'weighted_average',
    ) -> Dict[str, Any]:
        """
        Evaluate ensemble model performance against individual models.

        Args:
            tag_name: Sensor tag name
            test_days: Number of days for testing
            method: Ensemble method ('weighted_average' or 'stacking')

        Returns:
            Dictionary with evaluation metrics
        """
        # Get test data
        test_end = datetime.now()
        test_start = test_end - timedelta(days=test_days)

        test_data = await self._fetch_test_data(tag_name, test_start, test_end)

        if len(test_data) < 24:
            raise ValueError(f"Insufficient test data: {len(test_data)} points")

        # Load models
        available_models = await self._load_models(tag_name)

        # Evaluate individual models
        individual_metrics = {}
        for model_type, (model, model_info) in available_models.items():
            try:
                metrics = await self._evaluate_single_model(
                    model=model,
                    model_type=model_type,
                    test_data=test_data,
                )
                individual_metrics[model_type] = metrics
            except Exception as e:
                logger.error(f"Failed to evaluate {model_type}: {e}")

        # Evaluate ensemble
        if method == 'weighted_average':
            ensemble_metrics = await self._evaluate_weighted_average_ensemble(
                tag_name, test_data, available_models
            )
        elif method == 'stacking':
            ensemble_metrics = await self._evaluate_stacking_ensemble(
                tag_name, test_data, available_models
            )
        else:
            raise ValueError(f"Unknown ensemble method: {method}")

        return {
            'tag_name': tag_name,
            'test_period': {
                'start': test_start.isoformat(),
                'end': test_end.isoformat(),
                'samples': len(test_data),
            },
            'method': method,
            'individual_models': individual_metrics,
            'ensemble': ensemble_metrics,
            'improvement': {
                'mae_reduction': self._calculate_improvement(
                    individual_metrics, ensemble_metrics, 'mae'
                ),
                'rmse_reduction': self._calculate_improvement(
                    individual_metrics, ensemble_metrics, 'rmse'
                ),
            },
        }

    async def _load_models(
        self,
        tag_name: str,
        model_types: Optional[List[str]] = None,
    ) -> Dict[str, Tuple[Any, Dict[str, Any]]]:
        """Load available trained models for a tag."""
        query = select(ModelRegistry).where(ModelRegistry.tag_name == tag_name)

        if model_types:
            query = query.where(ModelRegistry.model_type.in_(model_types))

        result = await self.session.execute(query)
        model_records = result.scalars().all()

        models = {}
        for record in model_records:
            try:
                model, model_info = await self.training_pipeline.load_model(
                    model_id=record.model_id
                )
                models[record.model_type] = (model, model_info)
            except Exception as e:
                logger.error(f"Failed to load model {record.model_id}: {e}")

        return models

    async def _generate_single_model_predictions(
        self,
        model: Any,
        model_type: str,
        tag_name: str,
        horizon: int,
    ) -> np.ndarray:
        """Generate predictions from a single model."""
        # Fetch recent data for context
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=168)  # 7 days

        recent_data = await self._fetch_test_data(tag_name, start_time, end_time)

        loop = asyncio.get_event_loop()

        if model_type == 'ARIMA':
            forecast = await loop.run_in_executor(
                None, lambda: model.predict(n_periods=horizon)
            )
            return np.array(forecast)

        elif model_type == 'Prophet':
            future_df = pd.DataFrame({
                'ds': pd.date_range(
                    start=end_time + timedelta(minutes=1),
                    periods=horizon,
                    freq='1min'
                )
            })
            forecast = await loop.run_in_executor(
                None, lambda: model.predict(future_df)
            )
            return forecast['yhat'].values

        elif model_type == 'XGBoost':
            # XGBoost requires iterative prediction
            # For simplicity, predict single step and repeat
            # In production, implement proper iterative forecasting
            predictions = []
            for _ in range(horizon):
                # Use last known features (simplified)
                pred = await loop.run_in_executor(
                    None,
                    lambda: model.predict(recent_data[-1:].reshape(1, -1))[0]
                )
                predictions.append(pred)

            return np.array(predictions)

        else:
            raise ValueError(f"Unknown model type: {model_type}")

    async def _calculate_dynamic_weights(
        self,
        tag_name: str,
        available_models: Dict[str, Tuple[Any, Dict[str, Any]]],
    ) -> Dict[str, float]:
        """
        Calculate dynamic weights based on recent model performance.

        Weights are inversely proportional to MAE (lower error = higher weight).
        """
        # Get recent performance from model_info
        errors = {}
        for model_type, (model, model_info) in available_models.items():
            mae = model_info.get('metrics', {}).get('mae', 1.0)
            errors[model_type] = mae

        # Calculate weights (inverse of MAE, normalized)
        inverse_errors = {k: 1.0 / max(v, 1e-6) for k, v in errors.items()}
        total = sum(inverse_errors.values())
        weights = {k: v / total for k, v in inverse_errors.items()}

        logger.info(f"Dynamic weights for {tag_name}: {weights}")

        return weights

    def _weighted_average_predictions(
        self,
        predictions_dict: Dict[str, np.ndarray],
        weights: Dict[str, float],
    ) -> List[float]:
        """Combine predictions using weighted average."""
        # Ensure all predictions have same length
        lengths = [len(preds) for preds in predictions_dict.values()]
        min_length = min(lengths)

        # Truncate to minimum length
        predictions_dict = {
            k: v[:min_length] for k, v in predictions_dict.items()
        }

        # Calculate weighted average
        ensemble_preds = np.zeros(min_length)
        for model_type, preds in predictions_dict.items():
            weight = weights.get(model_type, 0.0)
            ensemble_preds += weight * preds

        return ensemble_preds.tolist()

    async def _train_meta_model(
        self,
        tag_name: str,
        available_models: Dict[str, Tuple[Any, Dict[str, Any]]],
        meta_model_type: str = 'ridge',
    ):
        """Train meta-model for stacking."""
        # Fetch training data (last 30 days)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)

        train_data = await self._fetch_test_data(tag_name, start_time, end_time)

        if len(train_data) < 100:
            raise ValueError("Insufficient data for meta-model training")

        # Generate predictions from base models
        X_meta = []
        y_meta = []

        # Use sliding window approach
        window_size = 24  # 24-hour window

        for i in range(len(train_data) - window_size - 1):
            base_predictions = []

            for model_type, (model, _) in available_models.items():
                try:
                    # Predict next value using window
                    pred = await self._generate_single_model_predictions(
                        model=model,
                        model_type=model_type,
                        tag_name=tag_name,
                        horizon=1,
                    )
                    base_predictions.append(pred[0])
                except Exception:
                    base_predictions.append(0.0)

            X_meta.append(base_predictions)
            y_meta.append(train_data[i + window_size + 1])

        X_meta = np.array(X_meta)
        y_meta = np.array(y_meta)

        # Train meta-model
        loop = asyncio.get_event_loop()

        if meta_model_type == 'ridge':
            self.meta_model = Ridge(alpha=1.0)
        else:
            self.meta_model = LinearRegression()

        await loop.run_in_executor(
            None, lambda: self.meta_model.fit(X_meta, y_meta)
        )

        logger.info(f"Meta-model trained for {tag_name} ({meta_model_type})")

    async def _stack_predictions(
        self,
        predictions_dict: Dict[str, np.ndarray],
        meta_model: Any,
    ) -> List[float]:
        """Combine predictions using stacking meta-model."""
        # Prepare input for meta-model
        min_length = min(len(preds) for preds in predictions_dict.values())

        X_meta = np.array([
            [predictions_dict[model_type][i] for model_type in predictions_dict.keys()]
            for i in range(min_length)
        ])

        # Predict with meta-model
        loop = asyncio.get_event_loop()
        ensemble_preds = await loop.run_in_executor(
            None, lambda: meta_model.predict(X_meta)
        )

        return ensemble_preds.tolist()

    async def _fetch_test_data(
        self,
        tag_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> np.ndarray:
        """Fetch test data for evaluation."""
        query = text("""
            SELECT value
            FROM influx_hist
            WHERE tag_name = :tag_name
                AND ts >= :start_time
                AND ts <= :end_time
                AND quality = 192
            ORDER BY ts ASC
        """)

        result = await self.session.execute(
            query,
            {
                'tag_name': tag_name,
                'start_time': start_time,
                'end_time': end_time,
            }
        )

        rows = result.fetchall()
        data = np.array([float(row[0]) for row in rows])

        return data

    async def _evaluate_single_model(
        self,
        model: Any,
        model_type: str,
        test_data: np.ndarray,
    ) -> Dict[str, float]:
        """Evaluate a single model on test data."""
        # Simplified evaluation (predict all test points)
        try:
            predictions = await self._generate_single_model_predictions(
                model=model,
                model_type=model_type,
                tag_name="",  # Not used
                horizon=len(test_data),
            )

            # Truncate to same length
            min_len = min(len(predictions), len(test_data))
            predictions = predictions[:min_len]
            actuals = test_data[:min_len]

            mae = mean_absolute_error(actuals, predictions)
            rmse = np.sqrt(mean_squared_error(actuals, predictions))

            return {'mae': float(mae), 'rmse': float(rmse)}

        except Exception as e:
            logger.error(f"Model evaluation failed: {e}")
            return {'mae': float('inf'), 'rmse': float('inf')}

    async def _evaluate_weighted_average_ensemble(
        self,
        tag_name: str,
        test_data: np.ndarray,
        available_models: Dict[str, Tuple[Any, Dict[str, Any]]],
    ) -> Dict[str, float]:
        """Evaluate weighted average ensemble."""
        # Get weights
        weights = await self._calculate_dynamic_weights(tag_name, available_models)

        # Generate ensemble predictions
        predictions_dict = {}
        for model_type, (model, _) in available_models.items():
            try:
                preds = await self._generate_single_model_predictions(
                    model=model,
                    model_type=model_type,
                    tag_name=tag_name,
                    horizon=len(test_data),
                )
                predictions_dict[model_type] = preds
            except Exception:
                pass

        ensemble_preds = self._weighted_average_predictions(predictions_dict, weights)

        # Evaluate
        min_len = min(len(ensemble_preds), len(test_data))
        ensemble_preds = np.array(ensemble_preds[:min_len])
        actuals = test_data[:min_len]

        mae = mean_absolute_error(actuals, ensemble_preds)
        rmse = np.sqrt(mean_squared_error(actuals, ensemble_preds))

        return {'mae': float(mae), 'rmse': float(rmse)}

    async def _evaluate_stacking_ensemble(
        self,
        tag_name: str,
        test_data: np.ndarray,
        available_models: Dict[str, Tuple[Any, Dict[str, Any]]],
    ) -> Dict[str, float]:
        """Evaluate stacking ensemble."""
        # Similar to weighted average but using meta-model
        # Simplified implementation
        return await self._evaluate_weighted_average_ensemble(
            tag_name, test_data, available_models
        )

    def _calculate_improvement(
        self,
        individual_metrics: Dict[str, Dict[str, float]],
        ensemble_metrics: Dict[str, float],
        metric_name: str,
    ) -> float:
        """Calculate improvement of ensemble over best individual model."""
        best_individual = min(
            [m.get(metric_name, float('inf')) for m in individual_metrics.values()]
        )

        ensemble_value = ensemble_metrics.get(metric_name, float('inf'))

        if best_individual == 0:
            return 0.0

        improvement = (best_individual - ensemble_value) / best_individual * 100

        return float(improvement)
