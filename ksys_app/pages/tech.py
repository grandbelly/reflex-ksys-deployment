"""
Tech page temporarily disabled
"""
import reflex as rx

def tech_page():
    """Tech 페이지 임시 비활성화"""
    return rx.center(
        rx.vstack(
            rx.heading("Tech 페이지 점검 중", size="5"),
            rx.text("MVP 대시보드를 테스트 중입니다", size="3"),
            rx.link("MVP 대시보드로 이동", href="/dashboard-mvp", color="blue"),
            spacing="4"
        ),
        height="100vh"
    )