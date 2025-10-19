"""
알람 뷰어 페이지
자연어 설명과 함께 알람 이벤트를 표시
"""
import reflex as rx
from ..components.layout import shell
from ..states.alarm_state import AlarmState


def alarm_level_badge(level: str, count: int) -> rx.Component:
    """알람 레벨별 배지"""
    colors = {
        "CRITICAL": "red",
        "WARNING": "amber",
        "INFO": "blue",
        "EMERGENCY": "purple"
    }

    return rx.badge(
        rx.hstack(
            rx.text(level, size="1", weight="bold"),
            rx.text(count.to_string(), size="2", weight="bold"),
            spacing="1"
        ),
        color_scheme=colors.get(level, "gray"),
        variant="soft",
        radius="full",
        size="2"
    )


def alarm_filter_section() -> rx.Component:
    """필터 섹션 - 벡터 검색 포함"""
    return rx.card(
        rx.vstack(
            # 통계 배지들
            rx.hstack(
                rx.text("알람 현황", size="3", weight="bold"),
                rx.hstack(
                    alarm_level_badge("CRITICAL", AlarmState.critical_count),
                    alarm_level_badge("WARNING", AlarmState.warning_count),
                    alarm_level_badge("INFO", AlarmState.info_count),
                    rx.badge(
                        rx.hstack(
                            rx.text("Total:", size="1"),
                            rx.text(AlarmState.total_alarms.to_string(), size="1", weight="bold"),
                            spacing="1"
                        ),
                        variant="outline",
                        size="2"
                    ),
                    spacing="3"
                ),
                justify="between",
                width="100%"
            ),

            # 벡터 검색 바
            rx.hstack(
                rx.input(
                    value=AlarmState.vector_search_query,
                    on_change=AlarmState.set_vector_search_query,
                    placeholder="자연어로 알람 검색... (예: 온도 센서 위험)",
                    size="2",
                    width="400px"
                ),
                rx.button(
                    rx.icon("search", size=16),
                    "유사 알람 검색",
                    on_click=AlarmState.search_similar_alarms,
                    size="2",
                    variant="solid",
                    color_scheme="blue"
                ),
                rx.cond(
                    AlarmState.is_vector_search,
                    rx.button(
                        "검색 초기화",
                        on_click=AlarmState.clear_vector_search,
                        size="2",
                        variant="soft"
                    ),
                    rx.box()
                ),
                spacing="2"
            ),

            # 필터 컨트롤
            rx.hstack(
                # 레벨 필터
                rx.select(
                    ["all", "info", "warning", "critical", "emergency"],
                    value=AlarmState.filter_level,
                    on_change=AlarmState.set_filter_level,
                    placeholder="레벨 필터",
                    size="2"
                ),

                # 태그 필터
                rx.input(
                    value=AlarmState.filter_tag,
                    on_change=AlarmState.set_filter_tag,
                    placeholder="태그 검색...",
                    size="2",
                    width="200px"
                ),

                # 기간 필터
                rx.select(
                    ["1h", "6h", "24h", "7d", "30d"],
                    value=AlarmState.filter_date_range,
                    on_change=AlarmState.set_filter_date_range,
                    size="2"
                ),

                # 새로고침 버튼
                rx.button(
                    rx.icon("refresh-cw", size=16),
                    "새로고침",
                    on_click=AlarmState.load_alarm_events,
                    size="2",
                    variant="soft"
                ),

                spacing="3"
            ),

            spacing="3",
            width="100%"
        ),
        size="2"
    )


def alarm_event_card(event: dict) -> rx.Component:
    """개별 알람 이벤트 카드 - 자연어 설명 포함"""

    # 레벨별 스타일 - 항상 cond 사용 (Reflex foreach 호환)
    border_style = rx.cond(
        event["level"] == "CRITICAL",
        "border-l-4 border-red-500",
        rx.cond(
            event["level"] == "EMERGENCY",
            "border-l-4 border-red-500",
            rx.cond(
                event["level"] == "WARNING",
                "border-l-4 border-amber-500",
                "border-l-4 border-blue-500"
            )
        )
    )

    return rx.card(
        rx.vstack(
            # 헤더
            rx.hstack(
                rx.hstack(
                    # 레벨별 아이콘 조건부 표시
                    rx.cond(
                        event["level"] == "EMERGENCY",
                        rx.icon("siren", size=20, color="red"),
                        rx.cond(
                            event["level"] == "CRITICAL",
                            rx.icon("circle_alert", size=20, color="red"),
                            rx.cond(
                                event["level"] == "WARNING",
                                rx.icon("triangle_alert", size=20, color="amber"),
                                rx.icon("info", size=20, color="blue")
                            )
                        )
                    ),
                    rx.vstack(
                        rx.hstack(
                            rx.badge(
                                event["level"],
                                color_scheme=event["status_color"],
                                variant="solid",
                                size="1"
                            ),
                            rx.text(
                                event["main_tag"],
                                size="3",
                                weight="bold"
                            ),
                            rx.text(
                                f"= {event['main_value']:.2f}",
                                size="3",
                                weight="medium",
                                color="gray"
                            ),
                            spacing="2"
                        ),
                        rx.text(
                            event["triggered_at"],
                            size="1",
                            color="gray"
                        ),
                        spacing="0",
                        align="start"
                    ),
                    spacing="3"
                ),

                rx.hstack(
                    rx.cond(
                        event["acknowledged"],
                        rx.badge(
                            "확인됨",
                            color_scheme="green",
                            variant="soft",
                            size="1"
                        ),
                        rx.button(
                            "확인",
                            size="1",
                            variant="soft",
                            on_click=lambda: AlarmState.acknowledge_alarm(event["event_id"])
                        )
                    ),
                    rx.cond(
                        event["resolved"],
                        rx.badge(
                            "해결됨",
                            color_scheme="blue",
                            variant="soft",
                            size="1"
                        ),
                        rx.button(
                            "해결",
                            size="1",
                            variant="outline",
                            on_click=lambda: AlarmState.resolve_alarm(event["event_id"])
                        )
                    ),
                    spacing="2"
                ),

                justify="between",
                width="100%"
            ),

            # 자연어 설명
            rx.cond(
                event["natural_description"],
                rx.box(
                    rx.text(
                        event["natural_description"],
                        size="2",
                        color="gray.700",
                        class_name="italic"
                    ),
                    class_name="bg-gray-50 p-3 rounded-lg"
                ),
                rx.box()
            ),

            # 컨텍스트 정보
            rx.cond(
                event["context"],
                rx.box(
                    rx.vstack(
                        rx.text("📊 컨텍스트", size="1", weight="bold", color="gray"),
                        rx.text(
                            event["context"],
                            size="1",
                            color="gray.600"
                        ),
                        spacing="1"
                    ),
                    class_name="border-l-2 border-gray-300 pl-3"
                ),
                rx.box()
            ),

            # 권장사항 - 간단한 텍스트로 표시
            rx.cond(
                event.get("recommendations", []),
                rx.box(
                    rx.vstack(
                        rx.text("💡 권장 조치", size="1", weight="bold", color="blue"),
                        rx.text(
                            "• 현재 상황을 모니터링하세요",
                            size="1"
                        ),
                        rx.text(
                            "• 필요시 운영팀에 보고하세요",
                            size="1"
                        ),
                        spacing="2"
                    ),
                    class_name="bg-blue-50 p-3 rounded-lg"
                ),
                rx.box()
            ),

            # 기술적 상세 (접을 수 있음)
            rx.accordion.root(
                rx.accordion.item(
                    rx.accordion.trigger(
                        rx.hstack(
                            rx.text("기술적 상세", size="1", color="gray"),
                            rx.icon("chevron-down", size=14)
                        )
                    ),
                    rx.accordion.content(
                        rx.vstack(
                            rx.text(f"Event ID: {event['event_id']}", size="1", font_family="mono"),
                            rx.text(f"Scenario: {event['scenario_id']}", size="1"),
                            rx.text(f"원본 메시지: {event['message']}", size="1"),
                            rx.text("수행된 액션: 자동 알림 생성", size="1"),
                            spacing="1"
                        )
                    ),
                    value="details"
                ),
                collapsible=True,
                width="100%"
            ),

            spacing="3",
            width="100%"
        ),
        size="2",
        class_name=border_style,
        style={"cursor": "pointer"}
    )


def alarm_list_section() -> rx.Component:
    """알람 리스트 섹션"""
    return rx.cond(
        AlarmState.loading,
        rx.center(
            rx.spinner(size="3"),
            padding="8"
        ),
        rx.cond(
            AlarmState.error,
            rx.callout(
                AlarmState.error,
                icon="triangle_alert",
                color_scheme="red"
            ),
            rx.scroll_area(
                rx.vstack(
                    rx.foreach(
                        AlarmState.alarm_events,
                        lambda event: alarm_event_card(event)
                    ),
                    spacing="3",
                    width="100%"
                ),
                height="calc(100vh - 250px)",
                scrollbars="vertical"
            )
        )
    )


def alarm_viewer_page() -> rx.Component:
    """알람 뷰어 메인 페이지"""
    return shell(
        rx.vstack(
            # 페이지 헤더
            rx.hstack(
                rx.heading("알람 이벤트 뷰어", size="5"),
                rx.text(
                    "자연어 설명과 권장사항을 포함한 알람 관리",
                    size="2",
                    color="gray"
                ),
                align="center",
                spacing="3"
            ),

            # 필터 섹션
            alarm_filter_section(),

            # 알람 리스트
            alarm_list_section(),

            spacing="4",
            padding="4",
            width="100%"
        ),
        active_route="/alarms",
        on_mount=AlarmState.load_alarm_events
    )


# 페이지 등록용 함수
def register_alarm_page(app):
    """앱에 알람 페이지 등록"""
    app.add_page(alarm_viewer_page, route="/alarms", title="알람 뷰어")