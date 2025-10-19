"""SCADA 알람 실시간 로깅 뷰어 - 테이블 형식"""

import reflex as rx
from ksys_app.states.scada_alarm_state import ScadaAlarmState
from datetime import datetime


def alarm_severity_badge(severity: int) -> rx.Component:
    """심각도에 따른 배지 표시"""
    color_map = {
        1: "blue",
        2: "green",
        3: "yellow",
        4: "orange",
        5: "red"
    }
    label_map = {
        1: "정보",
        2: "주의",
        3: "경고",
        4: "위험",
        5: "긴급"
    }
    return rx.badge(
        label_map.get(severity, "알 수 없음"),
        color_scheme=color_map.get(severity, "gray"),
        variant="solid",
        size="2"
    )


def alarm_log_table() -> rx.Component:
    """실시간 알람 로그 테이블"""
    return rx.box(
        rx.vstack(
            # 헤더
            rx.hstack(
                rx.heading("SCADA 알람 실시간 로그", size="5"),
                rx.spacer(),
                rx.hstack(
                    rx.text(f"총 {ScadaAlarmState.total_alarms}건", size="2"),
                    rx.button(
                        rx.icon(tag="refresh_cw", size=16),
                        "새로고침",
                        on_click=ScadaAlarmState.load_alarm_logs,
                        size="2",
                        variant="outline"
                    ),
                    rx.button(
                        rx.icon(tag="play", size=16),
                        rx.cond(
                            ScadaAlarmState.is_streaming,
                            "정지",
                            "실시간 시작"
                        ),
                        on_click=ScadaAlarmState.toggle_streaming,
                        size="2",
                        color_scheme=rx.cond(
                            ScadaAlarmState.is_streaming,
                            "red",
                            "green"
                        )
                    ),
                    spacing="2"
                ),
                width="100%",
                justify="between",
                align="center",
                padding_bottom="1em"
            ),

            # 필터 옵션
            rx.hstack(
                rx.select(
                    ["전체", "긴급", "위험", "경고", "주의", "정보"],
                    placeholder="심각도 필터",
                    value=ScadaAlarmState.severity_filter,
                    on_change=ScadaAlarmState.set_severity_filter,
                    size="2",
                    width="150px"
                ),
                rx.input(
                    placeholder="태그명 검색...",
                    value=ScadaAlarmState.tag_filter,
                    on_change=ScadaAlarmState.set_tag_filter,
                    size="2",
                    width="200px"
                ),
                rx.text(
                    f"마지막 업데이트: {ScadaAlarmState.last_update}",
                    size="1",
                    color="gray"
                ),
                spacing="3",
                width="100%",
                padding_bottom="1em"
            ),

            # 알람 로그 테이블
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("시간", width="180px"),
                            rx.table.column_header_cell("태그", width="100px"),
                            rx.table.column_header_cell("값", width="100px"),
                            rx.table.column_header_cell("심각도", width="80px"),
                            rx.table.column_header_cell("AI 설명", min_width="300px"),
                            rx.table.column_header_cell("원인", min_width="200px"),
                            rx.table.column_header_cell("권장조치", min_width="200px"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            ScadaAlarmState.filtered_alarms,
                            lambda alarm: rx.table.row(
                                rx.table.cell(
                                    rx.text(alarm["timestamp"], size="2", font_family="monospace")
                                ),
                                rx.table.cell(
                                    rx.badge(alarm["tag_name"], variant="outline")
                                ),
                                rx.table.cell(
                                    rx.text(alarm["value"], font_weight="bold")
                                ),
                                rx.table.cell(
                                    alarm_severity_badge(alarm["severity"])
                                ),
                                rx.table.cell(
                                    rx.text(alarm["ai_description"], size="2")
                                ),
                                rx.table.cell(
                                    rx.text(alarm["ai_cause"], size="2", color="orange")
                                ),
                                rx.table.cell(
                                    rx.text(alarm["ai_action"], size="2", color="blue")
                                ),
                                background_color=rx.cond(
                                    alarm["is_new"],
                                    "rgba(255, 255, 0, 0.1)",
                                    "transparent"
                                ),
                                _hover={"background_color": "rgba(255, 255, 255, 0.05)"}
                            )
                        )
                    ),
                    variant="surface",
                    size="2",
                    width="100%"
                ),
                height="600px",
                overflow_y="auto",
                border="1px solid rgba(255, 255, 255, 0.1)",
                border_radius="8px"
            ),

            # 통계 정보
            rx.hstack(
                rx.card(
                    rx.vstack(
                        rx.text("긴급", size="2", weight="bold"),
                        rx.text(ScadaAlarmState.critical_count.to_string(), size="4"),
                        spacing="1"
                    ),
                    width="100%"
                ),
                rx.card(
                    rx.vstack(
                        rx.text("위험", size="2", weight="bold"),
                        rx.text(ScadaAlarmState.high_count.to_string(), size="4"),
                        spacing="1"
                    ),
                    width="100%"
                ),
                rx.card(
                    rx.vstack(
                        rx.text("경고", size="2", weight="bold"),
                        rx.text(ScadaAlarmState.warning_count.to_string(), size="4"),
                        spacing="1"
                    ),
                    width="100%"
                ),
                rx.card(
                    rx.vstack(
                        rx.text("주의", size="2", weight="bold"),
                        rx.text(ScadaAlarmState.low_count.to_string(), size="4"),
                        spacing="1"
                    ),
                    width="100%"
                ),
                rx.card(
                    rx.vstack(
                        rx.text("정보", size="2", weight="bold"),
                        rx.text(ScadaAlarmState.info_count.to_string(), size="4"),
                        spacing="1"
                    ),
                    width="100%"
                ),
                padding_top="1em",
                width="100%",
                spacing="3"
            ),

            spacing="4",
            width="100%"
        ),
        padding="1em",
        width="100%"
    )


def scada_alarm_viewer() -> rx.Component:
    """SCADA 알람 뷰어 페이지"""
    return rx.vstack(
        alarm_log_table(),
        spacing="4",
        width="100%",
        on_mount=ScadaAlarmState.initialize
    )