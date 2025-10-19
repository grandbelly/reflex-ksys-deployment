"""
Design System Components
Standardized, reusable UI components following design tokens
"""

import reflex as rx
from typing import Optional, List, Any, Union
from .tokens import DesignTokens as tokens


class DesignSystem:
    """Unified design system components"""

    @staticmethod
    def card(
        *children,
        title: Optional[str] = None,
        icon: Optional[str] = None,
        variant: str = "default",
        **kwargs
    ) -> rx.Component:
        """
        Standardized Card component

        Args:
            children: Card content
            title: Optional card title
            icon: Optional icon name (Lucide)
            variant: Card style variant (default, metric, alert, interactive)
            **kwargs: Additional Reflex props
        """
        # Variant styles
        variants = {
            "default": {
                "bg": "white",
                "border": f"1px solid {tokens.COLORS['gray']['200']}",
                "box_shadow": tokens.SHADOWS["sm"],
            },
            "metric": {
                "bg": "white",
                "border": "none",
                "box_shadow": tokens.SHADOWS["md"],
                "padding": tokens.SPACING["6"],
            },
            "alert": {
                "bg": tokens.COLORS["red"]["50"],
                "border": f"1px solid {tokens.COLORS['red']['200']}",
                "box_shadow": tokens.SHADOWS["sm"],
            },
            "interactive": {
                "bg": "white",
                "border": f"1px solid {tokens.COLORS['gray']['200']}",
                "box_shadow": tokens.SHADOWS["sm"],
                "_hover": {
                    "box_shadow": tokens.SHADOWS["md"],
                    "border_color": tokens.COLORS["primary"]["400"],
                }
            },
            "elevated": {
                "bg": "white",
                "border": "none",
                "box_shadow": tokens.SHADOWS["lg"],
            }
        }

        style = variants.get(variant, variants["default"])

        # Build header if title or icon provided
        header = None
        if title or icon:
            header = rx.hstack(
                rx.cond(
                    icon,
                    rx.icon(
                        icon,
                        size=20,
                        color=tokens.COLORS["gray"]["600"]
                    ),
                    rx.box()
                ),
                rx.cond(
                    title,
                    rx.text(
                        title,
                        font_size=tokens.FONT_SIZE["lg"],
                        font_weight=tokens.FONT_WEIGHT["semibold"],
                        color=tokens.COLORS["gray"]["800"]
                    ),
                    rx.box()
                ),
                width="100%",
                justify="start",
                spacing=tokens.SPACING["3"],
                margin_bottom=tokens.SPACING["4"]
            )

        return rx.box(
            rx.vstack(
                rx.cond(
                    header is not None,
                    header,
                    rx.box()
                ),
                *children,
                width="100%",
                align="start",
                spacing=tokens.SPACING["4"]
            ),
            padding=tokens.SPACING["5"],
            border_radius=tokens.BORDER_RADIUS["lg"],
            width="100%",
            transition=f"all {tokens.TRANSITIONS['normal']}",
            **style,
            **kwargs
        )

    @staticmethod
    def metric_card(
        label: str,
        value: Union[str, int, float],
        change: Optional[float] = None,
        icon: Optional[str] = None,
        unit: Optional[str] = None,
        **kwargs
    ) -> rx.Component:
        """
        Standardized metric/KPI card

        Args:
            label: Metric label
            value: Metric value
            change: Optional percentage change
            icon: Optional icon
            unit: Optional unit suffix (e.g., '%', 'MW')
        """
        # Format value
        if isinstance(value, (int, float)):
            formatted_value = f"{value:,.0f}" if isinstance(value, int) else f"{value:,.2f}"
        else:
            formatted_value = str(value)

        if unit:
            formatted_value = f"{formatted_value} {unit}"

        return DesignSystem.card(
            rx.vstack(
                # Header with label and icon
                rx.hstack(
                    rx.text(
                        label,
                        font_size=tokens.FONT_SIZE["sm"],
                        color=tokens.COLORS["gray"]["600"],
                        font_weight=tokens.FONT_WEIGHT["medium"]
                    ),
                    rx.spacer(),
                    rx.cond(
                        icon,
                        rx.icon(
                            icon,
                            size=16,
                            color=tokens.COLORS["gray"]["400"]
                        ),
                        rx.box()
                    ),
                    width="100%"
                ),
                # Value
                rx.text(
                    formatted_value,
                    font_size=tokens.FONT_SIZE["3xl"],
                    font_weight=tokens.FONT_WEIGHT["bold"],
                    color=tokens.COLORS["gray"]["900"]
                ),
                # Change indicator
                rx.cond(
                    change is not None,
                    rx.hstack(
                        rx.icon(
                            rx.cond(
                                change >= 0,
                                "trending-up",
                                "trending-down"
                            ),
                            size=16,
                            color=rx.cond(
                                change >= 0,
                                tokens.SEMANTIC["success"],
                                tokens.SEMANTIC["error"]
                            )
                        ),
                        rx.text(
                            f"{abs(change):.1f}%",
                            font_size=tokens.FONT_SIZE["sm"],
                            color=rx.cond(
                                change >= 0,
                                tokens.COLORS["green"]["600"],
                                tokens.COLORS["red"]["600"]
                            ),
                            font_weight=tokens.FONT_WEIGHT["medium"]
                        ),
                        spacing=tokens.SPACING["1"]
                    ),
                    rx.box()
                ),
                spacing=tokens.SPACING["2"],
                align="start",
                width="100%"
            ),
            variant="metric",
            **kwargs
        )

    @staticmethod
    def button(
        text: str,
        variant: str = "primary",
        size: str = "md",
        icon: Optional[str] = None,
        icon_position: str = "left",
        **kwargs
    ) -> rx.Component:
        """
        Standardized button component

        Args:
            text: Button text
            variant: Style variant (primary, secondary, ghost, danger, outline)
            size: Size variant (sm, md, lg)
            icon: Optional icon name
            icon_position: Icon position (left, right)
        """
        # Size styles
        sizes = {
            "sm": {
                "padding_x": tokens.SPACING["3"],
                "padding_y": tokens.SPACING["2"],
                "font_size": tokens.FONT_SIZE["sm"]
            },
            "md": {
                "padding_x": tokens.SPACING["4"],
                "padding_y": tokens.SPACING["2.5"],
                "font_size": tokens.FONT_SIZE["md"]
            },
            "lg": {
                "padding_x": tokens.SPACING["6"],
                "padding_y": tokens.SPACING["3"],
                "font_size": tokens.FONT_SIZE["lg"]
            }
        }

        # Variant styles
        variants = {
            "primary": {
                "bg": tokens.COLORS["primary"]["500"],
                "color": "white",
                "_hover": {"bg": tokens.COLORS["primary"]["600"]},
                "_active": {"bg": tokens.COLORS["primary"]["700"]}
            },
            "secondary": {
                "bg": tokens.COLORS["gray"]["100"],
                "color": tokens.COLORS["gray"]["700"],
                "_hover": {"bg": tokens.COLORS["gray"]["200"]},
                "_active": {"bg": tokens.COLORS["gray"]["300"]}
            },
            "ghost": {
                "bg": "transparent",
                "color": tokens.COLORS["gray"]["600"],
                "_hover": {"bg": tokens.COLORS["gray"]["100"]},
                "_active": {"bg": tokens.COLORS["gray"]["200"]}
            },
            "danger": {
                "bg": tokens.COLORS["red"]["500"],
                "color": "white",
                "_hover": {"bg": tokens.COLORS["red"]["600"]},
                "_active": {"bg": tokens.COLORS["red"]["700"]}
            },
            "outline": {
                "bg": "transparent",
                "color": tokens.COLORS["primary"]["600"],
                "border": f"1px solid {tokens.COLORS['primary']['300']}",
                "_hover": {
                    "bg": tokens.COLORS["primary"]["50"],
                    "border_color": tokens.COLORS["primary"]["400"]
                }
            }
        }

        size_style = sizes.get(size, sizes["md"])
        variant_style = variants.get(variant, variants["primary"])

        # Build button content with icon
        if icon and icon_position == "left":
            content = rx.hstack(
                rx.icon(icon, size=16),
                rx.text(text),
                spacing=tokens.SPACING["2"]
            )
        elif icon and icon_position == "right":
            content = rx.hstack(
                rx.text(text),
                rx.icon(icon, size=16),
                spacing=tokens.SPACING["2"]
            )
        else:
            content = rx.text(text)

        return rx.button(
            content,
            border_radius=tokens.BORDER_RADIUS["md"],
            font_weight=tokens.FONT_WEIGHT["medium"],
            transition=f"all {tokens.TRANSITIONS['fast']}",
            cursor="pointer",
            **size_style,
            **variant_style,
            **kwargs
        )

    @staticmethod
    def heading(
        text: str,
        level: int = 1,
        **kwargs
    ) -> rx.Component:
        """
        Standardized heading component

        Args:
            text: Heading text
            level: Heading level (1-6)
        """
        styles = {
            1: {
                "font_size": tokens.FONT_SIZE["4xl"],
                "font_weight": tokens.FONT_WEIGHT["bold"],
                "color": tokens.COLORS["gray"]["900"]
            },
            2: {
                "font_size": tokens.FONT_SIZE["3xl"],
                "font_weight": tokens.FONT_WEIGHT["bold"],
                "color": tokens.COLORS["gray"]["900"]
            },
            3: {
                "font_size": tokens.FONT_SIZE["2xl"],
                "font_weight": tokens.FONT_WEIGHT["semibold"],
                "color": tokens.COLORS["gray"]["800"]
            },
            4: {
                "font_size": tokens.FONT_SIZE["xl"],
                "font_weight": tokens.FONT_WEIGHT["semibold"],
                "color": tokens.COLORS["gray"]["800"]
            },
            5: {
                "font_size": tokens.FONT_SIZE["lg"],
                "font_weight": tokens.FONT_WEIGHT["medium"],
                "color": tokens.COLORS["gray"]["700"]
            },
            6: {
                "font_size": tokens.FONT_SIZE["md"],
                "font_weight": tokens.FONT_WEIGHT["medium"],
                "color": tokens.COLORS["gray"]["700"]
            }
        }

        style = styles.get(level, styles[1])

        return rx.heading(
            text,
            as_=f"h{level}",
            line_height=tokens.LINE_HEIGHT["tight"],
            **style,
            **kwargs
        )

    @staticmethod
    def badge(
        text: str,
        variant: str = "default",
        **kwargs
    ) -> rx.Component:
        """
        Standardized badge component

        Args:
            text: Badge text
            variant: Style variant (default, success, warning, error, info)
        """
        variants = {
            "default": {
                "bg": tokens.COLORS["gray"]["100"],
                "color": tokens.COLORS["gray"]["800"]
            },
            "success": {
                "bg": tokens.COLORS["green"]["100"],
                "color": tokens.COLORS["green"]["800"]
            },
            "warning": {
                "bg": tokens.COLORS["amber"]["100"],
                "color": tokens.COLORS["amber"]["800"]
            },
            "error": {
                "bg": tokens.COLORS["red"]["100"],
                "color": tokens.COLORS["red"]["800"]
            },
            "info": {
                "bg": tokens.COLORS["primary"]["100"],
                "color": tokens.COLORS["primary"]["800"]
            }
        }

        style = variants.get(variant, variants["default"])

        return rx.badge(
            text,
            padding_x=tokens.SPACING["2.5"],
            padding_y=tokens.SPACING["0.5"],
            border_radius=tokens.BORDER_RADIUS["md"],
            font_size=tokens.FONT_SIZE["xs"],
            font_weight=tokens.FONT_WEIGHT["medium"],
            **style,
            **kwargs
        )

    @staticmethod
    def divider(**kwargs) -> rx.Component:
        """Standardized divider"""
        return rx.divider(
            border_color=tokens.COLORS["gray"]["200"],
            **kwargs
        )

    @staticmethod
    def skeleton(
        height: str = "20px",
        **kwargs
    ) -> rx.Component:
        """Loading skeleton"""
        return rx.skeleton(
            height=height,
            border_radius=tokens.BORDER_RADIUS["md"],
            **kwargs
        )

    @staticmethod
    def alert(
        title: str,
        description: Optional[str] = None,
        status: str = "info",
        **kwargs
    ) -> rx.Component:
        """
        Standardized alert component

        Args:
            title: Alert title
            description: Optional description
            status: Alert status (info, success, warning, error)
        """
        status_config = {
            "info": {
                "bg": tokens.COLORS["primary"]["50"],
                "border": tokens.COLORS["primary"]["200"],
                "icon": "info",
                "icon_color": tokens.COLORS["primary"]["500"]
            },
            "success": {
                "bg": tokens.COLORS["green"]["50"],
                "border": tokens.COLORS["green"]["200"],
                "icon": "circle-check",
                "icon_color": tokens.COLORS["green"]["500"]
            },
            "warning": {
                "bg": tokens.COLORS["amber"]["50"],
                "border": tokens.COLORS["amber"]["200"],
                "icon": "triangle-alert",
                "icon_color": tokens.COLORS["amber"]["500"]
            },
            "error": {
                "bg": tokens.COLORS["red"]["50"],
                "border": tokens.COLORS["red"]["200"],
                "icon": "circle-alert",
                "icon_color": tokens.COLORS["red"]["500"]
            }
        }

        config = status_config.get(status, status_config["info"])

        return rx.box(
            rx.hstack(
                rx.icon(
                    config["icon"],
                    size=20,
                    color=config["icon_color"]
                ),
                rx.vstack(
                    rx.text(
                        title,
                        font_weight=tokens.FONT_WEIGHT["semibold"],
                        font_size=tokens.FONT_SIZE["sm"],
                        color=tokens.COLORS["gray"]["900"]
                    ),
                    rx.cond(
                        description,
                        rx.text(
                            description,
                            font_size=tokens.FONT_SIZE["sm"],
                            color=tokens.COLORS["gray"]["700"]
                        ),
                        rx.box()
                    ),
                    align="start",
                    spacing=tokens.SPACING["1"],
                    flex="1"
                ),
                spacing=tokens.SPACING["3"],
                align="start"
            ),
            bg=config["bg"],
            border=f"1px solid {config['border']}",
            border_radius=tokens.BORDER_RADIUS["md"],
            padding=tokens.SPACING["4"],
            **kwargs
        )
