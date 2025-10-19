# Technical indicators removed - focusing on trend analysis
# This file is kept for reference but not used
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..db import q
from ..utils.query_optimizer import optimize_query_params


def _pick_view(window: str) -> str:
    """📊 적응적 해상도: 시간 범위에 따른 최적 뷰 선택
    
    정책:
    - 5분~1시간: 1분 해상도 (단기 변동성 중요)
    - 1~24시간: 10분 해상도 (중기 트렌드)
    - 1~7일: 1시간 해상도 (일간 패턴)
    - 7일 이상: 1일 해상도 (장기 추세)
    """
    wl = (window or "").lower()
    
    # 분 단위 체크
    if "min" in wl or "minute" in wl:
        return "public.tech_ind_1m_mv"
    
    # 시간 단위 체크 (1, 4, 24시간 구분)
    if "hour" in wl:
        # 1시간 이하는 1분 해상도
        if "1 " in wl or "one" in wl:
            return "public.tech_ind_1m_mv"
        # 4시간, 24시간은 10분 해상도
        else:
            return "public.tech_ind_10m_mv"
    
    # 일 단위 체크 (7일 기준으로 구분)
    if "day" in wl:
        # 7일 이하는 1시간 해상도
        if any(d in wl for d in ["1", "2", "3", "4", "5", "6", "7"]):
            return "public.tech_ind_1h_mv"
        # 7일 초과는 1일 해상도
        else:
            return "public.tech_ind_1d_mv"
    
    # 월 단위는 1일 해상도
    if "month" in wl:
        return "public.tech_ind_1d_mv"
    
    # 기본값: 1분 해상도
    return "public.tech_ind_1m_mv"


# tech_indicators() removed - only tech_indicators_1m() used in practice


async def tech_indicators_1m(window: str, tag_name: str | None) -> List[Dict[str, Any]]:
    """🚀 성능 최적화된 기술 지표 조회 (1분 해상도)"""
    # 동적 LIMIT 계산
    limit, hint = optimize_query_params(window, tag_name)
    
    sql = (
        "SELECT bucket, tag_name, avg, sma_10, sma_60, bb_top, bb_bot, slope_60 "
        "FROM public.tech_ind_1m_mv "
        "WHERE bucket >= now() - %s::interval "
        "  AND (%s::text IS NULL OR tag_name = %s) "
        "ORDER BY bucket "
        f"LIMIT {limit}"  # 동적 LIMIT 적용
    )
    params: Tuple[str, str | None, str | None] = (window, tag_name, tag_name)
    result = await q(sql, params)
    print(f"🔍 tech_indicators_1m: Query returned {len(result)} records for window='{window}', tag='{tag_name}', LIMIT={limit}")
    return result


async def tech_indicators_adaptive(window: str, tag_name: str | None) -> List[Dict[str, Any]]:
    """🧠 적응적 기술 지표 조회 - 현재 비활성화됨"""
    # Technical indicators 기능이 제거되어 빈 리스트 반환
    return []


