"""Algorithm Comparison Chart - Compare Prophet, Auto-ARIMA, XGBoost performance."""

import reflex as rx
from typing import Any


def algorithm_comparison_chart(state_class: Any) -> rx.Component:
    """
    Bar chart comparing 3 algorithms: Prophet, Auto-ARIMA, XGBoost.

    Shows validation MAPE for direct comparison.
    Lower MAPE = better performance.

    Args:
        state_class: ModelPerformanceState class reference with algorithm_comparison_data

    Returns:
        Recharts bar chart component
    """
    return rx.cond(
        state_class.algorithm_comparison_data.length() > 0,
        rx.vstack(
            # Training Condition Warnings
            rx.cond(
                state_class.training_conditions_match,
                rx.callout.root(
                    rx.callout.icon(rx.icon("circle-check-big")),
                    rx.vstack(
                        rx.foreach(
                            state_class.training_condition_warnings,
                            lambda warning: rx.text(warning, size="1"),
                        ),
                        spacing="1",
                    ),
                    color_scheme="green",
                    size="1",
                ),
                rx.callout.root(
                    rx.callout.icon(rx.icon("triangle-alert")),
                    rx.vstack(
                        rx.text(
                            "훈련 조건 불일치 경고",
                            weight="bold",
                            size="2",
                        ),
                        rx.foreach(
                            state_class.training_condition_warnings,
                            lambda warning: rx.text(warning, size="1"),
                        ),
                        rx.text(
                            "아래 비교 결과는 참고용으로만 사용하세요. "
                            "정확한 비교를 위해서는 동일 조건에서 모든 알고리즘을 훈련하는 것을 권장합니다.",
                            size="1",
                            color="gray",
                        ),
                        spacing="1",
                    ),
                    color_scheme="amber",
                    size="1",
                ),
            ),

            # Header with interpretation guide
            rx.callout.root(
                rx.callout.icon(rx.icon("info")),
                rx.callout.text(
                    "3가지 알고리즘의 Train MAE vs Validation MAE 비교 (낮을수록 우수)"
                ),
                color_scheme="purple",
                size="1",
            ),

            # Bar Chart - Train MAE vs Validation MAE
            rx.recharts.bar_chart(
                # X-axis - Model Names
                rx.recharts.x_axis(
                    data_key="model_name",
                ),

                # Y-axis - MAE
                rx.recharts.y_axis(
                    label={
                        "value": "MAE",
                        "angle": -90,
                        "position": "insideLeft"
                    },
                ),

                # Tooltip with custom formatter
                rx.recharts.graphing_tooltip(
                    content_style={
                        "backgroundColor": "var(--gray-1)",
                        "border": "1px solid var(--gray-6)",
                        "borderRadius": "8px",
                        "padding": "12px",
                    },
                    formatter=rx.Var.create(
                        """(value, name, props) => {
                            if (name === 'Train MAE') {
                                return [`${value ? value.toFixed(2) : 'N/A'}`, 'Train MAE'];
                            }
                            if (name === 'Validation MAE') {
                                return [`${value ? value.toFixed(2) : 'N/A'}`, 'Validation MAE'];
                            }
                            return [value, name];
                        }"""
                    ),
                ),

                # Legend
                rx.recharts.legend(
                    vertical_align="top",
                    height=36,
                ),

                # Grid
                rx.recharts.cartesian_grid(
                    stroke_dasharray="3 3",
                    opacity=0.3,
                ),

                # Train MAE Bar - Sky Blue (Design System)
                rx.recharts.bar(
                    data_key="train_mae",
                    fill=rx.color("blue", 8),
                    name="Train MAE",
                    radius=[8, 8, 0, 0],  # Rounded top corners
                ),

                # Validation MAE Bar - Brand Purple (Design System)
                rx.recharts.bar(
                    data_key="validation_mae",
                    fill=rx.color("purple", 9),
                    name="Validation MAE",
                    radius=[8, 8, 0, 0],  # Rounded top corners
                ),

                data=state_class.algorithm_comparison_data,
                width="100%",
                height=400,
            ),

            # Performance Summary Table
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("모델 ID"),
                        rx.table.column_header_cell("알고리즘"),
                        rx.table.column_header_cell("Train MAE"),
                        rx.table.column_header_cell("Val MAE"),
                        rx.table.column_header_cell("Val MAPE (%)"),
                        rx.table.column_header_cell("훈련 샘플"),
                        rx.table.column_header_cell("훈련 시간"),
                        rx.table.column_header_cell("순위"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        state_class.algorithm_comparison_data,
                        lambda algo: rx.table.row(
                            # Model ID
                            rx.table.cell(
                                rx.badge(
                                    "#" + algo["model_id"].to(str),
                                    color_scheme="gray",
                                    variant="outline",
                                    size="1",
                                )
                            ),

                            # Algorithm Name
                            rx.table.cell(
                                rx.badge(
                                    algo["model_name"],
                                    color_scheme=rx.cond(
                                        algo["rank"] == 1,
                                        "green",
                                        rx.cond(
                                            algo["rank"] == 2,
                                            "blue",
                                            "gray"
                                        )
                                    ),
                                    variant="soft",
                                    size="2",
                                )
                            ),

                            # Train MAE
                            rx.table.cell(
                                rx.text(
                                    rx.cond(
                                        algo["train_mae"].to(str) != "None",
                                        rx.cond(
                                            algo["train_mae"] == 0.0,
                                            "0.00",
                                            algo["train_mae"].to(str)
                                        ),
                                        "N/A"
                                    ),
                                    size="2",
                                    weight="medium",
                                    color="blue",
                                )
                            ),

                            # Validation MAE
                            rx.table.cell(
                                rx.text(
                                    rx.cond(
                                        algo["validation_mae"].to(str) != "None",
                                        rx.cond(
                                            algo["validation_mae"] == 0.0,
                                            "0.00",
                                            algo["validation_mae"].to(str)
                                        ),
                                        "N/A"
                                    ),
                                    size="2",
                                    weight="bold",
                                    color="purple",
                                )
                            ),

                            # Validation MAPE
                            rx.table.cell(
                                rx.text(
                                    rx.cond(
                                        algo["validation_mape"].to(str) != "None",
                                        rx.cond(
                                            algo["validation_mape"] == 0.0,
                                            "0.00%",
                                            algo["validation_mape"].to(str) + "%"
                                        ),
                                        "N/A"
                                    ),
                                    size="2",
                                    color="gray",
                                )
                            ),

                            # Training Samples
                            rx.table.cell(
                                rx.text(
                                    rx.cond(
                                        algo["training_samples"].to(str) != "None" & (algo["training_samples"] != 0),
                                        algo["training_samples"].to(str),
                                        "N/A"
                                    ),
                                    size="2",
                                    color="gray",
                                )
                            ),

                            # Training Time (created_at)
                            rx.table.cell(
                                rx.text(
                                    rx.cond(
                                        algo["created_at"] != "",
                                        algo["created_at"],
                                        "N/A"
                                    ),
                                    size="1",
                                    color="gray",
                                )
                            ),

                            # Rank
                            rx.table.cell(
                                rx.cond(
                                    algo["rank"] == 1,
                                    rx.badge(
                                        rx.hstack(
                                            rx.icon("trophy", size=12),
                                            rx.text("1위"),
                                            spacing="1",
                                        ),
                                        color_scheme="green",
                                        variant="soft",
                                    ),
                                    rx.badge(
                                        algo["rank"].to(str) + "위",
                                        color_scheme="gray",
                                        variant="soft",
                                    )
                                )
                            ),
                        ),
                    ),
                ),
                variant="surface",
                size="2",
            ),

            spacing="4",
            width="100%",
        ),

        # No data state
        rx.center(
            rx.vstack(
                rx.icon("bar-chart", size=48, color="gray"),
                rx.text(
                    "알고리즘 비교 데이터가 없습니다.",
                    size="4",
                    color="gray",
                    weight="medium",
                ),
                rx.callout.root(
                    rx.callout.icon(rx.icon("info")),
                    rx.vstack(
                        rx.text(
                            "비교 데이터가 표시되지 않는 이유:",
                            size="2",
                            weight="bold",
                        ),
                        rx.text(
                            "1. Training Wizard에서 아직 모델을 훈련하지 않았거나",
                            size="1",
                        ),
                        rx.text(
                            "2. 훈련된 모델에 검증 메트릭(validation_mape)이 저장되지 않았습니다.",
                            size="1",
                        ),
                        rx.text(
                            "Training Wizard에서 Prophet, Auto-ARIMA, XGBoost를 각각 훈련하고",
                            size="1",
                        ),
                        rx.text(
                            "모델 저장 시 검증 결과가 포함되도록 확인하세요.",
                            size="1",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    color_scheme="blue",
                    size="1",
                ),
                spacing="3",
                align="center",
                width="100%",
                max_width="600px",
            ),
            height="400px",
            padding="4",
        ),
    )


def best_algorithm_card(state_class: Any) -> rx.Component:
    """
    Card highlighting the best performing algorithm.

    Args:
        state_class: ModelPerformanceState class reference

    Returns:
        Card component
    """
    return rx.cond(
        state_class.best_algorithm != "",
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("trophy", size=24, color="gold"),
                    rx.heading("최고 성능 알고리즘", size="4"),
                    spacing="2",
                    align="center",
                ),

                rx.divider(),

                rx.hstack(
                    # Algorithm badge
                    rx.badge(
                        state_class.best_algorithm,
                        color_scheme="green",
                        variant="soft",
                        size="3",
                    ),

                    rx.vstack(
                        rx.text(
                            "Validation MAPE: " + state_class.best_algorithm_mape + "%",
                            size="3",
                            weight="bold",
                            color="green",
                        ),
                        rx.text(
                            state_class.best_algorithm_points + " validation points",
                            size="2",
                            color="gray",
                        ),
                        spacing="1",
                        align="start",
                    ),

                    spacing="4",
                    align="center",
                    width="100%",
                ),

                rx.callout.root(
                    rx.callout.icon(rx.icon("lightbulb")),
                    rx.callout.text(
                        "이 알고리즘은 검증 데이터에서 가장 낮은 MAPE를 기록했습니다. "
                        "실시간 예측에 배포를 고려하세요."
                    ),
                    color_scheme="green",
                    size="1",
                ),

                spacing="4",
                width="100%",
            ),
            size="2",
        ),
        rx.fragment(),
    )
