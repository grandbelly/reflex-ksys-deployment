"""
Fixed Forecast Player Page - Properly styled with metric cards, zones, and table
"""
import reflex as rx
from ..states.forecast_player_state import ForecastPlayerState as FPS
from ..components.layout import shell
from ..components.page_header import page_header
from ..utils.responsive import responsive_grid_columns


# =========================================================================
# TOP METRIC CARDS (설계 화면처럼 3개 카드)
# =========================================================================

def metric_card(title: str, value: str, color: str, icon: str) -> rx.Component:
    """Individual metric card with colored background"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=20, color="white"),
                rx.text(title, size="2", color="white", opacity=0.9),
                spacing="2",
                align="center"
            ),
            rx.heading(value, size="6", color="white", weight="bold"),
            spacing="2",
            align="start"
        ),
        style={
            "background": color,
            "border": "none",
            "padding": "1.5rem",
            "width": "100%"
        }
    )


def metrics_header() -> rx.Component:
    """Top metrics display with 3 cards like design - RESPONSIVE"""
    return rx.grid(
        # MAPE Card - Green
        metric_card(
            "평균 절대 오차 (MAPE)",
            FPS.mape_display,
            "linear-gradient(135deg, #10b981 0%, #059669 100%)",
            "trending-up"
        ),

        # R² Score Card - Purple
        metric_card(
            "모델 설명력 (R²)",
            FPS.r2_display,
            "linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)",
            "bar-chart-2"
        ),

        # Accuracy Card - Pink
        metric_card(
            "예측 정확도",
            FPS.accuracy_percentage_display,
            "linear-gradient(135deg, #ec4899 0%, #db2777 100%)",
            "target"
        ),

        columns=responsive_grid_columns(mobile=1, tablet=2, desktop=3),
        spacing="4",
        width="100%"
    )


# =========================================================================
# SYSTEM STATUS CARDS (좌측 패널)
# =========================================================================

def system_status_panel() -> rx.Component:
    """System status information panel"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("activity", size=20, color=rx.color("blue", 9)),
                rx.heading("시스템 정보", size="3"),
                spacing="2"
            ),
            rx.divider(),
            rx.vstack(
                rx.hstack(
                    rx.text("센서명:", size="2", color=rx.color("gray", 10)),
                    rx.text(FPS.selected_tag_name, size="2", weight="bold"),
                    justify="between",
                    width="100%"
                ),
                rx.hstack(
                    rx.text("예측 횟수:", size="2", color=rx.color("gray", 10)),
                    rx.text(f"{FPS.total_predictions_count}", size="2", weight="bold"),
                    justify="between",
                    width="100%"
                ),
                rx.hstack(
                    rx.text("갱신 주기:", size="2", color=rx.color("gray", 10)),
                    rx.text(FPS.forecast_interval_display, size="2", weight="bold"),
                    justify="between",
                    width="100%"
                ),
                rx.hstack(
                    rx.text("모델:", size="2", color=rx.color("gray", 10)),
                    rx.text(
                        FPS.current_model_type,
                        size="2",
                        weight="bold"
                    ),
                    justify="between",
                    width="100%"
                ),
                rx.hstack(
                    rx.text("데이터 윈도우:", size="2", color=rx.color("gray", 10)),
                    rx.text(f"{FPS.chart_data.length()} points", size="2", weight="bold"),
                    justify="between",
                    width="100%"
                ),
                rx.hstack(
                    rx.text("예측 호라이즌:", size="2", color=rx.color("gray", 10)),
                    rx.text(
                        FPS.forecast_horizon_display,
                        size="2",
                        weight="bold"
                    ),
                    justify="between",
                    width="100%"
                ),
                spacing="3",
                width="100%"
            ),
            spacing="3",
            width="100%"
        ),
        style={"height": "100%"}
    )


def recent_updates_panel() -> rx.Component:
    """Recent update information panel"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("clock", size=20, color=rx.color("green", 9)),
                rx.heading("업데이트 현황", size="3"),
                spacing="2"
            ),
            rx.divider(),
            rx.vstack(
                # T0 Reference Time (기준 시간)
                rx.hstack(
                    rx.text("T0 기준 시간:", size="2", color=rx.color("gray", 10)),
                    rx.text(FPS.t0_reference_time_display, size="2", weight="bold", color=rx.color("purple", 11)),
                    justify="between",
                    width="100%"
                ),

                # Last Update Time
                rx.hstack(
                    rx.text("마지막 업데이트:", size="2", color=rx.color("gray", 10)),
                    rx.text(FPS.last_update, size="2", weight="bold", color=rx.color("blue", 11)),
                    justify="between",
                    width="100%"
                ),

                # Scheduler Status (forecast-scheduler container)
                rx.hstack(
                    rx.text("예측 스케줄러:", size="2", color=rx.color("gray", 10)),
                    rx.cond(
                        FPS.scheduler_running,
                        rx.badge("정상 작동", color_scheme="blue", variant="solid", size="2"),
                        rx.badge("중지됨", color_scheme="red", variant="soft", size="2")
                    ),
                    justify="between",
                    width="100%"
                ),

                # Next Forecast Countdown (from cache)
                rx.hstack(
                    rx.text("다음 예측:", size="2", color=rx.color("gray", 10)),
                    rx.badge(
                        FPS.next_forecast_time_display,
                        color_scheme="green",
                        variant="soft",
                        size="2"
                    ),
                    justify="between",
                    width="100%"
                ),

                spacing="3",
                width="100%"
            ),
            spacing="3",
            width="100%"
        ),
        style={"height": "100%"}
    )


# =========================================================================
# ENHANCED CHART WITH ZONES (설계처럼 구역 표시)
# =========================================================================

def enhanced_forecast_chart() -> rx.Component:
    """Enhanced chart with proper zones and colors - LINE CHARTS ONLY"""
    return rx.card(
        rx.vstack(
            rx.heading("시계열 트렌드 차트 (Rolling Window)", size="4"),
            rx.recharts.composed_chart(
                    # Past Zone Background (파란색 영역)
                    rx.recharts.reference_area(
                        x1=FPS.past_zone_start,
                        x2=FPS.t0_label,
                        fill="#3b82f6",
                        fill_opacity=0.05,
                        stroke="#3b82f6",
                        stroke_width=1,
                        stroke_dasharray="3 3",
                        label="과거 (Past)"
                    ),

                    # Future Zone Background (주황색 영역)
                    rx.recharts.reference_area(
                        x1=FPS.t0_label,
                        x2=FPS.future_zone_end,
                        fill="#f97316",
                        fill_opacity=0.05,
                        stroke="#f97316",
                        stroke_width=1,
                        stroke_dasharray="3 3",
                        label="미래 (Future)"
                    ),

                    # T0 Reference Line (빨간 수직선)
                    rx.recharts.reference_line(
                        x=FPS.t0_label,
                        stroke="#ef4444",
                        stroke_width=2,
                        stroke_dasharray="5 5",
                        label="T0"
                    ),

                    # Confidence Interval Upper Line (dashed)
                    rx.recharts.line(
                        data_key="ci_upper",
                        stroke="#f97316",
                        stroke_width=1,
                        stroke_dasharray="3 3",
                        dot=False,
                        name="Upper CI",
                        connect_nulls=True
                    ),

                    # Confidence Interval Lower Line (dashed)
                    rx.recharts.line(
                        data_key="ci_lower",
                        stroke="#f97316",
                        stroke_width=1,
                        stroke_dasharray="3 3",
                        dot=False,
                        name="Lower CI",
                        connect_nulls=True
                    ),

                    # Predicted Values Line (주황색 실선) - SWAPPED TO FIRST
                    rx.recharts.line(
                        data_key="predicted_value",
                        stroke="#f97316",
                        stroke_width=3,
                        dot={"r": 4, "fill": "#f97316"},
                        name="예측값 (Forecast)",
                        connect_nulls=True
                    ),

                    # Actual Values Line (파란색 실선) - SWAPPED TO SECOND
                    rx.recharts.line(
                        data_key="actual_value",
                        stroke="#3b82f6",
                        stroke_width=3,
                        dot={"r": 4, "fill": "#3b82f6"},
                        name="실측값 (Actual)",
                        connect_nulls=True  # ✅ 실측값 누락 구간 연결
                    ),

                    # X Axis
                    rx.recharts.x_axis(
                        data_key="time_label",
                        angle=-45,
                        text_anchor="end",
                        height=100,
                        interval=FPS.chart_x_axis_interval,
                        tick={"fontSize": 10}
                    ),

                    # Y Axis - ✅ 데이터 기반 동적 범위 (실측값 + 예측값, ±5% 마진)
                    rx.recharts.y_axis(
                        domain=FPS.y_axis_domain
                    ),

                    # Grid
                    rx.recharts.cartesian_grid(
                        stroke_dasharray="3 3",
                        stroke="#e2e8f0",
                        opacity=0.5
                    ),

                    # Tooltip
                    rx.recharts.tooltip(
                        content_style={
                            "backgroundColor": "rgba(255, 255, 255, 0.95)",
                            "border": "1px solid #e2e8f0",
                            "borderRadius": "8px",
                            "padding": "10px"
                        }
                    ),

                    # Legend
                    rx.recharts.legend(
                        icon_type="line",
                        vertical_align="bottom"
                    ),

                data=FPS.chart_data,
                width="100%",
                height=600
            ),
            spacing="3",
            width="100%"
        ),
        width="100%"
    )


# =========================================================================
# STYLED DATA TABLE (설계처럼 색상 구분)
# =========================================================================

def styled_data_table() -> rx.Component:
    """Horizontal data table (metrics as rows, time as columns) - ALL DATA WITH SCROLL"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("table", size=20, color=rx.color("purple", 9)),
                rx.heading("상세 데이터 테이블 (전체 시계열)", size="4"),
                rx.spacer(),
                rx.badge(
                    f"{FPS.chart_data.length()} 시점",
                    color_scheme="purple",
                    variant="soft"
                ),
                spacing="2",
                align="center",
                width="100%"
            ),
            rx.callout.root(
                rx.callout.icon(rx.icon("info")),
                rx.callout.text(
                    "차트의 모든 데이터를 표시합니다. 가로 스크롤하여 전체 시계열 데이터를 확인하세요."
                ),
                color_scheme="purple",
                size="1"
            ),
            rx.divider(),
            # Fixed height container with scroll
            rx.box(
                rx.table.root(
                    # Table Header - Time labels as columns
                    rx.table.header(
                        rx.table.row(
                            # First column - Metric name
                            rx.table.column_header_cell(
                                "메트릭",
                                style={
                                    "background": rx.color("gray", 3),
                                    "fontWeight": "bold",
                                    "position": "sticky",
                                    "left": "0",
                                    "zIndex": "10",
                                    "minWidth": "120px"
                                }
                            ),
                            # Time columns
                            rx.foreach(
                                FPS.table_time_columns,
                                lambda col: rx.table.column_header_cell(
                                    col["label"],
                                    style=rx.cond(
                                        col["is_present"],
                                        {
                                            "background": rx.color("yellow", 3),
                                            "fontWeight": "bold",
                                            "borderLeft": "2px solid",
                                            "borderRight": "2px solid",
                                            "borderColor": rx.color("red", 9)
                                        },
                                        rx.cond(
                                            col["is_future"],
                                            {"background": rx.color("green", 2)},
                                            {"background": rx.color("blue", 2)}
                                        )
                                    )
                                )
                            )
                        )
                    ),
                    # Table Body - Each metric as a row
                    rx.table.body(
                        # Row 1: Actual Time
                        rx.table.row(
                            rx.table.cell("실제 시간", style={"fontWeight": "bold", "background": rx.color("gray", 2)}),
                            rx.foreach(
                                FPS.time_row_data,
                                lambda val: rx.table.cell(val)
                            )
                        ),
                        # Row 2: Actual Values (계획값 row removed)
                        rx.table.row(
                            rx.table.cell("실측값", style={"fontWeight": "bold", "background": rx.color("blue", 2)}),
                            rx.foreach(
                                FPS.actual_row_data,
                                lambda val: rx.table.cell(
                                    rx.cond(
                                        val != "-",
                                        rx.text(val, color=rx.color("blue", 11), weight="bold"),
                                        rx.text("-", color=rx.color("gray", 8))
                                    )
                                )
                            )
                        ),
                        # Row 3: Predicted Values
                        rx.table.row(
                            rx.table.cell("예측값", style={"fontWeight": "bold", "background": rx.color("orange", 2)}),
                            rx.foreach(
                                FPS.predicted_row_data,
                                lambda val: rx.table.cell(
                                    rx.cond(
                                        val != "-",
                                        rx.text(val, color=rx.color("orange", 11), weight="bold"),
                                        rx.text("-", color=rx.color("gray", 8))
                                    )
                                )
                            )
                        ),
                        # Row 4: Absolute Error
                        rx.table.row(
                            rx.table.cell("절대오차", style={"fontWeight": "bold", "background": rx.color("gray", 2)}),
                            rx.foreach(
                                FPS.error_row_data,
                                lambda val: rx.table.cell(val)
                            )
                        ),
                        # Row 5: Relative Error %
                        rx.table.row(
                            rx.table.cell("상대오차 (%)", style={"fontWeight": "bold", "background": rx.color("gray", 2)}),
                            rx.foreach(
                                FPS.error_pct_row_data,
                                lambda val: rx.table.cell(
                                    rx.cond(
                                        val != "-",
                                        rx.badge(val, color_scheme="yellow", variant="soft"),
                                        rx.text("-", color=rx.color("gray", 8))
                                    )
                                )
                            )
                        ),
                        # Row 6: MAPE (Mean Absolute Percentage Error)
                        rx.table.row(
                            rx.table.cell("MAPE", style={"fontWeight": "bold", "background": rx.color("purple", 2)}),
                            rx.table.cell(
                                rx.cond(
                                    FPS.mape_metric,
                                    rx.badge(f"{FPS.mape_metric:.2f}%", color_scheme="purple", variant="solid", size="2"),
                                    rx.text("-", color=rx.color("gray", 8))
                                ),
                                colspan="66"  # Span all time columns
                            )
                        ),
                        # Row 7: Status
                        rx.table.row(
                            rx.table.cell("상태", style={"fontWeight": "bold", "background": rx.color("gray", 2)}),
                            rx.foreach(
                                FPS.status_row_data,
                                lambda val: rx.table.cell(
                                    rx.cond(
                                        val == "양호",
                                        rx.badge(val, color_scheme="green", variant="solid"),
                                        rx.cond(
                                            val == "주의",
                                            rx.badge(val, color_scheme="yellow", variant="solid"),
                                            rx.cond(
                                                val == "예측",
                                                rx.badge(val, color_scheme="blue", variant="solid"),
                                                rx.text("-", color=rx.color("gray", 8))
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    ),
                    width="max-content",  # Table takes its natural width
                    variant="surface",
                    size="2"
                ),
                # Container with fixed size and scroll
                width="100%",
                height="400px",  # Fixed height
                style={
                    "overflowX": "scroll",  # Force horizontal scroll
                    "overflowY": "auto",    # Vertical scroll if needed
                    "border": "1px solid var(--gray-6)",
                    "borderRadius": "8px"
                }
            ),
            spacing="3",
            width="100%"
        ),
        width="100%",
        style={"overflow": "hidden"}
    )


# =========================================================================
# MODEL SELECTOR AND CONTROLS
# =========================================================================

def model_controls() -> rx.Component:
    """Model selection and control buttons"""
    return rx.card(
        rx.vstack(
            # Model Selector
            rx.vstack(
                rx.text("모델 선택", size="2", weight="medium"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="배포된 모델을 선택하세요",
                        style={"width": "100%", "minWidth": "300px"}
                    ),
                    rx.select.content(
                        rx.foreach(
                            FPS.deployed_models,
                            lambda m: rx.select.item(
                                f"[{m['model_id']}] {m['model_name']} ({m['tag_name']})",
                                value=m['model_id'].to(str)
                            )
                        )
                    ),
                    value=rx.cond(FPS.selected_model_id, FPS.selected_model_id.to(str), ""),
                    on_change=FPS.select_model,
                    size="3",
                    width="100%"
                ),
                spacing="2",
                width="100%"
            ),

            # Control Button
            rx.button(
                rx.icon("database", size=16),
                " 데이터 새로고침",
                on_click=FPS.load_predictions,
                variant="soft",
                size="3",
                width="100%",
                disabled=~FPS.selected_model_id  # Disable if no model selected
            ),

            spacing="3",
            width="100%"
        ),
        width="100%"
    )


# =========================================================================
# MAIN PAGE LAYOUT
# =========================================================================

@rx.page(
    route="/forecast-player-fixed",
    title="예측 플레이어 | KSYS",
    on_load=[
        FPS.load_deployed_models,
        FPS.start_countdown_monitor  # Start real-time countdown
    ]
)
def forecast_player_fixed() -> rx.Component:
    """Fixed forecast player page with proper styling - CONTAINER CONSTRAINED"""
    return shell(
        rx.container(
            rx.vstack(
                # Page Header - AI Model Style
                page_header(
                    title="실시간 예측 대시보드",
                    icon="activity",
                    subtitle=f"Rolling Window 기반 {FPS.forecast_interval_display} 간격 연속 예측 시스템"
                ),

                # Top Metrics (3 Cards)
                metrics_header(),

                # Model Controls
                model_controls(),

                # Main Content
                rx.cond(
                    FPS.has_predictions,
                    rx.vstack(
                        # System Info Row (2 panels side by side) - RESPONSIVE
                        rx.grid(
                            system_status_panel(),
                            recent_updates_panel(),
                            columns=responsive_grid_columns(mobile=1, tablet=2, desktop=2),
                            spacing="4",
                            width="100%"
                        ),

                        # Main Chart (full width)
                        enhanced_forecast_chart(),

                        # Data Table (horizontal layout)
                        styled_data_table(),

                        spacing="4",
                        width="100%"
                    ),

                    # Empty State
                    rx.center(
                        rx.vstack(
                            rx.icon("database", size=64, color=rx.color("gray", 8)),
                            rx.heading("예측 데이터가 없습니다", size="5"),
                            rx.text("모델을 선택하고 스트리밍을 시작하세요", size="3", color=rx.color("gray", 10)),
                            rx.button(
                                "스트리밍 시작",
                                on_click=FPS.start_streaming,
                                size="4",
                                color_scheme="blue"
                            ),
                            spacing="4",
                            align="center"
                        ),
                        padding="8",
                        min_height="400px"
                    )
                ),

                spacing="4",
                width="100%"
            ),
            size="4",
            padding_x="6",
            padding_y="4"
        ),
        active_route="/forecast-player-fixed"
    )