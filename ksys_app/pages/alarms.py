"""
Alarms Page - Unified rule-based alarm monitoring
- Clean, simple UI
- RULE_BASE scenario alarms
- Uses service pattern
"""
import reflex as rx
from typing import Dict
from ..states.alarms import AlarmsState
from ..states.dashboard_realtime import DashboardRealtimeState
from ..components.layout import shell
from ..components.cards.stat_card import stat_card
from ..components.alarms.filter_bar import filter_bar
from ..components.alarms.pagination import pagination
from ..styles.design_tokens import get_icon


def isa_level_badge(alarm: Dict) -> rx.Component:
    """
    ISA-18.2 compliant alarm level badge
    Shows: Priority + ISA Name (e.g., "P4: Emergency", "P2: Caution")
    """
    # Get ISA fields from alarm dict
    isa_priority = alarm.get("isa_priority", 0)
    isa_display = alarm.get("isa_display", alarm.get("level_name", "Unknown"))
    isa_color = alarm.get("isa_color", "gray")

    # Format: "P4: Emergency"
    label = f"P{isa_priority}: {isa_display}"

    return rx.badge(
        label,
        color_scheme=isa_color,
        variant="solid",
        size="1",
    )

def level_badge(level: int, level_name: str) -> rx.Component:
    """Legacy badge for backward compatibility"""
    color_map = {
        5: "red",     # CRITICAL
        4: "orange",  # ERROR
        3: "yellow",  # WARNING
        2: "blue",    # INFO
        1: "gray",    # CAUTION
    }

    color = color_map.get(level, "gray")

    return rx.badge(
        level_name,
        color_scheme=color,
        variant="solid",
        size="1",
    )


def stat_tile(title: str, value: rx.Var, color: str = "blue") -> rx.Component:
    """
    Statistics tile - DEPRECATED, use stat_card instead
    This is kept for backward compatibility only
    """
    return rx.box(
        rx.vstack(
            rx.text(title, size="2", color="#6b7280"),  # gray-500
            rx.text(value, size="6", weight="bold", color="#111827"),  # black
            spacing="1",
            align="center",
        ),
        padding="4",
        border_radius="lg",
        bg="white",  # KSYS: Always white background
        border="1px solid #e5e7eb",  # gray-200
        width="100%",
    )


def alarm_card(alarm: Dict) -> rx.Component:
    """
    Alarm card component - Light Mode

    KSYS Design: Always white background (#FFFFFF), black text (#111827)
    """
    return rx.box(
        rx.vstack(
            # Header: Level badge + Time
            rx.flex(
                level_badge(alarm["level"], alarm["level_name"]),
                rx.spacer(),
                rx.text(
                    alarm["triggered_at_short"],
                    size="2",
                    color="#6b7280"  # gray-500 for timestamps
                ),
                justify="between",
                align="center",
                width="100%",
            ),

            # Message
            rx.text(
                alarm["message"],
                size="3",
                weight="medium",
                color="#111827",  # KSYS: Always black text
            ),

            # Sensor info and action
            rx.flex(
                rx.hstack(
                    rx.badge(alarm["tag_name"], variant="soft", color_scheme="blue"),
                    rx.text(
                        f"{alarm['value']}{alarm['unit']}",
                        size="2",
                        color="#6b7280"
                    ),
                    spacing="2",
                ),
                rx.spacer(),
                rx.cond(
                    alarm["acknowledged"],
                    rx.badge("✓ Acknowledged", variant="soft", color_scheme="green"),
                    rx.button(
                        "Acknowledge",
                        size="2",
                        variant="soft",
                        color_scheme="blue",
                        on_click=lambda: AlarmsState.acknowledge_alarm(alarm["event_id"]),
                    ),
                ),
                justify="between",
                align="center",
                width="100%",
            ),

            spacing="3",
            align="start",
            width="100%",
        ),
        padding="4",
        bg="white",  # KSYS: Always white background
        border="1px solid #e5e7eb",  # gray-200
        border_radius="lg",
        width="100%",
        _hover={"border_color": "#3b82f6"},  # blue-500 on hover
        class_name="transition-all duration-200",
    )


def active_alarms_view() -> rx.Component:
    """Active Alarms view - Real-time alarm monitoring table from Dashboard"""
    def table_row(sensor: Dict) -> rx.Component:
        return rx.table.row(
            rx.table.cell(rx.text(sensor["tag_name"], size="2", weight="medium", color="#111827"), width="80px"),
            rx.table.cell(rx.badge(rx.cond(sensor["status"] == 0, "NORMAL", rx.cond(sensor["status"] == 1, "WARNING", "CRITICAL")),
                color_scheme=rx.cond(sensor["status"] == 0, "green", rx.cond(sensor["status"] == 1, "amber", "red")), variant="soft", size="1"), width="100px"),
            rx.table.cell(rx.text(sensor["value_str"], size="2", weight="medium", color="#111827"), width="100px"),
            rx.table.cell(rx.text(sensor["range_str"], size="2", color="#6b7280"), width="140px"),
            rx.table.cell(rx.text(sensor["deviation_str"], size="2", color=rx.cond(sensor["status"] == 2, "#ef4444", rx.cond(sensor["status"] == 1, "#f59e0b", "#6b7280")), weight="medium"), width="100px"),
            rx.table.cell(rx.hstack(rx.box(width=sensor["risk_pct_str"], height="16px", bg=rx.cond(sensor["status"] == 2, "#ef4444", rx.cond(sensor["status"] == 1, "#f59e0b", "#10b981")), border_radius="2px"),
                rx.text(sensor["risk_pct_str"], size="2", weight="medium", color="#111827"), spacing="2", align="center"), width="150px"),
            rx.table.cell(rx.text(sensor["timestamp"], size="2", color="#6b7280", weight="regular"), width="140px"),
            rx.table.cell(rx.button(rx.cond(sensor["status"] == 0, "확인", "조치"), size="1", variant="soft", color_scheme=rx.cond(sensor["status"] == 0, "green", "red")), width="100px"),
            bg=rx.cond(sensor["status"] == 2, "rgba(239, 68, 68, 0.1)", rx.cond(sensor["status"] == 1, "rgba(245, 158, 11, 0.1)", "white")),
            border_left=rx.cond(sensor["status"] == 2, "4px solid #ef4444", rx.cond(sensor["status"] == 1, "4px solid #f59e0b", "4px solid transparent")),
            _hover={"bg": "rgba(59, 130, 246, 0.05)", "cursor": "pointer"}
        )
    return rx.vstack(
        rx.heading("실시간 알람 모니터링", size="5", color="#111827"),
        rx.table.root(
            rx.table.header(rx.table.row(
                rx.table.column_header_cell("ID", width="80px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                rx.table.column_header_cell("상태", width="100px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                rx.table.column_header_cell("현재값", width="100px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                rx.table.column_header_cell("범위", width="140px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                rx.table.column_header_cell("초과량", width="100px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                rx.table.column_header_cell("위험도", width="150px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                rx.table.column_header_cell("판정시간", width="140px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                rx.table.column_header_cell("액션", width="100px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                style={"backgroundColor": "#f9fafb !important"})),
            rx.table.body(rx.foreach(DashboardRealtimeState.sensors, table_row)),
            width="100%", style={"backgroundColor": "white"}),
        width="100%", spacing="3", align="start")


def history_alarms_view() -> rx.Component:
    """History view - VTScada style table"""
    def history_row(alarm: Dict) -> rx.Component:
        return rx.table.row(
            rx.table.cell(rx.badge(rx.cond(alarm["acknowledged"], "✓ 확인완료", "● 미확인"), color_scheme=rx.cond(alarm["acknowledged"], "green", "orange"), variant="solid", size="1"), width="100px"),
            rx.table.cell(rx.text(alarm["triggered_at_short"], size="2", color="#6b7280"), width="140px"),
            rx.table.cell(rx.text(alarm["tag_name"], size="2", weight="medium", color="#111827"), width="120px"),
            rx.table.cell(isa_level_badge(alarm), width="120px"),
            rx.table.cell(rx.badge(alarm["scenario_id"], color_scheme=rx.cond(alarm["scenario_id"] == "AI_BASE", "purple", "blue"), variant="soft", size="1"), width="120px"),
            rx.table.cell(rx.text(f"{alarm['value']}{alarm['unit']}", size="2", weight="medium", color="#111827"), width="100px"),
            rx.table.cell(rx.text(alarm["message"], size="2", color="#6b7280"), width="300px"),
            rx.table.cell(rx.cond(alarm["acknowledged"], rx.badge("확인완료", variant="soft", color_scheme="green", size="1"),
                rx.button("Acknowledge", size="1", variant="soft", color_scheme="blue", on_click=lambda: AlarmsState.acknowledge_alarm(alarm["event_id"]))), width="120px"),
            _hover={"bg": "rgba(59, 130, 246, 0.05)", "cursor": "pointer"})
    return rx.cond(AlarmsState.filtered_count > 0,
        rx.vstack(
            rx.table.root(
                rx.table.header(rx.table.row(
                    rx.table.column_header_cell("상태", width="100px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                    rx.table.column_header_cell("시간", width="140px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                    rx.table.column_header_cell("센서", width="120px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                    rx.table.column_header_cell("ISA Priority", width="120px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                    rx.table.column_header_cell("시나리오", width="120px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                    rx.table.column_header_cell("값", width="100px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                    rx.table.column_header_cell("메시지", width="300px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                    rx.table.column_header_cell("액션", width="120px", style={"backgroundColor": "#f9fafb !important", "color": "#374151 !important"}),
                    style={"backgroundColor": "#f9fafb !important"})),
                rx.table.body(rx.foreach(AlarmsState.paginated_alarms, history_row)),
                width="100%", style={"backgroundColor": "white"}),
            pagination(current_page=AlarmsState.page, total_pages=AlarmsState.total_pages, total_items=AlarmsState.filtered_count,
                page_size=AlarmsState.page_size, on_prev=AlarmsState.prev_page, on_next=AlarmsState.next_page),
            spacing="4", width="100%"),
        rx.center(rx.vstack(rx.icon("inbox", size=48, color="#9ca3af"),
            rx.text("No alarms found", size="4", weight="bold", color="#6b7280"),
            rx.text("Try adjusting the filters or time range", size="2", color="#9ca3af"),
            spacing="3", align="center"), padding="12"))


def alarms_page() -> rx.Component:
    """
    Main alarms page - Light Mode

    KSYS Design: White background, black text throughout
    """
    return shell(
        rx.vstack(
            # Header
            rx.flex(
                rx.heading(
                    "🚨 Alarm Dashboard",
                    size="6",
                    weight="bold",
                    color="#111827",  # KSYS: Always black
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("refresh-cw", size=16),
                    "Refresh",
                    size="2",
                    variant="soft",
                    color_scheme="blue",
                    on_click=AlarmsState.refresh_data,
                    loading=AlarmsState.loading,
                ),
                justify="between",
                align="center",
                width="100%",
            ),

            # Sensor Summary (4 cards from Dashboard)
            rx.grid(
                stat_card(
                    title="Total Sensors",
                    value=DashboardRealtimeState.total_devices,
                    icon="cpu",
                    color="gray",
                ),
                stat_card(
                    title="Normal",
                    value=DashboardRealtimeState.normal_count,
                    icon="circle-check",
                    color="green",
                ),
                stat_card(
                    title="Warning",
                    value=DashboardRealtimeState.warning_count,
                    icon="triangle-alert",
                    color="orange",
                ),
                stat_card(
                    title="Critical",
                    value=DashboardRealtimeState.critical_count,
                    icon="circle-alert",
                    color="red",
                ),
                columns="4",
                spacing="3",
                width="100%",
            ),

            # ISA-18.2 Priority Statistics (History view only)
            rx.cond(
                AlarmsState.view_mode == "history",
                rx.vstack(
                    rx.text("ISA-18.2 Alarm Priority Distribution", size="3", weight="bold", color="#111827"),
                    rx.grid(
                        stat_card(
                            title="P1: Advisory",
                            value=AlarmsState.stat_priority_1_low,
                            icon="info",
                            color="blue",
                        ),
                        stat_card(
                            title="P2: Caution",
                            value=AlarmsState.stat_priority_2_medium,
                            icon="triangle-alert",
                            color="yellow",
                        ),
                        stat_card(
                            title="P3: Warning",
                            value=AlarmsState.stat_priority_3_high,
                            icon="alert-circle",
                            color="orange",
                        ),
                        stat_card(
                            title="P4: Emergency",
                            value=AlarmsState.stat_priority_4_critical,
                            icon="circle-alert",
                            color="red",
                        ),
                        columns="4",
                        spacing="3",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                    padding_y="3",
                ),
                rx.box(),
            ),

                        # View Mode Toggle (Active / History)
            rx.hstack(
                rx.button(
                    rx.icon("activity", size=16),
                    "Active Alarms",
                    on_click=lambda: AlarmsState.set_view_mode("active"),
                    color_scheme=rx.cond(AlarmsState.view_mode == "active", "blue", "gray"),
                    variant=rx.cond(AlarmsState.view_mode == "active", "solid", "soft"),
                    size="2",
                ),
                rx.button(
                    rx.icon("history", size=16),
                    "History",
                    on_click=lambda: AlarmsState.set_view_mode("history"),
                    color_scheme=rx.cond(AlarmsState.view_mode == "history", "blue", "gray"),
                    variant=rx.cond(AlarmsState.view_mode == "history", "solid", "soft"),
                    size="2",
                ),
                spacing="2",
                padding_y="2",
            ),

            # Time Range & Show Acknowledged (only for History view)
            rx.cond(
                AlarmsState.view_mode == "history",
                rx.hstack(
                    rx.text("Time Range:", size="2", weight="medium"),
                    rx.segmented_control.root(
                        rx.segmented_control.item("1h", value="1"),
                        rx.segmented_control.item("6h", value="6"),
                        rx.segmented_control.item("24h", value="24"),
                        rx.segmented_control.item("7d", value="168"),
                        value=str(AlarmsState.selected_hours),
                        on_change=AlarmsState.set_hours_filter,
                    ),
                    rx.spacer(),
                    rx.switch(
                        "Show Acknowledged",
                        checked=AlarmsState.show_acknowledged,
                        on_change=AlarmsState.toggle_show_acknowledged,
                    ),
                    width="100%",
                    align="center",
                ),
                rx.box(),
            ),

            # Search & Filters (only for History view)
            rx.cond(
                AlarmsState.view_mode == "history",
                filter_bar(
                    search_value=AlarmsState.search_query,
                    severity_filter=AlarmsState.severity_filter,
                    status_filter=AlarmsState.status_filter,
                    on_search=AlarmsState.set_search_query,
                    on_severity_change=AlarmsState.set_severity_filter,
                    on_status_change=AlarmsState.set_status_filter,
                ),
                rx.box(),
            ),

            # Info bar (only for History view)
            rx.cond(
                AlarmsState.view_mode == "history",
                rx.flex(
                    rx.text(
                        f"Showing {AlarmsState.filtered_count} alarms",
                        size="2",
                        color="#6b7280",
                        weight="medium",
                    ),
                    rx.spacer(),
                    rx.text(
                        f"Last update: {AlarmsState.last_update}",
                        size="2",
                        color="#9ca3af",
                    ),
                    align="center",
                    justify="between",
                    width="100%",
                    padding="3",
                    bg="#f9fafb",
                    border_radius="md",
                ),
                rx.box(),
            ),

            # Error message
            rx.cond(
                AlarmsState.error_message != "",
                rx.callout(
                    AlarmsState.error_message,
                    icon="triangle-alert",
                    color_scheme="red",
                ),
                rx.box(),
            ),

            # Content Area - Active or History view
            rx.cond(
                AlarmsState.loading,
                rx.center(
                    rx.vstack(
                        rx.spinner(size="3", color="#3b82f6"),
                        rx.text("Loading alarms...", size="2", color="#6b7280"),
                        spacing="3",
                        align="center",
                    ),
                    padding="12",
                ),
                rx.cond(
                    AlarmsState.view_mode == "active",
                    active_alarms_view(),
                    history_alarms_view(),
                ),
            ),

            spacing="4",
            width="100%",
            padding="4",
            bg="#f9fafb",  # Light gray page background
            min_height="100vh",
        ),
        active_route="/alarms",
    )