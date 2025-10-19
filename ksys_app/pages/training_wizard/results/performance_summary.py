"""Training Results - Performance Summary and Actions Component"""
import reflex as rx
from ....states.training_wizard_state import TrainingWizardState
from ....components.saved_data_display import saved_model_info_section


def performance_summary_section() -> rx.Component:
    """Model performance summary with best model badge

    Note: This shows the best model selected based on validation MAPE.
    The MAPE shown here is from walk-forward validation, NOT forecast MAPE
    (since forecast is future prediction with no actual values to compare).

    See "Evaluation Metrics" section above for detailed validation metrics.
    """
    return rx.cond(
        TrainingWizardState.has_evaluation_metrics,
        rx.vstack(
            rx.heading("Model Performance", size="3"),
            rx.hstack(
                rx.badge(
                    rx.text("Best Model: ", TrainingWizardState.selected_model),
                    color_scheme="green",
                    size="3"
                ),
                rx.badge(
                    rx.text("Validation MAPE: ", TrainingWizardState.mape_value),
                    color_scheme="blue",
                    size="3"
                ),
                spacing="3",
                justify="center",
            ),
            align="center",
            spacing="3",
        ),
        rx.box(),  # Don't show if no validation metrics
    )


def saved_data_section() -> rx.Component:
    """Saved model and predictions data display"""
    return saved_model_info_section(TrainingWizardState)


def action_buttons_section() -> rx.Component:
    """Action buttons for saving model, restarting, and navigating to performance"""
    return rx.hstack(
        rx.button(
            "Save Model",
            on_click=TrainingWizardState.save_model,
            size="4",
            color_scheme="green",
            disabled=TrainingWizardState.model_saved,
        ),
        rx.button(
            "Train Another Model",
            on_click=TrainingWizardState.reset_wizard,
            size="4",
            color_scheme="gray",
        ),
        # 🆕 NEW: Navigate to Model Performance (appears after save)
        rx.cond(
            TrainingWizardState.model_saved,
            rx.button(
                rx.hstack(
                    rx.icon("chart-no-axes-column", size=18),
                    rx.text("성능 비교 보기"),
                    spacing="2",
                ),
                on_click=TrainingWizardState.navigate_to_performance,
                size="4",
                color_scheme="blue",
            ),
            rx.fragment(),
        ),
        spacing="4",
        justify="center",
        width="100%",
    )
