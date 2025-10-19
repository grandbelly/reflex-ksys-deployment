"""Sparkline Chart Component using Reflex Recharts

Features:
- 48px height sparkline
- Fixed Y-axis domain [min, max]
- Warning threshold bands (amber, 12% opacity)
- Critical threshold bands (red, 18% opacity)
- Missing data handling (line breaks, connectNulls=False)
- Range overflow clamping with marker
- Last point marker
- Status-based line colors
"""
import reflex as rx
from typing import List, Dict, Optional


def sparkline_chart(
    data: List[Dict],
    min_val: float = 0,
    max_val: float = 100,
    warning_low: Optional[float] = None,
    warning_high: Optional[float] = None,
    status: int = 0,
    width: int = 250,
    height: int = 48,
    **kwargs
) -> rx.Component:
    """Create a sparkline chart using Reflex Recharts

    Args:
        data: List of {"time": str, "value": float|None}
        min_val: Minimum Y value for domain
        max_val: Maximum Y value for domain
        warning_low: Warning lower threshold (optional)
        warning_high: Warning upper threshold (optional)
        status: 0=normal (blue), 1=warning (amber), 2=critical (red)
        width: Chart width in pixels
        height: Chart height in pixels (default: 48px for sparkline)

    Returns:
        Recharts LineChart component
    """

    # Determine line color based on status
    if status == 0:
        line_color = "#3b82f6"  # blue
        area_color = "#3b82f6"
    elif status == 1:
        line_color = "#f59e0b"  # amber
        area_color = "#f59e0b"
    else:
        line_color = "#ef4444"  # red
        area_color = "#ef4444"

    # Clamp values to range and mark overflow
    processed_data = []
    for point in data:
        if point.get("value") is not None:
            val = point["value"]
            clamped = max(min_val, min(max_val, val))
            processed_data.append({
                "time": point.get("time", ""),
                "value": clamped,
                "overflow": val > max_val or val < min_val
            })
        else:
            # Keep None for line breaks
            processed_data.append({
                "time": point.get("time", ""),
                "value": None,
                "overflow": False
            })

    return rx.box(
        rx.recharts.line_chart(
            # Data
            *[
                # Warning threshold area (if exists)
                rx.recharts.reference_area(
                    y1=warning_high if warning_high else max_val,
                    y2=max_val,
                    fill="#f59e0b",
                    fill_opacity=0.12,
                    if_false_render=True
                ) if warning_high else rx.fragment(),

                # Critical threshold area (top 10% of range)
                rx.recharts.reference_area(
                    y1=max_val * 0.9,
                    y2=max_val,
                    fill="#ef4444",
                    fill_opacity=0.18,
                    if_false_render=True
                ),

                # Main line
                rx.recharts.line(
                    data_key="value",
                    stroke=line_color,
                    stroke_width=2,
                    dot=False,
                    connect_nulls=False,  # Break line at null values
                    is_animation_active=False,
                    type_="monotone"
                ),

                # Last point marker (if data exists)
                rx.recharts.line(
                    data_key="value",
                    stroke="none",
                    dot={
                        "r": 3,
                        "fill": line_color,
                        "stroke": "white",
                        "strokeWidth": 2
                    },
                    is_animation_active=False,
                    data=[processed_data[-1]] if processed_data else []
                ) if processed_data else rx.fragment(),

                # Y-axis (hidden but sets domain)
                rx.recharts.y_axis(
                    domain=[min_val, max_val],
                    hide=True
                ),

                # X-axis (hidden)
                rx.recharts.x_axis(
                    data_key="time",
                    hide=True
                ),
            ],
            data=processed_data,
            width=width,
            height=height,
            margin={"top": 2, "right": 2, "bottom": 2, "left": 2}
        ),
        width=f"{width}px",
        height=f"{height}px",
        border_radius="4px",
        border=f"1px solid {line_color}",
        overflow="hidden",
        background="#f9fafb"
    )


def sparkline_simple(
    data: List[Dict],
    status: int = 0,
    width: int = 250,
    height: int = 48
) -> rx.Component:
    """Simplified sparkline for quick use

    Args:
        data: List of {"time": str, "value": float|None}
        status: 0=normal, 1=warning, 2=critical
        width: Chart width
        height: Chart height

    Returns:
        Simple sparkline chart
    """
    # Status color
    if status == 0:
        line_color = "#3b82f6"
    elif status == 1:
        line_color = "#f59e0b"
    else:
        line_color = "#ef4444"

    return rx.box(
        rx.recharts.line_chart(
            rx.recharts.line(
                data_key="value",
                stroke=line_color,
                stroke_width=2,
                dot=False,
                connect_nulls=False,
                is_animation_active=False
            ),
            rx.recharts.y_axis(hide=True),
            rx.recharts.x_axis(data_key="time", hide=True),
            data=data,
            width=width,
            height=height,
            margin={"top": 2, "right": 2, "bottom": 2, "left": 2}
        ),
        width=f"{width}px",
        height=f"{height}px",
        border_radius="4px",
        border=f"1px solid {line_color}",
        background="#f9fafb"
    )
