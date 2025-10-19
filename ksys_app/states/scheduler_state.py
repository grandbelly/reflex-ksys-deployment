"""
Scheduler State - Manages forecasting schedulers lifecycle within Reflex app.

This state automatically starts all schedulers when the app initializes.
No separate process needed - schedulers run as background tasks within Reflex.
"""

import reflex as rx
from reflex.utils import console
from ..schedulers import start_all_schedulers, stop_all_schedulers


class SchedulerState(rx.State):
    """State to manage forecasting schedulers within Reflex app"""

    schedulers_running: bool = False
    scheduler_error: str = ""

    @rx.event(background=True)
    async def start_schedulers(self):
        """Start all forecasting schedulers in background"""
        try:
            console.log("=" * 80)
            console.log("🚀 Starting Forecasting Schedulers from State...")
            console.log("=" * 80)

            async with self:
                self.schedulers_running = True
                self.scheduler_error = ""

            # Start all schedulers (this runs indefinitely)
            await start_all_schedulers()

        except Exception as e:
            console.error(f"❌ Scheduler error in State: {e}")
            async with self:
                self.schedulers_running = False
                self.scheduler_error = str(e)

    async def stop_schedulers(self):
        """Stop all schedulers gracefully"""
        try:
            console.log("🛑 Stopping schedulers...")
            await stop_all_schedulers()

            self.schedulers_running = False
            self.scheduler_error = ""
            console.log("✅ Schedulers stopped")

        except Exception as e:
            console.error(f"❌ Error stopping schedulers: {e}")
            self.scheduler_error = str(e)
