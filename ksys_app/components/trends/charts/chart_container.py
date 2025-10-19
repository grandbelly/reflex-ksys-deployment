"""Chart container component"""
import reflex as rx


def chart_container(
    title: str,
    subtitle: str = "",
    children: rx.Component = None,
    actions: list[rx.Component] = None,
    height: str = "400px",
) -> rx.Component:
    """
    Container for charts with title, subtitle, and optional action buttons

    Args:
        title: Chart title
        subtitle: Chart description (optional)
        children: Chart component
        actions: Action buttons (download, fullscreen, etc.)
        height: Chart container height

    Returns:
        Styled chart container
    """
    header_content = [
        rx.vstack(
            rx.heading(
                title,
                size="4",
                weight="medium",
                color=rx.color("slate", 12),
            ),
            rx.cond(
                subtitle != "",
                rx.text(
                    subtitle,
                    size="2",
                    color=rx.color("slate", 10),
                ),
            ),
            spacing="1",
            align_items="start",
        ),
    ]

    if actions:
        header_content.append(
            rx.hstack(
                *actions,
                spacing="2",
            )
        )

    return rx.card(
        rx.vstack(
            # Header
            rx.hstack(
                *header_content,
                justify="between",
                width="100%",
            ),
            # Chart content
            rx.box(
                children,
                width="100%",
                height=height,
                class_name="chart-container",
            ),
            spacing="4",
            width="100%",
        ),
        padding="4",
        bg=rx.color("slate", 2),
        border=f"1px solid {rx.color('slate', 6)}",
    )
