"""
실시간 알람 페이지 (태그별 현재 상태)
작성일: 2025-09-26
"""

import reflex as rx
from datetime import datetime, timezone, timedelta
from ..states.alarm_rt_state import AlarmRTState
from ..components.layout import shell

# KST 시간대
KST = timezone(timedelta(hours=9))

def format_kst_time(dt):
    """UTC를 KST로 변환하여 표시"""
    if dt:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        return dt.replace(tzinfo=timezone.utc).astimezone(KST).strftime("%m-%d %H:%M:%S")
    return "-"

def status_badge(status: str) -> rx.Component:
    """상태별 뱃지 컴포넌트"""
    color_map = {
        "NORMAL": "green",
        "WARNING": "yellow",
        "CRITICAL": "red",
        "INFO": "blue"
    }
    return rx.badge(
        status,
        variant="solid",
        color_scheme=color_map.get(status, "gray"),
    )

def acknowledge_button(tag_name: str, acknowledged: bool) -> rx.Component:
    """인지 버튼"""
    if acknowledged:
        return rx.badge("인지됨", color_scheme="green", variant="outline")
    else:
        return rx.button(
            "인지",
            size="1",
            on_click=AlarmRTState.acknowledge_alarm(tag_name),
            color_scheme="blue",
        )

def alarm_rt_table_old() -> rx.Component:
    """실시간 알람 테이블"""
    return rx.box(
        rx.table(
            rx.thead(
                rx.tr(
                    rx.th("태그"),
                    rx.th("상태"),
                    rx.th("현재값"),
                    rx.th("임계값"),
                    rx.th("마지막 알람"),
                    rx.th("인지"),
                    rx.th("시나리오"),
                )
            ),
            rx.tbody(
                rx.foreach(
                    AlarmRTState.realtime_alarms,
                    lambda alarm: rx.tr(
                        rx.td(
                            rx.text(alarm["tag_name"], font_weight="bold")
                        ),
                        rx.td(status_badge(alarm["status"])),
                        rx.td(
                            rx.text(
                                f"{alarm['current_value']:.1f}",
                                color=rx.cond(
                                    alarm["status"] == "CRITICAL",
                                    "red.600",
                                    rx.cond(
                                        alarm["status"] == "WARNING",
                                        "yellow.600",
                                        "gray.600"
                                    )
                                )
                            )
                        ),
                        rx.td(
                            rx.text(
                                f"{alarm['threshold_low']:.0f} ~ {alarm['threshold_high']:.0f}",
                                font_size="1",
                                color="gray.500"
                            )
                        ),
                        rx.td(
                            rx.text(
                                format_kst_time(alarm["last_alarm_time"]),
                                font_size="1"
                            )
                        ),
                        rx.td(
                            acknowledge_button(
                                alarm["tag_name"],
                                alarm["acknowledged"]
                            )
                        ),
                        rx.td(
                            rx.badge(
                                alarm["scenario"],
                                variant="subtle",
                                color_scheme=rx.cond(
                                    alarm["scenario"] == "AI_BASE",
                                    "purple",
                                    rx.cond(
                                        alarm["scenario"] == "DYNAMIC_RULE",
                                        "blue",
                                        "gray"
                                    )
                                )
                            )
                        ),
                    )
                )
            ),
        ),
        width="100%",
        overflow_x="auto",
    )

def alarm_stats_cards() -> rx.Component:
    """알람 통계 카드"""
    return rx.hstack(
        rx.box(
            rx.vstack(
                rx.text("CRITICAL", font_size="sm", color="gray.600"),
                rx.text(AlarmRTState.critical_count, font_size="2xl", font_weight="bold"),
                rx.text("긴급 대응 필요", font_size="xs", color="gray.500"),
                spacing="1",
            ),
            padding="4",
            bg="red.50",
            border="1px solid",
            border_color="red.300",
            border_radius="lg",
            width="100%",
        ),
        rx.box(
            rx.vstack(
                rx.text("WARNING", font_size="sm", color="gray.600"),
                rx.text(AlarmRTState.warning_count, font_size="2xl", font_weight="bold"),
                rx.text("주의 관찰", font_size="xs", color="gray.500"),
                spacing="1",
            ),
            padding="4",
            bg="yellow.50",
            border="1px solid",
            border_color="yellow.300",
            border_radius="lg",
            width="100%",
        ),
        rx.box(
            rx.vstack(
                rx.text("NORMAL", font_size="sm", color="gray.600"),
                rx.text(AlarmRTState.normal_count, font_size="2xl", font_weight="bold"),
                rx.text("정상 상태", font_size="xs", color="gray.500"),
                spacing="1",
            ),
            padding="4",
            bg="green.50",
            border="1px solid",
            border_color="green.300",
            border_radius="lg",
            width="100%",
        ),
        rx.box(
            rx.vstack(
                rx.text("미인지", font_size="sm", color="gray.600"),
                rx.text(AlarmRTState.unacknowledged_count, font_size="2xl", font_weight="bold"),
                rx.text("확인 필요", font_size="xs", color="gray.500"),
                spacing="1",
            ),
            padding="4",
            bg="blue.50",
            border="1px solid",
            border_color="blue.300",
            border_radius="lg",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )

def alarms_rt_page() -> rx.Component:
    """실시간 알람 메인 페이지"""
    return shell(
        rx.vstack(
        # 헤더
        rx.hstack(
            rx.heading(
                "🔴 실시간 알람 상태",
                size="5",
            ),
            rx.spacer(),
            rx.hstack(
                rx.text(
                    f"마지막 갱신: {AlarmRTState.last_update}",
                    font_size="1",
                    color="gray.500",
                ),
                rx.button(
                    "새로고침",
                    on_click=AlarmRTState.refresh_realtime,
                    size="1",
                    color_scheme="blue",
                ),
                rx.switch(
                    is_checked=AlarmRTState.auto_refresh,
                    on_change=AlarmRTState.toggle_auto_refresh,
                ),
                rx.text("자동 갱신 (5초)", font_size="1"),
            ),
            width="100%",
            padding="4",
            bg="white",
            border_radius="lg",
            shadow="sm",
        ),

        # 통계 카드
        alarm_stats_cards(),

        # 필터
        rx.hstack(
            rx.select(
                ["전체", "CRITICAL", "WARNING", "NORMAL", "미인지"],
                default_value="전체",
                on_change=AlarmRTState.set_filter,
            ),
            rx.select(
                ["모든 시나리오", "DYNAMIC_RULE", "AI_BASE", "RULE_BASE"],
                default_value="모든 시나리오",
                on_change=AlarmRTState.set_scenario_filter,
            ),
            rx.button(
                "모두 인지",
                on_click=AlarmRTState.acknowledge_all,
                size="1",
                variant="outline",
                color_scheme="green",
            ),
            width="100%",
            padding="4",
        ),

        # 테이블
        rx.box(
            alarm_rt_table(),
            width="100%",
            padding="4",
            bg="white",
            border_radius="lg",
            shadow="sm",
        ),

        # 범례
        rx.hstack(
            rx.text("시나리오:", font_weight="bold", font_size="1"),
            rx.badge("DYNAMIC_RULE", color_scheme="blue", variant="subtle"),
            rx.text("동적 QC 규칙", font_size="1"),
            rx.badge("AI_BASE", color_scheme="purple", variant="subtle"),
            rx.text("AI 분석", font_size="1"),
            rx.badge("RULE_BASE", color_scheme="gray", variant="subtle"),
            rx.text("고정 규칙", font_size="1"),
            padding="2",
            bg="gray.50",
            border_radius="md",
        ),

        spacing="4",
        padding="4",
        width="100%",
        )
    )