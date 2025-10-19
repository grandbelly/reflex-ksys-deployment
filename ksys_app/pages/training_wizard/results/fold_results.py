"""Training Results - Fold-by-Fold Walk-Forward Validation Results"""
import reflex as rx
from ....states.training_wizard_state import TrainingWizardState


def fold_results_section() -> rx.Component:
    """Walk-forward fold-by-fold results with individual charts"""
    return rx.cond(
        TrainingWizardState.fold_results,
        rx.vstack(
            rx.heading("Walk-Forward Validation: Fold-by-Fold Results", size="3"),
            rx.callout(
                rx.vstack(
                    rx.text(
                        "Each fold represents a separate train-test split in walk-forward validation",
                        size="2",
                        weight="bold"
                    ),
                    rx.text(
                        f"Total folds: {TrainingWizardState.fold_results.length()} | Each fold shows Actual vs Predicted comparison",
                        size="1",
                        color="gray"
                    ),
                    spacing="1",
                ),
                icon="layers",
                color_scheme="purple",
                size="2",
            ),

            # Fold-by-fold summary table
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Fold"),
                            rx.table.column_header_cell("Cutoff Date"),
                            rx.table.column_header_cell("Data Points"),
                            rx.table.column_header_cell("MAE"),
                            rx.table.column_header_cell("MAPE (%)"),
                            rx.table.column_header_cell("RMSE"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            TrainingWizardState.fold_results,
                            lambda fold: rx.table.row(
                                rx.table.cell(
                                    rx.badge(fold["fold"], color_scheme="blue", size="1")
                                ),
                                rx.table.cell(rx.text(fold["cutoff"], size="1")),
                                rx.table.cell(rx.text(fold["n_points"], size="1")),
                                rx.table.cell(rx.text(fold["mae"], size="1")),
                                rx.table.cell(rx.text(fold["mape"], size="1")),
                                rx.table.cell(rx.text(fold["rmse"], size="1")),
                            ),
                        ),
                    ),
                    size="2",
                    variant="surface",
                ),
                padding="4",
                border_radius="md",
                border="1px solid",
                border_color=rx.color("gray", 4),
                background=rx.color("gray", 1),
            ),

            # Note: Individual fold charts disabled due to Reflex 0.8.9 nested data limitation
            # validation_data arrays cannot be accessed in rx.foreach() lambda
            rx.callout(
                rx.vstack(
                    rx.text(
                        "Fold-by-fold charts temporarily unavailable",
                        weight="bold",
                        size="2"
                    ),
                    rx.text(
                        "Performance metrics for each fold are shown in the table above. "
                        "Individual Actual vs Predicted charts require nested data structure support.",
                        size="1",
                        color="gray"
                    ),
                    spacing="1",
                ),
                icon="info",
                color_scheme="blue",
                size="2",
            ),

            spacing="4",
            width="100%",
        ),
    )
