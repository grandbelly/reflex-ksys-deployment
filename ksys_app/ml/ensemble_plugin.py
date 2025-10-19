"""
Ensemble Model Plugin for Pipeline V2

앙상블 전략:
1. Simple Average: 모든 모델의 평균
2. Weighted Average: MAPE 기반 가중 평균 (성능 좋은 모델에 더 큰 가중치)
3. Stacking: Meta-learner를 사용한 앙상블

사용 예시:
    pipeline = (TrainingPipelineV2(session)
        .set_data_source("INLET_PRESSURE", days=30)
        .add_model("auto_arima", seasonal=True)
        .add_model("prophet")
        .add_model("ensemble", strategy="weighted", base_models=["auto_arima", "prophet"])
        .build()
    )
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from reflex.utils import console


class EnsembleStrategy(ABC):
    """앙상블 전략 베이스 클래스"""

    @abstractmethod
    def combine(
        self,
        predictions: Dict[str, pd.DataFrame],
        weights: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """예측값들을 결합"""
        pass


class SimpleAverageStrategy(EnsembleStrategy):
    """단순 평균 앙상블"""

    def combine(
        self,
        predictions: Dict[str, pd.DataFrame],
        weights: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """모든 모델의 단순 평균"""
        if not predictions:
            raise ValueError("No predictions to combine")

        # 모든 예측값을 DataFrame 리스트로 변환
        pred_list = []
        for model_name, pred_df in predictions.items():
            # 예측 컬럼 찾기 (모델마다 다름)
            if 'yhat' in pred_df.columns:
                pred_list.append(pred_df['yhat'].values)
            elif 'AutoARIMA' in pred_df.columns:
                pred_list.append(pred_df['AutoARIMA'].values)
            else:
                # 첫 번째 수치 컬럼 사용
                numeric_cols = pred_df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    pred_list.append(pred_df[numeric_cols[0]].values)

        # 평균 계산
        ensemble_pred = np.mean(pred_list, axis=0)

        # DataFrame으로 반환
        result_df = pd.DataFrame({
            'ensemble': ensemble_pred
        })

        console.info(f"   Simple average of {len(predictions)} models")
        return result_df


class WeightedAverageStrategy(EnsembleStrategy):
    """가중 평균 앙상블 (MAPE 기반)"""

    def combine(
        self,
        predictions: Dict[str, pd.DataFrame],
        weights: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """MAPE 기반 가중 평균"""
        if not predictions:
            raise ValueError("No predictions to combine")

        if weights is None:
            # 가중치 없으면 단순 평균으로 fallback
            console.warn("No weights provided, using simple average")
            return SimpleAverageStrategy().combine(predictions)

        # 가중치 정규화 (합이 1이 되도록)
        total_weight = sum(weights.values())
        normalized_weights = {k: v/total_weight for k, v in weights.items()}

        # 가중 평균 계산
        weighted_sum = None
        for model_name, pred_df in predictions.items():
            weight = normalized_weights.get(model_name, 0)

            # 예측 컬럼 찾기
            if 'yhat' in pred_df.columns:
                pred_values = pred_df['yhat'].values
            elif 'AutoARIMA' in pred_df.columns:
                pred_values = pred_df['AutoARIMA'].values
            else:
                numeric_cols = pred_df.select_dtypes(include=[np.number]).columns
                pred_values = pred_df[numeric_cols[0]].values

            if weighted_sum is None:
                weighted_sum = pred_values * weight
            else:
                weighted_sum += pred_values * weight

        result_df = pd.DataFrame({
            'ensemble': weighted_sum
        })

        console.info(f"   Weighted average with weights: {normalized_weights}")
        return result_df


class StackingStrategy(EnsembleStrategy):
    """스태킹 앙상블 (Meta-learner)"""

    def __init__(self, meta_model_type: str = 'linear'):
        """
        Args:
            meta_model_type: 'linear', 'ridge', 'lasso'
        """
        self.meta_model_type = meta_model_type
        self.meta_model = None

    def train_meta_model(
        self,
        base_predictions: Dict[str, np.ndarray],
        true_values: np.ndarray
    ):
        """Meta-learner 학습"""
        from sklearn.linear_model import LinearRegression, Ridge, Lasso

        # Base 모델 예측을 feature로 사용
        X = np.column_stack(list(base_predictions.values()))
        y = true_values

        # Meta-model 생성
        if self.meta_model_type == 'linear':
            self.meta_model = LinearRegression()
        elif self.meta_model_type == 'ridge':
            self.meta_model = Ridge()
        elif self.meta_model_type == 'lasso':
            self.meta_model = Lasso()

        self.meta_model.fit(X, y)
        console.info(f"   Meta-model ({self.meta_model_type}) trained")

    def combine(
        self,
        predictions: Dict[str, pd.DataFrame],
        weights: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """Meta-learner로 예측 결합"""
        if self.meta_model is None:
            console.warn("Meta-model not trained, using simple average")
            return SimpleAverageStrategy().combine(predictions)

        # Base 모델 예측을 feature로 변환
        pred_list = []
        for model_name, pred_df in predictions.items():
            if 'yhat' in pred_df.columns:
                pred_list.append(pred_df['yhat'].values)
            elif 'AutoARIMA' in pred_df.columns:
                pred_list.append(pred_df['AutoARIMA'].values)
            else:
                numeric_cols = pred_df.select_dtypes(include=[np.number]).columns
                pred_list.append(pred_df[numeric_cols[0]].values)

        X = np.column_stack(pred_list)

        # Meta-model 예측
        ensemble_pred = self.meta_model.predict(X)

        result_df = pd.DataFrame({
            'ensemble': ensemble_pred
        })

        console.info(f"   Stacking with {self.meta_model_type} meta-model")
        return result_df


# ============================================================================
# Ensemble Model Plugin for Pipeline V2
# ============================================================================

class EnsembleModelPlugin:
    """
    앙상블 모델 플러그인

    여러 base 모델의 예측을 결합하여 더 나은 예측 생성

    Note: ModelPlugin 상속하지 않음 (다른 모델들을 결합하는 특수 플러그인)
    """

    def __init__(
        self,
        strategy: str = "weighted",
        base_models: Optional[List[str]] = None,
        meta_model_type: str = "linear"
    ):
        """
        Args:
            strategy: 'simple', 'weighted', 'stacking'
            base_models: 결합할 base 모델 이름 리스트
            meta_model_type: stacking 전략에서 사용할 meta-model
        """
        self.strategy_name = strategy
        self.base_models = base_models or []
        self.meta_model_type = meta_model_type

        # 전략 객체 생성
        if strategy == "simple":
            self.strategy = SimpleAverageStrategy()
        elif strategy == "weighted":
            self.strategy = WeightedAverageStrategy()
        elif strategy == "stacking":
            self.strategy = StackingStrategy(meta_model_type)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        self.trained_models = {}
        self.model_weights = {}

    def get_name(self) -> str:
        return f"ensemble_{self.strategy_name}"

    def register_base_model(self, name: str, model: Any, mape: float):
        """Base 모델 등록"""
        self.trained_models[name] = model

        # MAPE 기반 가중치 계산 (낮을수록 좋음)
        # weight = 1 / (1 + mape)
        self.model_weights[name] = 1.0 / (1.0 + mape)

        console.info(f"   Registered {name} with MAPE={mape:.2f}%, weight={self.model_weights[name]:.4f}")

    async def train(self, data: pd.DataFrame) -> Any:
        """
        앙상블은 base 모델들이 이미 학습되어 있다고 가정
        Stacking의 경우 meta-model 학습
        """
        console.info(f"✅ Ensemble ({self.strategy_name}) ready with {len(self.trained_models)} base models")

        if isinstance(self.strategy, StackingStrategy):
            # Stacking: meta-model 학습 필요
            # (실제 구현에서는 validation set에서 base 예측을 생성해야 함)
            console.info("   Note: Stacking meta-model training not implemented yet")

        return self

    async def predict(self, horizon: int) -> pd.DataFrame:
        """Base 모델들의 예측을 결합"""
        if not self.trained_models:
            raise ValueError("No base models registered")

        # 각 base 모델로 예측
        predictions = {}
        for model_name, model in self.trained_models.items():
            pred = await model.predict(horizon)
            predictions[model_name] = pred

        # 전략에 따라 결합
        ensemble_pred = self.strategy.combine(predictions, self.model_weights)

        console.info(f"✅ Ensemble prediction generated (horizon={horizon})")
        return ensemble_pred


# ============================================================================
# Helper Function: Create Ensemble from Pipeline Results
# ============================================================================

def create_ensemble_from_results(
    pipeline_results: Dict[str, Any],
    strategy: str = "weighted",
    meta_model_type: str = "linear"
) -> EnsembleModelPlugin:
    """
    파이프라인 실행 결과에서 앙상블 생성

    Args:
        pipeline_results: pipeline.execute() 결과
        strategy: 앙상블 전략
        meta_model_type: stacking meta-model 타입

    Returns:
        EnsembleModelPlugin

    Example:
        result = await pipeline.execute()
        ensemble = create_ensemble_from_results(result['results'], strategy='weighted')
        prediction = await ensemble.predict(horizon=24)
    """
    # Base 모델 이름 추출
    base_model_names = list(pipeline_results.keys())

    # 앙상블 생성
    ensemble = EnsembleModelPlugin(
        strategy=strategy,
        base_models=base_model_names,
        meta_model_type=meta_model_type
    )

    # Base 모델 등록
    for model_name, result in pipeline_results.items():
        model = result['model']
        mape = result['metrics'].get('mape', 100.0)
        ensemble.register_base_model(model_name, model, mape)

    return ensemble


# ============================================================================
# Example Usage
# ============================================================================

async def example_ensemble_usage():
    """앙상블 사용 예시"""
    from ksys_app.ml.pipeline_v2_hybrid import TrainingPipelineV2
    from ksys_app.db_orm import get_async_session

    async with get_async_session() as session:
        # 1. 여러 모델 학습
        pipeline = (TrainingPipelineV2(session)
            .set_data_source("INLET_PRESSURE", days=30)
            .add_feature_engineering()
                .add_lag([1, 6, 24])
                .add_rolling([6, 24])
            .done()
            .add_model("auto_arima", seasonal=True)
            .add_model("prophet")
            .add_validation("walk_forward", n_splits=5)
            .build()
        )

        result = await pipeline.execute()

        # 2. 앙상블 생성
        ensemble = create_ensemble_from_results(
            result['results'],
            strategy='weighted'  # 'simple', 'weighted', 'stacking'
        )

        # 3. 예측
        forecast = await ensemble.predict(horizon=24)
        print(f"Ensemble forecast: {forecast}")

        return ensemble
