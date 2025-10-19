"""AI 응답용 시각화 컴포넌트들"""

import reflex as rx
from typing import List, Dict, Any
import math


def sensor_status_heatmap(sensor_data: List[Dict[str, Any]]) -> rx.Component:
    """센서 상태 히트맵 시각화 - Plotly 사용"""
    if not sensor_data:
        return rx.el.div("데이터 없음", class_name="text-gray-400")
    
    # Plotly 히트맵 데이터 준비
    sensor_names = [sensor.get('sensor', sensor.get('tag_name', 'Unknown')) for sensor in sensor_data]
    sensor_values = [float(sensor.get('value', 0)) for sensor in sensor_data]
    
    # 2D 그리드로 변환 (3x3 또는 적절한 크기)
    grid_size = math.ceil(math.sqrt(len(sensor_data)))
    
    # 2D 배열 생성
    z_values = []
    labels = []
    for i in range(grid_size):
        row_values = []
        row_labels = []
        for j in range(grid_size):
            idx = i * grid_size + j
            if idx < len(sensor_data):
                row_values.append(sensor_values[idx])
                row_labels.append(sensor_names[idx])
            else:
                row_values.append(0)
                row_labels.append("")
        z_values.append(row_values)
        labels.append(row_labels)
    
    # Plotly 히트맵 생성
    heatmap_fig = {
        "data": [
            {
                "type": "heatmap",
                "z": z_values,
                "text": labels,
                "texttemplate": "%{text}",
                "textfont": {"size": 10, "color": "white"},
                "colorscale": [
                    [0, "green"],    # 낮은 값 - 정상
                    [0.5, "yellow"], # 중간 값 - 경고  
                    [1, "red"]       # 높은 값 - 위험
                ],
                "showscale": True,
                "hovertemplate": "<b>%{text}</b><br>값: %{z}<extra></extra>"
            }
        ],
        "layout": {
            "title": "센서 상태 히트맵",
            "width": 400,
            "height": 300,
            "xaxis": {"showticklabels": False},
            "yaxis": {"showticklabels": False},
            "margin": {"l": 40, "r": 40, "t": 60, "b": 40}
        }
    }
    
    return rx.plotly(
        data=heatmap_fig,
        class_name="w-full"
    )


def sensor_comparison_bar(sensor_data: List[Dict[str, Any]]) -> rx.Component:
    """센서 값 비교 바 차트"""
    if not sensor_data:
        return rx.el.div("데이터 없음", class_name="text-gray-400")
    
    # Plotly 바 차트 데이터
    sensor_names = [sensor.get('sensor', sensor.get('tag_name', 'Unknown')) for sensor in sensor_data]
    sensor_values = [float(sensor.get('value', 0)) for sensor in sensor_data]
    
    bar_fig = {
        "data": [
            {
                "type": "bar",
                "x": sensor_names,
                "y": sensor_values,
                "marker": {"color": "#3b82f6"},
                "hovertemplate": "<b>%{x}</b><br>값: %{y}<extra></extra>"
            }
        ],
        "layout": {
            "title": "센서 값 비교",
            "width": 500,
            "height": 300,
            "xaxis": {"title": "센서"},
            "yaxis": {"title": "값"},
            "margin": {"l": 60, "r": 40, "t": 60, "b": 60}
        }
    }
    
    return rx.plotly(
        data=bar_fig,
        class_name="w-full"
    )


def qc_violations_chart(violations_data: List[Dict[str, Any]]) -> rx.Component:
    """QC 위반 차트"""
    if not violations_data:
        return rx.el.div("위반 없음", class_name="text-green-600")
    
    sensor_names = [v.get('sensor', 'Unknown') for v in violations_data]
    values = [float(v.get('value', 0)) for v in violations_data]
    max_vals = [float(v.get('max_val', 0)) for v in violations_data]
    
    violations_fig = {
        "data": [
            {
                "type": "bar",
                "name": "현재값",
                "x": sensor_names,
                "y": values,
                "marker": {"color": "red"}
            },
            {
                "type": "bar",
                "name": "임계값",
                "x": sensor_names,
                "y": max_vals,
                "marker": {"color": "orange"}
            }
        ],
        "layout": {
            "title": "QC 위반 현황",
            "barmode": "group",
            "width": 500,
            "height": 300,
            "xaxis": {"title": "센서"},
            "yaxis": {"title": "값"},
            "margin": {"l": 60, "r": 40, "t": 60, "b": 60}
        }
    }
    
    return rx.plotly(
        data=violations_fig,
        class_name="w-full"
    )


def data_count_pie_chart(count_data: List[Dict[str, Any]]) -> rx.Component:
    """데이터 개수 파이 차트"""
    if not count_data:
        return rx.el.div("데이터 없음", class_name="text-gray-400")
    
    labels = [item.get('sensor', 'Unknown') for item in count_data]
    values = [int(item.get('count', 0)) for item in count_data]
    
    pie_fig = {
        "data": [
            {
                "type": "pie",
                "labels": labels,
                "values": values,
                "hovertemplate": "<b>%{label}</b><br>개수: %{value}<extra></extra>"
            }
        ],
        "layout": {
            "title": "데이터 개수 분포",
            "width": 400,
            "height": 300,
            "margin": {"l": 40, "r": 40, "t": 60, "b": 40}
        }
    }
    
    return rx.plotly(
        data=pie_fig,
        class_name="w-full"
    )


def sensor_trend_chart(trend_data: List[Dict[str, Any]], title: str = "센서 트렌드") -> rx.Component:
    """센서 트렌드 차트"""
    if not trend_data:
        return rx.el.div("차트 데이터 없음", class_name="text-gray-400")
    
    times = [item.get('time', f'T{i}') for i, item in enumerate(trend_data)]
    values = [float(item.get('value', 0)) for item in trend_data]
    
    trend_fig = {
        "data": [
            {
                "type": "scatter",
                "mode": "lines+markers",
                "x": times,
                "y": values,
                "line": {"color": "#3b82f6", "width": 2},
                "marker": {"size": 6, "color": "#3b82f6"},
                "hovertemplate": "<b>%{x}</b><br>값: %{y}<extra></extra>"
            }
        ],
        "layout": {
            "title": title,
            "width": 500,
            "height": 300,
            "xaxis": {"title": "시간"},
            "yaxis": {"title": "값"},
            "margin": {"l": 60, "r": 40, "t": 60, "b": 60}
        }
    }
    
    return rx.plotly(
        data=trend_fig,
        class_name="w-full"
    )