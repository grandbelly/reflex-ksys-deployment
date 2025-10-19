"""Training Wizard - Step 3: Feature Configuration"""
import reflex as rx
from reflex.utils import console
from ...states.training_wizard_state import TrainingWizardState


def step_3_features() -> rx.Component:
    """Step 3: Feature Configuration"""
    console.log("DEBUG: step_3_features() called")
    return rx.card(
        rx.vstack(
            # Header with icon
            rx.hstack(
                rx.icon("wrench", size=24, color=rx.color("purple", 9)),
                rx.vstack(
                    rx.heading("Step 3: Configure Features", size="4"),
                    # Dynamic text based on selected model
                    rx.cond(
                        TrainingWizardState.selected_model == "auto_arima",
                        rx.text("Choose between pure ARIMA or add feature engineering", size="2", color="gray"),
                        rx.text("Configure feature engineering for your model", size="2", color="gray"),
                    ),
                    spacing="1",
                    align_items="start",
                ),
                spacing="3",
                align_items="center",
                width="100%",
            ),

            rx.divider(),

        rx.vstack(
            # Option 1: Skip Feature Engineering (Pure ARIMA) - Only for ARIMA
            rx.cond(
                TrainingWizardState.selected_model == "auto_arima",
                rx.box(
                    rx.checkbox(
                        "Use Pure Auto-ARIMA (no external features)",
                        checked=TrainingWizardState.skip_feature_engineering,
                        on_change=TrainingWizardState.toggle_skip_features,
                        size="3",
                    ),
                    padding="3",
                    border_radius="md",
                    bg=rx.color("purple", 2),
                    border="1px solid",
                    border_color=rx.color('purple', 6),
                    width="100%",
                ),
            ),

            # Feature Engineering Options (hidden if skipped)
            rx.cond(
                ~TrainingWizardState.skip_feature_engineering,
                rx.vstack(
                    rx.divider(),

                    # Create new or load existing
                    rx.hstack(
                        rx.button(
                            "Create New Configuration",
                            on_click=TrainingWizardState.toggle_feature_creator,
                            size="2",
                            variant="soft",
                            color_scheme="purple",
                        ),
                        spacing="2",
                        width="100%",
                    ),

                    # Feature Creator (collapsed by default)
                    rx.cond(
                        TrainingWizardState.show_feature_creator,
                        rx.box(
                            rx.vstack(
                                rx.heading("Create Feature Configuration", size="3"),

                                # Config name with validation
                                rx.vstack(
                                    rx.text("Configuration Name:", weight="bold"),
                                    rx.input(
                                        placeholder="e.g., my_features",
                                        value=TrainingWizardState.new_config_name,
                                        on_change=TrainingWizardState.set_new_config_name,
                                        width="100%",
                                    ),
                                    # Validation message
                                    rx.cond(
                                        TrainingWizardState.new_config_name != "",
                                        rx.text(
                                            TrainingWizardState.config_name_validation_message,
                                            size="2",
                                            color=rx.cond(
                                                TrainingWizardState.config_name_exists,
                                                "red",
                                                "green"
                                            ),
                                        ),
                                    ),
                                    spacing="1",
                                ),

                                # Rolling Features (optimized for RO membrane monitoring)
                                rx.vstack(
                                    rx.text("Rolling Window Features (10-min data):", weight="bold"),
                                    rx.text("Optimal ranges for fouling detection", size="1", color="gray"),
                                    rx.hstack(
                                        rx.checkbox("30min (3p) - rapid", value="3", on_change=lambda: TrainingWizardState.toggle_rolling_feature("3")),
                                        rx.checkbox("3h (18p) - trend", value="18", on_change=lambda: TrainingWizardState.toggle_rolling_feature("18")),
                                        rx.checkbox("12h (72p) - accumulation", value="72", on_change=lambda: TrainingWizardState.toggle_rolling_feature("72")),
                                        rx.checkbox("24h (144p) - cycle", value="144", on_change=lambda: TrainingWizardState.toggle_rolling_feature("144")),
                                        spacing="3",
                                        wrap="wrap",
                                    ),
                                    spacing="2",
                                ),

                                # Create button
                                rx.hstack(
                                    rx.button(
                                        "Cancel",
                                        on_click=TrainingWizardState.toggle_feature_creator,
                                        size="2",
                                        variant="soft",
                                        color_scheme="gray",
                                    ),
                                    rx.button(
                                        "Create Configuration",
                                        on_click=TrainingWizardState.create_feature_config,
                                        size="2",
                                        variant="solid",
                                        color_scheme="green",
                                        disabled=~TrainingWizardState.can_create_config,  # ✅ NEW: Disable if name exists
                                    ),
                                    spacing="2",
                                    justify="end",
                                    width="100%",
                                ),

                                spacing="4",
                            ),
                            padding="4",
                            border_radius="md",
                            border="1px solid",
                            border_color=rx.color('purple', 6),
                            bg=rx.color("purple", 2),
                        ),
                    ),

                    # Load existing config (only show if configs exist)
                    rx.cond(
                        TrainingWizardState.available_feature_configs.length() > 0,
                        rx.vstack(
                            rx.text("Or Load Existing Configuration:", weight="bold"),
                            rx.select(
                                TrainingWizardState.available_feature_configs,
                                placeholder="Select feature config...",
                                on_change=TrainingWizardState.load_feature_config,
                                width="100%",
                                size="3",
                            ),
                            spacing="2",
                        ),
                    ),

                    # Display loaded config
                    rx.cond(
                        TrainingWizardState.feature_config_loaded,
                        rx.box(
                            rx.vstack(
                                rx.heading("Loaded Features", size="3"),
                                rx.vstack(
                                    rx.heading(TrainingWizardState.feature_counts['rolling'], size="6", color="green"),
                                    rx.text("Rolling Window Features", size="2", color="gray"),
                                    align="center",
                                    spacing="1",
                                ),
                                spacing="3",
                            ),
                            padding="4",
                            border_radius="md",
                            border="1px solid",
                            border_color=rx.color('green', 6),
                            bg=rx.color("green", 2),
                        ),
                    ),

                    spacing="4",
                    width="100%",
                ),
            ),

            spacing="4",
            width="100%",
        ),

            spacing="4",
            width="100%",
        ),
        size="3",
        width="100%",
    )
