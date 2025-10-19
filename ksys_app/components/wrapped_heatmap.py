"""
Properly wrapped React Grid Heatmap for Reflex
"""

import reflex as rx
from typing import List, Dict, Any


class HeatMapGrid(rx.Component):
    """React Grid Heatmap Component"""

    library = "react-grid-heatmap@1.3.0"
    tag = "HeatMapGrid"

    # Props
    data: rx.Var[List[List[float]]]
    xLabels: rx.Var[List[str]]
    yLabels: rx.Var[List[str]]
    cellHeight: rx.Var[str] = "30px"
    square: rx.Var[bool] = False
    xLabelsPos: rx.Var[str] = "bottom"
    yLabelsPos: rx.Var[str] = "left"

    # Color customization
    cellRender: rx.Var[Any] = None  # Custom cell renderer
    cellStyle: rx.Var[Any] = None   # Custom cell style function


def wrapped_grid_heatmap(state) -> rx.Component:
    """
    Wrapped React Grid Heatmap - Clean version without legend
    Fully responsive with horizontal scroll for small screens
    """

    return rx.vstack(
        # Heatmap Stats
        rx.hstack(
            rx.badge(f"Tag: {state.selected_tag}", color="blue", variant="soft"),
            rx.badge(f"Period: {state.selected_days} days", color="green", variant="soft"),
            rx.badge(
                f"Success: {state.overall_success_rate}%",
                color=rx.cond(
                    state.overall_success_rate >= 95, "green",
                    rx.cond(
                        state.overall_success_rate >= 80, "blue",
                        rx.cond(
                            state.overall_success_rate >= 60, "amber",
                            "red"
                        )
                    )
                ),
                variant="soft"
            ),
            spacing="2",
            width="100%",
            flex_wrap="wrap",  # Allow wrapping on small screens
        ),

        # The Heatmap Component with horizontal scroll - FIXED FOR CARD RESPONSIVENESS
        rx.cond(
            state.heatmap_matrix,
            rx.box(
                rx.box(
                    rx.vstack(
                        # Hour labels (x-axis)
                        rx.hstack(
                            rx.box(width="90px", min_width="90px"),  # Spacer for date column
                            rx.foreach(
                                state.hour_labels,
                                lambda hour: rx.box(
                                    rx.text(hour, font_size="11px", weight="medium", color="gray"),
                                    width="32px",
                                    min_width="28px",
                                    display="flex",
                                    align_items="center",
                                    justify_content="center",
                                )
                            ),
                            spacing="2",
                            align="center",
                        ),
                        # Heatmap rows
                        rx.foreach(
                            state.heatmap_matrix,
                            lambda row, row_idx: render_heatmap_row(row, row_idx, state)
                        ),
                        spacing="2",
                    ),
                    min_width="fit-content",  # Critical: Allow content to determine width
                ),
                width="100%",
                overflow_x="auto",  # Enable horizontal scroll
                overflow_y="visible",
                padding_bottom="4",
                # Add smooth scrolling
                style={
                    "-webkit-overflow-scrolling": "touch",  # Smooth scroll on iOS
                    "scrollbar-width": "thin",  # Firefox
                }
            ),
            rx.text("데이터 로딩 중...", color="gray")
        ),

        spacing="3",
        width="100%",
        align="start",  # Align to start to prevent stretching
    )


def render_heatmap_row(row: list, row_idx: int, state) -> rx.Component:
    """히트맵의 각 행을 렌더링 - Better sizing and alignment"""
    return rx.hstack(
        # 날짜 레이블 - Fixed width to prevent layout shift
        rx.box(
            rx.text(
                state.date_labels[row_idx],
                font_size="12px",
                weight="medium",
                color="gray"
            ),
            width="90px",
            min_width="90px",
            flex_shrink="0",
            display="flex",
            align_items="center",
        ),
        # 각 시간 셀
        rx.foreach(
            row,
            lambda val, col_idx: render_heatmap_cell(val, col_idx)
        ),
        spacing="2",
        align="center",
    )


def render_heatmap_cell(val: float, col_idx: int) -> rx.Component:
    """히트맵의 각 셀을 렌더링 - Larger cells with better responsiveness"""
    return rx.box(
        rx.text(
            f"{val:.0f}",
            font_size="11px",
            color="white",
            weight="medium"
        ),
        width="32px",  # Increased from 20px
        height="32px",  # Increased from 20px
        min_width="28px",  # Prevent shrinking too much
        min_height="28px",
        bg=rx.cond(
            val >= 95, "#22c55e",  # green
            rx.cond(
                val >= 80, "#3b82f6",  # blue
                rx.cond(
                    val >= 60, "#fbbf24",  # amber
                    "#ef4444"  # red
                )
            )
        ),
        opacity=rx.cond(val >= 30, val / 100, 0.3),
        display="flex",
        align_items="center",
        justify_content="center",
        border_radius="4px",
        flex_shrink="0"  # Prevent cells from shrinking
    )