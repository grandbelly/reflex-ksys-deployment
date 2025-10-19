"""Training Wizard - Step 2: Model Selection"""
import reflex as rx
from reflex.utils import console
from ...states.training_wizard_state import TrainingWizardState
from ...utils.responsive import responsive_grid_columns


def step_2_model() -> rx.Component:
    """Step 2: Model Selection"""
    console.log("DEBUG: step_2_model() called")
    return rx.card(
        rx.vstack(
            # Header with icon
            rx.hstack(
                rx.icon("brain-circuit", size=24, color=rx.color("purple", 9)),
                rx.vstack(
                    rx.heading("Step 2: Select Model", size="4"),
                    rx.text("Choose the forecasting algorithm", size="2", color="gray"),
                    spacing="1",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
                width="100%",
            ),

            rx.divider(),

        rx.vstack(
            # Model cards
            rx.grid(
                # Auto ARIMA
                rx.box(
                    rx.vstack(
                        rx.heading("Auto ARIMA", size="3"),
                        rx.text("Automatic ARIMA with seasonal support", size="2", color="gray"),
                        rx.text("✓ Best for seasonal patterns", size="1", color="green"),
                        rx.text("✓ Automatic parameter tuning", size="1", color="green"),
                        rx.button(
                            "Select",
                            on_click=lambda: TrainingWizardState.set_selected_model("auto_arima"),
                            size="2",
                            width="100%",
                            variant=rx.cond(
                                TrainingWizardState.selected_model == "auto_arima",
                                "solid",
                                "soft"
                            ),
                            color_scheme="purple",
                        ),
                        spacing="2",
                    ),
                    padding="4",
                    border_radius="md",
                    border="2px solid",
                    border_color=rx.cond(TrainingWizardState.selected_model == 'auto_arima', rx.color('green', 8), rx.color('gray', 6)),
                    bg=rx.cond(
                        TrainingWizardState.selected_model == "auto_arima",
                        rx.color("green", 2),
                        rx.color("gray", 1)
                    ),
                    width="100%",
                    min_width="0",
                ),

                # Prophet
                rx.box(
                    rx.vstack(
                        rx.heading("Prophet", size="3"),
                        rx.text("Facebook's forecasting tool", size="2", color="gray"),
                        rx.text("✓ Handles missing data well", size="1", color="green"),
                        rx.text("✓ Good for trends", size="1", color="green"),
                        rx.button(
                            "Select",
                            on_click=lambda: TrainingWizardState.set_selected_model("prophet"),
                            size="2",
                            width="100%",
                            variant=rx.cond(
                                TrainingWizardState.selected_model == "prophet",
                                "solid",
                                "soft"
                            ),
                            color_scheme="purple",
                        ),
                        spacing="2",
                    ),
                    padding="4",
                    border_radius="md",
                    border="2px solid",
                    border_color=rx.cond(TrainingWizardState.selected_model == 'prophet', rx.color('blue', 8), rx.color('gray', 6)),
                    bg=rx.cond(
                        TrainingWizardState.selected_model == "prophet",
                        rx.color("blue", 2),
                        rx.color("gray", 1)
                    ),
                    width="100%",
                    min_width="0",
                ),

                # XGBoost
                rx.box(
                    rx.vstack(
                        rx.heading("XGBoost", size="3"),
                        rx.text("Gradient boosting algorithm", size="2", color="gray"),
                        rx.text("✓ High accuracy", size="1", color="green"),
                        rx.text("⚠ Requires features", size="1", color="orange"),
                        rx.button(
                            "Select",
                            on_click=lambda: TrainingWizardState.set_selected_model("xgboost"),
                            size="2",
                            width="100%",
                            variant=rx.cond(
                                TrainingWizardState.selected_model == "xgboost",
                                "solid",
                                "soft"
                            ),
                            color_scheme="purple",
                        ),
                        spacing="2",
                    ),
                    padding="4",
                    border_radius="md",
                    border="2px solid",
                    border_color=rx.cond(TrainingWizardState.selected_model == 'xgboost', rx.color('purple', 8), rx.color('gray', 6)),
                    bg=rx.cond(
                        TrainingWizardState.selected_model == "xgboost",
                        rx.color("purple", 2),
                        rx.color("gray", 1)
                    ),
                    width="100%",
                    min_width="0",
                ),

                columns=responsive_grid_columns(mobile=1, tablet=2, desktop=3),
                gap="4",
                width="100%",
            ),

            spacing="3",
            width="100%",
        ),

            spacing="4",
            width="100%",
        ),
        size="3",
        width="100%",
    )
