"""
Stat Card Component for Alarm Dashboard
========================================

통계 정보를 시각적으로 표시하는 카드 컴포넌트
- 아이콘, 트렌드, 클릭 이벤트 지원
- 디자인 토큰 기반 일관된 스타일링

작성일: 2025-10-02
참고: docs/alarm/alarm-components.md
"""

import reflex as rx
from typing import Optional
from ...styles.design_tokens import (
    get_icon,
    TYPOGRAPHY,
    SPACING,
    COMPONENT_DEFAULTS,
)


def stat_card(
    title: str,
    value: int | str | rx.Var,
    icon: str,
    color: str = "gray",
    trend: Optional[str | rx.Var] = None,
    trend_direction: Optional[str] = None,
    subtitle: Optional[str | rx.Var] = None,
    on_click: Optional[rx.EventHandler] = None,
) -> rx.Component:
    """
    통계 카드 컴포넌트

    Args:
        title: 카드 제목 (예: "Total Alarms", "Critical")
        value: 표시할 값 (예: "7,878", State.critical_count)
        icon: Lucide 아이콘 이름 (예: "database", "alert-circle")
        color: 색상 테마 (예: "red", "orange", "blue", "gray")
        trend: 트렌드 정보 (예: "+5%", "-2%", "+120")
        trend_direction: 트렌드 방향 ("up" | "down" | None)
        subtitle: 부가 설명 (예: "Immediate action", "All alarms")
        on_click: 클릭 이벤트 핸들러

    Returns:
        rx.Component: StatCard 컴포넌트

    Examples:
        >>> # 기본 사용
        >>> stat_card(
        ...     title="Total Alarms",
        ...     value="7,878",
        ...     icon="database",
        ...     color="gray",
        ... )

        >>> # State와 연동 + 트렌드
        >>> stat_card(
        ...     title="Critical",
        ...     value=AlarmState.critical_count,
        ...     icon="alert-circle",
        ...     color="red",
        ...     trend="+5%",
        ...     trend_direction="up",
        ...     subtitle="Immediate action required",
        ... )

        >>> # 클릭 이벤트
        >>> stat_card(
        ...     title="Unacknowledged",
        ...     value=AlarmState.unacked_count,
        ...     icon="bell",
        ...     color="orange",
        ...     on_click=AlarmState.filter_by_unacked,
        ... )
    """

    # 트렌드 아이콘 및 색상
    trend_config = {
        "up": ("trending-up", "green"),
        "down": ("trending-down", "red"),
    }
    trend_icon, trend_color = trend_config.get(trend_direction, ("minus", "gray"))

    return rx.card(
        rx.vstack(
            # 상단: 아이콘 + 트렌드
            rx.flex(
                # 아이콘 박스
                rx.box(
                    rx.icon(
                        icon,
                        size=24,
                    ),
                    padding="3",
                    border_radius="lg",
                    bg=rx.color(color, 3),
                ),

                rx.spacer(),

                # 트렌드 (조건부 표시)
                rx.cond(
                    trend != None,
                    rx.flex(
                        rx.icon(
                            trend_icon,
                            size=14,
                        ),
                        rx.text(
                            trend,
                            size="1",
                            weight="medium",
                        ),
                        gap="1",
                        align="center",
                        color=rx.color(trend_color, 11),
                    ),
                    rx.fragment(),
                ),

                justify="between",
                align="start",
                width="100%",
            ),

            # 중앙: 값 (크고 굵게)
            rx.text(
                value,
                size=TYPOGRAPHY["stat_value"]["size"],
                weight=TYPOGRAPHY["stat_value"]["weight"],
                class_name="mt-3",
            ),

            # 하단: 타이틀 + 서브타이틀
            rx.vstack(
                rx.text(
                    title,
                    size=TYPOGRAPHY["stat_title"]["size"],
                    weight=TYPOGRAPHY["stat_title"]["weight"],
                    color="gray",
                    class_name="uppercase tracking-wide",
                ),
                rx.cond(
                    subtitle != None,
                    rx.text(
                        subtitle,
                        size="1",
                        color="gray",
                        class_name="opacity-70",
                    ),
                    rx.fragment(),
                ),
                spacing="1",
                align="start",
                width="100%",
            ),

            spacing="2",
            align="start",
            width="100%",
        ),
        size=COMPONENT_DEFAULTS["stat_card"]["size"],
        variant=COMPONENT_DEFAULTS["stat_card"]["variant"],
        class_name="hover:shadow-xl transition-all duration-300 hover:-translate-y-1 cursor-pointer",
        on_click=on_click,
    )


def stat_card_compact(
    title: str,
    value: int | str | rx.Var,
    color: str = "gray",
) -> rx.Component:
    """
    컴팩트 버전 StatCard (모바일용)

    Args:
        title: 카드 제목
        value: 표시할 값
        color: 색상 테마

    Returns:
        rx.Component: 컴팩트 StatCard

    Examples:
        >>> stat_card_compact("Critical", "7,343", "red")
    """
    return rx.box(
        rx.hstack(
            rx.text(
                value,
                size="4",
                weight="bold",
            ),
            rx.text(
                title,
                size="1",
                color="gray",
            ),
            spacing="2",
            align="center",
        ),
        padding="3",
        bg=rx.color(color, 2),
        border_radius="md",
    )


def stat_card_minimal(
    value: int | str | rx.Var,
    label: str,
) -> rx.Component:
    """
    미니멀 버전 StatCard (사이드바용)

    Args:
        value: 표시할 값
        label: 레이블

    Returns:
        rx.Component: 미니멀 StatCard

    Examples:
        >>> stat_card_minimal("503", "Warning")
    """
    return rx.vstack(
        rx.text(
            value,
            size="5",
            weight="bold",
        ),
        rx.text(
            label,
            size="1",
            color="gray",
        ),
        spacing="1",
        align="center",
    )
