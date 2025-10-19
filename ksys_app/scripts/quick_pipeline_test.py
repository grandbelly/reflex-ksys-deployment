"""
Quick Pipeline V2 Test (7 days data only)

Usage:
    docker exec reflex-ksys-app python ksys_app/scripts/quick_pipeline_test.py
"""

import asyncio
import sys
import json
sys.path.insert(0, '/app')

from ksys_app.db_orm import get_async_session
from ksys_app.ml.pipeline_v2_hybrid import TrainingPipelineV2


async def quick_test():
    """Quick test with preprocessing chain"""
    print("\n" + "="*80)
    print("🧪 QUICK TEST: Pipeline V2 with Preprocessing (3 days data)")
    print("="*80)

    async with get_async_session() as session:
        pipeline = (TrainingPipelineV2(session)
            .set_data_source("INLET_PRESSURE", days=3)  # Only 3 days
            .add_preprocessing()
                .interpolate(method='linear')
                .remove_outliers(threshold=3.0)
            .done()
            .add_feature_engineering()
                .add_lag([1, 6])  # Only 2 lag features
                .add_rolling([6])  # Only 1 rolling window
            .done()
            .add_model("auto_arima", seasonal=False)  # Disable seasonality for speed
            .build()
        )

        print("\n🚀 Executing pipeline...")
        result = await pipeline.execute()

        print("\n" + "="*80)
        print("✅ RESULTS")
        print("="*80)

        # Results
        if result['results']:
            for model_name, model_result in result['results'].items():
                metrics = model_result.get('metrics', {})
                if metrics:
                    print(f"\n{model_name}:")
                    for metric_name, value in metrics.items():
                        print(f"   {metric_name.upper()}: {value:.4f}")

        # Metadata
        print("\n📊 METADATA:")
        metadata = result['metadata']
        print(f"   Tag: {metadata.tag_name}")
        print(f"   Raw samples: {metadata.raw_samples}")
        print(f"   Processed samples: {metadata.processed_samples}")
        print(f"   Outliers removed: {metadata.outliers_removed}")
        print(f"   Interpolated gaps: {metadata.interpolated_gaps}")
        print(f"   Preprocessing steps: {metadata.preprocessing_steps}")
        print(f"   Features created: {len(metadata.features_created)}")
        print(f"   Models trained: {metadata.models_trained}")
        print(f"   Training duration: {metadata.training_duration:.2f}s")

        if metadata.best_model:
            print(f"\n🏆 Best Model: {metadata.best_model} (MAPE: {metadata.best_mape:.2f}%)")

        print("\n" + "="*80)
        print("✅ TEST COMPLETED SUCCESSFULLY")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(quick_test())
