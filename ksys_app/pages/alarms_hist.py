"""
알람 이력 페이지 (시계열 히스토리)
작성일: 2025-09-26
"""

import reflex as rx
from datetime import datetime, timezone, timedelta
from ..states.alarm_hist_state import AlarmHistState
from ..components.layout import shell

# KST 시간대
KST = timezone(timedelta(hours=9))

def format_kst_time(dt):
    """UTC를 KST로 변환하여 표시"""
    if dt:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        return dt.replace(tzinfo=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M:%S")
    return "-"

def level_badge(level: int) -> rx.Component:
    """알람 레벨 뱃지"""
    level_map = {
        5: ("EMERGENCY", "red"),
        4: ("CRITICAL", "red"),
        3: ("WARNING", "yellow"),
        2: ("CAUTION", "orange"),
        1: ("INFO", "blue")
    }
    label, color = level_map.get(level, ("UNKNOWN", "gray"))
    return rx.badge(label, variant="solid", color_scheme=color)

def scenario_badge(scenario: str) -> rx.Component:
    """시나리오 타입 뱃지"""
    color_map = {
        "AI_BASE": "purple",
        "DYNAMIC_RULE": "blue",
        "RULE_BASE": "gray",
        "D101_AI": "pink",
        "D102_AI": "cyan"
    }
    return rx.badge(
        scenario,
        variant="subtle",
        color_scheme=color_map.get(scenario, "gray"),
        size="1"
    )

def alarm_timeline() -> rx.Component:
    """알람 타임라인 차트"""
    return rx.vstack(
        rx.heading("알람 발생 추이", size="md"),
        rx.recharts.area_chart(
            rx.recharts.area(
                data_key="count",
                stroke="rgb(59, 130, 246)",
                fill="rgb(59, 130, 246, 0.3)",
            ),
            rx.recharts.x_axis(data_key="time"),
            rx.recharts.y_axis(),
            rx.recharts.tooltip(),
            rx.recharts.legend(),
            data=AlarmHistState.timeline_data,
            height=200,
        ),
        width="100%",
        bg="white",
        padding="4",
        border_radius="lg",
        shadow="sm",
    )

def alarm_history_table() -> rx.Component:
    """알람 이력 테이블"""
    return rx.box(
        rx.table(
            rx.thead(
                rx.tr(
                    rx.th("시간"),
                    rx.th("태그"),
                    rx.th("레벨"),
                    rx.th("시나리오"),
                    rx.th("값"),
                    rx.th("메시지"),
                    rx.th("상태"),
                )
            ),
            rx.tbody(
                rx.foreach(
                    AlarmHistState.alarm_history,
                    lambda alarm: rx.tr(
                        rx.td(
                            rx.text(
                                format_kst_time(alarm["triggered_at"]),
                                font_size="1"
                            )
                        ),
                        rx.td(
                            rx.text(alarm["tag_name"], font_weight="bold")
                        ),
                        rx.td(level_badge(alarm["level"])),
                        rx.td(scenario_badge(alarm["scenario_id"])),
                        rx.td(
                            rx.text(f"{alarm['value']:.1f}", font_size="1")
                        ),
                        rx.td(
                            rx.tooltip(
                                rx.text(
                                    alarm["message"][:50] + "..." if len(alarm["message"]) > 50 else alarm["message"],
                                    font_size="1"
                                ),
                                label=alarm["message"]
                            )
                        ),
                        rx.td(
                            rx.hstack(
                                rx.cond(
                                    alarm["acknowledged"],
                                    rx.icon("check", color="green", size=16),
                                    rx.icon("x", color="gray", size=16),
                                ),
                                rx.cond(
                                    alarm["resolved"],
                                    rx.badge("해결", color_scheme="green", size="1"),
                                    rx.badge("활성", color_scheme="red", size="1"),
                                ),
                                spacing="1",
                            )
                        ),
                    )
                )
            ),
        ),
        width="100%",
        overflow_x="auto",
    )

def date_filter_controls() -> rx.Component:
    """날짜 필터 컨트롤"""
    return rx.hstack(
        rx.input(
            type="datetime-local",
            value=AlarmHistState.start_date,
            on_change=AlarmHistState.set_start_date,
            width="200px",
        ),
        rx.text("~"),
        rx.input(
            type="datetime-local",
            value=AlarmHistState.end_date,
            on_change=AlarmHistState.set_end_date,
            width="200px",
        ),
        rx.select(
            ["1시간", "6시간", "24시간", "7일", "30일"],
            default_value="24시간",
            on_change=AlarmHistState.set_quick_range,
            width="120px",
        ),
        rx.button(
            "조회",
            on_click=AlarmHistState.fetch_history,
            color_scheme="blue",
            size="1",
        ),
        rx.button(
            rx.icon("download", size=16),
            "Excel",
            on_click=AlarmHistState.export_excel,
            variant="outline",
            size="1",
        ),
        spacing="2",
        align="center",
    )

def alarm_statistics() -> rx.Component:
    """알람 통계 카드"""
    return rx.hstack(
        rx.box(
            rx.vstack(
                rx.text("총 알람", font_size="sm", color="gray.600"),
                rx.text(AlarmHistState.total_alarms, font_size="2xl", font_weight="bold"),
                rx.text(f"{AlarmHistState.date_range}", font_size="xs", color="gray.500"),
                spacing="1",
            ),
            padding="4",
            bg="gray.50",
            border="1px solid",
            border_color="gray.300",
            border_radius="lg",
            width="100%",
        ),
        rx.box(
            rx.vstack(
                rx.text("센서별 최다", font_size="sm", color="gray.600"),
                rx.text(AlarmHistState.top_sensor, font_size="2xl", font_weight="bold"),
                rx.text(f"{AlarmHistState.top_sensor_count}건", font_size="xs", color="gray.500"),
                spacing="1",
            ),
            padding="4",
            bg="blue.50",
            border="1px solid",
            border_color="blue.300",
            border_radius="lg",
            width="100%",
        ),
        rx.box(
            rx.vstack(
                rx.text("평균 레벨", font_size="sm", color="gray.600"),
                rx.text(f"{AlarmHistState.avg_level:.1f}", font_size="2xl", font_weight="bold"),
                rx.text("5점 만점", font_size="xs", color="gray.500"),
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
                rx.text("해결율", font_size="sm", color="gray.600"),
                rx.text(f"{AlarmHistState.resolution_rate:.0f}%", font_size="2xl", font_weight="bold"),
                rx.text(f"{AlarmHistState.resolved_count}/{AlarmHistState.total_alarms}", font_size="xs", color="gray.500"),
                spacing="1",
            ),
            padding="4",
            bg="green.50",
            border="1px solid",
            border_color="green.300",
            border_radius="lg",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )

def sensor_distribution() -> rx.Component:
    """센서별 알람 분포"""
    return rx.vstack(
        rx.heading("센서별 알람 분포", size="md"),
        rx.recharts.bar_chart(
            rx.recharts.bar(
                data_key="count",
                fill="rgb(59, 130, 246)",
            ),
            rx.recharts.x_axis(data_key="sensor"),
            rx.recharts.y_axis(),
            rx.recharts.tooltip(),
            data=AlarmHistState.sensor_distribution,
            height=200,
        ),
        width="100%",
        bg="white",
        padding="4",
        border_radius="lg",
        shadow="sm",
    )

def alarms_hist_page() -> rx.Component:
    """알람 이력 메인 페이지"""
    return shell(
        rx.vstack(
        # 헤더
        rx.hstack(
            rx.heading(
                "📊 알람 이력 분석",
                size="5",
            ),
            rx.spacer(),
            rx.text(
                f"마지막 조회: {AlarmHistState.last_fetch}",
                font_size="1",
                color="gray.500",
            ),
            width="100%",
            padding="4",
            bg="white",
            border_radius="lg",
            shadow="sm",
        ),

        # 날짜 필터
        rx.box(
            date_filter_controls(),
            width="100%",
            padding="4",
            bg="white",
            border_radius="lg",
            shadow="sm",
        ),

        # 통계 카드
        alarm_statistics(),

        # 차트 섹션
        rx.hstack(
            alarm_timeline(),
            sensor_distribution(),
            spacing="4",
            width="100%",
        ),

        # 필터 옵션
        rx.hstack(
            rx.select(
                ["전체"] + AlarmHistState.sensor_list,
                default_value="전체",
                placeholder="센서 선택",
                on_change=AlarmHistState.set_sensor_filter,
                width="150px",
            ),
            rx.select(
                ["전체", "DYNAMIC_RULE", "AI_BASE", "RULE_BASE"],
                default_value="전체",
                placeholder="시나리오",
                on_change=AlarmHistState.set_scenario_filter,
                width="150px",
            ),
            rx.select(
                ["전체", "EMERGENCY", "CRITICAL", "WARNING", "CAUTION", "INFO"],
                default_value="전체",
                placeholder="레벨",
                on_change=AlarmHistState.set_level_filter,
                width="150px",
            ),
            rx.checkbox(
                "미해결만",
                is_checked=AlarmHistState.unresolved_only,
                on_change=AlarmHistState.toggle_unresolved,
            ),
            rx.button(
                "필터 초기화",
                on_click=AlarmHistState.reset_filters,
                variant="outline",
                size="1",
            ),
            width="100%",
            padding="4",
            bg="gray.50",
            border_radius="md",
        ),

        # 이력 테이블
        rx.box(
            alarm_history_table(),
            width="100%",
            padding="4",
            bg="white",
            border_radius="lg",
            shadow="sm",
        ),

        # 페이지네이션
        rx.hstack(
            rx.button(
                "이전",
                on_click=AlarmHistState.prev_page,
                disabled=AlarmHistState.current_page == 1,
                size="1",
            ),
            rx.text(f"페이지 {AlarmHistState.current_page} / {AlarmHistState.total_pages}"),
            rx.button(
                "다음",
                on_click=AlarmHistState.next_page,
                disabled=AlarmHistState.current_page == AlarmHistState.total_pages,
                size="1",
            ),
            rx.select(
                ["10", "25", "50", "100"],
                default_value=str(AlarmHistState.page_size),
                on_change=AlarmHistState.set_page_size,
                width="80px",
            ),
            rx.text("개씩 보기", font_size="1"),
            justify="center",
            width="100%",
            padding="4",
        ),

        spacing="4",
        padding="4",
        width="100%",
        )
    )