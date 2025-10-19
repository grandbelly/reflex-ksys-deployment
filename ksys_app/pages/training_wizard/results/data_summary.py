"""Training Results - Data Summary Component"""
import reflex as rx
from ....states.training_wizard_state import TrainingWizardState


def data_summary_section() -> rx.Component:
    """Data summary with sensor info and sample counts"""
    return rx.vstack(
        rx.heading("Data Summary", size="3"),
        rx.grid(
            rx.vstack(
                rx.heading(TrainingWizardState.selected_tag, size="5"),
                rx.text("Sensor", size="1", color="gray"),
                align="center",
                spacing="1",
            ),
            rx.vstack(
                rx.heading(TrainingWizardState.raw_samples_display, size="5"),
                rx.text("Raw Samples", size="1", color="gray"),
                align="center",
                spacing="1",
            ),
            rx.vstack(
                rx.heading(TrainingWizardState.processed_samples_display, size="5"),
                rx.text("Processed", size="1", color="gray"),
                align="center",
                spacing="1",
            ),
            rx.vstack(
                rx.heading("--", size="5"),
                rx.text("Duration", size="1", color="gray"),
                align="center",
                spacing="1",
            ),
            columns="4",
            spacing="4",
        ),
        spacing="2",
    )


def preprocessing_section() -> rx.Component:
    """Preprocessing information if applicable"""
    return rx.cond(
        TrainingWizardState.training_complete,
        rx.vstack(
            rx.heading("Preprocessing Applied", size="3"),
            rx.hstack(
                rx.badge(
                    "Outliers Removed",
                    color_scheme="red",
                    size="2"
                ),
                rx.badge(
                    "Gaps Filled",
                    color_scheme="blue",
                    size="2"
                ),
                spacing="2",
            ),
            spacing="2",
        ),
    )


def feature_engineering_section() -> rx.Component:
    """Feature engineering summary"""
    return rx.vstack(
        rx.heading("Feature Engineering", size="3"),
        rx.grid(
            rx.vstack(
                rx.heading(TrainingWizardState.original_features_display, size="5", color="gray"),
                rx.text("Original", size="1", color="gray"),
                align="center",
                spacing="1",
            ),
            rx.vstack(
                rx.text("→", size="6"),
                align="center",
            ),
            rx.vstack(
                rx.heading(TrainingWizardState.final_features_display, size="5", color="green"),
                rx.text("Final Features", size="1", color="gray"),
                align="center",
                spacing="1",
            ),
            columns="3",
            spacing="2",
        ),
        spacing="2",
    )
