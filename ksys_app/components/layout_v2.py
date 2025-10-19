"""
SalesX-style Layout Components (Purple Theme)
Improved sidebar, header, and shell based on design system
"""
import reflex as rx
import os
from ..states.base_state import BaseState as B

# AI 기능 활성화 여부
ENABLE_AI_FEATURES = os.getenv('ENABLE_AI_FEATURES', 'true').lower() == 'true'
APP_VERSION = os.getenv("APP_VERSION", "FULL").upper()

if APP_VERSION == "PART":
    ENABLE_AI_FEATURES = False

# 메뉴 구성
BASE_MENU = [
    {"type": "header", "name": "모니터링"},
    {"icon": "home", "name": "Dashboard", "path": "/", "desc": "실시간 모니터링"},
    {"icon": "trending-up", "name": "Trend", "path": "/trend", "desc": "시계열 분석"},
    {"icon": "bell", "name": "Alarms", "path": "/alarms", "desc": "알람 관리"},
    {"icon": "signal", "name": "Communication", "path": "/comm", "desc": "통신 상태"},
]

AI_MENU = [
    {"type": "divider"},
    {"type": "header", "name": "AI 모델"},
    {"icon": "graduation-cap", "name": "Training", "path": "/training-wizard", "desc": "모델 학습"},
    {"icon": "chart-no-axes-column", "name": "Performance", "path": "/model-performance", "desc": "성능 분석"},
    {"icon": "play", "name": "Forecast", "path": "/forecast-player", "desc": "예측 모니터링"},
    {"type": "divider"},
    {"type": "header", "name": "AI 분석"},
    {"icon": "bot", "name": "AI Chat", "path": "/ai", "desc": "AI 인사이트"},
]

MENU_CONFIG = {
    "FULL": BASE_MENU + AI_MENU if ENABLE_AI_FEATURES else BASE_MENU,
    "PART": BASE_MENU,
}

ACTIVE_MENU = MENU_CONFIG.get(APP_VERSION, MENU_CONFIG["FULL"])


def sidebar_menu_item(
    menu: dict,
    active: str
) -> rx.Component:
    """사이드바 메뉴 아이템 - Purple theme"""

    # 구분선
    if menu.get("type") == "divider":
        return rx.divider(margin_top="3", margin_bottom="3")

    # 그룹 헤더
    if menu.get("type") == "header":
        return rx.text(
            menu["name"],
            size="1",
            weight="bold",
            color=rx.color("gray", 10),
            class_name="px-3 py-2 uppercase tracking-wide",
        )

    # 일반 메뉴 아이템
    is_active = active == menu["path"]

    return rx.link(
        rx.hstack(
            rx.icon(
                menu["icon"],
                size=20,
                color=rx.cond(is_active, rx.color("purple", 11), rx.color("gray", 11)),
            ),
            rx.text(
                menu["name"],
                size="2",
                weight=rx.cond(is_active, "bold", "medium"),
                color=rx.cond(is_active, rx.color("purple", 11), rx.color("gray", 11)),
            ),
            spacing="3",
            padding="12px 16px",
            border_radius="8px",
            background=rx.cond(is_active, rx.color("purple", 3), "transparent"),
            _hover={"background": rx.color("gray", 3)},
            width="100%",
            cursor="pointer",
        ),
        href=menu["path"],
        underline="none",
        width="100%",
    )


def sidebar_v2(active: str = "/") -> rx.Component:
    """
    Improved Sidebar - SalesX Purple Theme
    - 240px width
    - White background
    - Purple accent for active items
    - Clean, modern design
    """
    return rx.box(
        rx.vstack(
            # Logo section
            rx.hstack(
                rx.icon("arrow-left", size=20, color=rx.color("gray", 10)),
                rx.heading("KSYS", size="6", weight="bold", color=rx.color("purple", 11)),
                spacing="3",
                padding="16px",
            ),

            # Search bar
            rx.input(
                placeholder="Search",
                size="2",
                width="100%",
            ),

            # Menu items
            rx.vstack(
                *[sidebar_menu_item(menu, active) for menu in ACTIVE_MENU],
                spacing="1",
                width="100%",
                flex="1",
            ),

            # Spacer
            rx.spacer(),

            # Bottom section (Settings, Help)
            rx.vstack(
                rx.divider(),
                sidebar_menu_item(
                    {"icon": "settings", "name": "Settings", "path": "/settings"},
                    active
                ),
                sidebar_menu_item(
                    {"icon": "help-circle", "name": "Help", "path": "/help"},
                    active
                ),
                spacing="2",
                width="100%",
            ),

            spacing="4",
            height="100%",
            width="100%",
        ),
        width="240px",
        height="100vh",
        background="white",
        border_right="1px solid",
        border_color=rx.color("gray", 4),
        padding="24px 16px",
        position="fixed",
        left="0",
        top="0",
        z_index="100",
        overflow_y="auto",
    )


def header_v2(page_title: str = "Dashboard") -> rx.Component:
    """
    Improved Header - SalesX Style
    - 64px height
    - White background
    - Page title on left
    - Actions on right
    """
    return rx.box(
        rx.hstack(
            # Left: Page title
            rx.hstack(
                rx.icon("arrow-left", size=20, color=rx.color("gray", 10)),
                rx.heading(page_title, size="6"),
                spacing="3",
            ),

            # Right: Actions
            rx.hstack(
                rx.button(
                    rx.icon("calendar", size=16),
                    "Sep 18, 2024",
                    variant="soft",
                    size="2",
                ),
                rx.icon_button(
                    rx.icon("mail", size=20),
                    variant="soft",
                    size="2",
                ),
                rx.icon_button(
                    rx.icon("bell", size=20),
                    variant="soft",
                    size="2",
                ),
                rx.avatar(
                    fallback="U",
                    size="2",
                ),
                spacing="3",
            ),

            justify="between",
            align="center",
            width="100%",
        ),
        height="64px",
        padding="16px 32px",
        background="white",
        border_bottom="1px solid",
        border_color=rx.color("gray", 4),
        position="sticky",
        top="0",
        z_index="90",
    )


def shell_v2(
    *children: rx.Component,
    page_title: str = "Dashboard",
    active_route: str = "/",
    on_mount=None
) -> rx.Component:
    """
    Shell layout with sidebar and header - SalesX style
    Args:
        children: Page content
        page_title: Title for header
        active_route: Active menu route
        on_mount: Optional on_mount handler
    """
    return rx.box(
        # Sidebar
        sidebar_v2(active=active_route),

        # Main content area
        rx.box(
            # Header
            header_v2(page_title=page_title),

            # Content
            rx.box(
                *children,
                padding="32px",
                background=rx.color("gray", 2),
                min_height="calc(100vh - 64px)",
            ),

            margin_left="240px",  # Sidebar width
        ),

        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=on_mount,
    )


def responsive_shell(
    *children: rx.Component,
    page_title: str = "Dashboard",
    active_route: str = "/",
    on_mount=None
) -> rx.Component:
    """
    Responsive shell with collapsible sidebar
    Uses BaseState.sidebar_collapsed for toggle
    """
    return rx.box(
        # Collapsible sidebar
        rx.cond(
            B.sidebar_collapsed,
            # Collapsed: Icon-only sidebar (64px)
            rx.box(
                rx.vstack(
                    rx.icon_button(
                        rx.icon("panel-left-open", size=20),
                        on_click=B.toggle_sidebar,
                        variant="ghost",
                        size="2",
                    ),
                    *[
                        rx.link(
                            rx.icon_button(
                                rx.icon(menu["icon"], size=18),
                                variant="ghost",
                                size="2",
                            ),
                            href=menu["path"],
                        )
                        for menu in ACTIVE_MENU
                        if menu.get("type") not in ["divider", "header"]
                    ],
                    spacing="2",
                    align="center",
                ),
                width="64px",
                height="100vh",
                background="white",
                border_right="1px solid",
                border_color=rx.color("gray", 4),
                padding="16px 8px",
                position="fixed",
                left="0",
                top="0",
                z_index="100",
            ),
            # Expanded: Full sidebar
            sidebar_v2(active=active_route),
        ),

        # Main content
        rx.box(
            header_v2(page_title=page_title),
            rx.box(
                *children,
                padding="32px",
                background=rx.color("gray", 2),
                min_height="calc(100vh - 64px)",
            ),
            margin_left=rx.cond(B.sidebar_collapsed, "64px", "240px"),
            transition="margin-left 0.3s ease",
        ),

        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=on_mount,
    )
