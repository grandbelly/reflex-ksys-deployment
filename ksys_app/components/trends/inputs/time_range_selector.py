"""Time range selector component"""
import reflex as rx


def time_range_selector(
    selected_range: rx.Var,
    on_change,
    custom_enabled: bool = False,
) -> rx.Component:
    """
    Time range selector with quick presets and custom range option

    Args:
        selected_range: State variable for selected time range
        on_change: Handler function for selection changes
        custom_enabled: Enable custom date picker

    Returns:
        Time range selector component
    """
    time_ranges = [
        "Last Hour",
        "Last 6 Hours",
        "Last 24 Hours",
        "Last 7 Days",
        "Last 30 Days",
        "Custom",
    ]

    return rx.vstack(
        rx.text(
            "Time Range",
            size="2",
            weight="medium",
            color=rx.color("slate", 12),
        ),
        rx.select(
            time_ranges,
            value=selected_range,
            on_change=on_change,
            size="2",
            variant="soft",
        ),
        rx.cond(
            custom_enabled & (selected_range == "Custom"),
            rx.hstack(
                rx.input(
                    type="datetime-local",
                    size="2",
                    placeholder="Start time",
                ),
                rx.text("to", size="2", color=rx.color("slate", 10)),
                rx.input(
                    type="datetime-local",
                    size="2",
                    placeholder="End time",
                ),
                spacing="2",
                width="100%",
            ),
        ),
        spacing="2",
        width="100%",
    )
