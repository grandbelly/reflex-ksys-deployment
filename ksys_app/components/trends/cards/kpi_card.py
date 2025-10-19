"""KPI card component"""
import reflex as rx


def kpi_card(
    label: str,
    value: rx.Var | str,
    unit: str = "",
    icon: str = "",
    status: str = "normal",  # normal, warning, critical
    trend: str = "",  # up, down, neutral
    trend_value: str = "",
) -> rx.Component:
    """
    KPI card with value, label, status indicator, and trend

    Args:
        label: KPI description
        value: Main value (can be Var or string)
        unit: Unit of measurement
        icon: Lucide icon name
        status: Status color (normal/warning/critical)
        trend: Trend direction (up/down/neutral)
        trend_value: Trend percentage or value

    Returns:
        Styled KPI card component
    """
    # Status color mapping
    status_colors = {
        "normal": "green",
        "warning": "yellow",
        "critical": "red",
    }
    status_color = status_colors.get(status, "green")

    # Trend icon mapping
    trend_icons = {
        "up": "trending-up",
        "down": "trending-down",
        "neutral": "minus",
    }
    trend_icon = trend_icons.get(trend, "")

    return rx.card(
        rx.vstack(
            # Header with icon and label
            rx.hstack(
                rx.cond(
                    icon != "",
                    rx.icon(
                        icon,
                        size=20,
                        color=rx.color(status_color, 9),
                    ),
                ),
                rx.text(
                    label,
                    size="2",
                    weight="medium",
                    color=rx.color("slate", 11),
                ),
                justify="between",
                width="100%",
            ),
            # Value section
            rx.hstack(
                rx.text(
                    value,
                    size="6",
                    weight="bold",
                    color=rx.color("slate", 12),
                ),
                rx.cond(
                    unit != "",
                    rx.text(
                        unit,
                        size="3",
                        color=rx.color("slate", 10),
                    ),
                ),
                spacing="2",
                align_items="baseline",
            ),
            # Trend indicator (if provided)
            rx.cond(
                trend != "",
                rx.hstack(
                    rx.icon(
                        trend_icon,
                        size=16,
                        color=rx.color(
                            rx.cond(
                                trend == "up",
                                "green",
                                rx.cond(trend == "down", "red", "gray")
                            ),
                            9
                        ),
                    ),
                    rx.text(
                        trend_value,
                        size="2",
                        color=rx.color("slate", 10),
                    ),
                    spacing="1",
                ),
            ),
            spacing="3",
            align_items="start",
            width="100%",
        ),
        class_name="card-hover",
        padding="4",
        bg=rx.color("slate", 3),
        border=f"1px solid {rx.color('slate', 6)}",
    )
