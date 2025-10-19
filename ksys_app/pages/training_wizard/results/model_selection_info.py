"""Training Results - Model Selection Information Component"""
import reflex as rx
from ....states.training_wizard_state import TrainingWizardState


def model_selection_info_section() -> rx.Component:
    """Display selected model and training parameters"""
    return rx.vstack(
        rx.heading("Model Configuration", size="3"),

        # Model Selection
        rx.callout(
            rx.vstack(
                rx.text("Selected Model", weight="bold", size="2"),
                rx.badge(
                    TrainingWizardState.selected_model,
                    color_scheme="blue",
                    size="2",
                ),
                spacing="1",
            ),
            icon="sparkles",
            color_scheme="blue",
            size="2",
        ),

        # Training Parameters
        rx.callout(
            rx.grid(
                # Training Days
                rx.vstack(
                    rx.text("Training Period", size="1", color="gray"),
                    rx.text(
                        f"{TrainingWizardState.training_days} days",
                        size="2",
                        weight="bold"
                    ),
                    align="center",
                    spacing="1",
                ),
                # Forecast Configuration (NEW - shows "10분 단위 6시간 예측 (36개 스텝)")
                rx.vstack(
                    rx.text("Forecast Configuration", size="1", color="gray"),
                    rx.text(
                        TrainingWizardState.forecast_summary,
                        size="2",
                        weight="bold"
                    ),
                    align="center",
                    spacing="1",
                ),
                # Preprocessing
                rx.vstack(
                    rx.text("Preprocessing", size="1", color="gray"),
                    rx.badge(
                        rx.cond(
                            TrainingWizardState.enable_preprocessing,
                            "Enabled",
                            "Disabled"
                        ),
                        color_scheme=rx.cond(
                            TrainingWizardState.enable_preprocessing,
                            "green",
                            "gray"
                        ),
                    ),
                    align="center",
                    spacing="1",
                ),
                # Feature Engineering
                rx.vstack(
                    rx.text("Feature Engineering", size="1", color="gray"),
                    rx.badge(
                        rx.cond(
                            TrainingWizardState.skip_feature_engineering,
                            "Skipped",
                            "Enabled"
                        ),
                        color_scheme=rx.cond(
                            TrainingWizardState.skip_feature_engineering,
                            "gray",
                            "green"
                        ),
                    ),
                    align="center",
                    spacing="1",
                ),
                columns="4",
                spacing="4",
            ),
            icon="settings",
            color_scheme="gray",
            size="1",
        ),

        # Feature Config (if used)
        rx.cond(
            ~TrainingWizardState.skip_feature_engineering,
            rx.callout(
                rx.hstack(
                    rx.text("Feature Configuration:", size="2", color="gray"),
                    rx.text(
                        TrainingWizardState.selected_feature_config,
                        size="2",
                        weight="bold",
                        color="blue"
                    ),
                    spacing="2",
                ),
                icon="layers",
                color_scheme="cyan",
                size="1",
            ),
        ),

        spacing="3",
    )
