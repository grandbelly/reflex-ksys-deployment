"""
Alarm Dashboard Design Tokens
================================

디자인 시스템의 색상, 타이포그래피, 간격 등을 정의합니다.
모든 알람 관련 컴포넌트는 이 토큰을 사용하여 일관성을 유지합니다.

작성일: 2025-10-02
참고: docs/alarm/alarm-dashboard-specs.md
"""

from typing import Dict, Tuple, Literal

# ============================================
# Severity Colors (알람 심각도별 색상)
# ============================================

SeverityType = Literal["CRITICAL", "WARNING", "INFO"]

SEVERITY_COLORS: Dict[SeverityType, Dict[str, str]] = {
    "CRITICAL": {
        "color": "red",           # Reflex color scheme
        "variant": "solid",       # Badge variant
        "icon": "alert-circle",   # Lucide icon name
    },
    "WARNING": {
        "color": "orange",
        "variant": "solid",
        "icon": "alert-triangle",
    },
    "INFO": {
        "color": "blue",
        "variant": "soft",
        "icon": "info",
    },
}

# ============================================
# Status Colors (알람 상태별 색상)
# ============================================

StatusType = Literal["ACTIVE", "UNACKNOWLEDGED", "ACKNOWLEDGED", "RESOLVED"]

STATUS_COLORS: Dict[StatusType, Tuple[str, str]] = {
    "ACTIVE": ("green", "soft"),
    "UNACKNOWLEDGED": ("gray", "outline"),
    "ACKNOWLEDGED": ("blue", "soft"),
    "RESOLVED": ("gray", "ghost"),
}

# ============================================
# Typography (타이포그래피)
# ============================================

TYPOGRAPHY = {
    # StatCard 타이포그래피
    "stat_title": {
        "size": "1",
        "weight": "medium",
    },
    "stat_value": {
        "size": "6",
        "weight": "bold",
    },
    "stat_subtitle": {
        "size": "1",
        "weight": "normal",
    },

    # AlarmItem 타이포그래피
    "alarm_message": {
        "size": "2",
        "weight": "medium",
    },
    "alarm_sensor": {
        "size": "1",
        "weight": "medium",
    },
    "alarm_metadata": {
        "size": "1",
        "weight": "normal",
    },

    # 공통
    "timestamp": {
        "size": "1",
        "weight": "normal",
    },
}

# ============================================
# Icons (아이콘 매핑)
# ============================================

ICONS = {
    # Statistics
    "total": "database",
    "critical": "alert-circle",
    "warning": "alert-triangle",
    "info": "info",
    "unacked": "bell",
    "acked": "circle-check",

    # Actions
    "acknowledge": "check",
    "details": "eye",
    "filter": "filter",
    "search": "search",
    "refresh": "refresh-cw",
    "close": "x",

    # Status
    "active": "activity",
    "resolved": "circle-check-big",
    "pending": "clock",

    # Navigation
    "prev": "chevron-left",
    "next": "chevron-right",
    "first": "chevrons-left",
    "last": "chevrons-right",

    # Location
    "location": "map-pin",
    "time": "clock",
}

# ============================================
# Spacing (간격)
# ============================================

SPACING = {
    "card_padding": "4",        # StatCard 내부 패딩
    "item_padding": "4",        # AlarmItem 내부 패딩
    "section_gap": "6",         # 섹션 간 간격
    "component_gap": "3",       # 컴포넌트 간 간격
    "grid_gap": "4",            # 그리드 간격
}

# ============================================
# Sizes (크기)
# ============================================

SIZES = {
    "icon_sm": 16,
    "icon_md": 20,
    "icon_lg": 24,
    "icon_xl": 28,

    "badge_sm": "1",
    "badge_md": "2",

    "button_sm": "1",
    "button_md": "2",
    "button_lg": "3",
}

# ============================================
# Component Defaults (컴포넌트 기본값)
# ============================================

COMPONENT_DEFAULTS = {
    "stat_card": {
        "size": "3",
        "variant": "surface",
    },
    "alarm_item": {
        "border_radius": "lg",
        "padding": SPACING["item_padding"],
    },
    "badge": {
        "size": "2",
    },
    "button": {
        "size": "2",
    },
}

# ============================================
# Helper Functions (헬퍼 함수)
# ============================================

def get_severity_color(severity: str) -> Dict[str, str]:
    """
    Severity에 해당하는 색상 정보 반환

    Args:
        severity: "CRITICAL", "WARNING", "INFO" (대소문자 무관)

    Returns:
        {"color": "red", "variant": "solid", "icon": "alert-circle"}

    Examples:
        >>> get_severity_color("critical")
        {"color": "red", "variant": "solid", "icon": "alert-circle"}
    """
    severity_upper = severity.upper()
    if severity_upper in SEVERITY_COLORS:
        return SEVERITY_COLORS[severity_upper]
    # 기본값 (알 수 없는 severity)
    return {"color": "gray", "variant": "soft", "icon": "help-circle"}


def get_status_color(status: str) -> Tuple[str, str]:
    """
    Status에 해당하는 색상 정보 반환

    Args:
        status: "ACTIVE", "UNACKNOWLEDGED", "ACKNOWLEDGED", "RESOLVED"

    Returns:
        (color: str, variant: str)

    Examples:
        >>> get_status_color("active")
        ("green", "soft")
    """
    status_upper = status.upper()
    if status_upper in STATUS_COLORS:
        return STATUS_COLORS[status_upper]
    # 기본값
    return ("gray", "soft")


def get_icon(icon_key: str) -> str:
    """
    아이콘 키에 해당하는 Lucide 아이콘 이름 반환

    Args:
        icon_key: "total", "critical", "acknowledge", etc.

    Returns:
        Lucide icon name

    Examples:
        >>> get_icon("total")
        "database"
        >>> get_icon("acknowledge")
        "check"
    """
    return ICONS.get(icon_key, "circle")


# ============================================
# Animation Classes (애니메이션)
# ============================================

ANIMATIONS = {
    "hover_scale": "hover:scale-105 transition-transform duration-200",
    "hover_shadow": "hover:shadow-xl transition-shadow duration-300",
    "hover_lift": "hover:-translate-y-1 transition-all duration-300",
    "fade_in": "animate-fade-in",
    "slide_in": "animate-slide-in-from-bottom",
}

# ============================================
# Responsive Breakpoints (반응형)
# ============================================

BREAKPOINTS = {
    "mobile": "sm",      # < 640px
    "tablet": "md",      # 640px - 1024px
    "desktop": "lg",     # > 1024px
}

GRID_COLUMNS = {
    "stats_mobile": "1",
    "stats_tablet": "3",
    "stats_desktop": "6",
}
