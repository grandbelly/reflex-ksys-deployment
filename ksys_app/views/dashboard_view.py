"""Dashboard View - Clean component structure"""
import reflex as rx
import reflex_chakra as rc
from typing import Dict


def sensor_tile(sensor: Dict) -> rx.Component:
    """센서 타일 컴포넌트 - 단순하고 명확한 구조"""
    return rx.card(
        rx.vstack(
            # Header
            rx.hstack(
                rx.badge(
                    sensor["tag_name"],
                    color_scheme=rx.cond(
                        sensor["status"] == 2, "red",
                        rx.cond(sensor["status"] == 1, "amber", "green")
                    )
                ),
                rx.text(
                    sensor["range_text"],
                    size="1",
                    color="gray"
                ),
                width="100%",
                justify="between"
            ),

            # Gauge
            rx.center(
                rc.circular_progress(
                    rc.circular_progress_label(
                        rx.text(
                            sensor["value_text"],
                            font_weight="bold",
                            size="5"
                        )
                    ),
                    value=sensor["gauge_percent"],
                    color=rx.cond(
                        sensor["status"] == 2, "red.400",
                        rx.cond(sensor["status"] == 1, "yellow.400", "green.400")
                    ),
                    size="100px",
                    thickness="10px"
                ),
                padding="3"
            ),

            # Timestamp
            rx.text(
                sensor["timestamp"],
                size="1",
                color="gray",
                align="center"
            ),

            # Mini Chart
            rx.cond(
                sensor["has_chart"],
                rx.recharts.line_chart(
                    rx.recharts.line(
                        data_key="value",
                        stroke=sensor["chart_color"],
                        stroke_width=2,
                        dot=False
                    ),
                    rx.recharts.x_axis(data_key="time", hide=True),
                    rx.recharts.y_axis(hide=True),
                    data=sensor["chart_data"],
                    width="100%",
                    height=60,
                    margin={"top": 5, "right": 5, "left": 5, "bottom": 5}
                ),
                rx.box(
                    rx.text("Loading chart...", size="1", color="gray"),
                    height="60px",
                    display="flex",
                    align_items="center",
                    justify_content="center"
                )
            ),

            spacing="2",
            width="100%"
        ),
        size="2"
    )


def status_bar(stats: Dict) -> rx.Component:
    """상태 바 컴포넌트"""
    return rx.hstack(
        rx.badge(
            f"Normal: {stats['normal']}",
            color_scheme="green",
            size="2"
        ),
        rx.badge(
            f"Warning: {stats['warning']}",
            color_scheme="amber",
            size="2"
        ),
        rx.badge(
            f"Critical: {stats['critical']}",
            color_scheme="red",
            size="2"
        ),
        spacing="2"
    )


def control_bar(state) -> rx.Component:
    """컨트롤 바 컴포넌트"""
    return rx.hstack(
        rx.heading("Dashboard", size="5"),
        rx.spacer(),

        # Status
        status_bar(state.sensor_stats),

        rx.divider(orientation="vertical"),

        # Controls
        rx.text(state.last_update, size="2", color="gray"),

        rx.button(
            rx.cond(
                state.auto_refresh,
                "Stop Auto-refresh",
                "Start Auto-refresh"
            ),
            on_click=state.toggle_auto_refresh,
            color_scheme=rx.cond(
                state.auto_refresh,
                "red",
                "green"
            ),
            size="2"
        ),

        rx.button(
            "Refresh",
            on_click=state.manual_refresh,
            size="2",
            variant="soft"
        ),

        width="100%",
        padding="4",
        border_bottom="1px solid var(--gray-3)"
    )


def dashboard_page() -> rx.Component:
    """대시보드 페이지 - 깔끔한 구조"""
    from ..controllers.dashboard_controller import DashboardController

    return rx.box(
        control_bar(DashboardController),

        rx.cond(
            DashboardController.is_loading,
            rx.center(
                rx.spinner(size="3"),
                height="400px"
            ),

            rx.cond(
                DashboardController.has_error,
                rx.callout(
                    DashboardController.error_message,
                    icon="triangle-alert",
                    color_scheme="red",
                    margin="4"
                ),

                rx.grid(
                    rx.foreach(
                        DashboardController.sensor_tiles,
                        sensor_tile
                    ),
                    columns="4",
                    spacing="4",
                    padding="4",
                    width="100%"
                )
            )
        ),

        width="100%",
        height="100vh"
    )