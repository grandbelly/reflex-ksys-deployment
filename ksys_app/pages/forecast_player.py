"""
Forecast Player Page - Step-by-step forecast playback with timeline visualization
Supports two modes: Realtime (live streaming) and Playback (step-by-step navigation)
"""
import reflex as rx
from ..states.forecast_player_state import ForecastPlayerState as FPS
from ..components.layout import shell


# =========================================================================
# VIEW MODE TOGGLE
# =========================================================================

def view_mode_toggle() -> rx.Component:
    """Toggle between Realtime and Playback modes"""
    return rx.hstack(
        rx.button(
            rx.icon("wifi", size=16),
            " 실시간",
            on_click=FPS.switch_to_realtime_mode,
            color_scheme=rx.cond(
                FPS.view_mode == "realtime",
                "blue",
                "gray"
            ),
            variant=rx.cond(
                FPS.view_mode == "realtime",
                "solid",
                "soft"
            ),
            size="2"
        ),
        rx.button(
            rx.icon("video", size=16),
            " 재생",
            on_click=FPS.switch_to_playback_mode,
            color_scheme=rx.cond(
                FPS.view_mode == "playback",
                "purple",
                "gray"
            ),
            variant=rx.cond(
                FPS.view_mode == "playback",
                "solid",
                "soft"
            ),
            size="2"
        ),
        spacing="2"
    )


# =========================================================================
# STEP NAVIGATION CONTROLS (Playback Mode)
# =========================================================================

def step_counter() -> rx.Component:
    """Display current step number"""
    return rx.badge(
        f"Step {FPS.current_step_number} / {FPS.total_steps}",
        color_scheme="purple",
        variant="soft",
        size="2"
    )


def step_navigation_controls() -> rx.Component:
    """Navigation controls for stepping through forecasts"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("rewind", size=20, color=rx.color("purple", 9)),
                rx.heading("예측 스텝 탐색", size="4"),
                spacing="2",
                align="center"
            ),

            # Step counter
            rx.cond(
                FPS.has_steps,
                step_counter(),
                rx.text("스텝을 불러오는 중...", size="2", color="gray")
            ),

            # Navigation buttons
            rx.cond(
                FPS.has_steps,
                rx.hstack(
                    # First step
                    rx.button(
                        rx.icon("chevrons-left", size=16),
                        " 처음",
                        on_click=FPS.go_first_step,
                        disabled=~FPS.can_go_prev,
                        size="2",
                        variant="soft"
                    ),
                    # Previous step
                    rx.button(
                        rx.icon("chevron-left", size=16),
                        " 이전",
                        on_click=FPS.go_prev_step,
                        disabled=~FPS.can_go_prev,
                        size="2",
                        variant="soft"
                    ),
                    # Next step
                    rx.button(
                        " 다음 ",
                        rx.icon("chevron-right", size=16),
                        on_click=FPS.go_next_step,
                        disabled=~FPS.can_go_next,
                        size="2",
                        variant="soft"
                    ),
                    # Last step
                    rx.button(
                        " 마지막 ",
                        rx.icon("chevrons-right", size=16),
                        on_click=FPS.go_last_step,
                        disabled=~FPS.can_go_next,
                        size="2",
                        variant="soft"
                    ),
                    spacing="2",
                    width="100%",
                    justify="center"
                ),
                rx.fragment()
            ),

            # Current step info
            rx.cond(
                FPS.has_steps,
                rx.box(
                    rx.vstack(
                        rx.text("예측 생성 시각:", size="1", color="gray", weight="medium"),
                        rx.text(
                            FPS.current_step_info.get("forecast_time_kst", "-"),
                            size="2",
                            weight="bold"
                        ),
                        spacing="1",
                        align="center"
                    ),
                    padding="3",
                    border_radius="md",
                    bg=rx.color("purple", 2),
                    border=f"1px solid {rx.color('purple', 6)}",
                    width="100%"
                ),
                rx.fragment()
            ),

            spacing="3",
            width="100%"
        ),
        width="100%"
    )


# =========================================================================
# TIMELINE CHART (Playback Mode - Shows Actual + Forecast Overlay)
# =========================================================================

def timeline_chart() -> rx.Component:
    """
    Timeline chart showing actual history + forecast overlay
    Distinguishes between actual values and predicted values
    """
    return rx.box(
        rx.recharts.line_chart(
            # Actual values line (solid blue)
            rx.recharts.line(
                data_key="actual",
                stroke="#3b82f6",
                stroke_width=2,
                dot={"r": 4, "fill": "#3b82f6"},
                name="실측값 (Actual)",
                connect_nulls=False
            ),

            # Forecast values line (dashed red)
            rx.recharts.line(
                data_key="forecast",
                stroke="#ef4444",
                stroke_width=2,
                stroke_dasharray="5 5",
                dot={"r": 4, "fill": "#ef4444"},
                name="예측값 (Forecast)",
                connect_nulls=False
            ),

            # Confidence interval upper
            rx.recharts.line(
                data_key="ci_upper",
                stroke="#fca5a5",
                stroke_width=1,
                stroke_dasharray="3 3",
                dot=False,
                name="95% CI Upper"
            ),

            # Confidence interval lower
            rx.recharts.line(
                data_key="ci_lower",
                stroke="#fca5a5",
                stroke_width=1,
                stroke_dasharray="3 3",
                dot=False,
                name="95% CI Lower"
            ),

            # Axes
            rx.recharts.x_axis(
                data_key="timestamp",
                angle=-45,
                text_anchor="end",
                height=80,
                tick={"fontSize": 10},
                stroke=rx.color("slate", 8)
            ),
            rx.recharts.y_axis(
                stroke=rx.color("slate", 8),
                domain=["dataMin - 5", "dataMax + 5"]
            ),

            # Grid, Tooltip, Legend
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
                stroke=rx.color("slate", 6)
            ),
            rx.recharts.tooltip(
                content_style={
                    "backgroundColor": rx.color("slate", 2),
                    "border": f"1px solid {rx.color('slate', 6)}",
                    "borderRadius": "6px"
                }
            ),
            rx.recharts.legend(),

            # Data and sizing
            data=FPS.timeline_chart_data,
            width="100%",
            height=400
        ),
        width="100%"
    )


# =========================================================================
# STEP DATA TABLE (Playback Mode - Shows Actual + Forecast Side-by-Side)
# =========================================================================

def step_data_table() -> rx.Component:
    """Table showing both actual and forecast values for current step"""
    return rx.card(
        rx.vstack(
            rx.heading("스텝 데이터 (Actual vs Forecast)", size="4"),
            rx.cond(
                FPS.timeline_chart_data,
                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("시각 (KST)"),
                                rx.table.column_header_cell("실측값"),
                                rx.table.column_header_cell("예측값"),
                                rx.table.column_header_cell("오차"),
                                rx.table.column_header_cell("CI Lower"),
                                rx.table.column_header_cell("CI Upper"),
                                rx.table.column_header_cell("Horizon (h)")
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                FPS.timeline_chart_data,
                                lambda row: rx.table.row(
                                    rx.table.cell(row["timestamp"]),
                                    rx.table.cell(
                                        rx.cond(
                                            row.get("actual"),
                                            row["actual"],
                                            "-"
                                        )
                                    ),
                                    rx.table.cell(
                                        rx.cond(
                                            row.get("forecast"),
                                            row["forecast"],
                                            "-"
                                        )
                                    ),
                                    rx.table.cell(
                                        rx.cond(
                                            row.get("actual") & row.get("forecast"),
                                            row.get("error", "-"),
                                            "-"
                                        )
                                    ),
                                    rx.table.cell(
                                        rx.cond(
                                            row.get("ci_lower"),
                                            row["ci_lower"],
                                            "-"
                                        )
                                    ),
                                    rx.table.cell(
                                        rx.cond(
                                            row.get("ci_upper"),
                                            row["ci_upper"],
                                            "-"
                                        )
                                    ),
                                    rx.table.cell(
                                        rx.cond(
                                            row.get("horizon_hours"),
                                            f"{row['horizon_hours']}h",
                                            "-"
                                        )
                                    )
                                )
                            )
                        ),
                        width="100%",
                        variant="surface",
                        size="2"
                    ),
                    class_name="w-full overflow-x-auto"
                ),
                rx.text("스텝 데이터가 없습니다", color="gray", size="2")
            ),
            spacing="3",
            width="100%"
        ),
        width="100%"
    )


# =========================================================================
# REALTIME MODE COMPONENTS (Original Multi-Horizon Chart)
# =========================================================================

def status_banner() -> rx.Component:
    """Status banner showing streaming state, countdown timer, and last update time (HTML 가이드 스타일)"""
    return rx.box(
        rx.hstack(
            # 데이터 스트림 활성 (펄스 애니메이션 점)
            rx.hstack(
                rx.box(
                    width="10px",
                    height="10px",
                    border_radius="50%",
                    bg=rx.cond(FPS.is_streaming, "#4CAF50", "#9ca3af"),
                    style=rx.cond(
                        FPS.is_streaming,
                        {
                            "animation": "pulse 2s infinite",
                            "@keyframes pulse": {
                                "0%, 100%": {"opacity": 1},
                                "50%": {"opacity": 0.5}
                            }
                        },
                        {}
                    )
                ),
                rx.text(
                    rx.cond(FPS.is_streaming, "데이터 스트림 활성", "데이터 스트림 정지"),
                    size="2",
                    weight="medium"
                ),
                spacing="2",
                align="center"
            ),

            # 모델 실행 중
            rx.hstack(
                rx.box(
                    width="10px",
                    height="10px",
                    border_radius="50%",
                    bg=rx.cond(FPS.has_predictions, "#4CAF50", "#FF9800"),
                    style={
                        "animation": "pulse 2s infinite",
                        "@keyframes pulse": {
                            "0%, 100%": {"opacity": 1},
                            "50%": {"opacity": 0.5}
                        }
                    }
                ),
                rx.text("모델 실행 중", size="2", weight="medium"),
                spacing="2",
                align="center"
            ),

            # 마지막 업데이트
            rx.hstack(
                rx.text(
                    "마지막 업데이트: ",
                    rx.text(FPS.last_update, weight="bold", as_="span"),
                    size="2"
                ),
                spacing="1"
            ),

            # 다음 갱신 카운트다운
            rx.hstack(
                rx.text(
                    "다음 갱신: ",
                    size="2"
                ),
                rx.text(
                    FPS.countdown_display,
                    size="2",
                    weight="bold",
                    color=rx.color("blue", 11)
                ),
                spacing="1"
            ),

            spacing="4",
            align="center",
            width="100%",
            justify="between"
        ),
        padding="4",
        border_radius="8px",
        bg=rx.color("slate", 3),
        width="100%"
    )


def realtime_forecast_chart() -> rx.Component:
    """
    Rolling Window Chart - 레퍼런스 스타일

    배경 구역:
    - Past (T-10 ~ T0): 매우 밝은 파란색 투명 배경 (#dbeafe opacity 0.3)
    - Future (T0 ~ T+36): 매우 밝은 주황색 투명 배경 (#fed7aa opacity 0.3)

    데이터:
    - 실측값 (과거): 파란 실선
    - 예측값 (미래): 주황 실선 + 주황 점선 CI 영역
    - T0 구분선: 빨간 점선
    """
    return rx.box(
        rx.recharts.composed_chart(
            # 배경 구역 1: Past zone (매우 밝은 파란색) - 실제 데이터 포인트 사용
            rx.recharts.reference_area(
                x1=FPS.past_zone_start,  # 첫 번째 데이터 포인트
                x2=FPS.t0_label,  # T0 지점 (actual → predicted 전환점)
                fill="#dbeafe",  # Blue-100 (very light blue)
                fill_opacity=0.3,
                stroke="none"
            ),

            # 배경 구역 2: Future zone (매우 밝은 주황색) - 실제 데이터 포인트 사용
            rx.recharts.reference_area(
                x1=FPS.t0_label,  # T0 지점
                x2=FPS.future_zone_end,  # 마지막 데이터 포인트
                fill="#fed7aa",  # Orange-200 (very light orange)
                fill_opacity=0.1,  # Reduced from 0.3 to 0.1 for lighter appearance
                stroke="none"
            ),

            # CI 라인 (주황 점선 - area 제거, line으로 변경)
            rx.recharts.line(
                data_key="ci_upper",
                stroke="#f97316",
                stroke_width=1,
                stroke_dasharray="3 3",
                dot=False,
                name="95% CI Upper",
                connect_nulls=True
            ),
            rx.recharts.line(
                data_key="ci_lower",
                stroke="#f97316",
                stroke_width=1,
                stroke_dasharray="3 3",
                dot=False,
                name="95% CI Lower",
                connect_nulls=True
            ),

            # 실측값 라인 (과거 - 파란색)
            rx.recharts.line(
                data_key="actual_value",
                stroke="#2563eb",
                stroke_width=2,
                dot={"r": 3, "fill": "#2563eb", "strokeWidth": 0},
                name="실측값 (Actual)",
                connect_nulls=False
            ),

            # 예측값 라인 (미래 - 주황색)
            rx.recharts.line(
                data_key="predicted_value",
                stroke="#f97316",
                stroke_width=2,
                dot={"r": 3, "fill": "#f97316", "strokeWidth": 0},
                name="예측값 (Forecast)",
                connect_nulls=False
            ),

            # T0 구분선 (빨간 점선) - 실제 T0 데이터 포인트 사용
            rx.recharts.reference_line(
                x=FPS.t0_label,
                stroke="#ef4444",
                stroke_width=2,
                stroke_dasharray="5 5",
                label="T0"
            ),

            # X축
            rx.recharts.x_axis(
                data_key="time_label",
                angle=-45,
                text_anchor="end",
                height=120,
                interval=4,
                tick={"fontSize": 10, "fill": "#64748b"},
                stroke="#cbd5e1"
            ),

            # Y축
            rx.recharts.y_axis(
                stroke="#cbd5e1",
                tick={"fill": "#64748b"},
                domain=["dataMin - 10", "dataMax + 10"]
            ),

            # 그리드
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
                stroke="#e2e8f0",
                opacity=0.5
            ),

            # 툴팁
            rx.recharts.tooltip(
                content_style={
                    "backgroundColor": "white",
                    "border": "1px solid #cbd5e1",
                    "borderRadius": "6px",
                    "color": "#334155"
                }
            ),

            # 범례
            rx.recharts.legend(),

            data=FPS.chart_data,
            width="100%",
            height=500
        ),
        width="100%",
        padding="4",
        border_radius="8px",
        style={
            "backgroundColor": "#f9fafb",
            "border": "1px solid #e5e7eb"
        }
    )


def gradient_metric_card(label: str, value: rx.Var, gradient: str, icon: str = "bar-chart") -> rx.Component:
    """Gradient metric card (HTML 가이드 스타일)"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=20, color="white"),
                rx.text(label, size="2", color="white", weight="medium", style={"opacity": "0.9"}),
                spacing="2",
                align="center"
            ),
            rx.text(value, size="7", weight="bold", color="white"),
            spacing="2",
            align="start"
        ),
        padding="4",
        border_radius="8px",
        style={
            "background": gradient,
            "color": "white",
            "flex": "1"
        }
    )


def accuracy_metrics_panel() -> rx.Component:
    """Display MAPE, RMSE, Confidence metrics with gradients (HTML 가이드 스타일)"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("bar-chart", size=20, color=rx.color("blue", 9)),
                rx.heading("📊 실시간 메트릭", size="4"),
                spacing="2",
                align="center"
            ),
            rx.cond(
                FPS.has_accuracy_data,
                rx.vstack(
                    # MAPE - 녹색 그라디언트
                    gradient_metric_card(
                        "평균 절대 오차율 (MAPE)",
                        FPS.mape_formatted,
                        "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)",
                        "trending-up"
                    ),
                    # RMSE - 보라색 그라디언트
                    gradient_metric_card(
                        "평균 제곱근 오차 (RMSE)",
                        FPS.accuracy_metrics["rmse"],
                        "linear-gradient(135deg, #4776e6 0%, #8e54e9 100%)",
                        "activity"
                    ),
                    # 예측 신뢰도 - 핑크 그라디언트
                    gradient_metric_card(
                        "예측 신뢰도",
                        "95.2%",  # TODO: 실제 신뢰도 값으로 교체
                        "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
                        "shield-check"
                    ),
                    spacing="3",
                    width="100%"
                ),
                rx.vstack(
                    rx.text("📊 실시간 예측 활성화", size="2", weight="bold", color=rx.color("blue", 11)),
                    rx.text(
                        f"총 {FPS.total_predictions_count}개 예측 생성됨 (실제값 대기 중)",
                        size="1",
                        color="gray"
                    ),
                    spacing="1",
                    align="center"
                )
            ),
            spacing="3",
            width="100%"
        ),
        width="100%"
    )


def system_info_panel() -> rx.Component:
    """시스템 정보 패널 (HTML 가이드 스타일)"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("settings", size=20, color=rx.color("purple", 9)),
                rx.heading("⚙️ 시스템 정보", size="4"),
                spacing="2",
                align="center"
            ),
            rx.vstack(
                rx.text("• 윈도우 크기: 20 시점", size="2", color=rx.color("slate", 11)),
                rx.text("• 예측 범위: 12 시점", size="2", color=rx.color("slate", 11)),
                rx.text("• 갱신 주기: 10분", size="2", color=rx.color("slate", 11)),
                rx.text(f"• 모델: {FPS.selected_model_info.get('model_type', 'N/A')}", size="2", color=rx.color("slate", 11)),
                rx.text("• 신뢰구간: 95%", size="2", color=rx.color("slate", 11)),
                rx.text("• 총 업데이트: 12회", size="2", color=rx.color("slate", 11)),  # TODO: 실제 카운터 추가
                spacing="2",
                align="start"
            ),
            spacing="3",
            width="100%"
        ),
        width="100%"
    )


def realtime_control_buttons() -> rx.Component:
    """Start/Stop streaming buttons for Realtime mode"""
    return rx.hstack(
        rx.cond(
            FPS.is_streaming,
            rx.fragment(),
            rx.button(
                rx.icon("play", size=16),
                " Start Streaming",
                on_click=FPS.start_streaming,
                color_scheme="green",
                size="3"
            )
        ),
        rx.cond(
            FPS.is_streaming,
            rx.button(
                rx.icon("square", size=16),
                " Stop",
                on_click=FPS.stop_streaming,
                color_scheme="red",
                variant="soft",
                size="3"
            ),
            rx.fragment()
        ),
        spacing="2"
    )


def realtime_predictions_table() -> rx.Component:
    """Table showing rolling window data (same as chart) - Realtime Mode"""
    return rx.card(
        rx.vstack(
            rx.heading("Rolling Window Data (Chart와 동일)", size="4"),
            rx.cond(
                FPS.chart_data,
                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("시각 (KST)"),
                                rx.table.column_header_cell("실측값 (Actual)"),
                                rx.table.column_header_cell("예측값 (Predicted)"),
                                rx.table.column_header_cell("CI Lower"),
                                rx.table.column_header_cell("CI Upper")
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                FPS.chart_data,
                                lambda row: rx.table.row(
                                    rx.table.cell(row["time_label"]),
                                    rx.table.cell(
                                        rx.cond(
                                            row.get("actual_value") != None,
                                            f"{row['actual_value']:.2f}",
                                            "-"
                                        )
                                    ),
                                    rx.table.cell(
                                        rx.cond(
                                            row.get("predicted_value") != None,
                                            f"{row['predicted_value']:.2f}",
                                            "-"
                                        )
                                    ),
                                    rx.table.cell(
                                        rx.cond(
                                            row.get("ci_lower") != None,
                                            f"{row['ci_lower']:.2f}",
                                            "-"
                                        )
                                    ),
                                    rx.table.cell(
                                        rx.cond(
                                            row.get("ci_upper") != None,
                                            f"{row['ci_upper']:.2f}",
                                            "-"
                                        )
                                    )
                                )
                            )
                        ),
                        width="100%",
                        variant="surface",
                        size="2"
                    ),
                    class_name="w-full overflow-x-auto"
                ),
                rx.text("No data available", color="gray")
            ),
            spacing="3",
            width="100%"
        ),
        width="100%"
    )


# =========================================================================
# PLAYLIST PANEL
# =========================================================================

def playlist_panel() -> rx.Component:
    """실시간 예측 플레이리스트 - 모든 활성 모델의 카운트다운 표시"""
    return rx.cond(
        FPS.show_playlist,
        rx.card(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.icon("list-music", size=20, color=rx.color("blue", 9)),
                    rx.heading(
                        f"📋 실시간 예측 플레이리스트 ({FPS.playlist_count})",
                        size="4"
                    ),
                    rx.button(
                        rx.icon("x", size=16),
                        on_click=FPS.toggle_playlist,
                        variant="ghost",
                        size="1"
                    ),
                    spacing="2",
                    align="center",
                    justify="between",
                    width="100%"
                ),

                # Playlist items
                rx.cond(
                    FPS.has_playlist,
                    rx.vstack(
                        rx.foreach(
                            FPS.playlist_items,
                            lambda item: rx.box(
                                rx.hstack(
                                    # Play icon if selected
                                    rx.cond(
                                        item["model_id"] == FPS.selected_model_id,
                                        rx.icon("play-circle", size=16, color=rx.color("green", 9)),
                                        rx.box(width="16px", height="16px")  # Spacer
                                    ),

                                    # Tag name and model type
                                    rx.vstack(
                                        rx.text(
                                            item["tag_name"],
                                            size="3",
                                            weight="bold",
                                            color=rx.cond(
                                                item["model_id"] == FPS.selected_model_id,
                                                rx.color("blue", 11),
                                                rx.color("slate", 12)
                                            )
                                        ),
                                        rx.text(
                                            item["model_type"],
                                            size="1",
                                            color=rx.color("slate", 10)
                                        ),
                                        spacing="0",
                                        align="start",
                                        flex="1"
                                    ),

                                    # Countdown (simplified - show seconds only)
                                    rx.vstack(
                                        rx.text(
                                            "다음 예측:",
                                            size="1",
                                            color=rx.color("slate", 10)
                                        ),
                                        rx.text(
                                            item["countdown_seconds"],
                                            "초",
                                            size="2",
                                            weight="bold",
                                            color=rx.color("blue", 11)
                                        ),
                                        spacing="0",
                                        align="end"
                                    ),

                                    spacing="3",
                                    align="center",
                                    width="100%"
                                ),
                                padding="3",
                                border_radius="md",
                                bg=rx.cond(
                                    item["model_id"] == FPS.selected_model_id,
                                    rx.color("blue", 3),
                                    rx.color("slate", 2)
                                ),
                                border=rx.cond(
                                    item["model_id"] == FPS.selected_model_id,
                                    f"2px solid {rx.color('blue', 7)}",
                                    f"1px solid {rx.color('slate', 6)}"
                                ),
                                cursor="pointer",
                                on_click=lambda item_id=item["model_id"]: FPS.select_from_playlist(item_id),
                                _hover={
                                    "background": rx.color("blue", 2),
                                    "border_color": rx.color("blue", 6)
                                }
                            )
                        ),
                        spacing="2",
                        width="100%"
                    ),
                    rx.text("플레이리스트가 비어있습니다", size="2", color="gray")
                ),

                spacing="3",
                width="100%"
            ),
            width="100%",
            max_width="400px"
        ),
        rx.fragment()
    )


# =========================================================================
# MODEL SELECTOR
# =========================================================================

def model_selector() -> rx.Component:
    """Dropdown to select deployed model"""
    return rx.hstack(
        rx.select.root(
            rx.select.trigger(placeholder="Select a deployed model"),
            rx.select.content(
                rx.foreach(
                    FPS.deployed_models,
                    lambda m: rx.select.item(
                        f"{m['model_name']} ({m['tag_name']})",
                        value=m['model_id'].to(str)
                    )
                )
            ),
            value=FPS.selected_model_id.to(str),
            on_change=FPS.select_model,
            size="3",
            flex="1"
        ),
        rx.button(
            rx.icon("list-music", size=16),
            f" Playlist ({FPS.playlist_count})",
            on_click=FPS.toggle_playlist,
            color_scheme=rx.cond(FPS.show_playlist, "blue", "gray"),
            variant=rx.cond(FPS.show_playlist, "solid", "soft"),
            size="3"
        ),
        spacing="2",
        width="100%"
    )


# =========================================================================
# MAIN PAGE
# =========================================================================

@rx.page(
    route="/forecast-player",
    title="Forecast Player | KSYS",
    on_load=FPS.load_deployed_models
)
def forecast_player() -> rx.Component:
    """Main Forecast Player page with Realtime and Playback modes"""
    return shell(
        # Gradient background container (HTML 예제처럼)
        rx.box(
            rx.container(
                rx.vstack(
                    # Header with gradient text
                    rx.center(
                        rx.vstack(
                            rx.hstack(
                                rx.icon("refresh-cw", size=32, color="white"),
                                rx.heading(
                                    "실시간 Rolling Window 예측 대시보드",
                                    size="8",
                                    weight="bold",
                                    style={
                                        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                                        "-webkit-background-clip": "text",
                                        "-webkit-text-fill-color": "transparent",
                                        "background-clip": "text"
                                    }
                                ),
                                spacing="3",
                                align="center"
                            ),
                            rx.text(
                                "10분 간격 연속 갱신 시스템 | Real-time Time Series Forecasting",
                                size="3",
                                color=rx.color("slate", 11),
                                weight="medium"
                            ),
                            spacing="2",
                            align="center"
                        ),
                        padding_y="4",
                        border_bottom=f"2px solid {rx.color('slate', 6)}"
                    ),

                # Main content
                rx.cond(
                    FPS.has_deployed_models,
                    rx.vstack(
                        # Model selection and Playlist button
                        rx.vstack(
                            rx.text("Select Model", size="2", weight="medium", color="#374151"),
                            model_selector(),
                            spacing="2",
                            width="100%"
                        ),

                        # Playlist panel (conditionally shown)
                        playlist_panel(),

                        # View mode toggle
                        view_mode_toggle(),

                        # REALTIME MODE
                        rx.cond(
                            FPS.view_mode == "realtime",
                            rx.vstack(
                                # Status banner
                                status_banner(),

                                # Control buttons
                                realtime_control_buttons(),

                                # Chart and predictions (세로 배치: 사이드 패널 위 → 차트 아래)
                                rx.cond(
                                    FPS.has_predictions,
                                    rx.vstack(
                                        # 위: 사이드 패널을 가로로 배치
                                        rx.hstack(
                                            # 실시간 메트릭
                                            accuracy_metrics_panel(),

                                            # 시스템 정보
                                            system_info_panel(),

                                            spacing="4",
                                            width="100%",
                                            align="start"
                                        ),

                                        # 아래: 차트 (전체 너비로 크게)
                                        rx.card(
                                            rx.vstack(
                                                rx.heading(
                                                    "시계열 트렌드 차트 (Rolling Window)",
                                                    size="4",
                                                    weight="medium"
                                                ),
                                                realtime_forecast_chart(),
                                                spacing="3",
                                                width="100%"
                                            ),
                                            width="100%",
                                            min_height="600px"
                                        ),

                                        # Predictions Table (제일 아래에 전체 너비로 추가)
                                        realtime_predictions_table(),

                                        spacing="4",
                                        width="100%"
                                    ),
                                    rx.center(
                                        rx.vstack(
                                            rx.icon("circle-alert", size=48, color="#9ca3af"),
                                            rx.text("No predictions available", size="4", weight="bold", color="#6b7280"),
                                            rx.text("Click 'Start Streaming' to load predictions", size="2", color="#9ca3af"),
                                            spacing="3",
                                            align="center"
                                        ),
                                        padding="8",
                                        border_radius="lg",
                                        border="2px dashed #e5e7eb",
                                        bg="white",
                                        width="100%"
                                    )
                                ),

                                spacing="4",
                                width="100%"
                            ),
                            # PLAYBACK MODE
                            rx.vstack(
                                # Step navigation controls
                                step_navigation_controls(),

                                # Timeline chart
                                rx.cond(
                                    FPS.timeline_chart_data,
                                    rx.card(
                                        rx.vstack(
                                            rx.badge(
                                                f"타임라인: {FPS.selected_tag_name}",
                                                color_scheme="purple",
                                                variant="soft",
                                                size="2"
                                            ),
                                            timeline_chart(),
                                            spacing="3",
                                            width="100%"
                                        ),
                                        width="100%"
                                    ),
                                    rx.center(
                                        rx.vstack(
                                            rx.icon("database", size=48, color="#9ca3af"),
                                            rx.text("스텝 데이터가 없습니다", size="4", weight="bold", color="#6b7280"),
                                            rx.text("모델을 선택하면 예측 스텝을 불러옵니다", size="2", color="#9ca3af"),
                                            spacing="3",
                                            align="center"
                                        ),
                                        padding="8",
                                        border_radius="lg",
                                        border="2px dashed #e5e7eb",
                                        bg="white",
                                        width="100%"
                                    )
                                ),

                                spacing="4",
                                width="100%"
                            )
                        ),

                        spacing="4",
                        width="100%"
                    ),
                    rx.center(
                        rx.vstack(
                            rx.icon("database", size=48, color="#9ca3af"),
                            rx.text("No deployed models found", size="4", weight="bold", color="#6b7280"),
                            rx.text("Please deploy a model from Model Performance page", size="2", color="#9ca3af"),
                            spacing="3",
                            align="center"
                        ),
                        padding="8",
                        border_radius="lg",
                        border="2px dashed #e5e7eb",
                        bg="white",
                        width="100%"
                    )
                ),

                spacing="4",
                width="100%"
            ),
            size="4",
            padding="4"
        )  # rx.container 닫기
        ),  # rx.box 닫기
        active_route="/forecast-player"
    )  # shell 닫기
