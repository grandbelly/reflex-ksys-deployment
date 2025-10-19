"""
Model Training Pipeline for Time-Series Forecasting

Implements training workflows using statsforecast (unified lightweight library):
- AutoARIMA: Automatic ARIMA model selection
- AutoETS: Exponential Smoothing State Space Model
- AutoCES: Complex Exponential Smoothing
- MSTL: Multiple Seasonal-Trend decomposition using LOESS

Benefits of statsforecast:
- High-performance statistical models (faster than pmdarima/prophet)
- Efficient parallel processing for multiple time series
- Simple API with minimal configuration
- Native support for exogenous variables

Includes:
- Walk-forward validation
- Model evaluation metrics (MAE, RMSE, MAPE)
- Model serialization (joblib)
- Model registry integration
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import pytz
import pandas as pd
import numpy as np
import joblib
import logging

# Reflex utilities (import early for console logging)
from reflex.utils import console

# Database
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# ML Libraries - Unified lightweight statsforecast
try:
    from statsforecast import StatsForecast
    from statsforecast.models import AutoARIMA, AutoETS, AutoCES, MSTL
    STATSFORECAST_AVAILABLE = True
    console.info("✅ statsforecast loaded - AutoARIMA, ETS models available")
except ImportError:
    STATSFORECAST_AVAILABLE = False
    console.warn("⚠️ statsforecast not available - forecasting disabled")

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error

# Internal
from ksys_app.db_orm import get_async_session
from ksys_app.services.feature_engineering_service import FeatureEngineeringService


KST = pytz.timezone('Asia/Seoul')


class ModelTrainingPipeline:
    """
    Training pipeline for time-series forecasting models.

    Features:
    - Auto ARIMA with seasonal components
    - Prophet with daily/weekly seasonality
    - XGBoost with engineered features
    - Walk-forward validation
    - Model persistence and versioning
    """

    def __init__(
        self,
        session: AsyncSession,
        model_dir: str = "models/forecasting"
    ):
        """
        Initialize training pipeline.

        Args:
            session: Async database session
            model_dir: Directory to save trained models
        """
        self.session = session
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.feature_service = FeatureEngineeringService(session)

    # ============================================================================
    # Data Preparation
    # ============================================================================

    async def get_training_data(
        self,
        tag_name: str,
        start_time: datetime,
        end_time: datetime,
        include_features: bool = True
    ) -> pd.DataFrame:
        """
        Fetch and prepare training data for a sensor tag.

        Args:
            tag_name: Sensor tag name
            start_time: Start of training period (UTC)
            end_time: End of training period (UTC)
            include_features: Whether to generate engineered features

        Returns:
            DataFrame with timestamp, value, and optional features
        """
        try:
            console.info(f"Fetching training data for {tag_name}: {start_time} to {end_time}")

            # Set query timeout
            await self.session.execute(text("SET LOCAL statement_timeout = '30s'"))

            # Fetch aggregated data (10-minute buckets)
            # 10분 집계 데이터 사용 - 노이즈 감소 및 학습 속도 향상
            query = text("""
                SELECT
                    bucket AT TIME ZONE 'UTC' AS ts,
                    avg AS value
                FROM influx_agg_10m
                WHERE tag_name = :tag_name
                  AND bucket >= :start_time
                  AND bucket <= :end_time
                ORDER BY bucket
            """)

            result = await self.session.execute(query, {
                "tag_name": tag_name,
                "start_time": start_time,
                "end_time": end_time
            })
            rows = result.mappings().all()

            if not rows:
                console.warn(f"No training data found for {tag_name}")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame([dict(row) for row in rows])
            df['ts'] = pd.to_datetime(df['ts'], utc=True)
            df = df.set_index('ts').sort_index()

            console.info(f"Loaded {len(df)} data points (10-min aggregated) for {tag_name}")

            # Generate features if requested
            if include_features:
                features_df = await self.feature_service.generate_all_features(
                    tag_name, start_time, end_time,
                    include_seasonal=False  # Skip seasonal for training data
                )

                if not features_df.empty:
                    features_df['ts'] = pd.to_datetime(features_df['ts'], utc=True)
                    features_df = features_df.set_index('ts')
                    df = df.join(features_df.drop(columns=['value'], errors='ignore'))
                    console.info(f"Added {len(features_df.columns)} features to training data")

            return df.reset_index()

        except Exception as e:
            console.error(f"Error fetching training data for {tag_name}: {e}")
            return pd.DataFrame()

    # ============================================================================
    # ARIMA Model Training (Subtask 33.1)
    # ============================================================================

    async def train_arima(
        self,
        tag_name: str,
        train_data: pd.DataFrame,
        seasonal: bool = True,
        season_length: int = 24,  # Seasonal period (24 hours for daily seasonality)
        **kwargs
    ) -> Tuple[Any, Dict[str, float]]:
        """
        Train AutoARIMA model using statsforecast.

        Args:
            tag_name: Sensor tag name
            train_data: Training DataFrame with 'ts' and 'value' columns
            seasonal: Enable seasonal ARIMA (SARIMA)
            season_length: Seasonal period (default: 24 for hourly data)
            **kwargs: Additional parameters for AutoARIMA

        Returns:
            Tuple of (trained_model, metrics_dict)
        """
        if not STATSFORECAST_AVAILABLE:
            raise ImportError("statsforecast is not installed - ARIMA training unavailable")

        try:
            console.info(f"Training AutoARIMA model for {tag_name}")

            if train_data.empty or 'value' not in train_data.columns:
                raise ValueError(f"Invalid training data for {tag_name}")

            # Prepare data in statsforecast format
            # Required columns: unique_id, ds (datetime), y (value)
            df = train_data.copy()
            df['unique_id'] = tag_name
            df['ds'] = pd.to_datetime(df['ts']) if 'ts' in df.columns else df.index
            df['y'] = df['value']
            df = df[['unique_id', 'ds', 'y']].reset_index(drop=True)

            # Initialize AutoARIMA model
            model = AutoARIMA(season_length=season_length if seasonal else 1)

            # Create StatsForecast instance
            sf = StatsForecast(
                models=[model],
                freq='10min',  # 10-minute frequency (matches influx_agg_10m)
                n_jobs=-1,
            )

            # Train model (run in thread pool)
            loop = asyncio.get_event_loop()
            fitted_models = await loop.run_in_executor(
                None,
                lambda: sf.fit(df)
            )

            # Calculate metrics using fitted values from cross-validation
            # Note: statsforecast doesn't provide fitted values directly
            # We'll use a simple train/test split for metrics
            train_size = int(len(df) * 0.8)
            train_df = df.iloc[:train_size]
            test_df = df.iloc[train_size:]

            # Retrain on training set
            sf_train = StatsForecast(
                models=[AutoARIMA(season_length=season_length if seasonal else 1)],
                freq='10min',  # 10-minute frequency (matches influx_agg_10m)
                n_jobs=-1,
            )
            await loop.run_in_executor(None, lambda: sf_train.fit(train_df))

            # Predict on test set
            h = len(test_df)
            forecast_df = await loop.run_in_executor(
                None,
                lambda: sf_train.predict(h=h)
            )

            # Calculate metrics
            y_true = test_df['y'].values
            y_pred = forecast_df['AutoARIMA'].values

            metrics = self._calculate_metrics(y_true, y_pred)

            console.info(f"AutoARIMA training complete for {tag_name}: MAPE={metrics['mape']:.2f}%")

            return sf, metrics

        except Exception as e:
            console.error(f"Error training AutoARIMA for {tag_name}: {e}")
            raise

    # ============================================================================
    # ETS Model Training (Subtask 33.2) - Replaces Prophet
    # ============================================================================

    async def train_prophet(
        self,
        tag_name: str,
        train_data: pd.DataFrame,
        season_length: int = 24,
        **kwargs
    ) -> Tuple[Any, Dict[str, float]]:
        """
        Train AutoETS (Exponential Smoothing) model using statsforecast.

        ETS is a faster and lighter alternative to Prophet for seasonal time series.

        Args:
            tag_name: Sensor tag name
            train_data: Training DataFrame with 'ts' and 'value' columns
            season_length: Seasonal period (default: 24 for hourly data)
            **kwargs: Additional parameters for AutoETS

        Returns:
            Tuple of (trained_model, metrics_dict)
        """
        if not STATSFORECAST_AVAILABLE:
            raise ImportError("statsforecast is not installed - ETS training unavailable")

        try:
            console.info(f"Training AutoETS model for {tag_name}")

            if train_data.empty or 'value' not in train_data.columns:
                raise ValueError(f"Invalid training data for {tag_name}")

            # Prepare data in statsforecast format
            df = train_data.copy()
            df['unique_id'] = tag_name
            df['ds'] = pd.to_datetime(df['ts']) if 'ts' in df.columns else df.index
            df['y'] = df['value']
            df = df[['unique_id', 'ds', 'y']].reset_index(drop=True)

            # Initialize AutoETS model
            model = AutoETS(season_length=season_length)

            # Create StatsForecast instance
            sf = StatsForecast(
                models=[model],
                freq='10min',  # 10-minute frequency (matches influx_agg_10m)
                n_jobs=-1,
            )

            # Train model (run in thread pool)
            loop = asyncio.get_event_loop()
            fitted_models = await loop.run_in_executor(
                None,
                lambda: sf.fit(df)
            )

            # Calculate metrics using fitted values from cross-validation
            # Note: statsforecast doesn't provide fitted values directly
            # We'll use a simple train/test split for metrics
            train_size = int(len(df) * 0.8)
            train_df = df.iloc[:train_size]
            test_df = df.iloc[train_size:]

            # Retrain on training set
            sf_train = StatsForecast(
                models=[AutoETS(season_length=season_length)],
                freq='10min',  # 10-minute frequency (matches influx_agg_10m)
                n_jobs=-1,
            )
            await loop.run_in_executor(None, lambda: sf_train.fit(train_df))

            # Predict on test set
            h = len(test_df)
            forecast_df = await loop.run_in_executor(
                None,
                lambda: sf_train.predict(h=h)
            )

            # Calculate metrics
            y_true = test_df['y'].values
            y_pred = forecast_df['AutoETS'].values

            metrics = self._calculate_metrics(y_true, y_pred)

            console.info(f"AutoETS training complete for {tag_name}: MAPE={metrics['mape']:.2f}%")

            return sf, metrics

        except Exception as e:
            console.error(f"Error training AutoETS for {tag_name}: {e}")
            raise

    # ============================================================================
    # XGBoost Model Training (Subtask 33.3) - DISABLED (use statsforecast only)
    # ============================================================================

    async def train_xgboost(
        self,
        tag_name: str,
        train_data: pd.DataFrame,
        target_col: str = 'value',
        feature_cols: Optional[List[str]] = None,
        **kwargs
    ) -> Tuple[Any, Dict[str, float]]:
        """
        XGBoost training is DISABLED to keep forecasting lightweight.

        Use statsforecast AutoARIMA or AutoETS instead for better performance
        and simpler deployment.

        Args:
            tag_name: Sensor tag name
            train_data: Training DataFrame with features
            target_col: Target column name
            feature_cols: List of feature columns (auto-detect if None)
            **kwargs: Additional XGBoost parameters

        Returns:
            Tuple of (trained_model, metrics_dict)
        """
        raise NotImplementedError(
            "XGBoost training is disabled. Use train_arima() or train_prophet() (AutoETS) instead."
        )

        try:
            console.info(f"Training XGBoost model for {tag_name}")

            if train_data.empty or target_col not in train_data.columns:
                raise ValueError(f"Invalid training data for {tag_name}")

            # Auto-detect feature columns
            if feature_cols is None:
                exclude_cols = ['ts', 'value', target_col]
                feature_cols = [col for col in train_data.columns if col not in exclude_cols]

            if not feature_cols:
                raise ValueError(f"No features available for XGBoost training on {tag_name}")

            # Prepare features and target
            X = train_data[feature_cols].fillna(0)  # Fill NaN with 0
            y = train_data[target_col].values

            # Default XGBoost parameters
            xgb_params = {
                'objective': 'reg:squarederror',
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 100,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42,
                'n_jobs': -1
            }
            xgb_params.update(kwargs)

            # Train model
            model = xgb.XGBRegressor(**xgb_params)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: model.fit(X, y)
            )

            # In-sample predictions
            y_pred = model.predict(X)
            metrics = self._calculate_metrics(y, y_pred)

            # Add feature importance to metrics
            metrics['feature_importance'] = dict(zip(
                feature_cols,
                model.feature_importances_.tolist()
            ))

            console.info(f"XGBoost training complete for {tag_name}: MAPE={metrics['mape']:.2f}%")

            return model, metrics

        except Exception as e:
            console.error(f"Error training XGBoost for {tag_name}: {e}")
            raise

    # ============================================================================
    # Backtesting with Walk-Forward Validation (Subtask 33.4)
    # ============================================================================

    async def walk_forward_validation(
        self,
        tag_name: str,
        data: pd.DataFrame,
        model_type: str,
        forecast_interval_minutes: int,  # NEW: From user config (e.g., 10 for 10-min data)
        forecast_horizon_hours: int,     # NEW: From user config (e.g., 6 for 6-hour forecast)
        n_splits: int = 5,
        **model_kwargs
    ) -> Dict[str, Any]:
        """
        Perform walk-forward validation for time series.

        Args:
            tag_name: Sensor tag name
            data: Full dataset
            model_type: 'arima', 'prophet', or 'xgboost'
            forecast_interval_minutes: Data interval in minutes (e.g., 10 for 10-min data)
            forecast_horizon_hours: Forecast horizon in hours (e.g., 6 for 6-hour forecast)
            n_splits: Number of train-test splits (walk-forward folds)
            **model_kwargs: Parameters for model training

        Returns:
            Dict with validation results and metrics

        Example:
            With 10-min intervals and 6-hour forecast:
            - forecast_interval_minutes = 10
            - forecast_horizon_hours = 6
            - test_size = (6 * 60) / 10 = 36 periods
        """
        try:
            # Calculate test_size dynamically from user's forecast configuration
            # This ensures validation test period matches the user's expected forecast horizon
            test_size = int((forecast_horizon_hours * 60) / forecast_interval_minutes)

            console.info(f"Walk-forward validation for {tag_name} using {model_type}")
            console.info(f"  - Forecast config: {forecast_interval_minutes}-min intervals, {forecast_horizon_hours}-hour horizon")
            console.info(f"  - Calculated test_size: {test_size} periods (matches user's forecast horizon)")
            console.info(f"  - Number of folds: {n_splits}")

            tscv = TimeSeriesSplit(n_splits=n_splits, test_size=test_size)

            all_metrics = []
            fold_results = []

            for fold, (train_idx, test_idx) in enumerate(tscv.split(data)):
                train_data = data.iloc[train_idx]
                test_data = data.iloc[test_idx]

                console.info(f"Fold {fold+1}/{n_splits}: Train={len(train_data)}, Test={len(test_data)}")

                # Train model
                if model_type == 'arima':
                    model, _ = await self.train_arima(tag_name, train_data, **model_kwargs)
                    y_pred = model.predict(n_periods=len(test_data))
                elif model_type == 'prophet':
                    model, _ = await self.train_prophet(tag_name, train_data, **model_kwargs)
                    future = model.make_future_dataframe(periods=len(test_data), freq='H')
                    forecast = model.predict(future)
                    y_pred = forecast['yhat'].iloc[-len(test_data):].values
                elif model_type == 'xgboost':
                    model, _ = await self.train_xgboost(tag_name, train_data, **model_kwargs)
                    X_test = test_data[[col for col in test_data.columns if col not in ['ts', 'value']]]
                    y_pred = model.predict(X_test.fillna(0))
                else:
                    raise ValueError(f"Unknown model type: {model_type}")

                # Calculate metrics
                y_true = test_data['value'].values
                metrics = self._calculate_metrics(y_true, y_pred)
                all_metrics.append(metrics)

                fold_results.append({
                    'fold': fold + 1,
                    'train_size': len(train_data),
                    'test_size': len(test_data),
                    'metrics': metrics
                })

            # Aggregate metrics
            avg_metrics = {
                'mae': np.mean([m['mae'] for m in all_metrics]),
                'rmse': np.mean([m['rmse'] for m in all_metrics]),
                'mape': np.mean([m['mape'] for m in all_metrics]),
            }

            console.info(f"Walk-forward validation complete: Avg MAPE={avg_metrics['mape']:.2f}%")

            return {
                'tag_name': tag_name,
                'model_type': model_type,
                'n_splits': n_splits,
                'avg_metrics': avg_metrics,
                'fold_results': fold_results
            }

        except Exception as e:
            console.error(f"Error in walk-forward validation for {tag_name}: {e}")
            raise

    # ============================================================================
    # Model Serialization and Registry (Subtask 33.5)
    # ============================================================================

    async def save_model(
        self,
        tag_name: str,
        model: Any,
        model_type: str,
        metrics: Dict[str, float],
        hyperparameters: Optional[Dict[str, Any]] = None,
        version: str = "1.0"
    ) -> int:
        """
        Save trained model to PostgreSQL BYTEA and register in database.

        Args:
            tag_name: Sensor tag name
            model: Trained model object
            model_type: 'arima', 'prophet', or 'xgboost'
            metrics: Training metrics
            hyperparameters: Model hyperparameters
            version: Model version string

        Returns:
            model_id from database
        """
        try:
            # Serialize model to pickle bytes
            import pickle
            loop = asyncio.get_event_loop()
            model_bytes = await loop.run_in_executor(
                None,
                lambda: pickle.dumps(model)
            )

            console.info(f"Model serialized to pickle bytes: {len(model_bytes)} bytes")

            # Register in database with pickle BYTEA
            insert_query = text("""
                INSERT INTO model_registry (
                    model_name, model_type, version, tag_name,
                    hyperparameters, model_pickle, model_size_bytes,
                    validation_mape, is_active, created_at
                )
                VALUES (
                    :model_name, :model_type, :version, :tag_name,
                    :hyperparameters, :model_pickle, :model_size_bytes,
                    :validation_mape, :is_active, NOW()
                )
                RETURNING model_id
            """)

            import json

            result = await self.session.execute(insert_query, {
                "model_name": f"{tag_name}_{model_type}",
                "model_type": model_type,
                "version": version,
                "tag_name": tag_name,
                "hyperparameters": json.dumps(hyperparameters or {}),
                "model_pickle": model_bytes,  # BYTEA column
                "model_size_bytes": len(model_bytes),
                "validation_mape": metrics.get('mape', 0.0),
                "is_active": True
            })

            model_id = result.scalar()
            await self.session.commit()

            console.info(f"Model registered in database: model_id={model_id}, size={len(model_bytes)} bytes")

            return model_id

        except Exception as e:
            console.error(f"Error saving model for {tag_name}: {e}")
            await self.session.rollback()
            raise

    async def load_model(
        self,
        model_id: Optional[int] = None,
        tag_name: Optional[str] = None,
        model_type: Optional[str] = None
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Load trained model from PostgreSQL BYTEA or disk (fallback).

        Args:
            model_id: Specific model ID to load
            tag_name: Load latest active model for tag
            model_type: Model type filter

        Returns:
            Tuple of (model_object, model_metadata)
        """
        try:
            # Query model registry
            if model_id:
                query = text("SELECT * FROM model_registry WHERE model_id = :model_id")
                params = {"model_id": model_id}
            elif tag_name:
                query = text("""
                    SELECT * FROM model_registry
                    WHERE tag_name = :tag_name
                      AND is_active = TRUE
                      AND (:model_type IS NULL OR model_type = :model_type)
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                params = {"tag_name": tag_name, "model_type": model_type}
            else:
                raise ValueError("Must provide model_id or tag_name")

            result = await self.session.execute(query, params)
            row = result.mappings().first()

            if not row:
                raise ValueError(f"Model not found: model_id={model_id}, tag_name={tag_name}")

            metadata = dict(row)
            loop = asyncio.get_event_loop()

            # Try to load from BYTEA first (preferred)
            if metadata.get('model_pickle'):
                import pickle
                model = await loop.run_in_executor(
                    None,
                    lambda: pickle.loads(metadata['model_pickle'])
                )
                console.info(f"Model loaded from PostgreSQL BYTEA: {metadata['model_name']} (ID: {metadata['model_id']}, {len(metadata['model_pickle'])} bytes)")

            # Fallback to file path (legacy support)
            elif metadata.get('model_path'):
                model_path = Path(metadata['model_path'])
                if not model_path.exists():
                    raise FileNotFoundError(f"Model file not found: {model_path}")

                model = await loop.run_in_executor(
                    None,
                    lambda: joblib.load(model_path)
                )
                console.info(f"Model loaded from file (legacy): {metadata['model_name']} (ID: {metadata['model_id']})")

            else:
                raise ValueError(f"Model {metadata['model_id']} has no pickle data or file path")

            return model, metadata

        except Exception as e:
            console.error(f"Error loading model: {e}")
            raise

    # ============================================================================
    # Utility Methods
    # ============================================================================

    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate regression metrics."""
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = mean_absolute_percentage_error(y_true, y_pred) * 100  # Convert to percentage

        return {
            'mae': float(mae),
            'rmse': float(rmse),
            'mape': float(mape)
        }
