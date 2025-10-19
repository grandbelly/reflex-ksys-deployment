"""
Stock-style chart component inspired by Reflex trend example
"""
import reflex as rx
from typing import List, Dict, Any


def stock_style_chart(data: List[Dict[str, Any]], height: int = 400) -> rx.Component:
    """주식 스타일 차트 컴포넌트"""
    return rx.recharts.area_chart(
        rx.recharts.area(
            data_key="value",
            stroke="#10b981",  # Emerald green
            fill="url(#colorGradient)",
            stroke_width=2,
            dot=False,
            animation_duration=300,
        ),
        rx.recharts.defs(
            rx.recharts.linear_gradient(
                rx.recharts.stop(offset="0%", stop_color="#10b981", stop_opacity=0.8),
                rx.recharts.stop(offset="95%", stop_color="#10b981", stop_opacity=0.1),
                id="colorGradient",
                x1="0", y1="0", x2="0", y2="1",
            ),
        ),
        rx.recharts.x_axis(
            data_key="time",
            stroke="#4a5568",
            tick={"fill": "#718096", "fontSize": 11},
            axis_line={"stroke": "#2d3748"},
        ),
        rx.recharts.y_axis(
            stroke="#4a5568",
            tick={"fill": "#718096", "fontSize": 11},
            axis_line={"stroke": "#2d3748"},
            domain=["dataMin - 5", "dataMax + 5"],
            tick_count=5,
        ),
        rx.recharts.cartesian_grid(
            stroke_dasharray="3 3",
            stroke="#2d3748",
            opacity=0.3,
            horizontal=True,
            vertical=False,
        ),
        rx.recharts.tooltip(
            content_style={
                "backgroundColor": "#1a202c",
                "border": "1px solid #2d3748",
                "borderRadius": "8px",
                "padding": "8px",
            },
            label_style={"color": "#a0aec0", "fontSize": "12px"},
            item_style={"color": "#10b981", "fontSize": "14px", "fontWeight": "bold"},
        ),
        data=data,
        height=height,
        margin={"top": 20, "right": 30, "bottom": 40, "left": 60},
    )


def time_range_selector(selected: str, on_change) -> rx.Component:
    """시간 범위 선택 버튼 그룹"""
    ranges = [
        {"label": "1D", "value": "1 day"},
        {"label": "5D", "value": "5 days"},
        {"label": "1M", "value": "30 days"},
        {"label": "6M", "value": "180 days"},
        {"label": "1Y", "value": "1 year"},
        {"label": "5Y", "value": "5 years"},
        {"label": "MAX", "value": "max"},
    ]
    
    return rx.hstack(
        *[
            rx.button(
                r["label"],
                size="2",
                variant="ghost" if selected != r["value"] else "solid",
                color_scheme="teal" if selected == r["value"] else "gray",
                on_click=lambda v=r["value"]: on_change(v),
                width="60px",
            )
            for r in ranges
        ],
        spacing="2",
    )


def ticker_info_header(
    ticker: str,
    company: str,
    price: float,
    change: float,
    market_cap: str = None
) -> rx.Component:
    """주식 정보 헤더"""
    change_color = "green" if change >= 0 else "red"
    change_icon = "trending-up" if change >= 0 else "trending-down"
    
    return rx.vstack(
        rx.hstack(
            # 티커 심볼
            rx.heading(ticker, size="8", weight="bold"),
            # 회사명
            rx.badge(
                company,
                variant="surface",
                size="2",
                radius="full",
            ),
            rx.spacer(),
            # 현재 가격
            rx.hstack(
                rx.icon(change_icon, color=change_color, size=24),
                rx.text(
                    f"{price:.2f}",
                    size="7",
                    weight="bold",
                    color=change_color,
                ),
                rx.text("USD", size="3", color="gray"),
                spacing="2",
            ),
        ),
        # 추가 정보
        rx.hstack(
            rx.text(f"Market Cap: {market_cap}", size="2", color="gray") if market_cap else rx.fragment(),
            rx.text(f"Change: {change:+.2f}%", size="2", color=change_color),
            rx.text("At Regular Market Close", size="2", color="gray"),
            spacing="4",
        ),
        spacing="3",
        width="100%",
    )