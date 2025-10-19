"""
Communication Service
- Handles communication statistics queries
- Returns data for heatmap and analytics
"""
from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy import text
from ksys_app.services.base_service import BaseService


class CommunicationService(BaseService):
    """Service for communication success rate monitoring"""

    async def get_available_tags(self) -> List[str]:
        """
        Get list of available sensor tags

        Returns:
            List of tag names
        """
        query = text("""
            SELECT DISTINCT tag_name
            FROM influx_latest
            ORDER BY tag_name
        """)

        rows = await self.execute_query(query, timeout="5s")
        return [row['tag_name'] for row in rows]

    async def get_hourly_stats(self, tag: str, days: int) -> List[Dict]:
        """
        Get hourly communication statistics (KST timezone)
        Automatically detects data collection interval

        Args:
            tag: Sensor tag name
            days: Number of days to look back

        Returns:
            List of hourly statistics with:
            - timestamp: Hour timestamp (KST)
            - record_count: Actual record count
            - expected_count: Expected record count (auto-detected from actual interval)
            - success_rate: Percentage of expected records received
            - date: Date string (KST)
            - hour: Hour of day (KST)
        """
        query = text("""
            WITH hourly_data AS (
                SELECT
                    (date_trunc('hour', ts AT TIME ZONE 'Asia/Seoul'))::timestamp as timestamp_kst,
                    COUNT(*) as record_count,
                    -- FIXED interval: 10 seconds = 360 records per hour
                    360 as expected_count
                FROM influx_hist
                WHERE (ts AT TIME ZONE 'Asia/Seoul') >= (NOW() AT TIME ZONE 'Asia/Seoul') - :days * INTERVAL '1 day'
                  AND (ts AT TIME ZONE 'Asia/Seoul') < (NOW() AT TIME ZONE 'Asia/Seoul')
                  AND tag_name = :tag
                GROUP BY date_trunc('hour', ts AT TIME ZONE 'Asia/Seoul')
            )
            SELECT
                timestamp_kst as timestamp,
                record_count,
                GREATEST(expected_count, 1) as expected_count,  -- Minimum 1 to avoid division issues
                LEAST(
                    ROUND((record_count::NUMERIC / NULLIF(GREATEST(expected_count, 1), 0)) * 100, 2),
                    100.0  -- Cap at 100%
                ) as success_rate,
                TO_CHAR(timestamp_kst, 'YYYY-MM-DD') as date,
                EXTRACT(hour FROM timestamp_kst) as hour
            FROM hourly_data
            ORDER BY timestamp_kst DESC
        """)

        return await self.execute_query(
            query,
            {"days": days, "tag": tag},
            timeout="15s"  # Longer timeout for larger queries
        )

    async def get_daily_stats(self, days: int) -> List[Dict]:
        """
        Get daily statistics for all tags (KST timezone)
        Automatically detects data collection interval per tag
        Only returns days with actual data (not full calendar period)

        Args:
            days: Number of days to look back

        Returns:
            List of daily statistics with:
            - date: Date (KST)
            - tag_name: Sensor tag
            - daily_count: Records for the day
            - expected_daily_count: Expected records (auto-detected, 86400 / interval)
            - success_rate: Percentage
        """
        query = text("""
            WITH interval_per_tag AS (
                -- Detect interval for each tag (two-step to avoid window function in aggregate)
                SELECT
                    tag_name,
                    COALESCE(
                        ROUND(AVG(interval_seconds))::int,
                        10  -- Default 10 seconds
                    ) as detected_interval_seconds
                FROM (
                    SELECT
                        tag_name,
                        EXTRACT(EPOCH FROM (ts - LAG(ts) OVER (PARTITION BY tag_name ORDER BY ts))) as interval_seconds
                    FROM (
                        SELECT tag_name, ts
                        FROM influx_hist
                        WHERE ts >= NOW() - INTERVAL '2 hours'
                        ORDER BY tag_name, ts
                    ) sample
                ) intervals
                WHERE interval_seconds IS NOT NULL
                GROUP BY tag_name
            ),
            daily_intervals AS (
                -- First calculate intervals between consecutive records
                SELECT
                    (date_trunc('day', ts AT TIME ZONE 'Asia/Seoul'))::date as date_kst,
                    tag_name,
                    EXTRACT(EPOCH FROM (ts - LAG(ts) OVER (PARTITION BY tag_name, date_trunc('day', ts AT TIME ZONE 'Asia/Seoul') ORDER BY ts))) as interval_seconds
                FROM influx_hist
                WHERE (ts AT TIME ZONE 'Asia/Seoul') >= (NOW() AT TIME ZONE 'Asia/Seoul') - :days * INTERVAL '1 day'
                  AND (ts AT TIME ZONE 'Asia/Seoul') < (NOW() AT TIME ZONE 'Asia/Seoul')
            ),
            daily_active_time AS (
                -- Then sum the intervals per day per tag
                SELECT
                    date_kst,
                    tag_name,
                    COALESCE(SUM(interval_seconds), 0) as active_seconds
                FROM daily_intervals
                WHERE interval_seconds IS NOT NULL
                GROUP BY date_kst, tag_name
            ),
            daily_data AS (
                SELECT
                    (date_trunc('day', h.ts AT TIME ZONE 'Asia/Seoul'))::date as date_kst,
                    h.tag_name,
                    COUNT(*) as daily_count,
                    -- Calculate expected based on ACTIVE time only (excludes downtime)
                    CASE
                        WHEN COALESCE(dat.active_seconds, 0) > 0
                        THEN (dat.active_seconds / COALESCE(i.detected_interval_seconds, 10))::int
                        ELSE 0
                    END as expected_daily_count
                FROM influx_hist h
                LEFT JOIN interval_per_tag i ON h.tag_name = i.tag_name
                LEFT JOIN daily_active_time dat ON
                    h.tag_name = dat.tag_name AND
                    (date_trunc('day', h.ts AT TIME ZONE 'Asia/Seoul'))::date = dat.date_kst
                WHERE (h.ts AT TIME ZONE 'Asia/Seoul') >= (NOW() AT TIME ZONE 'Asia/Seoul') - :days * INTERVAL '1 day'
                  AND (h.ts AT TIME ZONE 'Asia/Seoul') < (NOW() AT TIME ZONE 'Asia/Seoul')
                GROUP BY date_trunc('day', h.ts AT TIME ZONE 'Asia/Seoul'), h.tag_name, i.detected_interval_seconds, dat.active_seconds
            )
            SELECT
                date_kst::text as date,  -- Convert date to string
                tag_name,
                daily_count,
                GREATEST(expected_daily_count, 1) as expected_daily_count,  -- Minimum 1
                LEAST(
                    ROUND((daily_count::NUMERIC / NULLIF(GREATEST(expected_daily_count, 1), 0)) * 100, 2),
                    100.0  -- Cap at 100%
                )::float as success_rate  -- Convert to float
            FROM daily_data
            WHERE daily_count > 0  -- Only return days with actual data
            ORDER BY date_kst DESC, tag_name
        """)

        rows = await self.execute_query(
            query,
            {"days": days},
            timeout="15s"
        )

        # Convert to serializable format
        return [
            {
                "date": row["date"],
                "tag_name": row["tag_name"],
                "daily_count": int(row["daily_count"]),
                "expected_daily_count": int(row["expected_daily_count"]),
                "success_rate": float(row["success_rate"])
            }
            for row in rows
        ]

    async def get_tag_summary(self, tag: str, days: int) -> Dict:
        """
        Get summary statistics for a specific tag (KST timezone)

        Uses dynamic interval detection to calculate expected records.

        Args:
            tag: Sensor tag name
            days: Number of days to look back

        Returns:
            Dict with summary stats:
            - total_records: Total records received
            - expected_records: Total expected records (based on detected interval)
            - success_rate: Overall success rate
            - active_hours: Number of hours with data (KST)
        """
        # Ensure days is int (防止 문자열 전달)
        days_int = int(days) if not isinstance(days, int) else days

        query = text("""
            WITH interval_detection AS (
                -- Detect actual data interval for this tag
                SELECT
                    COALESCE(
                        ROUND(AVG(interval_seconds))::int,
                        10  -- Default to 10 seconds if detection fails
                    ) as detected_interval_seconds
                FROM (
                    SELECT
                        EXTRACT(EPOCH FROM (ts - LAG(ts) OVER (ORDER BY ts))) as interval_seconds
                    FROM (
                        SELECT ts
                        FROM influx_hist
                        WHERE tag_name = :tag
                          AND ts >= NOW() - INTERVAL '2 hours'
                        ORDER BY ts
                        LIMIT 100
                    ) sample
                ) intervals
                WHERE interval_seconds IS NOT NULL
            ),
            time_intervals AS (
                -- First calculate intervals between consecutive records
                SELECT
                    EXTRACT(EPOCH FROM (ts - LAG(ts) OVER (ORDER BY ts))) as interval_seconds
                FROM influx_hist
                WHERE (ts AT TIME ZONE 'Asia/Seoul') >= (NOW() AT TIME ZONE 'Asia/Seoul') - :days * INTERVAL '1 day'
                  AND (ts AT TIME ZONE 'Asia/Seoul') < (NOW() AT TIME ZONE 'Asia/Seoul')
                  AND tag_name = :tag
            ),
            active_time AS (
                -- Then sum the intervals (excludes system downtime periods)
                SELECT
                    COALESCE(SUM(interval_seconds), 0) as total_active_seconds
                FROM time_intervals
                WHERE interval_seconds IS NOT NULL
            ),
            stats AS (
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT date_trunc('hour', ts AT TIME ZONE 'Asia/Seoul')) as active_hours,
                    -- Expected = active time / interval (only count when system was running)
                    CASE
                        WHEN (SELECT total_active_seconds FROM active_time) > 0
                        THEN ((SELECT total_active_seconds FROM active_time) / (SELECT detected_interval_seconds FROM interval_detection))::int
                        ELSE 0
                    END as expected_records
                FROM influx_hist
                WHERE (ts AT TIME ZONE 'Asia/Seoul') >= (NOW() AT TIME ZONE 'Asia/Seoul') - :days * INTERVAL '1 day'
                  AND (ts AT TIME ZONE 'Asia/Seoul') < (NOW() AT TIME ZONE 'Asia/Seoul')
                  AND tag_name = :tag
            )
            SELECT
                total_records,
                GREATEST(expected_records, 1) as expected_records,  -- Minimum 1
                active_hours,
                LEAST(
                    ROUND((total_records::NUMERIC / NULLIF(GREATEST(expected_records, 1), 0)) * 100, 2),
                    100.0  -- Cap at 100%
                ) as success_rate
            FROM stats
        """)

        rows = await self.execute_query(
            query,
            {
                "tag": tag,
                "days": days_int
            },
            timeout="10s"
        )

        if rows:
            return rows[0]
        else:
            return {
                "total_records": 0,
                "expected_records": 0,
                "active_hours": 0,
                "success_rate": 0.0
            }