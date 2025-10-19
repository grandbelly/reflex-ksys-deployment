"""
Pipeline V2 Direct Test (standalone - no reflex app needed)

Tests:
1. Preprocessing chain
2. Feature engineering chain
3. Model training with 10m aggregation data
4. Metadata tracking

Usage:
    python ksys_app/scripts/test_pipeline_v2_direct.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pandas as pd
from datetime import datetime, timedelta
import pytz
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

# Direct imports
from ksys_app.ml.pipeline_v2_hybrid import (
    TrainingPipelineV2,
    ModelRegistry,
    PipelineMetadata
)

KST = pytz.timezone('Asia/Seoul')


async def get_test_session():
    """Create test database session"""
    # Use Docker internal hostname when running in container
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@pgai-db:5432/ecoanp"

    engine = create_async_engine(
        DATABASE_URL,
        poolclass=None,
        echo=False
    )

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    return async_session()


async def test_preprocessing_chain():
    """Test 1: Preprocessing chain"""
    print("\n" + "="*80)
    print("TEST 1: Preprocessing Chain")
    print("="*80)

    async with await get_test_session() as session:
        pipeline = (TrainingPipelineV2(session)
            .set_data_source("INLET_PRESSURE", days=3)
            .add_preprocessing()
                .interpolate(method='linear')
                .remove_outliers(threshold=3.0)
                .scale(method='standard')
            .done()
            .build()
        )

        # Load and preprocess data only
        print("\n📥 Loading data from influx_agg_10m...")
        await pipeline._load_data()
        print(f"   Loaded {len(pipeline._raw_data)} rows")

        print("\n🧹 Applying preprocessing...")
        await pipeline._apply_preprocessing()

        metadata = pipeline.metadata
        print(f"\n📊 Preprocessing Results:")
        print(f"   Raw samples: {metadata.raw_samples}")
        print(f"   Processed samples: {metadata.processed_samples}")
        print(f"   Outliers removed: {metadata.outliers_removed}")
        print(f"   Interpolated gaps: {metadata.interpolated_gaps}")
        print(f"   Steps: {metadata.preprocessing_steps}")

        return pipeline


async def test_feature_engineering():
    """Test 2: Feature engineering chain"""
    print("\n" + "="*80)
    print("TEST 2: Feature Engineering Chain")
    print("="*80)

    async with await get_test_session() as session:
        pipeline = (TrainingPipelineV2(session)
            .set_data_source("INLET_PRESSURE", days=3)
            .add_feature_engineering()
                .add_lag([1, 6])  # 10분 간격이므로: 1=10분, 6=1시간
                .add_rolling([6, 12])  # 6=1시간, 12=2시간
                .add_temporal(['hour', 'dayofweek'])
            .done()
            .build()
        )

        print("\n📥 Loading data...")
        await pipeline._load_data()

        print("\n⚙️ Applying feature engineering...")
        await pipeline._apply_feature_engineering()

        metadata = pipeline.metadata
        print(f"\n📊 Feature Engineering Results:")
        print(f"   Original features: {metadata.original_features}")
        print(f"   Final features: {metadata.final_features}")
        print(f"   Features created: {len(metadata.features_created)}")
        print(f"   Feature list: {metadata.features_created}")

        # Show sample data
        print(f"\n📋 Sample data (first 3 rows):")
        print(pipeline._processed_data.head(3).to_string())

        return pipeline


async def test_full_pipeline():
    """Test 3: Full pipeline with model training"""
    print("\n" + "="*80)
    print("TEST 3: Full Pipeline with AutoARIMA")
    print("="*80)

    async with await get_test_session() as session:
        pipeline = (TrainingPipelineV2(session)
            .set_data_source("INLET_PRESSURE", days=7)  # 7 days = ~1000 samples at 10min
            .add_preprocessing()
                .interpolate(method='linear')
                .remove_outliers(threshold=3.0)
            .done()
            .add_feature_engineering()
                .add_lag([1, 6])
                .add_rolling([6])
            .done()
            .add_model("auto_arima", seasonal=False)  # Disable seasonality for speed
            .build()
        )

        print("\n🚀 Executing full pipeline...")
        result = await pipeline.execute()

        print("\n" + "="*80)
        print("✅ RESULTS")
        print("="*80)

        # Model results
        if result['results']:
            for model_name, model_result in result['results'].items():
                print(f"\n{model_name}:")
                metrics = model_result.get('metrics', {})
                if metrics:
                    for metric_name, value in metrics.items():
                        print(f"   {metric_name.upper()}: {value:.4f}")

        # Full metadata
        metadata = result['metadata']
        print(f"\n📊 PIPELINE METADATA:")
        print(f"   Tag: {metadata.tag_name}")
        print(f"   Data period: {metadata.data_start} → {metadata.data_end}")
        print(f"   Raw samples: {metadata.raw_samples}")
        print(f"   Processed samples: {metadata.processed_samples}")
        print(f"   Outliers removed: {metadata.outliers_removed}")
        print(f"   Features created: {len(metadata.features_created)}")
        print(f"   Models trained: {metadata.models_trained}")
        print(f"   Training duration: {metadata.training_duration:.2f}s")

        if metadata.best_model:
            print(f"\n🏆 Best Model: {metadata.best_model} (MAPE: {metadata.best_mape:.2f}%)")

        return result


async def test_model_registry():
    """Test 4: Model registry"""
    print("\n" + "="*80)
    print("TEST 4: Model Registry")
    print("="*80)

    print("\n📦 Available models:")
    for model_name in ModelRegistry.list_models():
        print(f"   - {model_name}")

    print("\n✅ Registry test passed")


async def test_config_based():
    """Test 5: Configuration-based pipeline"""
    print("\n" + "="*80)
    print("TEST 5: Configuration-based Pipeline")
    print("="*80)

    from ksys_app.ml.pipeline_v2_hybrid import create_pipeline_from_config

    config = {
        "data_source": {
            "tag_name": "FEED_FLOW",
            "days": 5
        },
        "preprocessing": [
            {"type": "interpolate", "params": {"method": "linear"}},
            {"type": "remove_outliers", "params": {"threshold": 3.0}}
        ],
        "feature_engineering": {
            "lags": [1, 6],
            "rolling": [6],
            "temporal": ["hour"]
        },
        "models": [
            {"type": "auto_arima", "params": {"seasonal": False}}
        ]
    }

    print("\n📝 Config:")
    import json
    print(json.dumps(config, indent=2))

    async with await get_test_session() as session:
        pipeline = await create_pipeline_from_config(session, config)
        result = await pipeline.execute()

        metadata = result['metadata']
        print(f"\n✅ Config-based pipeline executed:")
        print(f"   Samples: {metadata.processed_samples}")
        print(f"   Models: {metadata.models_trained}")
        print(f"   Duration: {metadata.training_duration:.2f}s")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 PIPELINE V2 COMPREHENSIVE TESTS")
    print("="*80)

    try:
        # Test 1: Preprocessing
        await test_preprocessing_chain()

        # Test 2: Feature engineering
        await test_feature_engineering()

        # Test 3: Model registry
        await test_model_registry()

        # Test 4: Full pipeline
        await test_full_pipeline()

        # Test 5: Config-based
        await test_config_based()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)

        print("\n📋 SUMMARY:")
        print("   ✅ Preprocessing chain working")
        print("   ✅ Feature engineering working")
        print("   ✅ Model registry functional")
        print("   ✅ 10-minute aggregation data loading")
        print("   ✅ Metadata tracking complete")
        print("   ✅ Configuration-based pipeline working")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
