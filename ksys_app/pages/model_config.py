"""
Model Configuration Page

Dynamic model hyperparameter editor.
NO hardcoded values - all parameters loaded from database schema.

Features:
- Select model type (AutoARIMA, Prophet, XGBoost, Ensemble)
- Automatically render form based on schema
- Save/Load/Clone/Delete configurations
- Validation before save
- View all saved model configs
"""

import reflex as rx
from ..states.model_config_state import ModelConfigState, render_param_input


def config_editor() -> rx.Component:
    """Dynamic configuration editor"""
    return rx.vstack(
        rx.heading("Model Configuration Editor", size="5"),

        # Error/Success messages
        rx.cond(
            ModelConfigState.error_message,
            rx.callout(
                ModelConfigState.error_message,
                color_scheme="red",
                icon="triangle-alert",
            ),
        ),
        rx.cond(
            ModelConfigState.success_message,
            rx.callout(
                ModelConfigState.success_message,
                color_scheme="green",
                icon="circle-check",
            ),
        ),

        # Validation errors
        rx.cond(
            ModelConfigState.validation_errors.length() > 0,
            rx.callout(
                rx.vstack(
                    rx.text("Validation errors:", weight="bold"),
                    rx.foreach(
                        ModelConfigState.validation_errors,
                        lambda err: rx.text(f"• {err}", size="1"),
                    ),
                    spacing="1",
                ),
                color_scheme="red",
                icon="triangle-alert",
            ),
        ),

        # Tag and Model Type Selection
        rx.hstack(
            rx.vstack(
                rx.text("Tag:", weight="bold"),
                rx.select(
                    ["INLET_PRESSURE", "FEED_FLOW", "FEED_COND", "OUTLET_PRESSURE"],
                    value=ModelConfigState.selected_tag,
                    on_change=ModelConfigState.set_selected_tag,
                ),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Model Type:", weight="bold"),
                rx.select(
                    ModelConfigState.available_model_types,
                    value=ModelConfigState.selected_model_type,
                    on_change=ModelConfigState.set_selected_model_type,
                ),
                spacing="1",
            ),
            rx.button(
                "Load Schema",
                on_click=ModelConfigState.load_schema,
                loading=ModelConfigState.is_loading,
            ),
            spacing="4",
            align="end",
        ),

        # Dynamic Parameter Form
        rx.cond(
            ModelConfigState.model_schema,
            rx.vstack(
                rx.heading("Parameters", size="4"),

                # Dynamically render inputs based on schema
                rx.foreach(
                    ModelConfigState.model_schema,
                    lambda item: render_param_input(item[0], item[1]),
                ),

                # Actions
                rx.hstack(
                    rx.button(
                        "Reset to Default",
                        on_click=ModelConfigState.reset_to_default,
                        variant="soft",
                    ),
                    rx.button(
                        "Save Configuration",
                        on_click=ModelConfigState.save_config,
                        loading=ModelConfigState.is_saving,
                        color_scheme="green",
                    ),
                    spacing="2",
                ),

                spacing="3",
                padding="4",
                border_radius="md",
                border=f"1px solid {rx.color('gray', 6)}",
            ),
            rx.text("Select a model type and click Load Schema", color="gray"),
        ),

        spacing="4",
    )


def saved_models_list() -> rx.Component:
    """List of saved model configurations"""
    return rx.vstack(
        rx.hstack(
            rx.heading("Saved Models", size="5"),
            rx.button(
                "Refresh",
                on_click=ModelConfigState.load_saved_models,
                size="2",
                variant="soft",
            ),
            spacing="2",
            align="center",
        ),

        rx.cond(
            ModelConfigState.saved_models.length() > 0,
            rx.vstack(
                rx.foreach(
                    ModelConfigState.saved_models,
                    lambda model: rx.box(
                        rx.hstack(
                            rx.vstack(
                                rx.text(model["model_name"], weight="bold"),
                                rx.hstack(
                                    rx.badge(model["model_type"], color_scheme="blue"),
                                    rx.badge(f"v{model['version']}", color_scheme="gray"),
                                    rx.cond(
                                        model["train_mape"],
                                        rx.badge(
                                            f"MAPE: {model['train_mape']:.2f}%",
                                            color_scheme="green",
                                        ),
                                    ),
                                    spacing="1",
                                ),
                                rx.text(
                                    f"Created: {model['created_at'][:19]}",
                                    size="1",
                                    color="gray",
                                ),
                                spacing="1",
                                align="start",
                            ),

                            rx.spacer(),

                            rx.hstack(
                                rx.button(
                                    "Load",
                                    on_click=lambda: ModelConfigState.load_model_config(model["model_id"]),
                                    size="2",
                                    variant="soft",
                                ),
                                rx.button(
                                    "Clone",
                                    on_click=lambda: ModelConfigState.clone_model(model["model_id"]),
                                    size="2",
                                    variant="soft",
                                    color_scheme="blue",
                                ),
                                rx.button(
                                    "Delete",
                                    on_click=lambda: ModelConfigState.delete_model(model["model_id"]),
                                    size="2",
                                    variant="soft",
                                    color_scheme="red",
                                ),
                                spacing="1",
                            ),

                            width="100%",
                            align="center",
                        ),

                        # Show hyperparameters
                        rx.cond(
                            model["hyperparameters"],
                            rx.box(
                                rx.text("Hyperparameters:", size="1", weight="bold", color="gray"),
                                rx.text(
                                    rx.format("{}", model["hyperparameters"]),
                                    size="1",
                                    color="gray",
                                    style={"fontFamily": "monospace"},
                                ),
                                padding_top="2",
                            ),
                        ),

                        padding="3",
                        border_radius="md",
                        border=f"1px solid {rx.color('gray', 6)}",
                    ),
                ),
                spacing="2",
            ),
            rx.text("No saved models found for this tag", color="gray"),
        ),

        spacing="3",
    )


@rx.page("/model-config", on_load=[
    ModelConfigState.load_schema,
    ModelConfigState.load_saved_models
])
def model_config_page() -> rx.Component:
    """Model configuration page"""
    return rx.box(
        rx.vstack(
            rx.heading("Model Hyperparameter Configuration", size="6"),
            rx.text("Configure model parameters without hardcoding - all settings stored in database"),

            rx.grid(
                # Left: Editor
                config_editor(),

                # Right: Saved models
                saved_models_list(),

                columns="2",
                spacing="6",
            ),

            spacing="4",
            width="100%",
            max_width="1400px",
        ),
        padding="6",
    )
