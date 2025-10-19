"""
Flexible Training Pipeline with Method Chaining and Plugin System

Design Principles:
1. Method Chaining: Fluent API for pipeline configuration
2. Plugin System: Easy to add new algorithms
3. Configuration-based: Dynamic pipeline creation
4. Reusable Components: Modular design

Example Usage:
    # Method chaining
    pipeline = (TrainingPipeline(session)
        .set_data_source("INLET_PRESSURE", days=30)
        .add_feature_engineering(lags=[1, 6, 24], rolling=[6, 24])
        .add_model("auto_arima", seasonal=True)
        .add_model("prophet", changepoint_prior_scale=0.05)
        .add_validation("walk_forward", n_splits=5)
        .set_metrics(["mape", "rmse", "mae"])
        .build()
    )

    results = await pipeline.execute()

    # Configuration-based
    config = {
        "data_source": {"tag_name": "INLET_PRESSURE", "days": 30},
        "feature_engineering": {"lags": [1, 6, 24], "rolling": [6, 24]},
        "models": [
            {"type": "auto_arima", "params": {"seasonal": True}},
            {"type": "prophet", "params": {"changepoint_prior_scale": 0.05}}
        ],
        "validation": {"type": "walk_forward", "n_splits": 5},
        "metrics": ["mape", "rmse", "mae"]
    }

    pipeline = TrainingPipeline(session).from_config(config)
    results = await pipeline.execute()
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import pandas as pd
import pytz
from reflex.utils import console
from sqlalchemy.ext.asyncio import AsyncSession

from ksys_app.services.feature_engineering_service import FeatureEngineeringService


KST = pytz.timezone('Asia/Seoul')


# ============================================================================
# Plugin Base Classes
# ============================================================================

class ModelPlugin(ABC):
    """Base class for all model plugins"""

    def __init__(self, **params):
        self.params = params
        self.model = None

    @abstractmethod
    async def train(self, data: pd.DataFrame) -> Any:
        """Train the model and return model object"""
        pass

    @abstractmethod
    async def predict(self, horizon: int) -> pd.DataFrame:
        """Generate predictions for given horizon"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return model name"""
        pass


class ValidationStrategy(ABC):
    """Base class for validation strategies"""

    @abstractmethod
    async def validate(
        self,
        data: pd.DataFrame,
        model_plugin: ModelPlugin
    ) -> Dict[str, float]:
        """Execute validation and return metrics"""
        pass


class MetricCalculator(ABC):
    """Base class for metric calculators"""

    @abstractmethod
    def calculate(self, y_true: pd.Series, y_pred: pd.Series) -> float:
        """Calculate metric value"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return metric name"""
        pass


# ============================================================================
# Built-in Model Plugins
# ============================================================================

class AutoARIMAPlugin(ModelPlugin):
    """Auto ARIMA model plugin using statsforecast"""

    def get_name(self) -> str:
        return "auto_arima"

    async def train(self, data: pd.DataFrame) -> Any:
        """Train Auto ARIMA model"""
        try:
            from statsforecast import StatsForecast
            from statsforecast.models import AutoARIMA

            # Prepare data for statsforecast
            df = data.copy()
            df['ds'] = df['timestamp']
            df['y'] = df['value']
            df['unique_id'] = 'series_1'

            # Create model
            models = [AutoARIMA(season_length=24, **self.params)]
            sf = StatsForecast(models=models, freq='H', n_jobs=-1)

            # Fit
            sf.fit(df[['unique_id', 'ds', 'y']])

            self.model = sf
            console.info(f"✅ {self.get_name()} trained successfully")
            return self.model

        except ImportError:
            console.error("statsforecast not installed")
            raise

    async def predict(self, horizon: int) -> pd.DataFrame:
        """Generate predictions"""
        if self.model is None:
            raise ValueError("Model not trained")

        forecast = self.model.predict(h=horizon)
        return forecast


class ProphetPlugin(ModelPlugin):
    """Prophet model plugin"""

    def get_name(self) -> str:
        return "prophet"

    async def train(self, data: pd.DataFrame) -> Any:
        """Train Prophet model"""
        try:
            from prophet import Prophet

            # Prepare data
            df = data.copy()
            df['ds'] = df['timestamp']
            df['y'] = df['value']

            # Create and fit model
            model = Prophet(**self.params)
            model.fit(df[['ds', 'y']])

            self.model = model
            console.info(f"✅ {self.get_name()} trained successfully")
            return self.model

        except ImportError:
            console.error("prophet not installed")
            raise

    async def predict(self, horizon: int) -> pd.DataFrame:
        """Generate predictions"""
        if self.model is None:
            raise ValueError("Model not trained")

        future = self.model.make_future_dataframe(periods=horizon, freq='H')
        forecast = self.model.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]


class XGBoostPlugin(ModelPlugin):
    """XGBoost model plugin with feature engineering"""

    def get_name(self) -> str:
        return "xgboost"

    async def train(self, data: pd.DataFrame) -> Any:
        """Train XGBoost model"""
        try:
            import xgboost as xgb

            # Prepare features (assume feature engineering already done)
            feature_cols = [c for c in data.columns if c not in ['timestamp', 'value', 'tag_name']]

            if not feature_cols:
                raise ValueError("No features available for XGBoost")

            X = data[feature_cols].fillna(0)
            y = data['value'].values

            # Default params
            params = {
                'objective': 'reg:squarederror',
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 100,
                'random_state': 42,
                'n_jobs': -1
            }
            params.update(self.params)

            # Train
            model = xgb.XGBRegressor(**params)
            model.fit(X, y)

            self.model = model
            self.feature_cols = feature_cols
            console.info(f"✅ {self.get_name()} trained successfully")
            return self.model

        except ImportError:
            console.error("xgboost not installed")
            raise

    async def predict(self, horizon: int) -> pd.DataFrame:
        """Generate predictions (requires future features)"""
        if self.model is None:
            raise ValueError("Model not trained")

        # Note: For XGBoost, you need to provide future features
        # This is a placeholder - actual implementation depends on your feature engineering
        raise NotImplementedError("XGBoost prediction requires future feature generation")


# ============================================================================
# Built-in Validation Strategies
# ============================================================================

class WalkForwardValidation(ValidationStrategy):
    """Walk-forward validation strategy with dynamic test_size calculation"""

    def __init__(
        self,
        forecast_interval_minutes: int,  # REQUIRED: Data interval from user config (e.g., 10 for 10-min data)
        forecast_horizon_hours: int,     # REQUIRED: Forecast horizon from user config (e.g., 6 for 6-hour forecast)
        training_days: int = None,        # OPTIONAL: Training period in days (for n_splits calculation)
        n_splits: int = None,             # OPTIONAL: Will be calculated if not provided
        test_size: int = None             # DEPRECATED: Will be calculated from forecast params
    ):
        """
        Initialize walk-forward validation with intelligent parameter calculation.

        Args:
            forecast_interval_minutes: REQUIRED - Data interval in minutes (e.g., 10)
            forecast_horizon_hours: REQUIRED - Forecast horizon in hours (e.g., 6)
            training_days: OPTIONAL - Training period in days (used to calculate optimal n_splits)
            n_splits: OPTIONAL - Number of folds. If not provided, will be calculated automatically
            test_size: DEPRECATED - Will be calculated automatically

        Calculation Logic:
            1. test_size = (forecast_horizon_hours * 60) / forecast_interval_minutes
            2. total_samples = (training_days * 24 * 60) / forecast_interval_minutes
            3. max_n_splits = (total_samples / test_size) - 1
            4. optimal_n_splits = min(max_n_splits, 10)  # Cap at 10 folds

        Example 1: 7 days, 10-min intervals, 6-hour forecast
            >>> validator = WalkForwardValidation(
            ...     forecast_interval_minutes=10,
            ...     forecast_horizon_hours=6,
            ...     training_days=7
            ... )
            >>> validator.test_size
            36  # (6 * 60) / 10
            >>> validator.n_splits
            10  # min((1008 / 36) - 1, 10) = min(27, 10) = 10

        Example 2: 3 days, 10-min intervals, 12-hour forecast
            >>> validator = WalkForwardValidation(
            ...     forecast_interval_minutes=10,
            ...     forecast_horizon_hours=12,
            ...     training_days=3
            ... )
            >>> validator.test_size
            72  # (12 * 60) / 10
            >>> validator.n_splits
            5  # min((432 / 72) - 1, 10) = min(5, 10) = 5
        """
        # Validation
        if forecast_interval_minutes is None or forecast_interval_minutes <= 0:
            raise ValueError("forecast_interval_minutes is required and must be > 0")

        if forecast_horizon_hours is None or forecast_horizon_hours <= 0:
            raise ValueError("forecast_horizon_hours is required and must be > 0")

        self.forecast_interval_minutes = forecast_interval_minutes
        self.forecast_horizon_hours = forecast_horizon_hours
        self.training_days = training_days

        # Calculate test_size from forecast configuration
        if test_size is not None:
            # Legacy support
            self.test_size = test_size
            console.warn(
                f"⚠️  Using legacy test_size={test_size}. "
                f"Expected: {int((forecast_horizon_hours * 60) / forecast_interval_minutes)}"
            )
        else:
            self.test_size = int((forecast_horizon_hours * 60) / forecast_interval_minutes)
            console.info(
                f"✅ Calculated test_size: {self.test_size} periods "
                f"({forecast_interval_minutes}-min × {forecast_horizon_hours}h)"
            )

        # Calculate n_splits intelligently
        if n_splits is not None:
            # User provided n_splits
            self.n_splits = n_splits
            console.info(f"📌 Using user-provided n_splits: {n_splits}")
        elif training_days is not None:
            # Calculate optimal n_splits from training period
            total_samples = int((training_days * 24 * 60) / forecast_interval_minutes)
            max_n_splits = (total_samples // self.test_size) - 1

            # Cap n_splits between 3 and 10 for practical purposes
            self.n_splits = max(3, min(max_n_splits, 10))

            console.info(
                f"🧮 Auto-calculated n_splits: {self.n_splits} "
                f"(from {training_days}d = {total_samples} samples, max={max_n_splits})"
            )

            # Validation: ensure we have enough data
            min_required_samples = (self.n_splits + 1) * self.test_size
            if total_samples < min_required_samples:
                raise ValueError(
                    f"❌ Insufficient data for validation!\n"
                    f"   - Training days: {training_days}\n"
                    f"   - Total samples: {total_samples}\n"
                    f"   - Test size: {self.test_size} periods ({forecast_horizon_hours}h)\n"
                    f"   - Calculated n_splits: {self.n_splits}\n"
                    f"   - Required samples: {min_required_samples}\n"
                    f"   - Shortfall: {min_required_samples - total_samples} samples\n"
                    f"   💡 Solution: Increase training_days to {((min_required_samples * forecast_interval_minutes) / (24 * 60)):.1f} days or reduce forecast_horizon_hours"
                )
        else:
            # Default fallback
            self.n_splits = 5
            console.warn(
                f"⚠️  No training_days provided, using default n_splits=5. "
                f"This may not be optimal for your data!"
            )

    async def validate(
        self,
        data: pd.DataFrame,
        model_plugin: ModelPlugin
    ) -> Dict[str, float]:
        """
        Perform walk-forward validation with data quality checks and interpolation.

        Data Processing Steps:
            1. Sort by timestamp (ensures chronological order)
            2. Detect and fill missing timestamps
            3. Interpolate missing values (time-ordered)
            4. Validate data constraints
            5. Execute walk-forward cross-validation

        Constraints:
            - Data must be time-ordered
            - No duplicate timestamps
            - All gaps filled via interpolation
            - Sufficient data for n_splits folds
            - min_required_samples = (n_splits + 1) * test_size

        If the model plugin has an evaluate() method, use that instead of
        manual walk-forward validation (which can fail for some models like Prophet).
        """
        console.log(f"🔍 [DEBUG] WalkForwardValidation.validate() called for {model_plugin.get_name()}")
        console.log(f"🔍 [DEBUG] Data shape: {data.shape}, columns: {data.columns.tolist()}")

        # ========================================================================
        # STEP 1: Data Quality Checks and Preprocessing
        # ========================================================================

        console.info("📋 Data Quality Checks:")

        # 1.1 Check for timestamp column
        if 'timestamp' not in data.columns:
            raise ValueError(
                "❌ Data missing required 'timestamp' column!\n"
                "   Required columns: ['timestamp', 'value']"
            )

        # 1.2 Sort by timestamp (REQUIRED for time-series validation)
        data = data.sort_values('timestamp').reset_index(drop=True)
        console.info(f"   ✅ Data sorted by timestamp: {len(data)} rows")

        # 1.3 Check for duplicates
        duplicates = data['timestamp'].duplicated().sum()
        if duplicates > 0:
            console.warn(f"   ⚠️  Found {duplicates} duplicate timestamps - removing duplicates")
            data = data.drop_duplicates(subset=['timestamp'], keep='first').reset_index(drop=True)

        # 1.4 Detect missing timestamps and interpolate
        if len(data) >= 2:
            # Calculate expected interval
            time_diffs = data['timestamp'].diff().dropna()
            expected_interval = time_diffs.mode()[0] if len(time_diffs) > 0 else pd.Timedelta(minutes=self.forecast_interval_minutes)

            # Generate complete time range
            start_time = data['timestamp'].min()
            end_time = data['timestamp'].max()
            expected_times = pd.date_range(
                start=start_time,
                end=end_time,
                freq=expected_interval
            )

            original_len = len(data)
            expected_len = len(expected_times)
            missing_count = expected_len - original_len

            if missing_count > 0:
                console.warn(
                    f"   ⚠️  Detected {missing_count} missing timestamps "
                    f"({(missing_count/expected_len)*100:.1f}% of expected data)"
                )

                # Create complete DataFrame with all timestamps
                complete_df = pd.DataFrame({'timestamp': expected_times})
                data = complete_df.merge(data, on='timestamp', how='left')

                # Interpolate missing values (time-ordered linear interpolation)
                if 'value' in data.columns:
                    missing_values = data['value'].isna().sum()
                    if missing_values > 0:
                        console.info(f"   🔧 Interpolating {missing_values} missing values (linear method)")
                        data['value'] = data['value'].interpolate(method='linear', limit_direction='both')

                        # If still NaN at boundaries, forward/backward fill
                        if data['value'].isna().sum() > 0:
                            data['value'] = data['value'].fillna(method='ffill').fillna(method='bfill')

                console.info(f"   ✅ Data filled: {original_len} → {len(data)} rows")
            else:
                console.info(f"   ✅ No missing timestamps detected")

        # 1.5 Final validation checks
        if data['value'].isna().sum() > 0:
            raise ValueError(
                f"❌ Data still contains {data['value'].isna().sum()} NaN values after interpolation!\n"
                "   Cannot proceed with validation."
            )

        # ========================================================================
        # STEP 2: Constraint Validation
        # ========================================================================

        console.info("🔒 Constraint Validation:")

        actual_samples = len(data)
        min_required_samples = (self.n_splits + 1) * self.test_size

        console.info(f"   • Forecast config: {self.forecast_interval_minutes}-min intervals, {self.forecast_horizon_hours}h horizon")
        console.info(f"   • Test size: {self.test_size} periods (= {self.forecast_horizon_hours}h)")
        console.info(f"   • Number of folds: {self.n_splits}")
        console.info(f"   • Actual samples: {actual_samples}")
        console.info(f"   • Required samples: {min_required_samples} (= ({self.n_splits} + 1) × {self.test_size})")

        if actual_samples < min_required_samples:
            # Calculate how much more data is needed
            shortage = min_required_samples - actual_samples
            shortage_days = (shortage * self.forecast_interval_minutes) / (24 * 60)

            raise ValueError(
                f"❌ CONSTRAINT VIOLATION: Insufficient data for {self.n_splits}-fold validation!\n"
                f"\n"
                f"Current Configuration:\n"
                f"   • Training data: {actual_samples} samples\n"
                f"   • Forecast horizon: {self.forecast_horizon_hours}h ({self.test_size} periods)\n"
                f"   • Validation folds: {self.n_splits}\n"
                f"\n"
                f"Constraint Formula:\n"
                f"   required_samples = (n_splits + 1) × test_size\n"
                f"   {min_required_samples} = ({self.n_splits} + 1) × {self.test_size}\n"
                f"\n"
                f"Data Shortage:\n"
                f"   • Missing: {shortage} samples ({shortage_days:.1f} days)\n"
                f"\n"
                f"Solutions:\n"
                f"   1. Increase training period to {self.training_days + shortage_days:.1f} days\n"
                f"   2. Reduce forecast_horizon_hours (currently {self.forecast_horizon_hours}h)\n"
                f"   3. Increase forecast_interval_minutes (currently {self.forecast_interval_minutes}min)\n"
                f"   4. Reduce n_splits (currently {self.n_splits}, minimum 3)\n"
            )

        # Check if data divides evenly
        remainder = (actual_samples - self.test_size) % self.test_size
        if remainder != 0:
            console.warn(
                f"   ⚠️  Dataset doesn't divide evenly: "
                f"{actual_samples} samples with test_size={self.test_size} "
                f"leaves remainder of {remainder} samples"
            )

        console.info(f"   ✅ All constraints satisfied - proceeding with validation")

        # ========================================================================
        # STEP 3: Execute Validation
        # ========================================================================

        # Check if model has its own evaluate() method
        has_evaluate = hasattr(model_plugin, 'evaluate')
        is_callable = callable(getattr(model_plugin, 'evaluate', None)) if has_evaluate else False
        console.log(f"🔍 [DEBUG] Model has evaluate()? {has_evaluate}, Is callable? {is_callable}")

        if has_evaluate and is_callable:
            console.info(f"   Using {model_plugin.get_name()} built-in evaluate() method")
            try:
                console.log(f"🔍 [DEBUG] Calling {model_plugin.get_name()}.evaluate() with n_windows={self.n_splits}, horizon={self.test_size}")
                # ✅ PASS forecast configuration to evaluate()
                metrics = await model_plugin.evaluate(
                    data,
                    n_windows=self.n_splits,
                    horizon=self.test_size  # Use calculated test_size from forecast config
                )

                console.log(f"🔍 [DEBUG] evaluate() returned: type={type(metrics)}, keys={list(metrics.keys()) if isinstance(metrics, dict) else 'N/A'}")

                if metrics:
                    console.log(f"🔍 [DEBUG] Metrics content:")
                    for key, value in metrics.items():
                        if key == 'validation_data':
                            console.log(f"🔍 [DEBUG]   - {key}: {len(value)} items")
                        else:
                            console.log(f"🔍 [DEBUG]   - {key}: {value}")

                # If evaluate() returned valid metrics, use them
                # Check for presence of validation_data which indicates successful evaluation
                if metrics and 'validation_data' in metrics and len(metrics.get('validation_data', [])) > 0:
                    console.info(f"   {model_plugin.get_name()} evaluate() succeeded: {len(metrics['validation_data'])} validation points")
                    console.log(f"🔍 [DEBUG] OK Returning metrics from built-in evaluate()")
                    return metrics
                else:
                    console.warn(f"   {model_plugin.get_name()} evaluate() returned empty validation_data, falling back to walk-forward")
                    console.log(f"🔍 [DEBUG] ⚠️ validation_data check failed - falling back")
            except Exception as e:
                console.warn(f"   {model_plugin.get_name()} evaluate() failed: {e}, falling back to walk-forward")
                console.log(f"🔍 [DEBUG] FAIL Exception in evaluate(): {type(e).__name__}: {str(e)}")
                import traceback
                console.log(f"🔍 [DEBUG] Traceback:\n{traceback.format_exc()}")

        console.log(f"🔍 [DEBUG] Falling back to manual walk-forward validation")

        # Fallback to manual walk-forward validation
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, mean_absolute_error

        tscv = TimeSeriesSplit(n_splits=self.n_splits, test_size=self.test_size)

        mapes = []
        rmses = []
        maes = []

        for fold, (train_idx, test_idx) in enumerate(tscv.split(data)):
            train_data = data.iloc[train_idx]
            test_data = data.iloc[test_idx]

            # Train on fold
            await model_plugin.train(train_data)

            # Predict
            forecast = await model_plugin.predict(len(test_data))

            # Extract predictions (different for each model type)
            if isinstance(model_plugin, AutoARIMAPlugin):
                y_pred = forecast['AutoARIMA'].values
            elif isinstance(model_plugin, ProphetPlugin):
                y_pred = forecast['yhat'].iloc[-len(test_data):].values
            else:
                continue  # Skip XGBoost for now

            y_true = test_data['value'].values

            # Calculate metrics
            mapes.append(mean_absolute_percentage_error(y_true, y_pred) * 100)
            rmses.append(mean_squared_error(y_true, y_pred, squared=False))
            maes.append(mean_absolute_error(y_true, y_pred))

        # Handle case when no validation folds were generated
        if not mapes or not rmses or not maes:
            console.warn("No validation folds completed - returning zero metrics")
            return {
                'mape': 0.0,
                'rmse': 0.0,
                'mae': 0.0
            }

        return {
            'mape': sum(mapes) / len(mapes),
            'rmse': sum(rmses) / len(rmses),
            'mae': sum(maes) / len(maes)
        }


# ============================================================================
# Pipeline Builder with Method Chaining
# ============================================================================

class TrainingPipeline:
    """
    Flexible training pipeline with method chaining.

    Supports:
    - Fluent API for configuration
    - Plugin-based model registration
    - Dynamic pipeline creation from config
    - Reusable components
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.feature_service = FeatureEngineeringService(session)

        # Pipeline configuration
        self._data_source = {}
        self._feature_config = {}
        self._models: List[ModelPlugin] = []
        self._validation: Optional[ValidationStrategy] = None
        self._metrics: List[str] = ['mape', 'rmse', 'mae']

        # Data cache
        self._raw_data: Optional[pd.DataFrame] = None
        self._processed_data: Optional[pd.DataFrame] = None

    # ========================================================================
    # Method Chaining API
    # ========================================================================

    def set_data_source(self, tag_name: str, days: int = 30, start_time: Optional[datetime] = None) -> 'TrainingPipeline':
        """Set data source configuration"""
        self._data_source = {
            'tag_name': tag_name,
            'days': days,
            'start_time': start_time
        }
        return self

    def add_feature_engineering(
        self,
        lags: Optional[List[int]] = None,
        rolling: Optional[List[int]] = None,
        time_features: bool = True
    ) -> 'TrainingPipeline':
        """Add feature engineering configuration"""
        self._feature_config = {
            'lags': lags or [1, 6, 24],
            'rolling': rolling or [6, 24],
            'time_features': time_features
        }
        return self

    def add_model(self, model_type: str, **params) -> 'TrainingPipeline':
        """Add a model plugin to the pipeline"""
        # Plugin registry
        model_registry = {
            'auto_arima': AutoARIMAPlugin,
            'prophet': ProphetPlugin,
            'xgboost': XGBoostPlugin
        }

        if model_type not in model_registry:
            raise ValueError(f"Unknown model type: {model_type}")

        plugin = model_registry[model_type](**params)
        self._models.append(plugin)
        console.info(f"➕ Added model: {plugin.get_name()}")
        return self

    def add_validation(self, validation_type: str, **params) -> 'TrainingPipeline':
        """Add validation strategy"""
        if validation_type == 'walk_forward':
            self._validation = WalkForwardValidation(**params)
        else:
            raise ValueError(f"Unknown validation type: {validation_type}")

        console.info(f"➕ Added validation: {validation_type}")
        return self

    def set_metrics(self, metrics: List[str]) -> 'TrainingPipeline':
        """Set evaluation metrics"""
        self._metrics = metrics
        return self

    def build(self) -> 'TrainingPipeline':
        """Finalize pipeline configuration"""
        console.info("🔨 Pipeline built successfully")
        console.info(f"   Data: {self._data_source.get('tag_name', 'N/A')}")
        console.info(f"   Models: {len(self._models)}")
        console.info(f"   Validation: {'Yes' if self._validation else 'No'}")
        return self

    # ========================================================================
    # Configuration-based API
    # ========================================================================

    def from_config(self, config: Dict[str, Any]) -> 'TrainingPipeline':
        """Create pipeline from configuration dictionary"""
        # Data source
        if 'data_source' in config:
            self.set_data_source(**config['data_source'])

        # Feature engineering
        if 'feature_engineering' in config:
            self.add_feature_engineering(**config['feature_engineering'])

        # Models
        if 'models' in config:
            for model_cfg in config['models']:
                self.add_model(model_cfg['type'], **model_cfg.get('params', {}))

        # Validation
        if 'validation' in config:
            self.add_validation(
                config['validation']['type'],
                **config['validation'].get('params', {})
            )

        # Metrics
        if 'metrics' in config:
            self.set_metrics(config['metrics'])

        return self.build()

    # ========================================================================
    # Execution
    # ========================================================================

    async def execute(self) -> Dict[str, Any]:
        """Execute the training pipeline"""
        console.info("🚀 Executing training pipeline...")

        # Step 1: Load data
        console.info("📥 Step 1: Loading data...")
        await self._load_data()

        # Step 2: Feature engineering
        console.info("⚙️  Step 2: Feature engineering...")
        await self._apply_feature_engineering()

        # Step 3: Train models
        console.info("🎓 Step 3: Training models...")
        results = {}

        for model in self._models:
            console.info(f"   Training {model.get_name()}...")

            # Train
            await model.train(self._processed_data)

            # Validate if strategy provided
            if self._validation:
                console.info(f"   Validating {model.get_name()}...")
                metrics = await self._validation.validate(self._processed_data, model)
                results[model.get_name()] = {
                    'model': model,
                    'metrics': metrics
                }
                console.info(f"   ✅ {model.get_name()} - MAPE: {metrics['mape']:.2f}%")
            else:
                results[model.get_name()] = {
                    'model': model,
                    'metrics': {}
                }

        console.info("✅ Pipeline execution complete")
        return results

    # ========================================================================
    # Internal Methods
    # ========================================================================

    async def _load_data(self):
        """Load raw data from database"""
        from sqlalchemy import text

        tag_name = self._data_source['tag_name']
        days = self._data_source['days']
        end_time = datetime.now(KST)
        start_time = end_time - timedelta(days=days)

        query = text("""
            SELECT
                ts AT TIME ZONE 'Asia/Seoul' as timestamp,
                value
            FROM influx_hist
            WHERE tag_name = :tag_name
              AND ts >= :start_time
              AND ts < :end_time
              AND value IS NOT NULL
            ORDER BY ts
        """)

        rows = (await self.session.execute(
            query,
            {'tag_name': tag_name, 'start_time': start_time, 'end_time': end_time}
        )).mappings().all()

        self._raw_data = pd.DataFrame([dict(r) for r in rows])
        console.info(f"   Loaded {len(self._raw_data)} rows for {tag_name}")

    async def _apply_feature_engineering(self):
        """Apply feature engineering transformations"""
        if not self._feature_config:
            self._processed_data = self._raw_data
            return

        df = self._raw_data.copy()

        # Lag features
        if self._feature_config.get('lags'):
            for lag in self._feature_config['lags']:
                df[f'lag_{lag}h'] = df['value'].shift(lag)

        # Rolling features
        if self._feature_config.get('rolling'):
            for window in self._feature_config['rolling']:
                df[f'rolling_mean_{window}h'] = df['value'].rolling(window).mean()
                df[f'rolling_std_{window}h'] = df['value'].rolling(window).std()

        # Time-based features
        if self._feature_config.get('time_features'):
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            df['month'] = df['timestamp'].dt.month

        # Drop NaN rows created by lag/rolling
        df = df.dropna()

        self._processed_data = df
        console.info(f"   Features: {list(df.columns)}")
        console.info(f"   Samples after feature engineering: {len(df)}")


# ============================================================================
# Plugin Registry for Easy Extension
# ============================================================================

class PluginRegistry:
    """Global registry for custom model plugins"""

    _registry: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, plugin_class: type):
        """Register a new model plugin"""
        if not issubclass(plugin_class, ModelPlugin):
            raise TypeError("Plugin must inherit from ModelPlugin")

        cls._registry[name] = plugin_class
        console.info(f"📦 Registered plugin: {name}")

    @classmethod
    def get(cls, name: str) -> type:
        """Get plugin class by name"""
        return cls._registry.get(name)

    @classmethod
    def list_plugins(cls) -> List[str]:
        """List all registered plugins"""
        return list(cls._registry.keys())
