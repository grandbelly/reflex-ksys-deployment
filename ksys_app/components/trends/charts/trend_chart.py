"""Trend chart component using recharts"""
import reflex as rx


def trend_chart(
    data: rx.Var,
    mode: str = "line",  # line, area, bar, scatter
    x_key: str = "timestamp",
    y_keys: list[str] = None,
    colors: list[str] = None,
    show_grid: bool = True,
    show_legend: bool = True,
    show_tooltip: bool = True,
) -> rx.Component:
    """
    Flexible trend chart supporting multiple visualization modes

    Args:
        data: Chart data (list of dicts)
        mode: Chart type (line, area, bar, scatter)
        x_key: X-axis data key
        y_keys: Y-axis data keys (for multiple series)
        colors: Colors for each series
        show_grid: Display grid lines
        show_legend: Display legend
        show_tooltip: Display tooltip

    Returns:
        Recharts component
    """
    if y_keys is None:
        y_keys = ["value"]

    if colors is None:
        colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]

    # Common chart properties
    chart_props = {
        "data": data,
        "width": "100%",
        "height": "100%",
    }

    # Create chart based on mode
    if mode == "line":
        chart = rx.recharts.line_chart(
            *[
                rx.recharts.line(
                    data_key=key,
                    stroke=colors[i % len(colors)],
                    stroke_width=2,
                )
                for i, key in enumerate(y_keys)
            ],
            rx.recharts.x_axis(
                data_key=x_key,
                stroke=rx.color("slate", 8),
            ),
            rx.recharts.y_axis(
                stroke=rx.color("slate", 8),
            ),
            rx.cond(
                show_grid,
                rx.recharts.cartesian_grid(
                    stroke_dasharray="3 3",
                    stroke=rx.color("slate", 6),
                ),
            ),
            rx.cond(
                show_tooltip,
                rx.recharts.tooltip(
                    content_style={
                        "backgroundColor": rx.color("slate", 2),
                        "border": f"1px solid {rx.color('slate', 6)}",
                        "borderRadius": "6px",
                    },
                ),
            ),
            rx.cond(
                show_legend,
                rx.recharts.legend(),
            ),
            **chart_props,
        )

    elif mode == "area":
        chart = rx.recharts.area_chart(
            *[
                rx.recharts.area(
                    data_key=key,
                    stroke=colors[i % len(colors)],
                    fill=colors[i % len(colors)],
                    fill_opacity=0.3,
                )
                for i, key in enumerate(y_keys)
            ],
            rx.recharts.x_axis(
                data_key=x_key,
                stroke=rx.color("slate", 8),
            ),
            rx.recharts.y_axis(
                stroke=rx.color("slate", 8),
            ),
            rx.cond(
                show_grid,
                rx.recharts.cartesian_grid(
                    stroke_dasharray="3 3",
                    stroke=rx.color("slate", 6),
                ),
            ),
            rx.cond(
                show_tooltip,
                rx.recharts.tooltip(),
            ),
            rx.cond(
                show_legend,
                rx.recharts.legend(),
            ),
            **chart_props,
        )

    elif mode == "bar":
        chart = rx.recharts.bar_chart(
            *[
                rx.recharts.bar(
                    data_key=key,
                    fill=colors[i % len(colors)],
                )
                for i, key in enumerate(y_keys)
            ],
            rx.recharts.x_axis(
                data_key=x_key,
                stroke=rx.color("slate", 8),
            ),
            rx.recharts.y_axis(
                stroke=rx.color("slate", 8),
            ),
            rx.cond(
                show_grid,
                rx.recharts.cartesian_grid(
                    stroke_dasharray="3 3",
                    stroke=rx.color("slate", 6),
                ),
            ),
            rx.cond(
                show_tooltip,
                rx.recharts.tooltip(),
            ),
            rx.cond(
                show_legend,
                rx.recharts.legend(),
            ),
            **chart_props,
        )

    elif mode == "scatter":
        chart = rx.recharts.scatter_chart(
            *[
                rx.recharts.scatter(
                    data_key=key,
                    fill=colors[i % len(colors)],
                )
                for i, key in enumerate(y_keys)
            ],
            rx.recharts.x_axis(
                data_key=x_key,
                stroke=rx.color("slate", 8),
            ),
            rx.recharts.y_axis(
                stroke=rx.color("slate", 8),
            ),
            rx.cond(
                show_grid,
                rx.recharts.cartesian_grid(
                    stroke_dasharray="3 3",
                    stroke=rx.color("slate", 6),
                ),
            ),
            rx.cond(
                show_tooltip,
                rx.recharts.tooltip(),
            ),
            rx.cond(
                show_legend,
                rx.recharts.legend(),
            ),
            **chart_props,
        )

    else:
        chart = rx.text("Invalid chart mode", color="red")

    return chart
