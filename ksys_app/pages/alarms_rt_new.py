"""
실시간 알람 대시보드 - 개선 버전
Light Mode 디자인, 캡처 화면 기준
작성일: 2025-10-02
"""

import reflex as rx
from ..states.alarm_rt_state import AlarmRTState as A
from ..components.layout import shell
from ..components.alarms import (
    stat_card,
    filter_bar,
    live_indicator,
    action_bar,
    alarm_item,
    pagination,
)


def alarms_rt_page() -> rx.Component:
    """실시간 알람 대시보드 - Light Mode"""
    return shell(
        rx.vstack(
            # Header with LIVE indicator and refresh
            rx.flex(
                rx.heading(
                    "🔴 Alarm Dashboard",
                    size="5",
                    weight="bold",
                    color="#111827",
                ),
                rx.spacer(),
                rx.flex(
                    live_indicator(
                        is_live=True,
                        last_update=A.last_update,
                    ),
                    rx.button(
                        rx.icon("refresh-cw", size=16),
                        "Refresh",
                        size="2",
                        variant="soft",
                        color_scheme="blue",
                        on_click=A.refresh_realtime,
                    ),
                    gap="3",
                    align="center",
                ),
                justify="between",
                align="center",
                width="100%",
            ),

            # Statistics Cards (6 cards in grid)
            rx.grid(
                stat_card(
                    title="Total",
                    value=A.total_alarm_count,
                    icon="database",
                    color="gray",
                ),
                stat_card(
                    title="Critical",
                    value=A.critical_count,
                    icon="alert-circle",
                    color="red",
                ),
                stat_card(
                    title="Warning",
                    value=A.warning_count,
                    icon="alert-triangle",
                    color="orange",
                ),
                stat_card(
                    title="Info",
                    value=A.normal_count,
                    icon="info",
                    color="blue",
                ),
                stat_card(
                    title="Unacked",
                    value=A.unacknowledged_count,
                    icon="bell",
                    color="orange",
                ),
                stat_card(
                    title="Acked",
                    value=A.acknowledged_count,
                    icon="circle-check",
                    color="green",
                ),
                columns=rx.breakpoints(
                    initial="2",
                    xs="2",
                    sm="3",
                    md="6",
                    lg="6",
                ),
                gap="4",
                width="100%",
            ),

            # Filter Bar
            filter_bar(
                search_value="",
                severity_filter="all",
                status_filter="all",
            ),

            # Action Bar
            action_bar(
                shown_count=A.total_alarm_count,
                selected_count=0,
            ),

            # Alarm List
            rx.vstack(
                rx.cond(
                    A.realtime_alarms,
                    rx.vstack(
                        rx.foreach(
                            A.realtime_alarms,
                            alarm_item,
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    # No data state
                    rx.center(
                        rx.vstack(
                            rx.icon("inbox", size=48, color="#9ca3af"),
                            rx.text(
                                "알람이 없습니다",
                                size="4",
                                weight="bold",
                                color="#6b7280",
                            ),
                            rx.text(
                                "필터를 조정하거나 새로고침하세요",
                                size="2",
                                color="#9ca3af",
                            ),
                            spacing="3",
                        ),
                        padding="12",
                    ),
                ),
                width="100%",
            ),

            # Pagination (simple version)
            rx.flex(
                rx.text(
                    f"Showing {A.total_alarm_count} alarms",
                    size="2",
                    color="#6b7280",
                ),
                rx.button(
                    "Next",
                    size="2",
                    variant="soft",
                    color_scheme="gray",
                ),
                justify="between",
                align="center",
                padding="3",
                bg="#f9fafb",
                border_radius="md",
                width="100%",
            ),

            spacing="4",
            padding="4",
            width="100%",
            class_name="bg-white min-h-screen",
        ),
        active_route="/alarms_rt_new",
        on_mount=A.on_load,
    )