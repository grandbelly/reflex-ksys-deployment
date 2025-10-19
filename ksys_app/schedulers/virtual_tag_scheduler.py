"""
Virtual Tag Scheduler - Periodic calculation of Virtual Tags

This scheduler:
1. Runs every 10 minutes (aligned with influx_agg_10m aggregation)
2. Calculates all active Virtual Tags
3. Stores results in virtual_tag_values table
4. Registers Virtual Tags in influx_tag table (if not already registered)
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import text
from reflex.utils import console

# Add project root to path for standalone execution
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ksys_app.db_orm import get_async_session
from ksys_app.services.virtual_tag_service import VirtualTagService


async def register_virtual_tags_in_influx_tag():
    """
    Register Virtual Tags in influx_tag table so they appear in dashboards

    This ensures Virtual Tags are treated like regular sensors
    """
    async with get_async_session() as session:
        query = text("""
            INSERT INTO influx_tag (key, tag_id, tag_name, tag_type, unit, description, meta, updated_at)
            SELECT
                'virtual_' || tag_name,
                tag_name,
                tag_name,
                'virtual',
                unit,
                description,
                jsonb_build_object(
                    'formula_type', formula_type,
                    'formula', formula,
                    'source_tags', source_tags
                ),
                now()
            FROM virtual_tag_definitions
            WHERE is_active = true
            ON CONFLICT (key) DO UPDATE
            SET
                tag_id = EXCLUDED.tag_id,
                tag_name = EXCLUDED.tag_name,
                tag_type = EXCLUDED.tag_type,
                unit = EXCLUDED.unit,
                description = EXCLUDED.description,
                meta = EXCLUDED.meta,
                updated_at = now()
        """)

        result = await session.execute(query)
        await session.commit()

        count = result.rowcount
        console.info(f"📝 Registered {count} Virtual Tags in influx_tag")


async def calculate_virtual_tags_periodic():
    """
    Periodic Virtual Tag calculation task

    Runs every 1 minute at :00 seconds
    """
    console.info("🚀 Virtual Tag Scheduler started")

    # Initial registration
    await register_virtual_tags_in_influx_tag()

    # Run forever with 1-minute intervals
    while True:
        try:
            # Calculate immediately, then wait until next minute
            start_time = datetime.now()
            console.info(f"\n{'='*60}")
            console.info(f"🔄 Virtual Tag calculation started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            console.info(f"{'='*60}")

            async with get_async_session() as session:
                service = VirtualTagService(session)

                # Calculate with 1-minute time delta
                await service.calculate_and_store(time_delta=1.0)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            console.info(f"✅ Calculation completed in {duration:.2f}s")

            # Wait until next minute at :00 seconds (accounting for calculation time)
            now = datetime.now()
            seconds_to_wait = 60 - now.second
            if seconds_to_wait > 0:
                console.info(f"⏱️  Waiting {seconds_to_wait}s until next minute...")
                await asyncio.sleep(seconds_to_wait)

        except Exception as e:
            console.error(f"❌ Virtual Tag calculation error: {e}")
            # Continue after error - wait 10 seconds before retry
            await asyncio.sleep(10)


async def calculate_virtual_tags_once():
    """
    Run Virtual Tag calculation once (for testing/manual trigger)
    """
    console.info("🔄 One-time Virtual Tag calculation")

    # Register first
    await register_virtual_tags_in_influx_tag()

    # Calculate
    async with get_async_session() as session:
        service = VirtualTagService(session)
        await service.calculate_and_store(time_delta=10.0)

    console.info("✅ One-time calculation complete")


if __name__ == "__main__":
    # Run periodic scheduler (production mode)
    asyncio.run(calculate_virtual_tags_periodic())
