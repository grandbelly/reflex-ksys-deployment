"""Training Wizard - Step 4: Training Parameters"""
import reflex as rx
from reflex.utils import console
from ...states.training_wizard_state import TrainingWizardState
from ...utils.responsive import responsive_grid_columns


def step_4_params() -> rx.Component:
    """Step 4: Training Parameters"""
    console.log("DEBUG: step_4_params() called")
    return rx.card(
        rx.vstack(
            # Header with icon
            rx.hstack(
                rx.icon("settings", size=24, color=rx.color("purple", 9)),
                rx.vstack(
                    rx.heading("Step 4: Set Training Parameters", size="4"),
                    rx.text("Configure how the model will be trained", size="2", color="gray"),
                    spacing="1",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
                width="100%",
            ),

            rx.divider(),

            rx.vstack(
            # Data parameters
            rx.vstack(
                rx.heading("Data Configuration", size="3"),
                rx.grid(
                    rx.vstack(
                        rx.text("Training Days:", weight="bold"),
                        rx.input(type="number",
                            value=TrainingWizardState.training_days,
                            on_change=TrainingWizardState.set_training_days,
                            min_=1,
                            max_=30,
                            width="100%",
                        ),
                        rx.text("Amount of historical data", size="1", color="gray"),
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Forecast Interval (minutes):", weight="bold"),
                        rx.input(type="number",
                            value=TrainingWizardState.forecast_interval_minutes,
                            on_change=TrainingWizardState.set_forecast_interval_minutes,
                            min_=1,
                            max_=60,
                            width="100%",
                        ),
                        rx.text("Prediction frequency (e.g., 10 = every 10 minutes)", size="1", color="gray"),
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Forecast Horizon (hours):", weight="bold"),
                        rx.input(type="number",
                            value=TrainingWizardState.forecast_horizon_hours,
                            on_change=TrainingWizardState.set_forecast_horizon_hours,
                            min_=1,
                            max_=24,
                            width="100%",
                        ),
                        rx.text("How far ahead to predict (e.g., 6 = 6 hours)", size="1", color="gray"),
                        spacing="1",
                        width="100%",
                    ),
                    columns=responsive_grid_columns(mobile=1, tablet=2, desktop=3),
                    spacing="4",
                    width="100%",
                ),
                spacing="2",
            ),

            # Model-specific parameters (AutoARIMA)
            rx.cond(
                TrainingWizardState.selected_model == "auto_arima",
                rx.vstack(
                    rx.heading("AutoARIMA Parameters", size="3"),
                    rx.vstack(
                        rx.text("Seasonal Period (season_length):", weight="bold"),
                        rx.input(
                            type="number",
                            value=TrainingWizardState.season_length,
                            on_change=TrainingWizardState.set_season_length,
                            min_=1,
                            max_=288,  # Max: 48 hours for 10-min data
                            width="150px",
                        ),
                        rx.text("1 = non-seasonal, 144 = daily (24h for 10-min data), 1008 = weekly", size="1", color="gray"),
                        rx.callout.root(
                            rx.callout.icon(rx.icon("info")),
                            rx.callout.text(
                                "💡 Most sensor data has no daily patterns. Use 1 (non-seasonal) for faster training.",
                                size="1"
                            ),
                            color_scheme="purple",
                            size="1",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    spacing="2",
                ),
                rx.box(),  # Empty box for other models
            ),

            # Preprocessing
            rx.vstack(
                rx.heading("Preprocessing", size="3"),
                rx.hstack(
                    rx.switch(
                        checked=TrainingWizardState.enable_preprocessing,
                        on_change=TrainingWizardState.set_enable_preprocessing,
                    ),
                    rx.text("Enable data preprocessing", weight="bold"),
                    spacing="2",
                ),
                rx.cond(
                    TrainingWizardState.enable_preprocessing,
                    rx.vstack(
                        rx.text("✓ Interpolate missing values (linear)", size="2", color="green"),
                        rx.text("✓ Remove outliers", size="2", color="green"),
                        rx.hstack(
                            rx.text("Outlier Threshold (Z-score):", size="2"),
                            rx.input(type="number",
                                value=TrainingWizardState.outlier_threshold,
                                on_change=TrainingWizardState.set_outlier_threshold,
                                min_=1.0,
                                max_=5.0,
                                step=0.5,
                                width="100px",
                            ),
                            spacing="2",
                        ),
                        padding_left="4",
                        spacing="2",
                    ),
                    rx.box(),  # Empty box when preprocessing disabled
                ),
                spacing="2",
            ),

            # Validation Feasibility Check
            rx.callout.root(
                rx.callout.icon(
                    rx.cond(
                        TrainingWizardState.validation_feasibility["severity"] == "error",
                        rx.icon("circle-alert"),
                        rx.cond(
                            TrainingWizardState.validation_feasibility["severity"] == "warning",
                            rx.icon("triangle-alert"),
                            rx.icon("circle-check")
                        )
                    )
                ),
                rx.vstack(
                    rx.callout.text(
                        TrainingWizardState.validation_feasibility["message"],
                        weight="bold",
                        size="2",
                    ),
                    rx.callout.text(
                        f"Test size: {TrainingWizardState.validation_feasibility['test_size']} periods | "
                        f"Folds: {TrainingWizardState.validation_feasibility['n_splits']} | "
                        f"Required: {TrainingWizardState.validation_feasibility['min_required_samples']} samples | "
                        f"Estimated: {TrainingWizardState.validation_feasibility['estimated_samples']} samples",
                        size="1",
                        color="gray",
                    ),
                    spacing="1",
                    width="100%",
                ),
                color_scheme=rx.cond(
                    TrainingWizardState.validation_feasibility["severity"] == "error",
                    "red",
                    rx.cond(
                        TrainingWizardState.validation_feasibility["severity"] == "warning",
                        "orange",
                        "green"
                    )
                ),
                size="1",
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
