"""
Postprocessing Chain for Pipeline V2

후처리 단계:
1. Clip: 예측값을 물리적 범위로 제한
2. Smooth: 예측값을 smoothing (이동 평균)
3. Validate: 예측값 검증 및 이상치 제거
4. Transform: 역변환 (예: scaled → original)

사용 예시:
    pipeline = (TrainingPipelineV2(session)
        .set_data_source("INLET_PRESSURE", days=30)
        .add_model("auto_arima")
        .add_postprocessing()
            .clip(min_value=0, max_value=5000)
            .smooth(window=3)
            .validate(check_negative=True, check_jumps=True)
        .done()
        .build()
    )
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from reflex.utils import console


# ============================================================================
# Postprocessing Steps
# ============================================================================

class PostprocessingStep(ABC):
    """후처리 단계 베이스 클래스"""

    @abstractmethod
    async def apply(self, predictions: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """후처리 적용"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """단계 이름"""
        pass


class ClipStep(PostprocessingStep):
    """예측값을 물리적 범위로 제한"""

    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None):
        self.min_value = min_value
        self.max_value = max_value

    async def apply(self, predictions: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Clip predictions to physical range"""
        df = predictions.copy()

        # 예측 컬럼 찾기
        pred_col = self._find_prediction_column(df)

        original_min = df[pred_col].min()
        original_max = df[pred_col].max()

        # Clip
        if self.min_value is not None:
            df[pred_col] = df[pred_col].clip(lower=self.min_value)
        if self.max_value is not None:
            df[pred_col] = df[pred_col].clip(upper=self.max_value)

        clipped_min = df[pred_col].min()
        clipped_max = df[pred_col].max()

        metadata['postprocessing_steps'] = metadata.get('postprocessing_steps', [])
        metadata['postprocessing_steps'].append(self.get_name())

        console.info(f"   ✓ Clipped: [{original_min:.2f}, {original_max:.2f}] → [{clipped_min:.2f}, {clipped_max:.2f}]")

        return df

    def get_name(self) -> str:
        return f"clip_{self.min_value}_{self.max_value}"

    def _find_prediction_column(self, df: pd.DataFrame) -> str:
        """예측 컬럼 찾기"""
        for col in ['yhat', 'ensemble', 'AutoARIMA', 'prediction', 'forecast']:
            if col in df.columns:
                return col

        # 첫 번째 수치 컬럼 사용
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            return numeric_cols[0]

        raise ValueError("No prediction column found")


class SmoothStep(PostprocessingStep):
    """예측값 smoothing (이동 평균)"""

    def __init__(self, window: int = 3, method: str = 'rolling'):
        """
        Args:
            window: smoothing window size
            method: 'rolling' or 'ewm' (exponential weighted moving average)
        """
        self.window = window
        self.method = method

    async def apply(self, predictions: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Smooth predictions"""
        df = predictions.copy()

        pred_col = self._find_prediction_column(df)
        original_std = df[pred_col].std()

        # Smoothing
        if self.method == 'rolling':
            df[pred_col] = df[pred_col].rolling(window=self.window, center=True).mean()
            # Fill NaN values at edges
            df[pred_col] = df[pred_col].bfill().ffill()
        elif self.method == 'ewm':
            df[pred_col] = df[pred_col].ewm(span=self.window).mean()

        smoothed_std = df[pred_col].std()

        metadata['postprocessing_steps'] = metadata.get('postprocessing_steps', [])
        metadata['postprocessing_steps'].append(self.get_name())

        console.info(f"   ✓ Smoothed: std {original_std:.2f} → {smoothed_std:.2f} (method={self.method}, window={self.window})")

        return df

    def get_name(self) -> str:
        return f"smooth_{self.method}_{self.window}"

    def _find_prediction_column(self, df: pd.DataFrame) -> str:
        for col in ['yhat', 'ensemble', 'AutoARIMA', 'prediction', 'forecast']:
            if col in df.columns:
                return col
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            return numeric_cols[0]
        raise ValueError("No prediction column found")


class ValidateStep(PostprocessingStep):
    """예측값 검증 및 이상치 제거"""

    def __init__(
        self,
        check_negative: bool = True,
        check_jumps: bool = True,
        max_jump_percent: float = 50.0,
        replace_invalid: str = 'interpolate'  # 'interpolate', 'drop', 'clip'
    ):
        """
        Args:
            check_negative: 음수 체크
            check_jumps: 급격한 변화 체크
            max_jump_percent: 최대 변화율 (%)
            replace_invalid: 이상치 처리 방법
        """
        self.check_negative = check_negative
        self.check_jumps = check_jumps
        self.max_jump_percent = max_jump_percent
        self.replace_invalid = replace_invalid

    async def apply(self, predictions: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Validate and clean predictions"""
        df = predictions.copy()

        pred_col = self._find_prediction_column(df)
        invalid_mask = pd.Series(False, index=df.index)

        # Check negative values
        if self.check_negative:
            negative_mask = df[pred_col] < 0
            invalid_mask |= negative_mask
            negative_count = negative_mask.sum()
            if negative_count > 0:
                console.warn(f"   Found {negative_count} negative values")

        # Check jumps
        if self.check_jumps:
            pct_change = df[pred_col].pct_change().abs() * 100
            jump_mask = pct_change > self.max_jump_percent
            invalid_mask |= jump_mask
            jump_count = jump_mask.sum()
            if jump_count > 0:
                console.warn(f"   Found {jump_count} jumps > {self.max_jump_percent}%")

        # Replace invalid values
        invalid_count = invalid_mask.sum()
        if invalid_count > 0:
            if self.replace_invalid == 'interpolate':
                df.loc[invalid_mask, pred_col] = np.nan
                df[pred_col] = df[pred_col].interpolate(method='linear')
                console.info(f"   ✓ Interpolated {invalid_count} invalid values")
            elif self.replace_invalid == 'drop':
                df = df[~invalid_mask]
                console.info(f"   ✓ Dropped {invalid_count} invalid values")
            elif self.replace_invalid == 'clip':
                if self.check_negative:
                    df.loc[df[pred_col] < 0, pred_col] = 0
                console.info(f"   ✓ Clipped {invalid_count} invalid values")

        metadata['postprocessing_steps'] = metadata.get('postprocessing_steps', [])
        metadata['postprocessing_steps'].append(self.get_name())
        metadata['invalid_predictions_removed'] = metadata.get('invalid_predictions_removed', 0) + invalid_count

        return df

    def get_name(self) -> str:
        return f"validate_{self.replace_invalid}"

    def _find_prediction_column(self, df: pd.DataFrame) -> str:
        for col in ['yhat', 'ensemble', 'AutoARIMA', 'prediction', 'forecast']:
            if col in df.columns:
                return col
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            return numeric_cols[0]
        raise ValueError("No prediction column found")


class TransformStep(PostprocessingStep):
    """역변환 (scaled → original)"""

    def __init__(self, scaler_type: str = 'standard', scaler_params: Optional[Dict] = None):
        """
        Args:
            scaler_type: 'standard', 'minmax'
            scaler_params: {'mean': ..., 'std': ...} or {'min': ..., 'max': ...}
        """
        self.scaler_type = scaler_type
        self.scaler_params = scaler_params or {}

    async def apply(self, predictions: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """Inverse transform predictions"""
        df = predictions.copy()

        pred_col = self._find_prediction_column(df)

        # Inverse transform
        if self.scaler_type == 'standard':
            mean = self.scaler_params.get('mean', 0)
            std = self.scaler_params.get('std', 1)
            df[pred_col] = df[pred_col] * std + mean
            console.info(f"   ✓ Inverse standard scaling (mean={mean:.2f}, std={std:.2f})")
        elif self.scaler_type == 'minmax':
            min_val = self.scaler_params.get('min', 0)
            max_val = self.scaler_params.get('max', 1)
            df[pred_col] = df[pred_col] * (max_val - min_val) + min_val
            console.info(f"   ✓ Inverse minmax scaling (min={min_val:.2f}, max={max_val:.2f})")

        metadata['postprocessing_steps'] = metadata.get('postprocessing_steps', [])
        metadata['postprocessing_steps'].append(self.get_name())

        return df

    def get_name(self) -> str:
        return f"transform_{self.scaler_type}"

    def _find_prediction_column(self, df: pd.DataFrame) -> str:
        for col in ['yhat', 'ensemble', 'AutoARIMA', 'prediction', 'forecast']:
            if col in df.columns:
                return col
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            return numeric_cols[0]
        raise ValueError("No prediction column found")


# ============================================================================
# Postprocessing Chain Builder
# ============================================================================

class PostprocessingChain:
    """후처리 체인 빌더"""

    def __init__(self):
        self.steps = []

    def clip(self, min_value: Optional[float] = None, max_value: Optional[float] = None) -> 'PostprocessingChain':
        """예측값을 물리적 범위로 제한"""
        self.steps.append(ClipStep(min_value, max_value))
        return self

    def smooth(self, window: int = 3, method: str = 'rolling') -> 'PostprocessingChain':
        """예측값 smoothing"""
        self.steps.append(SmoothStep(window, method))
        return self

    def validate(
        self,
        check_negative: bool = True,
        check_jumps: bool = True,
        max_jump_percent: float = 50.0,
        replace_invalid: str = 'interpolate'
    ) -> 'PostprocessingChain':
        """예측값 검증"""
        self.steps.append(ValidateStep(check_negative, check_jumps, max_jump_percent, replace_invalid))
        return self

    def transform(self, scaler_type: str = 'standard', scaler_params: Optional[Dict] = None) -> 'PostprocessingChain':
        """역변환"""
        self.steps.append(TransformStep(scaler_type, scaler_params))
        return self

    async def apply(self, predictions: pd.DataFrame) -> pd.DataFrame:
        """모든 후처리 단계 적용"""
        df = predictions.copy()
        metadata = {}

        console.info(f"🧹 Applying {len(self.steps)} postprocessing steps...")

        for step in self.steps:
            df = await step.apply(df, metadata)

        console.info(f"✅ Postprocessing complete: {metadata.get('postprocessing_steps', [])}")

        return df


# ============================================================================
# Example Usage
# ============================================================================

async def example_postprocessing():
    """후처리 사용 예시"""

    # 가상의 예측 데이터
    predictions = pd.DataFrame({
        'yhat': [100, 150, -10, 200, 500, 180, 190, 195]  # 음수와 급격한 변화 포함
    })

    print("Original predictions:")
    print(predictions)

    # 후처리 체인 생성
    postprocessor = (PostprocessingChain()
        .validate(check_negative=True, check_jumps=True, max_jump_percent=50)
        .clip(min_value=0, max_value=300)
        .smooth(window=3, method='rolling')
    )

    # 적용
    cleaned = await postprocessor.apply(predictions)

    print("\nCleaned predictions:")
    print(cleaned)

    return cleaned
