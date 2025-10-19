"""
Training Results Display Component
Enhanced display for Pipeline V2 metadata
"""

import reflex as rx
from ..states.training_state import TrainingState


def training_results_enhanced() -> rx.Component:
    """Training 결과 - Pipeline V2 전체 메타데이터 표시"""
    return rx.cond(
        TrainingState.training_complete,
        rx.vstack(
            rx.heading("Training Results", size="4"),

            # Data Summary
            rx.vstack(
                rx.heading("Data Summary", size="3"),
                rx.grid(
                    rx.vstack(
                        rx.text("Sensor", size="1", color="gray"),
                        rx.text(TrainingState.result_metadata.get("tag_name", "N/A"), weight="bold"),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Raw Samples", size="1", color="gray"),
                        rx.text(str(TrainingState.result_metadata.get("raw_samples", 0)), weight="bold"),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Processed", size="1", color="gray"),
                        rx.text(str(TrainingState.result_metadata.get("processed_samples", 0)), weight="bold"),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Duration", size="1", color="gray"),
                        rx.text(TrainingState.result_metadata.get("training_duration", "N/A"), weight="bold"),
                        spacing="1",
                    ),
                    columns="4",
                    spacing="4",
                ),
                spacing="2",
            ),

            # Preprocessing Summary
            rx.cond(
                TrainingState.result_metadata.get("preprocessing_steps"),
                rx.vstack(
                    rx.heading("Preprocessing", size="3"),
                    rx.hstack(
                        rx.badge(
                            f"Outliers: {TrainingState.result_metadata.get('outliers_removed', 0)}",
                            color_scheme="red"
                        ),
                        rx.badge(
                            f"Gaps Filled: {TrainingState.result_metadata.get('interpolated_gaps', 0)}",
                            color_scheme="blue"
                        ),
                        spacing="2",
                    ),
                    spacing="2",
                ),
            ),

            # Feature Engineering Summary
            rx.vstack(
                rx.heading("Feature Engineering", size="3"),
                rx.grid(
                    rx.vstack(
                        rx.text("Original Features", size="1", color="gray"),
                        rx.text(str(TrainingState.result_metadata.get("original_features", 0)), weight="bold"),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Final Features", size="1", color="gray"),
                        rx.text(str(TrainingState.result_metadata.get("final_features", 0)), weight="bold"),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Features Created", size="1", color="gray"),
                        rx.text(str(len(TrainingState.result_metadata.get("features_created", []))), weight="bold"),
                        spacing="1",
                    ),
                    columns="3",
                    spacing="4",
                ),
                spacing="2",
            ),

            # Model Performance
            rx.vstack(
                rx.heading("Model Performance", size="3"),
                rx.hstack(
                    rx.badge(
                        f"Model: {TrainingState.result_metadata.get('best_model', 'N/A')}",
                        color_scheme="green",
                        size="2"
                    ),
                    rx.badge(
                        f"MAPE: {TrainingState.result_metadata.get('best_mape', 'N/A')}",
                        color_scheme="blue",
                        size="2"
                    ),
                    spacing="2",
                ),
                rx.cond(
                    TrainingState.result_metadata.get("models_trained"),
                    rx.text(
                        f"Models Trained: {', '.join(TrainingState.result_metadata.get('models_trained', []))}",
                        size="2",
                        color="gray"
                    ),
                ),
                spacing="2",
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

            spacing="4",
            padding="4",
            border_radius="md",
            border=f"1px solid {rx.color('green', 6)}",
            bg=rx.color("green", 2),
        ),
    )
