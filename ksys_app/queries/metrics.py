from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional

from ..db import q


def _calculate_dynamic_limit(window: str) -> int:
    """Calculate appropriate limit based on time window to optimize query performance."""
    wl = (window or "").strip().lower()
    if "minute" in wl and ("1 " in wl or "5 " in wl):
        return 1440  # 1 day worth of minutes
    elif "hour" in wl and ("12" in wl or "24" in wl):
        return 2880  # 2 days worth of 10-minute buckets
    elif "day" in wl:
        if "7" in wl:
            return 1008  # 7 days worth of hours
        elif "30" in wl:
            return 720   # 30 days worth of hours
    return 10000  # Default maximum


def _auto_view(window: str) -> str:
    """단순 정책 매핑:
    - 분 단위(window에 'minute' 포함) → 1분 뷰
    - 시간 단위(window에 'hour' 포함)  → 10분 뷰
    - 일/월 단위(window에 'day'/'month' 포함) → 1시간 뷰(기본), 필요 시 1일 뷰 사용
    """
    wl = (window or "").strip().lower()
    if "minute" in wl:
        return "public.influx_agg_1m"
    if "hour" in wl:
        return "public.influx_agg_10m"
    if ("month" in wl) or ("months" in wl) or ("day" in wl):
        # 기본은 1시간 집계. 1일 집계는 resolution='1d'로 강제 지정 시 사용
        return "public.influx_agg_1h"
    return "public.influx_agg_1h"


async def timeseries(
    window: str,
    tag_name: Optional[str],
    resolution: Optional[str] = None,
    start_iso: Optional[str] = None,
    end_iso: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch timeseries with optional resolution override ('1m'|'10m'|'1h'|'1d').

    Returns all standard columns: n, avg, sum, min, max, last, first, diff.
    Ordered by time ascending for stable charting.
    """
    import logging
    logger = logging.getLogger(__name__)

    if resolution in {"1m", "1min", "1minute", "1 minute"}:
        view = "public.influx_agg_1m"
    elif resolution in {"10m", "10min", "10 minutes", "10 minute"}:
        view = "public.influx_agg_10m"
    elif resolution in {"1h", "1hour", "1 hour"}:
        view = "public.influx_agg_1h"
    elif resolution in {"1d", "1day", "1 day"}:
        view = "public.influx_agg_1d"
    else:
        view = _auto_view(window)

    logger.info(f"🔍 timeseries query: window={window}, tag_name={tag_name}, resolution={resolution}, view={view}")

    if start_iso and end_iso:
        limit = _calculate_dynamic_limit(window or "7 days")
        sql = f"""
            SELECT bucket, tag_name, n, avg, sum, min, max, last, first, diff
            FROM {view}
            WHERE bucket BETWEEN %s::timestamptz AND %s::timestamptz
              AND (%s::text IS NULL OR tag_name = %s)
            ORDER BY bucket ASC
            LIMIT {limit}
        """
        params_se: Tuple[Optional[str], Optional[str], Optional[str], Optional[str]] = (
            start_iso,
            end_iso,
            tag_name,
            tag_name,
        )
        return await q(sql, params_se)

    # 집계 뷰별로 적절한 개수와 시간 범위 설정
    if view == "public.influx_agg_1m":
        # 1분 집계: 최근 N개 데이터 (시간 기반이 아닌 개수 기반)
        if window in ["60 min", "60 minutes", "1 hour"]:
            record_limit = 60  # 1시간 = 60개
        elif window in ["24 hour", "24 hours", "1 day"]:
            record_limit = 1440  # 24시간 = 1440개 (너무 많으므로 제한)
            record_limit = min(record_limit, 240)  # 최대 4시간치만
        elif window in ["7 days", "7 day"]:
            record_limit = 420  # 7일은 너무 많으므로 7시간치만
        elif window in ["30 days", "30 day", "1 month"]:
            record_limit = 720  # 30일은 너무 많으므로 12시간치만
        else:
            record_limit = 60  # 기본값

        sql = f"""
            SELECT * FROM (
                SELECT bucket, tag_name, n, avg, sum, min, max, last, first, diff
                FROM {view}
                WHERE (%s::text IS NULL OR tag_name = %s)
                ORDER BY bucket DESC
                LIMIT {record_limit}
            ) sub
            ORDER BY bucket ASC
        """
        params: Tuple[Optional[str], Optional[str]] = (tag_name, tag_name)

    elif view == "public.influx_agg_10m":
        # 10분 집계: 적절한 시간 범위
        limit = 10000  # 기본값 설정
        if window in ["60 min", "60 minutes", "1 hour"]:
            time_window = "1 hour"  # 6개
        elif window in ["24 hour", "24 hours", "1 day"]:
            time_window = "24 hours"  # 144개
        elif window in ["7 days", "7 day"]:
            time_window = "7 days"  # 1008개
        elif window in ["30 days", "30 day", "1 month"]:
            time_window = "30 days"  # 4320개 (제한 필요)
            limit = 720  # 최대 5일치만
        else:
            time_window = window

        sql = f"""
            SELECT bucket, tag_name, n, avg, sum, min, max, last, first, diff
            FROM {view}
            WHERE bucket >= now() - %s::interval
              AND (%s::text IS NULL OR tag_name = %s)
            ORDER BY bucket ASC
            LIMIT {limit}
        """
        params: Tuple[str, Optional[str], Optional[str]] = (time_window, tag_name, tag_name)

    elif view in ["public.influx_agg_1h", "public.influx_agg_1d"]:
        # 1시간/1일 집계: 기존 로직 유지
        limit = _calculate_dynamic_limit(window)  # limit 변수 정의
        sql = f"""
            SELECT bucket, tag_name, n, avg, sum, min, max, last, first, diff
            FROM {view}
            WHERE bucket >= now() - %s::interval
              AND (%s::text IS NULL OR tag_name = %s)
            ORDER BY bucket ASC
            LIMIT {limit}
        """
        params: Tuple[str, Optional[str], Optional[str]] = (window, tag_name, tag_name)
    else:
        # 기본 로직
        limit = _calculate_dynamic_limit(window)  # limit 변수 정의
        sql = f"""
            SELECT bucket, tag_name, n, avg, sum, min, max, last, first, diff
            FROM {view}
            WHERE bucket >= now() - %s::interval
              AND (%s::text IS NULL OR tag_name = %s)
            ORDER BY bucket ASC
            LIMIT {limit}
        """
        params: Tuple[str, Optional[str], Optional[str]] = (window, tag_name, tag_name)
    # limit 변수가 정의되지 않은 경우 처리
    if 'limit' not in locals():
        limit = record_limit if 'record_limit' in locals() else 'N/A'
    logger.info(f"📊 SQL: {sql[:100]}... LIMIT={limit}, params={params}")
    result = await q(sql, params)
    logger.info(f"✅ timeseries returned {len(result)} rows")
    return result


