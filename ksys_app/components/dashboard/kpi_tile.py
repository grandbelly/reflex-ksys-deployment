"""
KPI Tile Component for Dashboard - Manufacturing Dashboard Dark Theme
======================================================================
Manufacturing Dashboard style KPI cards with gradient backgrounds.
"""
import reflex as rx
from typing import Optional
from ...states.base_state import BaseState as B


def kpi_tile_compact(
    title: str,
    value: rx.Var | str | int | float,
    subtitle: Optional[rx.Var | str] = None,
    color: str = "blue",
    icon: Optional[str] = None,
) -> rx.Component:
    """
    Compact KPI Tile - Light background to distinguish from sensor cards

    Args:
        title: KPI title (e.g., "Total Devices")
        value: Main KPI value (e.g., "9", "77.8%")
        subtitle: Optional subtitle (e.g., "온라인 디바이스")
        color: Color theme (blue, red, orange, gray)
        icon: Optional icon name from lucide (small, inline)

    Returns:
        Compact KPI tile with light colored background
    """
    # Icon and background colors
    color_schemes = {
        "blue": {"icon": "#3b82f6", "bg": "#eff6ff"},      # blue-50
        "red": {"icon": "#ef4444", "bg": "#fef2f2"},        # red-50
        "orange": {"icon": "#f97316", "bg": "#fff7ed"},     # orange-50
        "gray": {"icon": "#6b7280", "bg": "#f9fafb"}        # gray-50
    }

    scheme = color_schemes.get(color, color_schemes["gray"])

    return rx.box(
        rx.hstack(
            # Left: Title with small inline icon
            rx.vstack(
                rx.hstack(
                    rx.text(title, size="1", color="#6b7280", weight="medium"),  # gray-500
                    rx.cond(
                        icon is not None,
                        rx.icon(icon, size=14, color=scheme["icon"]),
                        rx.box()
                    ),
                    spacing="1",
                    align="center"
                ),
                rx.text(value, size="6", weight="bold", color="#111827"),  # gray-900
                rx.cond(
                    subtitle is not None,
                    rx.text(subtitle, size="1", color="#6b7280"),  # gray-500
                    rx.box()
                ),
                spacing="1",
                align="start"
            ),
            spacing="3",
            align="center",
            width="100%"
        ),
        padding="3",
        bg=scheme["bg"],  # Light colored background
        border_radius="8px",
        border="1px solid #e5e7eb",  # gray-200
        width="100%"
    )


def kpi_tile(
    title: str,
    value: rx.Var | str | int | float,
    subtitle: Optional[rx.Var | str] = None,
    color: str = "blue",
    icon: Optional[str] = None,
    trend: Optional[rx.Var | str] = None,
    trend_direction: Optional[str] = None  # "up" | "down" | "neutral"
) -> rx.Component:
    """
    Manufacturing Dashboard Style KPI Tile with gradient background

    Args:
        title: KPI title (e.g., "Total Sensors")
        value: Main KPI value (e.g., "9", "100%")
        subtitle: Optional subtitle (e.g., "Active", "Last hour")
        color: Color scheme (blue, green, yellow, red, gray)
        icon: Optional icon name from lucide
        trend: Optional trend text (e.g., "+5%", "-2.3%")
        trend_direction: Trend direction for color coding

    Returns:
        Manufacturing Dashboard style card component
    """
    # Status-based gradient colors (Manufacturing Dashboard pattern)
    gradient_colors = {
        "green": "from-green-500 to-emerald-600",
        "blue": "from-blue-500 to-cyan-600",
        "yellow": "from-yellow-500 to-orange-600",
        "red": "from-red-500 to-pink-600",
        "gray": "from-slate-500 to-slate-600"
    }

    # Trend color mapping
    trend_colors = {
        "up": "green",
        "down": "red",
        "neutral": "gray"
    }
    trend_color = trend_colors.get(trend_direction, "gray") if trend_direction else "gray"

    # Icon color classes
    icon_gradient = gradient_colors.get(color, gradient_colors["blue"])

    return rx.box(
        rx.vstack(
            # Icon with gradient background
            rx.hstack(
                rx.box(
                    rx.cond(
                        icon is not None,
                        rx.icon(icon, size=24, color="white"),
                        rx.box()
                    ),
                    class_name=f"p-3 rounded-lg bg-gradient-to-br {icon_gradient}",
                ),
                rx.cond(
                    trend is not None,
                    rx.hstack(
                        rx.icon(
                            rx.match(
                                trend_direction,
                                ("up", "trending-up"),
                                ("down", "trending-down"),
                                "minus"
                            ),
                            size=16,
                            class_name=rx.match(
                                trend_direction,
                                ("up", "text-green-400"),
                                ("down", "text-red-400"),
                                "text-slate-400"
                            )
                        ),
                        rx.text(
                            trend,
                            size="2",
                            class_name=rx.match(
                                trend_direction,
                                ("up", "text-green-400"),
                                ("down", "text-red-400"),
                                "text-slate-400"
                            )
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.box()
                ),
                justify="between",
                align="center",
                class_name="mb-4",
            ),

            # Value
            rx.text(
                value,
                size="8",
                weight="bold",
                class_name="text-black mb-2",
            ),

            # Title and subtitle
            rx.vstack(
                rx.text(
                    title,
                    size="2",
                    class_name="text-black",
                ),
                rx.cond(
                    subtitle is not None,
                    rx.text(
                        subtitle,
                        size="1",
                        class_name="text-black",
                    ),
                    rx.box()
                ),
                spacing="1",
                align="start",
                width="100%"
            ),

            spacing="3",
            width="100%"
        ),
        class_name="bg-white rounded-xl p-5 border border-blue-200 hover:border-blue-400 transition-all duration-200 shadow-sm",
    )


def kpi_tiles_row(
    tiles: list[dict]
) -> rx.Component:
    """
    Render a row of Manufacturing Dashboard KPI tiles

    Args:
        tiles: List of tile configurations, each with keys:
            - title: str
            - value: rx.Var | str
            - subtitle: Optional[str]
            - color: str
            - icon: Optional[str]
            - trend: Optional[str]
            - trend_direction: Optional[str]

    Returns:
        Grid of KPI tiles
    """
    return rx.grid(
        *[
            kpi_tile(
                title=tile.get("title", ""),
                value=tile.get("value", ""),
                subtitle=tile.get("subtitle"),
                color=tile.get("color", "blue"),
                icon=tile.get("icon"),
                trend=tile.get("trend"),
                trend_direction=tile.get("trend_direction")
            )
            for tile in tiles
        ],
        spacing="4",
        width="100%",
        columns="4"
    )


# Compact KPI tiles row for new design
def dashboard_kpi_tiles_compact(state_class) -> rx.Component:
    """
    Compact Dashboard KPI Tiles - Simple & Intuitive
    직관적인 텍스트: 총 센서 수, Normal, Warning, Critical

    Args:
        state_class: State class with KPI properties

    Returns:
        Row of 4 compact KPI tiles with clear labels
    """
    return rx.grid(
        kpi_tile_compact(
            title="총 센서 수",
            value=state_class.total_devices,
            subtitle="모니터링 중",
            color="gray",
            icon="cpu"
        ),
        kpi_tile_compact(
            title="Normal",
            value=state_class.normal_count,
            subtitle="정상",
            color="blue",
            icon="circle-check"
        ),
        kpi_tile_compact(
            title="Warning",
            value=state_class.warning_count,
            subtitle="주의",
            color="orange",
            icon="triangle-alert"
        ),
        kpi_tile_compact(
            title="Critical",
            value=state_class.critical_count,
            subtitle="위험",
            color="red",
            icon="circle-alert"
        ),
        spacing="3",
        columns="4",
        width="100%"
    )


# Preset KPI tiles for dashboard
def dashboard_kpi_tiles(state_class) -> rx.Component:
    """
    Dashboard Summary Bar - 4 KPI tiles matching the intended design
    의도한 디자인: 총 디바이스, Critical 비율, 평균 조과율, 최고 조과

    Args:
        state_class: State class with KPI properties (e.g., DashboardRealtimeState)

    Returns:
        Row of 4 KPI tiles with proper statistics
    """
    return kpi_tiles_row([
        {
            "title": "총 디바이스",
            "value": state_class.total_devices,
            "subtitle": "온라인 디바이스 수",
            "color": "blue",
            "icon": "chart-no-axes-column-increasing"
        },
        {
            "title": "Critical 비율",
            "value": state_class.critical_percentage_display,
            "subtitle": rx.text(state_class.critical_count, "개 디바이스"),
            "color": "red",
            "icon": "triangle-alert"
        },
        {
            "title": "평균 조과율",
            "value": state_class.avg_deviation_display,
            "subtitle": "Critical 평균",
            "color": "yellow",
            "icon": "trending-up"
        },
        {
            "title": "최고 조과",
            "value": state_class.max_alarm_display,
            "subtitle": state_class.max_alarm_sensor,
            "color": "red",
            "icon": "circle-alert"
        }
    ])


def status_badges_row(state_class) -> rx.Component:
    """
    Status badges row - Compact badge display showing Normal/Warning/Critical counts
    새 디자인: ● Normal:1  ● Warning:1  ● Critical:7

    Args:
        state_class: State class with count properties

    Returns:
        Row of status badges
    """
    return rx.hstack(
        rx.badge(
            rx.hstack(
                rx.icon("circle", size=10, color="green"),
                rx.text("Normal:", size="2", weight="medium"),
                rx.text(state_class.normal_count, size="2", weight="bold"),
                spacing="1"
            ),
            variant="soft",
            color_scheme="green"
        ),
        rx.badge(
            rx.hstack(
                rx.icon("circle", size=10, color="orange"),
                rx.text("Warning:", size="2", weight="medium"),
                rx.text(state_class.warning_count, size="2", weight="bold"),
                spacing="1"
            ),
            variant="soft",
            color_scheme="amber"
        ),
        rx.badge(
            rx.hstack(
                rx.icon("circle", size=10, color="red"),
                rx.text("Critical:", size="2", weight="medium"),
                rx.text(state_class.critical_count, size="2", weight="bold"),
                spacing="1"
            ),
            variant="soft",
            color_scheme="red"
        ),
        spacing="2",
        padding="2"
    )


def device_status_distribution_bar(state_class) -> rx.Component:
    """
    Device Status Distribution Bar - Horizontal segmented bar showing device status distribution
    디바이스 상태 분포 - Critical/Warning/Normal 비율을 시각화

    Args:
        state_class: State class with device count properties

    Returns:
        Horizontal segmented bar with legend
    """
    return rx.box(
        rx.vstack(
            # Title
            rx.text(
                "디바이스 상태 분포",
                size="2",
                weight="medium",
                color="gray",
                margin_bottom="2"
            ),

            # Segmented bar
            rx.hstack(
                # Critical segment
                rx.box(
                    width=f"{state_class.critical_percentage}%",
                    height="24px",
                    bg="#dc2626",  # red-600
                    border_radius="4px 0 0 4px",
                ),
                # Warning segment
                rx.box(
                    width=f"{state_class.warning_percentage}%",
                    height="24px",
                    bg="#f59e0b",  # amber-500
                ),
                # Normal segment
                rx.box(
                    width=f"{state_class.normal_percentage}%",
                    height="24px",
                    bg="#10b981",  # emerald-500
                    border_radius="0 4px 4px 0",
                ),
                width="100%",
                spacing="0",
                overflow="hidden",
            ),

            # Legend
            rx.hstack(
                rx.hstack(
                    rx.box(width="12px", height="12px", bg="#dc2626", border_radius="2px"),
                    rx.text("Critical", size="1", color="gray"),
                    spacing="1",
                ),
                rx.hstack(
                    rx.box(width="12px", height="12px", bg="#f59e0b", border_radius="2px"),
                    rx.text("Warning", size="1", color="gray"),
                    spacing="1",
                ),
                rx.hstack(
                    rx.box(width="12px", height="12px", bg="#10b981", border_radius="2px"),
                    rx.text("Normal", size="1", color="gray"),
                    spacing="1",
                ),
                spacing="4",
                justify="end",
                width="100%",
                margin_top="2",
            ),

            spacing="2",
            width="100%",
        ),
        padding="4",
        bg="white",
        border_radius="8px",
        border="1px solid #e5e7eb",
        margin_top="4",
        margin_bottom="4",
    )
