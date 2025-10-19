"""Training Results - Validation Charts and Tables Component"""
import reflex as rx
from ....states.training_wizard_state import TrainingWizardState
from ....components.training_charts import validation_chart, forecast_chart


def validation_chart_section() -> rx.Component:
    """Model validation chart (actual vs predicted)"""
    return rx.cond(
        TrainingWizardState.validation_chart_data,
        rx.vstack(
            rx.heading("Model Validation: Actual vs Predicted", size="3"),
            rx.callout(
                rx.vstack(
                    rx.text(
                        "Walk-forward validation results",
                        size="2",
                        weight="bold"
                    ),
                    rx.text(
                        "Comparing actual values with model predictions to calculate MAPE",
                        size="1",
                        color="gray"
                    ),
                    spacing="1",
                ),
                icon="target",
                color_scheme="blue",
                size="2",
            ),
            # Validation chart (Actual vs Predicted)
            rx.box(
                validation_chart(TrainingWizardState),
                width="100%",
                padding="4",
                border_radius="md",
                border="1px solid",
                border_color=rx.color("gray", 4),
                background=rx.color("gray", 1),
            ),
            spacing="3",
        ),
    )


def comparison_table_section() -> rx.Component:
    """Detailed comparison table (actual vs predicted)"""
    return rx.cond(
        TrainingWizardState.validation_chart_data,
        rx.vstack(
            rx.heading("Detailed Comparison (Actual vs Predicted)", size="3"),
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Timestamp"),
                            rx.table.column_header_cell("Actual Value"),
                            rx.table.column_header_cell("Predicted Value"),
                            rx.table.column_header_cell("Error"),
                            rx.table.column_header_cell("Error %"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            TrainingWizardState.validation_table_data,
                            lambda row: rx.table.row(
                                rx.table.cell(row["timestamp"]),
                                rx.table.cell(row["actual"]),
                                rx.table.cell(row["predicted"]),
                                rx.table.cell(row["error"]),
                                rx.table.cell(row["error_pct"]),
                            ),
                        ),
                    ),
                    size="2",
                    variant="surface",
                ),
                max_height="400px",
                overflow_y="auto",
            ),
            spacing="3",
        ),
    )


def forecast_chart_section() -> rx.Component:
    """Forecast with confidence intervals chart"""
    return rx.cond(
        TrainingWizardState.forecast_with_intervals,
        rx.vstack(
            rx.heading("Forecast with Historical Context", size="3"),
            rx.callout(
                rx.vstack(
                    rx.text(
                        rx.cond(
                            TrainingWizardState.forecast_summary,
                            f"Historical actual data + {TrainingWizardState.forecast_summary} with confidence intervals",
                            "Historical actual data + forecast with confidence intervals"
                        ),
                        size="2",
                        weight="bold"
                    ),
                    rx.text(
                        "Green line = Past actual values | Blue line = Future forecast | Shaded area = Confidence intervals",
                        size="1",
                        color="gray"
                    ),
                    spacing="1",
                ),
                icon="trending-up",
                color_scheme="green",
                size="2",
            ),
            # Forecast chart with confidence intervals
            rx.box(
                forecast_chart(TrainingWizardState),
                width="100%",
                padding="4",
                border_radius="md",
                border="1px solid",
                border_color=rx.color("gray", 4),
                background=rx.color("gray", 1),
            ),

            spacing="3",
        ),
    )


def matplotlib_forecast_plot_section() -> rx.Component:
    """Kaggle-style forecast plot section with dialog button"""
    return rx.cond(
        TrainingWizardState.forecast_with_intervals,
        rx.vstack(
            rx.heading("Forecast Visualization", size="3"),
            rx.callout(
                rx.vstack(
                    rx.text(
                        "View your forecast in full-screen mode",
                        size="2",
                        weight="bold"
                    ),
                    rx.text(
                        rx.cond(
                            TrainingWizardState.forecast_summary,
                            f"Historical data + {TrainingWizardState.forecast_summary} with confidence intervals",
                            "Historical data + forecast with confidence intervals"
                        ),
                        size="1",
                        color="gray"
                    ),
                    spacing="1",
                ),
                icon="chart-line",
                color_scheme="purple",
                size="2",
            ),

            rx.button(
                rx.icon("maximize-2", size=20),
                "Open Full Forecast View",
                on_click=TrainingWizardState.open_forecast_dialog,
                size="3",
                variant="surface",
                color_scheme="purple",
                width="100%",
            ),

            # Include the dialog
            forecast_dialog(),

            spacing="3",
        ),
    )


def forecast_dialog() -> rx.Component:
    """Dialog for full-screen forecast visualization"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.heading("Forecast Visualization", size="4"),
                    rx.spacer(),
                    rx.button(
                        rx.icon("x", size=20),
                        on_click=TrainingWizardState.close_forecast_dialog,
                        variant="ghost",
                        color_scheme="gray",
                    ),
                    width="100%",
                    align="center",
                ),

                rx.divider(),

                # Large forecast chart
                forecast_chart(TrainingWizardState),

                rx.text(
                    f"Model: {TrainingWizardState.selected_model} | Sensor: {TrainingWizardState.selected_tag}",
                    size="2",
                    color="gray",
                ),

                spacing="4",
                width="100%",
            ),
            max_width="90vw",
            max_height="90vh",
        ),
        open=TrainingWizardState.show_forecast_dialog,
    )


