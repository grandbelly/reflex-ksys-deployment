"""Loading state component"""
import reflex as rx


def loading_state(
    message: str = "Loading data...",
    size: str = "3",
) -> rx.Component:
    """
    Loading indicator with optional message

    Args:
        message: Loading message
        size: Spinner size

    Returns:
        Loading component
    """
    return rx.center(
        rx.vstack(
            rx.spinner(
                size=size,
                color=rx.color("blue", 9),
            ),
            rx.text(
                message,
                size="2",
                color=rx.color("slate", 10),
            ),
            spacing="3",
            align="center",
        ),
        width="100%",
        min_height="200px",
    )
