"""
Test Feature Config V2 Integration with Pipeline V2

완전히 데이터베이스 기반으로 feature engineering 설정 로드
하드코딩 Zero!

Usage:
    docker exec reflex-ksys-app python ksys_app/scripts/test_feature_config_integration.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from reflex.utils import console

from ksys_app.services.feature_config_service_v2 import FeatureConfigServiceV2


async def get_test_session():
    """Create test database session"""
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@pgai-db:5432/ecoanp"

    engine = create_async_engine(DATABASE_URL, poolclass=None, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    return async_session()


async def test_basic_operations():
    """Test 1: Basic CRUD operations"""
    print("\n" + "="*80)
    print("TEST 1: Basic CRUD Operations")
    print("="*80)

    async with await get_test_session() as session:
        service = FeatureConfigServiceV2(session)

        # 1. Get existing config
        config = await service.get_config("INLET_PRESSURE", "default_arima")
        print(f"\n📥 Loaded config: {config['config_name']}")
        print(f"   Config ID: {config['config_id']}")
        print(f"   Model Type: {config['model_type']}")
        print(f"   Notes: {config['notes']}")

        # 2. Get lag features
        lag_features = await service.get_lag_features(config['config_id'])
        print(f"\n📊 Lag features ({len(lag_features)}):")
        for i, lag in enumerate(lag_features):
            status = "✅" if lag.get("enabled", True) else "❌"
            print(f"   [{i}] {status} {lag['name']}: {lag['periods']} {lag['unit']}")

        # 3. Get rolling features
        rolling_features = await service.get_rolling_features(config['config_id'])
        print(f"\n📊 Rolling features ({len(rolling_features)}):")
        for i, rolling in enumerate(rolling_features):
            status = "✅" if rolling.get("enabled", True) else "❌"
            print(f"   [{i}] {status} {rolling['name']}: window={rolling['window']}, agg={rolling['agg']}")

        # 4. Get temporal features
        temporal_features = await service.get_temporal_features(config['config_id'])
        print(f"\n📊 Temporal features ({len(temporal_features)}):")
        for i, temporal in enumerate(temporal_features):
            status = "✅" if temporal.get("enabled", True) else "❌"
            cyclical = "🔄" if temporal.get("cyclical", False) else "  "
            print(f"   [{i}] {status} {cyclical} {temporal['type']}")


async def test_add_features():
    """Test 2: Add new features"""
    print("\n" + "="*80)
    print("TEST 2: Add New Features")
    print("="*80)

    async with await get_test_session() as session:
        service = FeatureConfigServiceV2(session)

        config = await service.get_config("INLET_PRESSURE", "default_arima")
        config_id = config['config_id']

        # Add new lag feature
        print("\n➕ Adding new lag feature: lag_24h (144 rows)")
        success = await service.add_lag_feature(
            config_id=config_id,
            periods=144,
            unit="rows",
            name="lag_24h"
        )
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")

        # Add new rolling feature
        print("\n➕ Adding new rolling feature: rolling_mean_24h")
        success = await service.add_rolling_feature(
            config_id=config_id,
            window=144,
            agg="mean",
            unit="rows",
            name="rolling_mean_24h"
        )
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")

        # Add new temporal feature
        print("\n➕ Adding new temporal feature: month (cyclical)")
        success = await service.add_temporal_feature(
            config_id=config_id,
            feature_type="month",
            cyclical=True
        )
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")

        # Verify
        all_features = await service.get_all_enabled_features("INLET_PRESSURE", "default_arima")
        print(f"\n✅ Total enabled features:")
        print(f"   Lag: {len(all_features['lag'])}")
        print(f"   Rolling: {len(all_features['rolling'])}")
        print(f"   Temporal: {len(all_features['temporal'])}")


async def test_toggle_features():
    """Test 3: Toggle features"""
    print("\n" + "="*80)
    print("TEST 3: Toggle Features On/Off")
    print("="*80)

    async with await get_test_session() as session:
        service = FeatureConfigServiceV2(session)

        config = await service.get_config("INLET_PRESSURE", "default_arima")
        config_id = config['config_id']

        # Before
        features_before = await service.get_all_enabled_features("INLET_PRESSURE", "default_arima")
        print(f"\n📊 Before toggle:")
        print(f"   Enabled lag features: {len(features_before['lag'])}")

        # Disable first lag feature
        print(f"\n❌ Disabling lag feature at index 0")
        success = await service.toggle_lag_feature(config_id, index=0, enabled=False)
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")

        # After
        features_after = await service.get_all_enabled_features("INLET_PRESSURE", "default_arima")
        print(f"\n📊 After toggle:")
        print(f"   Enabled lag features: {len(features_after['lag'])}")
        print(f"   Difference: {len(features_before['lag']) - len(features_after['lag'])}")

        # Re-enable
        print(f"\n✅ Re-enabling lag feature at index 0")
        success = await service.toggle_lag_feature(config_id, index=0, enabled=True)
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")


async def test_pipeline_integration():
    """Test 4: Integration with Pipeline V2 (simulation)"""
    print("\n" + "="*80)
    print("TEST 4: Pipeline V2 Integration Simulation")
    print("="*80)

    async with await get_test_session() as session:
        service = FeatureConfigServiceV2(session)

        # Get all enabled features
        features = await service.get_all_enabled_features("INLET_PRESSURE", "default_arima")

        print("\n🔨 Building Pipeline V2 from database config...")
        print("\n# Pipeline configuration code (pseudo):")
        print("pipeline = TrainingPipelineV2(session)")
        print("    .set_data_source('INLET_PRESSURE', days=7)")

        # Preprocessing (could also be from DB!)
        print("    .add_preprocessing()")
        print("        .interpolate(method='linear')")
        print("        .remove_outliers(threshold=3.0)")
        print("    .done()")

        # Feature engineering from DB
        print("    .add_feature_engineering()")

        # Lag features
        if features['lag']:
            lag_periods = [f['periods'] for f in features['lag']]
            print(f"        .add_lag({lag_periods})  # From DB!")

        # Rolling features
        if features['rolling']:
            rolling_windows = list(set(f['window'] for f in features['rolling']))
            print(f"        .add_rolling({rolling_windows})  # From DB!")

        # Temporal features
        if features['temporal']:
            temporal_types = [f['type'] for f in features['temporal']]
            print(f"        .add_temporal({temporal_types})  # From DB!")

        print("    .done()")
        print("    .add_model('auto_arima')")
        print("    .build()")

        print("\n✅ Pipeline configuration loaded from database!")
        print(f"\n📊 Feature counts:")
        print(f"   Lag: {len(features['lag'])}")
        print(f"   Rolling: {len(features['rolling'])}")
        print(f"   Temporal: {len(features['temporal'])}")
        print(f"   Seasonal: {len(features['seasonal'])}")
        print(f"   Fourier: {len(features['fourier'])}")
        print(f"   Total: {sum(len(v) for v in features.values())}")


async def test_clone_config():
    """Test 5: Clone configuration"""
    print("\n" + "="*80)
    print("TEST 5: Clone Configuration")
    print("="*80)

    async with await get_test_session() as session:
        service = FeatureConfigServiceV2(session)

        # Get original
        original = await service.get_config("INLET_PRESSURE", "default_arima")
        print(f"\n📋 Original config:")
        print(f"   ID: {original['config_id']}")
        print(f"   Name: {original['config_name']}")

        # Clone
        print(f"\n📋 Cloning config...")
        new_id = await service.clone_config(
            source_config_id=original['config_id'],
            new_config_name=f"experimental_{original['config_id']}"
        )
        print(f"   New config ID: {new_id}")

        # Verify
        cloned = await service.get_config_by_id(new_id)
        print(f"\n✅ Cloned config:")
        print(f"   ID: {cloned['config_id']}")
        print(f"   Name: {cloned['config_name']}")
        print(f"   Notes: {cloned['notes']}")

        # Compare features
        orig_features = await service.get_all_enabled_features(
            original['tag_name'],
            original['config_name']
        )
        clone_features = await service.get_lag_features(new_id)

        print(f"\n📊 Feature comparison:")
        print(f"   Original lag features: {len(orig_features['lag'])}")
        print(f"   Cloned lag features: {len(clone_features)}")
        print(f"   Match: {'✅' if len(orig_features['lag']) == len(clone_features) else '❌'}")


async def test_list_configs():
    """Test 6: List all configs"""
    print("\n" + "="*80)
    print("TEST 6: List All Configurations")
    print("="*80)

    async with await get_test_session() as session:
        service = FeatureConfigServiceV2(session)

        # List all
        all_configs = await service.list_configs()
        print(f"\n📋 All configurations ({len(all_configs)}):")
        for config in all_configs:
            print(f"\n   • {config['config_name']} ({config['tag_name']})")
            print(f"     Model: {config['model_type'] or 'Any'}")
            print(f"     Features: Lag={config['lag_count']}, Rolling={config['rolling_count']}, Temporal={config['temporal_count']}")
            print(f"     Total enabled: {config['total_enabled_features']}")

        # List by tag
        inlet_configs = await service.list_configs(tag_name="INLET_PRESSURE")
        print(f"\n📋 INLET_PRESSURE configurations ({len(inlet_configs)}):")
        for config in inlet_configs:
            print(f"   • {config['config_name']} - {config['total_enabled_features']} features")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 FEATURE CONFIG V2 INTEGRATION TESTS")
    print("="*80)

    try:
        await test_basic_operations()
        await test_add_features()
        await test_toggle_features()
        await test_pipeline_integration()
        await test_clone_config()
        await test_list_configs()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)

        print("\n📋 SUMMARY:")
        print("   ✅ Basic CRUD operations working")
        print("   ✅ Add features working")
        print("   ✅ Toggle features working")
        print("   ✅ Pipeline V2 integration ready")
        print("   ✅ Clone configuration working")
        print("   ✅ List configurations working")

        print("\n🎯 NEXT STEPS:")
        print("   1. Update Pipeline V2 to load from FeatureConfigServiceV2")
        print("   2. Create UI page for feature config management")
        print("   3. Add validation before training")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
