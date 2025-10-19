"""Training Wizard - Header Component"""
import reflex as rx
from reflex.utils import console
from ...states.training_wizard_state import TrainingWizardState


def wizard_header() -> rx.Component:
    """Wizard 헤더 - 현재 단계 표시"""
    console.log("DEBUG: wizard_header() called")
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("wand-sparkles", size=28, color=rx.color("purple", 9)),
                rx.vstack(
                    rx.heading("ML Training Wizard", size="5"),
                    rx.text("Follow the steps to train your model", size="2", color="gray"),
                    spacing="1",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
            ),

            rx.divider(),

            # Progress indicator
            rx.hstack(
                # Step 1
                rx.vstack(
                    rx.cond(
                        TrainingWizardState.wizard_step >= 1,
                        rx.badge("1", color_scheme="purple", size="3"),
                        rx.badge("1", variant="soft", size="3"),
                    ),
                    rx.text("Sensor", size="1", color="gray"),
                    align="center",
                    spacing="1",
                ),
                rx.icon("chevron-right", size=16, color="gray"),

                # Step 2
                rx.vstack(
                    rx.cond(
                        TrainingWizardState.wizard_step >= 2,
                        rx.badge("2", color_scheme="purple", size="3"),
                        rx.badge("2", variant="soft", size="3"),
                    ),
                    rx.text("Model", size="1", color="gray"),
                    align="center",
                    spacing="1",
                ),
                rx.icon("chevron-right", size=16, color="gray"),

                # Step 3
                rx.vstack(
                    rx.cond(
                        TrainingWizardState.wizard_step >= 3,
                        rx.badge("3", color_scheme="purple", size="3"),
                        rx.badge("3", variant="soft", size="3"),
                    ),
                    rx.text("Features", size="1", color="gray"),
                    align="center",
                    spacing="1",
                ),
                rx.icon("chevron-right", size=16, color="gray"),

                # Step 4
                rx.vstack(
                    rx.cond(
                        TrainingWizardState.wizard_step >= 4,
                        rx.badge("4", color_scheme="purple", size="3"),
                        rx.badge("4", variant="soft", size="3"),
                    ),
                    rx.text("Params", size="1", color="gray"),
                    align="center",
                    spacing="1",
                ),
                rx.icon("chevron-right", size=16, color="gray"),

                # Step 5
                rx.vstack(
                    rx.cond(
                        TrainingWizardState.wizard_step >= 5,
                        rx.badge("5", color_scheme="purple", size="3"),
                        rx.badge("5", variant="soft", size="3"),
                    ),
                    rx.text("Train", size="1", color="gray"),
                    align="center",
                    spacing="1",
                ),
                rx.icon("chevron-right", size=16, color="gray"),

                # Step 6
                rx.vstack(
                    rx.cond(
                        TrainingWizardState.wizard_step >= 6,
                        rx.badge("6", color_scheme="purple", size="3"),
                        rx.badge("6", variant="soft", size="3"),
                    ),
                    rx.text("Results", size="1", color="gray"),
                    align="center",
                    spacing="1",
                ),

                spacing="2",
                align="center",
                wrap="wrap",
            ),

            spacing="3",
            width="100%",
        ),
        size="2",
        width="100%",
    )
