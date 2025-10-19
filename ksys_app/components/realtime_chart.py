import reflex as rx
from typing import List, Dict, Any

def realtime_trend_chart(chart_data: rx.Var | List[Dict[str, Any]], tag_name: str = "") -> rx.Component:
    """실시간 10초 간격 트렌드 찰 - 최근 1분간 6개 데이터 포인트"""
    
    def create_realtime_chart():
        return rx.recharts.line_chart(
            rx.recharts.line(
                data_key="value",
                stroke="#10b981",
                stroke_width=2,
                dot={"fill": "#10b981", "r": 3},
                animation_duration=300  # 부드러운 애니메이션
            ),
            rx.recharts.x_axis(
                data_key="bucket",
                tick_line=False,
                axis_line=False,
                tick={"fontSize": 7, "fill": "#6b7280", "angle": -45, "textAnchor": "end"},
                interval=0,  # 모든 시간 표시 (45도 회전)
                height=40   # 회전된 텍스트를 위한 여백 추가
            ),
            rx.recharts.y_axis(
                tick_line=False,
                axis_line=False,
                tick={"fontSize": 8, "fill": "#6b7280"},
                width=35
            ),
            rx.recharts.responsive_container(
                width="100%",
                height="100%"
            ),
            data=chart_data,
            width="100%",
            height=120,
            margin={"top": 10, "right": 10, "left": 0, "bottom": 35}  # 회전된 X축 라벨을 위한 여백 증가
        )
    
    return rx.cond(
        chart_data,
        create_realtime_chart(),
        rx.el.div(
            rx.text("실시간 데이터 로딩 중...", class_name="text-xs text-gray-400"),
            class_name="w-full h-[120px] flex items-center justify-center border border-dashed border-gray-200 rounded"
        )
    )


