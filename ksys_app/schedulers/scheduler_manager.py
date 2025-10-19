"""
Scheduler Manager - Start and manage all forecasting schedulers.

This manager:
1. Starts all three schedulers in background tasks
2. Provides graceful shutdown
3. Monitors scheduler health

Usage:
    from ksys_app.schedulers.scheduler_manager import start_all_schedulers

    # In ksys_app.py after app initialization:
    asyncio.create_task(start_all_schedulers())
"""

import asyncio
from typing import List, Optional
import logging
logger = logging.getLogger(__name__)

from .forecast_scheduler import get_forecast_scheduler
from .actual_value_updater import get_actual_value_updater
from .performance_aggregator import get_performance_aggregator


class SchedulerManager:
    """Manages all forecasting schedulers."""

    def __init__(self):
        """Initialize manager."""
        self.tasks: List[asyncio.Task] = []
        self.is_running = False

    async def start_all(self):
        """Start all schedulers in background tasks."""
        if self.is_running:
            logger.info("⚠️ Schedulers already running")
            return

        self.is_running = True
        logger.info("=" * 80)
        logger.info("🚀 STARTING ALL FORECASTING SCHEDULERS")
        logger.info("=" * 80)

        try:
            from datetime import datetime

            # Get scheduler instances
            forecast_scheduler = get_forecast_scheduler()
            actual_value_updater = get_actual_value_updater()
            performance_aggregator = get_performance_aggregator()

            # Calculate delay to align with 10-minute schedule
            now = datetime.now()
            current_minute = now.minute
            current_second = now.second

            # ===================================================================
            # 10-MINUTE PIPELINE SCHEDULE (Sequential execution within 10min)
            # ===================================================================
            # x:00 → ForecastScheduler (generate predictions) ~1min
            # x:01 → ActualValueUpdater (backfill actual values) ~1-2min
            # x:03 → PerformanceAggregator (calculate metrics) ~1min
            # x:04 → Complete → Forecast Player UI updates
            # x:10 → Next cycle starts
            # ===================================================================

            # ForecastScheduler: Run at x:00, x:10, x:20, x:30, x:40, x:50
            forecast_target_minutes = [0, 10, 20, 30, 40, 50]
            next_forecast_minute = min([m for m in forecast_target_minutes if m > current_minute] + [forecast_target_minutes[0] + 60])
            forecast_delay = ((next_forecast_minute - current_minute) * 60 - current_second) % 3600

            # ActualValueUpdater: Run at x:01, x:11, x:21, x:31, x:41, x:51 (1min after Forecast)
            updater_target_minutes = [1, 11, 21, 31, 41, 51]
            next_updater_minute = min([m for m in updater_target_minutes if m > current_minute] + [updater_target_minutes[0] + 60])
            updater_delay = ((next_updater_minute - current_minute) * 60 - current_second) % 3600

            # PerformanceAggregator: Run at x:03, x:13, x:23, x:33, x:43, x:53 (3min after Forecast)
            aggregator_target_minutes = [3, 13, 23, 33, 43, 53]
            next_aggregator_minute = min([m for m in aggregator_target_minutes if m > current_minute] + [aggregator_target_minutes[0] + 60])
            aggregator_delay = ((next_aggregator_minute - current_minute) * 60 - current_second) % 3600

            logger.info(f"⏰ Current time: {now.strftime('%H:%M:%S')}")
            logger.info(f"⏰ ForecastScheduler will start in {forecast_delay}s (at x:{next_forecast_minute%60:02d})")
            logger.info(f"⏰ ActualValueUpdater will start in {updater_delay}s (at x:{next_updater_minute%60:02d})")
            logger.info(f"⏰ PerformanceAggregator will start in {aggregator_delay}s (at x:{next_aggregator_minute%60:02d})")

            # Start ForecastScheduler (every 10 minutes, at x:00)
            async def start_forecast_with_delay():
                await asyncio.sleep(forecast_delay)
                await forecast_scheduler.start(interval_seconds=600)  # 10 minutes

            forecast_task = asyncio.create_task(start_forecast_with_delay())
            self.tasks.append(forecast_task)
            logger.info("✅ ForecastScheduler task created (10-minute interval, starts at x:00)")

            # Start ActualValueUpdater (every 10 minutes, at x:01)
            async def start_updater_with_delay():
                await asyncio.sleep(updater_delay)
                await actual_value_updater.start(interval_seconds=600)  # 10 minutes

            updater_task = asyncio.create_task(start_updater_with_delay())
            self.tasks.append(updater_task)
            logger.info("✅ ActualValueUpdater task created (10-minute interval, starts at x:01)")

            # Start PerformanceAggregator (every 10 minutes, at x:03)
            async def start_aggregator_with_delay():
                await asyncio.sleep(aggregator_delay)
                await performance_aggregator.start(interval_seconds=600)  # 10 minutes

            aggregator_task = asyncio.create_task(start_aggregator_with_delay())
            self.tasks.append(aggregator_task)
            logger.info("✅ PerformanceAggregator task created (10-minute interval, starts at x:03)")

            logger.info("=" * 80)
            logger.info("✅ ALL SCHEDULERS CONFIGURED SUCCESSFULLY")
            logger.info("=" * 80)

            # Keep tasks alive
            await asyncio.gather(*self.tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"❌ Scheduler startup error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.is_running = False

    async def stop_all(self):
        """Stop all schedulers gracefully."""
        if not self.is_running:
            return

        logger.info("=" * 80)
        logger.info("🛑 STOPPING ALL SCHEDULERS")
        logger.info("=" * 80)

        # Stop schedulers
        get_forecast_scheduler().stop()
        get_actual_value_updater().stop()
        get_performance_aggregator().stop()

        # Cancel tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for cancellation
        await asyncio.gather(*self.tasks, return_exceptions=True)

        self.tasks.clear()
        self.is_running = False

        logger.info("✅ All schedulers stopped")
        logger.info("=" * 80)


# Singleton instance
_manager_instance: Optional[SchedulerManager] = None


def get_scheduler_manager() -> SchedulerManager:
    """Get or create SchedulerManager singleton instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SchedulerManager()
    return _manager_instance


async def start_all_schedulers():
    """
    Convenience function to start all schedulers.

    Usage in ksys_app.py:
        import asyncio
        from ksys_app.schedulers.scheduler_manager import start_all_schedulers

        # After app initialization:
        asyncio.create_task(start_all_schedulers())
    """
    manager = get_scheduler_manager()
    await manager.start_all()


async def stop_all_schedulers():
    """
    Convenience function to stop all schedulers.

    Usage:
        from ksys_app.schedulers.scheduler_manager import stop_all_schedulers

        await stop_all_schedulers()
    """
    manager = get_scheduler_manager()
    await manager.stop_all()
