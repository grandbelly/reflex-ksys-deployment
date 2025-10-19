"""Pipeline Detail Card - Compact display of ML pipeline configuration."""

import reflex as rx


def pipeline_detail_card(model: rx.Var) -> rx.Component:
    """Display compact ML pipeline configuration for side-by-side comparison.

    Designed for 3-column grid layout with concise information.
    Uses flattened hyperparameters from model_performance_state.
    """

    return rx.card(
        rx.vstack(
            # Header - Compact
            rx.vstack(
                rx.hstack(
                    rx.badge(
                        model["model_type"],
                        color_scheme="purple",
                        variant="solid",
                        size="2"
                    ),
                    rx.badge(
                        "v" + model["version"].to(str),
                        color_scheme="gray",
                        variant="soft",
                        size="1"
                    ),
                    spacing="2",
                    align="center",
                    justify="center",
                ),
                spacing="1",
                align="center",
                width="100%",
            ),

            rx.divider(),

            # Performance Metrics - Prominent at top
            rx.grid(
                rx.vstack(
                    rx.text("Val MAE", size="1", color="gray", weight="medium"),
                    rx.text(
                        rx.cond(
                            model["validation_mae"],
                            model["validation_mae"].to(str),
                            "N/A"
                        ),
                        size="4",
                        weight="bold",
                        color=rx.color("purple", 11)
                    ),
                    spacing="0",
                    align="center",
                ),
                rx.vstack(
                    rx.text("MAPE", size="1", color="gray", weight="medium"),
                    rx.text(
                        rx.cond(
                            model["validation_mape"],
                            model["validation_mape"].to(str) + "%",
                            "N/A"
                        ),
                        size="4",
                        weight="bold",
                        color=rx.color("blue", 11)
                    ),
                    spacing="0",
                    align="center",
                ),
                columns="2",
                spacing="3",
                width="100%",
                padding="2",
                border_radius="md",
                bg=rx.color("purple", 2),
            ),

            rx.divider(),

            # Pipeline Configuration - Using flattened fields
            rx.vstack(
                rx.text("파이프라인 구성", size="2", weight="bold"),

                # Preprocessing
                rx.vstack(
                    rx.text("전처리:", size="1", weight="bold", color=rx.color("blue", 9)),
                    rx.cond(
                        model["enable_preprocessing"],
                        rx.vstack(
                            rx.text(
                                f"✓ Outlier removal (Z-score: {model['outlier_threshold']})",
                                size="1",
                                color="gray"
                            ),
                            rx.text("✓ Interpolation (linear)", size="1", color="gray"),
                            rx.text("✓ Missing value handling", size="1", color="gray"),
                            spacing="1",
                            align_items="start",
                        ),
                        rx.text("✗ No preprocessing", size="1", color="gray"),
                    ),
                    spacing="1",
                    align_items="start",
                    width="100%",
                ),

                # Feature Engineering
                rx.cond(
                    (model["model_type"] == "XGBOOST") | (model["feature_config_name"] != ""),
                    rx.vstack(
                        rx.text("피처 엔지니어링:", size="1", weight="bold", color=rx.color("green", 9)),
                        rx.cond(
                            model["feature_config_name"] != "",
                            rx.vstack(
                                rx.text(f"✓ Config: {model['feature_config_name']}", size="1", color="gray"),
                                rx.text("✓ Lag features (1h, 6h, 24h)", size="1", color="gray"),
                                rx.text("✓ Rolling stats (6h, 24h)", size="1", color="gray"),
                                rx.text("✓ Time features (hour, day)", size="1", color="gray"),
                                spacing="1",
                                align_items="start",
                            ),
                            rx.text("✗ No feature engineering", size="1", color="gray"),
                        ),
                        spacing="1",
                        align_items="start",
                        width="100%",
                    ),
                    rx.box(),  # Empty box for models that don't need feature engineering
                ),

                # Model-specific parameters
                rx.vstack(
                    rx.text("모델 파라미터:", size="1", weight="bold", color=rx.color("purple", 9)),
                    rx.cond(
                        model["model_type"] == "AUTO_ARIMA",
                        rx.vstack(
                            rx.text(f"✓ Season length: {model['season_length']}", size="1", color="gray"),
                            rx.text(f"✓ Forecast horizon: {model['forecast_horizon']}h", size="1", color="gray"),
                            rx.text(f"✓ Training days: {model['training_days']}d", size="1", color="gray"),
                            spacing="1",
                            align_items="start",
                        ),
                        rx.cond(
                            model["model_type"] == "PROPHET",
                            rx.vstack(
                                rx.text(f"✓ Forecast horizon: {model['forecast_horizon']}h", size="1", color="gray"),
                                rx.text(f"✓ Training days: {model['training_days']}d", size="1", color="gray"),
                                rx.text("✓ Auto seasonality detection", size="1", color="gray"),
                                spacing="1",
                                align_items="start",
                            ),
                            rx.cond(
                                model["model_type"] == "XGBOOST",
                                rx.vstack(
                                    rx.text(f"✓ Forecast horizon: {model['forecast_horizon']}h", size="1", color="gray"),
                                    rx.text(f"✓ Training days: {model['training_days']}d", size="1", color="gray"),
                                    rx.text("✓ Gradient boosting", size="1", color="gray"),
                                    spacing="1",
                                    align_items="start",
                                ),
                                rx.text("N/A", size="1", color="gray"),
                            ),
                        ),
                    ),
                    spacing="1",
                    align_items="start",
                    width="100%",
                ),

                spacing="2",
                align_items="start",
                width="100%",
            ),

            spacing="3",
            width="100%",
        ),
        size="1",  # Smaller card size for compact layout
        height="100%",  # Equal height cards
    )
