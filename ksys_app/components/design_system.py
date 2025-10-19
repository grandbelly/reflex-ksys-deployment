"""
SalesX Design System Components
Reflex implementation of the SalesX design system with purple theme
"""
import reflex as rx
from typing import List, Dict, Optional, Any

# ============================================================================
# COLOR PALETTE
# ============================================================================

COLORS = {
    # Primary Colors
    "brand_purple": "#6366F1",
    "purple_light": "#818CF8",
    "purple_dark": "#4F46E5",

    # Secondary Colors
    "orange": "#FB923C",
    "sky_blue": "#38BDF8",
    "green": "#10B981",
    "red": "#EF4444",

    # Neutral Colors
    "gray_900": "#111827",
    "gray_700": "#374151",
    "gray_500": "#6B7280",
    "gray_300": "#D1D5DB",
    "gray_100": "#F3F4F6",
    "gray_50": "#F9FAFB",
    "white": "#FFFFFF",
}


# ============================================================================
# BUTTONS
# ============================================================================

def primary_button(
    text: str,
    on_click=None,
    size: str = "3",
    icon: Optional[str] = None,
    **kwargs
) -> rx.Component:
    """Primary purple button - SalesX style"""
    content = [rx.icon(icon, size=16)] if icon else []
    content.append(text)

    return rx.button(
        *content,
        on_click=on_click,
        color_scheme="purple",
        size=size,
        radius="large",
        **kwargs
    )


def secondary_button(
    text: str,
    on_click=None,
    size: str = "3",
    icon: Optional[str] = None,
    **kwargs
) -> rx.Component:
    """Secondary outline button - SalesX style"""
    content = [rx.icon(icon, size=16)] if icon else []
    content.append(text)

    return rx.button(
        *content,
        on_click=on_click,
        variant="outline",
        color_scheme="gray",
        size=size,
        radius="large",
        **kwargs
    )


def icon_button(
    icon: str,
    on_click=None,
    variant: str = "soft",
    size: str = "2",
    **kwargs
) -> rx.Component:
    """Icon-only button"""
    return rx.icon_button(
        rx.icon(icon, size=20),
        on_click=on_click,
        variant=variant,
        size=size,
        **kwargs
    )


# ============================================================================
# METRIC CARDS
# ============================================================================

def metric_card(
    icon: str,
    label: str,
    value: Any,
    change_percent: Optional[float] = None,
    change_amount: Optional[Any] = None,
    is_positive: bool = True,
    icon_color: str = "purple"
) -> rx.Component:
    """
    Metric card component - SalesX style

    Args:
        icon: Lucide icon name
        label: Metric label
        value: Main metric value
        change_percent: Percentage change (optional)
        change_amount: Amount change (optional)
        is_positive: Whether change is positive
        icon_color: Icon background color scheme
    """
    return rx.card(
        rx.flex(
            # Icon with colored background
            rx.box(
                rx.icon(icon, size=24, color="white"),
                background=rx.color(icon_color, 9),
                border_radius="8px",
                padding="8px",
                width="40px",
                height="40px",
                display="flex",
                align_items="center",
                justify_content="center",
            ),

            # Content
            rx.vstack(
                # Label
                rx.text(
                    label,
                    color=rx.color("gray", 11),
                    font_size="14px",
                    font_weight="500",
                ),

                # Value and badge
                rx.hstack(
                    rx.text(
                        value,
                        color=rx.color("gray", 12),
                        font_size="36px",
                        font_weight="700",
                        line_height="1",
                    ),
                    rx.cond(
                        change_percent is not None,
                        rx.badge(
                            f"↑ {change_percent}%" if is_positive else f"↓ {change_percent}%",
                            color_scheme="green" if is_positive else "red",
                            variant="soft",
                        ),
                        rx.fragment(),
                    ),
                    align_items="center",
                    spacing="2",
                ),

                # Additional info
                rx.cond(
                    change_amount is not None,
                    rx.text(
                        f"+{change_amount} from last month →" if is_positive else f"{change_amount} from last month →",
                        color=rx.color("gray", 10),
                        font_size="12px",
                    ),
                    rx.fragment(),
                ),

                spacing="2",
                align_items="start",
                width="100%",
            ),

            direction="column",
            spacing="3",
        ),
        size="3",
    )


# ============================================================================
# CONTENT CARDS
# ============================================================================

def content_card(
    title: str,
    *children,
    actions: Optional[rx.Component] = None,
    **kwargs
) -> rx.Component:
    """Generic content card with optional title and actions"""
    header_content = [
        rx.heading(title, size="5", weight="bold"),
    ]

    if actions:
        header = rx.hstack(
            *header_content,
            actions,
            justify="between",
            width="100%",
            padding_bottom="4",
        )
    else:
        header = rx.vstack(*header_content, padding_bottom="2", width="100%", align_items="start")

    return rx.card(
        rx.vstack(
            header,
            *children,
            spacing="4",
            align_items="start",
            width="100%",
        ),
        size="3",
        **kwargs
    )


# ============================================================================
# STATUS BADGES
# ============================================================================

def status_badge(
    text: str,
    status: str = "default",
    **kwargs
) -> rx.Component:
    """
    Status badge component

    Args:
        text: Badge text
        status: One of: "success", "warning", "error", "default"
    """
    color_map = {
        "success": "green",
        "warning": "orange",
        "error": "red",
        "default": "gray",
        "in_stock": "green",
        "out_of_stock": "red",
    }

    color = color_map.get(status.lower(), "gray")

    return rx.badge(
        text,
        color_scheme=color,
        variant="soft",
        **kwargs
    )


# ============================================================================
# STAT BOX (for summaries)
# ============================================================================

def stat_box(
    label: str,
    value: Any,
    change: Optional[float] = None,
    color: str = "purple"
) -> rx.Component:
    """Small stat box for summaries"""
    return rx.vstack(
        rx.text(label, size="1", color=rx.color("gray", 10)),
        rx.heading(str(value), size="6", weight="bold"),
        rx.cond(
            change is not None,
            rx.badge(
                f"↑ {change}%",
                color_scheme=color,
                variant="soft",
            ),
            rx.fragment(),
        ),
        spacing="1",
        align_items="start",
    )


# ============================================================================
# TRAFFIC BAR (for progress visualization)
# ============================================================================

def traffic_bar(
    source: str,
    percentage: int,
    color: str = "purple"
) -> rx.Component:
    """Traffic source progress bar"""
    return rx.hstack(
        rx.hstack(
            rx.box(
                width="12px",
                height="12px",
                border_radius="2px",
                background=rx.color(color, 9),
            ),
            rx.text(source, size="2"),
            spacing="2",
            flex="1",
        ),
        rx.progress(
            value=percentage,
            color_scheme=color,
            width="60%",
        ),
        rx.text(f"{percentage}%", size="1", weight="medium"),
        spacing="3",
        width="100%",
    )


# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================

def sidebar_item(
    icon: str,
    label: str,
    path: str,
    is_active: bool = False,
    on_click=None
) -> rx.Component:
    """Sidebar menu item - purple theme"""
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=20),
            rx.text(label, size="2", weight="medium"),
            spacing="3",
            padding="12px 16px",
            border_radius="8px",
            background=rx.cond(
                is_active,
                rx.color("purple", 3),
                "transparent",
            ),
            color=rx.cond(
                is_active,
                rx.color("purple", 11),
                rx.color("gray", 11),
            ),
            _hover={"background": rx.color("gray", 3)},
            width="100%",
            cursor="pointer",
        ),
        href=path,
        on_click=on_click,
        underline="none",
        width="100%",
    )


# ============================================================================
# TABLE COMPONENTS
# ============================================================================

def data_table(
    title: str,
    columns: List[str],
    data: List[Dict],
    actions: Optional[rx.Component] = None
) -> rx.Component:
    """
    Generic data table component

    Args:
        title: Table title
        columns: List of column names
        data: List of row dictionaries
        actions: Optional action buttons (Sort, Export, etc.)
    """
    return content_card(
        title,
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    *[rx.table.column_header_cell(col) for col in columns]
                ),
            ),
            rx.table.body(
                *[
                    rx.table.row(
                        *[rx.table.cell(str(row.get(col, ""))) for col in columns]
                    )
                    for row in data
                ]
            ),
            variant="surface",
            size="3",
            width="100%",
        ),
        actions=actions
    )


# ============================================================================
# CHARTS (placeholder wrappers for recharts)
# ============================================================================

def line_chart(
    data: List[Dict],
    data_key: str = "value",
    x_axis_key: str = "name",
    height: int = 400,
    color: str = "purple"
) -> rx.Component:
    """Simple line chart wrapper"""
    return rx.recharts.line_chart(
        rx.recharts.line(
            data_key=data_key,
            stroke=rx.color(color, 9),
            stroke_width=2,
        ),
        rx.recharts.x_axis(data_key=x_axis_key),
        rx.recharts.y_axis(),
        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
        data=data,
        height=height,
        width="100%",
    )


def bar_chart(
    data: List[Dict],
    data_key: str = "value",
    x_axis_key: str = "name",
    height: int = 300,
    color: str = "purple"
) -> rx.Component:
    """Simple bar chart wrapper"""
    return rx.recharts.bar_chart(
        rx.recharts.bar(
            data_key=data_key,
            fill=rx.color(color, 9),
        ),
        rx.recharts.x_axis(data_key=x_axis_key),
        rx.recharts.y_axis(),
        data=data,
        height=height,
        width="100%",
    )


# ============================================================================
# INPUT COMPONENTS
# ============================================================================

def search_input(
    placeholder: str = "Search",
    on_change=None,
    **kwargs
) -> rx.Component:
    """Search input field"""
    return rx.input(
        placeholder=placeholder,
        on_change=on_change,
        size="2",
        width="100%",
        **kwargs
    )


def select_dropdown(
    options: List[str],
    default_value: Optional[str] = None,
    on_change=None,
    size: str = "2",
    **kwargs
) -> rx.Component:
    """Select dropdown"""
    return rx.select(
        options,
        default_value=default_value or options[0] if options else None,
        on_change=on_change,
        size=size,
        **kwargs
    )


# ============================================================================
# LAYOUT HELPERS
# ============================================================================

def metrics_row(*metric_cards) -> rx.Component:
    """4-column responsive metric cards row"""
    return rx.grid(
        *metric_cards,
        columns=["1", "2", "4", "4"],  # mobile, tablet, desktop, large
        spacing="6",
        width="100%",
    )


def two_column_layout(left: rx.Component, right: rx.Component) -> rx.Component:
    """2-column responsive layout (2:1 ratio)"""
    return rx.grid(
        left,
        right,
        columns=["1", "1", "3", "3"],  # Stack on mobile, 2:1 on desktop
        spacing="6",
        width="100%",
    )
