"""Section container component"""
import reflex as rx
from typing import List


def section_container(
    title: str = "",
    children: List[rx.Component] = None,
    **props
) -> rx.Component:
    """
    Container for a section with optional title

    Args:
        title: Section heading (optional)
        children: Child components
        **props: Additional props (padding, spacing, etc.)

    Returns:
        Styled section container
    """
    default_props = {
        "padding": "4",
        "spacing": "4",
    }
    merged_props = {**default_props, **props}

    content = []
    if title:
        content.append(
            rx.heading(
                title,
                size="4",
                weight="medium",
                color=rx.color("slate", 12),
                margin_bottom="3",
            )
        )

    if children:
        content.extend(children if isinstance(children, list) else [children])

    return rx.box(
        rx.vstack(
            *content,
            **merged_props,
        ),
        bg=rx.color("slate", 2),
        border_radius="8px",
        border=f"1px solid {rx.color('slate', 6)}",
    )
