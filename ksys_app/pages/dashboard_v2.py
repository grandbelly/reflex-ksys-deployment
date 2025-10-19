"""
SalesX-style Dashboard Page
Complete implementation using the design system
"""
import reflex as rx
from typing import List, Dict
from ..components.layout_v2 import shell_v2, responsive_shell
from ..components.design_system import (
    metric_card,
    metrics_row,
    content_card,
    two_column_layout,
    primary_button,
    secondary_button,
    icon_button,
    traffic_bar,
    stat_box,
    status_badge,
    line_chart,
    bar_chart,
)


class DashboardV2State(rx.State):
    """State for Dashboard V2"""

    # Metrics
    total_revenue: float = 2189.00
    revenue_change: float = 7.52
    revenue_amount: float = 3256

    total_visitors: int = 611
    visitors_change: float = 6.20
    visitors_amount: int = 27

    total_transitions: float = 3250
    transitions_change: float = 3.56
    transitions_amount: float = 365

    total_products: int = 980
    products_change: float = 3.72
    products_amount: int = 70

    # Chart data
    sales_data: List[Dict] = [
        {"month": "Jan", "value": 22000},
        {"month": "Feb", "value": 24000},
        {"month": "Mar", "value": 25000},
        {"month": "Apr", "value": 26000},
        {"month": "May", "value": 28000},
        {"month": "Jun", "value": 27000},
    ]

    # Traffic data
    traffic_sources: List[Dict] = [
        {"source": "Google", "percentage": 55, "color": "purple"},
        {"source": "Shopify", "percentage": 30, "color": "orange"},
        {"source": "Facebook", "percentage": 15, "color": "blue"},
    ]

    # Product data
    products: List[Dict] = [
        {
            "name": "Leather Flat Sandals",
            "price": 220.20,
            "status": "In Stock",
            "sold": 206,
            "total": 5361.20,
        },
        {
            "name": "Modern T Shirt",
            "price": 50.00,
            "status": "Out Of Stock",
            "sold": 103,
            "total": 4235.20,
        },
        {
            "name": "Designer Jeans",
            "price": 180.00,
            "status": "In Stock",
            "sold": 95,
            "total": 3420.00,
        },
        {
            "name": "Sport Shoes",
            "price": 120.00,
            "status": "In Stock",
            "sold": 150,
            "total": 4500.00,
        },
    ]

    # Product sales stats
    packed: int = 756
    packed_change: float = 5.7

    delivered: int = 1052
    delivered_change: float = 7.3

    shipped: int = 1564
    shipped_change: float = 11.7


def dashboard_metrics() -> rx.Component:
    """Top metrics row - 4 cards"""
    return metrics_row(
        metric_card(
            icon="trending-up",
            label="Total Revenue",
            value=f"${DashboardV2State.total_revenue:,.2f}",
            change_percent=DashboardV2State.revenue_change,
            change_amount=f"${DashboardV2State.revenue_amount:,.0f}",
            is_positive=True,
            icon_color="purple",
        ),
        metric_card(
            icon="eye",
            label="Total Visitors",
            value=str(DashboardV2State.total_visitors),
            change_percent=DashboardV2State.visitors_change,
            change_amount=DashboardV2State.visitors_amount,
            is_positive=True,
            icon_color="orange",
        ),
        metric_card(
            icon="repeat",
            label="Total Transactions",
            value=f"${DashboardV2State.total_transitions:,.0f}",
            change_percent=DashboardV2State.transitions_change,
            change_amount=f"${DashboardV2State.transitions_amount:,.0f}",
            is_positive=True,
            icon_color="blue",
        ),
        metric_card(
            icon="package",
            label="Total Products",
            value=str(DashboardV2State.total_products),
            change_percent=DashboardV2State.products_change,
            change_amount=DashboardV2State.products_amount,
            is_positive=True,
            icon_color="green",
        ),
    )


def sales_analytics_card() -> rx.Component:
    """Sales analytics chart card"""
    actions = rx.hstack(
        secondary_button(
            "Valuation data as of Sep 18, 2024",
            icon="calendar",
            size="1",
        ),
        spacing="2",
    )

    return content_card(
        "Sales Analytics",
        line_chart(
            data=DashboardV2State.sales_data,
            data_key="value",
            x_axis_key="month",
            height=400,
            color="purple",
        ),
        actions=actions,
    )


def traffic_card() -> rx.Component:
    """Traffic sources card with tabs"""
    return content_card(
        "Traffic",
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Week", value="week"),
                rx.tabs.trigger("Month", value="month"),
            ),
            rx.tabs.content(
                rx.vstack(
                    *[
                        traffic_bar(
                            traffic["source"],
                            traffic["percentage"],
                            traffic["color"]
                        )
                        for traffic in DashboardV2State.traffic_sources
                    ],
                    spacing="3",
                    width="100%",
                ),
                value="week",
            ),
            rx.tabs.content(
                rx.text("Monthly traffic data", size="2", color=rx.color("gray", 10)),
                value="month",
            ),
            default_value="week",
        ),
    )


def product_table_card() -> rx.Component:
    """Top selling products table"""
    actions = rx.hstack(
        icon_button("arrow-up-down"),
        icon_button("download"),
        spacing="2",
    )

    return content_card(
        "Top Selling",
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Product Info"),
                    rx.table.column_header_cell("Price"),
                    rx.table.column_header_cell("Status"),
                    rx.table.column_header_cell("Sold"),
                    rx.table.column_header_cell("Total Earning"),
                ),
            ),
            rx.table.body(
                *[
                    rx.table.row(
                        rx.table.cell(
                            rx.hstack(
                                rx.avatar(fallback=product["name"][0], size="3"),
                                rx.text(product["name"]),
                                spacing="2",
                            ),
                        ),
                        rx.table.cell(f"${product['price']:.2f}"),
                        rx.table.cell(
                            status_badge(
                                product["status"],
                                status="in_stock" if product["status"] == "In Stock" else "out_of_stock",
                            ),
                        ),
                        rx.table.cell(f"{product['sold']} Pcs"),
                        rx.table.cell(
                            rx.text(f"${product['total']:.2f}", weight="medium")
                        ),
                    )
                    for product in DashboardV2State.products
                ],
            ),
            variant="surface",
            size="3",
            width="100%",
        ),
        actions=actions,
    )


def product_sales_summary() -> rx.Component:
    """Product sales summary sidebar"""
    return content_card(
        "Product Sales",
        # Stats
        rx.hstack(
            stat_box(
                "Packed",
                DashboardV2State.packed,
                DashboardV2State.packed_change,
                "purple"
            ),
            stat_box(
                "Delivered",
                DashboardV2State.delivered,
                DashboardV2State.delivered_change,
                "orange"
            ),
            stat_box(
                "Shipped",
                DashboardV2State.shipped,
                DashboardV2State.shipped_change,
                "blue"
            ),
            spacing="4",
            width="100%",
        ),

        # Chart
        bar_chart(
            data=[
                {"name": "Packed", "value": DashboardV2State.packed},
                {"name": "Delivered", "value": DashboardV2State.delivered},
                {"name": "Shipped", "value": DashboardV2State.shipped},
            ],
            data_key="value",
            x_axis_key="name",
            height=200,
            color="purple",
        ),

        actions=rx.select(
            ["Last Month", "Last Quarter", "Last Year"],
            default_value="Last Month",
            size="1",
        ),
    )


@rx.page(route="/dashboard-v2", title="Dashboard V2")
def dashboard_v2() -> rx.Component:
    """Main dashboard page with SalesX design"""
    return shell_v2(
        # Top metrics
        dashboard_metrics(),

        # Sales analytics + Traffic
        two_column_layout(
            sales_analytics_card(),
            traffic_card(),
        ),

        # Product table + Sales summary
        two_column_layout(
            product_table_card(),
            product_sales_summary(),
        ),

        page_title="Dashboard",
        active_route="/dashboard-v2",
    )


@rx.page(route="/dashboard-responsive", title="Dashboard (Responsive)")
def dashboard_responsive() -> rx.Component:
    """Responsive dashboard with collapsible sidebar"""
    return responsive_shell(
        # Top metrics
        dashboard_metrics(),

        # Sales analytics + Traffic
        two_column_layout(
            sales_analytics_card(),
            traffic_card(),
        ),

        # Product table + Sales summary
        two_column_layout(
            product_table_card(),
            product_sales_summary(),
        ),

        page_title="Dashboard",
        active_route="/dashboard-responsive",
    )
