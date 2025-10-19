"""
ForecastScheduler - Generate online predictions every 5 minutes.

This scheduler:
1. Queries deployed models (is_deployed = TRUE)
2. Loads pickle model files
3. Generates predictions for multiple horizons (1h, 2h, 6h, 12h, 24h)
4. Inserts predictions into predictions table (NOT training_evaluation)
5. Predictions have target_time in the FUTURE (not past)

Architecture Reference: docs/forecast_result/ONLINE_FORECAST_REDESIGN_20251014.md
"""

import asyncio
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging
logger = logging.getLogger(__name__)
from sqlalchemy import text

from ..db_orm import get_async_session


class ForecastScheduler:
    """
    Generates online predictions for deployed models every 5 minutes.

    Key Principles:
    - ONLY generates predictions for deployed models (is_deployed = TRUE)
    - target_time is always in the FUTURE (> forecast_time)
    - Saves to predictions table (NOT training_evaluation)
    - Supports multiple horizons: 60, 120, 360, 720, 1440 minutes
    """

    def __init__(self):
        """Initialize scheduler with forecast horizons (PRD v3.0 Section 2.3)."""
        self.horizons = [10, 30, 60]  # 10min, 30min, 60min as per PRD v3.0
        self.is_running = False

    async def get_deployed_models(self) -> List[Dict]:
        """
        Get all deployed models from model_registry with pickle BYTEA.

        Returns:
            List of dicts with model_id, tag_name, model_type, model_pickle, pipeline_config
        """
        async with get_async_session() as session:
            query = text("""
                SELECT
                    model_id,
                    tag_name,
                    model_type,
                    model_pickle,
                    model_path,
                    version,
                    pipeline_config
                FROM model_registry
                WHERE is_deployed = TRUE
                  AND is_active = TRUE
                ORDER BY model_id
            """)

            result = await session.execute(query)
            models = result.mappings().all()

            return [dict(row) for row in models]

    async def load_model_from_bytea(self, model_pickle: bytes, model_path: Optional[str] = None):
        """
        Load trained model from PostgreSQL BYTEA or pickle file (fallback).

        Args:
            model_pickle: Pickle bytes from model_registry.model_pickle
            model_path: Fallback path to pickle file (legacy support)

        Returns:
            Trained model object or None if loading fails
        """
        try:
            # Try BYTEA first (preferred)
            if model_pickle:
                loop = asyncio.get_event_loop()
                model = await loop.run_in_executor(
                    None,
                    lambda: pickle.loads(model_pickle)
                )
                logger.info(f"✅ Loaded model from PostgreSQL BYTEA ({len(model_pickle)} bytes)")
                return model

            # Fallback to file path (legacy)
            elif model_path:
                model_file = Path(model_path)
                if not model_file.exists():
                    logger.error(f"Model file not found: {model_path}")
                    return None

                loop = asyncio.get_event_loop()
                model = await loop.run_in_executor(
                    None,
                    lambda: pickle.load(open(model_file, 'rb'))
                )
                logger.info(f"✅ Loaded model from file (legacy): {model_path}")
                return model

            else:
                logger.error("❌ No model_pickle or model_path provided")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            return None

    async def generate_predictions(
        self,
        model,
        model_type: str,
        last_value: float,
        horizons: List[int]
    ) -> Dict[str, List[float]]:
        """
        Generate predictions with confidence intervals using actual trained models.

        Args:
            model: Trained model object (statsforecast)
            model_type: Model type (PROPHET/AutoETS, AUTO_ARIMA, XGBOOST)
            last_value: Latest sensor value (for fallback only)
            horizons: List of forecast horizons in minutes

        Returns:
            Dict with 'predictions', 'ci_lower', 'ci_upper' lists
        """
        try:
            if model is None:
                logger.warning(f"⚠️ No model provided, using persistence model (last_value)")
                return {
                    'predictions': [last_value] * len(horizons),
                    'ci_lower': [last_value * 0.95] * len(horizons),  # Simple ±5%
                    'ci_upper': [last_value * 1.05] * len(horizons)
                }

            # statsforecast models (AutoARIMA, AutoETS)
            if model_type in ['AUTO_ARIMA', 'PROPHET']:
                # ✅ FIX: Model.predict() is async, await it directly
                forecast_df = await model.predict(len(horizons), level=[95])

                # Extract predictions and confidence intervals
                # Column names: 'AutoARIMA', 'AutoARIMA-lo-95', 'AutoARIMA-hi-95'
                # or 'AutoETS', 'AutoETS-lo-95', 'AutoETS-hi-95'
                model_col = 'AutoARIMA' if model_type == 'AUTO_ARIMA' else 'AutoETS'

                predictions = forecast_df[model_col].tolist()
                ci_lower = forecast_df[f'{model_col}-lo-95'].tolist() if f'{model_col}-lo-95' in forecast_df.columns else predictions
                ci_upper = forecast_df[f'{model_col}-hi-95'].tolist() if f'{model_col}-hi-95' in forecast_df.columns else predictions

                logger.info(f"✅ Generated {len(predictions)} predictions with CI for {model_type}")
                return {
                    'predictions': predictions,
                    'ci_lower': ci_lower,
                    'ci_upper': ci_upper
                }

            # XGBoost models (no native CI, use ±10% as approximation)
            elif model_type == 'XGBOOST':
                logger.warning(f"⚠️ XGBoost CI not implemented, using ±10% approximation")
                # TODO: Implement proper quantile regression or bootstrapping for XGBoost
                predictions = [last_value] * len(horizons)  # Placeholder
                return {
                    'predictions': predictions,
                    'ci_lower': [p * 0.9 for p in predictions],
                    'ci_upper': [p * 1.1 for p in predictions]
                }

            else:
                logger.error(f"❌ Unknown model type: {model_type}")
                return {
                    'predictions': [last_value] * len(horizons),
                    'ci_lower': [last_value] * len(horizons),
                    'ci_upper': [last_value] * len(horizons)
                }

        except Exception as e:
            logger.error(f"❌ Prediction generation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fallback to persistence model
            return {
                'predictions': [last_value] * len(horizons),
                'ci_lower': [last_value * 0.95] * len(horizons),
                'ci_upper': [last_value * 1.05] * len(horizons)
            }

    async def get_latest_sensor_value(self, tag_name: str, reference_time: Optional[datetime] = None) -> Optional[float]:
        """
        Get latest sensor value from influx_agg_10m (10-minute aggregated data).

        IMPORTANT: Uses influx_agg_10m to match training data source.
        reference_time is rounded to x:00, x:10, x:20, etc. for stable T0.

        Args:
            tag_name: Sensor tag name
            reference_time: Target time to search (default: now, rounded to 10-min boundary)

        Returns:
            Latest avg value from 10-min bucket, or None
        """
        async with get_async_session() as session:
            # If no reference_time, use now rounded to 10-minute boundary
            if reference_time is None:
                now = datetime.now()
                rounded_minute = (now.minute // 10) * 10
                reference_time = now.replace(minute=rounded_minute, second=0, microsecond=0)

            # Query influx_agg_10m for bucket matching reference_time
            # IMPORTANT: Use same data source as training (influx_agg_10m, not influx_hist)
            query = text("""
                SELECT avg as value, bucket
                FROM influx_agg_10m
                WHERE tag_name = :tag_name
                  AND bucket <= :ref_time
                ORDER BY bucket DESC
                LIMIT 1
            """)

            result = await session.execute(query, {
                "tag_name": tag_name,
                "ref_time": reference_time
            })
            row = result.mappings().first()

            if row:
                return float(row["value"])

            logger.warning(f"No 10-min aggregated data found for {tag_name} near {reference_time}")
            return None

    async def save_predictions(
        self,
        model_id: int,
        tag_name: str,
        prediction_data: Dict[str, List[float]],
        horizons: List[int],
        forecast_time: datetime
    ):
        """
        Save predictions with confidence intervals to predictions table.

        Args:
            model_id: Model ID from model_registry
            tag_name: Sensor tag name
            prediction_data: Dict with 'predictions', 'ci_lower', 'ci_upper'
            horizons: List of forecast horizons in minutes
            forecast_time: When predictions were generated (NOW)
        """
        async with get_async_session() as session:
            insert_sql = text("""
                INSERT INTO predictions (
                    model_id,
                    tag_name,
                    forecast_time,
                    target_time,
                    predicted_value,
                    ci_lower,
                    ci_upper,
                    actual_value,
                    horizon_minutes,
                    created_at
                )
                VALUES (
                    :model_id,
                    :tag_name,
                    :forecast_time,
                    :target_time,
                    :predicted_value,
                    :ci_lower,
                    :ci_upper,
                    NULL,  -- actual_value filled by ActualValueUpdater
                    :horizon_minutes,
                    :created_at
                )
                ON CONFLICT (target_time, tag_name, model_id, horizon_minutes) DO NOTHING
            """)

            predictions = prediction_data['predictions']
            ci_lower = prediction_data['ci_lower']
            ci_upper = prediction_data['ci_upper']

            for i, horizon in enumerate(horizons):
                target_time = forecast_time + timedelta(minutes=horizon)

                await session.execute(insert_sql, {
                    "model_id": model_id,
                    "tag_name": tag_name,
                    "forecast_time": forecast_time,
                    "target_time": target_time,
                    "predicted_value": float(predictions[i]),
                    "ci_lower": float(ci_lower[i]),
                    "ci_upper": float(ci_upper[i]),
                    "horizon_minutes": horizon,
                    "created_at": forecast_time,
                })

            await session.commit()
            logger.info(f"✅ Saved {len(predictions)} predictions with CI for model {model_id}")

    async def generate_forecast_player_cache(
        self,
        model_id: int,
        tag_name: str,
        forecast_time: datetime,
        horizons: List[int]
    ):
        """
        Generate and save Forecast Player cache snapshot for ultra-fast UI queries.

        This method:
        1. Calls ForecastService.get_rolling_window_data() to generate Rolling Window
        2. Calls ForecastService.get_predictions() to get formatted predictions
        3. Calculates metrics (MAPE, RMSE, MAE)
        4. Saves everything to forecast_player_cache table

        Args:
            model_id: Model ID
            tag_name: Sensor tag name
            forecast_time: When predictions were generated
            horizons: List of forecast horizons
        """
        try:
            from ..services.forecast_service import ForecastService

            async with get_async_session() as session:
                service = ForecastService(session)

                # Generate Rolling Window data (Past 30 + Present 1 + Future N)
                rolling_window = await service.get_rolling_window_data(
                    model_id=model_id,
                    lookback_intervals=30
                )

                # Get formatted predictions for table display (7 rows)
                predictions_data = await service.get_predictions(
                    model_id=model_id,
                    hours_ahead=24
                )
                predictions_data = predictions_data[:7]  # Limit to 7 rows

                # Get latest sensor value (extract numeric value from dict)
                latest_value_dict = await service.get_latest_sensor_value(tag_name)
                latest_value = latest_value_dict["value"] if latest_value_dict else None

                # Calculate metrics (MAPE, RMSE, MAE) from recent predictions with actuals
                metrics_query = text("""
                    SELECT
                        ROUND(AVG(ABS((actual_value - predicted_value) / NULLIF(actual_value, 0)) * 100)::numeric, 2) as mape,
                        ROUND(SQRT(AVG(POWER(predicted_value - actual_value, 2)))::numeric, 2) as rmse,
                        ROUND(AVG(ABS(predicted_value - actual_value))::numeric, 2) as mae
                    FROM predictions
                    WHERE model_id = :model_id
                      AND actual_value IS NOT NULL
                      AND created_at >= NOW() - INTERVAL '24 hours'
                """)
                metrics_result = await session.execute(metrics_query, {"model_id": model_id})
                metrics_row = metrics_result.mappings().first()

                mape = float(metrics_row["mape"]) if metrics_row and metrics_row["mape"] else None
                rmse = float(metrics_row["rmse"]) if metrics_row and metrics_row["rmse"] else None
                mae = float(metrics_row["mae"]) if metrics_row and metrics_row["mae"] else None
                accuracy = round(100 - mape, 2) if mape else None

                # Calculate next forecast time (current + 10 minutes)
                next_forecast_at = forecast_time + timedelta(minutes=10)

                # Find latest actual data timestamp for reference_time
                ref_time_query = text("""
                    SELECT MAX(ts) AT TIME ZONE 'Asia/Seoul' as ref_time
                    FROM influx_hist
                    WHERE tag_name = :tag_name
                      AND quality IN (0, 192)
                """)
                ref_time_result = await session.execute(ref_time_query, {"tag_name": tag_name})
                ref_time_row = ref_time_result.mappings().first()
                reference_time = ref_time_row["ref_time"] if ref_time_row else forecast_time

                # Insert into forecast_player_cache
                insert_cache_sql = text("""
                    INSERT INTO forecast_player_cache (
                        model_id,
                        tag_name,
                        forecast_time,
                        reference_time,
                        rolling_window,
                        predictions_data,
                        mape,
                        rmse,
                        mae,
                        accuracy,
                        next_forecast_at,
                        latest_value
                    )
                    VALUES (
                        :model_id,
                        :tag_name,
                        :forecast_time,
                        :reference_time,
                        :rolling_window,
                        :predictions_data,
                        :mape,
                        :rmse,
                        :mae,
                        :accuracy,
                        :next_forecast_at,
                        :latest_value
                    )
                    ON CONFLICT (model_id, forecast_time) DO UPDATE SET
                        rolling_window = EXCLUDED.rolling_window,
                        predictions_data = EXCLUDED.predictions_data,
                        mape = EXCLUDED.mape,
                        rmse = EXCLUDED.rmse,
                        mae = EXCLUDED.mae,
                        accuracy = EXCLUDED.accuracy,
                        next_forecast_at = EXCLUDED.next_forecast_at,
                        latest_value = EXCLUDED.latest_value
                """)

                await session.execute(insert_cache_sql, {
                    "model_id": model_id,
                    "tag_name": tag_name,
                    "forecast_time": forecast_time,
                    "reference_time": reference_time,
                    "rolling_window": json.dumps(rolling_window),
                    "predictions_data": json.dumps(predictions_data),
                    "mape": mape,
                    "rmse": rmse,
                    "mae": mae,
                    "accuracy": accuracy,
                    "next_forecast_at": next_forecast_at,
                    "latest_value": latest_value
                })

                await session.commit()
                logger.info(f"✅ Saved Forecast Player cache for model {model_id} ({len(rolling_window)} points, MAPE={mape}%)")

        except Exception as e:
            logger.error(f"❌ Failed to generate Forecast Player cache for model {model_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def run_once(self):
        """
        Run one iteration of forecast generation.

        This method:
        1. Gets all deployed models
        2. For each model:
           - Loads model from pickle
           - Gets latest sensor value
           - Generates predictions
           - Saves to predictions table

        IMPORTANT: forecast_time is rounded to nearest 10-minute boundary (x:00:00, x:10:00, etc.)
        to ensure stable T0 reference time in Forecast Player UI.
        """
        try:
            # Round forecast_time to nearest 10-minute boundary (x:00:00, x:10:00, x:20:00, etc.)
            now = datetime.now()
            rounded_minute = (now.minute // 10) * 10
            forecast_time = now.replace(minute=rounded_minute, second=0, microsecond=0)
            logger.info(f"🔄 ForecastScheduler starting at {forecast_time}")

            # Get deployed models
            deployed_models = await self.get_deployed_models()

            if not deployed_models:
                logger.info("⚠️ No deployed models found")
                return

            logger.info(f"📊 Found {len(deployed_models)} deployed model(s)")

            # Process each model
            for model_info in deployed_models:
                model_id = model_info["model_id"]
                tag_name = model_info["tag_name"]
                model_type = model_info["model_type"]
                model_path = model_info["model_path"]
                pipeline_config_json = model_info.get("pipeline_config")

                logger.info(f"🔧 Processing model {model_id} ({model_type}) for {tag_name}")

                # Extract horizons from pipeline_config (NEW - offline/online sync)
                horizons = self.horizons  # Default fallback
                forecast_interval = 10
                forecast_horizon_hours = 1

                if pipeline_config_json:
                    try:
                        pipeline_config = json.loads(pipeline_config_json)
                        forecast_config = pipeline_config.get("forecast_config", {})

                        if forecast_config.get("horizons"):
                            horizons = forecast_config["horizons"]
                            forecast_interval = forecast_config.get("forecast_interval_minutes", 10)
                            forecast_horizon_hours = forecast_config.get("forecast_horizon_hours", 1)
                            logger.info(f"📊 Using horizons from pipeline_config: {forecast_interval}분 단위 {forecast_horizon_hours}시간 예측 ({len(horizons)}개 스텝)")
                            logger.info(f"   First 5 steps: {horizons[:5]}")
                        else:
                            logger.warning(f"⚠️ No horizons in pipeline_config for model {model_id}, using default: {horizons}")
                    except Exception as e:
                        logger.error(f"❌ Failed to parse pipeline_config for model {model_id}: {e}")
                        logger.warning(f"   Using default horizons: {horizons}")

                # Get latest sensor value (aligned to forecast_time for stable T0)
                last_value = await self.get_latest_sensor_value(tag_name, reference_time=forecast_time)

                if last_value is None:
                    logger.error(f"❌ No sensor data for {tag_name}, skipping")
                    continue

                logger.info(f"📈 Latest value for {tag_name}: {last_value:.2f}")

                # Load actual model from PostgreSQL BYTEA
                model_pickle = model_info.get("model_pickle")
                model = await self.load_model_from_bytea(model_pickle, model_path)

                if model is None:
                    logger.error(f"❌ Failed to load model {model_id}, skipping")
                    continue

                # Generate predictions with confidence intervals using actual model
                prediction_data = await self.generate_predictions(
                    model=model,
                    model_type=model_type,
                    last_value=last_value,
                    horizons=horizons  # Use model-specific horizons
                )

                # Save predictions with CI
                await self.save_predictions(
                    model_id=model_id,
                    tag_name=tag_name,
                    prediction_data=prediction_data,
                    horizons=horizons,  # Use model-specific horizons
                    forecast_time=forecast_time
                )

                # Generate and save Forecast Player cache (NEW - ultra-fast UI queries)
                await self.generate_forecast_player_cache(
                    model_id=model_id,
                    tag_name=tag_name,
                    forecast_time=forecast_time,
                    horizons=horizons
                )

            logger.info(f"✅ ForecastScheduler completed at {datetime.now()}")

        except Exception as e:
            logger.error(f"❌ ForecastScheduler error: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def start(self, interval_seconds: int = 300):
        """
        Start the scheduler to run every interval_seconds (default 5 minutes = 300s, 10 minutes = 600s).

        IMPORTANT: Aligns execution to exact clock times (00 seconds of 00, 10, 20, 30, 40, 50 minutes).
        This ensures T0 (reference time) is stable and consistent across all forecast cycles.

        Args:
            interval_seconds: Interval in seconds (600 = 10 minutes)
        """
        self.is_running = True
        logger.info(f"🚀 ForecastScheduler started (interval: {interval_seconds}s, aligned to x:00:00)")

        while self.is_running:
            # Execute forecast generation
            await self.run_once()

            # Calculate sleep time to align next execution to exact clock time (x:00:00, x:10:00, etc.)
            now = datetime.now()
            interval_minutes = interval_seconds // 60

            # Calculate next target minute (round up to next interval boundary)
            current_total_minutes = now.hour * 60 + now.minute
            next_target_minutes = ((current_total_minutes // interval_minutes) + 1) * interval_minutes
            next_hour = next_target_minutes // 60
            next_minute = next_target_minutes % 60

            # Calculate seconds until next target (always align to 00 seconds)
            seconds_until_next_minute = 60 - now.second
            minutes_until_target = (next_minute - now.minute) % interval_minutes
            if minutes_until_target == 0 and now.second > 0:
                # If we're past the target second, wait until next interval
                minutes_until_target = interval_minutes

            total_sleep_seconds = minutes_until_target * 60 + seconds_until_next_minute - now.microsecond / 1_000_000

            # Ensure sleep is positive
            if total_sleep_seconds <= 0:
                total_sleep_seconds = interval_seconds

            logger.info(f"⏰ Next run at {next_hour:02d}:{next_minute:02d}:00 (sleeping {int(total_sleep_seconds)}s)")
            await asyncio.sleep(total_sleep_seconds)

    def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        logger.info("🛑 ForecastScheduler stopped")


# Singleton instance
_scheduler_instance: Optional[ForecastScheduler] = None


def get_forecast_scheduler() -> ForecastScheduler:
    """Get or create ForecastScheduler singleton instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ForecastScheduler()
    return _scheduler_instance
