"""
Enhanced Trend Page with Stock-style Charts
"""
import reflex as rx
from ..states.dashboard import DashboardState as D
from ..components.stock_chart import stock_style_chart, time_range_selector, ticker_info_header


def enhanced_trend_page() -> rx.Component:
    """Enhanced trend page with stock-style visualization"""
    return rx.box(
        # Dark background
        rx.vstack(
            # Header with ticker info
            rx.card(
                ticker_info_header(
                    ticker=D.tag_name,
                    company="Industrial Sensor",
                    price=D.kpi_avg,
                    change=2.5,  # Calculate from data
                    market_cap=None,
                ),
                width="100%",
                style={
                    "backgroundColor": "rgba(30, 30, 30, 0.8)",
                    "backdropFilter": "blur(10px)",
                    "border": "1px solid rgba(255, 255, 255, 0.1)",
                },
            ),
            
            # Time range selector
            rx.card(
                time_range_selector(
                    selected=D.window,
                    on_change=D.set_window,
                ),
                width="100%",
                style={
                    "backgroundColor": "rgba(30, 30, 30, 0.6)",
                    "border": "1px solid rgba(255, 255, 255, 0.05)",
                },
            ),
            
            # Main chart area
            rx.card(
                rx.cond(
                    D.series_for_tag.length() > 0,
                    stock_style_chart(
                        data=D.series_for_tag,
                        height=500,
                    ),
                    rx.center(
                        rx.vstack(
                            rx.icon("line-chart", size=64, color="gray"),
                            rx.text(
                                "No data to display",
                                size="4",
                                color="gray",
                            ),
                            rx.text(
                                "Please select a tag and time range",
                                size="2",
                                color="gray",
                            ),
                            spacing="3",
                        ),
                        height="500px",
                    ),
                ),
                width="100%",
                padding="20px",
                style={
                    "backgroundColor": "rgba(20, 20, 20, 0.9)",
                    "border": "1px solid rgba(255, 255, 255, 0.05)",
                },
            ),
            
            # Additional metrics cards
            rx.hstack(
                # Min/Max card
                rx.card(
                    rx.vstack(
                        rx.text("Range", size="2", color="gray"),
                        rx.hstack(
                            rx.vstack(
                                rx.text("MIN", size="1", color="gray"),
                                rx.text(D.kpi_min_s, size="4", weight="bold", color="#ef4444"),
                                spacing="1",
                            ),
                            rx.divider(orientation="vertical", height="40px"),
                            rx.vstack(
                                rx.text("MAX", size="1", color="gray"),
                                rx.text(D.kpi_max_s, size="4", weight="bold", color="#10b981"),
                                spacing="1",
                            ),
                            spacing="4",
                            align_items="center",
                        ),
                        spacing="2",
                    ),
                    style={
                        "backgroundColor": "rgba(30, 30, 30, 0.6)",
                        "border": "1px solid rgba(255, 255, 255, 0.05)",
                        "flex": "1",
                    },
                ),
                
                # Average card
                rx.card(
                    rx.vstack(
                        rx.text("Average", size="2", color="gray"),
                        rx.text(D.kpi_avg_s, size="5", weight="bold", color="#3b82f6"),
                        spacing="2",
                    ),
                    style={
                        "backgroundColor": "rgba(30, 30, 30, 0.6)",
                        "border": "1px solid rgba(255, 255, 255, 0.05)",
                        "flex": "1",
                    },
                ),
                
                # Data points card
                rx.card(
                    rx.vstack(
                        rx.text("Data Points", size="2", color="gray"),
                        rx.text(D.kpi_count_s, size="5", weight="bold"),
                        spacing="2",
                    ),
                    style={
                        "backgroundColor": "rgba(30, 30, 30, 0.6)",
                        "border": "1px solid rgba(255, 255, 255, 0.05)",
                        "flex": "1",
                    },
                ),
                
                width="100%",
                spacing="3",
            ),
            
            spacing="4",
            padding="20px",
            width="100%",
        ),
        style={
            "backgroundColor": "#0f0f0f",
            "minHeight": "100vh",
        },
    )