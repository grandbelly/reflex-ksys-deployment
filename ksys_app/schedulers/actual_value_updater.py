"""
ActualValueUpdater - Fill actual values when target_time arrives.

This scheduler:
1. Finds predictions WHERE target_time <= NOW() AND actual_value IS NULL
2. Joins with influx_hist to get actual values
3. Updates predictions table with actual_value
4. Calculates errors (prediction_error, absolute_percentage_error)
5. Also updates training_evaluation table if needed

Runs every 10 minutes.

Architecture Reference: docs/forecast_result/ONLINE_FORECAST_REDESIGN_20251014.md
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging
logger = logging.getLogger(__name__)
from sqlalchemy import text

from ..db_orm import get_async_session


class ActualValueUpdater:
    """
    Fills actual_value in predictions table when target_time arrives.

    Key Principles:
    - Finds predictions where target_time has passed (target_time <= NOW())
    - Gets actual value from influx_hist
    - Updates both predictions and training_evaluation tables
    - Calculates prediction errors
    """

    def __init__(self):
        """Initialize updater."""
        self.is_running = False

    async def update_predictions_actual_values(self) -> int:
        """
        Update actual values in predictions table using BATCH processing.

        Optimizations:
        - Process in smaller batches (100 at a time)
        - Use tag_name directly instead of join with model_registry
        - Limit time range to reduce scan size

        Returns:
            Number of records updated
        """
        total_updated = 0
        batch_size = 100

        async with get_async_session() as session:
            # Set statement timeout (per batch)
            await session.execute(text("SET LOCAL statement_timeout = '15s'"))

            # OPTIMIZED: Process in batches, use tag_name directly
            update_sql = text("""
                WITH to_update AS (
                    SELECT prediction_id, tag_name, target_time, predicted_value
                    FROM predictions
                    WHERE target_time <= NOW()
                      AND target_time >= NOW() - INTERVAL '7 days'  -- Limit scan range
                      AND actual_value IS NULL
                    ORDER BY target_time DESC
                    LIMIT :batch_size
                ),
                matched_actuals AS (
                    SELECT DISTINCT ON (tu.prediction_id)
                        tu.prediction_id,
                        ih.value AS actual_value,
                        (tu.predicted_value - ih.value) AS prediction_error,
                        CASE
                            WHEN ih.value != 0
                            THEN ABS((tu.predicted_value - ih.value) / ih.value) * 100
                            ELSE NULL
                        END AS absolute_percentage_error
                    FROM to_update tu
                    JOIN influx_hist ih ON tu.tag_name = ih.tag_name
                    WHERE ih.ts BETWEEN (tu.target_time - INTERVAL '5 minutes')
                                    AND (tu.target_time + INTERVAL '5 minutes')
                    ORDER BY tu.prediction_id, ABS(EXTRACT(EPOCH FROM (ih.ts - tu.target_time)))
                )
                UPDATE predictions p
                SET
                    actual_value = ma.actual_value,
                    prediction_error = ma.prediction_error,
                    absolute_percentage_error = ma.absolute_percentage_error
                FROM matched_actuals ma
                WHERE p.prediction_id = ma.prediction_id
                RETURNING p.prediction_id
            """)

            # Process multiple batches until no more updates
            max_batches = 20  # Safety limit
            batch_count = 0

            while batch_count < max_batches:
                try:
                    result = await session.execute(update_sql, {"batch_size": batch_size})
                    updated_ids = result.fetchall()
                    updated_count = len(updated_ids)

                    if updated_count == 0:
                        break  # No more records to update

                    await session.commit()
                    total_updated += updated_count
                    batch_count += 1

                    logger.info(f"✅ Batch {batch_count}: Updated {updated_count} prediction(s)")

                    # If less than batch_size, we're done
                    if updated_count < batch_size:
                        break

                except Exception as e:
                    logger.error(f"❌ Batch {batch_count + 1} failed: {e}")
                    await session.rollback()
                    break

            if total_updated > 0:
                logger.info(f"✅ Total updated: {total_updated} prediction(s) across {batch_count} batch(es)")
            else:
                logger.info("⚠️ No predictions ready for actual value update")

            return total_updated

    async def update_training_evaluation_actual_values(self) -> int:
        """
        Update actual values in training_evaluation table.

        Returns:
            Number of records updated
        """
        async with get_async_session() as session:
            # Set statement timeout
            await session.execute(text("SET LOCAL statement_timeout = '30s'"))

            # Update actual values by joining with influx_hist
            update_sql = text("""
                WITH matched_actuals AS (
                    SELECT DISTINCT ON (te.evaluation_id)
                        te.evaluation_id,
                        ih.value AS actual_value,
                        (te.predicted_value - ih.value) AS prediction_error,
                        CASE
                            WHEN ih.value != 0
                            THEN ABS((te.predicted_value - ih.value) / ih.value) * 100
                            ELSE NULL
                        END AS absolute_percentage_error
                    FROM training_evaluation te
                    JOIN influx_hist ih ON te.sensor_tag = ih.tag_name
                    WHERE te.target_time <= NOW()
                      AND (te.actual_value IS NULL OR te.actual_value = 0)
                      AND ih.ts BETWEEN (te.target_time - INTERVAL '5 minutes')
                                    AND (te.target_time + INTERVAL '5 minutes')
                    ORDER BY te.evaluation_id, ABS(EXTRACT(EPOCH FROM (ih.ts - te.target_time)))
                )
                UPDATE training_evaluation te
                SET
                    actual_value = ma.actual_value,
                    prediction_error = ma.prediction_error,
                    absolute_percentage_error = ma.absolute_percentage_error
                FROM matched_actuals ma
                WHERE te.evaluation_id = ma.evaluation_id
                RETURNING te.evaluation_id
            """)

            result = await session.execute(update_sql)
            updated_ids = result.fetchall()
            updated_count = len(updated_ids)

            await session.commit()

            if updated_count > 0:
                logger.info(f"✅ Updated {updated_count} training evaluation(s) with actual values")

            return updated_count

    async def run_once(self):
        """
        Run one iteration of actual value updating.

        This method:
        1. Updates predictions table
        2. Updates training_evaluation table
        3. Reports total updates
        """
        try:
            logger.info(f"🔄 ActualValueUpdater starting at {datetime.now()}")

            # Update predictions table
            predictions_updated = await self.update_predictions_actual_values()

            # Update training_evaluation table
            evaluations_updated = await self.update_training_evaluation_actual_values()

            total_updated = predictions_updated + evaluations_updated

            if total_updated > 0:
                logger.info(f"✅ ActualValueUpdater completed: {total_updated} record(s) updated")
            else:
                logger.info("⚠️ ActualValueUpdater completed: No records updated")

        except Exception as e:
            logger.error(f"❌ ActualValueUpdater error: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def start(self, interval_seconds: int = 600):
        """
        Start the updater to run every interval_seconds (default 10 minutes).

        Args:
            interval_seconds: Interval in seconds (600 = 10 minutes)
        """
        self.is_running = True
        logger.info(f"🚀 ActualValueUpdater started (interval: {interval_seconds}s)")

        while self.is_running:
            await self.run_once()
            await asyncio.sleep(interval_seconds)

    def stop(self):
        """Stop the updater."""
        self.is_running = False
        logger.info("🛑 ActualValueUpdater stopped")


# Singleton instance
_updater_instance: Optional[ActualValueUpdater] = None


def get_actual_value_updater() -> ActualValueUpdater:
    """Get or create ActualValueUpdater singleton instance."""
    global _updater_instance
    if _updater_instance is None:
        _updater_instance = ActualValueUpdater()
    return _updater_instance
