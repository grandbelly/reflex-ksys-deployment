"""Unified Dashboard Page - MVC + Real-time Pattern"""
import reflex as rx
from ..views.dashboard_realtime_view import dashboard_realtime_page
from ..states.dashboard_realtime import DashboardRealtimeState
from ..states.scheduler_state import SchedulerState
from ..components.layout import shell


@rx.page(
    route="/",
    title="Dashboard | KSYS",
    on_load=[
        DashboardRealtimeState.start_streaming,
        SchedulerState.start_schedulers  # Start forecasting schedulers
    ]
)
def dashboard() -> rx.Component:
    """Main dashboard with real-time updates using MVC pattern"""
    return shell(
        dashboard_realtime_page(),
        active_route="/"

    )