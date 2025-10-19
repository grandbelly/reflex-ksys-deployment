"""Page header component"""
import reflex as rx


def page_header(
    title: str,
    subtitle: str = "",
    icon: str = "activity"
) -> rx.Component:
    """
    Page header with title, subtitle, and icon

    Args:
        title: Main heading text
        subtitle: Secondary description text
        icon: Lucide icon name

    Returns:
        Styled header component
    """
    return rx.box(
        rx.hstack(
            rx.icon(
                icon,
                size=32,
                color=rx.color("slate", 12),
            ),
            rx.vstack(
                rx.heading(
                    title,
                    size="7",
                    weight="bold",
                    color=rx.color("slate", 12),
                ),
                rx.cond(
                    subtitle != "",
                    rx.text(
                        subtitle,
                        size="3",
                        color=rx.color("slate", 11),
                    ),
                ),
                spacing="1",
                align_items="start",
            ),
            spacing="4",
            align_items="center",
        ),
        padding="6",
        border_bottom=f"1px solid {rx.color('slate', 6)}",
        bg=rx.color("slate", 2),
    )
