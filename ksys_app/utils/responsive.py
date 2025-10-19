"""반응형 레이아웃 유틸리티"""
import reflex as rx
from typing import Dict, Any


def responsive_grid_columns(**kwargs) -> Dict[str, str]:
    """
    반응형 그리드 컬럼 설정

    Usage:
        rx.grid(
            ...,
            columns=responsive_grid_columns(mobile=1, tablet=2, desktop=3)
        )
    """
    return rx.breakpoints(
        initial=str(kwargs.get("mobile", 1)),
        xs=str(kwargs.get("mobile", 1)),
        sm=str(kwargs.get("tablet", 2)),
        md=str(kwargs.get("tablet", 2)),
        lg=str(kwargs.get("desktop", 3)),
        xl=str(kwargs.get("wide", kwargs.get("desktop", 3)))
    )


def responsive_container(**style_overrides) -> Dict[str, Any]:
    """
    반응형 컨테이너 스타일

    기본값:
    - width: 100%
    - max_width: 100%
    - padding: 반응형 (mobile: 2, tablet: 3, desktop: 4)
    """
    base_style = {
        "width": "100%",
        "max_width": "100%",
    }

    # 반응형 패딩
    if "padding" not in style_overrides:
        base_style["class_name"] = "p-2 sm:p-3 md:p-4 lg:p-6"

    base_style.update(style_overrides)
    return base_style


def responsive_card(**style_overrides) -> Dict[str, Any]:
    """
    반응형 카드 스타일

    기본값:
    - width: 100%
    - min_width: 0 (flex-shrink 허용)
    - padding: 반응형
    """
    base_style = {
        "width": "100%",
        "min_width": "0",
        "class_name": "p-3 sm:p-4 md:p-5"
    }
    base_style.update(style_overrides)
    return base_style


def responsive_spacing(mobile: str = "2", tablet: str = "3", desktop: str = "4") -> str:
    """
    반응형 spacing 클래스 생성

    Returns:
        Tailwind spacing 클래스 문자열
    """
    return f"space-y-{mobile} sm:space-y-{tablet} md:space-y-{desktop}"


def responsive_text_size(mobile: str = "2", tablet: str = "3", desktop: str = "4") -> str:
    """
    반응형 텍스트 크기

    Returns:
        size prop 값 (Reflex는 breakpoints를 직접 지원하지 않으므로 기본값 반환)
    """
    # Reflex의 size prop은 breakpoints를 지원하지 않으므로 desktop 사이즈 사용
    return desktop


def responsive_chart_height(mobile: int = 250, tablet: int = 300, desktop: int = 400) -> int:
    """
    반응형 차트 높이

    Note: Recharts는 고정 높이만 지원하므로 데스크톱 기준값 사용
    향후 컨테이너 쿼리나 JavaScript로 개선 가능
    """
    return desktop


# Breakpoint 상수
BREAKPOINTS = {
    "mobile": "0px",      # 0-639px
    "tablet": "640px",    # 640-767px
    "md": "768px",        # 768-1023px
    "desktop": "1024px",  # 1024-1279px
    "wide": "1280px",     # 1280px+
}


# 반응형 그리드 프리셋
GRID_PRESETS = {
    "cards_1_2_3": responsive_grid_columns(mobile=1, tablet=2, desktop=3),
    "cards_1_2_4": responsive_grid_columns(mobile=1, tablet=2, desktop=4),
    "cards_1_3_3": responsive_grid_columns(mobile=1, tablet=3, desktop=3),
    "filters_1_2_3": responsive_grid_columns(mobile=1, tablet=2, desktop=3),
    "kpi_2_3_4": responsive_grid_columns(mobile=2, tablet=3, desktop=4),
}
