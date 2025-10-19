"""Training Wizard - Step 6: View Results (Refactored to use modular components)"""
import reflex as rx
from reflex.utils import console
from ...states.training_wizard_state import TrainingWizardState

# Import all result section components
from .results import (
    data_summary_section,
    preprocessing_section,
    feature_engineering_section,
    model_selection_info_section,
    model_diagnostics_section,
    evaluation_metrics_section,
    fold_results_section,
    residuals_diagnostics_section,
    validation_chart_section,
    comparison_table_section,
    forecast_chart_section,
    matplotlib_forecast_plot_section,
    performance_summary_section,
    saved_data_section,
    action_buttons_section,
)


def step_6_results() -> rx.Component:
    """Step 6: View Results - Modular component assembly"""
    console.log("DEBUG: step_6_results() called")
    return rx.vstack(
        rx.heading("Step 6: Training Results", size="5"),
        rx.text("Your model has been trained successfully!", color="gray"),

        rx.vstack(
            # Data Summary
            data_summary_section(),

            # Preprocessing (if applicable)
            preprocessing_section(),

            # Features
            feature_engineering_section(),

            # Model Selection Info (NEW - shows selected model and parameters)
            model_selection_info_section(),

            # Model Diagnostics (AutoARIMA specific)
            model_diagnostics_section(),

            # Evaluation Metrics (Walk-Forward Validation)
            evaluation_metrics_section(),

            # Fold-by-Fold Results (Walk-Forward Validation Details)
            # ENABLED: Type annotation fix (list[dict[str, Any]]) resolved UntypedVarError
            fold_results_section(),

            # Residuals Diagnostics
            residuals_diagnostics_section(),

            # Model Validation Chart (Actual vs Predicted)
            validation_chart_section(),

            # Comparison Table (Actual vs Predicted)
            comparison_table_section(),

            # Forecast with Confidence Intervals (Combined: Historical + Future)
            forecast_chart_section(),

            # Matplotlib Forecast Plot (Kaggle style)
            matplotlib_forecast_plot_section(),

            # Model Performance Summary
            performance_summary_section(),

            # Saved Model Data Display (auto-populated after save_model button is clicked)
            saved_data_section(),

            # Actions
            action_buttons_section(),

            spacing="5",
            width="100%",
        ),

        spacing="4",
        width="100%",
    )
