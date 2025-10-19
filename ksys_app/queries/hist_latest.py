"""
Get latest values directly from influx_hist table
"""

import psycopg
from ..db import _dsn
from typing import List, Dict, Any

async def get_latest_hist_values(tag_name: str = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Get latest N values directly from influx_hist table

    Args:
        tag_name: Optional tag filter, if None gets all tags
        limit: Number of latest values per tag (default 5)
    """
    async with await psycopg.AsyncConnection.connect(_dsn()) as conn:
        async with conn.cursor() as cur:
            if tag_name:
                # Single tag - get latest N values
                query = """
                    SELECT
                        tag_name,
                        value,
                        ts,
                        ts AT TIME ZONE 'Asia/Seoul' as ts_kst
                    FROM influx_hist
                    WHERE tag_name = %s
                    ORDER BY ts DESC
                    LIMIT %s
                """
                await cur.execute(query, (tag_name, limit))
            else:
                # All tags - get latest N values per tag using window function
                query = f"""
                    WITH latest_per_tag AS (
                        SELECT
                            tag_name,
                            value,
                            ts,
                            ts AT TIME ZONE 'Asia/Seoul' as ts_kst,
                            ROW_NUMBER() OVER (PARTITION BY tag_name ORDER BY ts DESC) as rn
                        FROM influx_hist
                    )
                    SELECT
                        tag_name,
                        value,
                        ts,
                        ts_kst
                    FROM latest_per_tag
                    WHERE rn <= {limit}
                    ORDER BY tag_name, ts DESC
                """
                await cur.execute(query)

            rows = await cur.fetchall()
            return [
                {
                    "tag_name": row[0],
                    "value": float(row[1]) if row[1] is not None else 0.0,
                    "ts": row[2],  # Keep UTC timestamp with timezone
                    "ts_kst": row[3]  # Seoul time without timezone (for display only)
                }
                for row in rows
            ]