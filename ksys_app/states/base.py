"""Base state for common functionality across all states."""
import reflex as rx
import asyncio
from typing import Any, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from ..db import get_pool, q, execute_query


class BaseState(rx.State):
    """Base state with common functionality for all states."""

    # Common state variables
    is_loading: bool = False
    error: str = ""
    last_update: str = ""
    auto_refresh_enabled: bool = False
    refresh_interval: int = 30  # seconds

    # Sidebar state - shared across all pages
    sidebar_collapsed: bool = False

    # Theme state - shared across all pages
    theme_mode: str = "dark"  # "dark" or "light"

    # Private state for managing refresh
    _refresh_task_running: bool = False

    @rx.event
    def toggle_sidebar(self):
        """Toggle sidebar collapse state"""
        self.sidebar_collapsed = not self.sidebar_collapsed

    @rx.event
    def toggle_theme(self):
        """Toggle between dark and light theme"""
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"

    async def query(self, sql: str, params: tuple = ()):
        """Execute a query using the singleton pool."""
        try:
            return await q(sql, params)
        except Exception as e:
            self.error = str(e)
            raise

    async def execute(self, sql: str, params: tuple = ()):
        """Execute a command using the singleton pool."""
        try:
            return await execute_query(sql, params)
        except Exception as e:
            self.error = str(e)
            raise

    def update_last_update(self, timestamp: Optional[datetime] = None):
        """Update last update time using DB timestamp or current time."""
        if timestamp:
            kst_time = timestamp.astimezone(ZoneInfo("Asia/Seoul"))
            self.last_update = kst_time.strftime("%H:%M:%S")
        else:
            # Fallback to current time if no DB timestamp
            kst_now = datetime.now(ZoneInfo("Asia/Seoul"))
            self.last_update = kst_now.strftime("%H:%M:%S")

    def clear_error(self):
        """Clear error message."""
        self.error = ""

    @rx.event(background=True)
    async def start_auto_refresh(self):
        """Common auto-refresh pattern for all states."""
        async with self:
            if self._refresh_task_running:
                return  # Already running
            self._refresh_task_running = True
            self.auto_refresh_enabled = True

        while True:
            async with self:
                if not self.auto_refresh_enabled:
                    self._refresh_task_running = False
                    break

            # Call the child class's refresh method
            if hasattr(self, 'refresh_data'):
                await self.refresh_data()

            # Yield to update UI
            yield

            # Check if still enabled
            if not self.auto_refresh_enabled:
                async with self:
                    self._refresh_task_running = False
                break

            # Wait for refresh interval
            await asyncio.sleep(self.refresh_interval)

    @rx.event
    def stop_auto_refresh(self):
        """Stop auto-refresh."""
        self.auto_refresh_enabled = False

    @rx.event
    def toggle_auto_refresh(self):
        """Toggle auto-refresh on/off."""
        if self.auto_refresh_enabled:
            self.stop_auto_refresh()
        else:
            return BaseState.start_auto_refresh

    @rx.event
    def set_refresh_interval(self, interval: int):
        """Set refresh interval in seconds."""
        self.refresh_interval = max(5, min(300, interval))  # 5s to 5min
