"""
Time-Series Forecast Pipeline

완전한 MLOps 파이프라인:
- 전처리: 결측치, 이상치, 정규화
- 피처 엔지니어링: Lag, Rolling, Temporal, Difference
- 모델: RandomForest (빠르고 정확)
- 후처리: 역정규화, 클리핑
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

from reflex.utils import console


# ============================================================================
# STEP 1: 전처리 (Preprocessing)
# ============================================================================

def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    결측치 처리

    전략:
    1. Forward Fill (최대 6시간)
    2. Backward Fill (최대 6시간)
    3. 선형 보간
    4. 마지막 수단: 중앙값
    """
    # 결측치 비율 확인
    missing_ratio = df['value'].isna().sum() / len(df)

    if missing_ratio > 0.3:  # 30% 이상 결측치
        raise ValueError(f"Too many missing values: {missing_ratio:.1%}")

    # Forward fill (최대 6시간)
    df['value'] = df['value'].fillna(method='ffill', limit=6)

    # Backward fill (남은 결측치)
    df['value'] = df['value'].fillna(method='bfill', limit=6)

    # 선형 보간 (여전히 남은 결측치)
    df['value'] = df['value'].interpolate(method='linear', limit_direction='both')

    # 마지막 수단: 중앙값
    if df['value'].isna().any():
        median_value = df['value'].median()
        df['value'] = df['value'].fillna(median_value)

    return df


def remove_outliers(
    df: pd.DataFrame,
    method: str = 'iqr',
    threshold: float = 3.0,
    **kwargs
) -> pd.DataFrame:
    """
    이상치 제거

    Methods:
    - 'iqr': Interquartile Range (사분위수 범위)
    - 'zscore': Z-score (표준편차 기반)
    """

    if method == 'iqr':
        # IQR 방식 (가장 안정적)
        Q1 = df['value'].quantile(0.25)
        Q3 = df['value'].quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR

        # 이상치를 경계값으로 클리핑 (제거하지 않고)
        df['value'] = df['value'].clip(lower=lower_bound, upper=upper_bound)

    elif method == 'zscore':
        # Z-score 방식
        mean = df['value'].mean()
        std = df['value'].std()

        lower_bound = mean - threshold * std
        upper_bound = mean + threshold * std

        df['value'] = df['value'].clip(lower=lower_bound, upper=upper_bound)

    return df


class DataScaler:
    """데이터 정규화 및 역정규화"""

    def __init__(self, method: str = 'standard'):
        """
        method: 'standard' | 'minmax' | 'robust'
        """
        if method == 'standard':
            self.scaler = StandardScaler()  # (x - mean) / std
        elif method == 'minmax':
            self.scaler = MinMaxScaler()    # (x - min) / (max - min)
        else:
            self.scaler = RobustScaler()    # 중앙값 기반 (이상치에 강함)

        self.fitted = False

    def fit_transform(self, values: np.ndarray) -> np.ndarray:
        """학습 데이터에 사용 (fit + transform)"""
        values_2d = values.reshape(-1, 1)
        scaled = self.scaler.fit_transform(values_2d)
        self.fitted = True
        return scaled.flatten()

    def transform(self, values: np.ndarray) -> np.ndarray:
        """테스트 데이터에 사용 (transform only)"""
        if not self.fitted:
            raise ValueError("Scaler not fitted yet")
        values_2d = values.reshape(-1, 1)
        scaled = self.scaler.transform(values_2d)
        return scaled.flatten()

    def inverse_transform(self, values: np.ndarray) -> np.ndarray:
        """정규화 역변환 (예측 후 원래 스케일로 복원)"""
        values_2d = values.reshape(-1, 1)
        original = self.scaler.inverse_transform(values_2d)
        return original.flatten()


def preprocess_data(
    df: pd.DataFrame,
    sensor_config: Dict,
    scaler: Optional[DataScaler] = None
) -> Tuple[pd.DataFrame, DataScaler]:
    """
    전체 전처리 파이프라인

    Args:
        df: Raw data (ts, value)
        sensor_config: {
            'min_value': 0.0,
            'max_value': 10.0,
            'outlier_method': 'iqr',
            'outlier_threshold': 3.0,
            'scaler': 'standard'
        }
        scaler: 기존 scaler (예측 시 사용)

    Returns:
        (preprocessed_df, scaler)
    """
    df = df.copy()

    # Step 1: 결측치 처리
    df = handle_missing_values(df)

    # Step 2: 이상치 제거
    df = remove_outliers(
        df,
        method=sensor_config.get('outlier_method', 'iqr'),
        threshold=sensor_config.get('outlier_threshold', 3.0)
    )

    # Step 3: 물리적 한계값 적용 (센서별)
    min_val = sensor_config.get('min_value', 0.0)
    max_val = sensor_config.get('max_value', 100.0)
    df['value'] = df['value'].clip(lower=min_val, upper=max_val)

    # Step 4: 정규화
    if scaler is None:
        # 학습 시: fit_transform
        scaler = DataScaler(method=sensor_config.get('scaler', 'standard'))
        df['value_scaled'] = scaler.fit_transform(df['value'].values)
    else:
        # 예측 시: transform only
        df['value_scaled'] = scaler.transform(df['value'].values)

    return df, scaler


# ============================================================================
# STEP 2: 피처 엔지니어링 (Feature Engineering)
# ============================================================================

def create_lag_features(
    df: pd.DataFrame,
    lags: List[int],
    target_col: str = 'value_scaled'
) -> pd.DataFrame:
    """래그 피처 생성"""
    df = df.copy()

    for lag in lags:
        df[f'lag_{lag}h'] = df[target_col].shift(lag)

    return df


def create_rolling_features(
    df: pd.DataFrame,
    windows: List[int],
    target_col: str = 'value_scaled'
) -> pd.DataFrame:
    """롤링 통계 피처 생성"""
    df = df.copy()

    for window in windows:
        # 이동 평균
        df[f'rolling_mean_{window}h'] = df[target_col].rolling(
            window=window,
            min_periods=1
        ).mean()

        # 이동 표준편차
        df[f'rolling_std_{window}h'] = df[target_col].rolling(
            window=window,
            min_periods=1
        ).std()

        # 이동 최소값
        df[f'rolling_min_{window}h'] = df[target_col].rolling(
            window=window,
            min_periods=1
        ).min()

        # 이동 최대값
        df[f'rolling_max_{window}h'] = df[target_col].rolling(
            window=window,
            min_periods=1
        ).max()

    return df


def create_temporal_features(df: pd.DataFrame, ts_col: str = 'ts') -> pd.DataFrame:
    """시간 기반 피처 생성"""
    df = df.copy()

    # datetime으로 변환
    if not pd.api.types.is_datetime64_any_dtype(df[ts_col]):
        df[ts_col] = pd.to_datetime(df[ts_col])

    # 시간대 (0-23)
    df['hour'] = df[ts_col].dt.hour

    # 요일 (0=월요일, 6=일요일)
    df['dayofweek'] = df[ts_col].dt.dayofweek

    # 주말 여부
    df['is_weekend'] = (df['dayofweek'] >= 5).astype(int)

    # 근무시간 여부 (9-18시)
    df['is_business_hour'] = ((df['hour'] >= 9) & (df['hour'] < 18)).astype(int)

    # Cyclical encoding (주기성을 연속적으로 표현)
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

    return df


def create_difference_features(
    df: pd.DataFrame,
    periods: List[int] = [1, 24],
    target_col: str = 'value_scaled'
) -> pd.DataFrame:
    """변화율 피처 생성"""
    df = df.copy()

    for period in periods:
        # 절대 차이
        df[f'diff_{period}h'] = df[target_col].diff(periods=period)

    return df


def engineer_features(
    df: pd.DataFrame,
    feature_config: Dict
) -> pd.DataFrame:
    """
    전체 피처 엔지니어링 파이프라인

    Args:
        df: 전처리된 데이터 (ts, value, value_scaled)
        feature_config: {
            'lag_periods': [1, 6, 24],
            'rolling_windows': [6, 24],
            'include_temporal': True,
            'include_diff': True
        }

    Returns:
        피처가 추가된 데이터프레임
    """
    df = df.copy()

    # 1. 래그 피처
    if 'lag_periods' in feature_config:
        df = create_lag_features(
            df,
            lags=feature_config['lag_periods'],
            target_col='value_scaled'
        )

    # 2. 롤링 피처
    if 'rolling_windows' in feature_config:
        df = create_rolling_features(
            df,
            windows=feature_config['rolling_windows'],
            target_col='value_scaled'
        )

    # 3. 시간 피처
    if feature_config.get('include_temporal', True):
        df = create_temporal_features(df, ts_col='ts')

    # 4. 차분 피처
    if feature_config.get('include_diff', True):
        df = create_difference_features(
            df,
            periods=[1, 24],
            target_col='value_scaled'
        )

    # 5. NaN 제거 (초기 래그 기간)
    max_lag = max(feature_config.get('lag_periods', [1]))
    df = df.iloc[max_lag:].reset_index(drop=True)

    # 남은 NaN을 0으로 채우기
    df = df.fillna(0)

    return df


# ============================================================================
# STEP 3: SimpleForecastPipeline
# ============================================================================

class SimpleForecastPipeline:
    """
    간단하고 빠른 예측 파이프라인

    RandomForest 기반 (빠르고 효과적)
    """

    def __init__(self, tag_name: str):
        self.tag_name = tag_name
        self.scaler = None
        self.model = None
        self.feature_cols = []

        # 기본 설정
        self.feature_config = {
            'lag_periods': [1, 6, 24],
            'rolling_windows': [6, 24],
            'include_temporal': True,
            'include_diff': True
        }

        self.sensor_config = {
            'min_value': 0.0,
            'max_value': 10.0,
            'outlier_method': 'iqr',
            'outlier_threshold': 3.0,
            'scaler': 'standard'
        }

    async def train(self, df: pd.DataFrame) -> Dict:
        """
        모델 학습

        Args:
            df: Raw data (ts, value)

        Returns:
            Training metrics
        """
        console.info(f"Training pipeline for {self.tag_name}")

        # Step 1: 전처리
        console.info("  1/4 Preprocessing...")
        df_processed, self.scaler = preprocess_data(df, self.sensor_config)

        # Step 2: 피처 엔지니어링
        console.info("  2/4 Feature engineering...")
        df_features = engineer_features(df_processed, self.feature_config)

        console.info(f"  Generated {len(df_features)} samples with {len(df_features.columns)} features")

        # Step 3: 학습/테스트 분리 (80/20)
        console.info("  3/4 Train/test split...")
        train_size = int(len(df_features) * 0.8)
        train_df = df_features.iloc[:train_size]
        test_df = df_features.iloc[train_size:]

        # 피처와 타겟 분리
        self.feature_cols = [col for col in df_features.columns
                            if col not in ['ts', 'value', 'value_scaled']]

        X_train = train_df[self.feature_cols].values
        y_train = train_df['value_scaled'].values
        X_test = test_df[self.feature_cols].values
        y_test = test_df['value_scaled'].values

        console.info(f"  Train: {len(X_train)} samples, Test: {len(X_test)} samples")

        # Step 4: 모델 학습
        console.info("  4/4 Model training...")
        self.model = RandomForestRegressor(
            n_estimators=50,  # 라즈베리파이용 경량화
            max_depth=10,
            min_samples_split=5,
            n_jobs=2,  # 코어 2개만 사용
            random_state=42
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.model.fit(X_train, y_train))

        # 평가
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)

        # 원래 스케일로 복원
        y_train_orig = self.scaler.inverse_transform(y_train)
        y_pred_train_orig = self.scaler.inverse_transform(y_pred_train)
        y_test_orig = self.scaler.inverse_transform(y_test)
        y_pred_test_orig = self.scaler.inverse_transform(y_pred_test)

        # 메트릭 계산
        metrics = {
            'train_mae': float(mean_absolute_error(y_train_orig, y_pred_train_orig)),
            'train_rmse': float(np.sqrt(mean_squared_error(y_train_orig, y_pred_train_orig))),
            'test_mae': float(mean_absolute_error(y_test_orig, y_pred_test_orig)),
            'test_rmse': float(np.sqrt(mean_squared_error(y_test_orig, y_pred_test_orig))),
            'n_features': len(self.feature_cols),
            'n_samples': len(df_features)
        }

        console.info(f"✅ Training complete - Test MAE: {metrics['test_mae']:.4f}")

        return metrics

    async def predict(self, df: pd.DataFrame, horizon: int = 24) -> List[float]:
        """
        예측 수행

        Args:
            df: Recent data for context
            horizon: 예측 기간 (시간 단위)

        Returns:
            List of predictions
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained yet")

        # 전처리 (transform only)
        df_processed, _ = preprocess_data(df, self.sensor_config, scaler=self.scaler)

        # 피처 엔지니어링
        df_features = engineer_features(df_processed, self.feature_config)

        # 예측 (마지막 행 사용)
        last_features = df_features[self.feature_cols].iloc[-1:].values
        prediction_scaled = self.model.predict(last_features)[0]
        prediction = self.scaler.inverse_transform([prediction_scaled])[0]

        # 단일 값 예측만 지원 (다중 스텝 예측은 향후 구현)
        return [float(prediction)] * horizon

    async def save(self, path: Path):
        """모델 저장"""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_config': self.feature_config,
            'sensor_config': self.sensor_config,
            'feature_cols': self.feature_cols,
            'tag_name': self.tag_name
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model_data, path, compress=3)
        console.info(f"Model saved: {path}")

    async def load(self, path: Path):
        """모델 로드"""
        model_data = joblib.load(path)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_config = model_data['feature_config']
        self.sensor_config = model_data['sensor_config']
        self.feature_cols = model_data['feature_cols']
        self.tag_name = model_data['tag_name']

        console.info(f"Model loaded: {path}")
