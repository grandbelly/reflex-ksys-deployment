"""Dashboard Real-time View - UI Components following stock market pattern"""
import reflex as rx
import reflex_chakra as rc
from typing import Dict, List
from ..states.dashboard_realtime import DashboardRealtimeState
from ..components.dashboard import (
    dashboard_kpi_tiles,
    dashboard_kpi_tiles_compact,
    device_status_distribution_bar,
    status_badges_row
)
from ..utils.responsive import responsive_grid_columns, GRID_PRESETS


def realtime_header() -> rx.Component:
    """Real-time monitoring header with timestamp - Enhanced design"""
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon("activity", size=18, color="#3b82f6"),
                rx.text(
                    "실시간 모니터링",
                    size="4",
                    weight="bold",
                    color="#111827"
                ),
                spacing="2",
                align="center"
            ),
            rx.spacer(),
            rx.hstack(
                rx.icon("circle", size=10, color="green", style={"animation": "pulse 2s infinite"}),
                rx.text(
                    f"Last update: {DashboardRealtimeState.last_update}",
                    size="2",
                    color="#6b7280",
                    style={"font-family": "monospace"}
                ),
                spacing="2",
                align="center"
            ),
            width="100%",
            align="center"
        ),
        padding="4",
        border_bottom="2px solid #e5e7eb",
        bg="white"
    )


def status_bar() -> rx.Component:
    """Status bar showing system health"""

    return rx.box(
        rx.hstack(
            rx.badge(
                rx.hstack(
                    rx.icon("circle", size=10, color="green.500", style={"animation": "pulse 2s infinite"}),
                    rx.text("LIVE", size="1", weight="bold"),
                    spacing="1"
                ),
                variant="soft",
                color_scheme="green",
                size="2",
                style={"border-radius": "9999px"}
            ),
            rx.text(
                f"Last update: {DashboardRealtimeState.last_update}",
                size="1",
                class_name="text-slate-400",
                style={"font-family": "monospace"}
            ),
            rx.spacer(),
            rx.hstack(
                rx.text("정상:", size="2", weight="medium", class_name="text-green-400"),
                rx.text(DashboardRealtimeState.normal_count, size="2", weight="bold", class_name="text-green-300"),
                rx.text("|", class_name="text-slate-600"),
                rx.text("주의:", size="2", weight="medium", class_name="text-yellow-400"),
                rx.text(DashboardRealtimeState.warning_count, size="2", weight="bold", class_name="text-yellow-300"),
                rx.text("|", class_name="text-slate-600"),
                rx.text("위험:", size="2", weight="medium", class_name="text-red-400"),
                rx.text(DashboardRealtimeState.critical_count, size="2", weight="bold", class_name="text-red-300"),
                spacing="2"
            ),
            width="100%",
            align="center"
        ),
        padding="3",
        background="linear-gradient(90deg, var(--gray-2), var(--gray-1))",
        border_radius="lg",
        border="1px solid",
        class_name="bg-slate-800 rounded-lg border border-slate-700"
    )


def sensor_gauge(sensor_data: Dict) -> rx.Component:
    """Circular gauge component - using Chakra circular progress"""
    return rc.circular_progress(
        rc.circular_progress_label(
            rx.vstack(
                rx.text(
                    f"{sensor_data['value']:.2f}",
                    font_size="lg",
                    font_weight="bold", class_name="text-white"
                ),
                rx.cond(
                    sensor_data["unit"] != "",
                    rx.text(
                        sensor_data["unit"],
                        font_size="xs",
                        class_name="text-slate-400"
                    ),
                    rx.box()
                ),
                spacing="0",
                align_items="center"
            )
        ),
        value=sensor_data["gauge_percent"],
        size="90px",
        thickness="8px",
        color=rx.cond(
            sensor_data["status"] == 0,
            "green.400",
            rx.cond(
                sensor_data["status"] == 1,
                "yellow.400",
                "red.400"
            )
        ),
        track_color="slate.700"
    )


def mini_chart(
    data: List[Dict],
    min_val: float = None,
    max_val: float = None,
    status_color: str = "#10b981"  # Status-based color: green/yellow/red (3 states)
) -> rx.Component:
    """Enhanced mini chart with Stock Graph inspired styling

    Uses 3 status-based gradients (Normal/Warning/Critical) for the entire dashboard,
    not per-sensor gradients. This is more efficient and aligns with the 3-state alarm system.

    Stock Graph inspired features:
    - SVG linear gradient fill (top: 40% opacity → bottom: 5% opacity)
    - Minimal grid (stroke_opacity=0.2)
    - No axis lines (axis_line=False, tick_line=False)
    - Smooth curves with monotone interpolation
    - Clean, professional appearance

    3 Status Colors (3 gradients total):
    - Normal (green): #10b981 → gradient_green
    - Warning (yellow): #eab308 → gradient_yellow
    - Critical (red): #ef4444 → gradient_red

    Changes:
    - Height: 200px for better visibility
    - Legend at bottom with Value, Min, Max items
    - Dash-dot-dash pattern for threshold lines (8 4 2 4)
    - Timestamps in MM-DD HH:MM format
    """
    chart_components = []

    # MAIN DATA AREA - With fill opacity (simpler, works with dynamic colors)
    # SVG gradients require static IDs, which don't work well with dynamic status_color Var
    chart_components.append(
        rx.recharts.area(
            data_key="value",
            stroke=status_color,
            stroke_width=2,  # Thinner line (Stock Graph style)
            fill=status_color,
            fill_opacity=0.3,  # 30% opacity for Stock Graph effect
            dot=False,
            type_="monotone",  # Smooth curves
            animation_duration=300,
            active_dot=True  # Show dot on hover
        )
    )

    # REFERENCE LINES - Threshold boundaries (no labels, just lines)
    # Min threshold line
    chart_components.append(
        rx.cond(
            min_val != None,
            rx.recharts.reference_line(
                y=min_val,
                stroke="#f59e0b",  # orange-500
                stroke_dasharray="4 4",  # Dashed line (점선)
                stroke_width=1,  # Thin line
                if_overflow="extendDomain"
            ),
            rx.fragment()
        )
    )

    # Max threshold line
    chart_components.append(
        rx.cond(
            max_val != None,
            rx.recharts.reference_line(
                y=max_val,
                stroke="#f59e0b",  # orange-500
                stroke_dasharray="4 4",  # Dashed line (점선)
                stroke_width=1,  # Thin line
                if_overflow="extendDomain"
            ),
            rx.fragment()
        )
    )

    # AXES AND GRID - Stock Graph style (minimal, clean)
    chart_components.extend([
        # Cartesian grid - horizontal only, very subtle (Stock Graph style)
        rx.recharts.cartesian_grid(
            horizontal=True,
            vertical=False,  # No vertical lines
            stroke_dasharray="3 3",  # Stock Graph dash pattern
            stroke_opacity=0.2,  # Very subtle (Stock Graph style)
            stroke="#9ca3af",  # Neutral gray
        ),
        # X axis - no axis line, minimal style (Stock Graph inspired)
        rx.recharts.x_axis(
            data_key="timestamp",
            axis_line=False,  # No axis line (Stock Graph style)
            tick_line=False,  # No tick marks (Stock Graph style)
            height=50,
            angle=-30,
            text_anchor="end",
            tick={"fontSize": 8, "fill": "#9ca3af"}  # Neutral gray
        ),
        # Y axis - no axis line, minimal style (Stock Graph inspired)
        rx.recharts.y_axis(
            axis_line=False,  # No axis line (Stock Graph style)
            tick_line=False,  # No tick marks (Stock Graph style)
            width=55,
            tick={"fontSize": 11, "fill": "#9ca3af"}  # Neutral gray
        ),
        # Legend - minimal with tiny font
        rx.recharts.legend(
            vertical_align="bottom",
            height=12,
            icon_type="line",
            wrapperStyle={"fontSize": "7px", "paddingTop": "0px"}  # Very small font (7px)
        ),
        # Tooltip - enhanced styling
        rx.recharts.tooltip(
            content_style={
                "backgroundColor": "rgba(255, 255, 255, 0.98)",
                "border": "1px solid #d1d5db",
                "borderRadius": "6px",
                "padding": "8px 12px",
                "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                "fontSize": "11px"
            },
            label_style={
                "color": "#111827",
                "fontWeight": "600",
                "fontSize": "11px",
                "marginBottom": "4px"
            },
            item_style={
                "color": "#6b7280",
                "fontSize": "10px"
            },
            cursor={
                "stroke": status_color,
                "stroke_width": 1,
                "stroke_opacity": 0.3
            },
            separator=": "
        )
    ])

    # Return chart (using fill_opacity instead of SVG gradient for better compatibility)
    return rx.recharts.area_chart(
        *chart_components,
        data=data,  # Data with timestamps already formatted by state layer
        height=200,  # Increased to 200px to accommodate legend at bottom
        margin={"top": 10, "right": 10, "bottom": 10, "left": 5},  # Minimal bottom margin
        style={"cursor": "crosshair"}
    )


def sensor_tile(sensor_data: Dict) -> rx.Component:
    """Individual sensor tile with proper center alignment - Chart is clickable"""
    return rx.card(
        rx.vstack(
            # Header: Sensor ID + Description + Edit Button + Status Badge
            rx.hstack(
                rx.vstack(
                    rx.text(
                        sensor_data["tag_name"],
                        size="2",
                        weight="medium",
                        color="#6b7280"
                    ),
                    rx.cond(
                        sensor_data.get("description", "") != "",
                        rx.text(
                            sensor_data.get("description", ""),
                            size="1",
                            color="#9ca3af",
                            style={"white_space": "nowrap", "overflow": "hidden", "text_overflow": "ellipsis", "max_width": "100%"}
                        ),
                        rx.box()
                    ),
                    spacing="0",
                    align_items="start",
                    width="100%",
                    min_width="0"
                ),
                rx.icon_button(
                    rx.icon("settings", size=14),
                    size="1",
                    variant="ghost",
                    color_scheme="gray",
                    on_click=lambda: DashboardRealtimeState.open_edit_dialog(
                        sensor_data["tag_name"],
                        sensor_data.get("description", ""),
                        sensor_data.get("unit", ""),
                        sensor_data["min_val"],
                        sensor_data["max_val"],
                        sensor_data["warning_low"],
                        sensor_data["warning_high"],
                        sensor_data["critical_low"],
                        sensor_data["critical_high"]
                    ),
                    cursor="pointer",
                    flex_shrink="0"
                ),
                rx.spacer(),
                rx.badge(
                    rx.cond(
                        sensor_data["status"] == 0,
                        "Normal",
                        rx.cond(
                            sensor_data["status"] == 1,
                            "Warning",
                            "Critical"
                        )
                    ),
                    color_scheme=rx.cond(
                        sensor_data["status"] == 0,
                        "green",
                        rx.cond(
                            sensor_data["status"] == 1,
                            "amber",
                            "red"
                        )
                    ),
                    variant="soft",
                    size="1",
                    flex_shrink="0"
                ),
                width="100%",
                align="center"
            ),

            # Row 1: Small Gauge (Left) + Large Value (Right) - VERTICALLY CENTER ALIGNED
            rx.hstack(
                # Left: Small circular gauge
                rx.box(
                    rc.circular_progress(
                        rc.circular_progress_label(
                            rx.text(
                                f"{sensor_data['gauge_percent']:.0f}%",
                                size="1",
                                weight="bold",
                                color=rx.cond(
                                    sensor_data["status"] == 0,
                                    "#10b981",
                                    rx.cond(
                                        sensor_data["status"] == 1,
                                        "#f59e0b",
                                        "#ef4444"
                                    )
                                )
                            )
                        ),
                        value=sensor_data["gauge_percent"],
                        size="50px",
                        thickness="6px",
                        color=rx.cond(
                            sensor_data["status"] == 0,
                            "green.500",
                            rx.cond(
                                sensor_data["status"] == 1,
                                "yellow.500",
                                "red.500"
                            )
                        ),
                        track_color="gray.200"
                    ),
                    width="50px",
                    flex_shrink="0"
                ),

                # Right: Large value with unit and range - CENTERED
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            f"{sensor_data['value']:.2f}",
                            size="7",
                            weight="bold",
                            color="#111827"
                        ),
                        rx.cond(
                            sensor_data.get("unit", "") != "",
                            rx.text(
                                sensor_data.get("unit", ""),
                                size="3",
                                color="#6b7280",
                                style={"margin_left": "4px"}
                            ),
                            rx.box()
                        ),
                        spacing="1",
                        align="center"
                    ),
                    rx.text(
                        f"{sensor_data['min_val']:.2f} ~ {sensor_data['max_val']:.2f}",
                        size="1",
                        color="#6b7280"
                    ),
                    spacing="0",
                    align="center",  # Changed from "start" to "center"
                    justify="center",
                    width="100%"
                ),

                spacing="3",
                align="center",
                width="100%"
            ),

            # Row 2: Timestamp (moved above chart)
            rx.text(
                sensor_data["timestamp"],
                size="1",
                color="#9ca3af",
                text_align="right",
                width="100%"
            ),

            # Row 3: Mini sparkline chart (clickable) - Click to view full chart dialog
            rx.box(
                mini_chart(
                    sensor_data["chart_points"],
                    min_val=sensor_data.get("min_val"),
                    max_val=sensor_data.get("max_val"),
                    status_color=sensor_data["chart_color"],
                ),
                on_click=DashboardRealtimeState.open_chart_dialog(sensor_data["tag_name"]),
                cursor="pointer",
                border_radius="8px",
                border="1px dashed rgba(156, 163, 175, 0.3)",
                padding="2",
                width="100%",
                _hover={
                    "opacity": "0.85",
                    "border_color": "rgba(59, 130, 246, 0.5)",
                    "background": "rgba(59, 130, 246, 0.05)",
                },
                transition="all 0.2s ease",
            ),

            spacing="3",  # Increased from "2" to "3" for more vertical spacing
            width="100%"
        ),
        padding="4",  # Increased from "3" to "4" for more internal padding
        width="100%",
        class_name="bg-white border border-gray-200 hover:border-blue-400 transition-all duration-200 shadow-sm"
    )


def alarm_monitoring_table() -> rx.Component:
    """Real-time alarm monitoring table"""
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



def full_screen_chart_dialog() -> rx.Component:
    """Full-screen chart dialog for detailed sensor view"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.icon("chart-line", size=20, color="#3b82f6"),
                    rx.heading(
                        f"Sensor Chart: {DashboardRealtimeState.chart_dialog_tag_name}",
                        size="4"
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            rx.icon("x", size=20),
                            variant="ghost",
                            color_scheme="gray",
                        )
                    ),
                    width="100%",
                    align="center",
                ),

                rx.divider(),

                # Sensor info bar
                rx.cond(
                    DashboardRealtimeState.chart_dialog_sensor,
                    rx.hstack(
                        rx.badge(
                            rx.cond(
                                DashboardRealtimeState.chart_dialog_sensor.get("status", 0) == 0,
                                "Normal",
                                rx.cond(
                                    DashboardRealtimeState.chart_dialog_sensor.get("status", 0) == 1,
                                    "Warning",
                                    "Critical"
                                )
                            ),
                            color_scheme=rx.cond(
                                DashboardRealtimeState.chart_dialog_sensor.get("status", 0) == 0,
                                "green",
                                rx.cond(
                                    DashboardRealtimeState.chart_dialog_sensor.get("status", 0) == 1,
                                    "amber",
                                    "red"
                                )
                            ),
                            variant="soft",
                            size="2"
                        ),
                        rx.text(
                            f"Current: {DashboardRealtimeState.chart_dialog_sensor.get('value_str', '')}",
                            size="2",
                            weight="medium"
                        ),
                        rx.text(
                            f"Range: {DashboardRealtimeState.chart_dialog_sensor.get('range_str', '')}",
                            size="2",
                            color="gray"
                        ),
                        spacing="3",
                        align="center"
                    ),
                ),

                # Large chart with diagonal X-axis labels
                rx.box(
                    rx.recharts.area_chart(
                        rx.recharts.area(
                            data_key="value",
                            stroke=DashboardRealtimeState.chart_dialog_sensor.get("chart_color", "#3b82f6"),
                            fill=DashboardRealtimeState.chart_dialog_sensor.get("chart_color", "#3b82f6"),
                            fill_opacity=0.3,
                            type_="monotone",
                        ),
                        rx.recharts.x_axis(
                            data_key="timestamp",
                            angle=-45,  # Diagonal rotation for better readability
                            text_anchor="end",
                            height=100,  # Increased height to accommodate rotated labels
                            tick={"fontSize": 10}
                        ),
                        rx.recharts.y_axis(),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3", stroke_opacity=0.3),
                        rx.recharts.tooltip(),
                        rx.recharts.legend(),
                        # Reference lines for thresholds
                        rx.recharts.reference_line(
                            y=DashboardRealtimeState.chart_dialog_sensor.get("min_val", 0),
                            stroke="#f59e0b",
                            stroke_dasharray="4 4",
                            label="Min"
                        ),
                        rx.recharts.reference_line(
                            y=DashboardRealtimeState.chart_dialog_sensor.get("max_val", 100),
                            stroke="#f59e0b",
                            stroke_dasharray="4 4",
                            label="Max"
                        ),
                        data=DashboardRealtimeState.chart_dialog_data,
                        height=500,
                        width="100%"
                    ),
                    width="100%",
                    padding="4",
                    border_radius="md",
                    border="1px solid",
                    border_color=rx.color("gray", 4),
                    background=rx.color("gray", 1),
                ),

                rx.text(
                    f"Last 24 hours | Updated: {DashboardRealtimeState.last_update}",
                    size="2",
                    color="gray",
                ),

                spacing="4",
                width="100%",
            ),
            max_width="90vw",
            max_height="90vh",
        ),
        open=DashboardRealtimeState.show_chart_dialog,
        on_open_change=DashboardRealtimeState.set_show_chart_dialog,
    )


def sensor_edit_dialog() -> rx.Component:
    """Sensor information edit dialog"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("settings", size=20),
                    rx.text("센서 정보 편집"),
                    spacing="2",
                    align="center"
                )
            ),
            rx.dialog.description(
                f"센서 {DashboardRealtimeState.edit_tag_name}의 정보를 수정합니다.",
                size="2",
                margin_bottom="4"
            ),

            rx.vstack(
                # Description
                rx.vstack(
                    rx.text("설명", size="2", weight="medium"),
                    rx.input(
                        value=DashboardRealtimeState.edit_description,
                        on_change=DashboardRealtimeState.set_edit_description,
                        placeholder="센서 설명을 입력하세요",
                        width="100%"
                    ),
                    spacing="1",
                    width="100%"
                ),

                # Unit
                rx.vstack(
                    rx.text("단위", size="2", weight="medium"),
                    rx.input(
                        value=DashboardRealtimeState.edit_unit,
                        on_change=DashboardRealtimeState.set_edit_unit,
                        placeholder="단위 (예: °C, %, bar)",
                        width="100%"
                    ),
                    spacing="1",
                    width="100%"
                ),

                # Range: Min and Max
                rx.hstack(
                    rx.vstack(
                        rx.text("최소값", size="2", weight="medium"),
                        rx.input(
                            value=DashboardRealtimeState.edit_min_val,
                            on_change=DashboardRealtimeState.update_min_val,
                            type="number",
                            width="100%"
                        ),
                        spacing="1",
                        width="100%"
                    ),
                    rx.vstack(
                        rx.text("최대값", size="2", weight="medium"),
                        rx.input(
                            value=DashboardRealtimeState.edit_max_val,
                            on_change=DashboardRealtimeState.update_max_val,
                            type="number",
                            width="100%"
                        ),
                        spacing="1",
                        width="100%"
                    ),
                    spacing="3",
                    width="100%"
                ),

                # Warning Thresholds
                rx.hstack(
                    rx.vstack(
                        rx.text("경고 하한", size="2", weight="medium"),
                        rx.input(
                            value=DashboardRealtimeState.edit_warning_low,
                            on_change=DashboardRealtimeState.update_warning_low,
                            type="number",
                            width="100%"
                        ),
                        spacing="1",
                        width="100%"
                    ),
                    rx.vstack(
                        rx.text("경고 상한", size="2", weight="medium"),
                        rx.input(
                            value=DashboardRealtimeState.edit_warning_high,
                            on_change=DashboardRealtimeState.update_warning_high,
                            type="number",
                            width="100%"
                        ),
                        spacing="1",
                        width="100%"
                    ),
                    spacing="3",
                    width="100%"
                ),

                # Critical Thresholds
                rx.hstack(
                    rx.vstack(
                        rx.text("위험 하한", size="2", weight="medium"),
                        rx.input(
                            value=DashboardRealtimeState.edit_critical_low,
                            on_change=DashboardRealtimeState.update_critical_low,
                            type="number",
                            width="100%"
                        ),
                        spacing="1",
                        width="100%"
                    ),
                    rx.vstack(
                        rx.text("위험 상한", size="2", weight="medium"),
                        rx.input(
                            value=DashboardRealtimeState.edit_critical_high,
                            on_change=DashboardRealtimeState.update_critical_high,
                            type="number",
                            width="100%"
                        ),
                        spacing="1",
                        width="100%"
                    ),
                    spacing="3",
                    width="100%"
                ),

                spacing="4",
                width="100%"
            ),

            rx.flex(
                rx.dialog.close(
                    rx.button(
                        "취소",
                        variant="soft",
                        color_scheme="gray"
                    )
                ),
                rx.dialog.close(
                    rx.button(
                        "저장",
                        on_click=DashboardRealtimeState.save_sensor_info,
                        variant="solid"
                    )
                ),
                spacing="3",
                margin_top="4",
                justify="end"
            ),

            max_width="500px"
        ),
        open=DashboardRealtimeState.show_edit_dialog,
        on_open_change=DashboardRealtimeState.set_show_edit_dialog
    )


def dashboard_realtime_page() -> rx.Component:
    """Main dashboard page - like stock market dashboard

    Each mini_chart includes its own SVG gradient definition (Stock Graph pattern)
    """

    return rx.fragment(
        # Full-screen chart dialog
        full_screen_chart_dialog(),

        # Sensor edit dialog
        sensor_edit_dialog(),

        # Main content
        rx.vstack(
            # Header with timestamp (NEW)
            realtime_header(),

            # Compact KPI Tiles (NEW - smaller design)
        dashboard_kpi_tiles_compact(DashboardRealtimeState),

        # Status badges row (NEW - replacing distribution bar)
        status_badges_row(DashboardRealtimeState),

        # Sensor grid
        rx.grid(
            rx.foreach(
                DashboardRealtimeState.formatted_sensors,
                lambda sensor: sensor_tile(sensor)
            ),
            columns=GRID_PRESETS["cards_1_2_4"],  # 모바일:1, 태블릿:2, 데스크톱:4
            gap="4",
            width="100%"
        ),

            # Alarm monitoring table
            alarm_monitoring_table(),

            spacing="3",
            width="100%",
            class_name="p-2 sm:p-3 md:p-4"
        )
    )
