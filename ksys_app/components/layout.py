import reflex as rx
import os

# Import BaseState for sidebar toggle functionality (shared across all pages)
from ..states.base_state import BaseState as B

# AI 기능 활성화 여부 (ENABLE_AI_FEATURES 또는 APP_VERSION으로 제어)
ENABLE_AI_FEATURES = os.getenv('ENABLE_AI_FEATURES', 'true').lower() == 'true'
APP_VERSION = os.getenv("APP_VERSION", "FULL").upper()

# APP_VERSION이 PART면 AI 기능 비활성화
if APP_VERSION == "PART":
    ENABLE_AI_FEATURES = False

# 기본 메뉴
BASE_MENU = [
    {"type": "header", "name": "미니 SCADA"},
    {"icon": "layout-dashboard", "name": "대시보드", "path": "/", "desc": "실시간 모니터링"},
    {"icon": "trending-up", "name": "트렌드", "path": "/trend", "desc": "시계열 분석"},
    {"icon": "bell", "name": "알람", "path": "/alarms", "desc": "룰베이스 알람"},
    {"icon": "signal", "name": "통신 상태", "path": "/comm", "desc": "통신 성공률"},
]

# AI 메뉴 그룹 (학습 → 분석 워크플로우)
AI_MENU = [
    {"type": "divider"},
    {"type": "header", "name": "AI 예측 모델"},
    {"icon": "graduation-cap", "name": "모델 훈련", "path": "/training-wizard", "desc": "AI 모델 학습"},
    {"icon": "chart-no-axes-column", "name": "성능 비교", "path": "/model-performance", "desc": "모델 성능 분석"},
    {"icon": "play", "name": "예측 플레이어", "path": "/forecast-player-fixed", "desc": "실시간 예측 모니터링"},
    {"type": "divider"},
    {"type": "header", "name": "AI 분석"},
    {"icon": "bot", "name": "AI 인사이트", "path": "/ai", "desc": "대화형 AI 분석"},
    {"icon": "git-compare", "name": "알람 비교", "path": "/scada-alarm-comparison", "desc": "룰 vs AI 비교"},
]

# 버전별 메뉴 구성 정의
MENU_CONFIG = {
    "FULL": BASE_MENU + AI_MENU if ENABLE_AI_FEATURES else BASE_MENU,
    "PART": BASE_MENU,  # PART 버전은 항상 AI 제외
}

# 현재 버전의 메뉴 가져오기
ACTIVE_MENU = MENU_CONFIG.get(APP_VERSION, MENU_CONFIG["FULL"])


def render_menu_item(menu: dict, active: str) -> rx.Component:
    """메뉴 아이템 렌더링 (구분선, 헤더, 일반 메뉴) - 최적화된 클릭 이벤트"""
    # 구분선
    if menu.get("type") == "divider":
        return rx.divider(margin_top="3", margin_bottom="3")

    # 그룹 헤더
    if menu.get("type") == "header":
        return rx.text(
            menu["name"],
            size="1",
            weight="bold",
            color="#6b7280",
            class_name="px-3 py-2 uppercase tracking-wide",
        )

    # 일반 메뉴 아이템 - href만 사용하고 중첩 없이 깔끔하게 구성
    is_active = active == menu["path"]

    return rx.link(
        rx.flex(
            rx.icon(
                menu["icon"],
                size=20,
                color="#3b82f6" if is_active else "#6b7280",  # blue-500 or gray-500
            ),
            rx.text(
                menu["name"],
                size="3",
                weight="bold" if is_active else "medium",
                color="#3b82f6" if is_active else "#111827",  # blue-500 or gray-900
            ),
            align="center",
            gap="3",
        ),
        href=menu["path"],
        underline="none",
        width="100%",
        padding="0.75rem",
        border_radius="0.5rem",
        border_left=f"4px solid {'#3b82f6' if is_active else 'transparent'}",
        background="#eff6ff" if is_active else "transparent",  # blue-50 when active
        _hover={
            "background": "#f3f4f6" if not is_active else "#eff6ff",  # gray-100 or blue-50
            "transform": "translateX(2px)",
        },
        transition="all 0.2s ease",
        style={"text_decoration": "none"}
    )


def collapsed_sidebar() -> rx.Component:
    """접힌 사이드바 (아이콘만 표시) - Light Mode Only, 최적화된 클릭"""
    # 구분선과 헤더 제외한 실제 메뉴만 필터링
    menu_items = [m for m in ACTIVE_MENU if m.get("type") not in ["divider", "header"]]

    return rx.box(
        # 토글 버튼 (펼치기)
        rx.flex(
            rx.button(
                rx.icon("panel-left-open", size=20, color="#6b7280"),
                variant="ghost",
                size="2",
                on_click=B.toggle_sidebar,
                _hover={"background": "#f3f4f6"},
                style={"cursor": "pointer"}
            ),
            direction="column",
            align="center",
            gap="4",
            padding_bottom="1rem",
            border_bottom="1px solid #e5e7eb",
        ),
        # 축소된 네비게이션 아이콘들 - 버튼 없이 직접 링크로
        rx.vstack(
            *[
                rx.link(
                    rx.flex(
                        rx.icon(menu["icon"], size=18, color="#6b7280"),
                        justify="center",
                        align="center",
                        width="100%",
                        height="2.5rem",
                        border_radius="0.5rem",
                        _hover={
                            "background": "#f3f4f6",
                            "transform": "scale(1.1)",
                        },
                        transition="all 0.2s ease"
                    ),
                    href=menu["path"],
                    underline="none",
                    style={"text_decoration": "none"}
                )
                for menu in menu_items
            ],
            spacing="2",
            align="stretch",
            padding_top="1rem",
        ),
        height="100vh",
        width="64px",
        flex_shrink="0",
        padding="1rem 0.5rem",
        border_right="1px solid #e5e7eb",
        background="white",
        box_shadow="0 1px 3px 0 rgba(0, 0, 0, 0.1)",
        position="sticky",
        top="0",
        class_name="hidden lg:flex flex-col",
    )


def sidebar(active: str = "/") -> rx.Component:
    """사이드바 - Light Mode Only, 흰색 배경, 최적화된 디자인"""
    return rx.box(
        # 상단 로고 섹션
        rx.flex(
            rx.flex(
                rx.button(
                    rx.icon("panel-left-close", size=20, color="#6b7280"),
                    variant="ghost",
                    size="2",
                    on_click=B.toggle_sidebar,
                    _hover={"background": "#f3f4f6"},
                    style={"cursor": "pointer"}
                ),
                # KSYS CI 로고 이미지
                rx.image(
                    src="/logo.png",
                    alt="KSYS Logo",
                    height="40px",
                    width="auto"
                ),
                align="center",
                gap="3",
                width="100%",
                justify="center",
            ),
            direction="column",
            align="center",
            gap="3",
            padding_bottom="1rem",
            border_bottom="1px solid #e5e7eb",
            width="100%",
        ),

        # 네비게이션 메뉴 (구분선, 헤더, 메뉴 아이템 포함)
        rx.vstack(
            *[render_menu_item(menu, active) for menu in ACTIVE_MENU],
            spacing="2",
            align="stretch",
            padding_top="1.5rem",
            flex="1",
        ),

        # Spacer
        rx.spacer(),

        height="100vh",
        width="240px",
        flex_shrink="0",
        padding="1.5rem",
        border_right="1px solid #e5e7eb",
        background="white",
        box_shadow="0 1px 3px 0 rgba(0, 0, 0, 0.1)",
        position="sticky",
        top="0",
        overflow_y="auto",
        class_name="hidden lg:flex flex-col",
    )


def top_nav_cards(active: str = "/") -> rx.Component:
    """최상단 헤더의 네비게이션 카드들 (동적 메뉴)"""
    # 구분선과 헤더 제외한 실제 메뉴만 필터링
    menu_items = [m for m in ACTIVE_MENU if m.get("type") not in ["divider", "header"]]

    return rx.flex(
        *[
            rx.link(
                rx.card(
                    rx.flex(
                        rx.icon(
                            menu["icon"],
                            size=22 if active == menu["path"] else 18,
                            color="black"
                        ),
                        rx.vstack(
                            rx.text(
                                menu["name"],
                                size="4" if active == menu["path"] else "2",
                                weight="bold" if active == menu["path"] else "medium",
                                color="black"
                            ),
                            rx.text(
                                menu["desc"],
                                size="1",
                                color="black"
                            ),
                            spacing="0",
                            align="start"
                        ),
                        align="center",
                        gap="2"
                    ),
                    class_name="bg-white hover:bg-blue-50 hover:border-blue-400 border border-blue-200 transition-all duration-200 hover:shadow-md",
                    padding="3",
                    style={"min_width": "140px", "cursor": "pointer"}
                ),
                href=menu["path"],
                underline="none"
            )
            for menu in menu_items
        ],
        gap="3",
        align="center"
    )


def header(active_route: str = "/") -> rx.Component:
    """상단 헤더 - KSYS 로고만 표시 (공통 디자인 가이드)"""
    return rx.el.header(
        rx.flex(
            # 왼쪽: KSYS 로고
            rx.box(
                rx.text("KSYS", weight="bold", size="5", color="white"),
                bg="#3b82f6",  # blue-500
                padding="0.5rem 1rem",
                border_radius="8px"
            ),
            rx.spacer(),
            # 오른쪽: 사용자 아이콘 등 추가 가능 (현재는 비움)
            align="center",
            width="100%"
        ),
        class_name="w-full border-b border-gray-200 bg-white px-6 py-3 sticky top-0 z-10 shadow-sm",
    )


def stat_card(title: str, value: rx.Var | str, delta: str | None = None, good: bool | None = None, subtitle: str | None = None) -> rx.Component:
    badge = None
    if delta is not None and good is not None:
        badge = rx.el.span(
            delta,
            class_name=(
                "ml-2 text-xs px-1.5 py-0.5 rounded-md "
                + ("bg-green-900 text-green-400" if good else "bg-red-900 text-red-400")
            ),
        )
    return rx.el.div(
        rx.el.span(title, class_name="text-xs font-medium text-slate-400"),
        rx.el.div(
            rx.el.span(value, class_name="text-2xl font-semibold text-white"),
            badge or rx.fragment(),
            class_name="flex items-center mt-1",
        ),
        rx.el.span(subtitle or "", class_name="text-xs text-slate-500 mt-1"),
        class_name="bg-slate-800 border border-slate-700 rounded-xl shadow-sm p-5"
    )


def shell(*children: rx.Component, on_mount=None, active_route: str = "/") -> rx.Component:
    return rx.el.div(
        # 조건부 사이드바 표시
        rx.cond(
            B.sidebar_collapsed,
            collapsed_sidebar(),
            sidebar(active_route)
        ),
        rx.el.div(
            # 상단 헤더 제거 - 사이드바만 사용
            rx.el.div(
                *children,
                class_name="w-full min-h-screen",
            ),
            class_name="flex-1 min-h-screen bg-white",
        ),
        class_name="w-full min-h-screen bg-white flex",
        on_mount=on_mount,
    )
