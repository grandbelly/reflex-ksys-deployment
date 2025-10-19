"""Stat card component"""
import reflex as rx


def stat_card(
    title: str,
    stats: list[dict],  # [{"label": "...", "value": "...", "color": "..."}]
) -> rx.Component:
    """
    Card displaying multiple statistics

    Args:
        title: Card title
        stats: List of stat dictionaries with label, value, and optional color

    Returns:
        Styled stat card component
    """
    return rx.card(
        rx.vstack(
            # Title
            rx.heading(
                title,
                size="4",
                weight="medium",
                color=rx.color("slate", 12),
            ),
            # Stats grid
            rx.vstack(
                *[
                    rx.hstack(
                        rx.text(
                            stat.get("label", ""),
                            size="2",
                            color=rx.color("slate", 11),
                        ),
                        rx.text(
                            stat.get("value", ""),
                            size="3",
                            weight="bold",
                            color=rx.color(stat.get("color", "slate"), 12),
                        ),
                        justify="between",
                        width="100%",
                    )
                    for stat in stats
                ],
                spacing="3",
                width="100%",
            ),
            spacing="4",
            align_items="start",
            width="100%",
        ),
        class_name="card-hover",
        padding="4",
        bg=rx.color("slate", 3),
        border=f"1px solid {rx.color('slate', 6)}",
    )
