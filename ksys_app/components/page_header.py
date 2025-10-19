"""통일된 페이지 헤더 컴포넌트
작성일: 2025-10-07
설명: 모든 페이지에서 일관된 헤더 디자인 제공
"""

import reflex as rx
from typing import Optional


def page_header(
    title: str,
    icon: str,
    actions: Optional[rx.Component] = None,
    subtitle: Optional[str] = None,
    show_divider: bool = False
) -> rx.Component:
    """통일된 페이지 헤더 컴포넌트

    Args:
        title: 페이지 제목
        icon: Lucide icon name
        actions: 오른쪽에 표시할 액션 컴포넌트 (버튼, 뱃지 등)
        subtitle: 부제목 (옵션)
        show_divider: 제목 아래 divider 표시 여부

    Returns:
        rx.Component: 통일된 스타일의 헤더 카드

    Example:
        ```python
        page_header(
            title="D100 센서 트렌드",
            icon="trending-up",
            actions=rx.button("새로고침", on_click=...),
            show_divider=True
        )
        ```
    """
    return rx.card(
        rx.vstack(
            # Title row with icon and actions
            rx.flex(
                rx.hstack(
                    rx.icon(icon, size=20, color="#3b82f6"),
                    rx.heading(title, size="5", weight="bold", color="#111827"),
                    spacing="2",
                    align="center"
                ),
                actions if actions else rx.fragment(),
                justify="between",
                align="center",
                width="100%"
            ),

            # Optional subtitle
            rx.cond(
                subtitle is not None,
                rx.text(subtitle, size="2", color="gray"),
                rx.fragment()
            ),

            # Optional divider
            rx.cond(
                show_divider,
                rx.divider(),
                rx.fragment()
            ),

            spacing="3",
            width="100%"
        ),
        padding="4",
        width="100%"
    )
