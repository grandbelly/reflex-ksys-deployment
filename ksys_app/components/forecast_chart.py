"""Forecast Chart Component - Visualize predictions with confidence intervals."""

import reflex as rx
from typing import Any


def _create_gradient(color: str, id: str):
    """Create SVG gradient for area chart."""
    return rx.el.defs(
        rx.el.linear_gradient(
            rx.el.stop(offset="0%", stop_color=color, stop_opacity=0.3),
            rx.el.stop(offset="95%", stop_color=color, stop_opacity=0.05),
            id=id,
            x1="0", y1="0", x2="0", y2="1"
        )
    )


def forecast_chart(state_class: Any) -> rx.Component:
    """
    Create forecast visualization chart.

    Shows historical data as solid line/area and predictions with confidence intervals.

    Args:
        state_class: ForecastState class reference

    Returns:
        Recharts component
    """
    return rx.cond(
        state_class.has_predictions,
        rx.recharts.composed_chart(
            # Note: Gradients removed - ComposedChart doesn't allow Defs as children
            # Using solid fills instead

            # X-axis (timestamp)
            rx.recharts.x_axis(
                data_key="timestamp",
                tick_formatter=rx.Var.create(
                    """(value) => {
                        const date = new Date(value);
                        return date.toLocaleTimeString('ko-KR', {
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: false
                        });
                    }"""
                ),
                angle=-45,
                text_anchor="end",
                height=80,
            ),

            # Y-axis
            rx.recharts.y_axis(
                domain=rx.Var.create("[dataMin - 10, dataMax + 10]"),
            ),

            # Tooltip
            rx.recharts.graphing_tooltip(
                content_style={
                    "backgroundColor": "var(--gray-1)",
                    "border": "1px solid var(--gray-6)",
                    "borderRadius": "8px",
                },
                label_formatter=rx.Var.create(
                    """(value) => {
                        const date = new Date(value);
                        return date.toLocaleString('ko-KR', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: false
                        });
                    }"""
                ),
                formatter=rx.Var.create(
                    """(value) => value ? value.toFixed(2) : 'N/A'"""
                ),
            ),

            # Legend
            rx.recharts.legend(),

            # Grid
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
                opacity=0.3,
            ),

            # Reference line at boundary between historical and predicted
            rx.recharts.reference_line(
                x=rx.cond(
                    state_class.historical_data.length() > 0,
                    state_class.historical_data[-1]["timestamp"],
                    ""
                ),
                stroke="var(--gray-8)",
                stroke_dasharray="5 5",
                label="현재",
            ),

            # Confidence interval area (if enabled)
            rx.cond(
                state_class.show_confidence,
                rx.recharts.area(
                    data_key="upper_bound",
                    stroke="none",
                    fill="#f59e0b",
                    fill_opacity=0.2,
                    name="신뢰구간 상한",
                ),
                rx.fragment(),
            ),

            rx.cond(
                state_class.show_confidence,
                rx.recharts.area(
                    data_key="lower_bound",
                    stroke="none",
                    fill="#f59e0b",
                    fill_opacity=0.2,
                    name="신뢰구간 하한",
                ),
                rx.fragment(),
            ),

            # Historical data
            rx.cond(
                state_class.chart_mode == "area",
                rx.recharts.area(
                    data_key="historical",
                    stroke="#3b82f6",
                    fill="#3b82f6",
                    fill_opacity=0.3,
                    name="실측값",
                    stroke_width=2,
                ),
                rx.recharts.line(
                    data_key="historical",
                    stroke="#3b82f6",
                    name="실측값",
                    stroke_width=2,
                    dot=False,
                ),
            ),

            # Predicted data
            rx.cond(
                state_class.chart_mode == "area",
                rx.recharts.area(
                    data_key="predicted",
                    stroke="#10b981",
                    fill="#10b981",
                    fill_opacity=0.3,
                    name="예측값",
                    stroke_width=2,
                    stroke_dasharray="5 5",
                ),
                rx.recharts.line(
                    data_key="predicted",
                    stroke="#10b981",
                    name="예측값",
                    stroke_width=2,
                    stroke_dasharray="5 5",
                    dot=False,
                ),
            ),

            data=state_class.chart_data,
            width="100%",
            height=500,
        ),
        rx.center(
            rx.vstack(
                rx.icon("line-chart", size=48, color="gray"),
                rx.text(
                    "예측 데이터가 없습니다.",
                    size="4",
                    color="gray",
                    weight="medium",
                ),
                rx.text(
                    "센서를 선택하고 예측을 생성하세요.",
                    size="2",
                    color="gray",
                ),
                spacing="3",
                align="center",
            ),
            height="500px",
        ),
    )


def comparison_table(state_class: Any) -> rx.Component:
    """
    Create table comparing last historical values with first predictions.

    Args:
        state_class: ForecastState class reference

    Returns:
        Table component
    """
    return rx.cond(
        state_class.has_predictions,
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("시간"),
                        rx.table.column_header_cell("실측값"),
                        rx.table.column_header_cell("예측값"),
                        rx.table.column_header_cell("차이"),
                        rx.table.column_header_cell("신뢰구간"),
                    ),
                ),
                rx.table.body(
                    # Show last 5 historical points
                    rx.foreach(
                        state_class.historical_data[-5:],
                        lambda item: rx.table.row(
                            rx.table.cell(
                                rx.text(
                                    rx.Var.create(
                                        f"new Date('{item['timestamp']}').toLocaleTimeString('ko-KR', {{hour: '2-digit', minute: '2-digit', hour12: false}})",
                                        
                                    ),
                                    size="2",
                                )
                            ),
                            rx.table.cell(
                                rx.badge(
                                    f"{item['value']:.2f}",
                                    color_scheme="blue",
                                    variant="soft",
                                )
                            ),
                            rx.table.cell(
                                rx.text("-", size="2", color="gray")
                            ),
                            rx.table.cell(
                                rx.text("-", size="2", color="gray")
                            ),
                            rx.table.cell(
                                rx.text("-", size="2", color="gray")
                            ),
                        ),
                    ),

                    # Separator row
                    rx.table.row(
                        rx.table.cell(
                            rx.text(
                                "예측 시작",
                                size="2",
                                weight="bold",
                                color="green",
                            ),
                            col_span=5,
                        ),
                        style={"backgroundColor": "var(--green-3)"},
                    ),

                    # Show first 10 predictions
                    rx.foreach(
                        state_class.predictions[:10],
                        lambda item: rx.table.row(
                            rx.table.cell(
                                rx.text(
                                    rx.Var.create(
                                        f"new Date('{item['timestamp']}').toLocaleTimeString('ko-KR', {{hour: '2-digit', minute: '2-digit', hour12: false}})",
                                        
                                    ),
                                    size="2",
                                )
                            ),
                            rx.table.cell(
                                rx.text("-", size="2", color="gray")
                            ),
                            rx.table.cell(
                                rx.badge(
                                    f"{item['value']:.2f}",
                                    color_scheme="green",
                                    variant="soft",
                                )
                            ),
                            rx.table.cell(
                                rx.text("-", size="2", color="gray")
                            ),
                            rx.table.cell(
                                rx.cond(
                                    item['lower_bound'],
                                    rx.text(
                                        f"[{item['lower_bound']:.2f}, {item['upper_bound']:.2f}]",
                                        size="2",
                                        color="amber",
                                    ),
                                    rx.text("-", size="2", color="gray"),
                                )
                            ),
                        ),
                    ),
                ),
                variant="surface",
                size="2",
            ),
            overflow_x="auto",
            width="100%",
        ),
        rx.center(
            rx.text("데이터가 없습니다.", size="2", color="gray"),
            padding="4",
        ),
    )


def model_info_card(state_class: Any) -> rx.Component:
    """
    Display model information and metrics.

    Args:
        state_class: ForecastState class reference

    Returns:
        Card component
    """
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("brain", size=20, color="purple"),
                rx.heading("모델 정보", size="4"),
                spacing="2",
                align="center",
            ),

            rx.divider(),

            # Model details
            rx.grid(
                rx.box(
                    rx.text("모델 타입", size="2", color="gray", weight="medium"),
                    rx.text(
                        rx.cond(
                            state_class.model_info["model_type"],
                            state_class.model_info["model_type"],
                            "N/A"
                        ),
                        size="3",
                        weight="bold",
                    ),
                ),
                rx.box(
                    rx.text("버전", size="2", color="gray", weight="medium"),
                    rx.text(
                        rx.cond(
                            state_class.model_info["version"],
                            state_class.model_info["version"],
                            "N/A"
                        ),
                        size="3",
                        weight="bold",
                    ),
                ),
                rx.box(
                    rx.text("학습 시간", size="2", color="gray", weight="medium"),
                    rx.text(
                        rx.cond(
                            state_class.model_info["trained_at"],
                            state_class.model_info["trained_at"],
                            "N/A"
                        ),
                        size="3",
                    ),
                ),
                columns="3",
                spacing="4",
                width="100%",
            ),

            rx.divider(),

            # Metrics
            rx.cond(
                state_class.formatted_metrics.length() > 0,
                rx.vstack(
                    rx.text("성능 지표", size="2", color="gray", weight="medium"),
                    rx.grid(
                        rx.foreach(
                            state_class.formatted_metrics.items(),
                            lambda item: rx.box(
                                rx.vstack(
                                    rx.text(
                                        item[0].upper(),
                                        size="1",
                                        color="gray",
                                    ),
                                    rx.text(
                                        item[1],
                                        size="2",
                                        weight="bold",
                                    ),
                                    spacing="1",
                                ),
                            ),
                        ),
                        columns="4",
                        spacing="3",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.fragment(),
            ),

            spacing="4",
            width="100%",
        ),
        size="2",
    )
