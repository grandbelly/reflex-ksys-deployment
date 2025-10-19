"""
Communication success rate queries for time-series data collection monitoring
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from ksys_app.db import q


async def communication_hourly_stats(
    tag_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Get hourly communication statistics for tags
    
    Returns data aggregated by hour showing:
    - Total expected records (based on collection interval)
    - Actual collected records
    - Success rate percentage
    """
    
    # Default to last 7 days if no date range specified
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(days=7)
    
    # Query for hourly statistics
    query = """
    WITH hourly_data AS (
        SELECT 
            date_trunc('hour', ts) as hour,
            tag_name,
            COUNT(*) as record_count,
            -- Assuming 5-second collection interval, expect 720 records per hour
            720 as expected_count
        FROM influx_hist
        WHERE ts >= %s AND ts < %s
        {tag_filter}
        GROUP BY date_trunc('hour', ts), tag_name
    ),
    hourly_stats AS (
        SELECT 
            hour,
            tag_name,
            record_count,
            expected_count,
            ROUND((record_count::NUMERIC / expected_count) * 100, 2) as success_rate
        FROM hourly_data
    )
    SELECT 
        hour::timestamp as timestamp,
        EXTRACT(DOW FROM hour) as day_of_week,
        EXTRACT(HOUR FROM hour) as hour_of_day,
        TO_CHAR(hour, 'YYYY-MM-DD') as date,
        TO_CHAR(hour, 'HH24:00') as time_label,
        tag_name,
        record_count,
        expected_count,
        success_rate,
        CASE 
            WHEN success_rate >= 95 THEN 'excellent'
            WHEN success_rate >= 80 THEN 'good'
            WHEN success_rate >= 60 THEN 'warning'
            ELSE 'critical'
        END as status
    FROM hourly_stats
    ORDER BY hour DESC, tag_name
    """
    
    # Add tag filter if specified
    tag_filter = ""
    params = [start_date, end_date]
    
    if tag_name:
        tag_filter = "AND tag_name = %s"
        params.append(tag_name)
    
    query = query.format(tag_filter=tag_filter)
    
    try:
        result = await q(query, tuple(params))
        return result
    except Exception as e:
        print(f"Error fetching communication stats: {e}")
        return []


async def communication_daily_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Get daily summary of communication success rates across all tags
    """
    
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    query = """
    WITH daily_data AS (
        SELECT 
            date_trunc('day', ts) as day,
            tag_name,
            COUNT(*) as daily_count,
            -- Assuming 5-second interval, expect 17280 records per day (720*24)
            17280 as expected_daily_count
        FROM influx_hist
        WHERE ts >= %s AND ts < %s
        GROUP BY date_trunc('day', ts), tag_name
    )
    SELECT 
        day::date as date,
        tag_name,
        daily_count,
        expected_daily_count,
        ROUND((daily_count::NUMERIC / expected_daily_count) * 100, 2) as success_rate,
        CASE 
            WHEN (daily_count::NUMERIC / expected_daily_count) >= 0.95 THEN 'excellent'
            WHEN (daily_count::NUMERIC / expected_daily_count) >= 0.80 THEN 'good'
            WHEN (daily_count::NUMERIC / expected_daily_count) >= 0.60 THEN 'warning'
            ELSE 'critical'
        END as status
    FROM daily_data
    ORDER BY day DESC, tag_name
    """
    
    try:
        result = await q(query, (start_date, end_date))
        return result
    except Exception as e:
        print(f"Error fetching daily summary: {e}")
        return []


async def get_available_tags() -> List[str]:
    """
    Get list of all available sensor tags
    """
    
    query = """
    SELECT DISTINCT tag_name 
    FROM influx_latest
    ORDER BY tag_name
    """
    
    try:
        result = await q(query, ())
        return [row['tag_name'] for row in result]
    except Exception as e:
        print(f"Error fetching tags: {e}")
        return []


async def communication_heatmap_data(
    tag_name: str,
    days: int = 7
) -> Dict[str, Any]:
    """
    Get heatmap data for a specific tag
    
    Returns data formatted for heatmap visualization:
    - X-axis: Hours (0-23)
    - Y-axis: Days
    - Value: Success rate percentage
    """
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    query = """
    WITH hourly_data AS (
        SELECT 
            date_trunc('hour', ts) as hour,
            COUNT(*) as record_count
        FROM influx_hist
        WHERE ts >= %s AND ts < %s AND tag_name = %s
        GROUP BY date_trunc('hour', ts)
    ),
    time_grid AS (
        SELECT 
            generate_series(
                date_trunc('hour', %s::timestamp),
                date_trunc('hour', %s::timestamp),
                '1 hour'::interval
            ) as hour
    ),
    complete_data AS (
        SELECT 
            g.hour,
            COALESCE(h.record_count, 0) as record_count,
            720 as expected_count  -- 720 records per hour (5-second interval)
        FROM time_grid g
        LEFT JOIN hourly_data h ON g.hour = h.hour
    )
    SELECT 
        TO_CHAR(hour, 'YYYY-MM-DD') as date,
        EXTRACT(HOUR FROM hour) as hour_of_day,
        record_count,
        expected_count,
        ROUND((record_count::NUMERIC / expected_count) * 100, 2) as success_rate
    FROM complete_data
    ORDER BY hour
    """
    
    try:
        result = await q(query, (start_date, end_date, tag_name, start_date, end_date))
        
        # Transform data for heatmap format
        heatmap_data = {}
        dates = []
        
        for row in result:
            date = row['date']
            hour = int(row['hour_of_day'])
            success_rate = float(row['success_rate'])
            
            if date not in heatmap_data:
                heatmap_data[date] = [0] * 24
                dates.append(date)
            
            heatmap_data[date][hour] = success_rate
        
        return {
            'tag_name': tag_name,
            'dates': dates,
            'hours': list(range(24)),
            'data': heatmap_data,
            'period': f'{days} days'
        }
        
    except Exception as e:
        print(f"Error fetching heatmap data: {e}")
        return {
            'tag_name': tag_name,
            'dates': [],
            'hours': list(range(24)),
            'data': {},
            'period': f'{days} days'
        }