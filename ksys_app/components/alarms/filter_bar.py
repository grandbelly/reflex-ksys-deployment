"""
FilterBar Component for Alarm Dashboard
========================================

검색 및 필터링 UI 제공 - Light Mode
작성일: 2025-10-02
"""

import reflex as rx


def filter_bar(
    search_value: str | rx.Var = "",
    severity_filter: str | rx.Var = "all",
    status_filter: str | rx.Var = "all",
    on_search: rx.EventHandler = None,
    on_severity_change: rx.EventHandler = None,
    on_status_change: rx.EventHandler = None,
) -> rx.Component:
    """
    알람 필터바 컴포넌트 - 검색 + Severity + Status

    Args:
        search_value: 검색어
        severity_filter: Severity 필터값 ("all", "CRITICAL", "WARNING", "INFO")
        status_filter: Status 필터값 ("all", "UNACKNOWLEDGED", "ACKNOWLEDGED")
        on_search: 검색 이벤트 핸들러
        on_severity_change: Severity 변경 이벤트 핸들러
        on_status_change: Status 변경 이벤트 핸들러
    """

    # Build components conditionally based on event handlers
    search_input = rx.input(
        placeholder="Search by tag, message, or cause...",
        value=search_value,
        on_change=on_search,
        size="2",
        width="40%",
        bg="white",
    ) if on_search else rx.input(
        placeholder="Search by tag, message, or cause...",
        value=search_value,
        size="2",
        width="40%",
        bg="white",
    )

    severity_select = rx.select(
        ["all", "CRITICAL", "WARNING", "INFO"],
        value=severity_filter,
        on_change=on_severity_change,
        size="2",
        placeholder="All Severities",
    ) if on_severity_change else rx.select(
        ["all", "CRITICAL", "WARNING", "INFO"],
        value=severity_filter,
        size="2",
        placeholder="All Severities",
    )

    status_select = rx.select(
        ["all", "UNACKNOWLEDGED", "ACKNOWLEDGED"],
        value=status_filter,
        on_change=on_status_change,
        size="2",
        placeholder="All Status",
    ) if on_status_change else rx.select(
        ["all", "UNACKNOWLEDGED", "ACKNOWLEDGED"],
        value=status_filter,
        size="2",
        placeholder="All Status",
    )

    return rx.hstack(
        search_input,
        severity_select,
        status_select,
        width="100%",
        spacing="2",
    )


def live_indicator(is_live: bool | rx.Var = True, last_update: str | rx.Var = "Just now") -> rx.Component:
    """LIVE 인디케이터 - Light Mode"""
    return rx.flex(
        rx.box(
            width="8px",
            height="8px",
            border_radius="full",
            bg=rx.cond(is_live, "#10b981", "#9ca3af"),
            class_name=rx.cond(is_live, "animate-pulse", ""),
        ),
        rx.text("LIVE", size="2", weight="bold", color=rx.cond(is_live, "#10b981", "#9ca3af")),
        rx.text(f"Last update: {last_update}", size="1", color="#6b7280"),
        gap="2",
        align="center",
    )


def action_bar(shown_count: int | rx.Var, selected_count: int | rx.Var) -> rx.Component:
    """액션 바 - Light Mode"""
    return rx.flex(
        rx.text(
            f"{shown_count} alarms shown | {selected_count} selected",
            size="2",
            color="#6b7280",
        ),
        rx.spacer(),
        rx.flex(
            rx.button(
                "Acknowledge Selected",
                size="2",
                variant="solid",
                color_scheme="green",
                disabled=rx.cond(selected_count == 0, True, False),
            ),
            rx.button(
                "Clear Selected",
                size="2",
                variant="outline",
            ),
            gap="2",
        ),
        justify="between",
        align="center",
        padding="3",
        bg="#f9fafb",
        border_radius="md",
        width="100%",
    )
