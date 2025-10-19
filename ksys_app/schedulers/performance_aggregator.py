"""
PerformanceAggregator - Aggregate online prediction accuracy metrics.

This scheduler:
1. Aggregates completed predictions (actual_value IS NOT NULL)
2. Calculates MAE, MAPE, RMSE per model
3. Inserts into prediction_performance table
4. Groups by model_id, horizon_minutes, and time period

Runs every 1 hour.

Architecture Reference: docs/forecast_result/ONLINE_FORECAST_REDESIGN_20251014.md
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging
logger = logging.getLogger(__name__)
from sqlalchemy import text

from ..db_orm import get_async_session


class PerformanceAggregator:
    """
    Aggregates online prediction accuracy metrics hourly.

    Key Principles:
    - Aggregates completed predictions (actual_value NOT NULL)
    - Calculates MAE, MAPE, RMSE
    - Stores in prediction_performance table
    - Groups by model_id and horizon_minutes
    """

    def __init__(self):
        """Initialize aggregator."""
        self.is_running = False

    async def aggregate_performance_metrics(self) -> int:
        """
        Aggregate performance metrics for the last hour.

        Returns:
            Number of aggregation records created
        """
        async with get_async_session() as session:
            # Set statement timeout
            await session.execute(text("SET LOCAL statement_timeout = '60s'"))

            # Calculate aggregated metrics
            aggregation_sql = text("""
                INSERT INTO prediction_performance (
                    evaluation_time,
                    model_id,
                    tag_name,
                    horizon_minutes,
                    eval_start_time,
                    eval_end_time,
                    num_predictions,
                    mae,
                    mape,
                    rmse
                )
                SELECT
                    DATE_TRUNC('hour', NOW()) AS evaluation_time,
                    p.model_id,
                    mr.tag_name,
                    p.horizon_minutes,
                    DATE_TRUNC('hour', MIN(p.forecast_time)) AS eval_start_time,
                    DATE_TRUNC('hour', MAX(p.forecast_time)) AS eval_end_time,
                    COUNT(*) AS num_predictions,
                    (AVG(ABS(p.prediction_error)) FILTER (WHERE p.prediction_error IS NOT NULL))::numeric AS mae,
                    (AVG(p.absolute_percentage_error) FILTER (WHERE p.absolute_percentage_error IS NOT NULL))::numeric AS mape,
                    SQRT((AVG(p.prediction_error ^ 2) FILTER (WHERE p.prediction_error IS NOT NULL)))::numeric AS rmse
                FROM predictions p
                JOIN model_registry mr ON p.model_id = mr.model_id
                WHERE p.actual_value IS NOT NULL
                  AND p.forecast_time >= (NOW() - INTERVAL '1 hour')
                  AND p.forecast_time < NOW()
                GROUP BY p.model_id, mr.tag_name, p.horizon_minutes
                HAVING COUNT(*) >= 3  -- At least 3 predictions for meaningful metrics
                ON CONFLICT (evaluation_time, model_id, horizon_minutes) DO UPDATE
                SET
                    num_predictions = EXCLUDED.num_predictions,
                    mae = EXCLUDED.mae,
                    mape = EXCLUDED.mape,
                    rmse = EXCLUDED.rmse,
                    eval_start_time = EXCLUDED.eval_start_time,
                    eval_end_time = EXCLUDED.eval_end_time
                RETURNING performance_id
            """)

            result = await session.execute(aggregation_sql)
            created_ids = result.fetchall()
            created_count = len(created_ids)

            await session.commit()

            if created_count > 0:
                logger.info(f"✅ Created {created_count} performance aggregation record(s)")
            else:
                logger.info("⚠️ No performance aggregations created (insufficient data)")

            return created_count

    async def cleanup_old_performance_records(self, days_to_keep: int = 90):
        """
        Clean up old performance records beyond retention period.

        Args:
            days_to_keep: Number of days to keep (default 90)

        Returns:
            Number of records deleted
        """
        async with get_async_session() as session:
            delete_sql = text("""
                DELETE FROM prediction_performance
                WHERE eval_end_time < (NOW() - INTERVAL ':days days')
                RETURNING performance_id
            """)

            result = await session.execute(delete_sql, {"days": days_to_keep})
            deleted_ids = result.fetchall()
            deleted_count = len(deleted_ids)

            await session.commit()

            if deleted_count > 0:
                logger.info(f"🧹 Cleaned up {deleted_count} old performance record(s)")

            return deleted_count

    async def run_once(self):
        """
        Run one iteration of performance aggregation.

        This method:
        1. Aggregates performance metrics for last hour
        2. Cleans up old records (optional, once per day)
        """
        try:
            logger.info(f"🔄 PerformanceAggregator starting at {datetime.now()}")

            # Aggregate performance metrics
            created_count = await self.aggregate_performance_metrics()

            # Cleanup old records (run once per day at midnight)
            current_hour = datetime.now().hour
            if current_hour == 0:  # Midnight
                deleted_count = await self.cleanup_old_performance_records()
                if deleted_count > 0:
                    logger.info(f"🧹 Cleaned up {deleted_count} old record(s)")

            if created_count > 0:
                logger.info(f"✅ PerformanceAggregator completed: {created_count} record(s) created")
            else:
                logger.info("⚠️ PerformanceAggregator completed: No aggregations created")

        except Exception as e:
            logger.error(f"❌ PerformanceAggregator error: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def start(self, interval_seconds: int = 3600):
        """
        Start the aggregator to run every interval_seconds (default 1 hour).

        Args:
            interval_seconds: Interval in seconds (3600 = 1 hour)
        """
        self.is_running = True
        logger.info(f"🚀 PerformanceAggregator started (interval: {interval_seconds}s)")

        while self.is_running:
            await self.run_once()
            await asyncio.sleep(interval_seconds)

    def stop(self):
        """Stop the aggregator."""
        self.is_running = False
        logger.info("🛑 PerformanceAggregator stopped")


# Singleton instance
_aggregator_instance: Optional[PerformanceAggregator] = None


def get_performance_aggregator() -> PerformanceAggregator:
    """Get or create PerformanceAggregator singleton instance."""
    global _aggregator_instance
    if _aggregator_instance is None:
        _aggregator_instance = PerformanceAggregator()
    return _aggregator_instance
