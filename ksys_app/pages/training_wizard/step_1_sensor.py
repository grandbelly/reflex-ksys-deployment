"""
Training Wizard - Step 1: Sensor Selection
센서 선택 단계
"""

import reflex as rx
from reflex.utils import console
from ...states.training_wizard_state import TrainingWizardState


def step_1_sensor() -> rx.Component:
    """Step 1: Sensor Selection"""
    console.log("DEBUG: step_1_sensor() called")
    return rx.card(
        rx.vstack(
            # Header with icon
            rx.hstack(
                rx.icon("gauge", size=24, color=rx.color("purple", 9)),
                rx.vstack(
                    rx.heading("Step 1: Select Sensor", size="4"),
                    rx.text("Choose the sensor tag you want to train a model for", size="2", color="gray"),
                    spacing="1",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
                width="100%",
            ),

            rx.divider(),

            # Info callout
            rx.callout.root(
                rx.callout.icon(rx.icon("info")),
                rx.callout.text(
                    "센서를 선택하면 해당 센서의 과거 데이터를 기반으로 예측 모델을 학습합니다.",
                    size="1"
                ),
                color_scheme="purple",
                size="1",
            ),

            # Sensor selection
            rx.vstack(
                rx.text("센서 태그:", weight="bold", size="2"),
                rx.select(
                    TrainingWizardState.available_tags,
                    placeholder="Select sensor tag...",
                    value=TrainingWizardState.selected_tag,
                    on_change=TrainingWizardState.set_selected_tag,
                    width="100%",
                    size="3",
                ),

                rx.cond(
                    TrainingWizardState.selected_tag,
                    rx.callout.root(
                        rx.callout.icon(rx.icon("circle-check")),
                        rx.callout.text(
                            f"Selected: {TrainingWizardState.selected_tag}",
                            size="2"
                        ),
                        color_scheme="green",
                        size="1",
                    ),
                ),

                spacing="2",
                width="100%",
            ),

            spacing="4",
            width="100%",
        ),
        size="3",
        width="100%",
    )
