"""
Test script for the new Method Chaining + Plugin-based Training Pipeline

Usage:
    docker exec reflex-ksys-app python ksys_app/scripts/test_pipeline_builder.py
"""

import asyncio
import sys
sys.path.insert(0, '/app')

from ksys_app.db_orm import get_async_session
from ksys_app.ml.pipeline_builder import TrainingPipeline, PluginRegistry


async def test_method_chaining():
    """Test 1: Method chaining API"""
    print("\n" + "="*80)
    print("TEST 1: Method Chaining API")
    print("="*80)

    async with get_async_session() as session:
        # Fluent API with method chaining
        pipeline = (TrainingPipeline(session)
            .set_data_source("INLET_PRESSURE", days=7)
            .add_feature_engineering(lags=[1, 6, 24], rolling=[6, 24])
            .add_model("auto_arima", seasonal=True, season_length=24)
            .add_model("prophet", changepoint_prior_scale=0.05)
            .add_validation("walk_forward", n_splits=3, test_size=24)
            .set_metrics(["mape", "rmse", "mae"])
            .build()
        )

        # Execute pipeline
        results = await pipeline.execute()

        # Print results
        print("\n📊 Training Results:")
        for model_name, result in results.items():
            metrics = result['metrics']
            print(f"\n   {model_name}:")
            for metric_name, value in metrics.items():
                print(f"      {metric_name.upper()}: {value:.4f}")


async def test_config_based():
    """Test 2: Configuration-based pipeline"""
    print("\n" + "="*80)
    print("TEST 2: Configuration-based Pipeline")
    print("="*80)

    # Define pipeline configuration
    config = {
        "data_source": {
            "tag_name": "FEED_FLOW",
            "days": 7
        },
        "feature_engineering": {
            "lags": [1, 6, 12],
            "rolling": [6, 12],
            "time_features": True
        },
        "models": [
            {
                "type": "auto_arima",
                "params": {
                    "seasonal": True,
                    "season_length": 24
                }
            },
            {
                "type": "prophet",
                "params": {
                    "daily_seasonality": True,
                    "weekly_seasonality": True
                }
            }
        ],
        "validation": {
            "type": "walk_forward",
            "params": {
                "n_splits": 3,
                "test_size": 24
            }
        },
        "metrics": ["mape", "rmse"]
    }

    print("\n📝 Pipeline Configuration:")
    import json
    print(json.dumps(config, indent=2))

    async with get_async_session() as session:
        # Create pipeline from config
        pipeline = TrainingPipeline(session).from_config(config)

        # Execute
        results = await pipeline.execute()

        # Print results
        print("\n📊 Training Results:")
        for model_name, result in results.items():
            metrics = result['metrics']
            print(f"\n   {model_name}:")
            for metric_name, value in metrics.items():
                print(f"      {metric_name.upper()}: {value:.4f}")


async def test_multi_sensor_batch():
    """Test 3: Batch training for multiple sensors"""
    print("\n" + "="*80)
    print("TEST 3: Multi-sensor Batch Training")
    print("="*80)

    sensors = ["INLET_PRESSURE", "FEED_FLOW", "PRODUCT_FLOW"]

    # Shared configuration template
    base_config = {
        "feature_engineering": {
            "lags": [1, 6, 24],
            "rolling": [6, 24]
        },
        "models": [
            {"type": "auto_arima", "params": {"seasonal": True}},
            {"type": "prophet", "params": {}}
        ],
        "validation": {
            "type": "walk_forward",
            "params": {"n_splits": 3, "test_size": 24}
        },
        "metrics": ["mape"]
    }

    all_results = {}

    async with get_async_session() as session:
        for sensor in sensors:
            print(f"\n🔄 Training models for {sensor}...")

            # Create sensor-specific config
            config = {
                **base_config,
                "data_source": {"tag_name": sensor, "days": 7}
            }

            # Train
            pipeline = TrainingPipeline(session).from_config(config)
            results = await pipeline.execute()
            all_results[sensor] = results

    # Print summary
    print("\n" + "="*80)
    print("📊 BATCH TRAINING SUMMARY")
    print("="*80)

    for sensor, results in all_results.items():
        print(f"\n{sensor}:")
        for model_name, result in results.items():
            mape = result['metrics'].get('mape', 0)
            print(f"   {model_name}: MAPE = {mape:.2f}%")


async def test_plugin_listing():
    """Test 4: List available plugins"""
    print("\n" + "="*80)
    print("TEST 4: Available Plugins")
    print("="*80)

    print("\n📦 Built-in Model Plugins:")
    print("   - auto_arima (AutoARIMA from statsforecast)")
    print("   - prophet (Facebook Prophet)")
    print("   - xgboost (XGBoost with feature engineering)")

    print("\n📦 Registered Custom Plugins:")
    plugins = PluginRegistry.list_plugins()
    if plugins:
        for plugin_name in plugins:
            print(f"   - {plugin_name}")
    else:
        print("   (none)")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 TRAINING PIPELINE BUILDER - COMPREHENSIVE TESTS")
    print("="*80)

    try:
        # Test 1: Method chaining
        await test_method_chaining()

        # Test 2: Config-based
        await test_config_based()

        # Test 3: Batch training
        await test_multi_sensor_batch()

        # Test 4: Plugin listing
        await test_plugin_listing()

        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
