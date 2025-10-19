"""
알람 이력 페이지 - 간단한 버전
작성일: 2025-09-26
수정일: 2025-10-07 (통일된 헤더 적용)
"""

import reflex as rx
from datetime import datetime, timezone, timedelta
from ..states.alarm_hist_state import AlarmHistState
from ..components.layout import shell
from ..components.page_header import page_header

# KST 시간대
KST = timezone(timedelta(hours=9))

def format_kst_time_str(dt_str: str) -> str:
    """UTC 문자열을 KST로 변환하여 표시"""
    if dt_str:
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt.replace(tzinfo=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M:%S")
        except:
            return dt_str
    return "-"

def alarms_hist_page() -> rx.Component:
    """알람 이력 메인 페이지"""
    return shell(
        rx.vstack(
            # 헤더 - 통일된 디자인
            page_header(
                title="알람 이력 분석",
                icon="history",
                actions=rx.hstack(
                    rx.input(
                        type="datetime-local",
                        value=AlarmHistState.start_date,
                        on_change=AlarmHistState.set_start_date,
                        width="200px",
                    ),
                    rx.text("~", color="gray"),
                    rx.input(
                        type="datetime-local",
                        value=AlarmHistState.end_date,
                        on_change=AlarmHistState.set_end_date,
                        width="200px",
                    ),
                    rx.button(
                        rx.icon("search", size=16),
                        " 조회",
                        on_click=AlarmHistState.fetch_history,
                        color_scheme="blue",
                        variant="soft",
                        size="2",
                    ),
                    spacing="2",
                    align="center"
                )
            ),

            # 통계 카드
            rx.hstack(
                rx.box(
                    rx.vstack(
                        rx.text("총 알람", font_size="sm"),
                        rx.text(AlarmHistState.total_alarms, font_size="xl", font_weight="bold"),
                        rx.text(AlarmHistState.date_range, font_size="xs", color="gray.500"),
                        spacing="1",
                    ),
                    padding="4",
                    bg="gray.50",
                    border_radius="lg",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.text("최다 센서", font_size="sm"),
                        rx.text(AlarmHistState.top_sensor, font_size="xl", font_weight="bold"),
                        rx.text(f"{AlarmHistState.top_sensor_count}건", font_size="xs", color="gray.500"),
                        spacing="1",
                    ),
                    padding="4",
                    bg="blue.50",
                    border_radius="lg",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.text("평균 레벨", font_size="sm"),
                        rx.text(f"{AlarmHistState.avg_level:.2f}", font_size="xl", font_weight="bold"),
                        rx.text("5점 만점", font_size="xs", color="gray.500"),
                        spacing="1",
                    ),
                    padding="4",
                    bg="yellow.50",
                    border_radius="lg",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.text("해결율", font_size="sm"),
                        rx.text(f"{AlarmHistState.resolution_rate:.2f}%", font_size="xl", font_weight="bold"),
                        rx.text(f"{AlarmHistState.resolved_count}/{AlarmHistState.total_alarms}", font_size="xs", color="gray.500"),
                        spacing="1",
                    ),
                    padding="4",
                    bg="green.50",
                    border_radius="lg",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),

            # 알람 이력 리스트 - 인지 상태 우선 표시
            rx.vstack(
                rx.foreach(
                    AlarmHistState.alarm_history,
                    lambda alarm: rx.box(
                        rx.hstack(
                            # 인지 상태 - 제일 앞에 크게 표시
                            rx.vstack(
                                rx.text("상태", font_size="xs", color="gray.500"),
                                rx.badge(
                                    rx.cond(
                                        alarm["acknowledged"],
                                        "✓ 확인완료",
                                        "● 미확인"
                                    ),
                                    size="2",
                                    variant="solid",
                                    color_scheme=rx.cond(
                                        alarm["acknowledged"],
                                        "green",
                                        "orange"
                                    )
                                ),
                                spacing="1",
                                width="12%",
                            ),
                            rx.vstack(
                                rx.text(
                                    alarm["triggered_at"],
                                    font_size="sm",
                                    color="gray.600"
                                ),
                                rx.text(alarm["tag_name"], font_weight="bold"),
                                spacing="1",
                                width="20%",
                            ),
                            rx.vstack(
                                rx.text("레벨", font_size="xs", color="gray.500"),
                                rx.badge(
                                    rx.cond(
                                        alarm["level"] == 5,
                                        "EMERGENCY",
                                        rx.cond(
                                            alarm["level"] == 4,
                                            "CRITICAL",
                                            rx.cond(
                                                alarm["level"] == 3,
                                                "WARNING",
                                                rx.cond(
                                                    alarm["level"] == 2,
                                                    "CAUTION",
                                                    "INFO"
                                                )
                                            )
                                        )
                                    ),
                                    color_scheme=rx.cond(
                                        alarm["level"] == 5,
                                        "red",
                                        rx.cond(
                                            alarm["level"] == 4,
                                            "red",
                                            rx.cond(
                                                alarm["level"] == 3,
                                                "yellow",
                                                rx.cond(
                                                    alarm["level"] == 2,
                                                    "orange",
                                                    "blue"
                                                )
                                            )
                                        )
                                    )
                                ),
                                spacing="1",
                                width="15%",
                            ),
                            rx.vstack(
                                rx.text("시나리오", font_size="xs", color="gray.500"),
                                rx.badge(
                                    alarm["scenario_id"],
                                    variant="soft",
                                    color_scheme=rx.cond(
                                        alarm["scenario_id"] == "AI_BASE",
                                        "purple",
                                        rx.cond(
                                            alarm["scenario_id"] == "DYNAMIC_RULE",
                                            "blue",
                                            "gray"
                                        )
                                    )
                                ),
                                spacing="1",
                                width="15%",
                            ),
                            rx.vstack(
                                rx.text("값", font_size="xs", color="gray.500"),
                                rx.text(f"{alarm['value']:.2f}", font_weight="bold"),
                                spacing="1",
                                width="10%",
                            ),
                            rx.vstack(
                                rx.text("메시지", font_size="xs", color="gray.500"),
                                rx.text(
                                    alarm["message"],
                                    font_size="sm",
                                    max_width="200px",
                                    overflow="hidden",
                                    text_overflow="ellipsis"
                                ),
                                spacing="1",
                                width="25%",
                            ),
                            rx.vstack(
                                rx.text("해결상태", font_size="xs", color="gray.500"),
                                rx.badge(
                                    rx.cond(
                                        alarm["resolved"],
                                        "해결완료",
                                        "진행중"
                                    ),
                                    size="1",
                                    variant="soft",
                                    color_scheme=rx.cond(
                                        alarm["resolved"],
                                        "green",
                                        "gray"
                                    )
                                ),
                                spacing="1",
                                width="10%",
                            ),
                            width="100%",
                            justify="between",
                        ),
                        padding="4",
                        bg="white",
                        border="1px solid",
                        border_color="gray.200",
                        border_radius="lg",
                        _hover={"border_color": "gray.400"},
                    )
                ),
                spacing="2",
                width="100%",
            ),

            # 페이지네이션
            rx.hstack(
                rx.button(
                    "이전",
                    on_click=AlarmHistState.prev_page,
                    disabled=AlarmHistState.current_page == 1,
                    size="2",
                ),
                rx.text(f"페이지 {AlarmHistState.current_page} / {AlarmHistState.total_pages}"),
                rx.button(
                    "다음",
                    on_click=AlarmHistState.next_page,
                    disabled=AlarmHistState.current_page == AlarmHistState.total_pages,
                    size="2",
                ),
                justify="center",
                width="100%",
            ),

            spacing="4",
            padding="4",
            width="100%",
            on_mount=AlarmHistState.on_load,
        )
    )