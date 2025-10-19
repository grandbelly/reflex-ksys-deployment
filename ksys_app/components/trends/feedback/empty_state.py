"""Empty state component"""
import reflex as rx


def empty_state(
    title: str = "No data available",
    description: str = "Try selecting different filters or time range",
    icon: str = "database",
    action_label: str = "",
    on_action = None,
) -> rx.Component:
    """
    Empty state with icon, message, and optional action

    Args:
        title: Main message
        description: Helpful description
        icon: Lucide icon name
        action_label: Action button text (optional)
        on_action: Action button handler (optional)

    Returns:
        Empty state component
    """
    content = [
        rx.icon(
            icon,
            size=48,
            color=rx.color("slate", 8),
        ),
        rx.vstack(
            rx.heading(
                title,
                size="4",
                weight="medium",
                color=rx.color("slate", 11),
            ),
            rx.text(
                description,
                size="2",
                color=rx.color("slate", 9),
                text_align="center",
            ),
            spacing="2",
            align="center",
        ),
    ]

    if action_label and on_action:
        content.append(
            rx.button(
                action_label,
                on_click=on_action,
                variant="soft",
                size="2",
            )
        )

    return rx.center(
        rx.vstack(
            *content,
            spacing="4",
            align="center",
        ),
        width="100%",
        min_height="300px",
    )
