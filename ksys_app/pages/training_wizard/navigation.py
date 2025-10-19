"""Training Wizard - Navigation and Error Display Components"""
import reflex as rx
from reflex.utils import console
from ...states.training_wizard_state import TrainingWizardState


def wizard_navigation() -> rx.Component:
    """Navigation buttons"""
    console.log("DEBUG: wizard_navigation() called")
    return rx.card(
        rx.hstack(
            # Previous button
            rx.cond(
                TrainingWizardState.wizard_step > 1,
                rx.button(
                    rx.icon("chevron-left", size=16),
                    "Previous",
                    on_click=TrainingWizardState.previous_step,
                    size="2",
                    variant="soft",
                    color_scheme="gray",
                ),
                rx.box(),  # Empty box when condition is false
            ),

            rx.spacer(),

            # Next button
            rx.cond(
                TrainingWizardState.wizard_step < 6,
                rx.button(
                    "Next",
                    rx.icon("chevron-right", size=16),
                    on_click=TrainingWizardState.next_step,
                    size="2",
                    color_scheme="purple",
                    disabled=~TrainingWizardState.can_proceed,
                ),
                rx.box(),  # Empty box when condition is false
            ),

            width="100%",
            align_items="center",
        ),
        size="2",
        width="100%",
    )


def error_display() -> rx.Component:
    """Error display"""
    console.log("DEBUG: error_display() called")
    return rx.cond(
        TrainingWizardState.error_message,
        rx.callout.root(
            rx.callout.icon(rx.icon("triangle-alert")),
            rx.callout.text(TrainingWizardState.error_message),
            color_scheme="red",
            size="1",
        ),
        rx.box(),  # Empty box when no error
    )
