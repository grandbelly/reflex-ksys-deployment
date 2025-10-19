"""Training Results - Evaluation Metrics Component"""
import reflex as rx
from ....states.training_wizard_state import TrainingWizardState


def evaluation_metrics_section() -> rx.Component:
    """Walk-forward validation metrics display"""
    return rx.cond(
        TrainingWizardState.has_evaluation_metrics,
        rx.vstack(
            rx.heading("Evaluation Metrics (Walk-Forward Validation)", size="3"),
            rx.grid(
                # MAE
                rx.vstack(
                    rx.text("MAE", size="1", color="gray"),
                    rx.text(
                        TrainingWizardState.mae_value,
                        size="4",
                        weight="bold",
                        color="blue"
                    ),
                    rx.text("Mean Absolute Error", size="1", color="gray"),
                    align="center",
                    spacing="1",
                ),
                # MAPE
                rx.vstack(
                    rx.text("MAPE", size="1", color="gray"),
                    rx.text(
                        TrainingWizardState.mape_value,
                        size="4",
                        weight="bold",
                        color="blue"
                    ),
                    rx.text("Mean Absolute % Error", size="1", color="gray"),
                    align="center",
                    spacing="1",
                ),
                # RMSE
                rx.vstack(
                    rx.text("RMSE", size="1", color="gray"),
                    rx.text(
                        TrainingWizardState.rmse_value,
                        size="4",
                        weight="bold",
                        color="purple"
                    ),
                    rx.text("Root Mean Squared Error", size="1", color="gray"),
                    align="center",
                    spacing="1",
                ),
                columns="3",
                spacing="4",
            ),
            rx.grid(
                # SMAPE
                rx.vstack(
                    rx.text("SMAPE", size="1", color="gray"),
                    rx.text(
                        TrainingWizardState.smape_value,
                        size="3",
                        weight="bold",
                        color="green"
                    ),
                    rx.text("Symmetric MAPE", size="1", color="gray"),
                    align="center",
                    spacing="1",
                ),
                # MASE
                rx.vstack(
                    rx.text("MASE", size="1", color="gray"),
                    rx.text(
                        TrainingWizardState.mase_value,
                        size="3",
                        weight="bold",
                        color="orange"
                    ),
                    rx.text("Mean Absolute Scaled Error", size="1", color="gray"),
                    align="center",
                    spacing="1",
                ),
                # Validation Info
                rx.vstack(
                    rx.text("Validation", size="1", color="gray"),
                    rx.text(
                        TrainingWizardState.n_windows_display,
                        size="2",
                        weight="bold"
                    ),
                    rx.text(
                        TrainingWizardState.n_predictions_display,
                        size="1",
                        color="gray"
                    ),
                    align="center",
                    spacing="1",
                ),
                columns="3",
                spacing="4",
            ),
            spacing="3",
        ),
    )
