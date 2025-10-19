"""
Mini Chart Component
====================
Enhanced chart for sensor trend visualization with clear axes and threshold zones.
Redesigned for better information display with visible X/Y axes and colored reference zones.
"""

import reflex as rx
from typing import List, Dict, Optional


def mini_chart(
    data: List[Dict],
    color: str = "#3b82f6",
    height: int = 120,
    show_range_lines: bool = True,
    qc_min: Optional[float] = None,
    qc_max: Optional[float] = None,
    warning_low: Optional[float] = None,
    warning_high: Optional[float] = None,
    critical_low: Optional[float] = None,
    critical_high: Optional[float] = None
) -> rx.Component:
    """
    Render an enhanced mini chart with visible axes and threshold zones

    Args:
        data: List of dicts with "timestamp" and "value" keys
        color: Chart line color (hex or CSS color)
        height: Chart height in pixels (default 120 for better visibility)
        show_range_lines: Whether to show threshold zones and reference lines
        qc_min: Operating range minimum
        qc_max: Operating range maximum
        warning_low: Warning lower threshold (P3)
        warning_high: Warning upper threshold (P3)
        critical_low: Critical lower threshold (P4 Emergency)
        critical_high: Critical upper threshold (P4 Emergency)

    Returns:
        Recharts line chart with visible axes and colored threshold zones
    """

    return rx.recharts.line_chart(
        # Colored threshold zones for visual clarity
        # Critical zone HIGH (red background)
        rx.cond(
            show_range_lines & (critical_high is not None),
            rx.recharts.reference_area(
                y1=critical_high,
                y2="dataMax",
                fill="#fca5a5",
                fill_opacity=0.15,
                stroke="none"
            ),
            rx.fragment()
        ),
        # Warning zone HIGH (yellow background)
        rx.cond(
            show_range_lines & (warning_high is not None) & (critical_high is not None),
            rx.recharts.reference_area(
                y1=warning_high,
                y2=critical_high,
                fill="#fcd34d",
                fill_opacity=0.15,
                stroke="none"
            ),
            rx.fragment()
        ),
        # Warning zone LOW (yellow background)
        rx.cond(
            show_range_lines & (warning_low is not None) & (critical_low is not None),
            rx.recharts.reference_area(
                y1=critical_low,
                y2=warning_low,
                fill="#fcd34d",
                fill_opacity=0.15,
                stroke="none"
            ),
            rx.fragment()
        ),
        # Critical zone LOW (red background)
        rx.cond(
            show_range_lines & (critical_low is not None),
            rx.recharts.reference_area(
                y1="dataMin",
                y2=critical_low,
                fill="#fca5a5",
                fill_opacity=0.15,
                stroke="none"
            ),
            rx.fragment()
        ),

        # Main data line
        rx.recharts.line(
            data_key="value",
            stroke=color,
            stroke_width=2,
            dot=False,
            type_="monotone"
        ),

        # Reference lines with labels
        # Critical HIGH line
        rx.cond(
            show_range_lines & (critical_high is not None),
            rx.recharts.reference_line(
                y=critical_high,
                stroke="#ef4444",
                stroke_width=2,
                stroke_dasharray="4 4",
                label={
                    "value": "Critical",
                    "position": "insideTopRight",
                    "fontSize": 10,
                    "fill": "#ef4444",
                    "fontWeight": "bold"
                }
            ),
            rx.fragment()
        ),
        # Warning HIGH line
        rx.cond(
            show_range_lines & (warning_high is not None),
            rx.recharts.reference_line(
                y=warning_high,
                stroke="#f59e0b",
                stroke_width=1.5,
                stroke_dasharray="3 3",
                label={
                    "value": "Warning",
                    "position": "insideTopRight",
                    "fontSize": 9,
                    "fill": "#f59e0b"
                }
            ),
            rx.fragment()
        ),
        # Warning LOW line
        rx.cond(
            show_range_lines & (warning_low is not None),
            rx.recharts.reference_line(
                y=warning_low,
                stroke="#f59e0b",
                stroke_width=1.5,
                stroke_dasharray="3 3",
                label={
                    "value": "Warning",
                    "position": "insideBottomRight",
                    "fontSize": 9,
                    "fill": "#f59e0b"
                }
            ),
            rx.fragment()
        ),
        # Critical LOW line
        rx.cond(
            show_range_lines & (critical_low is not None),
            rx.recharts.reference_line(
                y=critical_low,
                stroke="#ef4444",
                stroke_width=2,
                stroke_dasharray="4 4",
                label={
                    "value": "Critical",
                    "position": "insideBottomRight",
                    "fontSize": 10,
                    "fill": "#ef4444",
                    "fontWeight": "bold"
                }
            ),
            rx.fragment()
        ),

        # X axis - visible with time labels
        rx.recharts.x_axis(
            data_key="timestamp",
            tick={"fontSize": 10, "fill": "#666"},
            stroke="#e5e7eb",
            tick_line={"stroke": "#e5e7eb"},
            tick_count=3,
            angle=-15,
            text_anchor="end",
            height=40
        ),

        # Y axis - visible with value labels
        rx.recharts.y_axis(
            tick={"fontSize": 10, "fill": "#666"},
            stroke="#e5e7eb",
            tick_line={"stroke": "#e5e7eb"},
            tick_count=5,
            width=50,
            domain=["auto", "auto"]
        ),

        # Grid for better readability
        rx.recharts.cartesian_grid(
            stroke_dasharray="3 3",
            stroke="#e5e7eb",
            stroke_opacity=0.3
        ),

        # Tooltip
        rx.recharts.tooltip(
            content_style={
                "backgroundColor": "rgba(255, 255, 255, 0.95)",
                "border": "1px solid #d1d5db",
                "borderRadius": "6px",
                "padding": "8px 10px",
                "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                "fontSize": "11px"
            },
            label_style={
                "color": "#374151",
                "fontWeight": "600",
                "fontSize": "11px",
                "marginBottom": "4px"
            },
            item_style={
                "color": "#6b7280",
                "fontSize": "11px"
            },
            separator=": ",
            cursor={"stroke": color, "strokeWidth": 1, "strokeOpacity": 0.3}
        ),

        data=data,
        height=height,
        margin={"top": 10, "right": 10, "bottom": 30, "left": 10},
        style={"cursor": "crosshair"}
    )
