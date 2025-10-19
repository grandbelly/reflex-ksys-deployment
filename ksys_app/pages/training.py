"""
Training Page - Comprehensive ML Model Training UI

모든 것을 통합한 Training 화면:
- Sensor 선택
- Model 파라미터 설정 (from database)
- Feature engineering 설정 (from database)
- Preprocessing 설정
- Training 실행
- Results 표시

Route: /training
"""

import reflex as rx
from ..states.training_state import TrainingState


def sensor_selection() -> rx.Component:
    """Sensor 선택"""
    return rx.vstack(
        rx.heading("1. Select Sensor", size="4"),
        rx.select(
            ["INLET_PRESSURE", "FEED_FLOW", "FEED_COND", "OUTLET_PRESSURE"],
            placeholder="Select sensor tag...",
            value=TrainingState.selected_tag,
            on_change=TrainingState.set_selected_tag,
            width="100%",
        ),
        spacing="2",
    )


def model_selection() -> rx.Component:
    """Model 타입 선택"""
    return rx.vstack(
        rx.heading("2. Select Model", size="4"),
        rx.select(
            ["auto_arima", "prophet", "xgboost", "ensemble"],
            placeholder="Select model type...",
            value=TrainingState.selected_model,
            on_change=TrainingState.set_selected_model,
            width="100%",
        ),
        rx.cond(
            TrainingState.selected_model,
            rx.text(
                f"Selected: {TrainingState.selected_model}",
                size="2",
                color="green",
            ),
        ),
        spacing="2",
    )


def feature_config_selection() -> rx.Component:
    """Feature configuration 선택"""
    return rx.vstack(
        rx.heading("3. Feature Configuration", size="4"),

        # Config 선택
        rx.select(
            TrainingState.available_feature_configs,
            placeholder="Select feature config...",
            value=TrainingState.selected_feature_config,
            on_change=TrainingState.load_feature_config,
            width="100%",
        ),

        # 선택된 config 정보
        rx.cond(
            TrainingState.feature_config_loaded,
            rx.vstack(
                rx.text("Features:", weight="bold", size="2"),
                rx.hstack(
                    rx.badge(f"Lag: {TrainingState.feature_counts['lag']}", color_scheme="blue"),
                    rx.badge(f"Rolling: {TrainingState.feature_counts['rolling']}", color_scheme="green"),
                    rx.badge(f"Temporal: {TrainingState.feature_counts['temporal']}", color_scheme="purple"),
                    spacing="2",
                ),
                rx.button(
                    "Customize Features",
                    on_click=TrainingState.open_feature_editor,
                    size="2",
                    variant="soft",
                ),
                spacing="2",
            ),
        ),

        spacing="2",
    )


def training_params() -> rx.Component:
    """Training 파라미터"""
    return rx.vstack(
        rx.heading("4. Training Parameters", size="4"),

        rx.hstack(
            rx.vstack(
                rx.text("Training Days:", weight="bold"),
                rx.number_input(
                    value=TrainingState.training_days,
                    on_change=TrainingState.set_training_days,
                    min_=1,
                    max_=30,
                ),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Forecast Horizon:", weight="bold"),
                rx.number_input(
                    value=TrainingState.forecast_horizon,
                    on_change=TrainingState.set_forecast_horizon,
                    min_=1,
                    max_=144,
                ),
                spacing="1",
            ),
            spacing="4",
        ),

        # Preprocessing options
        rx.vstack(
            rx.heading("Preprocessing", size="3"),
            rx.hstack(
                rx.switch(
                    checked=TrainingState.enable_preprocessing,
                    on_change=TrainingState.set_enable_preprocessing,
                ),
                rx.text("Enable Preprocessing"),
                spacing="2",
            ),
            rx.cond(
                TrainingState.enable_preprocessing,
                rx.vstack(
                    rx.hstack(
                        rx.text("Outlier Threshold:"),
                        rx.number_input(
                            value=TrainingState.outlier_threshold,
                            on_change=TrainingState.set_outlier_threshold,
                            min_=1.0,
                            max_=5.0,
                            step=0.5,
                        ),
                        spacing="2",
                    ),
                    padding_left="4",
                ),
            ),
            spacing="2",
        ),

        spacing="3",
    )


def training_actions() -> rx.Component:
    """Training 실행 버튼"""
    return rx.vstack(
        rx.divider(),
        rx.hstack(
            rx.button(
                "Start Training",
                on_click=TrainingState.start_training,
                loading=TrainingState.is_training,
                size="3",
                color_scheme="green",
                width="200px",
            ),
            rx.button(
                "Reset",
                on_click=TrainingState.reset_form,
                size="3",
                variant="soft",
            ),
            spacing="3",
        ),
        spacing="3",
    )


def training_progress() -> rx.Component:
    """Training 진행 상황"""
    return rx.cond(
        TrainingState.is_training,
        rx.vstack(
            rx.heading("Training in Progress...", size="4"),
            rx.progress(value=TrainingState.training_progress, max=100),
            rx.text(TrainingState.training_status, size="2", color="gray"),
            spacing="2",
            padding="4",
            border_radius="md",
            border=f"1px solid {rx.color('blue', 6)}",
            bg=rx.color("blue", 2),
        ),
    )


def training_results() -> rx.Component:
    """Training 결과"""
    return rx.cond(
        TrainingState.training_complete,
        rx.vstack(
            rx.heading("Training Results", size="4"),

            # Metadata
            rx.grid(
                rx.vstack(
                    rx.text("Samples", size="1", color="gray"),
                    rx.text(str(TrainingState.result_metadata.get("processed_samples", 0)), weight="bold"),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Features Created", size="1", color="gray"),
                    rx.text(str(len(TrainingState.result_metadata.get("features_created", []))), weight="bold"),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Training Duration", size="1", color="gray"),
                    rx.text(f"{TrainingState.result_metadata.get('training_duration', 0):.2f}s", weight="bold"),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Best Model", size="1", color="gray"),
                    rx.text(TrainingState.result_metadata.get("best_model", "N/A"), weight="bold"),
                    spacing="1",
                ),
                columns="4",
                spacing="4",
            ),

            # Model Performance
            rx.cond(
                TrainingState.result_metadata.get("mape", 0) > 0,
                rx.vstack(
                    rx.heading("Model Performance", size="3"),
                    rx.hstack(
                        rx.badge(f"MAPE: {TrainingState.result_metadata.get('mape', 0):.2f}%", color_scheme="green"),
                        rx.badge(f"RMSE: {TrainingState.result_metadata.get('rmse', 0):.2f}", color_scheme="blue"),
                        rx.badge(f"MAE: {TrainingState.result_metadata.get('mae', 0):.2f}", color_scheme="purple"),
                        spacing="2",
                    ),
                    spacing="2",
                ),
            ),

            # Actions
            rx.hstack(
                rx.button(
                    "View Predictions",
                    on_click=TrainingState.view_predictions,
                    size="2",
                    variant="soft",
                ),
                rx.button(
                    "Save Model",
                    on_click=TrainingState.save_model,
                    size="2",
                    color_scheme="green",
                ),
                rx.button(
                    "Train Another",
                    on_click=TrainingState.reset_form,
                    size="2",
                    variant="soft",
                ),
                spacing="2",
            ),

            spacing="3",
            padding="4",
            border_radius="md",
            border=f"1px solid {rx.color('green', 6)}",
            bg=rx.color("green", 2),
        ),
    )


def error_display() -> rx.Component:
    """에러 표시"""
    return rx.cond(
        TrainingState.error_message,
        rx.callout(
            TrainingState.error_message,
            color_scheme="red",
            icon="triangle-alert",
        ),
    )


@rx.page("/training", on_load=TrainingState.initialize)
def training_page() -> rx.Component:
    """Training page"""
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.heading("ML Model Training", size="6"),
                rx.badge("Pipeline V2", color_scheme="blue"),
                rx.badge("Database-Driven", color_scheme="green"),
                spacing="3",
                align="center",
            ),

            rx.text(
                "Train machine learning models with complete control over all settings",
                size="3",
                color="gray",
            ),

            # Error display
            error_display(),

            # Main content
            rx.grid(
                # Left panel: Configuration
                rx.vstack(
                    sensor_selection(),
                    model_selection(),
                    feature_config_selection(),
                    training_params(),
                    training_actions(),
                    spacing="4",
                    padding="4",
                    border_radius="md",
                    border=f"1px solid {rx.color('gray', 6)}",
                ),

                # Right panel: Results
                rx.vstack(
                    training_progress(),
                    training_results(),
                    spacing="4",
                ),

                columns="2",
                spacing="6",
                width="100%",
            ),

            spacing="4",
            width="100%",
            max_width="1400px",
        ),
        padding="6",
    )
