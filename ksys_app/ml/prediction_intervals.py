"""
Prediction Intervals 생성 유틸리티

3가지 방법 지원:
1. Conformal Prediction - 교차 검증 기반, 통계적으로 보정된 구간
2. Bootstrap Residuals - 과거 잔차 샘플링, 빠른 계산
3. Quantile Regression - 분위수 직접 예측, 비대칭 분포 처리
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Literal
from reflex.utils import console
from sklearn.model_selection import TimeSeriesSplit


class PredictionIntervalGenerator:
    """예측 구간 생성기 베이스 클래스"""

    def __init__(self, confidence_levels: List[int] = [80, 95]):
        """
        Args:
            confidence_levels: 신뢰 구간 수준 (예: [80, 95])
        """
        self.confidence_levels = confidence_levels

    def generate(
        self,
        predictions: np.ndarray,
        **kwargs
    ) -> Dict[str, np.ndarray]:
        """
        예측 구간 생성

        Returns:
            dict with keys: 'lo-80', 'hi-80', 'lo-95', 'hi-95', etc.
        """
        raise NotImplementedError


class ConformalPrediction(PredictionIntervalGenerator):
    """
    Conformal Prediction 방법

    교차 검증으로 과거 예측 오차 분포를 학습하고,
    이를 기반으로 통계적으로 보정된 예측 구간 생성

    특징:
    - 분포 가정 불필요 (non-parametric)
    - 통계적으로 보정됨 (well-calibrated)
    - 시간에 따라 불확실성 증가 반영
    """

    def __init__(
        self,
        confidence_levels: List[int] = [80, 95],
        n_windows: int = 5
    ):
        """
        Args:
            confidence_levels: 신뢰 구간 수준
            n_windows: 교차 검증 윈도우 개수 (많을수록 정확하지만 느림)
        """
        super().__init__(confidence_levels)
        self.n_windows = n_windows
        self.conformity_scores: Optional[np.ndarray] = None

    def fit(
        self,
        model,
        X: np.ndarray,
        y: np.ndarray,
        predict_fn=None
    ):
        """
        교차 검증으로 conformity scores 계산

        Args:
            model: 학습된 모델 (predict 메서드 필요)
            X: 입력 피처
            y: 실제 값
            predict_fn: 커스텀 예측 함수 (선택)
        """
        console.info(f"🔍 Computing conformity scores with {self.n_windows} windows...")

        # TimeSeriesSplit으로 교차 검증
        tscv = TimeSeriesSplit(n_splits=self.n_windows)

        all_errors = []

        for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]

            # 임시 모델 학습
            temp_model = model.__class__(**model.get_params())
            temp_model.fit(X_train, y_train)

            # 검증 세트 예측
            if predict_fn:
                y_pred = predict_fn(temp_model, X_val)
            else:
                y_pred = temp_model.predict(X_val)

            # 절대 오차 계산
            errors = np.abs(y_val - y_pred)
            all_errors.extend(errors)

            console.debug(f"  Fold {fold_idx + 1}: {len(errors)} errors, "
                         f"mean={np.mean(errors):.2f}, std={np.std(errors):.2f}")

        # Conformity scores = 절대 오차들
        self.conformity_scores = np.array(all_errors)
        console.info(f"✅ Collected {len(self.conformity_scores)} conformity scores")

    def generate(
        self,
        predictions: np.ndarray,
        time_decay: bool = True,
        **kwargs
    ) -> Dict[str, np.ndarray]:
        """
        Conformal 예측 구간 생성

        Args:
            predictions: 점 예측값
            time_decay: 시간이 지날수록 구간 확대 여부

        Returns:
            dict with 'lo-80', 'hi-80', 'lo-95', 'hi-95'
        """
        if self.conformity_scores is None:
            raise ValueError("Must call fit() first to compute conformity scores")

        horizon = len(predictions)
        intervals = {}

        for level in self.confidence_levels:
            # Alpha = (100 - level) / 100
            # 예: 80% → alpha=0.20 → quantile=0.90 (상위 10%를 제외)
            alpha = (100 - level) / 100
            quantile = 1 - alpha

            # Conformity scores의 분위수 계산
            base_interval = np.quantile(self.conformity_scores, quantile)

            # 시간에 따른 불확실성 증가 (선택)
            if time_decay:
                # 시간이 지날수록 구간 확대 (1.0 → 1.5 선형 증가)
                decay_factors = np.linspace(1.0, 1.5, horizon)
                interval_widths = base_interval * decay_factors
            else:
                interval_widths = np.full(horizon, base_interval)

            # 구간 생성
            intervals[f'lo-{level}'] = predictions - interval_widths
            intervals[f'hi-{level}'] = predictions + interval_widths

        console.info(f"✅ Generated Conformal intervals: {list(intervals.keys())}")
        return intervals


class BootstrapResiduals(PredictionIntervalGenerator):
    """
    Bootstrap Residuals 방법

    과거 예측 잔차를 랜덤 샘플링하여 미래 불확실성 시뮬레이션

    특징:
    - 빠른 계산 속도
    - 실제 모델 오차 패턴 반영
    - 잔차 독립성 가정 (시계열 자기상관 주의)
    """

    def __init__(
        self,
        confidence_levels: List[int] = [80, 95],
        n_bootstrap: int = 1000
    ):
        """
        Args:
            confidence_levels: 신뢰 구간 수준
            n_bootstrap: Bootstrap 반복 횟수 (많을수록 정확하지만 느림)
        """
        super().__init__(confidence_levels)
        self.n_bootstrap = n_bootstrap
        self.residuals: Optional[np.ndarray] = None

    def fit(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ):
        """
        학습 데이터의 잔차 저장

        Args:
            y_true: 실제 값
            y_pred: 예측 값
        """
        self.residuals = y_true - y_pred
        console.info(f"📊 Collected {len(self.residuals)} residuals for bootstrap")
        console.info(f"   Mean: {np.mean(self.residuals):.2f}, "
                    f"Std: {np.std(self.residuals):.2f}")

    def generate(
        self,
        predictions: np.ndarray,
        **kwargs
    ) -> Dict[str, np.ndarray]:
        """
        Bootstrap으로 예측 구간 생성

        Args:
            predictions: 점 예측값

        Returns:
            dict with 'lo-80', 'hi-80', 'lo-95', 'hi-95'
        """
        if self.residuals is None:
            raise ValueError("Must call fit() first to collect residuals")

        horizon = len(predictions)

        console.info(f"🔄 Running {self.n_bootstrap} bootstrap iterations...")

        # Bootstrap 시뮬레이션
        bootstrap_forecasts = []

        for i in range(self.n_bootstrap):
            # 잔차 랜덤 샘플링 (복원 추출)
            sampled_errors = np.random.choice(
                self.residuals,
                size=horizon,
                replace=True
            )

            # 예측값 + 샘플링된 오차
            bootstrap_forecast = predictions + sampled_errors
            bootstrap_forecasts.append(bootstrap_forecast)

        # NumPy 배열로 변환 (n_bootstrap x horizon)
        bootstrap_array = np.array(bootstrap_forecasts)

        # 분위수 계산
        intervals = {}

        for level in self.confidence_levels:
            # Alpha = (100 - level) / 100
            # 예: 80% → alpha=0.20 → lower=10%, upper=90%
            alpha = (100 - level) / 100
            lower_percentile = (alpha / 2) * 100  # 10%
            upper_percentile = (1 - alpha / 2) * 100  # 90%

            intervals[f'lo-{level}'] = np.percentile(
                bootstrap_array,
                lower_percentile,
                axis=0
            )
            intervals[f'hi-{level}'] = np.percentile(
                bootstrap_array,
                upper_percentile,
                axis=0
            )

        console.info(f"✅ Generated Bootstrap intervals: {list(intervals.keys())}")
        return intervals


class QuantileRegression(PredictionIntervalGenerator):
    """
    Quantile Regression 방법

    여러 분위수를 직접 예측하여 예측 구간 생성

    특징:
    - 비대칭 분포 처리 가능
    - 극단값 예측에 유용
    - 각 분위수별 별도 모델 필요
    """

    def __init__(
        self,
        confidence_levels: List[int] = [80, 95]
    ):
        """
        Args:
            confidence_levels: 신뢰 구간 수준
        """
        super().__init__(confidence_levels)
        self.quantile_models: Dict[float, any] = {}

    def fit(
        self,
        model_class,
        X: np.ndarray,
        y: np.ndarray,
        model_params: Dict = None
    ):
        """
        각 분위수별 모델 학습

        Args:
            model_class: 모델 클래스 (예: XGBRegressor)
            X: 입력 피처
            y: 실제 값
            model_params: 모델 파라미터
        """
        from xgboost import XGBRegressor

        model_params = model_params or {}

        # 각 신뢰 구간별 필요한 분위수 계산
        quantiles = set()
        for level in self.confidence_levels:
            alpha = (100 - level) / 100
            lower_q = alpha / 2  # 예: 0.1 for 80%
            upper_q = 1 - alpha / 2  # 예: 0.9 for 80%
            quantiles.add(lower_q)
            quantiles.add(upper_q)

        console.info(f"🎯 Training quantile models for: {sorted(quantiles)}")

        # 각 분위수별 모델 학습
        for q in quantiles:
            console.info(f"   Training quantile {q:.2f}...")

            # XGBoost quantile regression
            if model_class == XGBRegressor:
                qmodel = XGBRegressor(
                    objective='reg:quantileerror',
                    quantile_alpha=q,
                    **model_params
                )
            else:
                raise ValueError(f"Quantile regression not supported for {model_class}")

            qmodel.fit(X, y)
            self.quantile_models[q] = qmodel

        console.info(f"✅ Trained {len(self.quantile_models)} quantile models")

    def generate(
        self,
        X_future: np.ndarray,
        **kwargs
    ) -> Dict[str, np.ndarray]:
        """
        Quantile 예측 구간 생성

        Args:
            X_future: 미래 시점 피처

        Returns:
            dict with 'lo-80', 'hi-80', 'lo-95', 'hi-95'
        """
        if not self.quantile_models:
            raise ValueError("Must call fit() first to train quantile models")

        intervals = {}

        for level in self.confidence_levels:
            alpha = (100 - level) / 100
            lower_q = alpha / 2
            upper_q = 1 - alpha / 2

            # 하한 예측
            if lower_q in self.quantile_models:
                intervals[f'lo-{level}'] = self.quantile_models[lower_q].predict(X_future)

            # 상한 예측
            if upper_q in self.quantile_models:
                intervals[f'hi-{level}'] = self.quantile_models[upper_q].predict(X_future)

        console.info(f"✅ Generated Quantile intervals: {list(intervals.keys())}")
        return intervals


# ============================================================================
# 편의 함수
# ============================================================================

def create_interval_generator(
    method: Literal['conformal', 'bootstrap', 'quantile'],
    **kwargs
) -> PredictionIntervalGenerator:
    """
    예측 구간 생성기 팩토리 함수

    Args:
        method: 'conformal', 'bootstrap', 'quantile' 중 선택
        **kwargs: 각 방법별 파라미터

    Returns:
        PredictionIntervalGenerator 인스턴스

    Example:
        >>> generator = create_interval_generator('conformal', n_windows=5)
        >>> generator.fit(model, X, y)
        >>> intervals = generator.generate(predictions)
    """
    if method == 'conformal':
        return ConformalPrediction(**kwargs)
    elif method == 'bootstrap':
        return BootstrapResiduals(**kwargs)
    elif method == 'quantile':
        return QuantileRegression(**kwargs)
    else:
        raise ValueError(f"Unknown method: {method}. "
                        f"Choose from: 'conformal', 'bootstrap', 'quantile'")


def validate_intervals(
    y_true: np.ndarray,
    lower_bounds: np.ndarray,
    upper_bounds: np.ndarray,
    confidence_level: int = 95
) -> Dict[str, float]:
    """
    예측 구간 품질 검증

    Args:
        y_true: 실제 값
        lower_bounds: 하한 구간
        upper_bounds: 상한 구간
        confidence_level: 목표 신뢰 수준 (예: 95)

    Returns:
        dict with 'coverage', 'interval_width', 'calibration_error'
    """
    # Coverage: 실제 값이 구간 안에 들어간 비율
    in_interval = (y_true >= lower_bounds) & (y_true <= upper_bounds)
    coverage = np.mean(in_interval) * 100

    # Interval Width: 평균 구간 크기
    interval_width = np.mean(upper_bounds - lower_bounds)

    # Calibration Error: 목표와 실제 coverage 차이
    target_coverage = confidence_level
    calibration_error = abs(coverage - target_coverage)

    return {
        'coverage': coverage,
        'target_coverage': target_coverage,
        'interval_width': interval_width,
        'calibration_error': calibration_error
    }
