"""개선된 트렌드 페이지 - Syncing Charts with Brush"""
import reflex as rx
from ..states.trend_state import TrendState as T
from ..states.base import BaseState
from ..components.layout import shell
from ..utils.responsive import responsive_grid_columns, responsive_card, GRID_PRESETS


def chart_mode_selector() -> rx.Component:
    """차트 모드 선택자"""
    return rx.segmented_control.root(
        rx.segmented_control.item("Area", value="area"),
        rx.segmented_control.item("Line", value="line"),
        rx.segmented_control.item("Bar", value="bar"),
        value=T.chart_mode,
        size="2",
        on_change=T.set_chart_mode
    )


def trend_toggle_group() -> rx.Component:
    """트렌드 선택 세그먼트 컨트롤"""
    return rx.segmented_control.root(
        rx.segmented_control.item("Average", value="avg"),
        rx.segmented_control.item("Minimum", value="min"),
        rx.segmented_control.item("Maximum", value="max"),
        rx.segmented_control.item("First", value="first"),
        rx.segmented_control.item("Last", value="last"),
        value=T.trend_selected,
        on_change=T.set_trend_selected,
        size="2"
    )


def y_axis_mode_toggle() -> rx.Component:
    """Y축 모드 토글 버튼 - Auto/Fixed"""
    return rx.button(
        rx.cond(
            T.auto_scale,
            rx.hstack(
                rx.icon("maximize-2", size=16),
                "Auto",
                spacing="1"
            ),
            rx.hstack(
                rx.icon("minimize-2", size=16),
                "Fixed",
                spacing="1"
            )
        ),
        on_click=T.toggle_auto_scale,
        variant="soft",
        color_scheme=rx.cond(T.auto_scale, "green", "blue"),
        size="2"
    )


def aggregation_info_badge() -> rx.Component:
    """현재 선택된 집계 뷰와 시간 범위를 표시하는 배지"""
    return rx.hstack(
        rx.badge(
            rx.hstack(
                rx.icon("database", size=12),
                rx.text(
                    rx.cond(
                        T.aggregation_view == "1m", "1분 집계",
                        rx.cond(
                            T.aggregation_view == "10m", "10분 집계",
                            rx.cond(
                                T.aggregation_view == "1h", "1시간 집계",
                                rx.cond(
                                    T.aggregation_view == "1d", "1일 집계",
                                    "알 수 없음"
                                )
                            )
                        )
                    ),
                    size="1"
                ),
                spacing="1"
            ),
            color_scheme="blue",
            variant="soft"
        ),
        rx.badge(
            rx.hstack(
                rx.icon("clock", size=12),
                rx.text(
                    T.time_range_label,
                    size="1"
                ),
                spacing="1"
            ),
            color_scheme="green",
            variant="soft"
        ),
        spacing="2"
    )


def create_top_chart() -> rx.Component:
    """상단 차트 - 사용자 선택 타입 (Area/Line/Bar)"""
    # Area Chart
    area = rx.recharts.area_chart(
        rx.recharts.area(
            data_key=T.trend_selected,
            stroke="#3b82f6",
            fill="#3b82f6",
            fill_opacity=0.6,
            type_="monotone",
        ),
        rx.recharts.x_axis(
            data_key="bucket_formatted",
            angle=-45,
            text_anchor="end",
            height=80,
            tick={"fontSize": 10}
        ),
        rx.recharts.y_axis(
            domain=T.y_axis_domain
        ),
        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
        rx.recharts.tooltip(),
        data=T.series_for_tag,
        sync_id="trend",
        width="100%",
        height=300,  # 정수로 높이 지정
    )

    # Line Chart
    line = rx.recharts.line_chart(
        rx.recharts.line(
            data_key=T.trend_selected,
            stroke="#3b82f6",
            type_="monotone",
        ),
        rx.recharts.x_axis(
            data_key="bucket_formatted",
            angle=-45,
            text_anchor="end",
            height=80,
            tick={"fontSize": 10}
        ),
        rx.recharts.y_axis(
            domain=T.y_axis_domain
        ),
        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
        rx.recharts.tooltip(),
        data=T.series_for_tag,
        sync_id="trend",
        width="100%",
        height=300,
    )

    # Bar Chart
    bar = rx.recharts.bar_chart(
        rx.recharts.bar(
            data_key=T.trend_selected,
            fill="#3b82f6",
        ),
        rx.recharts.x_axis(
            data_key="bucket_formatted",
            angle=-45,
            text_anchor="end",
            height=80,
            tick={"fontSize": 10}
        ),
        rx.recharts.y_axis(
            domain=T.y_axis_domain
        ),
        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
        rx.recharts.tooltip(),
        data=T.series_for_tag,
        sync_id="trend",
        width="100%",
        height=300,
    )

    # 차트 타입에 따라 선택
    return rx.box(
        rx.cond(
            T.chart_mode == "line",
            line,
            rx.cond(
                T.chart_mode == "bar",
                bar,
                area  # default
            )
        ),
        width="100%"
    )


def create_bottom_chart_with_brush() -> rx.Component:
    """하단 차트 - Composed Chart with Brush (고정)"""
    return rx.box(
        rx.recharts.composed_chart(
            rx.recharts.area(
                data_key="avg",
                stroke="#3b82f6",
                fill="#3b82f6",
                fill_opacity=0.3,
                type_="monotone",
                name="Average"
            ),
            rx.recharts.line(
                data_key="max",
                stroke="#ef4444",
                type_="monotone",
                name="Maximum"
            ),
            rx.recharts.line(
                data_key="min",
                stroke="#10b981",
                type_="monotone",
                name="Minimum"
            ),
            rx.recharts.x_axis(
                data_key="bucket_formatted",
                angle=-45,
                text_anchor="end",
                height=80,
                tick={"fontSize": 10}
            ),
            rx.recharts.y_axis(
                domain=rx.cond(
                    T.auto_scale,
                    ["auto", "auto"],
                    ["dataMin - 5", "dataMax + 5"]
                )
            ),
            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
            rx.recharts.tooltip(),
            rx.recharts.legend(),
            rx.recharts.brush(
                data_key="bucket_formatted",
                height=40,
                stroke="#8884d8",
                fill="#f0f0f0"
            ),
            data=T.series_for_tag,
            sync_id="trend",
            width="100%",
            height=350,  # Brush 공간 확보
        ),
        width="100%"
    )


def trend_chart_area() -> rx.Component:
    """차트 영역 - 두 개의 동기화된 차트"""
    # 로딩 스피너
    loading_spinner = rx.center(
        rx.vstack(
            rx.spinner(size="3", color="blue"),
            rx.text("데이터 로딩 중...", size="3", color="#6b7280"),
            spacing="3"
        ),
        width="100%",
        height="600px",
        bg="white"
    )

    # 데이터 없음 메시지
    no_data_message = rx.center(
        rx.vstack(
            rx.icon("circle-alert", size=48, color="#9ca3af"),
            rx.text("차트 데이터가 없습니다", size="4", weight="bold", color="#6b7280"),
            rx.text("필터를 조정하고 다시 로드하세요", size="2", color="#9ca3af"),
            spacing="3"
        ),
        width="100%",
        height="600px",
        bg="white"
    )

    # 두 개의 동기화된 차트
    synced_charts = rx.vstack(
        # 상단 차트 - 사용자 선택
        rx.box(
            rx.vstack(
                rx.badge(
                    rx.cond(
                        T.chart_mode == "area", "Area Chart",
                        rx.cond(
                            T.chart_mode == "line", "Line Chart",
                            "Bar Chart"
                        )
                    ),
                    " - ",
                    T.trend_selected.upper(),
                    color_scheme="blue",
                    variant="soft",
                    size="2"
                ),
                create_top_chart(),
                spacing="2",
                width="100%"
            ),
            padding="3",
            border_radius="lg",
            bg="white",
            border="1px solid #e5e7eb",
            width="100%",
            min_width="0"  # flex-shrink 허용
        ),

        # 하단 차트 - Composed with Brush
        rx.box(
            rx.vstack(
                rx.badge(
                    "Comparison Chart (Avg, Max, Min) with Time Brush",
                    color_scheme="purple",
                    variant="soft",
                    size="2"
                ),
                create_bottom_chart_with_brush(),
                spacing="2",
                width="100%"
            ),
            padding="3",
            border_radius="lg",
            bg="white",
            border="1px solid #e5e7eb",
            width="100%",
            min_width="0"  # flex-shrink 허용
        ),

        spacing="4",
        width="100%"
    )

    # 로딩/데이터 없음/차트 선택
    return rx.cond(
        T.loading,
        loading_spinner,
        rx.cond(
            T.series_for_tag,
            synced_charts,
            no_data_message
        )
    )


def trend_page_enhanced_v2() -> rx.Component:
    """개선된 트렌드 페이지 v2"""
    return shell(
        rx.vstack(
            # 상단 컨트롤 영역
            rx.card(
                rx.vstack(
                    # Header
                    rx.flex(
                        rx.hstack(
                            rx.icon("chart-line", size=20, color="#3b82f6"),
                            rx.heading(
                                rx.cond(
                                    T.tag_name,
                                    f"{T.tag_name} 센서 트렌드",
                                    "센서 트렌드"
                                ),
                                size="5",
                                weight="bold",
                                color="#111827"
                            ),
                            spacing="2",
                            align="center"
                        ),
                        rx.button(
                            rx.icon("refresh-cw", size=16),
                            " 새로고침",
                            on_click=T.load,
                            variant="soft",
                            color_scheme="blue",
                            size="2",
                        ),
                        justify="between",
                        align="center",
                        width="100%"
                    ),

                    rx.divider(),

                    # 필터 컨트롤
                    rx.grid(
                        # 태그 선택
                        rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.icon("tag", size=14, color="#3b82f6"),
                                    rx.text("태그 선택", size="2", weight="medium", color="#374151"),
                                    spacing="1",
                                    align="center"
                                ),
                                rx.select(
                                    T.tags,
                                    value=T.tag_name,
                                    on_change=T.set_tag_select,
                                    placeholder="선택하세요",
                                    size="2",
                                    width="100%"
                                ),
                                spacing="2",
                                width="100%"
                            ),
                            padding="3",
                            border_radius="md",
                            bg="#eff6ff",
                            border="1px solid #dbeafe",
                            width="100%",
                            min_width="0"  # flex-shrink 허용
                        ),

                        # 집계 단위 선택
                        rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.icon("layers", size=14, color="#10b981"),
                                    rx.text("집계 단위", size="2", weight="medium", color="#374151"),
                                    spacing="1",
                                    align="center"
                                ),
                                rx.select(
                                    ["1m", "10m", "1h", "1d"],
                                    value=T.aggregation_view,
                                    on_change=T.set_aggregation_view,
                                    placeholder="선택하세요",
                                    size="2",
                                    width="100%"
                                ),
                                spacing="2",
                                width="100%"
                            ),
                            padding="3",
                            border_radius="md",
                            bg="#d1fae5",
                            border="1px solid #a7f3d0",
                            width="100%",
                            min_width="0"  # flex-shrink 허용
                        ),

                        # 조회 기간 선택
                        rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.icon("calendar", size=14, color="#f59e0b"),
                                    rx.text("조회 기간", size="2", weight="medium", color="#374151"),
                                    spacing="1",
                                    align="center"
                                ),
                                rx.select(
                                    T.time_range_labels,
                                    value=T.time_range_display,
                                    on_change=T.set_time_range,
                                    placeholder="선택하세요",
                                    size="2",
                                    width="100%"
                                ),
                                spacing="2",
                                width="100%"
                            ),
                            padding="3",
                            border_radius="md",
                            bg="#fef3c7",
                            border="1px solid #fde68a",
                            width="100%",
                            min_width="0"  # flex-shrink 허용
                        ),

                        columns=GRID_PRESETS["filters_1_2_3"],
                        gap="3",
                        width="100%"
                    ),

                    # 현재 선택 요약
                    rx.divider(),
                    rx.flex(
                        # 현재 태그 배지
                        rx.badge(
                            rx.icon("activity", size=12),
                            " ",
                            rx.cond(
                                T.tag_name,
                                T.tag_name,
                                "선택 안됨"
                            ),
                            color_scheme="purple",
                            variant="soft",
                            size="2"
                        ),

                        rx.spacer(),

                        # 상태 표시
                        aggregation_info_badge(),

                        spacing="2",
                        align="center",
                        width="100%"
                    ),

                    spacing="4",
                    width="100%"
                ),
                size="3",
                width="100%"
            ),

            # 차트 영역
            rx.card(
                rx.vstack(
                    # 차트 컨트롤
                    rx.grid(
                        rx.vstack(
                            rx.text("상단 차트 타입", size="2", weight="medium", color="#374151"),
                            chart_mode_selector(),
                            spacing="1",
                            align="start",
                            width="100%"
                        ),

                        rx.vstack(
                            rx.text("Y축 조정", size="2", weight="medium", color="#374151"),
                            y_axis_mode_toggle(),
                            spacing="1",
                            align="start",
                            width="100%"
                        ),

                        rx.vstack(
                            rx.text("데이터 선택", size="2", weight="medium", color="#374151"),
                            trend_toggle_group(),
                            spacing="1",
                            align="start",
                            width="100%"
                        ),

                        columns=responsive_grid_columns(mobile=1, tablet=3, desktop=3),
                        gap="3",
                        width="100%"
                    ),

                    rx.divider(),

                    # 안내 메시지
                    rx.callout.root(
                        rx.callout.icon(rx.icon("info")),
                        rx.callout.text(
                            "💡 하단 차트의 ",
                            rx.text("Brush(회색 영역)", weight="bold", as_="span"),
                            "를 드래그하여 시간 범위를 선택하세요. 두 차트가 동기화됩니다."
                        ),
                        color_scheme="blue",
                        variant="soft",
                        size="1"
                    ),

                    # 차트 렌더링
                    rx.box(
                        trend_chart_area(),
                        width="100%",
                    ),

                    spacing="3",
                    width="100%"
                ),
                class_name="mb-4",
                width="100%"
            ),

            # 데이터 테이블
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.heading("Historical Data", size="4", weight="bold", color="#111827"),
                        rx.spacer(),
                        rx.hstack(
                            # 데이터 개수
                            rx.badge(
                                rx.cond(
                                    T.series_for_tag,
                                    rx.fragment(
                                        rx.text(T.series_count_s),
                                        " / ",
                                        rx.text(T.expected_data_count),
                                        " rows"
                                    ),
                                    "No data"
                                ),
                                color_scheme="gray"
                            ),
                            # 데이터 완전성
                            rx.cond(
                                T.series_for_tag,
                                rx.badge(
                                    rx.icon("activity", size=14),
                                    " ",
                                    T.data_completeness,
                                    color_scheme=rx.cond(
                                        T.missing_data_count > 0,
                                        "orange",
                                        "green"
                                    ),
                                    variant="soft"
                                ),
                                rx.fragment()
                            ),
                            # 결측 데이터
                            rx.cond(
                                T.missing_data_count > 0,
                                rx.badge(
                                    rx.icon("circle-alert", size=14),
                                    " ",
                                    T.missing_data_count,
                                    " missing",
                                    color_scheme="red",
                                    variant="soft"
                                ),
                                rx.fragment()
                            ),
                            rx.button(
                                rx.icon("download", size=16),
                                "CSV 내보내기",
                                on_click=T.export_csv,
                                variant="soft",
                                color_scheme="green",
                                size="2",
                                disabled=rx.cond(T.series_for_tag, False, True)
                            ),
                            spacing="3"
                        ),
                        align="center",
                        width="100%"
                    ),

                    rx.divider(),

                    rx.cond(
                        T.series_for_tag,
                        rx.box(
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("No."),
                                        rx.table.column_header_cell("Tag"),
                                        rx.table.column_header_cell("Timestamp"),
                                        rx.table.column_header_cell("Average"),
                                        rx.table.column_header_cell("Min"),
                                        rx.table.column_header_cell("Max"),
                                        rx.table.column_header_cell("Last"),
                                        rx.table.column_header_cell("First"),
                                        rx.table.column_header_cell("Count")
                                    )
                                ),
                                rx.table.body(
                                    rx.foreach(
                                        T.series_for_tag_desc_with_num,
                                        lambda row: rx.table.row(
                                            rx.table.cell(row["No"]),
                                            rx.table.cell(row["Tag"]),
                                            rx.table.cell(
                                                row["Timestamp"],
                                                style=rx.cond(
                                                    row.get("Missing", False),
                                                    {"color": "#ef4444", "fontWeight": "500"},
                                                    {}
                                                )
                                            ),
                                            rx.table.cell(
                                                row["Average"],
                                                style=rx.cond(
                                                    row.get("Missing", False),
                                                    {"color": "#9ca3af", "fontStyle": "italic"},
                                                    {}
                                                )
                                            ),
                                            rx.table.cell(
                                                row["Min"],
                                                style=rx.cond(
                                                    row.get("Missing", False),
                                                    {"color": "#9ca3af", "fontStyle": "italic"},
                                                    {}
                                                )
                                            ),
                                            rx.table.cell(
                                                row["Max"],
                                                style=rx.cond(
                                                    row.get("Missing", False),
                                                    {"color": "#9ca3af", "fontStyle": "italic"},
                                                    {}
                                                )
                                            ),
                                            rx.table.cell(
                                                row["Last"],
                                                style=rx.cond(
                                                    row.get("Missing", False),
                                                    {"color": "#9ca3af", "fontStyle": "italic"},
                                                    {}
                                                )
                                            ),
                                            rx.table.cell(
                                                row["First"],
                                                style=rx.cond(
                                                    row.get("Missing", False),
                                                    {"color": "#9ca3af", "fontStyle": "italic"},
                                                    {}
                                                )
                                            ),
                                            rx.table.cell(
                                                row["Count"],
                                                style=rx.cond(
                                                    row.get("Missing", False),
                                                    {"color": "#9ca3af", "fontStyle": "italic"},
                                                    {}
                                                )
                                            ),
                                            style=rx.cond(
                                                row.get("Missing", False),
                                                {"backgroundColor": "#fef2f2"},
                                                {}
                                            )
                                        )
                                    )
                                ),
                                width="100%",
                                variant="surface",
                                size="2"
                            ),
                            class_name="w-full overflow-x-auto"
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("database", size=48, color="#9ca3af"),
                                rx.text("데이터가 없습니다", size="3", color="#6b7280"),
                                rx.text("태그를 선택하고 조회 기간을 설정하세요", size="2", color="#9ca3af"),
                                spacing="3",
                                align="center"
                            ),
                            height="300px",
                            class_name="border-2 border-dashed border-gray-200 rounded-lg bg-white"
                        )
                    ),

                    spacing="3",
                    width="100%"
                ),
                width="100%"
            ),

            spacing="4",
            width="100%",
            class_name="p-2 sm:p-4 md:p-6 max-w-full bg-white min-h-screen"
        ),
        active_route="/trend",
        on_mount=T.load
    )
