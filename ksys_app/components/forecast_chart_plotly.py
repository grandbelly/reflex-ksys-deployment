"""
MLForecast-style forecast chart using Plotly with rx.plotly()
Reflex 공식 Plotly 지원을 사용한 진짜 shaded band 신뢰구간 구현
"""

import plotly.graph_objects as go
import reflex as rx
from typing import List, Dict, Any


def create_mlforecast_chart_figure(data: List[Dict[str, Any]]) -> go.Figure:
    """
    MLForecast 스타일의 예측 차트 Figure 생성

    Args:
        data: 차트 데이터 (timestamp, actual, forecast, upper_95, lower_95 등)

    Returns:
        Plotly Figure object (rx.plotly에 직접 전달 가능)
    """

    if not data:
        # Empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color="gray")
        )
        return fig

    # 데이터 추출
    timestamps = []
    actual_vals = []
    forecast_vals = []
    lower_80_vals = []
    upper_80_vals = []
    lower_95_vals = []
    upper_95_vals = []

    for point in data:
        timestamps.append(point.get('timestamp', ''))

        # None 값 처리 (끊어진 선을 위해)
        actual = point.get('actual')
        actual_vals.append(actual if actual is not None else None)

        forecast = point.get('forecast')
        forecast_vals.append(forecast if forecast is not None else None)

        # 신뢰구간
        lower_80_vals.append(point.get('lower_80'))
        upper_80_vals.append(point.get('upper_80'))
        lower_95_vals.append(point.get('lower_95'))
        upper_95_vals.append(point.get('upper_95'))

    # Figure 생성
    fig = go.Figure()

    # 95% 신뢰구간 (가장 넓고 연한 색) - fill='tonexty'로 band 생성!
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=lower_95_vals,
        fill=None,
        mode='lines',
        line_color='rgba(0,0,0,0)',
        showlegend=False,
        hoverinfo='skip'
    ))

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=upper_95_vals,
        fill='tonexty',  # 이전 trace와의 사이를 채움! (바로 이것!)
        mode='lines',
        line_color='rgba(0,0,0,0)',
        fillcolor='rgba(150, 180, 255, 0.2)',  # 연한 파란색
        name='95% CI',
        hovertemplate='95% CI: %{y:.2f}'
    ))

    # 80% 신뢰구간 (더 좁고 진한 색)
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=lower_80_vals,
        fill=None,
        mode='lines',
        line_color='rgba(0,0,0,0)',
        showlegend=False,
        hoverinfo='skip'
    ))

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=upper_80_vals,
        fill='tonexty',
        mode='lines',
        line_color='rgba(0,0,0,0)',
        fillcolor='rgba(150, 180, 255, 0.35)',  # 더 진한 파란색
        name='80% CI',
        hovertemplate='80% CI: %{y:.2f}'
    ))

    # 실제값 (Historical)
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=actual_vals,
        mode='lines',
        line=dict(color='#2E7D32', width=2.5),  # 진한 초록
        name='Actual',
        hovertemplate='Actual: %{y:.2f}<br>%{x}'
    ))

    # 예측값 (Forecast)
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=forecast_vals,
        mode='lines',
        line=dict(color='#1976D2', width=3, dash='dash'),  # 진한 파란색, dashed
        name='Forecast',
        hovertemplate='Forecast: %{y:.2f}<br>%{x}'
    ))

    # 레이아웃 설정
    fig.update_layout(
        title={
            'text': 'Forecast with Confidence Intervals',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'weight': 'bold'}
        },
        xaxis=dict(
            title='Time',
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(200,200,200,0.3)'
        ),
        yaxis=dict(
            title='Value',
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(200,200,200,0.3)'
        ),
        hovermode='x unified',
        height=450,
        template='plotly_white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=80, b=50),
        plot_bgcolor='rgba(250, 250, 250, 0.5)',
        paper_bgcolor='white'
    )

    return fig


def forecast_chart_component() -> rx.Component:
    """
    Reflex 공식 plotly 컴포넌트 사용
    rx.plotly(data=figure) - 이게 올바른 방법!
    """
    from ..states.training_wizard_state import TrainingWizardState

    return rx.box(
        rx.plotly(
            data=TrainingWizardState.forecast_chart_figure
        ),
        width="100%",
        padding="4",
        border_radius="md",
        border="1px solid",
        border_color=rx.color("gray", 4),
        bg="white",
    )
