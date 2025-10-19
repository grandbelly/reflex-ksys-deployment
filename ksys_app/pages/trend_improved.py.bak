"""
Improved Trend Page with clean design
"""
import reflex as rx
from ..states.dashboard import DashboardState as D
from ..components.trend_enhanced import clean_area_chart, metric_card, time_range_pills, sensor_info_header
from ..components.layout import shell


def trend_page_improved() -> rx.Component:
    """Improved trend page with cleaner design"""
    return shell(
        rx.vstack(
            # Header with sensor info
            rx.card(
                sensor_info_header(
                    tag_name=rx.cond(D.tag_name, D.tag_name, "센서 선택"),
                    current_value=D.kpi_avg,
                    unit="",
                    status="normal",
                ),
                width="100%",
                class_name="bg-white shadow-sm",
            ),
            
            # Controls section
            rx.card(
                rx.vstack(
                    # Tag selector
                    rx.hstack(
                        rx.flex(
                            rx.icon("tag", size=16, color="gray"),
                            rx.text("태그 선택", size="2", weight="medium", color="gray"),
                            spacing="2",
                            align="center"
                        ),
                        rx.el.select(
                            rx.foreach(D.tags, lambda t: rx.el.option(t, value=t)),
                            value=rx.cond(D.tag_name, D.tag_name, ""),
                            on_change=[D.set_tag_select, D.load],
                            class_name="bg-white text-gray-900 px-3 py-2 rounded-lg border-2 border-gray-200 w-56 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
                        ),
                        align="center",
                    ),
                    
                    # Time range selector (pills style)
                    rx.box(
                        rx.text("조회 기간", size="2", weight="medium", color="gray", margin_bottom="8px"),
                        time_range_pills(D.window, lambda v: [D.set_window(v), D.load()]),
                    ),
                    
                    spacing="4",
                    width="100%",
                ),
                width="100%",
                class_name="bg-gray-50 border border-gray-200",
            ),
            
            # Main chart area
            rx.card(
                rx.vstack(
                    # Chart title and toggle
                    rx.hstack(
                        rx.heading("시계열 데이터", size="4", weight="bold"),
                        rx.spacer(),
                        # Chart mode toggle
                        rx.hstack(
                            rx.text("차트 모드:", size="2", color="gray"),
                            rx.segmented_control.root(
                                rx.segmented_control.item("Area", value="area"),
                                rx.segmented_control.item("Line", value="line"),
                                rx.segmented_control.item("Bar", value="bar"),
                                value="area",
                                size="1",
                            ),
                            spacing="2",
                            align="center",
                        ),
                    ),
                    
                    # Chart
                    rx.cond(
                        D.series_for_tag.length() > 0,
                        clean_area_chart(
                            data=D.series_for_tag,
                            height=400,
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("line-chart", size=48, color="gray"),
                                rx.text("데이터가 없습니다", size="4", color="gray"),
                                rx.text("태그와 조회 기간을 선택해주세요", size="2", color="gray"),
                                spacing="2",
                            ),
                            height="400px",
                        ),
                    ),
                    
                    spacing="4",
                    width="100%",
                ),
                width="100%",
                padding="24px",
            ),
            
            # Metrics summary
            rx.hstack(
                metric_card("평균", D.kpi_avg_s, "blue", "trending-up"),
                metric_card("최소", D.kpi_min_s, "green", "arrow-down"),
                metric_card("최대", D.kpi_max_s, "red", "arrow-up"),
                metric_card("데이터 포인트", D.kpi_count_s, "gray", "activity"),
                width="100%",
                spacing="3",
                wrap="wrap",
            ),
            
            spacing="4",
            width="100%",
            padding="20px",
        ),
    )