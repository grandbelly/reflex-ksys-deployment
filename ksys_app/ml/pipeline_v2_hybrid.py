"""
Hybrid Training Pipeline - Best of Both Worlds

통합 개선안:
1. 제 설계의 타입 안정성 + 플러그인 시스템
2. 제안하신 체인 패턴 + 전처리/후처리
3. 메타데이터 추적
4. 레지스트리 패턴으로 동적 확장

Example:
    # Method chaining with preprocessing
    pipeline = (TrainingPipelineV2(session)
        .set_data_source("INLET_PRESSURE", days=30)
        .add_preprocessing()
            .interpolate(method='linear')
            .remove_outliers(threshold=3.0)
            .scale(method='standard')
        .done()
        .add_feature_engineering()
            .add_lag([1, 6, 24])
            .add_rolling([6, 24])
            .add_temporal(['hour', 'dayofweek'])
        .done()
        .add_model("auto_arima", seasonal=True)
        .add_model("prophet")
        .add_validation("walk_forward", n_splits=5)
        .build()
    )

    result = await pipeline.execute()
    print(result.metadata)  # Full pipeline metadata
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import pytz
from reflex.utils import console
from sqlalchemy.ext.asyncio import AsyncSession

from ksys_app.services.feature_engineering_service import FeatureEngineeringService


KST = pytz.timezone('Asia/Seoul')


# ============================================================================
# Pipeline Metadata (추적 및 디버깅용)
# ============================================================================

@dataclass
class PipelineMetadata:
    """파이프라인 실행 메타데이터"""

    # Data info
    tag_name: str = ""
    data_start: Optional[datetime] = None
    data_end: Optional[datetime] = None
    raw_samples: int = 0
    processed_samples: int = 0

    # Preprocessing steps
    preprocessing_steps: List[str] = field(default_factory=list)
    outliers_removed: int = 0
    interpolated_gaps: int = 0

    # Detailed preprocessing statistics
    preprocessing_details: Dict[str, Any] = field(default_factory=dict)
    # Example: {
    #   "outliers": {"removed": 10, "percentage": 1.5, "threshold": 3.0, "method": "z-score"},
    #   "interpolation": {"gaps_filled": 5, "method": "linear", "largest_gap": 3},
    # }

    # Feature engineering
    features_created: List[str] = field(default_factory=list)
    original_features: int = 0
    final_features: int = 0

    # Model training
    models_trained: List[str] = field(default_factory=list)
    training_duration: float = 0.0

    # Results
    best_model: str = ""
    best_mape: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'tag_name': self.tag_name,
            'data_start': self.data_start.isoformat() if self.data_start else None,
            'data_end': self.data_end.isoformat() if self.data_end else None,
            'raw_samples': self.raw_samples,
            'processed_samples': self.processed_samples,
            'preprocessing_steps': self.preprocessing_steps,
            'outliers_removed': self.outliers_removed,
            'features_created': self.features_created,
            'models_trained': self.models_trained,
            'best_model': self.best_model,
            'best_mape': self.best_mape
        }


# ============================================================================
# Preprocessing Chain (제안하신 설계의 PreprocessorChain)
# ============================================================================

class PreprocessingStep(ABC):
    """전처리 단계 베이스 클래스"""

    @abstractmethod
    async def apply(self, df: pd.DataFrame, metadata: PipelineMetadata) -> pd.DataFrame:
        """전처리 적용"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """단계 이름"""
        pass


class InterpolateStep(PreprocessingStep):
    """결측치 보간"""

    def __init__(self, method: str = 'linear'):
        self.method = method

    async def apply(self, df: pd.DataFrame, metadata: PipelineMetadata) -> pd.DataFrame:
        before_count = df['value'].isna().sum()

        # Find gap sizes before interpolation
        gaps = df['value'].isna()
        gap_sizes = []
        current_gap = 0
        for is_gap in gaps:
            if is_gap:
                current_gap += 1
            else:
                if current_gap > 0:
                    gap_sizes.append(current_gap)
                current_gap = 0
        if current_gap > 0:
            gap_sizes.append(current_gap)

        # Perform interpolation
        df['value'] = df['value'].interpolate(method=self.method)
        after_count = df['value'].isna().sum()

        filled_count = before_count - after_count
        metadata.interpolated_gaps = filled_count
        metadata.preprocessing_steps.append(f"interpolate_{self.method}")

        # Store detailed statistics
        metadata.preprocessing_details['interpolation'] = {
            "gaps_filled": filled_count,
            "method": self.method,
            "total_gaps": len(gap_sizes),
            "largest_gap": max(gap_sizes) if gap_sizes else 0,
            "average_gap_size": sum(gap_sizes) / len(gap_sizes) if gap_sizes else 0,
            "percentage": (filled_count / len(df) * 100) if len(df) > 0 else 0,
        }

        console.info(f"   ✓ Interpolated {filled_count} gaps using {self.method} (largest: {metadata.preprocessing_details['interpolation']['largest_gap']})")
        return df

    def get_name(self) -> str:
        return f"interpolate_{self.method}"


class RemoveOutliersStep(PreprocessingStep):
    """이상치 제거 (Z-score 기반)"""

    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold

    async def apply(self, df: pd.DataFrame, metadata: PipelineMetadata) -> pd.DataFrame:
        # Calculate statistics before outlier removal
        mean_before = df['value'].mean()
        std_before = df['value'].std()

        z_scores = np.abs((df['value'] - mean_before) / std_before)
        before = len(df)
        df = df[z_scores < self.threshold].copy()
        after = len(df)

        removed_count = before - after
        metadata.outliers_removed = removed_count
        metadata.preprocessing_steps.append(f"remove_outliers_{self.threshold}")

        # Store detailed statistics
        metadata.preprocessing_details['outliers'] = {
            "removed": removed_count,
            "percentage": (removed_count / before * 100) if before > 0 else 0,
            "threshold": self.threshold,
            "method": "z-score",
            "mean_before": float(mean_before),
            "std_before": float(std_before),
            "mean_after": float(df['value'].mean()),
            "std_after": float(df['value'].std()),
        }

        console.info(f"   ✓ Removed {removed_count} outliers ({metadata.preprocessing_details['outliers']['percentage']:.2f}%)")
        return df

    def get_name(self) -> str:
        return f"remove_outliers_{self.threshold}"


class ScaleStep(PreprocessingStep):
    """스케일링"""

    def __init__(self, method: str = 'standard'):
        self.method = method

    async def apply(self, df: pd.DataFrame, metadata: PipelineMetadata) -> pd.DataFrame:
        if self.method == 'standard':
            df['value_scaled'] = (df['value'] - df['value'].mean()) / df['value'].std()
        elif self.method == 'minmax':
            df['value_scaled'] = (df['value'] - df['value'].min()) / (df['value'].max() - df['value'].min())

        metadata.preprocessing_steps.append(f"scale_{self.method}")
        console.info(f"   ✓ Scaled with {self.method}")
        return df

    def get_name(self) -> str:
        return f"scale_{self.method}"


class PreprocessingChain:
    """전처리 체인 빌더"""

    def __init__(self, pipeline: 'TrainingPipelineV2'):
        self.pipeline = pipeline
        self.steps: List[PreprocessingStep] = []

    def interpolate(self, method: str = 'linear') -> 'PreprocessingChain':
        self.steps.append(InterpolateStep(method))
        return self

    def remove_outliers(self, threshold: float = 3.0) -> 'PreprocessingChain':
        self.steps.append(RemoveOutliersStep(threshold))
        return self

    def scale(self, method: str = 'standard') -> 'PreprocessingChain':
        self.steps.append(ScaleStep(method))
        return self

    def done(self) -> 'TrainingPipelineV2':
        """체인 완료 - 파이프라인으로 복귀"""
        self.pipeline._preprocessing_steps = self.steps
        return self.pipeline


# ============================================================================
# Feature Engineering Chain
# ============================================================================

class FeatureEngineeringChain:
    """피처 엔지니어링 체인 빌더"""

    def __init__(self, pipeline: 'TrainingPipelineV2'):
        self.pipeline = pipeline
        self.config = {}

    def add_lag(self, periods: List[int]) -> 'FeatureEngineeringChain':
        self.config['lags'] = periods
        return self

    def add_rolling(self, windows: List[int]) -> 'FeatureEngineeringChain':
        self.config['rolling'] = windows
        return self

    def add_temporal(self, components: List[str]) -> 'FeatureEngineeringChain':
        self.config['temporal'] = components
        return self

    def add_fourier(self, periods: List[int]) -> 'FeatureEngineeringChain':
        self.config['fourier'] = periods
        return self

    def done(self) -> 'TrainingPipelineV2':
        """체인 완료 - 파이프라인으로 복귀"""
        self.pipeline._feature_config = self.config
        return self.pipeline


# ============================================================================
# Model Plugin (기존 설계 유지)
# ============================================================================

class ModelPlugin(ABC):
    """모델 플러그인 베이스 클래스"""

    def __init__(self, **params):
        self.params = params
        self.model = None

    @abstractmethod
    async def train(self, data: pd.DataFrame) -> Any:
        pass

    @abstractmethod
    async def predict(self, horizon: int) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass


class AutoARIMAPlugin(ModelPlugin):
    """Auto ARIMA model plugin using statsforecast with diagnostics"""

    def __init__(self, **params):
        super().__init__(**params)
        self.training_data = None
        self.model_info = {}  # Store ARIMA parameters, residuals, etc.

    def get_name(self) -> str:
        return "auto_arima"

    async def train(self, data: pd.DataFrame) -> Any:
        """Train Auto ARIMA model with full diagnostics"""
        try:
            from statsforecast import StatsForecast
            from statsforecast.models import AutoARIMA
            from statsforecast.arima import arima_string

            # Prepare data for statsforecast
            df = data.copy()
            df['ds'] = df['timestamp']
            df['y'] = df['value']
            df['unique_id'] = 'series_1'

            # Store training data for later use
            self.training_data = df[['unique_id', 'ds', 'y']].copy()

            # Create model with season_length based on data frequency
            # Data is 10-minute intervals: 6 per hour * 24 hours = 144 for daily seasonality
            season_length = self.params.get('season_length', 144)  # Default: 10-min data with daily seasonality
            models = [AutoARIMA(season_length=season_length)]
            sf = StatsForecast(models=models, freq='10T', n_jobs=1)  # 10T = 10 minute frequency

            # Fit model
            console.info(f"Training {self.get_name()} with season_length={season_length}...")
            sf.fit(self.training_data)

            self.model = sf

            # Extract model diagnostics
            try:
                fitted_model = sf.fitted_[0, 0].model_

                # Get ARIMA string representation (e.g., "ARIMA(4,0,3)(0,1,1)[12]")
                arima_params = arima_string(fitted_model)
                self.model_info['arima_string'] = arima_params.strip()

                # Get model parameters
                self.model_info['arma'] = fitted_model.get('arma', None)
                self.model_info['aic'] = fitted_model.get('aic', None)
                self.model_info['bic'] = fitted_model.get('bic', None)
                self.model_info['aicc'] = fitted_model.get('aicc', None)
                self.model_info['sigma2'] = fitted_model.get('sigma2', None)

                # Get residuals for diagnostic plots
                residuals = fitted_model.get('residuals', None)
                if residuals is not None:
                    self.model_info['residuals'] = residuals
                    self.model_info['residuals_mean'] = float(np.mean(residuals))
                    self.model_info['residuals_std'] = float(np.std(residuals))

                console.info(f"✅ {self.get_name()} trained: {self.model_info['arima_string']}")
                console.info(f"   AIC: {self.model_info['aic']:.2f}, BIC: {self.model_info['bic']:.2f}")

            except Exception as e:
                console.warn(f"Could not extract model diagnostics: {e}")

            return self.model

        except ImportError:
            console.error("statsforecast not installed")
            raise
        except Exception as e:
            console.error(f"Error training AutoARIMA: {e}")
            raise

    async def predict(self, horizon: int, level: list = None) -> pd.DataFrame:
        """
        Generate predictions with confidence intervals

        Args:
            horizon: Number of periods to forecast
            level: List of confidence levels (e.g., [80, 95])
        """
        if self.model is None:
            raise ValueError("Model not trained")

        # Generate forecast with confidence intervals
        if level:
            forecast = self.model.predict(h=horizon, level=level)
            console.info(f"Forecast generated with {len(level)} confidence intervals")
        else:
            forecast = self.model.predict(h=horizon)

        return forecast

    def get_fitted_values(self) -> pd.DataFrame:
        """Get fitted values from training"""
        if self.model is None:
            raise ValueError("Model not trained")

        try:
            # statsforecast stores fitted values in fitted_ attribute
            # fitted_ is a DataFrame with columns: unique_id, ds, AutoARIMA (fitted values)
            if hasattr(self.model, 'fitted_'):
                fitted_df = self.model.fitted_
                console.debug(f"Found fitted values: {fitted_df.shape if fitted_df is not None else 'None'}")
                return fitted_df
            else:
                console.warn("Model has no fitted_ attribute")
                return None
        except Exception as e:
            console.warn(f"Could not get fitted values: {e}")
            return None

    async def evaluate(self, test_data: pd.DataFrame = None, n_windows: int = 3, horizon: int = None) -> dict:
        """
        Evaluate model performance with walk-forward validation

        Args:
            test_data: Test dataset (optional, uses training data if not provided)
            n_windows: Number of walk-forward windows
            horizon: Forecast horizon in periods (from forecast_config, e.g., 36 for 6h @ 10-min intervals)

        Returns:
            dict with MAE, MAPE, MASE, RMSE, SMAPE, train_mae
        """
        if self.model is None:
            raise ValueError("Model not trained")

        try:
            # Use training data if test data not provided
            data = test_data if test_data is not None else self.training_data

            if data is None or len(data) == 0:
                console.log("No data available for Auto-ARIMA evaluation")
                return {}

            # ✅ Convert column names if needed (timestamp→ds, value→y)
            data = data.copy()
            if 'timestamp' in data.columns and 'ds' not in data.columns:
                data['ds'] = data['timestamp']
            if 'value' in data.columns and 'y' not in data.columns:
                data['y'] = data['value']

            # Ensure required columns and unique_id
            if 'unique_id' not in data.columns:
                data['unique_id'] = 'series_1'

            # Ensure we have required columns
            if 'ds' not in data.columns or 'y' not in data.columns:
                console.error(f"Auto-ARIMA evaluate: missing required columns. Available: {data.columns.tolist()}")
                return {}

            # NOTE: statsforecast AutoARIMA does not provide fitted values
            # predict(h=n) forecasts FUTURE values, not in-sample fitted values
            # Therefore, train_mae cannot be accurately calculated for AutoARIMA
            # Unlike Prophet/XGBoost which support in-sample predictions
            train_mae = None
            console.info("   ⚠️ Train MAE not calculated for AutoARIMA (statsforecast limitation)")

            # Perform cross-validation with walk-forward
            # ✅ Use user-configured horizon (e.g., 36 for 6h @ 10-min) instead of hardcoded 24
            if horizon is None:
                # Fallback to old behavior (for backward compatibility)
                horizon = min(24, len(data) // (n_windows + 1))
                console.warn(f"⚠️ No horizon provided, using fallback: {horizon}")

            # ✅ FIX: Validate that we have enough data for walk-forward validation
            # Required data: (n_windows * step_size) + horizon
            # Use horizon as step_size for non-overlapping windows
            required_data_points = (n_windows * horizon) + horizon
            if len(data) < required_data_points:
                console.warn(f"⚠️ Insufficient data for walk-forward validation")
                console.warn(f"   Required: {required_data_points} points ({n_windows} windows × {horizon} step + {horizon} test)")
                console.warn(f"   Available: {len(data)} points")
                # Reduce n_windows to fit available data
                max_windows = max(1, (len(data) - horizon) // horizon)
                if max_windows < n_windows:
                    n_windows = max_windows
                    console.warn(f"   Reducing to {n_windows} windows to fit available data")
                if n_windows < 1:
                    console.error("Not enough data for even 1 validation window")
                    return {}

            console.info(f"Evaluating with {n_windows} windows, horizon={horizon}, step_size={horizon}")

            cv_results = self.model.cross_validation(
                df=data[['unique_id', 'ds', 'y']],  # Only required columns
                h=horizon,
                step_size=horizon,  # Use same as horizon for non-overlapping windows
                n_windows=n_windows
            )

            # 🔍 DEBUG: Check cv_results
            console.debug(f"cv_results shape: {cv_results.shape if cv_results is not None else 'None'}")
            console.debug(f"cv_results columns: {cv_results.columns.tolist() if cv_results is not None else 'None'}")
            if cv_results is not None and len(cv_results) > 0:
                console.debug(f"cv_results first 3 rows:\n{cv_results.head(3)}")
                console.debug(f"cv_results unique cutoffs: {cv_results['cutoff'].unique() if 'cutoff' in cv_results.columns else 'No cutoff'}")

            # Calculate metrics
            actual = cv_results['y'].values
            predicted = cv_results['AutoARIMA'].values

            console.debug(f"actual shape: {actual.shape}, predicted shape: {predicted.shape}")
            console.debug(f"actual sample: {actual[:5]}")
            console.debug(f"predicted sample: {predicted[:5]}")

            # MAE - Mean Absolute Error
            mae = float(np.mean(np.abs(actual - predicted)))

            # MAPE - Mean Absolute Percentage Error
            mape = float(np.mean(np.abs((actual - predicted) / actual)) * 100)

            # RMSE - Root Mean Squared Error
            rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))

            # SMAPE - Symmetric Mean Absolute Percentage Error
            smape = float(np.mean(2 * np.abs(actual - predicted) / (np.abs(actual) + np.abs(predicted))) * 100)

            # MASE - Mean Absolute Scaled Error (using naive forecast as baseline)
            naive_error = np.mean(np.abs(np.diff(actual)))
            mase = float(mae / naive_error) if naive_error > 0 else 0.0

            # Extract actual vs predicted data for visualization
            validation_data = []
            for idx, row in cv_results.iterrows():
                validation_data.append({
                    "ds": row['ds'].isoformat() if hasattr(row['ds'], 'isoformat') else str(row['ds']),
                    "actual": float(row['y']),
                    "predicted": float(row['AutoARIMA']),
                })

            # ✅ NEW: Extract fold-by-fold results for detailed analysis
            fold_results = []
            if 'cutoff' in cv_results.columns:
                # Group by cutoff (each cutoff represents one fold)
                for fold_num, (cutoff_date, fold_data) in enumerate(cv_results.groupby('cutoff'), start=1):
                    fold_actual = fold_data['y'].values
                    fold_pred = fold_data['AutoARIMA'].values

                    # Calculate metrics for this fold
                    fold_mae = float(np.mean(np.abs(fold_actual - fold_pred)))
                    fold_mape = float(np.mean(np.abs((fold_actual - fold_pred) / fold_actual)) * 100)
                    fold_rmse = float(np.sqrt(np.mean((fold_actual - fold_pred) ** 2)))

                    # Extract fold validation data
                    fold_validation_data = [
                        {
                            "ds": row['ds'].isoformat() if hasattr(row['ds'], 'isoformat') else str(row['ds']),
                            "actual": float(row['y']),
                            "predicted": float(row['AutoARIMA']),
                        }
                        for _, row in fold_data.iterrows()
                    ]

                    # Format values for display (2 decimal places for metrics, date-only for cutoff)
                    cutoff_str = cutoff_date.isoformat() if hasattr(cutoff_date, 'isoformat') else str(cutoff_date)
                    if 'T' in cutoff_str:
                        cutoff_str = cutoff_str.split('T')[0]  # Extract date part only

                    fold_results.append({
                        "fold": fold_num,
                        "cutoff": cutoff_str,
                        "n_points": len(fold_data),
                        "mae": round(fold_mae, 2),
                        "mape": round(fold_mape, 2),
                        "rmse": round(fold_rmse, 2),
                        "validation_data": fold_validation_data
                    })

                console.info(f"   Extracted {len(fold_results)} fold results for detailed analysis")

            metrics = {
                "train_mae": train_mae,  # Add train MAE
                "mae": mae,
                "mape": mape,
                "mase": mase,
                "rmse": rmse,
                "smape": smape,
                "n_windows": n_windows,
                "horizon": horizon,
                "n_predictions": len(actual),
                "validation_data": validation_data,  # Add actual vs predicted pairs
                "fold_results": fold_results,  # ✅ NEW: Fold-by-fold results for detailed view
            }

            train_mae_str = f"{train_mae:.2f}" if train_mae is not None else "N/A"
            console.info(f"   Train MAE: {train_mae_str}")
            console.info(f"   Val MAE: {mae:.2f}, MAPE: {mape:.2f}%, RMSE: {rmse:.2f}")
            console.info(f"   Validation data: {len(validation_data)} points for chart")

            return metrics

        except Exception as e:
            console.warn(f"Could not evaluate model: {e}")
            return {}

    def get_residuals_analysis(self) -> dict:
        """
        Analyze residuals for diagnostic purposes
        
        Returns:
            dict with residuals statistics and histogram data
        """
        if self.model is None or 'residuals' not in self.model_info:
            return {}
        
        try:
            residuals = self.model_info['residuals']
            
            # Basic statistics
            residuals_mean = float(np.mean(residuals))
            residuals_std = float(np.std(residuals))
            residuals_min = float(np.min(residuals))
            residuals_max = float(np.max(residuals))
            
            # Normality tests
            from scipy import stats
            skewness = float(stats.skew(residuals))
            kurtosis = float(stats.kurtosis(residuals))
            
            # Q-Q plot data (quantiles)
            theoretical_quantiles = stats.norm.ppf(np.linspace(0.01, 0.99, 50))
            sample_quantiles = np.percentile(residuals, np.linspace(1, 99, 50))
            
            # Histogram data (bins)
            hist_counts, hist_edges = np.histogram(residuals, bins=20)
            histogram_data = [
                {
                    "bin_start": float(hist_edges[i]),
                    "bin_end": float(hist_edges[i+1]),
                    "count": int(hist_counts[i]),
                    "bin_center": float((hist_edges[i] + hist_edges[i+1]) / 2)
                }
                for i in range(len(hist_counts))
            ]
            
            # ACF data (autocorrelation function)
            from statsmodels.tsa.stattools import acf
            acf_values = acf(residuals, nlags=24, fft=False)
            acf_data = [
                {"lag": i, "acf": float(acf_values[i])}
                for i in range(len(acf_values))
            ]
            
            analysis = {
                "statistics": {
                    "mean": residuals_mean,
                    "std": residuals_std,
                    "min": residuals_min,
                    "max": residuals_max,
                    "skewness": skewness,
                    "kurtosis": kurtosis,
                },
                "qq_plot": {
                    "theoretical": theoretical_quantiles.tolist(),
                    "sample": sample_quantiles.tolist(),
                },
                "histogram": histogram_data,
                "acf": acf_data,
            }
            
            console.info(f"Residuals analysis: mean={residuals_mean:.4f}, std={residuals_std:.4f}")
            
            return analysis
            
        except Exception as e:
            console.warn(f"Could not analyze residuals: {e}")
            return {}

    def get_diagnostics(self) -> dict:
        """Return model diagnostics for visualization"""
        return self.model_info


class ProphetPlugin(ModelPlugin):
    """Prophet model plugin"""

    def __init__(self, **params):
        super().__init__(**params)
        self.training_data = None

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

            # Store training data for evaluation
            self.training_data = df[['ds', 'y']].copy()
            
            self.model = model
            # 예측 구간 생성기 학습
            from ksys_app.ml.prediction_intervals import create_interval_generator

            try:
                self.interval_generator = create_interval_generator(
                    method=self.interval_method,
                    **self.interval_params
                )

                if self.interval_method == 'conformal':
                    # Conformal Prediction: 교차 검증으로 conformity scores 계산
                    self.interval_generator.fit(model, X.values, y)
                    console.info("✅ Conformal prediction intervals fitted")

                elif self.interval_method == 'bootstrap':
                    # Bootstrap: 학습 데이터 잔차 저장
                    y_pred = model.predict(X.values)
                    self.interval_generator.fit(y, y_pred)
                    console.info("✅ Bootstrap residuals collected")

                elif self.interval_method == 'quantile':
                    # Quantile Regression: 분위수별 모델 학습
                    import xgboost as xgb
                    self.interval_generator.fit(
                        xgb.XGBRegressor,
                        X.values,
                        y,
                        model_params=self.params
                    )
                    console.info("✅ Quantile regression models trained")

            except Exception as e:
                console.warn(f"Interval generator fitting failed: {e}")
                self.interval_generator = None

            console.info(f"✅ {self.get_name()} trained successfully")
            return self.model

        except ImportError:
            console.error("prophet not installed")
            raise
        except Exception as e:
            console.error(f"Error training Prophet: {e}")
            raise

    async def predict(self, horizon: int, level: list = None) -> pd.DataFrame:
        """Generate predictions with confidence intervals

        Args:
            horizon: Number of 10-minute periods to forecast
            level: List of confidence levels (ignored for Prophet, uses default 80%)
        """
        if self.model is None:
            raise ValueError("Model not trained")

        # Use 10-minute frequency to match training data (influx_agg_10m)
        future = self.model.make_future_dataframe(periods=horizon, freq='10T')
        forecast = self.model.predict(future)
        
        # Prophet uses yhat_lower/yhat_upper for 80% confidence by default
        result = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(horizon).copy()
        
        # Rename to match expected format
        result = result.rename(columns={
            'yhat': 'Prophet',
            'yhat_lower': 'Prophet-lo-80',
            'yhat_upper': 'Prophet-hi-80'
        })
        
        # For 95% confidence, use wider interval (approximate)
        result['Prophet-lo-95'] = result['Prophet-lo-80'] * 1.2 - result['Prophet'] * 0.2
        result['Prophet-hi-95'] = result['Prophet-hi-80'] * 1.2 - result['Prophet'] * 0.2
        
        return result

    async def evaluate(self, test_data: pd.DataFrame = None, n_windows: int = 3, horizon: int = None) -> dict:
        """
        Evaluate Prophet model using simple train/test split

        Note: Prophet's cross_validation is unreliable with limited data,
        so we use a simple holdout validation approach instead.

        Args:
            test_data: Test dataset (optional, uses training data if not provided)
            n_windows: Number of walk-forward windows (ignored for simple split)
            horizon: Forecast horizon in periods (from forecast_config, used for validation split)

        Returns:
            dict with MAE, MAPE, MASE, RMSE, SMAPE, train_mae, validation_data
        """
        if self.model is None:
            raise ValueError("Model not trained")

        try:
            from prophet import Prophet

            # Use training data if test data not provided
            data = test_data if test_data is not None else self.training_data

            if data is None or len(data) == 0:
                console.log("No data available for Prophet evaluation")
                return {}

            # ✅ Convert column names if needed (timestamp→ds, value→y)
            data = data.copy()
            if 'timestamp' in data.columns and 'ds' not in data.columns:
                data['ds'] = data['timestamp']
            if 'value' in data.columns and 'y' not in data.columns:
                data['y'] = data['value']

            # Ensure we have required columns
            if 'ds' not in data.columns or 'y' not in data.columns:
                console.error(f"Prophet evaluate: missing required columns. Available: {data.columns.tolist()}")
                return {}

            # Calculate Train MAE using in-sample predictions
            train_mae = None
            try:
                # Use the already-trained model to predict on training data
                train_forecast = self.model.predict(self.training_data[['ds']])
                train_comparison = self.training_data[['ds', 'y']].merge(
                    train_forecast[['ds', 'yhat']],
                    on='ds',
                    how='inner'
                )
                if len(train_comparison) > 0:
                    train_actual = train_comparison['y'].values
                    train_pred = train_comparison['yhat'].values
                    train_mae = float(np.mean(np.abs(train_actual - train_pred)))
                    console.info(f"   Train MAE: {train_mae:.2f} (from {len(train_comparison)} training points)")
            except Exception as e:
                console.warn(f"Could not calculate train MAE: {e}")

            # ✅ Use SAME validation window as AutoARIMA for fair comparison
            # AutoARIMA uses last fold of walk-forward (same horizon size)
            # For consistency, use same validation window

            # horizon MUST be provided from forecast configuration
            if horizon is None:
                raise ValueError(
                    "Prophet evaluate() requires 'horizon' parameter from forecast configuration!\n"
                    "This should be passed from WalkForwardValidation.validate()"
                )

            # Use last 'horizon' points as test set (same as AutoARIMA's last fold)
            if len(data) < horizon + 10:  # Need at least 10 training points
                console.log(f"Insufficient data for validation (need >{horizon+10} points, have {len(data)})")
                return {}

            split_idx = len(data) - horizon

            # Split data - only use ds and y columns for Prophet
            train_df = data[['ds', 'y']].iloc[:split_idx].copy()
            test_df = data[['ds', 'y']].iloc[split_idx:].copy()

            console.log(f"Prophet validation: {len(train_df)} train, {len(test_df)} test points (horizon={horizon}, matched to AutoARIMA window)")

            # Create temporary Prophet model for validation
            val_model = Prophet(
                daily_seasonality=False,
                weekly_seasonality=False,
                yearly_seasonality=False,
                interval_width=0.95
            )

            # Fit on train data
            val_model.fit(train_df)

            # Make predictions on test period
            future = test_df[['ds']].copy()
            forecast = val_model.predict(future)

            # Merge with actual values
            comparison = test_df[['ds', 'y']].merge(
                forecast[['ds', 'yhat']],
                on='ds',
                how='inner'
            )

            if len(comparison) == 0:
                console.log("No matching dates between actual and predicted")
                return {}

            # Calculate metrics
            y_true = comparison['y'].values
            y_pred = comparison['yhat'].values

            # MAE - Mean Absolute Error
            mae = float(np.mean(np.abs(y_true - y_pred)))

            # MAPE - Mean Absolute Percentage Error
            mape = float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)

            # RMSE - Root Mean Squared Error
            rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

            # SMAPE - Symmetric Mean Absolute Percentage Error
            smape = float(np.mean(2.0 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred))) * 100)

            # MASE - Mean Absolute Scaled Error
            naive_error = np.mean(np.abs(np.diff(y_true)))
            mase = float(mae / naive_error) if naive_error > 0 else 0.0

            # Format validation data for chart display
            validation_data = [
                {
                    "ds": row['ds'].isoformat() if hasattr(row['ds'], 'isoformat') else str(row['ds']),
                    "actual": float(row['y']),
                    "predicted": float(row['yhat'])
                }
                for _, row in comparison.iterrows()
            ]

            train_mae_str = f"{train_mae:.2f}" if train_mae is not None else "N/A"
            console.log(f"Prophet metrics - Train MAE: {train_mae_str}")
            console.log(f"Prophet metrics - MAPE: {mape:.2f}%, MAE: {mae:.2f}, RMSE: {rmse:.2f}")
            console.log(f"Validation data: {len(validation_data)} points for chart")

            return {
                "train_mae": train_mae,  # Add train MAE
                "mae": mae,
                "mape": mape,
                "rmse": rmse,
                "smape": smape,
                "mase": mase,
                "validation_data": validation_data,
                "n_predictions": len(validation_data)
            }

        except Exception as e:
            console.error(f"Prophet evaluation error: {e}")
            import traceback
            traceback.print_exc()
            return {}



class XGBoostPlugin(ModelPlugin):
    """XGBoost model plugin with feature engineering and prediction intervals"""

    def __init__(
        self,
        interval_method: str = 'bootstrap',
        interval_params: dict = None,
        **params
    ):
        """
        Args:
            interval_method: 'conformal', 'bootstrap', 'quantile' 중 선택
            interval_params: 각 방법별 파라미터
            **params: XGBoost 모델 파라미터
        """
        super().__init__(**params)
        self.training_data = None
        self.last_timestamp = None

        # 예측 구간 생성 설정
        self.interval_method = interval_method
        self.interval_params = interval_params or {}
        self.interval_generator = None
        self.feature_cols = []

    def get_name(self) -> str:
        return "xgboost"

    async def train(self, data: pd.DataFrame) -> Any:
        """Train XGBoost model"""
        try:
            import xgboost as xgb

            # Prepare features (assume feature engineering already done)
            feature_cols = [c for c in data.columns if c not in ['timestamp', 'value', 'tag_name']]

            # If no features, create basic temporal features automatically
            if not feature_cols:
                console.warn("No features found - creating basic temporal features for XGBoost")
                data = data.copy()
                
                # Ensure timestamp is datetime and set as index
                if 'timestamp' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                    data = data.set_index('timestamp')
                
                # Create temporal features from index
                data['hour'] = data.index.hour
                data['day_of_week'] = data.index.dayofweek
                data['is_weekend'] = (data.index.dayofweek >= 5).astype(int)
                
                # Add lag features
                data['lag_1'] = data['value'].shift(1)
                data['lag_24'] = data['value'].shift(24)
                data = data.dropna()  # Remove rows with NaN from lag features
                
                feature_cols = ['hour', 'day_of_week', 'is_weekend', 'lag_1', 'lag_24']
                console.info(f"Created {len(feature_cols)} basic features: {feature_cols}")

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
            
            # Store training data and last timestamp for prediction
            self.training_data = data.copy()
            self.last_timestamp = data.index[-1] if isinstance(data.index, pd.DatetimeIndex) else None
            
            # 예측 구간 생성기 학습
            from ksys_app.ml.prediction_intervals import create_interval_generator

            try:
                self.interval_generator = create_interval_generator(
                    method=self.interval_method,
                    **self.interval_params
                )

                if self.interval_method == 'conformal':
                    # Conformal Prediction: 교차 검증으로 conformity scores 계산
                    self.interval_generator.fit(model, X.values, y)
                    console.info("✅ Conformal prediction intervals fitted")

                elif self.interval_method == 'bootstrap':
                    # Bootstrap: 학습 데이터 잔차 저장
                    y_pred = model.predict(X.values)
                    self.interval_generator.fit(y, y_pred)
                    console.info("✅ Bootstrap residuals collected")

                elif self.interval_method == 'quantile':
                    # Quantile Regression: 분위수별 모델 학습
                    import xgboost as xgb
                    self.interval_generator.fit(
                        xgb.XGBRegressor,
                        X.values,
                        y,
                        model_params=self.params
                    )
                    console.info("✅ Quantile regression models trained")

            except Exception as e:
                console.warn(f"Interval generator fitting failed: {e}")
                self.interval_generator = None

            console.info(f"✅ {self.get_name()} trained successfully")
            return self.model

        except ImportError:
            console.error("xgboost not installed")
            raise
        except Exception as e:
            console.error(f"Error training XGBoost: {e}")
            raise

    async def predict(self, horizon: int, level: list = None) -> pd.DataFrame:
        """Generate predictions with future feature generation

        Args:
            horizon: Number of 10-minute periods to forecast
            level: List of confidence levels (ignored for XGBoost, uses bootstrapping)
        """
        if self.model is None:
            raise ValueError("Model not trained")

        try:
            # Generate future timestamps
            if self.last_timestamp is None:
                raise ValueError("No timestamp information available from training")

            # Use 10-minute frequency to match training data (influx_agg_10m)
            future_timestamps = pd.date_range(
                start=self.last_timestamp + pd.Timedelta(minutes=10),
                periods=horizon,
                freq='10T'
            )
            
            # Create empty DataFrame for future features
            future_df = pd.DataFrame(index=future_timestamps)
            
            # Generate temporal features
            future_df['hour'] = future_df.index.hour
            future_df['day_of_week'] = future_df.index.dayofweek
            future_df['is_weekend'] = (future_df.index.dayofweek >= 5).astype(int)
            
            # For lag features, use recursive prediction
            # Start with last known values from training
            last_values = self.training_data['value'].tail(24).values.tolist()
            predictions = []
            
            for i in range(horizon):
                # Create feature row
                feature_row = {
                    'hour': future_df.iloc[i]['hour'],
                    'day_of_week': future_df.iloc[i]['day_of_week'],
                    'is_weekend': future_df.iloc[i]['is_weekend'],
                    'lag_1': last_values[-1] if len(last_values) > 0 else 0,
                    'lag_24': last_values[-24] if len(last_values) >= 24 else last_values[0],
                }
                
                # Make prediction
                X_future = pd.DataFrame([feature_row])[self.feature_cols]
                pred = self.model.predict(X_future)[0]
                predictions.append(pred)
                
                # Update last_values for next iteration
                last_values.append(pred)
                if len(last_values) > 24:
                    last_values.pop(0)
            
            # Create result DataFrame
            result = pd.DataFrame({
                'ds': future_timestamps,
                'XGBoost': predictions,
            })
            
            # Generate prediction intervals using trained generator
            if self.interval_generator is not None:
                try:
                    predictions_array = np.array(predictions)

                    if self.interval_method == 'quantile':
                        # Quantile 방법은 X_future 필요
                        # Prepare X_future for all horizons
                        X_future_list = []
                        for i in range(horizon):
                            feature_row = {
                                'hour': future_df.iloc[i]['hour'],
                                'day_of_week': future_df.iloc[i]['day_of_week'],
                                'is_weekend': future_df.iloc[i]['is_weekend'],
                                'lag_1': 0,  # Simplified for interval generation
                                'lag_24': 0,
                            }
                            X_future_list.append(feature_row)
                        X_future = pd.DataFrame(X_future_list)[self.feature_cols]

                        intervals = self.interval_generator.generate(X_future=X_future.values)
                    else:
                        # Conformal, Bootstrap은 predictions만 필요
                        intervals = self.interval_generator.generate(predictions_array)

                    # Add intervals to result
                    for key, values in intervals.items():
                        result[f'XGBoost-{key}'] = values

                    console.info(f"Generated {self.interval_method} intervals: {list(intervals.keys())}")

                except Exception as e:
                    console.warn(f"Interval generation failed: {e}, using fallback")
                    # Fallback to simple intervals
                    result['XGBoost-lo-80'] = result['XGBoost'] * 0.9
                    result['XGBoost-hi-80'] = result['XGBoost'] * 1.1
                    result['XGBoost-lo-95'] = result['XGBoost'] * 0.8
                    result['XGBoost-hi-95'] = result['XGBoost'] * 1.2
            else:
                # No interval generator - use simple fallback
                result['XGBoost-lo-80'] = result['XGBoost'] * 0.9
                result['XGBoost-hi-80'] = result['XGBoost'] * 1.1
                result['XGBoost-lo-95'] = result['XGBoost'] * 0.8
                result['XGBoost-hi-95'] = result['XGBoost'] * 1.2
            
            console.info(f"Generated {len(result)} XGBoost predictions")
            return result

        except Exception as e:
            console.error(f"Error generating XGBoost predictions: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def evaluate(self, test_data: pd.DataFrame = None, n_windows: int = 3, horizon: int = None) -> dict:
        """
        Evaluate XGBoost model using walk-forward validation

        Args:
            test_data: Test dataset (optional, uses training data if not provided)
            n_windows: Number of walk-forward windows
            horizon: Forecast horizon in periods (from forecast_config, used for validation split)

        Returns:
            dict with MAE, MAPE, MASE, RMSE, SMAPE, train_mae, validation_data
        """
        if self.model is None:
            raise ValueError("Model not trained")

        try:
            # Use training data if test data not provided
            data = test_data if test_data is not None else self.training_data

            if data is None or len(data) == 0:
                console.log("No data available for XGBoost evaluation")
                return {}

            # ✅ Check if data has required feature columns, if not create them automatically
            missing_features = [col for col in self.feature_cols if col not in data.columns]
            if missing_features:
                console.warn(f"XGBoost evaluate: missing features {missing_features}, creating them automatically")

                # Create features automatically (same as train() method)
                data = data.copy()

                # Ensure timestamp is datetime and set as index
                if 'timestamp' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                    data = data.set_index('timestamp')

                # Create temporal features from index
                data['hour'] = data.index.hour
                data['day_of_week'] = data.index.dayofweek
                data['is_weekend'] = (data.index.dayofweek >= 5).astype(int)

                # Add lag features
                data['lag_1'] = data['value'].shift(1)
                data['lag_24'] = data['value'].shift(24)
                data = data.dropna()  # Remove rows with NaN from lag features

                console.log(f"XGBoost evaluate: Created basic temporal features for validation")

            # Calculate Train MAE using training data predictions
            train_mae = None
            try:
                X_train = self.training_data[self.feature_cols].fillna(0)
                y_train_actual = self.training_data['value'].values
                y_train_pred = self.model.predict(X_train)
                train_mae = float(np.mean(np.abs(y_train_actual - y_train_pred)))
                console.info(f"   Train MAE: {train_mae:.2f} (from {len(y_train_actual)} training points)")
            except Exception as e:
                console.warn(f"Could not calculate train MAE: {e}")

            # ✅ Use SAME validation window as AutoARIMA for fair comparison
            # AutoARIMA uses last fold of walk-forward (same horizon size)
            # For consistency, use same validation window

            # horizon MUST be provided from forecast configuration
            if horizon is None:
                raise ValueError(
                    "XGBoost evaluate() requires 'horizon' parameter from forecast configuration!\n"
                    "This should be passed from WalkForwardValidation.validate()"
                )

            # Use last 'horizon' points as test set (same as AutoARIMA's last fold)
            if len(data) < horizon + 10:  # Need at least 10 training points
                console.log(f"Insufficient data for validation (need >{horizon+10} points, have {len(data)})")
                return {}

            split_idx = len(data) - horizon

            # Split data
            train_df = data.iloc[:split_idx].copy()
            test_df = data.iloc[split_idx:].copy()

            console.log(f"XGBoost validation: {len(train_df)} train, {len(test_df)} test points (horizon={horizon}, matched to AutoARIMA window)")

            # Get features
            X_test = test_df[self.feature_cols].fillna(0)
            y_true = test_df['value'].values

            # Make predictions
            y_pred = self.model.predict(X_test)

            # Calculate metrics
            mae = float(np.mean(np.abs(y_true - y_pred)))
            mape = float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)
            rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
            smape = float(np.mean(2.0 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred))) * 100)

            # MASE
            naive_error = np.mean(np.abs(np.diff(y_true)))
            mase = float(mae / naive_error) if naive_error > 0 else 0.0

            # Format validation data for chart display
            validation_data = [
                {
                    "ds": test_df.index[i].isoformat() if hasattr(test_df.index[i], 'isoformat') else str(test_df.index[i]),
                    "actual": float(y_true[i]),
                    "predicted": float(y_pred[i])
                }
                for i in range(len(y_true))
            ]

            train_mae_str = f"{train_mae:.2f}" if train_mae is not None else "N/A"
            console.log(f"XGBoost metrics - Train MAE: {train_mae_str}")
            console.log(f"XGBoost metrics - MAPE: {mape:.2f}%, MAE: {mae:.2f}, RMSE: {rmse:.2f}")
            console.log(f"Validation data: {len(validation_data)} points for chart")

            return {
                "train_mae": train_mae,  # Add train MAE
                "mae": mae,
                "mape": mape,
                "rmse": rmse,
                "smape": smape,
                "mase": mase,
                "validation_data": validation_data,
                "n_predictions": len(validation_data)
            }

        except Exception as e:
            console.error(f"XGBoost evaluation error: {e}")
            import traceback
            traceback.print_exc()
            return {}


# ============================================================================
# Model Registry (제안하신 설계의 레지스트리 패턴)
# ============================================================================

class ModelRegistry:
    """모델 레지스트리 - 동적 알고리즘 추가"""

    _models: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, plugin_class: type):
        """새로운 모델 등록"""
        if not issubclass(plugin_class, ModelPlugin):
            raise TypeError("Must inherit from ModelPlugin")

        cls._models[name] = plugin_class
        console.info(f"📦 Registered model: {name}")

    @classmethod
    def get(cls, name: str) -> type:
        """모델 클래스 가져오기"""
        if name not in cls._models:
            raise ValueError(f"Model '{name}' not registered")
        return cls._models[name]

    @classmethod
    def list_models(cls) -> List[str]:
        """등록된 모델 목록"""
        return list(cls._models.keys())


# Default models registration
ModelRegistry.register('auto_arima', AutoARIMAPlugin)
ModelRegistry.register('prophet', ProphetPlugin)
ModelRegistry.register('xgboost', XGBoostPlugin)


# ============================================================================
# Hybrid Training Pipeline V2
# ============================================================================

class TrainingPipelineV2:
    """
    하이브리드 학습 파이프라인

    Features:
    - 메서드 체이닝 (fluent API)
    - 전처리/후처리 체인
    - 메타데이터 추적
    - 레지스트리 패턴
    - 타입 안정성
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.feature_service = FeatureEngineeringService(session)

        # Configuration
        self._data_source = {}
        self._preprocessing_steps: List[PreprocessingStep] = []
        self._feature_config = {}
        self._models: List[ModelPlugin] = []
        self._validation = None

        # Data cache
        self._raw_data: Optional[pd.DataFrame] = None
        self._processed_data: Optional[pd.DataFrame] = None

        # Metadata
        self.metadata = PipelineMetadata()

    # ========================================================================
    # Fluent API
    # ========================================================================

    def set_data_source(self, tag_name: str, days: int = 30) -> 'TrainingPipelineV2':
        """데이터 소스 설정"""
        self._data_source = {'tag_name': tag_name, 'days': days}
        self.metadata.tag_name = tag_name
        return self

    def add_preprocessing(self) -> PreprocessingChain:
        """전처리 체인 시작"""
        return PreprocessingChain(self)

    def add_feature_engineering(self) -> FeatureEngineeringChain:
        """피처 엔지니어링 체인 시작"""
        return FeatureEngineeringChain(self)

    def add_model(self, model_type: str, **params) -> 'TrainingPipelineV2':
        """모델 추가 (레지스트리에서 가져오기)"""
        plugin_class = ModelRegistry.get(model_type)
        plugin = plugin_class(**params)
        self._models.append(plugin)
        console.info(f"➕ Added model: {plugin.get_name()}")
        return self

    def add_validation(self, validation_type: str, **params) -> 'TrainingPipelineV2':
        """검증 전략 추가"""
        from ksys_app.ml.pipeline_builder import WalkForwardValidation

        if validation_type == 'walk_forward':
            self._validation = WalkForwardValidation(**params)
        return self

    def build(self) -> 'TrainingPipelineV2':
        """파이프라인 빌드"""
        console.info("🔨 Pipeline V2 built successfully")
        console.info(f"   Preprocessing: {len(self._preprocessing_steps)} steps")
        console.info(f"   Features: {len(self._feature_config)} types")
        console.info(f"   Models: {len(self._models)}")
        return self

    # ========================================================================
    # Execution
    # ========================================================================

    async def execute(self) -> Dict[str, Any]:
        """파이프라인 실행"""
        import time
        start_time = time.time()

        console.info("🚀 Executing Pipeline V2...")

        # Step 1: Load data
        console.info("📥 Step 1: Loading data...")
        await self._load_data()

        # Step 2: Preprocessing
        if self._preprocessing_steps:
            console.info("🧹 Step 2: Preprocessing...")
            await self._apply_preprocessing()

        # Step 3: Feature engineering
        if self._feature_config:
            console.info("⚙️  Step 3: Feature engineering...")
            await self._apply_feature_engineering()

        # Step 4: Train models
        console.info("🎓 Step 4: Training models...")
        results = {}

        for model in self._models:
            console.info(f"   Training {model.get_name()}...")

            # Train
            await model.train(self._processed_data)
            self.metadata.models_trained.append(model.get_name())

            # Validate
            if self._validation:
                metrics = await self._validation.validate(self._processed_data, model)
                results[model.get_name()] = {
                    'model': model,
                    'metrics': metrics
                }
                console.info(f"   ✅ {model.get_name()} - MAPE: {metrics['mape']:.2f}%")

        # Find best model
        if results:
            best = min(results.items(), key=lambda x: x[1]['metrics'].get('mape', float('inf')))
            self.metadata.best_model = best[0]
            self.metadata.best_mape = best[1]['metrics']['mape']

        self.metadata.training_duration = time.time() - start_time

        console.info(f"✅ Pipeline complete in {self.metadata.training_duration:.2f}s")
        console.info(f"   Best model: {self.metadata.best_model} (MAPE: {self.metadata.best_mape:.2f}%)")

        return {
            'results': results,
            'metadata': self.metadata,
            'raw_data': self._raw_data  # Include raw data for chart display
        }

    # ========================================================================
    # Internal Methods
    # ========================================================================

    async def _load_data(self):
        """데이터 로드 - 10분 aggregation 데이터만 사용"""
        from sqlalchemy import text

        tag_name = self._data_source['tag_name']
        days = self._data_source['days']
        end_time = datetime.now(KST)
        start_time = end_time - timedelta(days=days)

        # ✅ 10분 aggregation 데이터만 사용 (성능 및 데이터 품질 향상)
        query = text("""
            SELECT
                bucket AT TIME ZONE 'Asia/Seoul' as timestamp,
                avg as value
            FROM influx_agg_10m
            WHERE tag_name = :tag_name
              AND bucket >= :start_time
              AND bucket < :end_time
              AND avg IS NOT NULL
            ORDER BY bucket
        """)

        rows = (await self.session.execute(
            query,
            {'tag_name': tag_name, 'start_time': start_time, 'end_time': end_time}
        )).mappings().all()

        self._raw_data = pd.DataFrame([dict(r) for r in rows])
        self.metadata.raw_samples = len(self._raw_data)
        self.metadata.data_start = start_time
        self.metadata.data_end = end_time

        console.info(f"   Loaded {len(self._raw_data)} rows")

    async def _apply_preprocessing(self):
        """전처리 체인 실행"""
        df = self._raw_data.copy()

        for step in self._preprocessing_steps:
            df = await step.apply(df, self.metadata)

        self._processed_data = df
        self.metadata.processed_samples = len(df)
        console.info(f"   Processed samples: {self.metadata.processed_samples}")

    async def _apply_feature_engineering(self):
        """피처 엔지니어링 적용"""
        df = self._processed_data if self._processed_data is not None else self._raw_data
        df = df.copy()

        self.metadata.original_features = len(df.columns)

        # Lag features
        if self._feature_config.get('lags'):
            for lag in self._feature_config['lags']:
                df[f'lag_{lag}h'] = df['value'].shift(lag)
                self.metadata.features_created.append(f'lag_{lag}h')

        # Rolling features
        if self._feature_config.get('rolling'):
            for window in self._feature_config['rolling']:
                df[f'rolling_mean_{window}h'] = df['value'].rolling(window).mean()
                df[f'rolling_std_{window}h'] = df['value'].rolling(window).std()
                self.metadata.features_created.extend([
                    f'rolling_mean_{window}h',
                    f'rolling_std_{window}h'
                ])

        # Temporal features
        if self._feature_config.get('temporal'):
            for comp in self._feature_config['temporal']:
                if comp == 'hour':
                    df['hour'] = df['timestamp'].dt.hour
                    self.metadata.features_created.append('hour')
                elif comp == 'dayofweek':
                    df['dayofweek'] = df['timestamp'].dt.dayofweek
                    self.metadata.features_created.append('dayofweek')

        df = df.dropna()
        self._processed_data = df
        self.metadata.final_features = len(df.columns)

        console.info(f"   Created {len(self.metadata.features_created)} features")


# ============================================================================
# Configuration-based Factory (제안하신 설계)
# ============================================================================

async def create_pipeline_from_config(
    session: AsyncSession,
    config: Dict
) -> TrainingPipelineV2:
    """설정 기반 파이프라인 생성"""

    pipeline = TrainingPipelineV2(session)

    # Data source
    if 'data_source' in config:
        pipeline.set_data_source(**config['data_source'])

    # Preprocessing
    if 'preprocessing' in config:
        chain = pipeline.add_preprocessing()
        for step in config['preprocessing']:
            if step['type'] == 'interpolate':
                chain.interpolate(**step.get('params', {}))
            elif step['type'] == 'remove_outliers':
                chain.remove_outliers(**step.get('params', {}))
            elif step['type'] == 'scale':
                chain.scale(**step.get('params', {}))
        chain.done()

    # Feature engineering
    if 'feature_engineering' in config:
        chain = pipeline.add_feature_engineering()
        fe_config = config['feature_engineering']

        if 'lags' in fe_config:
            chain.add_lag(fe_config['lags'])
        if 'rolling' in fe_config:
            chain.add_rolling(fe_config['rolling'])
        if 'temporal' in fe_config:
            chain.add_temporal(fe_config['temporal'])

        chain.done()

    # Models
    if 'models' in config:
        for model_cfg in config['models']:
            pipeline.add_model(model_cfg['type'], **model_cfg.get('params', {}))

    # Validation
    if 'validation' in config:
        pipeline.add_validation(
            config['validation']['type'],
            **config['validation'].get('params', {})
        )

    return pipeline.build()
