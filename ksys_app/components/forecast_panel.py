"""
Dashboard용 예측 패널 컴포넌트
"""

import reflex as rx
from typing import Any, Dict, List


def forecast_panel(state_class: Any) -> rx.Component:
    """
    실시간 예측을 표시하는 패널

    Args:
        state_class: DashboardRealtimeState 클래스

    Returns:
        예측 패널 컴포넌트
    """
    return rx.cond(
        state_class.forecast_data,
        rx.vstack(
            # 헤더
            rx.hstack(
                rx.icon("trending-up", size=20, color="blue"),
                rx.heading("실시간 예측", size="4"),
                rx.spacer(),
                rx.text(
                    f"{state_class.forecast_data.to(dict).length()} 센서 예측 중",
                    size="2",
                    color="gray"
                ),
                width="100%",
                align="center",
            ),

            rx.divider(),

            # 예측 카드 그리드
            rx.grid(
                rx.foreach(
                    state_class.forecast_data,
                    lambda item: forecast_card(
                        item[0],  # tag_name (key)
                        item[1],  # forecast data (value)
                        state_class
                    )
                ),
                columns="2",
                gap="4",
                width="100%",
            ),

            spacing="4",
            width="100%",
            padding="4",
            bg=rx.color("gray", 2),
            border_radius="lg",
        ),
        rx.fragment(),  # 예측 데이터가 없을 때는 아무것도 표시하지 않음
    )


def forecast_card(tag_name: str, forecast: Dict, state_class: Any) -> rx.Component:
    """
    개별 센서의 예측 카드

    Args:
        tag_name: 센서 태그명
        forecast: 예측 데이터
        state_class: DashboardRealtimeState 클래스

    Returns:
        예측 카드 컴포넌트
    """
    return rx.card(
        rx.vstack(
            # 센서 정보
            rx.hstack(
                rx.text(tag_name, size="3", weight="bold"),
                rx.spacer(),
                rx.badge(
                    forecast["model_type"],
                    color_scheme="blue",
                    variant="soft",
                ),
                width="100%",
                align="center",
            ),

            # 간단한 예측 표시
            rx.box(
                rx.text("24시간 예측", size="1", color="gray"),
                rx.hstack(
                    # 현재값
                    rx.vstack(
                        rx.text("현재", size="1", color="gray"),
                        rx.text(
                            get_current_value(tag_name, state_class),
                            size="3",
                            weight="medium",
                        ),
                        align="center",
                        spacing="1",
                    ),

                    rx.icon("arrow-right", size=16, color="gray"),

                    # 1시간 후 예측
                    rx.vstack(
                        rx.text("1시간 후", size="1", color="blue"),
                        rx.text(
                            get_forecast_value(forecast, 0),
                            size="3",
                            weight="medium",
                            color="blue",
                        ),
                        align="center",
                        spacing="1",
                    ),

                    rx.icon("arrow-right", size=16, color="gray"),

                    # 6시간 후 예측
                    rx.vstack(
                        rx.text("6시간 후", size="1", color="purple"),
                        rx.text(
                            get_forecast_value(forecast, 5),
                            size="3",
                            weight="medium",
                            color="purple",
                        ),
                        align="center",
                        spacing="1",
                    ),

                    rx.icon("arrow-right", size=16, color="gray"),

                    # 24시간 후 예측
                    rx.vstack(
                        rx.text("24시간 후", size="1", color="orange"),
                        rx.text(
                            get_forecast_value(forecast, 23),
                            size="3",
                            weight="medium",
                            color="orange",
                        ),
                        align="center",
                        spacing="1",
                    ),

                    spacing="3",
                    align="center",
                ),
                padding="3",
                bg=rx.color("gray", 2),
                border_radius="md",
                width="100%",
            ),

            # 미니 차트 (선택적 구현)
            rx.cond(
                forecast["predictions"],
                mini_forecast_chart(forecast),
                rx.fragment(),
            ),

            spacing="3",
            width="100%",
        ),
        size="2",
    )


def get_current_value(tag_name: str, state_class: Any) -> str:
    """현재 센서 값 가져오기"""
    # 간단히 N/A 반환 (실제 값은 센서 데이터에서 조회)
    return "N/A"


def get_forecast_value(forecast: Dict, index: int) -> str:
    """예측 값 가져오기 (안전하게)"""
    # 간단히 N/A 반환
    return "N/A"


def mini_forecast_chart(forecast: Dict) -> rx.Component:
    """
    미니 예측 차트 (Recharts 사용)

    Args:
        forecast: 예측 데이터

    Returns:
        차트 컴포넌트
    """
    # 현재는 placeholder 차트만 반환
    return rx.box(
        rx.text("예측 차트", size="1", color="gray"),
        padding="2",
        bg=rx.color("gray", 2),
        border_radius="md",
        width="100%",
        height="100px",
    )


def forecast_summary_card(state_class: Any) -> rx.Component:
    """
    예측 요약 카드 (대시보드 상단용)

    Args:
        state_class: DashboardRealtimeState 클래스

    Returns:
        요약 카드 컴포넌트
    """
    return rx.cond(
        state_class.forecast_data,
        rx.card(
            rx.hstack(
                rx.icon("trending-up", size=24, color="blue"),

                rx.vstack(
                    rx.text("예측 모델 실행 중", size="1", color="gray"),
                    rx.text(
                        f"{state_class.forecast_data.to(dict).length()} 센서",
                        size="3",
                        weight="bold",
                    ),
                    spacing="1",
                ),

                rx.spacer(),

                rx.vstack(
                    rx.text("평균 예측 정확도", size="1", color="gray"),
                    rx.text(
                        "95.2%",  # 실제 구현에서는 계산된 값 사용
                        size="3",
                        weight="bold",
                        color="green",
                    ),
                    spacing="1",
                ),

                rx.spacer(),

                rx.button(
                    "예측 상세보기",
                    on_click=lambda: rx.redirect("/forecast"),
                    size="2",
                    variant="soft",
                ),

                width="100%",
                align="center",
                spacing="4",
                padding="2",
            ),
            size="2",
        ),
        rx.fragment(),
    )