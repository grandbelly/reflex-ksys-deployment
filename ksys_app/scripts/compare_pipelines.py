"""
파이프라인 설계 비교 데모

1. 기존 V1 (pipeline_builder.py)
2. 하이브리드 V2 (pipeline_v2_hybrid.py)
3. 설정 기반 팩토리 패턴

Usage:
    docker exec reflex-ksys-app python ksys_app/scripts/compare_pipelines.py
"""

import asyncio
import sys
import json
sys.path.insert(0, '/app')

from ksys_app.db_orm import get_async_session
from ksys_app.ml.pipeline_builder import TrainingPipeline as V1Pipeline
from ksys_app.ml.pipeline_v2_hybrid import TrainingPipelineV2, create_pipeline_from_config


async def demo_v1_basic():
    """V1: 기본 메서드 체이닝 (전처리 없음)"""
    print("\n" + "="*80)
    print("📦 DEMO 1: Pipeline V1 - Basic Method Chaining")
    print("="*80)

    async with get_async_session() as session:
        pipeline = (V1Pipeline(session)
            .set_data_source("INLET_PRESSURE", days=7)
            .add_feature_engineering(lags=[1, 6, 24], rolling=[6, 24])
            .add_model("auto_arima", seasonal=True)
            .add_validation("walk_forward", n_splits=3, test_size=24)
            .build()
        )

        results = await pipeline.execute()

        print("\n✅ Results:")
        for model_name, result in results.items():
            print(f"   {model_name}: MAPE = {result['metrics']['mape']:.2f}%")


async def demo_v2_preprocessing():
    """V2: 전처리 체인 포함"""
    print("\n" + "="*80)
    print("📦 DEMO 2: Pipeline V2 - With Preprocessing Chain")
    print("="*80)

    async with get_async_session() as session:
        pipeline = (TrainingPipelineV2(session)
            .set_data_source("INLET_PRESSURE", days=7)
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
            .add_validation("walk_forward", n_splits=3, test_size=24)
            .build()
        )

        result = await pipeline.execute()

        print("\n✅ Results:")
        for model_name, model_result in result['results'].items():
            print(f"   {model_name}: MAPE = {model_result['metrics']['mape']:.2f}%")

        print("\n📊 Metadata:")
        metadata = result['metadata'].to_dict()
        print(f"   Raw samples: {metadata['raw_samples']}")
        print(f"   Processed samples: {metadata['processed_samples']}")
        print(f"   Outliers removed: {metadata['outliers_removed']}")
        print(f"   Features created: {len(metadata['features_created'])}")
        print(f"   Best model: {metadata['best_model']}")
        print(f"   Best MAPE: {metadata['best_mape']:.2f}%")
        print(f"   Training duration: {result['metadata'].training_duration:.2f}s")


async def demo_v2_config_based():
    """V2: 설정 기반 팩토리"""
    print("\n" + "="*80)
    print("📦 DEMO 3: Pipeline V2 - Configuration-based Factory")
    print("="*80)

    # 설정 정의
    config = {
        "data_source": {
            "tag_name": "FEED_FLOW",
            "days": 7
        },
        "preprocessing": [
            {"type": "interpolate", "params": {"method": "linear"}},
            {"type": "remove_outliers", "params": {"threshold": 3.0}},
            {"type": "scale", "params": {"method": "standard"}}
        ],
        "feature_engineering": {
            "lags": [1, 6, 24],
            "rolling": [6, 24],
            "temporal": ["hour", "dayofweek"]
        },
        "models": [
            {"type": "auto_arima", "params": {"seasonal": True}},
            {"type": "prophet", "params": {}}
        ],
        "validation": {
            "type": "walk_forward",
            "params": {"n_splits": 3, "test_size": 24}
        }
    }

    print("\n📝 Configuration:")
    print(json.dumps(config, indent=2))

    async with get_async_session() as session:
        pipeline = await create_pipeline_from_config(session, config)
        result = await pipeline.execute()

        print("\n✅ Results:")
        for model_name, model_result in result['results'].items():
            print(f"   {model_name}: MAPE = {model_result['metrics']['mape']:.2f}%")

        print("\n📊 Full Metadata:")
        print(json.dumps(result['metadata'].to_dict(), indent=2, default=str))


async def demo_v2_custom_model():
    """V2: 커스텀 모델 등록"""
    print("\n" + "="*80)
    print("📦 DEMO 4: Pipeline V2 - Custom Model Registration")
    print("="*80)

    from ksys_app.ml.pipeline_v2_hybrid import ModelRegistry, ModelPlugin
    import pandas as pd

    # 간단한 커스텀 모델 (이동 평균)
    class MovingAveragePlugin(ModelPlugin):
        def get_name(self) -> str:
            return "moving_average"

        async def train(self, data: pd.DataFrame):
            self.window = self.params.get('window', 24)
            self.model = data['value'].rolling(self.window).mean()
            return self.model

        async def predict(self, horizon: int):
            # 간단한 구현 - 마지막 값 반복
            last_value = self.model.iloc[-1]
            return pd.DataFrame({
                'MovingAverage': [last_value] * horizon
            })

    # 등록
    ModelRegistry.register('moving_average', MovingAveragePlugin)

    print("\n📦 Registered custom model: moving_average")
    print(f"   Available models: {ModelRegistry.list_models()}")

    async with get_async_session() as session:
        pipeline = (TrainingPipelineV2(session)
            .set_data_source("INLET_PRESSURE", days=7)
            .add_preprocessing()
                .interpolate(method='linear')
            .done()
            .add_model("moving_average", window=24)
            .add_model("auto_arima", seasonal=True)
            .build()
        )

        result = await pipeline.execute()

        print("\n✅ Models trained:")
        for model_name in result['metadata'].models_trained:
            print(f"   - {model_name}")


async def main():
    """모든 데모 실행"""
    print("\n" + "="*80)
    print("🧪 PIPELINE DESIGN COMPARISON - COMPREHENSIVE DEMOS")
    print("="*80)

    try:
        # Demo 1: V1 기본
        await demo_v1_basic()

        # Demo 2: V2 전처리 체인
        await demo_v2_preprocessing()

        # Demo 3: V2 설정 기반
        await demo_v2_config_based()

        # Demo 4: V2 커스텀 모델
        await demo_v2_custom_model()

        print("\n" + "="*80)
        print("✅ ALL DEMOS COMPLETED")
        print("="*80)

        print("\n📋 SUMMARY:")
        print("\n V1 (pipeline_builder.py):")
        print("   ✅ 빠른 시작 - 3개 모델 즉시 사용")
        print("   ✅ 검증 통합 - Walk-forward validation")
        print("   ❌ 전처리 부족 - interpolation, outlier 제거 없음")
        print("   ❌ 메타데이터 부족")

        print("\n V2 (pipeline_v2_hybrid.py):")
        print("   ✅ 완전한 전처리 체인 - interpolate, outlier, scale")
        print("   ✅ 메타데이터 추적 - 전체 파이프라인 정보")
        print("   ✅ 레지스트리 패턴 - 동적 모델 추가")
        print("   ✅ 두 가지 API - 메서드 체이닝 + 설정 기반")
        print("   ✅ 타입 안정성 유지")

        print("\n 제안하신 FlexibleTrainingPipeline:")
        print("   ✅ 완전한 체인 구성")
        print("   ✅ 메타데이터 전달")
        print("   ❌ 타입 안정성 낮음 (딕셔너리 기반)")
        print("   ❌ 추상화 과다")

        print("\n🎯 RECOMMENDATION:")
        print("   → Use V2 for production (best of both worlds)")
        print("   → Keep V1 for quick prototyping")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
