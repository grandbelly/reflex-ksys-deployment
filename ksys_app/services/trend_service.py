"""
Trend Service - Raw SQL Service Pattern (NO ORM)
Based on successful dashboard pattern
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import pytz

class TrendService:
    """Trend data service using raw SQL"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_tags(self, limit: int = 20) -> List[str]:
        """Get list of available tags"""
        await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

        q = text("""
            SELECT DISTINCT tag_name
            FROM influx_latest
            WHERE tag_name IS NOT NULL
            ORDER BY tag_name
            LIMIT :limit
        """)

        result = await self.session.execute(q, {"limit": limit})
        rows = result.mappings().all()

        return [row["tag_name"] for row in rows]

    async def get_series_data(
        self,
        tag_name: str,
        start_time: datetime,
        end_time: datetime,
        aggregation_table: str,
        max_points: int = 5000
    ) -> List[Dict[str, Any]]:
        """Get time series data for a tag"""

        # Validate table name to prevent SQL injection
        allowed_tables = {
            "influx_agg_1m", "influx_agg_10m",
            "influx_agg_1h", "influx_agg_1d"
        }
        if aggregation_table not in allowed_tables:
            aggregation_table = "influx_agg_10m"

        await self.session.execute(text("SET LOCAL statement_timeout = '10s'"))

        # Use parameterized query for everything except table name
        # Note: Use > instead of >= for start_time to get exact count
        # e.g., 24 hours with 10m intervals = 144 buckets (not 145)
        q = text(f"""
            SELECT
                tag_name,
                bucket,
                avg::float AS avg,
                min::float AS min,
                max::float AS max,
                first::float AS first,
                last::float AS last,
                count::int AS count
            FROM {aggregation_table}
            WHERE tag_name = :tag_name
            AND bucket > :start_time
            AND bucket <= :end_time
            ORDER BY bucket DESC
            LIMIT :max_points
        """)

        result = await self.session.execute(q, {
            "tag_name": tag_name,
            "start_time": start_time,
            "end_time": end_time,
            "max_points": max_points
        })

        rows = result.mappings().all()

        # Format results with KST timezone
        kst = pytz.timezone('Asia/Seoul')
        series = []

        for row in rows:
            # Convert UTC to KST
            bucket_kst = None
            bucket_formatted = ""

            if row['bucket']:
                # bucket이 naive datetime이면 UTC로 간주하고 KST로 변환
                if row['bucket'].tzinfo is None:
                    bucket_utc = pytz.UTC.localize(row['bucket'])
                    bucket_kst = bucket_utc.astimezone(kst)
                else:
                    bucket_kst = row['bucket'].astimezone(kst)
                bucket_formatted = bucket_kst.strftime("%Y-%m-%d %H:%M:%S")

            series.append({
                "tag_name": row['tag_name'],
                "bucket": row['bucket'],
                "bucket_formatted": bucket_formatted,
                "avg": round(float(row['avg']), 2) if row['avg'] else 0.0,
                "min": round(float(row['min']), 2) if row['min'] else 0.0,
                "max": round(float(row['max']), 2) if row['max'] else 0.0,
                "first": round(float(row['first']), 2) if row['first'] else 0.0,
                "last": round(float(row['last']), 2) if row['last'] else 0.0,
                "count": row.get('count', 0) or 0
            })

        return series

    async def get_realtime_data(self, tag_name: str) -> Optional[Dict[str, Any]]:
        """Get latest realtime data for a tag"""
        await self.session.execute(text("SET LOCAL statement_timeout = '2s'"))

        q = text("""
            SELECT
                tag_name,
                value::float AS value,
                ts AT TIME ZONE 'UTC' AS ts,
                quality
            FROM influx_latest
            WHERE tag_name = :tag_name
            LIMIT 1
        """)

        result = await self.session.execute(q, {"tag_name": tag_name})
        row = result.mappings().first()

        if not row:
            return None

        # Convert to KST
        kst = pytz.timezone('Asia/Seoul')
        ts_kst = None
        ts_formatted = ""

        if row['ts']:
            if row['ts'].tzinfo is None:
                ts_utc = pytz.UTC.localize(row['ts'])
                ts_kst = ts_utc.astimezone(kst)
            else:
                ts_kst = row['ts'].astimezone(kst)
            ts_formatted = ts_kst.strftime("%Y-%m-%d %H:%M:%S")

        return {
            "tag_name": row['tag_name'],
            "value": round(float(row['value']), 2) if row['value'] else 0.0,
            "ts": row['ts'],
            "ts_formatted": ts_formatted,
            "quality": row['quality']
        }

    async def get_statistics(
        self,
        tag_name: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get statistics for a tag over time period"""
        await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

        q = text("""
            SELECT
                COUNT(*) AS count,
                AVG(value)::float AS avg,
                MIN(value)::float AS min,
                MAX(value)::float AS max,
                STDDEV(value)::float AS stddev
            FROM influx_hist
            WHERE tag_name = :tag_name
            AND ts >= NOW() - INTERVAL ':hours hours'
        """)

        result = await self.session.execute(q, {
            "tag_name": tag_name,
            "hours": hours
        })

        row = result.mappings().first()

        return {
            "count": row['count'] or 0,
            "avg": round(float(row['avg']), 2) if row['avg'] else 0.0,
            "min": round(float(row['min']), 2) if row['min'] else 0.0,
            "max": round(float(row['max']), 2) if row['max'] else 0.0,
            "stddev": round(float(row['stddev']), 2) if row['stddev'] else 0.0
        }