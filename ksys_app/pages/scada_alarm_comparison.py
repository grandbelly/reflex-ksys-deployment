"""
AI Alarms - Rule-based vs AI-based Alarm Comparison
====================================================

룰 베이스 알람과 AI 기반 알람을 비교 분석하는 페이지

작성일: 2025-10-03
디자인: Light Mode (KSYS 통일 디자인)
"""

import reflex as rx
from ksys_app.states.scada_alarm_comparison_state import ScadaAlarmComparisonState
from ksys_app.components.layout import shell
from datetime import datetime


def alarm_severity_badge(severity: int) -> rx.Component:
    """
    알람 레벨 배지 - Light Mode
    KSYS Design: 흰색 배경, 레벨별 색상 구분
    """
    color_map = {
        1: "gray",
        2: "blue",
        3: "yellow",
        4: "orange",
        5: "red"
    }
    label_map = {
        1: "CAUTION",
        2: "INFO",
        3: "WARNING",
        4: "ERROR",
        5: "CRITICAL"
    }
    return rx.badge(
        label_map.get(severity, "UNKNOWN"),
        color_scheme=color_map.get(severity, "gray"),
        variant="soft",
        size="2"
    )


def method_badge(method: str) -> rx.Component:
    """
    알람 방식 배지 - Light Mode
    """
    if method == "RULE_BASE" or "RULE" in str(method):
        return rx.badge(
            "Rule-based",
            color_scheme="blue",
            variant="surface",
            size="2"
        )
    elif method == "AI_BASE" or "AI" in str(method):
        return rx.badge(
            "AI-based",
            color_scheme="purple",
            variant="surface",
            size="2"
        )
    else:
        return rx.badge(
            str(method),
            color_scheme="gray",
            variant="surface",
            size="2"
        )


def stat_card_comparison(title: str, value: rx.Var, subtitle: str = "", color: str = "blue") -> rx.Component:
    """
    통계 카드 - Light Mode
    KSYS Design: 흰색 카드, 컬러 액센트
    """
    return rx.card(
        rx.vstack(
            rx.text(
                title,
                size="2",
                weight="bold",
                color="#111827"  # gray-900
            ),
            rx.text(
                value,
                size="6",
                weight="bold",
                color=rx.color(color, 9)
            ),
            rx.text(
                subtitle,
                size="1",
                color="#6b7280"  # gray-500
            ),
            spacing="1",
            align="center"
        ),
        bg="white",
        border=f"1px solid {rx.color(color, 4)}",
        class_name="hover:shadow-lg transition-all duration-200"
    )


def comparison_page_content() -> rx.Component:
    """알람 비교 메인 컨텐츠 - Light Mode"""
    return rx.vstack(
        # 페이지 헤더
        rx.flex(
            rx.vstack(
                rx.heading(
                    "AI Alarms Comparison",
                    size="7",
                    weight="bold",
                    color="#111827"
                ),
                rx.text(
                    "Rule-based vs AI-based alarm comparison and analysis",
                    size="3",
                    color="#6b7280"
                ),
                spacing="1",
                align="start"
            ),
            rx.spacer(),
            rx.hstack(
                rx.text(
                    f"Total: {ScadaAlarmComparisonState.total_pairs} pairs",
                    size="2",
                    color="#6b7280"
                ),
                rx.button(
                    rx.icon("refresh-cw", size=16),
                    "Refresh",
                    on_click=ScadaAlarmComparisonState.load_comparison_data,
                    size="2",
                    variant="outline",
                    color_scheme="blue"
                ),
                rx.button(
                    rx.icon("activity", size=16),
                    "Generate Test",
                    on_click=ScadaAlarmComparisonState.generate_test_data,
                    size="2",
                    color_scheme="green"
                ),
                spacing="2"
            ),
            width="100%",
            justify="between",
            align="center",
            padding_bottom="1.5rem"
        ),

        # 통계 카드 섹션
        rx.grid(
            stat_card_comparison(
                title="Rule-based Alarms",
                value=ScadaAlarmComparisonState.rule_count,
                subtitle="Avg response: <10ms",
                color="blue"
            ),
            stat_card_comparison(
                title="AI-based Alarms",
                value=ScadaAlarmComparisonState.ai_count,
                subtitle=f"Avg response: {ScadaAlarmComparisonState.avg_ai_response}s",
                color="purple"
            ),
            stat_card_comparison(
                title="Match Rate",
                value=f"{ScadaAlarmComparisonState.match_rate}%",
                subtitle="Level agreement",
                color="green"
            ),
            columns="3",
            spacing="4",
            width="100%"
        ),

        # 비교 테이블
        rx.card(
            rx.vstack(
                rx.heading("Comparison Details", size="4", color="#111827"),

                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Time", width="140px"),
                                rx.table.column_header_cell("Sensor", width="120px"),
                                rx.table.column_header_cell("Value", width="100px"),
                                rx.table.column_header_cell("Level", width="100px"),
                                rx.table.column_header_cell("Rule Message", min_width="300px"),
                                rx.table.column_header_cell("AI Message", min_width="300px"),
                                rx.table.column_header_cell("Response", width="100px"),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                ScadaAlarmComparisonState.comparison_data,
                                lambda item: rx.table.row(
                                    # 시간
                                    rx.table.cell(
                                        rx.text(
                                            item["timestamp"],
                                            size="2",
                                            font_family="monospace",
                                            color="#374151"
                                        )
                                    ),
                                    # 센서
                                    rx.table.cell(
                                        rx.vstack(
                                            rx.badge(item["tag_name"], variant="outline", color_scheme="blue"),
                                            rx.text(item["sensor_type"], size="1", color="#9ca3af"),
                                            spacing="1",
                                            align="start"
                                        )
                                    ),
                                    # 값
                                    rx.table.cell(
                                        rx.text(
                                            f"{item['value']}{item['unit']}",
                                            weight="bold",
                                            color="#111827"
                                        )
                                    ),
                                    # 레벨
                                    rx.table.cell(
                                        alarm_severity_badge(item["level"])
                                    ),
                                    # Rule 메시지
                                    rx.table.cell(
                                        rx.vstack(
                                            rx.text(item["rule_message"], size="2", color="#111827"),
                                            rx.text(
                                                f"Cause: {item['rule_cause']}",
                                                size="1",
                                                color="#f59e0b"  # orange-500
                                            ),
                                            rx.text(
                                                f"Action: {item['rule_action']}",
                                                size="1",
                                                color="#3b82f6"  # blue-500
                                            ),
                                            spacing="1",
                                            align="start"
                                        )
                                    ),
                                    # AI 메시지
                                    rx.table.cell(
                                        rx.vstack(
                                            rx.text(item["ai_message"], size="2", color="#111827"),
                                            rx.text(
                                                f"Cause: {item['ai_cause']}",
                                                size="1",
                                                color="#f59e0b"
                                            ),
                                            rx.text(
                                                f"Action: {item['ai_action']}",
                                                size="1",
                                                color="#3b82f6"
                                            ),
                                            spacing="1",
                                            align="start"
                                        )
                                    ),
                                    # 응답 시간
                                    rx.table.cell(
                                        rx.cond(
                                            item["ai_response_time"] != "",
                                            rx.text(
                                                f"{item['ai_response_time']}s",
                                                size="2",
                                                color="#8b5cf6",  # purple-500
                                                weight="medium"
                                            ),
                                            rx.text("N/A", size="2", color="#9ca3af")
                                        )
                                    ),
                                    bg=rx.cond(
                                        item["is_new"],
                                        "#fef3c7",  # yellow-100 for new items
                                        "white"
                                    ),
                                    class_name="hover:bg-gray-50 transition-colors duration-150"
                                )
                            )
                        ),
                        variant="surface",
                        size="2",
                        width="100%"
                    ),
                    max_height="500px",
                    overflow_y="auto",
                    border="1px solid #e5e7eb",
                    border_radius="8px"
                ),

                spacing="3",
                width="100%"
            ),
            bg="white"
        ),

        # 분석 섹션
        rx.grid(
            rx.card(
                rx.vstack(
                    rx.heading("Message Quality Analysis", size="4", color="#111827"),
                    rx.hstack(
                        rx.text("Average Length:", size="2", color="#6b7280"),
                        rx.text(
                            f"Rule: {ScadaAlarmComparisonState.avg_rule_length} chars",
                            size="2",
                            color="#3b82f6",
                            weight="medium"
                        ),
                        rx.text(
                            f"AI: {ScadaAlarmComparisonState.avg_ai_length} chars",
                            size="2",
                            color="#8b5cf6",
                            weight="medium"
                        ),
                        spacing="3"
                    ),
                    spacing="2",
                    align="start"
                ),
                bg="white"
            ),
            rx.card(
                rx.vstack(
                    rx.heading("Performance Comparison", size="4", color="#111827"),
                    rx.vstack(
                        rx.text(
                            f"AI Avg Response: {ScadaAlarmComparisonState.avg_ai_response}s",
                            size="2",
                            color="#8b5cf6",
                            weight="medium"
                        ),
                        rx.text(
                            "Rule-based: <10ms (fixed)",
                            size="2",
                            color="#3b82f6",
                            weight="medium"
                        ),
                        spacing="1",
                        align="start"
                    ),
                    spacing="2",
                    align="start"
                ),
                bg="white"
            ),
            columns="2",
            spacing="4",
            width="100%"
        ),

        spacing="5",
        width="100%",
        padding="2rem"
    )


@rx.page(route="/scada-alarm-comparison", title="AI Alarms | KSYS")
def scada_alarm_comparison() -> rx.Component:
    """AI 알람 비교 페이지 - Light Mode with Shell"""
    return shell(
        comparison_page_content(),
        active_route="/scada-alarm-comparison",
        on_mount=ScadaAlarmComparisonState.initialize
    )
