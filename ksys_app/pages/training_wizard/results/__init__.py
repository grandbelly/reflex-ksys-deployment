"""Training Results - Modular Components"""

from .data_summary import (
    data_summary_section,
    preprocessing_section,
    feature_engineering_section,
)
from .model_selection_info import model_selection_info_section
from .model_diagnostics import model_diagnostics_section
from .evaluation_metrics import evaluation_metrics_section
from .residuals_diagnostics import residuals_diagnostics_section
from .fold_results import fold_results_section
from .validation_charts import (
    validation_chart_section,
    comparison_table_section,
    forecast_chart_section,
    matplotlib_forecast_plot_section,
)
from .performance_summary import (
    performance_summary_section,
    saved_data_section,
    action_buttons_section,
)

__all__ = [
    # Data summary
    "data_summary_section",
    "preprocessing_section",
    "feature_engineering_section",
    # Model selection info
    "model_selection_info_section",
    # Model diagnostics
    "model_diagnostics_section",
    # Evaluation
    "evaluation_metrics_section",
    # Fold-by-fold results
    "fold_results_section",
    # Residuals
    "residuals_diagnostics_section",
    # Validation charts
    "validation_chart_section",
    "comparison_table_section",
    "forecast_chart_section",
    "matplotlib_forecast_plot_section",
    # Performance & actions
    "performance_summary_section",
    "saved_data_section",
    "action_buttons_section",
]
