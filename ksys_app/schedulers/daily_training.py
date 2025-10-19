"""
Daily Training Scheduler - Automate model retraining workflow.

This module provides scheduled model retraining that runs daily at 2 AM.
It handles:
1. Data collection from the last 30 days
2. Model training for all sensors
3. Model evaluation and comparison
4. Automatic deployment of better models
5. Drift detection and alerting
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db_orm import get_async_session
from ..models.forecasting_orm import ModelRegistry
from ..ml.training_pipeline import ModelTrainingPipeline
from ..ml.drift_detector import DriftDetector, DriftSeverity

logger = logging.getLogger(__name__)


class DailyTrainingScheduler:
    """Scheduler for daily model retraining."""

    def __init__(
        self,
        training_days: int = 30,
        min_data_points: int = 1000,
        enable_drift_check: bool = True,
    ):
        """
        Initialize scheduler.

        Args:
            training_days: Number of days of data to use for training
            min_data_points: Minimum data points required for training
            enable_drift_check: Whether to run drift detection
        """
        self.training_days = training_days
        self.min_data_points = min_data_points
        self.enable_drift_check = enable_drift_check

    async def run_daily_training(self):
        """
        Execute daily training workflow.

        This is the main entry point for the scheduled job.
        """
        logger.info("=" * 80)
        logger.info("STARTING DAILY MODEL TRAINING")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 80)

        start_time = datetime.now()

        try:
            async with get_async_session() as session:
                # Get list of active sensors
                sensors = await self._get_active_sensors(session)
                logger.info(f"Found {len(sensors)} active sensors")

                # Train models for each sensor
                results = []
                for sensor in sensors:
                    try:
                        result = await self._train_sensor_models(session, sensor)
                        results.append(result)
                    except Exception as e:
                        logger.error(
                            f"Failed to train models for {sensor}: {e}",
                            exc_info=True
                        )
                        results.append({
                            'sensor': sensor,
                            'status': 'error',
                            'error': str(e),
                        })

                # Check for drift if enabled
                if self.enable_drift_check:
                    await self._check_drift_for_all(session, sensors)

                # Generate summary report
                summary = self._generate_summary(results)
                logger.info("=" * 80)
                logger.info("DAILY TRAINING SUMMARY")
                logger.info(f"Total sensors: {summary['total']}")
                logger.info(f"Successful: {summary['successful']}")
                logger.info(f"Failed: {summary['failed']}")
                logger.info(f"Skipped: {summary['skipped']}")
                logger.info(
                    f"Duration: {(datetime.now() - start_time).total_seconds():.2f}s"
                )
                logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Daily training failed: {e}", exc_info=True)

    async def _get_active_sensors(self, session: AsyncSession) -> List[str]:
        """
        Get list of sensors that have sufficient recent data.

        Args:
            session: Database session

        Returns:
            List of sensor tag names
        """
        from sqlalchemy import text

        # Get sensors with recent data
        query = text("""
            SELECT DISTINCT tag_name
            FROM influx_hist
            WHERE ts >= NOW() - INTERVAL ':days days'
                AND quality = 192
            GROUP BY tag_name
            HAVING COUNT(*) >= :min_points
            ORDER BY tag_name
        """)

        result = await session.execute(
            query,
            {
                'days': self.training_days,
                'min_points': self.min_data_points,
            }
        )

        sensors = [row[0] for row in result.fetchall()]
        return sensors

    async def _train_sensor_models(
        self,
        session: AsyncSession,
        tag_name: str,
    ) -> Dict[str, Any]:
        """
        Train all model types for a sensor.

        Args:
            session: Database session
            tag_name: Sensor tag name

        Returns:
            Dictionary with training results
        """
        logger.info(f"Training models for {tag_name}")

        pipeline = ModelTrainingPipeline(session)

        # Prepare training period
        end_time = datetime.now()
        start_time = end_time - timedelta(days=self.training_days)

        try:
            # Fetch training data
            train_data = await pipeline.get_training_data(
                tag_name=tag_name,
                start_time=start_time,
                end_time=end_time,
                include_features=True,
            )

            if train_data.empty:
                logger.warning(f"No training data for {tag_name}")
                return {
                    'sensor': tag_name,
                    'status': 'skipped',
                    'reason': 'no_data',
                }

            # Train ARIMA
            arima_result = await self._train_single_model(
                pipeline=pipeline,
                tag_name=tag_name,
                train_data=train_data,
                model_type='ARIMA',
            )

            # Train Prophet (AutoETS)
            prophet_result = await self._train_single_model(
                pipeline=pipeline,
                tag_name=tag_name,
                train_data=train_data,
                model_type='Prophet',  # Now uses AutoETS from statsforecast
            )

            # XGBoost training is disabled (lightweight forecasting focus)
            # Only using statsforecast models: AutoARIMA and AutoETS

            # Compile results
            return {
                'sensor': tag_name,
                'status': 'success',
                'models': {
                    'ARIMA': arima_result,  # statsforecast AutoARIMA
                    'ETS': prophet_result,  # statsforecast AutoETS (was Prophet)
                },
                'training_period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'samples': len(train_data),
                },
            }

        except Exception as e:
            logger.error(f"Training failed for {tag_name}: {e}", exc_info=True)
            return {
                'sensor': tag_name,
                'status': 'error',
                'error': str(e),
            }

    async def _train_single_model(
        self,
        pipeline: ModelTrainingPipeline,
        tag_name: str,
        train_data,
        model_type: str,
    ) -> Dict[str, Any]:
        """Train a single model type."""
        try:
            if model_type == 'ARIMA':
                model, metrics = await pipeline.train_arima(
                    tag_name=tag_name,
                    train_data=train_data,
                    seasonal=True,
                    m=24,
                )

            elif model_type == 'Prophet':
                model, metrics = await pipeline.train_prophet(
                    tag_name=tag_name,
                    train_data=train_data,
                    daily_seasonality=True,
                    weekly_seasonality=True,
                )

            elif model_type == 'XGBoost':
                model, metrics = await pipeline.train_xgboost(
                    tag_name=tag_name,
                    train_data=train_data,
                    target_col='value',
                )

            else:
                raise ValueError(f"Unknown model type: {model_type}")

            # Check if new model is better than existing
            should_deploy = await self._should_deploy_model(
                pipeline=pipeline,
                tag_name=tag_name,
                model_type=model_type,
                new_metrics=metrics,
            )

            # Save model if it's an improvement
            if should_deploy:
                model_id = await pipeline.save_model(
                    tag_name=tag_name,
                    model=model,
                    model_type=model_type,
                    metrics=metrics,
                    version=datetime.now().strftime("%Y%m%d_%H%M%S"),
                )

                logger.info(
                    f"✅ {model_type} model deployed for {tag_name} "
                    f"(MAE: {metrics['mae']:.4f})"
                )

                return {
                    'model_id': model_id,
                    'metrics': metrics,
                    'deployed': True,
                }
            else:
                logger.info(
                    f"⏭️ {model_type} model not deployed for {tag_name} "
                    f"(existing model is better)"
                )

                return {
                    'metrics': metrics,
                    'deployed': False,
                    'reason': 'existing_better',
                }

        except Exception as e:
            logger.error(f"{model_type} training failed: {e}", exc_info=True)
            return {
                'deployed': False,
                'error': str(e),
            }

    async def _should_deploy_model(
        self,
        pipeline: ModelTrainingPipeline,
        tag_name: str,
        model_type: str,
        new_metrics: Dict[str, float],
    ) -> bool:
        """
        Determine if new model should replace existing model.

        Args:
            pipeline: Training pipeline
            tag_name: Sensor tag name
            model_type: Model type
            new_metrics: Metrics for new model

        Returns:
            True if new model should be deployed
        """
        # Query existing model
        query = select(ModelRegistry).where(
            ModelRegistry.tag_name == tag_name,
            ModelRegistry.model_type == model_type,
        ).order_by(ModelRegistry.created_at.desc()).limit(1)

        result = await pipeline.session.execute(query)
        existing = result.scalars().first()

        if not existing:
            # No existing model, deploy new one
            return True

        # Compare MAE (lower is better)
        new_mae = new_metrics.get('mae', float('inf'))
        existing_mae = existing.mae

        # Deploy if new model is at least 5% better
        improvement_threshold = 0.95  # 5% better
        return new_mae < (existing_mae * improvement_threshold)

    async def _check_drift_for_all(
        self,
        session: AsyncSession,
        sensors: List[str],
    ):
        """
        Check for drift in all sensor models.

        Args:
            session: Database session
            sensors: List of sensor tag names
        """
        logger.info("Checking for drift...")

        detector = DriftDetector(session)

        # Define periods
        current_end = datetime.now()
        current_start = current_end - timedelta(hours=24)
        reference_end = current_start
        reference_start = reference_end - timedelta(days=30)

        drift_alerts = []

        for tag_name in sensors:
            try:
                # Get latest model
                query = select(ModelRegistry).where(
                    ModelRegistry.tag_name == tag_name
                ).order_by(ModelRegistry.created_at.desc()).limit(1)

                result = await session.execute(query)
                model_record = result.scalars().first()

                if not model_record:
                    continue

                # Detect drift
                drift_result = await detector.detect_drift(
                    tag_name=tag_name,
                    model_id=model_record.model_id,
                    reference_start=reference_start,
                    reference_end=reference_end,
                    current_start=current_start,
                    current_end=current_end,
                )

                # Check severity
                if drift_result.get('overall_severity') in [
                    DriftSeverity.HIGH,
                    DriftSeverity.CRITICAL,
                ]:
                    drift_alerts.append(drift_result)
                    logger.warning(
                        f"⚠️ Drift detected for {tag_name}: "
                        f"{drift_result['overall_severity']}"
                    )

            except Exception as e:
                logger.error(f"Drift check failed for {tag_name}: {e}")

        if drift_alerts:
            logger.warning(f"🚨 {len(drift_alerts)} sensors with significant drift")

    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Generate summary statistics."""
        summary = {
            'total': len(results),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
        }

        for result in results:
            status = result.get('status', 'unknown')
            if status == 'success':
                summary['successful'] += 1
            elif status == 'error':
                summary['failed'] += 1
            elif status == 'skipped':
                summary['skipped'] += 1

        return summary


# Standalone script entry point for cron job
async def main():
    """Main entry point for scheduled job."""
    scheduler = DailyTrainingScheduler(
        training_days=30,
        min_data_points=1000,
        enable_drift_check=True,
    )

    await scheduler.run_daily_training()


if __name__ == "__main__":
    # Run daily training
    asyncio.run(main())
