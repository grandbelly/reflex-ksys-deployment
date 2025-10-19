"""
Training State - Complete Integration

Pipeline V2 + Feature Config + Model Config 완전 통합
"""

import reflex as rx
from typing import Dict, List, Any, Optional
from reflex.utils import console

from ..db_orm import get_async_session
from ..services.feature_config_service_final import FeatureConfigService

# ========================================================================
# Module-level cache for trained models
# Reflex State cannot store non-serializable objects like model instances
# ========================================================================
_training_cache: Dict[str, Dict[str, Any]] = {}

def _cache_training_result(tag_name: str, result: Dict[str, Any], model):
    """Store training result and model object in module-level cache"""
    from datetime import datetime
    global _training_cache
    _training_cache[tag_name] = {
        'result': result,
        'model': model,
        'timestamp': datetime.now()
    }
    console.info(f"✅ Cached training result for {tag_name}")

def _get_cached_model(tag_name: str):
    """Retrieve cached model object"""
    global _training_cache
    cached = _training_cache.get(tag_name)
    if cached:
        console.info(f"✅ Retrieved cached model for {tag_name}")
        return cached.get('model')
    console.warn(f"⚠️ No cached model found for {tag_name}")
    return None

def _clear_cache(tag_name: str = None):
    """Clear training cache for specific tag or all"""
    global _training_cache
    if tag_name:
        if tag_name in _training_cache:
            del _training_cache[tag_name]
            console.info(f"Cleared cache for {tag_name}")
    else:
        _training_cache.clear()
        console.info("Cleared all training cache")


class TrainingState(rx.State):
    """Training page state"""

    # Sensor selection
    selected_tag: str = ""
    available_tags: list[str] = []

    # Model selection
    selected_model: str = ""

    # Feature configuration
    available_feature_configs: list[str] = []
    selected_feature_config: str = ""
    feature_config_loaded: bool = False
    feature_counts: dict = {"rolling": 0, "temporal": 0}
    # New feature config creation
    show_feature_creator: bool = False
    skip_feature_engineering: bool = True  # Default to Pure ARIMA
    new_config_name: str = ""
    config_name_exists: bool = False  # ✅ NEW: Track if config name already exists
    selected_rolling_features: list[str] = []
    selected_temporal_features: list[str] = []

    # Training parameters
    training_days: int = 7
    forecast_horizon: int = 24  # DEPRECATED - use forecast_horizon_hours
    enable_preprocessing: bool = True
    outlier_threshold: float = 3.0

    # Forecast configuration (NEW - for offline/online sync)
    forecast_interval_minutes: int = 10  # 예측 간격 (분 단위)
    forecast_horizon_hours: int = 6      # 예측 기간 (시간 단위)

    # Model-specific parameters
    season_length: int = 1  # AutoARIMA seasonal period (1=non-seasonal, 144=daily for 10-min data)

    # Training state
    is_training: bool = False
    is_loading: bool = False  # For save model operation
    training_progress: int = 0
    training_status: str = ""
    training_complete: bool = False

    # Results
    result_metadata: dict = {}
    model_diagnostics: dict = {}  # ARIMA parameters, AIC, BIC, residuals info
    preprocessing_stats: dict = {}  # Outliers removed, interpolation, etc.
    feature_engineering_stats: dict = {}  # Features created, lag/rolling/temporal counts
    error_message: str = ""
    success_message: str = ""
    trained_model_id: int = 0  # 저장된 모델 ID (모델 객체는 DB에 저장)
    evaluation_metrics: dict = {}  # MAE, MAPE, MASE, RMSE, SMAPE
    fold_results: list[dict[str, Any]] = []  # ✅ NEW: Fold-by-fold walk-forward validation results
    forecast_with_intervals: list = []  # Predictions with 80%, 95% confidence intervals
    forecast_values: list = []  # Just the forecast values (for saving to DB)
    historical_data: list = []  # Raw sensor data for chart context
    residuals_analysis: dict = {}  # ACF, Q-Q plot, Histogram, Skewness, Kurtosis

    # Saved model info (after save_model)
    saved_model_info: dict = {}  # Model registry 정보
    saved_predictions: list = []  # 저장된 예측 데이터
    show_saved_data: bool = False  # 저장 데이터 표시 토글

    @rx.var
    def horizons(self) -> List[int]:
        """Generate continuous horizon list: [10, 20, 30, ..., 360]

        Returns list of horizon values in minutes based on:
        - forecast_interval_minutes: Gap between each prediction (e.g., 10분)
        - forecast_horizon_hours: Total forecast window (e.g., 6시간)

        Example: 10분 간격, 6시간 예측 → [10, 20, 30, ..., 360] (36개 스텝)
        """
        if self.forecast_interval_minutes <= 0 or self.forecast_horizon_hours <= 0:
            return []

        total_minutes = self.forecast_horizon_hours * 60
        return list(range(
            self.forecast_interval_minutes,
            total_minutes + self.forecast_interval_minutes,
            self.forecast_interval_minutes
        ))

    @rx.var
    def forecast_summary(self) -> str:
        """User-friendly display: '10분 단위 6시간 예측 (36개 스텝)'"""
        horizon_list = self.horizons
        if not horizon_list:
            return "예측 설정 없음"

        return f"{self.forecast_interval_minutes}분 단위 {self.forecast_horizon_hours}시간 예측 ({len(horizon_list)}개 스텝)"

    @rx.var
    def residuals_stats(self) -> dict:
        """Extract residuals statistics safely"""
        return self.residuals_analysis.get("statistics", {})

    @rx.event(background=True)
    async def initialize(self):
        """Page 초기화"""
        async with self:
            self.error_message = ""
            yield

        try:
            async with get_async_session() as session:
                service = FeatureConfigService(session)

                # Load available feature configs
                configs = await service.list_configs()

                async with self:
                    self.available_feature_configs = [
                        f"{c['tag_name']}:{c['config_name']}"
                        for c in configs
                    ]
                    yield

        except Exception as e:
            console.error(f"Initialize failed: {e}")
            async with self:
                self.error_message = f"Failed to initialize: {e}"
                yield

    def set_selected_tag(self, tag: str):
        """Tag 선택 시"""
        self.selected_tag = tag
        self.selected_feature_config = ""
        self.feature_config_loaded = False

        # Filter configs for this tag (background task)
        return TrainingState.filter_configs_for_tag

    @rx.event(background=True)
    async def filter_configs_for_tag(self):
        """선택된 tag의 config만 표시"""
        try:
            async with get_async_session() as session:
                service = FeatureConfigService(session)
                configs = await service.list_configs(tag_name=self.selected_tag)

                async with self:
                    self.available_feature_configs = [
                        c['config_name'] for c in configs
                    ]
                    yield

        except Exception as e:
            console.error(f"Filter configs failed: {e}")

    async def set_selected_model(self, model: str):
        """Model 선택 - 모델에 따라 feature engineering 자동 조정"""
        self.selected_model = model

        # Define model characteristics dynamically
        # This can be extended or modified based on actual model capabilities
        pure_timeseries_models = ["AutoARIMA"]  # Models that work best without external features
        feature_based_models = ["Prophet", "XGBoost"]  # Models that benefit from feature engineering

        # Automatically adjust skip_feature_engineering based on model type
        if model in pure_timeseries_models:
            self.skip_feature_engineering = True
            self.selected_feature_config = ""
            self.feature_config_loaded = False
        elif model in feature_based_models:
            # For models that benefit from features, enable feature engineering by default
            self.skip_feature_engineering = False

    @rx.event(background=True)
    async def load_feature_config(self, config_name: str):
        """Feature configuration 로드"""
        async with self:
            self.selected_feature_config = config_name
            self.feature_config_loaded = False
            yield

        try:
            async with get_async_session() as session:
                service = FeatureConfigService(session)
                enabled = await service.get_enabled_features(
                    self.selected_tag,
                    config_name
                )

                async with self:
                    self.feature_counts = {
                        "rolling": len(enabled.get("rolling", [])),
                        "temporal": len(enabled.get("temporal", []))
                    }
                    self.feature_config_loaded = True
                    yield

        except Exception as e:
            console.error(f"Load feature config failed: {e}")
            async with self:
                self.error_message = f"Failed to load config: {e}"
                yield

    async def toggle_skip_features(self, checked: bool):
        """Toggle skip feature engineering"""
        self.skip_feature_engineering = checked
        if checked:
            # Reset feature creator when skipping
            self.show_feature_creator = False
            self.selected_feature_config = ""
            self.feature_config_loaded = False

    async def toggle_feature_creator(self):
        """Toggle feature creator UI"""
        self.show_feature_creator = not self.show_feature_creator
        if self.show_feature_creator:
            # Reset fields
            self.new_config_name = ""
            self.selected_rolling_features = []
            self.selected_temporal_features = []

    @rx.var
    def config_name_validation_message(self) -> str:
        """Validation message for config name"""
        if not self.new_config_name:
            return ""
        if self.config_name_exists:
            return f"⚠️ Configuration name '{self.new_config_name}' already exists for {self.selected_tag}"
        return f"✅ Name '{self.new_config_name}' is available"

    @rx.var
    def can_create_config(self) -> bool:
        """Check if config can be created"""
        return bool(self.new_config_name and not self.config_name_exists)

    @rx.event(background=True)
    async def set_new_config_name(self, name: str):
        """Set new config name and check for duplicates"""
        async with self:
            self.new_config_name = name
            self.config_name_exists = False
            yield

        # Check if name exists (only if we have both tag and name)
        if not name or not self.selected_tag:
            return

        try:
            async with get_async_session() as session:
                from sqlalchemy import text

                check_query = text("""
                    SELECT COUNT(*) as count
                    FROM feature_config
                    WHERE tag_name = :tag_name AND config_name = :config_name
                """)

                result = await session.execute(check_query, {
                    "tag_name": self.selected_tag,
                    "config_name": name
                })

                count = result.scalar()

                async with self:
                    self.config_name_exists = (count > 0)
                    yield

        except Exception as e:
            console.error(f"Failed to check config name: {e}")

    async def toggle_rolling_feature(self, window: str):
        """Toggle rolling feature selection"""
        if window in self.selected_rolling_features:
            self.selected_rolling_features.remove(window)
        else:
            self.selected_rolling_features.append(window)

    async def toggle_temporal_feature(self, feature_type: str):
        """Toggle temporal feature selection"""
        if feature_type in self.selected_temporal_features:
            self.selected_temporal_features.remove(feature_type)
        else:
            self.selected_temporal_features.append(feature_type)

    @rx.event(background=True)
    async def create_feature_config(self):
        """Create new feature configuration"""
        if not self.new_config_name:
            async with self:
                self.error_message = "Please enter a configuration name"
                yield
            return

        if not self.selected_tag:
            async with self:
                self.error_message = "Please select a sensor first"
                yield
            return

        try:
            async with get_async_session() as session:
                service = FeatureConfigService(session)

                # Build rolling features
                rolling_features = [{"window": int(w), "enabled": True} for w in self.selected_rolling_features]

                # Build temporal features
                temporal_features = [{"type": t, "enabled": True} for t in self.selected_temporal_features]

                # Create config
                await service.create_config(
                    tag_name=self.selected_tag,
                    config_name=self.new_config_name,
                    rolling_features=rolling_features if rolling_features else None,
                    temporal_features=temporal_features if temporal_features else None,
                )

                # Reload configs
                configs = await service.list_configs(tag_name=self.selected_tag)

                # Load feature counts for the newly created config
                enabled = await service.get_enabled_features(
                    self.selected_tag,
                    self.new_config_name
                )

                async with self:
                    self.available_feature_configs = [c['config_name'] for c in configs]
                    self.selected_feature_config = self.new_config_name
                    self.feature_counts = {
                        "rolling": len(enabled.get("rolling", [])),
                        "temporal": len(enabled.get("temporal", []))
                    }
                    self.feature_config_loaded = True  # ✅ FIX: Set to True after creation
                    self.show_feature_creator = False
                    console.info(f"Created feature config: {self.new_config_name} - Features loaded: rolling={self.feature_counts['rolling']}, temporal={self.feature_counts['temporal']}")
                    yield


        except Exception as e:
            console.error(f"Create feature config failed: {e}")
            async with self:
                self.error_message = f"Failed to create config: {e}"
                yield

    @rx.event(background=True)
    async def start_training(self):
        """Training 시작 - Pipeline V2 실행"""
        # Validation
        if not self.selected_tag:
            async with self:
                self.error_message = "Please select a sensor"
                yield
            return

        if not self.selected_model:
            async with self:
                self.error_message = "Please select a model"
                yield
            return

        # Feature config validation - skip if Pure ARIMA is selected
        if not self.skip_feature_engineering and not self.selected_feature_config:
            async with self:
                self.error_message = "Please select a feature configuration or enable Pure ARIMA"
                yield
            return

        # Start training
        async with self:
            self.is_training = True
            self.training_complete = False
            self.training_progress = 0
            self.training_status = "Initializing..."
            self.error_message = ""
            yield

        try:
            async with get_async_session() as session:
                from ..services.feature_config_service_final import FeatureConfigService
                from ..ml.pipeline_v2_hybrid import TrainingPipelineV2

                # Step 1: Load feature configuration (skip if Pure ARIMA)
                config = {}
                if not self.skip_feature_engineering:
                    async with self:
                        self.training_progress = 10
                        self.training_status = "Loading feature configuration..."
                        yield

                    service = FeatureConfigService(session)
                    config = await service.get_enabled_features(
                        self.selected_tag,
                        self.selected_feature_config
                    )
                else:
                    async with self:
                        self.training_progress = 10
                        self.training_status = "Using Pure Auto-ARIMA (no external features)..."
                        yield

                # Step 2: Build Pipeline V2
                async with self:
                    self.training_progress = 20
                    self.training_status = "Building pipeline..."
                    yield

                pipeline = TrainingPipelineV2(session).set_data_source(
                    self.selected_tag,
                    days=self.training_days
                )

                # Step 3: Add preprocessing if enabled
                if self.enable_preprocessing:
                    async with self:
                        self.training_progress = 30
                        self.training_status = "Configuring preprocessing..."
                        yield

                    pipeline = (pipeline
                        .add_preprocessing()
                            .interpolate(method='linear')
                            .remove_outliers(threshold=self.outlier_threshold)
                        .done())

                # Step 4: Add feature engineering from database config
                async with self:
                    self.training_progress = 40
                    self.training_status = "Configuring features..."
                    yield

                feature_chain = pipeline.add_feature_engineering()

                # Add lag features
                if config.get('lag'):
                    lag_periods = [f['periods'] for f in config['lag'] if f.get('enabled', True)]
                    if lag_periods:
                        feature_chain = feature_chain.add_lag(lag_periods)

                # Add rolling features
                if config.get('rolling'):
                    rolling_windows = [f['window'] for f in config['rolling'] if f.get('enabled', True)]
                    if rolling_windows:
                        feature_chain = feature_chain.add_rolling(rolling_windows)

                # Add temporal features
                if config.get('temporal'):
                    temporal_types = [f['type'] for f in config['temporal'] if f.get('enabled', True)]
                    if temporal_types:
                        feature_chain = feature_chain.add_temporal(temporal_types)

                pipeline = feature_chain.done()

                # Step 5: Add model
                async with self:
                    self.training_progress = 50
                    self.training_status = f"Adding {self.selected_model} model..."
                    yield

                # Add model with model-specific parameters
                model_params = {}
                if self.selected_model == "auto_arima":
                    # Pass season_length to AutoARIMA
                    model_params["season_length"] = self.season_length
                    console.info(f"AutoARIMA: season_length={self.season_length}")

                pipeline = pipeline.add_model(self.selected_model, **model_params)

                # Step 6: Add validation
                async with self:
                    self.training_progress = 60
                    self.training_status = "Configuring validation..."
                    yield

                # Pass forecast configuration and training period to validation
                # This ensures validation parameters match user's configuration
                # n_splits will be calculated automatically based on data availability
                pipeline = pipeline.add_validation(
                    "walk_forward",
                    forecast_interval_minutes=self.forecast_interval_minutes,
                    forecast_horizon_hours=self.forecast_horizon_hours,
                    training_days=self.training_days  # ✅ NEW: For optimal n_splits calculation
                ).build()

                # Step 7: Execute training
                async with self:
                    self.training_progress = 70
                    self.training_status = "Training model (this may take a few minutes)..."
                    yield

                result = await pipeline.execute()

                # Extract and store historical data for chart display
                raw_data = result.get('raw_data')
                if raw_data is not None and not raw_data.empty:
                    async with self:
                        # Convert last 48 hours of raw data for chart
                        self.historical_data = [
                            {
                                "timestamp": row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp']),
                                "value": float(row['value'])
                            }
                            for _, row in raw_data.tail(48).iterrows()
                        ]
                        console.info(f"Stored {len(self.historical_data)} historical data points for chart")
                        yield

                # Step 8: Extract diagnostics and complete
                async with self:
                    self.training_progress = 90
                    self.training_status = "Extracting model diagnostics..."
                    yield

                # Extract model diagnostics
                model_results = result.get('results', {})
                best_model_name = result['metadata'].best_model

                if best_model_name and best_model_name in model_results:
                    best_model = model_results[best_model_name]['model']
                    model_metrics = model_results[best_model_name].get('metrics', {})

                    # Get model-specific diagnostics
                    if hasattr(best_model, 'get_diagnostics'):
                        diagnostics = best_model.get_diagnostics()
                        async with self:
                            self.model_diagnostics = {
                                "model_type": best_model_name,
                                "arima_string": diagnostics.get('arima_string', 'N/A'),
                                "aic": diagnostics.get('aic', None),
                                "bic": diagnostics.get('bic', None),
                                "aicc": diagnostics.get('aicc', None),
                                "sigma2": diagnostics.get('sigma2', None),
                                "residuals_mean": diagnostics.get('residuals_mean', None),
                                "residuals_std": diagnostics.get('residuals_std', None),
                            }
                            yield

                    # Use evaluation metrics from Pipeline validation (ALL models have this now)
                    if model_metrics:
                        async with self:
                            self.training_status = "Loading evaluation metrics..."
                            self.evaluation_metrics = model_metrics
                            # ✅ NEW: Store fold-by-fold results for detailed view
                            self.fold_results = model_metrics.get('fold_results', [])
                            console.info(f"✅ Evaluation metrics from pipeline: MAE={model_metrics.get('mae', 0):.2f}, MAPE={model_metrics.get('mape', 0):.2f}%")
                            console.info(f"   Validation data points: {model_metrics.get('n_predictions', 0)}")
                            if self.fold_results:
                                console.info(f"   Fold-by-fold results: {len(self.fold_results)} folds extracted")
                            yield

                    # Get residuals analysis (ACF, Q-Q plot, Histogram)
                    if hasattr(best_model, 'get_residuals_analysis'):
                        console.info("Analyzing residuals...")
                        residuals_data = best_model.get_residuals_analysis()

                        async with self:
                            self.residuals_analysis = residuals_data
                            if residuals_data:
                                stats = residuals_data.get('statistics', {})
                                console.info(f"Residuals: mean={stats.get('mean', 0):.4f}, skewness={stats.get('skewness', 0):.2f}")
                            yield

                # Extract preprocessing statistics
                metadata = result['metadata']
                async with self:
                    self.preprocessing_stats = {
                        "raw_samples": metadata.raw_samples,
                        "processed_samples": metadata.processed_samples,
                        "outliers_removed": metadata.outliers_removed,
                        "interpolated_gaps": metadata.interpolated_gaps,
                        "preprocessing_steps": metadata.preprocessing_steps,
                        "details": metadata.preprocessing_details,  # Detailed statistics
                    }

                    # Extract feature engineering statistics
                    self.feature_engineering_stats = {
                        "features_created": metadata.features_created,
                        "original_features": metadata.original_features,
                        "final_features": metadata.final_features,
                    }
                    yield

                # Generate forecast with confidence intervals
                if best_model_name and best_model_name in model_results:
                    best_model = model_results[best_model_name]['model']

                    if hasattr(best_model, 'predict'):
                        async with self:
                            self.training_status = "Generating forecast with confidence intervals..."
                            yield

                        # Use computed horizons length (e.g., 36 steps for 6 hours @ 10-min intervals)
                        horizon_steps = len(self.horizons) if self.horizons else self.forecast_horizon
                        console.info(f"Generating forecast: {horizon_steps} steps ({self.forecast_summary})")
                        console.info("With 80% and 95% confidence intervals...")

                        forecast_df = await best_model.predict(
                            horizon=horizon_steps,
                            level=[80, 95]
                        )

                        # Convert to list of dicts for Reflex state
                        async with self:
                            # Determine the model column name dynamically
                            model_col = None
                            for col in forecast_df.columns:
                                if col in ['AutoARIMA', 'Prophet', 'XGBoost', 'yhat']:
                                    model_col = col
                                    break

                            if not model_col:
                                # Fallback: use the first non-ds column
                                model_col = [c for c in forecast_df.columns if c != 'ds'][0] if len(forecast_df.columns) > 1 else 'forecast'

                            console.info(f"Using model column: {model_col}")

                            # Store forecast with actual model column names (NOT AutoARIMA for all)
                            self.forecast_with_intervals = [
                                {
                                    "ds": row.get('ds').isoformat() if hasattr(row.get('ds'), 'isoformat') else str(row.get('ds')),
                                    model_col: float(row.get(model_col, 0)),
                                    f"{model_col}-lo-80": float(row.get(f'{model_col}-lo-80', 0)),
                                    f"{model_col}-hi-80": float(row.get(f'{model_col}-hi-80', 0)),
                                    f"{model_col}-lo-95": float(row.get(f'{model_col}-lo-95', 0)),
                                    f"{model_col}-hi-95": float(row.get(f'{model_col}-hi-95', 0)),
                                }
                                for _, row in forecast_df.iterrows()
                            ]

                            # Also extract just the forecast values for save_model
                            self.forecast_values = [
                                float(row.get(model_col, row.get('AutoARIMA', row.get('yhat', 0))))
                                for _, row in forecast_df.iterrows()
                            ]
                            console.info(f"Forecast generated: {len(self.forecast_with_intervals)} points")
                            console.info(f"Forecast values: {len(self.forecast_values)} values extracted for save_model")
                            yield

                # Step 10: Cache model object for save_model
                # Model object cannot be stored in Reflex state (not serializable)
                # Store in module-level cache instead
                if best_model_name and best_model_name in model_results:
                    best_model = model_results[best_model_name]['model']
                    _cache_training_result(self.selected_tag, result, best_model)
                    console.info(f"✅ Model object cached for {self.selected_tag}")

                # Step 11: Complete
                async with self:
                    self.training_progress = 100
                    self.training_status = "Training complete!"
                    self.is_training = False
                    self.training_complete = True

                    # Extract real results from Pipeline V2
                    self.result_metadata = {
                        "tag_name": metadata.tag_name,
                        "data_start": metadata.data_start.isoformat() if metadata.data_start else None,
                        "data_end": metadata.data_end.isoformat() if metadata.data_end else None,
                        "raw_samples": metadata.raw_samples,
                        "processed_samples": metadata.processed_samples,
                        "preprocessing_steps": metadata.preprocessing_steps,
                        "outliers_removed": metadata.outliers_removed,
                        "interpolated_gaps": metadata.interpolated_gaps,
                        "features_created": metadata.features_created,
                        "original_features": metadata.original_features,
                        "final_features": metadata.final_features,
                        "models_trained": metadata.models_trained,
                        "training_duration": f"{metadata.training_duration:.2f}s",
                        "best_model": metadata.best_model,
                        "best_mape": f"{metadata.best_mape:.2f}%",
                    }
                    yield

        except Exception as e:
            console.error(f"Training failed: {e}")
            import traceback
            traceback.print_exc()

            async with self:
                self.is_training = False
                self.training_complete = False
                self.error_message = f"Training failed: {e}"
                yield

    def view_predictions(self):
        """예측 결과 보기 - Open forecast dialog"""
        console.log("Opening forecast dialog")
        # This method should be overridden by TrainingWizardState
        # But provide basic implementation for direct TrainingState usage
        if hasattr(self, 'open_forecast_dialog'):
            return self.open_forecast_dialog()
        else:
            console.warn("open_forecast_dialog not available in this state")

    @rx.event(background=True)
    async def save_model(self):
        """모델을 데이터베이스에 저장하고 예측 결과를 생성"""
        async with self:
            self.is_loading = True
            self.error_message = ""

        try:
            async with get_async_session() as session:
                from ..models.forecasting_orm import ModelRegistry, Prediction
                from datetime import datetime, timedelta
                import json
                import os
                import pickle
                from pathlib import Path

                # 1. Retrieve model from cache and serialize to pickle bytes
                model_name = f"{self.selected_model}_{self.selected_tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # Get trained model object from module-level cache
                trained_model = _get_cached_model(self.selected_tag)

                # Serialize model to pickle BYTEA (NOT file)
                model_pickle_bytes = None
                model_size = 0

                if trained_model is not None:
                    try:
                        # Serialize to bytes for PostgreSQL BYTEA
                        model_pickle_bytes = pickle.dumps(trained_model)
                        model_size = len(model_pickle_bytes)
                        console.info(f"✅ Model serialized to pickle bytes: {model_size} bytes")
                    except Exception as e:
                        console.error(f"Failed to pickle model: {e}")
                        console.warn(f"⚠️ Pickle failed, saving metadata only")
                else:
                    console.warn(f"⚠️ No cached model found, saving metadata only")

                # Remove microseconds to avoid sentinel values mismatch
                current_time = datetime.now().replace(microsecond=0)

                # Generate unique version with timestamp to avoid unique constraint violations
                version = f"1.0.{current_time.strftime('%Y%m%d%H%M%S')}"

                # 2. Parse datetime strings to datetime objects for database
                data_start_str = self.result_metadata.get('data_start')
                data_end_str = self.result_metadata.get('data_end')

                # Convert ISO strings to datetime objects
                data_start_dt = None
                data_end_dt = None
                if data_start_str:
                    try:
                        # Parse ISO format string (e.g., "2025-10-06T19:40:58.549566+09:00")
                        data_start_dt = datetime.fromisoformat(data_start_str)
                        # Remove microseconds and timezone for database
                        data_start_dt = data_start_dt.replace(microsecond=0, tzinfo=None)
                    except Exception as e:
                        console.error(f"Failed to parse data_start: {e}")

                if data_end_str:
                    try:
                        data_end_dt = datetime.fromisoformat(data_end_str)
                        # Remove microseconds and timezone for database
                        data_end_dt = data_end_dt.replace(microsecond=0, tzinfo=None)
                    except Exception as e:
                        console.error(f"Failed to parse data_end: {e}")

                # 3. Build pipeline_config with validation data and training info
                # IMPORTANT: Include horizons for offline/online sync
                computed_horizons = self.horizons  # [10, 20, 30, ..., 360]

                # Get feature config ID (integer) if feature engineering was used
                feature_config_id = None
                feature_config_name = None
                if not self.skip_feature_engineering and self.selected_feature_config:
                    try:
                        service = FeatureConfigService(session)
                        config = await service.get_config(self.selected_tag, self.selected_feature_config)
                        if config:
                            feature_config_id = config['config_id']
                            feature_config_name = config['config_name']
                    except Exception as e:
                        console.warn(f"Failed to get feature_config_id: {e}")
                        # Fallback to name only
                        feature_config_name = self.selected_feature_config

                pipeline_config = {
                    'forecast_config': {
                        'forecast_interval_minutes': self.forecast_interval_minutes,
                        'forecast_horizon_hours': self.forecast_horizon_hours,
                        'horizons': computed_horizons,
                        'total_steps': len(computed_horizons),
                    },
                    'metrics': {
                        'validation_data': self.evaluation_metrics.get('validation_data', []),
                        'mape': self.evaluation_metrics.get('mape', 0.0),
                        'mae': self.evaluation_metrics.get('mae', 0.0),
                        'rmse': self.evaluation_metrics.get('rmse', 0.0),
                        'mase': self.evaluation_metrics.get('mase', 0.0),
                        'smape': self.evaluation_metrics.get('smape', 0.0),
                        'n_predictions': self.evaluation_metrics.get('n_predictions', 0),
                    },
                    'training_info': {
                        'data_start': data_start_str,  # Keep string in JSON
                        'data_end': data_end_str,
                        'training_samples': self.result_metadata.get('processed_samples', 0),
                        'training_duration': self.result_metadata.get('training_duration', '0s'),
                        'preprocessing_steps': self.result_metadata.get('preprocessing_steps', []),
                        'features_created': self.result_metadata.get('features_created', 0),
                    },
                    'hyperparameters': {
                        'training_days': self.training_days,
                        # forecast_horizon REMOVED - use forecast_config.forecast_horizon_hours
                        'feature_config_id': feature_config_id,  # ✅ INTEGER from database
                        'feature_config_name': feature_config_name,  # ✅ STRING for readability
                        'enable_preprocessing': self.enable_preprocessing,
                        'outlier_threshold': self.outlier_threshold,
                    },
                }

                # Log what we're saving
                console.info(f"💾 Saving model with validation metrics:")
                console.info(f"   📊 EVALUATION_METRICS KEYS: {list(self.evaluation_metrics.keys())}")
                console.info(f"   - Train MAE: {self.evaluation_metrics.get('train_mae', 'NOT FOUND')}")
                console.info(f"   - Validation MAPE: {self.evaluation_metrics.get('mape', 0.0):.2f}%")
                console.info(f"   - Validation MAE: {self.evaluation_metrics.get('mae', 0.0):.2f}")
                console.info(f"   - Validation Points: {self.evaluation_metrics.get('n_predictions', 0)}")
                console.info(f"   - Training Samples: {self.result_metadata.get('processed_samples', 0)}")
                console.info(f"   - Training Period: {data_start_str} to {data_end_str}")
                console.info(f"   - Parsed dates for DB: {data_start_dt} to {data_end_dt}")
                console.info(f"📊 Forecast Configuration:")
                console.info(f"   - Interval: {self.forecast_interval_minutes}분 단위")
                console.info(f"   - Horizon: {self.forecast_horizon_hours}시간 예측")
                console.info(f"   - Total Steps: {len(computed_horizons)}개 스텝")
                console.info(f"   - Horizons: {computed_horizons[:5]}...{computed_horizons[-3:]} (showing first/last)")

                # 4. ModelRegistry에 모델 정보 저장 (with BYTEA pickle storage)
                model_entry = ModelRegistry(
                    model_name=model_name,
                    model_type=self.selected_model.upper(),
                    tag_name=self.selected_tag,
                    version=version,  # Unique timestamp-based version
                    model_pickle=model_pickle_bytes,  # ✅ BYTEA storage (PostgreSQL binary)
                    model_size_bytes=model_size,
                    is_active=True,
                    is_deployed=False,  # 초기에는 미배포 상태
                    # 성능 메트릭 - USE EVALUATION_METRICS (from walk-forward validation)
                    train_mae=self.evaluation_metrics.get('train_mae'),  # ✅ Now calculated in evaluate()
                    train_rmse=None,  # Future: calculate from training data
                    train_mape=None,  # Future: calculate from training data
                    validation_mae=self.evaluation_metrics.get('mae'),
                    validation_rmse=self.evaluation_metrics.get('rmse'),
                    validation_mape=self.evaluation_metrics.get('mape'),
                    # Training samples and dates (datetime objects for database)
                    training_samples=self.result_metadata.get('processed_samples'),
                    training_data_start=data_start_dt,  # ✅ datetime object
                    training_data_end=data_end_dt,  # ✅ datetime object
                    # Pipeline configuration with validation data
                    pipeline_config=json.dumps(pipeline_config),
                    # ✅ UPDATED: Use same hyperparameters from pipeline_config (no duplication)
                    hyperparameters=json.dumps(pipeline_config.get('hyperparameters', {})),
                    created_by="user",
                    created_at=current_time  # Explicitly set to avoid microseconds from default
                )

                session.add(model_entry)
                await session.flush()  # ID 생성을 위해 flush

                # 5. Save offline backtest predictions to training_evaluation table
                # (NOT predictions table - that's for online ForecastScheduler predictions)
                if self.forecast_values:
                    from sqlalchemy import text

                    # Remove microseconds to avoid sentinel values mismatch
                    current_time = datetime.now().replace(microsecond=0)

                    # Build INSERT statement for training_evaluation
                    insert_sql = text("""
                        INSERT INTO training_evaluation
                        (model_id, evaluation_time, target_time, predicted_value, actual_value,
                         horizon_minutes, model_type, sensor_tag)
                        VALUES
                        (:model_id, :evaluation_time, :target_time, :predicted_value, :actual_value,
                         :horizon_minutes, :model_type, :sensor_tag)
                    """)

                    # Execute INSERT for each prediction (offline backtest data)
                    # IMPORTANT: Use horizons list from forecast configuration
                    if not self.horizons:
                        console.error("⚠️ No horizons configured! Forecast configuration is missing.")
                        raise ValueError("Forecast configuration (horizons) is required for saving predictions")

                    for i, value in enumerate(self.forecast_values):
                        # Use horizon from configured list (e.g., 10, 20, 30... for 10-min intervals)
                        if i >= len(self.horizons):
                            console.error(f"⚠️ Forecast value index {i} exceeds horizons list length {len(self.horizons)}")
                            break

                        horizon_minutes = self.horizons[i]

                        # Calculate target_time based on actual horizon
                        target_time = (current_time + timedelta(minutes=horizon_minutes)).replace(microsecond=0)

                        # Execute INSERT to training_evaluation
                        await session.execute(insert_sql, {
                            'model_id': model_entry.model_id,
                            'evaluation_time': current_time,  # When model was trained
                            'target_time': target_time,       # Future timestamp (correct interval)
                            'predicted_value': float(value),
                            'actual_value': 0,                # Placeholder (will be filled by ActualValueUpdater)
                            'horizon_minutes': horizon_minutes,  # Use actual horizon (10, 20, 30...)
                            'model_type': self.selected_model.upper(),
                            'sensor_tag': self.selected_tag,
                        })

                    console.log(f"Inserted {len(self.forecast_values)} evaluation records to training_evaluation table")

                await session.commit()

                console.log(f"Model saved successfully: {model_entry.model_id}")
                console.log(f"Saved {len(self.forecast_values)} predictions to database")

                # 6. 저장된 데이터를 바로 조회 (verification)
                from sqlalchemy import select

                # Model Registry 정보 조회
                model_query = select(ModelRegistry).where(ModelRegistry.model_id == model_entry.model_id)
                result = await session.execute(model_query)
                saved_model = result.scalar_one_or_none()

                # Training evaluation 정보 조회 (offline backtest results)
                pred_query = text("""
                    SELECT
                        evaluation_id,
                        model_id,
                        evaluation_time,
                        target_time,
                        predicted_value,
                        actual_value,
                        horizon_minutes,
                        model_type,
                        sensor_tag
                    FROM training_evaluation
                    WHERE model_id = :model_id
                    ORDER BY target_time ASC
                """)
                pred_result = await session.execute(pred_query, {"model_id": model_entry.model_id})
                saved_preds = pred_result.mappings().all()

                async with self:
                    self.is_loading = False
                    self.trained_model_id = model_entry.model_id
                    self.success_message = f"모델이 성공적으로 저장되었습니다. (ID: {model_entry.model_id})"

                    # 저장된 모델 정보 저장
                    if saved_model:
                        self.saved_model_info = {
                            "model_id": saved_model.model_id,
                            "model_name": saved_model.model_name,
                            "model_type": saved_model.model_type,
                            "tag_name": saved_model.tag_name,
                            "version": saved_model.version,
                            "model_path": saved_model.model_path,
                            "model_size_bytes": saved_model.model_size_bytes,
                            "is_active": saved_model.is_active,
                            "is_deployed": saved_model.is_deployed,
                            "created_at": saved_model.created_at.isoformat() if saved_model.created_at else None,
                            "created_by": saved_model.created_by,
                            "hyperparameters": saved_model.hyperparameters,
                        }

                    # 저장된 evaluation 데이터 저장 (training_evaluation table)
                    self.saved_predictions = [
                        {
                            "evaluation_id": row["evaluation_id"],
                            "model_id": row["model_id"],
                            "evaluation_time": row["evaluation_time"].isoformat() if row["evaluation_time"] else None,
                            "target_time": row["target_time"].isoformat() if row["target_time"] else None,
                            "predicted_value": float(row["predicted_value"]) if row["predicted_value"] is not None else None,
                            "actual_value": float(row["actual_value"]) if row["actual_value"] is not None else None,
                            "horizon_minutes": row["horizon_minutes"],
                            "model_type": row["model_type"],
                            "sensor_tag": row["sensor_tag"],
                        }
                        for row in saved_preds
                    ]

                    # 자동으로 저장 데이터 표시
                    self.show_saved_data = True

                    console.log(f"Loaded saved model info: {self.saved_model_info.get('model_id')}")
                    console.log(f"Loaded {len(self.saved_predictions)} saved predictions")

                    yield rx.toast.success(
                        f"모델 저장 완료! Model ID: {model_entry.model_id}",
                        duration=5000,
                        position="top-right"
                    )

        except Exception as e:
            console.error(f"Error saving model: {e}")
            async with self:
                self.is_loading = False
                self.error_message = f"모델 저장 실패: {str(e)}"
                yield rx.toast.error(
                    f"모델 저장 실패: {str(e)}",
                    duration=7000,
                    position="top-right"
                )

    async def reset_form(self):
        """폼 리셋"""
        self.selected_tag = ""
        self.selected_model = ""
        self.selected_feature_config = ""
        self.feature_config_loaded = False
        self.training_complete = False
        self.error_message = ""
        self.result_metadata = {}

    # Setters with proper type conversion
    async def set_training_days(self, days: str):
        """Set training days from string input"""
        try:
            self.training_days = int(days) if days else self.training_days
        except (ValueError, TypeError):
            pass  # Keep existing value on error

    async def set_forecast_horizon(self, horizon: str):
        """Set forecast horizon from string input"""
        try:
            self.forecast_horizon = int(horizon) if horizon else self.forecast_horizon
        except (ValueError, TypeError):
            pass

    async def set_enable_preprocessing(self, enabled: bool):
        self.enable_preprocessing = enabled

    async def set_outlier_threshold(self, threshold: str):
        """Set outlier threshold from string input"""
        try:
            self.outlier_threshold = float(threshold) if threshold else self.outlier_threshold
        except (ValueError, TypeError):
            pass

    async def set_forecast_interval_minutes(self, interval: str):
        """Set forecast interval from string input"""
        try:
            self.forecast_interval_minutes = int(interval) if interval else self.forecast_interval_minutes
        except (ValueError, TypeError):
            pass

    async def set_forecast_horizon_hours(self, hours: str):
        """Set forecast horizon hours from string input"""
        try:
            self.forecast_horizon_hours = int(hours) if hours else self.forecast_horizon_hours
        except (ValueError, TypeError):
            pass

    async def set_season_length(self, length: str):
        """Set season_length from string input"""
        try:
            self.season_length = int(length) if length else self.season_length
        except (ValueError, TypeError):
            pass
