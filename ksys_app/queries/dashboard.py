"""
Dashboard unified query module - Single view data fetching
모든 대시보드 데이터를 dashboard_view에서 가져오는 통합 쿼리 모듈
"""

from typing import List, Dict, Any, Optional
import json
from ..db import q

async def get_dashboard_data(tag_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    dashboard_view에서 대시보드 데이터 가져오기

    Args:
        tag_names: 특정 태그만 필터링 (None이면 전체)

    Returns:
        대시보드 표시용 데이터 리스트
    """

    # WHERE 절 구성
    where_clause = ""
    params = []
    if tag_names:
        placeholders = ",".join([f"${i+1}" for i in range(len(tag_names))])
        where_clause = f"WHERE tag_name IN ({placeholders})"
        params = tag_names

    # 통합 쿼리 - dashboard_view에서 모든 데이터 가져오기
    dashboard_sql = f"""
    SELECT
        tag_name,

        -- 현재값 정보
        current_value,
        value_display,
        last_update_formatted,
        last_update_time,

        -- 변화율 정보 (뷰에서 직접 제공)
        delta_pct,
        delta_s,
        delta_icon,
        delta_color,

        -- 게이지 및 상태
        gauge_pct,
        status_level,
        status_color,

        -- QC 범위
        range_label,
        min_val,
        max_val,
        warn_min,
        warn_max,
        crit_min,
        crit_max,

        -- 미니 차트 데이터 (JSON)
        mini_chart_data

    FROM dashboard_view
    {where_clause}
    ORDER BY tag_name
    """

    # 쿼리 실행
    if params:
        rows = await q(dashboard_sql, tuple(params))
    else:
        rows = await q(dashboard_sql, ())

    # 결과 변환
    results = []
    for row in rows:
        # 미니 차트 데이터 파싱
        chart_data = []
        if row['mini_chart_data']:
            try:
                chart_data = json.loads(row['mini_chart_data']) if isinstance(row['mini_chart_data'], str) else row['mini_chart_data']
            except:
                chart_data = []

        results.append({
            'tag_name': row['tag_name'],

            # 값 정보
            'value': row['current_value'],
            'value_s': str(row['value_display']),
            'ts_s': row['last_update_time'],
            'last_update': row['last_update_formatted'],

            # 변화율 (뷰에서 직접 제공)
            'delta_pct': float(row['delta_pct']) if row['delta_pct'] else 0.0,
            'delta_s': row['delta_s'],
            'delta_icon': row['delta_icon'],  # 'trending-up', 'trending-down', 'minus'
            'delta_color': row['delta_color'],  # 'green', 'red', 'gray'

            # 상태 및 게이지
            'status_level': row['status_level'],
            'status_color': row['status_color'],
            'gauge_pct': float(row['gauge_pct']) if row['gauge_pct'] else 50.0,

            # QC 정보
            'range_label': row['range_label'],
            'qc_min': float(row['min_val']) if row['min_val'] else None,
            'qc_max': float(row['max_val']) if row['max_val'] else None,
            'warn_min': float(row['warn_min']) if row['warn_min'] else None,
            'warn_max': float(row['warn_max']) if row['warn_max'] else None,
            'crit_min': float(row['crit_min']) if row['crit_min'] else None,
            'crit_max': float(row['crit_max']) if row['crit_max'] else None,

            # 차트 데이터
            'chart_data': chart_data
        })

    return results


async def get_single_tag_dashboard(tag_name: str) -> Optional[Dict[str, Any]]:
    """
    단일 태그의 대시보드 데이터 가져오기

    Args:
        tag_name: 태그 이름

    Returns:
        대시보드 데이터 또는 None
    """
    results = await get_dashboard_data([tag_name])
    return results[0] if results else None


async def get_dashboard_stats() -> Dict[str, Any]:
    """
    대시보드 전체 통계 가져오기

    Returns:
        전체 통계 정보
    """
    stats_sql = """
    SELECT
        COUNT(*) as total_tags,
        COUNT(CASE WHEN status_level = 0 THEN 1 END) as normal_count,
        COUNT(CASE WHEN status_level = 1 THEN 1 END) as warning_count,
        COUNT(CASE WHEN status_level = 2 THEN 1 END) as critical_count,
        AVG(gauge_pct) as avg_gauge_pct,
        AVG(delta_pct) as avg_delta_pct
    FROM dashboard_view
    """

    result = await q(stats_sql, ())
    if result:
        row = result[0]
        return {
            'total_tags': row['total_tags'],
            'normal_count': row['normal_count'],
            'warning_count': row['warning_count'],
            'critical_count': row['critical_count'],
            'avg_gauge_pct': float(row['avg_gauge_pct']) if row['avg_gauge_pct'] else 0.0,
            'avg_delta_pct': float(row['avg_delta_pct']) if row['avg_delta_pct'] else 0.0
        }

    return {
        'total_tags': 0,
        'normal_count': 0,
        'warning_count': 0,
        'critical_count': 0,
        'avg_gauge_pct': 0.0,
        'avg_delta_pct': 0.0
    }