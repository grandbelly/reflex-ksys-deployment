import reflex as rx
import reflex_chakra as rc
from typing import List, Dict, Any, Optional
from ..states.base_state import BaseState as B


def unified_kpi_card(
    tag_name: str,
    value_s: rx.Var | str,
    delta_pct: rx.Var | float,
    delta_s: rx.Var | str,
    status_level: rx.Var | int,
    ts_s: rx.Var | str,
    range_label: rx.Var | str,
    chart_data: Optional[List[Dict[str, Any]]] = None,
    gauge_pct: Optional[float] = None,
    comm_status: Optional[bool] = None,
    comm_text: Optional[str] = None,
    realtime_mode: bool = False,
    realtime_data: Optional[List[Dict[str, Any]]] = None,
    qc_min: Optional[float] = None,
    qc_max: Optional[float] = None,
    on_detail_click: Optional[Any] = None,
    unit: Optional[str] = None,
    delta_icon: Optional[str] = None,
    delta_color: Optional[str] = None,
    ts_fresh: Optional[str] = "🔴",
) -> rx.Component:
    """통합 KPI 카드 컴포넌트"""
    
    # 상태별 색상 매핑
    status_color = rx.cond(
        status_level == 2, "red",
        rx.cond(status_level == 1, "amber", "green")
    )
    
    # 백엔드에서 전달된 아이콘과 색상 사용 (기본값 설정)
    # 이미 아래에서 직접 처리하므로 제거
    
    # 실제 값에서 숫자만 추출
    numeric_val = rx.Var.create(f"parseFloat(String({value_s}).replace(/[^0-9.-]/g, '')) || 0")
    
    return rx.card(
        rx.vstack(
            # 헤더 섹션
            rx.hstack(
                rx.hstack(
                    # 상태 인디케이터
                    rx.el.div(
                        class_name=rx.cond(
                            status_level == 2, "w-3 h-3 bg-red-500 rounded-full animate-pulse",
                            rx.cond(
                                status_level == 1, "w-3 h-3 bg-amber-500 rounded-full",
                                "w-3 h-3 bg-green-500 rounded-full"
                            )
                        )
                    ),
                    rx.text(
                        tag_name,
                        class_name="text-sm font-semibold text-gray-800 truncate",
                        title=tag_name
                    ),
                    spacing="2"
                ),
                
                # 우측 배지들
                rx.hstack(
                    # QC 범위 배지
                    rx.badge(
                        rx.hstack(
                            rx.icon("ruler", size=10),
                            rx.text(range_label, class_name="text-xs"),
                            spacing="1"
                        ),
                        color_scheme="gray", 
                        variant="soft", 
                        size="1"
                    ),
                    
                    # 통신 상태
                    rx.cond(
                        comm_status != None,
                        rx.badge(
                            rx.hstack(
                                rx.icon(
                                    rx.cond(comm_status, "activity", "alert-circle"),
                                    size=10
                                ),
                                rx.text(
                                    rx.cond(comm_text != None, comm_text, "연결"),
                                    class_name="text-xs"
                                ),
                                spacing="1"
                            ),
                            color_scheme=rx.cond(comm_status, "green", "red"),
                            variant="solid",
                            size="1"
                        ),
                        rx.fragment()
                    ),
                    
                    
                    spacing="1"
                ),
                
                justify="between",
                width="100%",
                align="center"
            ),
            
            # 게이지 섹션 - Chakra Progress
            rx.center(
                rx.box(
                    rc.circular_progress(
                        rc.circular_progress_label(
                            rx.vstack(
                                rx.text(
                                    value_s,
                                    font_weight="bold",
                                    font_size="lg",
                                    color="gray.800",
                                    transition="all 0.2s ease-in-out"
                                ),
                                rx.text(
                                    rx.cond(unit, unit, ""),
                                    font_size="xs",
                                    color="gray.500"
                                ),
                                spacing="0",
                                align="center"
                            )
                        ),
                        value=gauge_pct,
                        color=rx.cond(
                            status_level == 2, "red.500",
                            rx.cond(status_level == 1, "yellow.500", "green.500")
                        ),
                        size="96px",
                        thickness="8px",
                        track_color="gray.200",
                        transition="all 0.3s ease-in-out"
                    ),
                    position="relative"
                ),
                padding="4"
            ),
            
            # 타임스탬프와 갱신 상태
            rx.hstack(
                rx.text(
                    ts_s,
                    class_name="text-xs text-gray-500"
                ),
                rx.text(
                    ts_fresh,
                    class_name="text-xs"
                ),
                justify="center",
                spacing="1"
            ),
            
            # 트렌드 차트
            rx.cond(
                chart_data,
                rx.box(
                    rx.cond(
                        realtime_mode,
                        # 실시간 라인 차트 (개선된 미니 차트)
                        rx.recharts.line_chart(
                                # 1) 심플한 그리드 (세로선 제거, 가로선만)
                                rx.recharts.cartesian_grid(
                                    stroke="#f0f0f0",
                                    stroke_dasharray="2 2",
                                    vertical=False,
                                    horizontal=True
                                ),
                                # 2) 스무스한 라인
                                rx.recharts.line(
                                    data_key="value",
                                    type="monotone",
                                    stroke=rx.cond(
                                        status_level == 2, "#ef4444",  # 빨강
                                        rx.cond(status_level == 1, "#f59e0b", "#10b981")  # 주황/초록
                                    ),
                                    stroke_width=1.5,
                                    dot=False,  # 점 제거로 깔끔하게
                                    active_dot={"r": 3, "fill": "#fff", "stroke": "#2563eb", "strokeWidth": 1},
                                    connect_nulls=True,
                                    is_animation_active=False,  # 애니메이션 비활성화로 성능 향상
                                ),
                                # 3) X축 - 간소화된 레이블
                                rx.recharts.x_axis(
                                    data_key="bucket",
                                    tick_line=False,
                                    axis_line=False,  # Boolean 타입으로 수정
                                    tick={
                                        "fontSize": 8,
                                        "fill": "#6b7280",
                                        "angle": -90,  # 90도 회전
                                        "textAnchor": "end"
                                    },
                                    interval=0,  # 모든 틱 표시 (0 = 모두 표시)
                                    height=40  # 회전된 텍스트를 위해 높이 증가
                                ),
                                # 4) Y축 - 숨김 but 범위 자동 조정
                                rx.recharts.y_axis(
                                    hide=True,
                                    domain=["dataMin - 5", "dataMax + 5"],  # 여유 공간 추가
                                    allow_data_overflow=False
                                ),
                                # 5) 개선된 툴팁 (흰색 배경)
                                rx.recharts.tooltip(
                                    cursor=False,  # 커서 라인 제거
                                    content_style={
                                        "borderRadius": 6,
                                        "border": "1px solid #e5e7eb",
                                        "backgroundColor": "#ffffff",
                                        "color": "#374151",
                                        "padding": "8px 12px",
                                        "fontSize": "12px",
                                        "boxShadow": "0 4px 12px rgba(0,0,0,0.1)"
                                    },
                                    label_style={
                                        "color": "#6b7280",
                                        "fontSize": "11px",
                                        "marginBottom": "4px"
                                    },
                                    item_style={
                                        "color": "#111827",
                                        "fontSize": "12px",
                                        "fontWeight": "500"
                                    }
                                ),
                                data=rx.cond(realtime_mode, realtime_data, chart_data),
                                margin={"top": 5, "right": 5, "left": 5, "bottom": 35},
                                width="100%",
                                height=90
                        ),
                        # 기본 바 차트  
                        rx.recharts.bar_chart(
                            rx.recharts.bar(
                                data_key="avg",
                                fill="#10b981",
                                fill_opacity=0.8,
                                radius=[2, 2, 0, 0]
                            ),
                            rx.recharts.x_axis(
                                data_key="bucket",
                                tick_line=False,
                                axis_line=False,
                                tick={"fontSize": 7, "fill": "#9ca3af", "angle": -45, "textAnchor": "end"},  # 45도 회전
                                interval="preserveStartEnd",
                                height=25                         # 회전된 텍스트를 위한 여백
                            ),
                            rx.recharts.tooltip(
                                content_style={
                                    "backgroundColor": "white",
                                    "border": "1px solid #e5e7eb",
                                    "borderRadius": "6px",
                                    "color": "#374151",
                                    "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
                                }
                            ),
                            data=chart_data,
                            width="100%",
                            height=60,
                            margin={"top": 5, "right": 5, "left": 5, "bottom": 5}
                        )
                    ),
                    class_name="w-full bg-gray-50 rounded-md p-2"
                ),
                # 차트 데이터 없음
                rx.center(
                    rx.vstack(
                        rx.icon("bar-chart", size=16, color="gray"),
                        rx.text("데이터 없음", class_name="text-xs text-gray-400"),
                        spacing="1"
                    ),
                    height="60px",
                    class_name="border-2 border-dashed border-gray-200 rounded-md"
                )
            ),
            
            # 변화량 표시
            # rx.match를 사용해 아이콘 매칭
            rx.hstack(
                rx.match(
                    delta_icon,
                    ("trending-up", rx.icon("trending-up", size=16, color="green")),
                    ("trending-down", rx.icon("trending-down", size=16, color="red")),
                    rx.icon("minus", size=16, color="gray")  # 기본값
                ),
                rx.text(
                    delta_s,
                    class_name=rx.match(
                        delta_color,
                        ("green", "text-sm font-medium text-green-600"),
                        ("red", "text-sm font-medium text-red-600"),
                        "text-sm font-medium text-gray-500"  # 기본값
                    )
                ),
                spacing="2",
                justify="center"
            ),
            
            
            spacing="3",
            align="center",
            width="100%"
        ),
        
        variant="surface",
        size="2",
        class_name=rx.cond(
            status_level == 2,
            "border-red-500 border-2 shadow-red-500/20 shadow-lg animate-pulse cursor-pointer",
            rx.cond(
                status_level == 1,
                "border-amber-500 border-2 shadow-amber-500/20 cursor-pointer hover:shadow-lg transition-all duration-200",
                "border-gray-200 cursor-pointer hover:shadow-lg hover:bg-gray-50 transition-all duration-200"
            )
        ),
        on_click=on_detail_click
    )




