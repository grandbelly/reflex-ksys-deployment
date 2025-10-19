"""Model Performance Page - Monitor and deploy ML models - REDESIGNED."""

import reflex as rx
from ..states.model_performance_state import ModelPerformanceState as M
from ..components.layout import shell
from ..components.page_header import page_header
from ..components.performance_charts import (
    model_comparison_chart,
    saved_models_table,
    deployed_model_info_card,
)
from ..components.pipeline_detail_card import pipeline_detail_card
from ..components.algorithm_comparison_chart import (
    algorithm_comparison_chart,
    best_algorithm_card,
)
from ..utils.responsive import responsive_grid_columns


def control_panel() -> rx.Component:
    """Control panel - sensor selection and refresh - HORIZONTAL LAYOUT."""
    return rx.card(
        rx.hstack(
            # Sensor Selection
            rx.hstack(
                rx.text("센서:", size="2", weight="medium", color="gray"),
                rx.select.root(
                    rx.select.trigger(placeholder="센서 선택"),
                    rx.select.content(
                        rx.foreach(
                            M.available_sensors,
                            lambda sensor: rx.select.item(sensor, value=sensor),
                        ),
                    ),
                    value=M.selected_sensor,
                    on_change=M.set_selected_sensor,
                    size="2",
                ),
                spacing="2",
                align="center",
            ),

            rx.divider(orientation="vertical", size="4"),

            # Refresh Button
            rx.button(
                rx.icon("refresh-cw", size=16),
                "새로고침",
                on_click=M.refresh_data,
                loading=M.is_loading,
                size="2",
                variant="soft",
                color_scheme="purple",
            ),

            rx.spacer(),

            # Status
            rx.cond(
                M.last_update != "",
                rx.badge(
                    rx.hstack(
                        rx.icon("clock", size=12),
                        rx.text("업데이트: " + M.last_update, size="1"),
                        spacing="1",
                    ),
                    color_scheme="green",
                    variant="soft",
                ),
                rx.fragment(),
            ),

            spacing="4",
            align="center",
            width="100%",
        ),
        size="2",
        width="100%",
    )


@rx.page(
    route="/model-performance",
    title="모델 성능 - KSYS",
    on_load=M.on_mount,
)
def model_performance() -> rx.Component:
    """Model performance monitoring and deployment dashboard - REDESIGNED.

    Focuses on:
    1. Deployed model info (current real-time prediction)
    2. Saved models table (offline simulations with deploy buttons)
    3. Model comparison chart (performance comparison)
    """
    return shell(
        rx.container(
            rx.vstack(
                # Page Header
                page_header(
                    title="모델 성능 모니터링",
                    icon="chart-no-axes-column",
                    subtitle="ML 모델 배포 관리 및 성능 비교",
                ),

                # Error Display
                rx.cond(
                    M.error_message != "",
                    rx.callout.root(
                        rx.callout.icon(rx.icon("triangle-alert")),
                        rx.callout.text(M.error_message),
                        color_scheme="red",
                        size="2",
                    ),
                    rx.fragment(),
                ),

                # Control Panel (Horizontal)
                control_panel(),

                rx.divider(),

                # Section 1: Algorithm Comparison (Prophet, Auto-ARIMA, XGBoost)
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("trophy", size=20, color=rx.color("purple", 9)),
                            rx.heading("알고리즘 성능 비교", size="4"),
                            rx.spacer(),
                            rx.badge(
                                "Prophet / Auto-ARIMA / XGBoost",
                                color_scheme="purple",
                                variant="soft",
                            ),
                            spacing="2",
                            align="center",
                            width="100%",
                        ),

                        rx.callout.root(
                            rx.callout.icon(rx.icon("info")),
                            rx.callout.text(
                                "Training Wizard에서 훈련된 3가지 알고리즘의 검증 성능을 비교합니다. "
                                "MAPE가 낮을수록 예측 정확도가 높습니다."
                            ),
                            color_scheme="purple",
                            size="1",
                        ),

                        rx.divider(),

                        algorithm_comparison_chart(M),

                        spacing="4",
                        width="100%",
                    ),
                    size="2",
                    width="100%",
                ),

            # Best Algorithm Highlight
            best_algorithm_card(M),

            # Section 2: Deployed Model Info
            deployed_model_info_card(M),

            # Section 3: Saved Models Table
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.icon("layers", size=20, color=rx.color("blue", 9)),
                        rx.heading("저장된 모델 목록 (오프라인 시뮬레이션)", size="4"),
                        rx.spacer(),
                        rx.badge(
                            f"{M.saved_models.length()} 모델",
                            color_scheme="blue",
                            variant="soft",
                        ),
                        spacing="2",
                        align="center",
                        width="100%",
                    ),

                    rx.callout.root(
                        rx.callout.icon(rx.icon("info")),
                        rx.callout.text(
                            "Training Wizard에서 훈련된 모델들입니다. 최적 모델을 선택하고 '배포' 버튼을 클릭하면 실시간 예측 시스템에 적용됩니다."
                        ),
                        color_scheme="purple",
                        size="1",
                    ),

                    rx.divider(),

                    saved_models_table(M),

                    spacing="4",
                    width="100%",
                ),
                size="2",
                width="100%",
            ),

            # Section 4: Pipeline Details (Top 3 + Deployed only) - HORIZONTAL GRID
            rx.cond(
                M.pipeline_display_models.length() > 0,
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("settings", size=20, color=rx.color("purple", 9)),
                            rx.heading("ML 파이프라인 비교", size="4"),
                            rx.spacer(),
                            rx.badge(
                                f"{M.pipeline_display_models.length()}개 모델",
                                color_scheme="purple",
                                variant="soft",
                            ),
                            spacing="2",
                            align="center",
                            width="100%",
                        ),

                        rx.callout.root(
                            rx.callout.icon(rx.icon("info")),
                            rx.callout.text(
                                "성능 상위 3개 모델의 파이프라인을 가로로 비교합니다. 전처리, 피처 엔지니어링, 후처리 설정을 한눈에 확인하세요."
                            ),
                            color_scheme="purple",
                            size="1",
                        ),

                        rx.divider(),

                        # ✅ CHANGED: Display pipeline cards in RESPONSIVE GRID
                        rx.grid(
                            rx.foreach(
                                M.pipeline_display_models,
                                lambda model: pipeline_detail_card(model),
                            ),
                            columns=responsive_grid_columns(mobile=1, tablet=2, desktop=3),
                            spacing="4",
                            width="100%",
                        ),

                        spacing="4",
                        width="100%",
                    ),
                    size="2",
                    width="100%",
                ),
                rx.fragment(),
            ),

                spacing="4",
                width="100%",
            ),
            size="4",
            padding_x="6",
            padding_y="4",
        ),
        active_route="/model-performance"
    )
