"""Training Results - Residuals Diagnostics Component"""
import reflex as rx
from ....states.training_wizard_state import TrainingWizardState


def residuals_diagnostics_section() -> rx.Component:
    """Residuals statistics and diagnostics"""
    return rx.cond(
        TrainingWizardState.has_residuals_stats,
        rx.vstack(
            rx.heading("Residuals Diagnostics", size="3"),

            # Statistics Grid
            rx.grid(
                rx.vstack(
                    rx.text("Mean", size="1", color="gray"),
                    rx.text(
                        TrainingWizardState.residuals_mean_stat,
                        size="3",
                        weight="bold"
                    ),
                    align="center",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Std Dev", size="1", color="gray"),
                    rx.text(
                        TrainingWizardState.residuals_std_stat,
                        size="3",
                        weight="bold"
                    ),
                    align="center",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Skewness", size="1", color="gray"),
                    rx.text(
                        TrainingWizardState.residuals_skewness,
                        size="3",
                        weight="bold",
                        color="purple"
                    ),
                    align="center",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Kurtosis", size="1", color="gray"),
                    rx.text(
                        TrainingWizardState.residuals_kurtosis,
                        size="3",
                        weight="bold",
                        color="orange"
                    ),
                    align="center",
                    spacing="1",
                ),
                columns="4",
                spacing="4",
            ),

            # REMOVED - Recharts components causing initialization issues
            # Charts temporarily disabled - will use alternative visualization
            rx.callout(
                "Residual analysis charts temporarily disabled",
                icon="info",
                color_scheme="blue",
                size="2",
            ),

            spacing="4",
        ),
    )
