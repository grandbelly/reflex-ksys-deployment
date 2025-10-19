"""
Influx Latest Table Updater
Periodically updates influx_latest table with most recent sensor values
"""

import asyncio
import asyncpg
from datetime import datetime
import os
from typing import Optional

# Database connection string
DB_DSN = os.getenv("TS_DSN", "postgresql://ecoanp_user:ecoanp_password@localhost:5432/ecoanp")

async def update_influx_latest(conn: Optional[asyncpg.Connection] = None) -> bool:
    """
    Update influx_latest table with most recent sensor values

    Returns:
        bool: True if successful, False otherwise
    """
    close_conn = False
    try:
        # Create connection if not provided
        if conn is None:
            conn = await asyncpg.connect(DB_DSN)
            close_conn = True

        # Call the update function
        await conn.execute("SELECT update_influx_latest()")

        # Verify the update
        result = await conn.fetch("""
            SELECT
                COUNT(*) as count,
                MAX(ts) as latest_ts
            FROM influx_latest
        """)

        if result and result[0]['count'] > 0:
            print(f"✅ influx_latest updated: {result[0]['count']} sensors, latest: {result[0]['latest_ts']}")
            return True
        else:
            print("⚠️ influx_latest is empty after update")
            return False

    except Exception as e:
        print(f"❌ Error updating influx_latest: {e}")
        return False
    finally:
        if close_conn and conn:
            await conn.close()

async def periodic_updater(interval_seconds: int = 60):
    """
    Periodically update influx_latest table

    Args:
        interval_seconds: Update interval in seconds (default: 60)
    """
    print(f"🔄 Starting influx_latest updater (interval: {interval_seconds}s)")

    while True:
        try:
            await update_influx_latest()
        except Exception as e:
            print(f"❌ Updater error: {e}")

        await asyncio.sleep(interval_seconds)

def start_background_updater(interval_seconds: int = 60):
    """
    Start the updater as a background task

    Args:
        interval_seconds: Update interval in seconds
    """
    loop = asyncio.get_event_loop()
    task = loop.create_task(periodic_updater(interval_seconds))
    return task

if __name__ == "__main__":
    # Test the updater
    asyncio.run(update_influx_latest())