"""Manufacturing Dashboard Style KPI Cards - Dark Theme"""
import reflex as rx


def kpi_card(
    title: str,
    value: rx.Var | str,
    icon: str,
    status: str = "normal",
    trend: str | None = None,
    change: str | None = None,
) -> rx.Component:
    """
    Manufacturing Dashboard Style KPI Card with gradient background.

    Args:
        title: Card title
        value: Main value to display
        icon: Lucide icon name
        status: Status color - "normal", "warning", "critical"
        trend: Trend direction - "up", "down", "stable"
        change: Change percentage text (e.g., "+2.5%")
    """

    # Status-based gradient colors
    status_colors = {
        "normal": "from-green-500 to-emerald-600",
        "warning": "from-yellow-500 to-orange-600",
        "critical": "from-red-500 to-pink-600",
    }

    # Trend icons and colors
    trend_icons = {
        "up": ("trending-up", "text-green-400"),
        "down": ("trending-down", "text-red-400"),
        "stable": ("minus", "text-slate-400"),
    }

    gradient = status_colors.get(status, status_colors["normal"])

    # Build trend indicator if provided
    trend_indicator = None
    if trend and change:
        trend_icon, trend_color = trend_icons.get(trend, trend_icons["stable"])
        trend_indicator = rx.hstack(
            rx.icon(trend_icon, size=16, class_name=trend_color),
            rx.text(change, size="2", class_name=trend_color),
            spacing="1",
            align="center",
        )

    return rx.box(
        # Icon with gradient background
        rx.hstack(
            rx.box(
                rx.icon(icon, size=24, color="white"),
                class_name=f"p-3 rounded-lg bg-gradient-to-br {gradient}",
            ),
            trend_indicator or rx.fragment(),
            justify="between",
            align="center",
            class_name="mb-4",
        ),
        # Value
        rx.text(
            value,
            size="8",
            weight="bold",
            class_name="text-white mb-2",
        ),
        # Title
        rx.text(
            title,
            size="2",
            class_name="text-slate-400",
        ),
        class_name="bg-slate-800 rounded-xl p-5 border border-slate-700 hover:border-slate-600 transition-all duration-200",
    )


def metric_card(
    title: str,
    value: rx.Var | str,
    icon: str,
    subtitle: str | None = None,
    color: str = "blue",
) -> rx.Component:
    """
    Simpler metric card variant.

    Args:
        title: Card title
        value: Main value to display
        icon: Lucide icon name
        subtitle: Optional subtitle text
        color: Accent color - "blue", "green", "red", "yellow"
    """

    color_classes = {
        "blue": "text-blue-400",
        "green": "text-green-400",
        "red": "text-red-400",
        "yellow": "text-yellow-400",
    }

    icon_color = color_classes.get(color, color_classes["blue"])

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=20, class_name=icon_color),
                rx.text(title, size="2", class_name="text-slate-400"),
                spacing="2",
                align="center",
            ),
            rx.text(
                value,
                size="7",
                weight="bold",
                class_name="text-white",
            ),
            rx.cond(
                subtitle,
                rx.text(subtitle, size="1", class_name="text-slate-500"),
                rx.fragment(),
            ),
            spacing="2",
            align="start",
        ),
        class_name="bg-slate-800 rounded-lg p-4 border border-slate-700",
    )
