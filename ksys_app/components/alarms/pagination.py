"""
Pagination Component for Alarm Dashboard
=========================================

페이지 네비게이션 UI 제공
- 현재 페이지 / 총 페이지
- 이전/다음 버튼
- 페이지 번호 버튼

작성일: 2025-10-02
참고: docs/alarm/alarm-components.md
"""

import reflex as rx


def pagination(
    current_page: int | rx.Var,
    total_pages: int | rx.Var,
    total_items: int | rx.Var,
    page_size: int | rx.Var,
    on_prev: rx.EventHandler,
    on_next: rx.EventHandler,
    on_page_change: rx.EventHandler | None = None,
) -> rx.Component:
    """
    페이지네이션 컴포넌트

    Args:
        current_page: 현재 페이지 (1-indexed)
        total_pages: 총 페이지 수
        total_items: 총 아이템 수
        page_size: 페이지당 아이템 수
        on_prev: 이전 페이지 핸들러
        on_next: 다음 페이지 핸들러
        on_page_change: 특정 페이지로 이동 핸들러

    Returns:
        rx.Component: Pagination 컴포넌트

    Examples:
        >>> pagination(
        ...     current_page=AlarmsState.page,
        ...     total_pages=AlarmsState.total_pages,
        ...     total_items=AlarmsState.filtered_count,
        ...     page_size=AlarmsState.page_size,
        ...     on_prev=AlarmsState.prev_page,
        ...     on_next=AlarmsState.next_page,
        ... )
    """

    return rx.hstack(
        # 왼쪽: 항목 정보
        rx.text(
            f"Showing {(current_page - 1) * page_size + 1}-{rx.cond(current_page * page_size > total_items, total_items, current_page * page_size)} of {total_items}",
            size="2",
            color="gray",
        ),

        rx.spacer(),

        # 오른쪽: 페이지 버튼
        rx.hstack(
            # Previous 버튼
            rx.icon_button(
                rx.icon("chevron-left"),
                size="1",
                variant="soft",
                disabled=current_page == 1,
                on_click=on_prev,
            ),

            # 페이지 정보
            rx.text(
                f"{current_page} / {total_pages}",
                size="2",
                weight="medium",
            ),

            # Next 버튼
            rx.icon_button(
                rx.icon("chevron-right"),
                size="1",
                variant="soft",
                disabled=current_page >= total_pages,
                on_click=on_next,
            ),

            spacing="2",
            align="center",
        ),

        justify="between",
        align="center",
        width="100%",
        padding="3",
        border_top=f"1px solid {rx.color('gray', 3)}",
    )
