"""Chart mode selector component"""
import reflex as rx


def chart_mode_selector(
    selected_mode: rx.Var,
    on_change,
) -> rx.Component:
    """
    Chart visualization mode selector (line, area, bar, etc.)

    Args:
        selected_mode: State variable for selected chart mode
        on_change: Handler function for mode changes

    Returns:
        Chart mode selector component
    """
    modes = [
        {"value": "line", "icon": "line-chart", "label": "Line"},
        {"value": "area", "icon": "area-chart", "label": "Area"},
        {"value": "bar", "icon": "bar-chart", "label": "Bar"},
        {"value": "scatter", "icon": "scatter-chart", "label": "Scatter"},
    ]

    return rx.vstack(
        rx.text(
            "Chart Mode",
            size="2",
            weight="medium",
            color=rx.color("slate", 12),
        ),
        rx.flex(
            *[
                rx.button(
                    rx.hstack(
                        rx.icon(mode["icon"], size=16),
                        rx.text(mode["label"], size="2"),
                        spacing="2",
                    ),
                    variant=rx.cond(
                        selected_mode == mode["value"],
                        "solid",
                        "soft"
                    ),
                    color_scheme=rx.cond(
                        selected_mode == mode["value"],
                        "blue",
                        "gray"
                    ),
                    on_click=lambda v=mode["value"]: on_change(v),
                    size="2",
                )
                for mode in modes
            ],
            wrap="wrap",
            spacing="2",
            width="100%",
        ),
        spacing="2",
        width="100%",
    )
