"""
Query Optimization Utils - 쿼리 성능 최적화 유틸리티
"""
import re
import logging
from typing import Tuple, Optional
from datetime import timedelta


def parse_interval(window: str) -> timedelta:
    """간격 문자열을 timedelta로 파싱"""
    try:
        # 일반적인 패턴들 매칭
        if 'minute' in window.lower():
            match = re.search(r'(\d+)\s*minute', window.lower())
            if match:
                return timedelta(minutes=int(match.group(1)))
        elif 'hour' in window.lower():
            match = re.search(r'(\d+)\s*hour', window.lower())
            if match:
                return timedelta(hours=int(match.group(1)))
        elif 'day' in window.lower():
            match = re.search(r'(\d+)\s*day', window.lower())
            if match:
                return timedelta(days=int(match.group(1)))
        
        # 기본값: 1시간
        return timedelta(hours=1)
    except Exception:
        logging.warning(f"Failed to parse interval: {window}, using 1 hour default")
        return timedelta(hours=1)


def calculate_smart_limit(window: str, tag_name: Optional[str] = None) -> int:
    """
    시간 범위와 태그에 따른 지능형 LIMIT 계산
    
    🚀 성능 최적화 전략:
    - 짧은 범위: 더 많은 데이터 포인트 허용 (세밀한 분석)
    - 긴 범위: 데이터 포인트 제한 (메모리/성능 보호)
    - 특정 태그: 더 많은 데이터 허용
    - 전체 태그: 제한적 데이터 (다중 태그 부하 고려)
    """
    try:
        interval = parse_interval(window)
        total_minutes = int(interval.total_seconds() / 60)
        
        # 태그별 기본 승수
        tag_multiplier = 1.5 if tag_name else 1.0
        
        # 📊 시간대별 LIMIT 전략
        if total_minutes <= 60:  # 1시간 이하
            base_limit = 2000
        elif total_minutes <= 1440:  # 24시간 이하 (1일)
            base_limit = 5000  
        elif total_minutes <= 10080:  # 7일 이하 (1주)
            base_limit = 3000
        elif total_minutes <= 43200:  # 30일 이하 (1개월)
            base_limit = 1500
        else:  # 30일 초과
            base_limit = 1000
        
        # 최종 계산 및 범위 제한
        calculated_limit = int(base_limit * tag_multiplier)
        return min(max(calculated_limit, 500), 10000)  # 500 ~ 10000 범위
        
    except Exception as e:
        logging.error(f"Error calculating smart limit for window {window}: {e}")
        return 5000  # 안전한 기본값


def get_performance_hint(limit: int, window: str) -> str:
    """성능 힌트 메시지 생성"""
    if limit >= 8000:
        return f"⚡ 고성능 모드: {limit}개 데이터 포인트 (범위: {window})"
    elif limit >= 3000:
        return f"📊 표준 모드: {limit}개 데이터 포인트 (범위: {window})"
    else:
        return f"💾 절약 모드: {limit}개 데이터 포인트 (범위: {window})"


def optimize_query_params(window: str, tag_name: Optional[str] = None) -> Tuple[int, str]:
    """쿼리 매개변수 최적화"""
    limit = calculate_smart_limit(window, tag_name)
    hint = get_performance_hint(limit, window)
    
    # 개발 환경에서만 힌트 로그 출력
    import os
    if os.getenv('APP_ENV', 'development') == 'development':
        logging.info(hint)
    
    return limit, hint