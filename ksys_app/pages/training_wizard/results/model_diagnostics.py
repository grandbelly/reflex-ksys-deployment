"""Training Results - Model Diagnostics Component"""
import reflex as rx
from ....states.training_wizard_state import TrainingWizardState


def model_diagnostics_section() -> rx.Component:
    """Model diagnostics display (AutoARIMA specific)"""
    return rx.cond(
        TrainingWizardState.has_model_diagnostics,
        rx.vstack(
            rx.heading("Model Diagnostics", size="3"),
            rx.vstack(
                # ARIMA Parameters
                rx.callout(
                    rx.vstack(
                        rx.text("ARIMA Parameters", weight="bold", size="2"),
                        rx.text(
                            TrainingWizardState.arima_string,
                            size="3",
                            weight="bold",
                            color="blue",
                        ),
                        spacing="1",
                    ),
                    icon="brain",
                    color_scheme="blue",
                    size="2",
                ),

                # Model Selection Criteria
                rx.grid(
                    rx.vstack(
                        rx.text("AIC", size="1", color="gray"),
                        rx.text(
                            TrainingWizardState.aic_value,
                            size="3",
                            weight="bold"
                        ),
                        align="center",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("BIC", size="1", color="gray"),
                        rx.text(
                            TrainingWizardState.bic_value,
                            size="3",
                            weight="bold"
                        ),
                        align="center",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("AICc", size="1", color="gray"),
                        rx.text(
                            TrainingWizardState.aicc_value,
                            size="3",
                            weight="bold"
                        ),
                        align="center",
                        spacing="1",
                    ),
                    columns="3",
                    spacing="4",
                ),

                # Residuals Statistics
                rx.callout(
                    rx.grid(
                        rx.vstack(
                            rx.text("Residuals Mean", size="1", color="gray"),
                            rx.text(
                                TrainingWizardState.residuals_mean_value,
                                size="2"
                            ),
                            align="center",
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Residuals Std", size="1", color="gray"),
                            rx.text(
                                TrainingWizardState.residuals_std_value,
                                size="2"
                            ),
                            align="center",
                            spacing="1",
                        ),
                        columns="2",
                        spacing="4",
                    ),
                    icon="activity",
                    color_scheme="gray",
                    size="1",
                ),

                spacing="3",
            ),
            spacing="2",
        ),
    )
