"""
Saved Data Display Component - Training Wizard
모델 저장 후 저장된 데이터 표시
"""

import reflex as rx
from reflex.utils import console


def saved_model_info_section(state_class) -> rx.Component:
    """저장된 모델 정보 표시 (상세)"""
    return rx.cond(
        state_class.show_saved_data,
        rx.vstack(
            rx.heading("✅ Model Saved Successfully", size="3", color="green"),

            # Success callout
            rx.callout(
                rx.vstack(
                    rx.text("Model has been saved to the database", weight="bold"),
                    rx.text("Model predictions have been stored for future reference", color="gray", size="2"),
                    spacing="2",
                ),
                icon="circle-check-big",
                color_scheme="green",
                size="3",
            ),

            # Model Information Grid
            rx.box(
                rx.heading("Model Information", size="2", margin_bottom="3"),
                rx.grid(
                    # Model ID Badge
                    rx.vstack(
                        rx.text("Model ID", size="1", color="gray"),
                        rx.badge(
                            state_class.trained_model_id,
                            color_scheme="blue",
                            size="2"
                        ),
                        spacing="1",
                        align="center",
                    ),
                    # Model Type
                    rx.vstack(
                        rx.text("Model Type", size="1", color="gray"),
                        rx.text(
                            state_class.selected_model,
                            size="3",
                            weight="bold",
                            color="blue"
                        ),
                        spacing="1",
                        align="center",
                    ),
                    # Tag Name
                    rx.vstack(
                        rx.text("Sensor Tag", size="1", color="gray"),
                        rx.text(
                            state_class.selected_tag,
                            size="3",
                            weight="bold"
                        ),
                        spacing="1",
                        align="center",
                    ),
                    # Forecast Horizon
                    rx.vstack(
                        rx.text("Forecast Horizon", size="1", color="gray"),
                        rx.text(
                            state_class.forecast_horizon,
                            size="3",
                            weight="bold",
                            color="purple"
                        ),
                        spacing="1",
                        align="center",
                    ),
                    # MAPE
                    rx.vstack(
                        rx.text("MAPE", size="1", color="gray"),
                        rx.text(
                            state_class.mape_value,
                            size="3",
                            weight="bold",
                            color="green"
                        ),
                        spacing="1",
                        align="center",
                    ),
                    # Status
                    rx.vstack(
                        rx.text("Status", size="1", color="gray"),
                        rx.badge(
                            "Active",
                            color_scheme="green",
                            size="2"
                        ),
                        spacing="1",
                        align="center",
                    ),
                    columns="3",
                    spacing="4",
                    width="100%",
                ),
                padding="4",
                border_radius="md",
                border="1px solid",
                border_color=rx.color("gray", 4),
                background=rx.color("gray", 1),
            ),

            spacing="4",
            width="100%",
        ),
    )
