"""Tag selector component"""
import reflex as rx


def tag_selector(
    selected_tags: rx.Var,
    on_change,
    tag_options: list[str],
    placeholder: str = "Select tags",
    max_selections: int = 5,
) -> rx.Component:
    """
    Multi-select component for sensor tags

    Args:
        selected_tags: State variable for selected tags
        on_change: Handler function for selection changes
        tag_options: Available tag options
        placeholder: Placeholder text
        max_selections: Maximum number of selectable tags

    Returns:
        Tag selector component
    """
    return rx.vstack(
        rx.hstack(
            rx.text(
                "Sensor Tags",
                size="2",
                weight="medium",
                color=rx.color("slate", 12),
            ),
            rx.badge(
                f"{len(selected_tags)}/{max_selections}",
                color_scheme="blue",
                variant="soft",
            ),
            spacing="2",
        ),
        rx.select(
            tag_options,
            placeholder=placeholder,
            value=selected_tags[0] if len(selected_tags) > 0 else "",
            on_change=on_change,
            size="2",
            variant="soft",
        ),
        rx.flex(
            rx.foreach(
                selected_tags,
                lambda tag: rx.badge(
                    rx.hstack(
                        rx.text(tag, size="1"),
                        rx.icon(
                            "x",
                            size=12,
                            cursor="pointer",
                            on_click=lambda: on_change(tag, remove=True),
                        ),
                        spacing="1",
                    ),
                    color_scheme="blue",
                    variant="soft",
                ),
            ),
            wrap="wrap",
            spacing="2",
        ),
        spacing="2",
        width="100%",
    )
