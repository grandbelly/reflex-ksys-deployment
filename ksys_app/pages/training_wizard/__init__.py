"""
Training Wizard - Modular Components
Separated into individual step files for better maintainability

Route: /training-wizard
"""

import reflex as rx
from reflex.utils import console
from ...states.training_wizard_state import TrainingWizardState
from ...components.layout import shell
from ...utils.responsive import responsive_grid_columns, GRID_PRESETS

# Import step components
from .step_1_sensor import step_1_sensor
from .step_2_model import step_2_model
from .step_3_features import step_3_features
from .step_4_params import step_4_params
from .step_5_training import step_5_training
from .step_6_results import step_6_results

# Import header and navigation
from .header import wizard_header
from .navigation import wizard_navigation, error_display


@rx.page("/training-wizard", on_load=TrainingWizardState.initialize_wizard)
def training_wizard_page() -> rx.Component:
    """Training Wizard Page - Sequential Workflow"""
    console.log("DEBUG: training_wizard_page() called")
    return shell(
        rx.container(
            rx.vstack(
                # Header with progress
                wizard_header(),

                # Error display
                error_display(),

                # Main content area - show current step
                rx.box(
                    rx.cond(
                        TrainingWizardState.wizard_step == 1,
                        step_1_sensor(),
                        rx.cond(
                            TrainingWizardState.wizard_step == 2,
                            step_2_model(),
                            rx.cond(
                                TrainingWizardState.wizard_step == 3,
                                step_3_features(),
                                rx.cond(
                                    TrainingWizardState.wizard_step == 4,
                                    step_4_params(),
                                    rx.cond(
                                        TrainingWizardState.wizard_step == 5,
                                        step_5_training(),
                                        step_6_results(),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    width="100%",
                ),

                # Navigation
                wizard_navigation(),

                spacing="4",
                width="100%",
            ),
            size="4",
            padding_x="6",
            padding_y="4"
        ),
        active_route="/training-wizard"
    )


# Export all components for direct import if needed
__all__ = [
    "training_wizard_page",
    "step_1_sensor",
    "step_2_model",
    "step_3_features",
    "step_4_params",
    "step_5_training",
    "step_6_results",
    "wizard_header",
    "wizard_navigation",
    "error_display",
]
