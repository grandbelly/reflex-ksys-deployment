"""
Tests for Forecasting Database Schema

Verifies that the forecasting schema is correctly created with:
- All required tables
- TimescaleDB hypertables
- Proper indexes
- Views
- Retention policies

Task: 31 - Database Schema Design
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ksys_app.db_orm import get_async_session
from ksys_app.models.forecasting_orm import (
    ModelRegistry,
    Prediction,
    PredictionPerformance,
    FeatureStore,
    DriftMonitoring,
)


@pytest.fixture
async def session():
    """Create async database session for tests"""
    async with get_async_session() as session:
        yield session


class TestForecastingSchema:
    """Test forecasting database schema creation"""

    @pytest.mark.asyncio
    async def test_tables_exist(self, session: AsyncSession):
        """Verify all forecasting tables exist"""
        query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN (
                'model_registry',
                'predictions',
                'prediction_performance',
                'feature_store',
                'drift_monitoring'
            )
            ORDER BY table_name
        """)

        result = await session.execute(query)
        tables = [row[0] for row in result.fetchall()]

        expected_tables = [
            "drift_monitoring",
            "feature_store",
            "model_registry",
            "prediction_performance",
            "predictions",
        ]

        assert tables == expected_tables, f"Expected {expected_tables}, got {tables}"

    @pytest.mark.asyncio
    async def test_hypertables_exist(self, session: AsyncSession):
        """Verify TimescaleDB hypertables are created"""
        query = text("""
            SELECT hypertable_name
            FROM timescaledb_information.hypertables
            WHERE hypertable_schema = 'public'
            AND hypertable_name IN (
                'predictions',
                'prediction_performance',
                'feature_store',
                'drift_monitoring'
            )
            ORDER BY hypertable_name
        """)

        result = await session.execute(query)
        hypertables = [row[0] for row in result.fetchall()]

        expected = ["drift_monitoring", "feature_store", "prediction_performance", "predictions"]

        assert hypertables == expected, f"Expected {expected} hypertables, got {hypertables}"

    @pytest.mark.asyncio
    async def test_model_registry_structure(self, session: AsyncSession):
        """Verify model_registry table structure"""
        query = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'model_registry'
            ORDER BY ordinal_position
        """)

        result = await session.execute(query)
        columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.fetchall()}

        # Check key columns exist
        assert "model_id" in columns
        assert "model_name" in columns
        assert "model_type" in columns
        assert "version" in columns
        assert "tag_name" in columns
        assert "hyperparameters" in columns
        assert "model_path" in columns
        assert "validation_mape" in columns
        assert "is_active" in columns

        # Check primary key is NOT NULL
        assert columns["model_id"]["nullable"] == "NO"

    @pytest.mark.asyncio
    async def test_predictions_structure(self, session: AsyncSession):
        """Verify predictions table structure"""
        query = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'predictions'
            ORDER BY ordinal_position
        """)

        result = await session.execute(query)
        columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.fetchall()}

        # Check key columns exist
        assert "target_time" in columns
        assert "tag_name" in columns
        assert "model_id" in columns
        assert "horizon_minutes" in columns
        assert "forecast_time" in columns
        assert "predicted_value" in columns
        assert "ci_lower" in columns
        assert "ci_upper" in columns
        assert "actual_value" in columns
        assert "absolute_percentage_error" in columns

        # Check NOT NULL constraints
        assert columns["target_time"]["nullable"] == "NO"
        assert columns["predicted_value"]["nullable"] == "NO"

    @pytest.mark.asyncio
    async def test_views_exist(self, session: AsyncSession):
        """Verify forecasting views are created"""
        query = text("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
            AND table_name IN (
                'v_active_models',
                'v_recent_prediction_accuracy',
                'v_models_need_retraining'
            )
            ORDER BY table_name
        """)

        result = await session.execute(query)
        views = [row[0] for row in result.fetchall()]

        expected = ["v_active_models", "v_models_need_retraining", "v_recent_prediction_accuracy"]

        assert views == expected, f"Expected {expected} views, got {views}"

    @pytest.mark.asyncio
    async def test_retention_policies_exist(self, session: AsyncSession):
        """Verify retention policies are configured"""
        query = text("""
            SELECT format('%I.%I', ht.schema_name, ht.table_name) as hypertable,
                   config->>'drop_after' as retention_period
            FROM timescaledb_information.jobs j
            JOIN timescaledb_information.hypertables ht
                ON j.hypertable_name = ht.table_name
            WHERE j.proc_name = 'policy_retention'
            AND ht.schema_name = 'public'
            AND ht.table_name IN (
                'predictions',
                'prediction_performance',
                'feature_store',
                'drift_monitoring'
            )
            ORDER BY ht.table_name
        """)

        result = await session.execute(query)
        policies = {row[0]: row[1] for row in result.fetchall()}

        # Check policies exist for all hypertables
        assert "public.predictions" in policies
        assert "public.prediction_performance" in policies
        assert "public.feature_store" in policies
        assert "public.drift_monitoring" in policies

        # Check retention periods
        assert policies["public.predictions"] == "90 days"
        assert policies["public.prediction_performance"] == "365 days"
        assert policies["public.feature_store"] == "90 days"
        assert policies["public.drift_monitoring"] == "180 days"

    @pytest.mark.asyncio
    async def test_indexes_exist(self, session: AsyncSession):
        """Verify key indexes are created"""
        query = text("""
            SELECT
                tablename,
                indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename IN (
                'model_registry',
                'predictions',
                'prediction_performance',
                'feature_store',
                'drift_monitoring'
            )
            ORDER BY tablename, indexname
        """)

        result = await session.execute(query)
        indexes = result.fetchall()

        # Convert to dict for easier checking
        table_indexes = {}
        for table, index in indexes:
            if table not in table_indexes:
                table_indexes[table] = []
            table_indexes[table].append(index)

        # Check model_registry indexes
        assert "idx_model_registry_tag_name" in table_indexes["model_registry"]
        assert "idx_model_registry_model_type" in table_indexes["model_registry"]

        # Check predictions indexes
        assert "idx_predictions_tag_name" in table_indexes["predictions"]
        assert "idx_predictions_model_id" in table_indexes["predictions"]

        # Check prediction_performance indexes
        assert "idx_perf_model_id" in table_indexes["prediction_performance"]
        assert "idx_perf_tag_name" in table_indexes["prediction_performance"]


class TestForecastingCRUD:
    """Test basic CRUD operations on forecasting tables"""

    @pytest.mark.asyncio
    async def test_model_registry_insert(self, session: AsyncSession):
        """Test inserting a model into model_registry"""
        # Create test model
        test_model = ModelRegistry(
            model_name="TEST_ARIMA_v1",
            model_type="arima",
            version="1.0.0-test",
            tag_name="INLET_PRESSURE",
            hyperparameters={"p": 2, "d": 1, "q": 2},
            model_path="/tmp/test_model.pkl",
            training_samples=1000,
            validation_mape=15.5,
            validation_rmse=2.3,
            is_active=True,
        )

        session.add(test_model)
        await session.commit()
        await session.refresh(test_model)

        assert test_model.model_id is not None
        assert test_model.model_name == "TEST_ARIMA_v1"
        assert test_model.hyperparameters["p"] == 2

        # Cleanup
        await session.delete(test_model)
        await session.commit()

    @pytest.mark.asyncio
    async def test_predictions_insert(self, session: AsyncSession):
        """Test inserting predictions"""
        # First create a model
        test_model = ModelRegistry(
            model_name="TEST_MODEL_FOR_PRED",
            model_type="prophet",
            version="1.0.0-test",
            tag_name="INLET_PRESSURE",
            model_path="/tmp/test.pkl",
            is_active=True,
        )
        session.add(test_model)
        await session.commit()
        await session.refresh(test_model)

        # Create prediction
        now = datetime.utcnow()
        prediction = Prediction(
            target_time=now + timedelta(hours=1),
            forecast_time=now,
            tag_name="INLET_PRESSURE",
            model_id=test_model.model_id,
            horizon_minutes=60,
            predicted_value=12.5,
            ci_lower=11.0,
            ci_upper=14.0,
        )

        session.add(prediction)
        await session.commit()

        # Verify
        query = text("""
            SELECT predicted_value, ci_lower, ci_upper
            FROM predictions
            WHERE model_id = :model_id
        """)
        result = await session.execute(query, {"model_id": test_model.model_id})
        row = result.fetchone()

        assert row is not None
        assert float(row[0]) == 12.5
        assert float(row[1]) == 11.0
        assert float(row[2]) == 14.0

        # Cleanup
        await session.delete(prediction)
        await session.delete(test_model)
        await session.commit()

    @pytest.mark.asyncio
    async def test_feature_store_insert(self, session: AsyncSession):
        """Test inserting features into feature_store"""
        now = datetime.utcnow()
        feature = FeatureStore(
            feature_time=now,
            tag_name="INLET_PRESSURE",
            lag_1h=12.5,
            lag_24h=13.0,
            rolling_mean_6h=12.8,
            rolling_std_6h=0.5,
            hour_of_day=14,
            day_of_week=3,
            is_weekend=False,
            is_business_hour=True,
        )

        session.add(feature)
        await session.commit()

        # Verify
        query = text("""
            SELECT lag_1h, rolling_mean_6h, hour_of_day
            FROM feature_store
            WHERE tag_name = :tag_name
            AND feature_time = :feature_time
        """)
        result = await session.execute(
            query, {"tag_name": "INLET_PRESSURE", "feature_time": now}
        )
        row = result.fetchone()

        assert row is not None
        assert float(row[0]) == 12.5
        assert float(row[1]) == 12.8
        assert row[2] == 14

        # Cleanup
        await session.delete(feature)
        await session.commit()


class TestForecastingTriggers:
    """Test database triggers and functions"""

    @pytest.mark.asyncio
    async def test_prediction_error_trigger(self, session: AsyncSession):
        """Test automatic prediction error calculation trigger"""
        # Create test model
        test_model = ModelRegistry(
            model_name="TEST_TRIGGER_MODEL",
            model_type="arima",
            version="1.0.0-test",
            tag_name="INLET_PRESSURE",
            model_path="/tmp/test.pkl",
            is_active=True,
        )
        session.add(test_model)
        await session.commit()
        await session.refresh(test_model)

        # Create prediction without actual value
        now = datetime.utcnow()
        prediction = Prediction(
            target_time=now,
            forecast_time=now - timedelta(hours=1),
            tag_name="INLET_PRESSURE",
            model_id=test_model.model_id,
            horizon_minutes=60,
            predicted_value=12.5,
            ci_lower=11.0,
            ci_upper=14.0,
        )
        session.add(prediction)
        await session.commit()
        await session.refresh(prediction)

        # Update with actual value - trigger should calculate error
        prediction.actual_value = 13.0
        await session.commit()
        await session.refresh(prediction)

        # Verify error calculations
        assert prediction.prediction_error is not None
        assert abs(float(prediction.prediction_error) - 0.5) < 0.001  # 13.0 - 12.5 = 0.5
        assert prediction.absolute_percentage_error is not None
        # |0.5| / |13.0| * 100 = 3.846%
        assert abs(float(prediction.absolute_percentage_error) - 3.846) < 0.01

        # Cleanup
        await session.delete(prediction)
        await session.delete(test_model)
        await session.commit()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
