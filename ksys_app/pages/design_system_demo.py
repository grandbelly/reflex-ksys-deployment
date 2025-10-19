"""Design System Demo Page - Showcasing all components"""
import reflex as rx
from ..design_system import DesignSystem, DesignTokens
from ..components.layout import shell


def demo_cards_section() -> rx.Component:
    """Card components demonstration"""
    return rx.vstack(
        DesignSystem.heading("Cards", level=2),

        rx.grid(
            # Default card
            DesignSystem.card(
                rx.text("This is a default card with title and icon"),
                title="Default Card",
                icon="box"
            ),

            # Metric card
            DesignSystem.metric_card(
                label="Total Sensors",
                value=1234,
                change=5.2,
                icon="activity"
            ),

            # Alert card
            DesignSystem.card(
                rx.text("This is an alert card for important warnings"),
                title="Alert",
                icon="triangle-alert",
                variant="alert"
            ),

            # Interactive card
            DesignSystem.card(
                rx.text("This card has hover effects"),
                title="Interactive",
                icon="hand",
                variant="interactive"
            ),

            columns=rx.breakpoints(
                initial="1",
                sm="2",
                md="2",
                lg="4"
            ),
            spacing=DesignTokens.SPACING["4"]
        ),

        spacing=DesignTokens.SPACING["6"],
        width="100%",
        align="start"
    )


def demo_buttons_section() -> rx.Component:
    """Button components demonstration"""
    return rx.vstack(
        DesignSystem.heading("Buttons", level=2),

        # Primary buttons
        rx.hstack(
            DesignSystem.button("Primary", variant="primary"),
            DesignSystem.button("Secondary", variant="secondary"),
            DesignSystem.button("Ghost", variant="ghost"),
            DesignSystem.button("Danger", variant="danger"),
            DesignSystem.button("Outline", variant="outline"),
            spacing=DesignTokens.SPACING["3"]
        ),

        # With icons
        rx.hstack(
            DesignSystem.button(
                "Save",
                variant="primary",
                icon="save",
                icon_position="left"
            ),
            DesignSystem.button(
                "Next",
                variant="primary",
                icon="arrow-right",
                icon_position="right"
            ),
            spacing=DesignTokens.SPACING["3"]
        ),

        # Sizes
        rx.hstack(
            DesignSystem.button("Small", size="sm"),
            DesignSystem.button("Medium", size="md"),
            DesignSystem.button("Large", size="lg"),
            spacing=DesignTokens.SPACING["3"]
        ),

        spacing=DesignTokens.SPACING["6"],
        width="100%",
        align="start"
    )


def demo_typography_section() -> rx.Component:
    """Typography demonstration"""
    return rx.vstack(
        DesignSystem.heading("Typography", level=2),

        DesignSystem.heading("Heading 1", level=1),
        DesignSystem.heading("Heading 2", level=2),
        DesignSystem.heading("Heading 3", level=3),
        DesignSystem.heading("Heading 4", level=4),
        DesignSystem.heading("Heading 5", level=5),
        DesignSystem.heading("Heading 6", level=6),

        rx.text(
            "Body text - Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            font_size=DesignTokens.FONT_SIZE["md"],
            color=DesignTokens.COLORS["gray"]["700"]
        ),

        rx.text(
            "Small text - Helper or secondary information",
            font_size=DesignTokens.FONT_SIZE["sm"],
            color=DesignTokens.COLORS["gray"]["500"]
        ),

        spacing=DesignTokens.SPACING["4"],
        width="100%",
        align="start"
    )


def demo_badges_section() -> rx.Component:
    """Badge components demonstration"""
    return rx.vstack(
        DesignSystem.heading("Badges", level=2),

        rx.hstack(
            DesignSystem.badge("Default", variant="default"),
            DesignSystem.badge("Success", variant="success"),
            DesignSystem.badge("Warning", variant="warning"),
            DesignSystem.badge("Error", variant="error"),
            DesignSystem.badge("Info", variant="info"),
            spacing=DesignTokens.SPACING["2"]
        ),

        spacing=DesignTokens.SPACING["6"],
        width="100%",
        align="start"
    )


def demo_alerts_section() -> rx.Component:
    """Alert components demonstration"""
    return rx.vstack(
        DesignSystem.heading("Alerts", level=2),

        DesignSystem.alert(
            title="Success",
            description="Your changes have been saved successfully",
            status="success"
        ),

        DesignSystem.alert(
            title="Warning",
            description="Database connection is unstable",
            status="warning"
        ),

        DesignSystem.alert(
            title="Error",
            description="Failed to load sensor data",
            status="error"
        ),

        DesignSystem.alert(
            title="Info",
            description="System maintenance scheduled for tomorrow",
            status="info"
        ),

        spacing=DesignTokens.SPACING["4"],
        width="100%",
        align="start"
    )


def demo_colors_section() -> rx.Component:
    """Color palette demonstration"""
    return rx.vstack(
        DesignSystem.heading("Color Palette", level=2),

        # Primary colors
        rx.vstack(
            rx.text("Primary", font_weight=DesignTokens.FONT_WEIGHT["semibold"]),
            rx.hstack(
                *[
                    rx.box(
                        rx.text(
                            shade,
                            font_size=DesignTokens.FONT_SIZE["xs"],
                            color="white" if int(shade) >= 500 else "black"
                        ),
                        bg=DesignTokens.COLORS["primary"][shade],
                        padding=DesignTokens.SPACING["3"],
                        border_radius=DesignTokens.BORDER_RADIUS["md"]
                    )
                    for shade in ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900"]
                ],
                spacing=DesignTokens.SPACING["1"]
            ),
            align="start",
            spacing=DesignTokens.SPACING["2"]
        ),

        # Gray scale
        rx.vstack(
            rx.text("Gray", font_weight=DesignTokens.FONT_WEIGHT["semibold"]),
            rx.hstack(
                *[
                    rx.box(
                        rx.text(
                            shade,
                            font_size=DesignTokens.FONT_SIZE["xs"],
                            color="white" if int(shade) >= 500 else "black"
                        ),
                        bg=DesignTokens.COLORS["gray"][shade],
                        padding=DesignTokens.SPACING["3"],
                        border_radius=DesignTokens.BORDER_RADIUS["md"]
                    )
                    for shade in ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900"]
                ],
                spacing=DesignTokens.SPACING["1"]
            ),
            align="start",
            spacing=DesignTokens.SPACING["2"]
        ),

        spacing=DesignTokens.SPACING["6"],
        width="100%",
        align="start"
    )


@rx.page(
    route="/design-system-demo",
    title="Design System Demo | KSYS"
)
def design_system_demo() -> rx.Component:
    """Design system demonstration page"""
    return shell(
        rx.box(
            rx.vstack(
                # Header
                rx.vstack(
                    DesignSystem.heading("Design System Demo", level=1),
                    rx.text(
                        "Comprehensive showcase of KSYS design system components",
                        font_size=DesignTokens.FONT_SIZE["lg"],
                        color=DesignTokens.COLORS["gray"]["600"]
                    ),
                    spacing=DesignTokens.SPACING["2"],
                    align="start",
                    width="100%"
                ),

                DesignSystem.divider(),

                # Cards
                demo_cards_section(),

                DesignSystem.divider(),

                # Buttons
                demo_buttons_section(),

                DesignSystem.divider(),

                # Typography
                demo_typography_section(),

                DesignSystem.divider(),

                # Badges
                demo_badges_section(),

                DesignSystem.divider(),

                # Alerts
                demo_alerts_section(),

                DesignSystem.divider(),

                # Colors
                demo_colors_section(),

                spacing=DesignTokens.SPACING["8"],
                width="100%",
                align="start"
            ),
            padding=DesignTokens.SPACING["6"],
            max_width="1400px",
            margin="0 auto"
        ),
        active_route="/design-system-demo"
    )
