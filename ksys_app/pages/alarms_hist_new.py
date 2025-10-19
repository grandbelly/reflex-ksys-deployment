"""Simplified alarm history page with responsive design."""
import reflex as rx
from ..components.layout import shell
from ..states.alarm_hist_state import AlarmHistState


def alarms_hist_page() -> rx.Component:
    """Alarm history page with filtering and search."""
    return shell(
        rx.el.div(
            # Header
            rx.el.div(
                rx.el.h1(
                    "알람 이력 조회",
                    class_name="text-2xl font-bold text-gray-800"
                ),
                rx.el.p(
                    "과거 발생한 알람 이력을 조회하고 분석합니다",
                    class_name="text-gray-600 mt-1"
                ),
                class_name="mb-6"
            ),

            # Filter controls
            rx.el.div(
                # Date range selector
                rx.el.div(
                    rx.el.label("기간 선택", class_name="text-sm font-medium text-gray-700 mb-1"),
                    rx.el.div(
                        rx.button(
                            "오늘",
                            on_click=lambda: AlarmHistState.set_date_range("today"),
                            class_name=rx.cond(
                                AlarmHistState.selected_range == "today",
                                "px-3 py-1 bg-blue-500 text-white rounded-l",
                                "px-3 py-1 bg-gray-200 text-gray-700 rounded-l hover:bg-gray-300"
                            )
                        ),
                        rx.button(
                            "어제",
                            on_click=lambda: AlarmHistState.set_date_range("yesterday"),
                            class_name=rx.cond(
                                AlarmHistState.selected_range == "yesterday",
                                "px-3 py-1 bg-blue-500 text-white",
                                "px-3 py-1 bg-gray-200 text-gray-700 hover:bg-gray-300"
                            )
                        ),
                        rx.button(
                            "1주일",
                            on_click=lambda: AlarmHistState.set_date_range("week"),
                            class_name=rx.cond(
                                AlarmHistState.selected_range == "week",
                                "px-3 py-1 bg-blue-500 text-white",
                                "px-3 py-1 bg-gray-200 text-gray-700 hover:bg-gray-300"
                            )
                        ),
                        rx.button(
                            "1개월",
                            on_click=lambda: AlarmHistState.set_date_range("month"),
                            class_name=rx.cond(
                                AlarmHistState.selected_range == "month",
                                "px-3 py-1 bg-blue-500 text-white rounded-r",
                                "px-3 py-1 bg-gray-200 text-gray-700 rounded-r hover:bg-gray-300"
                            )
                        ),
                        class_name="inline-flex"
                    ),
                    class_name="flex flex-col"
                ),

                # Severity filter
                rx.el.div(
                    rx.el.label("심각도", class_name="text-sm font-medium text-gray-700 mb-1"),
                    rx.el.div(
                        rx.checkbox(
                            checked=AlarmHistState.show_critical,
                            on_change=AlarmHistState.toggle_critical,
                        ),
                        rx.el.label("Critical", class_name="ml-1 text-sm text-red-600 mr-3"),
                        rx.checkbox(
                            checked=AlarmHistState.show_warning,
                            on_change=AlarmHistState.toggle_warning,
                        ),
                        rx.el.label("Warning", class_name="ml-1 text-sm text-amber-600 mr-3"),
                        rx.checkbox(
                            checked=AlarmHistState.show_info,
                            on_change=AlarmHistState.toggle_info,
                        ),
                        rx.el.label("Info", class_name="ml-1 text-sm text-blue-600"),
                        class_name="flex items-center"
                    ),
                    class_name="flex flex-col"
                ),

                # Search button
                rx.button(
                    rx.icon("search", size=14),
                    "조회",
                    on_click=AlarmHistState.search_alarms,
                    class_name="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center gap-2 self-end"
                ),

                class_name="flex flex-wrap gap-4 mb-6 p-4 bg-gray-50 rounded-lg"
            ),

            # Statistics cards
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.span("총 알람", class_name="text-xs text-gray-500"),
                        rx.el.span(
                            f"{AlarmHistState.total_count}건",
                            class_name="text-xl font-bold text-gray-800"
                        ),
                        class_name="flex flex-col"
                    ),
                    class_name="bg-white p-4 rounded-lg border"
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.span("Critical", class_name="text-xs text-red-500"),
                        rx.el.span(
                            f"{AlarmHistState.critical_count}건",
                            class_name="text-xl font-bold text-red-600"
                        ),
                        class_name="flex flex-col"
                    ),
                    class_name="bg-red-50 p-4 rounded-lg border border-red-200"
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.span("Warning", class_name="text-xs text-amber-500"),
                        rx.el.span(
                            f"{AlarmHistState.warning_count}건",
                            class_name="text-xl font-bold text-amber-600"
                        ),
                        class_name="flex flex-col"
                    ),
                    class_name="bg-amber-50 p-4 rounded-lg border border-amber-200"
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.span("Info", class_name="text-xs text-blue-500"),
                        rx.el.span(
                            f"{AlarmHistState.info_count}건",
                            class_name="text-xl font-bold text-blue-600"
                        ),
                        class_name="flex flex-col"
                    ),
                    class_name="bg-blue-50 p-4 rounded-lg border border-blue-200"
                ),
                class_name="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6"
            ),

            # Alarm history table
            rx.el.div(
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("발생시간", class_name="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"),
                                rx.el.th("종료시간", class_name="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"),
                                rx.el.th("태그", class_name="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"),
                                rx.el.th("심각도", class_name="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"),
                                rx.el.th("메시지", class_name="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"),
                                rx.el.th("지속시간", class_name="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"),
                                class_name="bg-gray-50"
                            )
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                AlarmHistState.alarm_history,
                                lambda alarm: rx.el.tr(
                                    rx.el.td(
                                        alarm["start_time"],
                                        class_name="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                                    ),
                                    rx.el.td(
                                        alarm["end_time"],
                                        class_name="px-6 py-4 whitespace-nowrap text-sm text-gray-600"
                                    ),
                                    rx.el.td(
                                        alarm["tag_name"],
                                        class_name="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                                    ),
                                    rx.el.td(
                                        rx.el.span(
                                            alarm["severity"],
                                            class_name=rx.cond(
                                                alarm["severity"] == "CRITICAL",
                                                "px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800",
                                                rx.cond(
                                                    alarm["severity"] == "WARNING",
                                                    "px-2 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-800",
                                                    "px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800"
                                                )
                                            )
                                        ),
                                        class_name="px-6 py-4 whitespace-nowrap"
                                    ),
                                    rx.el.td(
                                        rx.el.span(
                                            alarm["message"],
                                            class_name="block max-w-md truncate",
                                            title=alarm["message"]
                                        ),
                                        class_name="px-6 py-4 text-sm text-gray-600"
                                    ),
                                    rx.el.td(
                                        alarm["duration"],
                                        class_name="px-6 py-4 whitespace-nowrap text-sm text-gray-500"
                                    ),
                                    class_name="hover:bg-gray-50"
                                )
                            ),
                            class_name="bg-white divide-y divide-gray-200"
                        ),
                        class_name="min-w-full divide-y divide-gray-200"
                    ),
                    class_name="overflow-x-auto"
                ),
                class_name="bg-white rounded-lg shadow"
            ),

            # Pagination
            rx.el.div(
                rx.el.div(
                    rx.el.span(
                        f"총 {AlarmHistState.total_count}개 중 {AlarmHistState.showing_count}개 표시",
                        class_name="text-sm text-gray-700"
                    ),
                    class_name="flex-1"
                ),
                rx.el.div(
                    rx.button(
                        "이전",
                        on_click=AlarmHistState.prev_page,
                        disabled=AlarmHistState.current_page == 1,
                        class_name=rx.cond(
                            AlarmHistState.current_page == 1,
                            "px-4 py-2 bg-gray-100 text-gray-400 rounded-l cursor-not-allowed",
                            "px-4 py-2 bg-white text-gray-700 border rounded-l hover:bg-gray-50"
                        )
                    ),
                    rx.el.span(
                        f"{AlarmHistState.current_page} / {AlarmHistState.total_pages}",
                        class_name="px-4 py-2 bg-white border-t border-b"
                    ),
                    rx.button(
                        "다음",
                        on_click=AlarmHistState.next_page,
                        disabled=AlarmHistState.current_page == AlarmHistState.total_pages,
                        class_name=rx.cond(
                            AlarmHistState.current_page == AlarmHistState.total_pages,
                            "px-4 py-2 bg-gray-100 text-gray-400 rounded-r cursor-not-allowed",
                            "px-4 py-2 bg-white text-gray-700 border rounded-r hover:bg-gray-50"
                        )
                    ),
                    class_name="flex items-center"
                ),
                class_name="flex justify-between items-center mt-4"
            ),

            # Empty state
            rx.cond(
                AlarmHistState.total_count == 0,
                rx.el.div(
                    rx.icon("inbox", size=64, color="gray"),
                    rx.el.h3(
                        "조회 결과가 없습니다",
                        class_name="text-xl font-semibold text-gray-800 mt-4"
                    ),
                    rx.el.p(
                        "선택한 기간에 발생한 알람이 없습니다",
                        class_name="text-gray-600 mt-2"
                    ),
                    class_name="flex flex-col items-center justify-center py-12"
                ),
                rx.text("")
            ),

            class_name="px-4 py-6"
        ),
        on_mount=AlarmHistState.on_load
    )