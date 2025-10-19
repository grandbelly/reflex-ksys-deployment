"""
Communication Success Rate Page - Light Mode Design
====================================================

통신 성공률 모니터링 페이지
- KPI 카드 (그라데이션 배경)
- 일별 트렌드 차트 (영역 차트 + 기준선)
- 시간대 분석
- Light Mode 전용 디자인

작성일: 2025-10-03
참고: docs/comms/communication-design-specs.md
"""

import reflex as rx
from ..components.layout import shell
from ..states.communication_state import CommunicationState


# ============================================================================
# KPI 카드 컴포넌트 (그라데이션 배경)
# ============================================================================

def comm_kpi_card(
    title: str,
    value: str | rx.Var,
    subtitle: str | rx.Var = "",
    gradient_from: str = "blue",
    gradient_to: str = "cyan",
    icon: str = "activity",
) -> rx.Component:
    """
    통신 성공률 KPI 카드 (그라데이션 배경)

    Examples:
        >>> comm_kpi_card(
        ...     title="평균 성공률",
        ...     value=CommunicationState.overall_success_rate,
        ...     subtitle="지난 24시간",
        ...     gradient_from="blue",
        ...     gradient_to="cyan",
        ...     icon="activity"
        ... )
    """
    return rx.card(
        rx.vstack(
            # 상단: 아이콘 + 타이틀
            rx.flex(
                rx.icon(
                    icon,
                    size=24,
                    color="white",
                ),
                rx.text(
                    title,
                    size="2",
                    weight="medium",
                    color="white",
                    class_name="opacity-90",
                ),
                align="center",
                gap="2",
            ),

            # 중앙: 큰 값
            rx.text(
                value,
                size="8",
                weight="bold",
                color="white",
                class_name="mt-4 mb-2",
            ),

            # 하단: 서브타이틀
            rx.cond(
                subtitle != "",
                rx.text(
                    subtitle,
                    size="1",
                    color="white",
                    class_name="opacity-75",
                ),
                rx.fragment(),
            ),

            spacing="1",
            align="start",
            width="100%",
        ),
        size="2",
        variant="classic",
        class_name=f"bg-gradient-to-br from-{gradient_from}-500 to-{gradient_to}-600 shadow-lg hover:shadow-xl transition-all duration-300",
        style={"min_height": "160px"},
    )


# ============================================================================
# 필터 컨트롤
# ============================================================================

def filter_controls() -> rx.Component:
    """센서 선택 + 기간 필터"""
    return rx.flex(
        # 센서 선택
        rx.box(
            rx.text("센서 선택:", size="2", weight="medium", class_name="mb-2"),
            rx.select(
                CommunicationState.available_tags,
                value=CommunicationState.selected_tag,
                on_change=CommunicationState.set_selected_tag,
                placeholder="센서 선택",
                size="2",
            ),
        ),

        # 기간 선택 (Segmented Control)
        rx.box(
            rx.text("조회 기간:", size="2", weight="medium", class_name="mb-2"),
            rx.segmented_control.root(
                rx.segmented_control.item("3일", value="3"),
                rx.segmented_control.item("7일", value="7"),
                rx.segmented_control.item("14일", value="14"),
                rx.segmented_control.item("30일", value="30"),
                value=CommunicationState.selected_days_str,
                on_change=CommunicationState.set_selected_days_str,
                default_value="7",
                size="2",
            ),
        ),

        # 새로고침 버튼
        rx.button(
            rx.icon("refresh-cw", size=18),
            "새로고침",
            variant="outline",
            size="2",
            on_click=CommunicationState.load_data,
            loading=CommunicationState.loading,
        ),

        justify="between",
        align="end",
        gap="4",
        width="100%",
        class_name="flex-wrap p-4 bg-white border border-gray-200 rounded-lg",
    )


# ============================================================================
# 알림 배너 (조건부 표시)
# ============================================================================

def alert_banner() -> rx.Component:
    """저성능 센서 알림 배너"""
    return rx.cond(
        CommunicationState.overall_success_rate < 95.0,
        rx.box(
            rx.flex(
                rx.icon(
                    "triangle-alert",
                    size=24,
                    color="white",
                ),
                rx.text(
                    f"⚠️ 성공률 저하 감지: {CommunicationState.overall_success_rate}% (기준: 95% 이상)",
                    size="3",
                    weight="medium",
                    color="white",
                ),
                align="center",
                gap="3",
            ),
            padding="4",
            border_radius="lg",
            class_name="bg-gradient-to-r from-orange-500 to-red-600 shadow-lg mb-4",
        ),
        rx.fragment(),
    )


# ============================================================================
# 차트 컴포넌트
# ============================================================================

def daily_trend_chart() -> rx.Component:
    """일별 트렌드 영역 차트 (기준선 포함)"""
    return rx.card(
        rx.vstack(
            rx.text("일별 성공률 트렌드", size="4", weight="bold", class_name="mb-4"),

            rx.cond(
                CommunicationState.daily_chart_data.length() > 0,
                rx.recharts.area_chart(
                    # 영역 (성공률)
                    rx.recharts.area(
                        data_key="success_rate",
                        fill=rx.color("blue", 3),
                        stroke=rx.color("blue", 7),
                        fill_opacity=0.6,
                        type_="monotone",
                    ),

                    # 기준선 (95%)
                    rx.recharts.reference_line(
                        y=95,
                        stroke=rx.color("red", 7),
                        stroke_width=2,
                        stroke_dasharray="5 5",
                        label="기준선 95%",
                    ),

                    # 축
                    rx.recharts.x_axis(
                        data_key="date",
                    ),
                    rx.recharts.y_axis(
                        domain=[0, 100],
                    ),

                    # 그리드 + 툴팁
                    rx.recharts.cartesian_grid(
                        stroke_dasharray="3 3",
                        stroke=rx.color("gray", 3),
                    ),
                    rx.recharts.graphing_tooltip(),

                    data=CommunicationState.daily_chart_data,
                    width="100%",
                    height=400,
                ),
                rx.text("데이터 없음", size="2", color="gray", class_name="text-center py-12"),
            ),

            spacing="3",
            width="100%",
        ),
        size="2",
        variant="classic",
    )


def hourly_bar_chart() -> rx.Component:
    """시간대별 성공률 바 차트"""
    return rx.card(
        rx.vstack(
            rx.text("시간대별 성공률 분포", size="4", weight="bold", class_name="mb-4"),

            rx.cond(
                CommunicationState.hourly_data.length() > 0,
                rx.recharts.bar_chart(
                    rx.recharts.bar(
                        data_key="success_rate",
                        fill=rx.color("blue", 7),
                        radius=[8, 8, 0, 0],
                    ),
                    rx.recharts.x_axis(
                        data_key="hour",
                    ),
                    rx.recharts.y_axis(
                        domain=[0, 100],
                    ),
                    rx.recharts.cartesian_grid(
                        stroke_dasharray="3 3",
                        stroke=rx.color("gray", 3),
                    ),
                    rx.recharts.graphing_tooltip(),
                    data=CommunicationState.hourly_data,
                    width="100%",
                    height=300,
                ),
                rx.text("데이터 없음", size="2", color="gray", class_name="text-center py-12"),
            ),

            spacing="3",
            width="100%",
        ),
        size="2",
        variant="classic",
    )


# ============================================================================
# 시간대 분석 카드
# ============================================================================

def period_analysis_card() -> rx.Component:
    """시간대 분석 (최적/최악 시간, 안정성)"""
    return rx.card(
        rx.vstack(
            rx.text(
                "시간대 분석",
                size="4",
                weight="bold",
                class_name="mb-4",
            ),

            # 최적 시간
            rx.flex(
                rx.icon("sun", size=20, color=rx.color("green", 9)),
                rx.vstack(
                    rx.text("최적 시간", size="1", color="gray"),
                    rx.text(
                        CommunicationState.hourly_pattern_stats['best_hour'],
                        size="3",
                        weight="bold",
                    ),
                    spacing="0",
                    align="start",
                ),
                gap="3",
                align="center",
            ),

            # 최악 시간
            rx.flex(
                rx.icon("moon", size=20, color=rx.color("red", 9)),
                rx.vstack(
                    rx.text("최악 시간", size="1", color="gray"),
                    rx.text(
                        CommunicationState.hourly_pattern_stats['worst_hour'],
                        size="3",
                        weight="bold",
                    ),
                    spacing="0",
                    align="start",
                ),
                gap="3",
                align="center",
            ),

            # 안정성
            rx.flex(
                rx.icon("shield-check", size=20, color=rx.color("blue", 9)),
                rx.vstack(
                    rx.text("표준편차", size="1", color="gray"),
                    rx.text(
                        f"{CommunicationState.hourly_pattern_stats['std_dev']}%",
                        size="3",
                        weight="bold",
                    ),
                    spacing="0",
                    align="start",
                ),
                gap="3",
                align="center",
            ),

            spacing="4",
            align="start",
            width="100%",
        ),
        size="2",
        variant="classic",
    )


# ============================================================================
# 메인 페이지
# ============================================================================

@rx.page(route="/comm", title="Communication | KSYS", on_load=CommunicationState.load_data)
def communication_page() -> rx.Component:
    """통신 성공률 페이지 - Light Mode Design"""

    return shell(
        rx.box(
            rx.vstack(
                # 페이지 헤더
                rx.flex(
                    rx.text(
                        "통신 성공률",
                        size="6",
                        weight="bold",
                    ),
                    rx.badge(
                        "Real-time",
                        variant="soft",
                        color="green",
                    ),
                    justify="between",
                    align="center",
                    width="100%",
                    class_name="mb-4",
                ),

                # 필터 컨트롤
                filter_controls(),

                # 알림 배너 (조건부)
                alert_banner(),

                # KPI 카드 그리드
                rx.cond(
                    CommunicationState.loading,
                    rx.box(
                        rx.spinner(size="3"),
                        rx.text("데이터 로딩 중...", class_name="ml-3"),
                        class_name="flex items-center justify-center py-12",
                    ),
                    rx.grid(
                        # 1. 평균 성공률
                        comm_kpi_card(
                            title="평균 성공률",
                            value=f"{CommunicationState.overall_success_rate}%",
                            subtitle=f"지난 {CommunicationState.selected_days}일",
                            gradient_from="blue",
                            gradient_to="cyan",
                            icon="activity",
                        ),

                        # 2. 전체 레코드
                        comm_kpi_card(
                            title="전체 레코드",
                            value=f"{CommunicationState.total_records:,}",
                            subtitle=f"예상: {CommunicationState.expected_records:,}",
                            gradient_from="green",
                            gradient_to="emerald",
                            icon="database",
                        ),

                        # 3. 활성 시간
                        comm_kpi_card(
                            title="활성 시간",
                            value=CommunicationState.active_hours_str,
                            subtitle=CommunicationState.total_hours_str,
                            gradient_from="purple",
                            gradient_to="pink",
                            icon="clock",
                        ),

                        # 4. 데이터 품질
                        comm_kpi_card(
                            title="데이터 품질",
                            value=rx.cond(
                                CommunicationState.overall_success_rate >= 95,
                                "Excellent",
                                rx.cond(
                                    CommunicationState.overall_success_rate >= 80,
                                    "Good",
                                    rx.cond(
                                        CommunicationState.overall_success_rate >= 60,
                                        "Warning",
                                        "Critical"
                                    )
                                )
                            ),
                            subtitle=f"{CommunicationState.selected_tag} 센서",
                            gradient_from=rx.cond(
                                CommunicationState.overall_success_rate >= 95,
                                "green",
                                rx.cond(
                                    CommunicationState.overall_success_rate >= 80,
                                    "blue",
                                    "orange"
                                )
                            ),
                            gradient_to=rx.cond(
                                CommunicationState.overall_success_rate >= 95,
                                "emerald",
                                rx.cond(
                                    CommunicationState.overall_success_rate >= 80,
                                    "cyan",
                                    "red"
                                )
                            ),
                            icon="circle-check",
                        ),

                        columns=rx.breakpoints(initial="1", sm="2", lg="4"),
                        gap="4",
                        width="100%",
                    ),
                ),

                # 차트 섹션 (2열)
                rx.grid(
                    # 일별 트렌드
                    daily_trend_chart(),

                    # 시간대 분석
                    period_analysis_card(),

                    columns=rx.breakpoints(initial="1", lg="2"),
                    gap="4",
                    width="100%",
                ),

                # 시간대별 분포
                hourly_bar_chart(),

                spacing="6",
                width="100%",
            ),
            padding="6",
            max_width="1400px",
            margin="0 auto",
        ),
        active_route="/comm",
    )
