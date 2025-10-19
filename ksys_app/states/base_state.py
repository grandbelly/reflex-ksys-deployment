"""
Base State Layer
- Provides common state management patterns
- All states inherit from this
"""
import reflex as rx
import asyncio
from typing import Optional
from reflex.utils import console


class BaseState(rx.State):
    """Base state with common utilities"""

    # Polling control
    _polling_active: bool = False
    _polling_interval: int = 10
    _polling_task: Optional[asyncio.Task] = None

    # Loading state
    loading: bool = False
    error_message: str = ""

    # Sidebar state - shared across all pages
    sidebar_collapsed: bool = False

    # Theme state - shared across all pages
    theme_mode: str = "dark"  # "dark" or "light"

    @rx.event
    def toggle_sidebar(self):
        """Toggle sidebar collapse state"""
        self.sidebar_collapsed = not self.sidebar_collapsed

    @rx.event
    def toggle_theme(self):
        """Toggle between dark and light theme"""
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"

    @rx.event(background=True)
    async def start_polling(self, interval: Optional[int] = None):
        """
        Start polling loop

        Args:
            interval: Polling interval in seconds (default: 10)

        Subclass must implement refresh_data() method
        """
        if interval:
            async with self:
                self._polling_interval = interval

        async with self:
            self._polling_active = True

        console.info(f"{self.__class__.__name__} polling started (interval: {self._polling_interval}s)")

        while self._polling_active:
            try:
                # Use timeout to prevent long-running queries
                await asyncio.wait_for(
                    self.refresh_data(),
                    timeout=self._polling_interval - 1
                )
            except asyncio.TimeoutError:
                console.log(f"{self.__class__.__name__} refresh timeout")
            except Exception as e:
                console.error(f"{self.__class__.__name__} polling error: {e}")

            # Wait for next interval
            await asyncio.sleep(self._polling_interval)

    async def stop_polling(self):
        """Stop polling loop"""
        async with self:
            self._polling_active = False

        console.info(f"{self.__class__.__name__} polling stopped")

    @rx.event(background=True)
    async def refresh_data(self):
        """
        Refresh data - must be implemented by subclass

        Example:
            @rx.event(background=True)
            async def refresh_data(self):
                from ksys_app.db_orm import get_async_session

                async with get_async_session() as session:
                    service = MyService(session)
                    data = await service.get_data()

                async with self:
                    self.data = data
                    yield
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement refresh_data()")

    def __repr__(self):
        return f"<{self.__class__.__name__}(loading={self.loading}, error={bool(self.error_message)})>"