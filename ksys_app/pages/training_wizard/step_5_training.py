"""Training Wizard - Step 5: Execute Training"""
import reflex as rx
from reflex.utils import console
from ...states.training_wizard_state import TrainingWizardState
from ...utils.responsive import responsive_grid_columns


def step_5_training() -> rx.Component:
    """Step 5: Execute Training"""
    console.log("DEBUG: step_5_training() called")
    return rx.card(
        rx.vstack(
            # Header with icon
            rx.hstack(
                rx.icon("rocket", size=24, color=rx.color("purple", 9)),
                rx.vstack(
                    rx.heading("Step 5: Ready to Train", size="4"),
                    rx.text("Review your configuration and start training", size="2", color="gray"),
                    spacing="1",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
                width="100%",
            ),

            rx.divider(),

            rx.vstack(
            # Configuration summary
            rx.box(
                rx.vstack(
                    rx.heading("Configuration Summary", size="3"),

                    rx.grid(
                        rx.vstack(
                            rx.text("Sensor", size="1", color="gray"),
                            rx.text(TrainingWizardState.selected_tag, weight="bold"),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Model", size="1", color="gray"),
                            rx.text(TrainingWizardState.selected_model, weight="bold"),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Feature Config", size="1", color="gray"),
                            rx.text(TrainingWizardState.selected_feature_config, weight="bold"),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Training Days", size="1", color="gray"),
                            rx.text(TrainingWizardState.training_days, weight="bold"),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Forecast Config", size="1", color="gray"),
                            rx.text(TrainingWizardState.forecast_summary, weight="bold"),
                            spacing="1",
                        ),
                        columns=responsive_grid_columns(mobile=1, tablet=3, desktop=5),
                        spacing="4",
                    ),

                    spacing="3",
                ),
                padding="4",
                border_radius="md",
                border="1px solid",
                border_color=rx.color('purple', 6),
                bg=rx.color("purple", 2),
            ),

            # Training progress
            rx.cond(
                TrainingWizardState.is_training,
                rx.box(
                    rx.vstack(
                        rx.heading("Training in Progress...", size="4"),
                        rx.progress(value=TrainingWizardState.training_progress, max=100, width="100%"),
                        rx.text(TrainingWizardState.training_status, size="2", color="gray"),
                        spacing="3",
                    ),
                    padding="4",
                    border_radius="md",
                    border="1px solid",
                    border_color=rx.color('green', 6),
                    bg=rx.color("green", 2),
                    width="100%",
                ),
            ),

            # Validation warning (if invalid)
            rx.cond(
                ~TrainingWizardState.validation_feasibility["is_valid"],
                rx.callout.root(
                    rx.callout.icon(rx.icon("circle-alert")),
                    rx.vstack(
                        rx.callout.text(TrainingWizardState.validation_feasibility["message"], weight="bold"),
                        rx.callout.text(
                            "Please adjust parameters in Step 4 to proceed",
                            size="1",
                            color="gray"
                        ),
                        spacing="1",
                    ),
                    color_scheme="red",
                    size="1",
                ),
            ),

            # Start button
            rx.cond(
                ~TrainingWizardState.is_training & ~TrainingWizardState.training_complete,
                rx.button(
                    "Start Training",
                    on_click=[
                        TrainingWizardState.start_wizard_training,
                        TrainingWizardState.monitor_training_completion
                    ],
                    size="3",
                    color_scheme="purple",
                    width="100%",
                    disabled=~TrainingWizardState.validation_feasibility["is_valid"],
                ),
            ),

            spacing="4",
            width="100%",
        ),

            spacing="4",
            width="100%",
        ),
        size="3",
        width="100%",
    )
