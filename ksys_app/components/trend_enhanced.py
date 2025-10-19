"""
Enhanced trend components with clean white theme
Inspired by stock chart design but adapted for industrial monitoring
"""
import reflex as rx
from typing import List, Dict, Any


def clean_area_chart(data: List[Dict[str, Any]], height: int = 400) -> rx.Component:
    """Clean area chart with subtle gradient - white theme"""
    return rx.recharts.area_chart(
        rx.recharts.area(
            data_key="avg",
            stroke="#3b82f6",  # Blue instead of green for professional look
            fill="url(#blueGradient)",
            stroke_width=2,
            dot=False,
            animation_duration=300,
        ),
        rx.recharts.defs(
            rx.recharts.linear_gradient(
                rx.recharts.stop(offset="0%", stop_color="#3b82f6", stop_opacity=0.3),
                rx.recharts.stop(offset="95%", stop_color="#3b82f6", stop_opacity=0.05),
                id="blueGradient",
                x1="0", y1="0", x2="0", y2="1",
            ),
        ),
        rx.recharts.x_axis(
            data_key="bucket_formatted",
            stroke="#e5e7eb",
            tick={"fill": "#6b7280", "fontSize": 11},
            axis_line={"stroke": "#e5e7eb"},
        ),
        rx.recharts.y_axis(
            stroke="#e5e7eb",
            tick={"fill": "#6b7280", "fontSize": 11},
            axis_line={"stroke": "#e5e7eb"},
            domain=["dataMin - 5", "dataMax + 5"],
        ),
        rx.recharts.cartesian_grid(
            stroke_dasharray="3 3",
            stroke="#f3f4f6",
            opacity=0.5,
            horizontal=True,
            vertical=False,
        ),
        rx.recharts.tooltip(
            content_style={
                "backgroundColor": "white",
                "border": "1px solid #e5e7eb",
                "borderRadius": "8px",
                "padding": "8px",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
            },
            label_style={"color": "#6b7280", "fontSize": "12px"},
            item_style={"color": "#3b82f6", "fontSize": "14px", "fontWeight": "bold"},
        ),
        data=data,
        height=height,
        margin={"top": 10, "right": 30, "bottom": 30, "left": 60},
    )


def metric_card(title: str, value: str, color: str = "blue", icon: str = None) -> rx.Component:
    """Clean metric card for displaying KPIs"""
    icon_color_map = {
        "blue": "#3b82f6",
        "green": "#10b981",
        "red": "#ef4444",
        "amber": "#f59e0b",
        "gray": "#6b7280",
    }
    
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=16, color=icon_color_map.get(color, "#6b7280")) if icon else rx.fragment(),
                rx.text(title, size="1", color="gray", weight="medium"),
                spacing="1",
                align="center",
            ),
            rx.text(
                value,
                size="5",
                weight="bold",
                color=icon_color_map.get(color, "#1f2937"),
            ),
            spacing="1",
        ),
        class_name="bg-white border border-gray-200 hover:shadow-md transition-shadow",
    )


def time_range_pills(selected: str, on_change) -> rx.Component:
    """Time range selection pills - cleaner than buttons"""
    ranges = [
        {"label": "5분", "value": "5 min"},
        {"label": "1시간", "value": "60 min"},
        {"label": "1일", "value": "24 hour"},
        {"label": "1주", "value": "7 days"},
        {"label": "1개월", "value": "30 days"},
        {"label": "3개월", "value": "3 months"},
    ]
    
    return rx.hstack(
        *[
            rx.box(
                rx.text(
                    r["label"],
                    size="2",
                    weight="medium" if selected == r["value"] else "normal",
                    color="white" if selected == r["value"] else "gray",
                ),
                padding="6px 12px",
                border_radius="full",
                background="#3b82f6" if selected == r["value"] else "#f3f4f6",
                cursor="pointer",
                on_click=lambda v=r["value"]: on_change(v),
                class_name="hover:shadow-sm transition-all",
            )
            for r in ranges
        ],
        spacing="2",
        wrap="wrap",
    )


def sensor_info_header(
    tag_name: str,
    current_value: float,
    unit: str = "",
    status: str = "normal"
) -> rx.Component:
    """Sensor information header"""
    status_colors = {
        "normal": "#10b981",
        "warning": "#f59e0b", 
        "critical": "#ef4444",
    }
    
    status_icons = {
        "normal": "circle-check",
        "warning": "alert-triangle",
        "critical": "alert-circle",
    }
    
    return rx.hstack(
        # Tag name
        rx.heading(tag_name, size="6", weight="bold", color="gray.900"),
        
        rx.spacer(),
        
        # Current value with status
        rx.hstack(
            rx.icon(
                status_icons.get(status, "info"),
                color=status_colors.get(status, "#6b7280"),
                size=20,
            ),
            rx.text(
                f"{current_value:.2f}",
                size="6",
                weight="bold",
                color=status_colors.get(status, "#1f2937"),
            ),
            rx.text(unit, size="3", color="gray"),
            spacing="2",
            align="center",
        ),
        
        width="100%",
        padding="12px 0",
        border_bottom="1px solid #e5e7eb",
    )