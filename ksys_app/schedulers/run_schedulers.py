#!/usr/bin/env python3
"""
Standalone Forecasting Schedulers Service

This script runs all forecasting schedulers as a separate process:
- ForecastScheduler: Every 5 minutes (generates online predictions)
- ActualValueUpdater: Every 10 minutes (fills actual values)
- PerformanceAggregator: Every 1 hour (calculates metrics)

Usage:
    # Direct execution
    python ksys_app/schedulers/run_schedulers.py

    # Docker
    docker exec reflex-ksys-app python ksys_app/schedulers/run_schedulers.py

    # Docker Compose (recommended)
    docker-compose up -d scheduler-service

Architecture Reference:
    docs/forecast_result/ONLINE_FORECAST_REDESIGN_20251014.md
    SCHEDULER_ARCHITECTURE_REVIEW.md
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ksys_app.schedulers.scheduler_manager import (
    get_scheduler_manager,
    start_all_schedulers,
    stop_all_schedulers
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals (SIGINT, SIGTERM)"""
    global shutdown_requested
    logger.info("=" * 80)
    logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
    logger.info("=" * 80)
    shutdown_requested = True


async def main():
    """Main entry point for scheduler service"""
    global shutdown_requested

    logger.info("=" * 80)
    logger.info("🚀 FORECASTING SCHEDULERS SERVICE STARTING")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Schedulers:")
    logger.info("  - ForecastScheduler: Every 5 minutes")
    logger.info("  - ActualValueUpdater: Every 10 minutes")
    logger.info("  - PerformanceAggregator: Every 1 hour")
    logger.info("")
    logger.info("Press Ctrl+C to stop gracefully")
    logger.info("=" * 80)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start all schedulers (this will run indefinitely)
        await start_all_schedulers()

    except KeyboardInterrupt:
        logger.info("🛑 Schedulers stopped by user (Ctrl+C)")

    except Exception as e:
        logger.error(f"❌ Fatal error in scheduler service: {e}", exc_info=True)
        return 1

    finally:
        if shutdown_requested:
            logger.info("🧹 Cleaning up schedulers...")
            try:
                await stop_all_schedulers()
                logger.info("✅ Schedulers stopped gracefully")
            except Exception as e:
                logger.error(f"❌ Error during shutdown: {e}")

        logger.info("=" * 80)
        logger.info("👋 Forecasting Schedulers Service Exited")
        logger.info("=" * 80)

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler service: {e}", exc_info=True)
        sys.exit(1)
