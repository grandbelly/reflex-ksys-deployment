from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
from ksys_app.utils.logger import get_logger, log_function

from ..db import q

# Initialize logger for this module
logger = get_logger(__name__)


@log_function
async def realtime_data(
    tag_name: str,
    window_seconds: int = 60,
    interval_seconds: int = 10
) -> List[Dict[str, Any]]:
    """influx_hist 테이블에서 실시간 원시 데이터를 5초 간격으로 집계
    
    Args:
        tag_name: 태그명
        window_seconds: 조회할 시간 범위 (초)
        interval_seconds: 데이터 집계 간격 (초)
    
    Returns:
        10초 간격으로 집계된 실시간 시계열 데이터
    """
    try:
        # influx_hist에서 최근 window_seconds 동안의 원시 데이터를 interval_seconds 간격으로 집계
        realtime_sql = """
            SELECT 
                time_bucket(%s::interval, ts) AS bucket,
                tag_name,
                AVG(value) AS value,
                COUNT(*) AS count
            FROM public.influx_hist 
            WHERE tag_name = %s
              AND ts >= NOW() - %s::interval
              AND quality = 0  -- 정상 데이터만
            GROUP BY bucket, tag_name
            ORDER BY bucket DESC
            LIMIT %s
        """
        
        interval_str = f"{interval_seconds} seconds"
        window_str = f"{window_seconds} seconds"
        max_points = window_seconds // interval_seconds
        
        results = await q(realtime_sql, (interval_str, tag_name, window_str, max_points))
        
        # 결과를 시간 순으로 정렬하고 포맷팅
        formatted_results = []
        for row in reversed(results):  # DESC를 ASC로 변환
            bucket_time = row['bucket']
            formatted_results.append({
                'bucket': bucket_time.strftime('%H:%M:%S'),
                'tag_name': row['tag_name'],
                'value': round(float(row['value']), 1),
                'count': int(row['count']),
                'timestamp': bucket_time.isoformat()
            })
        
        return formatted_results
        
    except Exception as e:
        # 🚨 보안 수정: DB 오류 시 시뮬레이션 데이터 반환하지 않음
        import logging
        logging.error(f"실시간 데이터 조회 실패 - tag_name: {tag_name}, 오류: {e}", exc_info=True)
        # 빈 리스트 반환 - 사용자에게 데이터 없음을 명확히 표시
        return []


@log_function
async def get_sliding_window_data(tag_name: str) -> List[Dict[str, Any]]:
    """슬라이딩 윈도우 방식으로 최근 1분간 5초 간격 데이터 12개 반환"""
    return await realtime_data(tag_name, window_seconds=60, interval_seconds=10)




async def get_all_tags_latest_realtime() -> List[Dict[str, Any]]:
    """모든 태그의 최신 실시간 데이터를 influx_latest에서 가져오기

    Returns:
        각 태그별 최신 값 데이터 리스트
    """
    try:
        # influx_latest에서 각 태그의 최신값 가져오기 (초기 로드와 동일한 소스)
        realtime_sql = """
            SELECT
                tag_name,
                value,
                ts
            FROM public.influx_latest
            ORDER BY tag_name
        """

        results = await q(realtime_sql, ())

        # 결과를 포맷팅
        formatted_results = []
        for row in results:
            formatted_results.append({
                'tag_name': row['tag_name'],
                'value': round(float(row['value']), 1) if row['value'] is not None else None,
                'ts': row['ts'],
                # ISO format timestamp for consistency
                'timestamp': row['ts'].isoformat() if row['ts'] else None
            })

        return formatted_results

    except Exception as e:
        # 🔧 오류 처리 개선: 적절한 로깅으로 교체
        import logging
        logging.error(f"모든 태그 실시간 데이터 조회 실패: {e}", exc_info=True)
        # 에러 발생시 빈 리스트 반환
        return []


async def get_all_tags_latest_hist() -> List[Dict[str, Any]]:
    """모든 태그의 5초 간격 최신 실시간 데이터 가져오기 (influx_hist 테이블 사용)

    Returns:
        각 태그별 최신 5초 간격 데이터 리스트
    """
    try:
        # influx_hist에서 각 태그의 최신 5초 간격 데이터 가져오기
        realtime_sql = """
            SELECT DISTINCT ON (tag_name)
                tag_name,
                value,
                ts,
                quality
            FROM public.influx_hist
            WHERE ts >= NOW() - INTERVAL '60 seconds'
              AND quality = 0
            ORDER BY tag_name, ts DESC
            LIMIT 50
        """

        results = await q(realtime_sql, ())

        # 결과를 포맷팅
        formatted_results = []
        for row in results:
            formatted_results.append({
                'tag_name': row['tag_name'],
                'value': round(float(row['value']), 1),
                'ts': row['ts'],
                'quality': int(row['quality']),
                # ISO format timestamp for consistency
                'timestamp': row['ts'].isoformat() if row['ts'] else None
            })

        return formatted_results

    except Exception as e:
        # 🔧 오류 처리 개선: 적절한 로깅으로 교체
        import logging
        logging.error(f"모든 태그 히스토리 데이터 조회 실패: {e}", exc_info=True)
        # 에러 발생시 빈 리스트 반환
        return []