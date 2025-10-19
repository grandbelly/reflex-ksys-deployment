"""
Dashboard Realtime State - Fixed Version
- No nested async with self blocks
- Proper background event usage
- yield for UI updates
"""
import reflex as rx
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Any
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from reflex.utils import console

from ksys_app.db_orm import get_async_session
from ksys_app.services.sensor_service import SensorService


class DashboardRealtimeState(rx.State):
    """Optimized dashboard state with controlled polling"""

    # Data
    sensors: List[Dict] = []
    chart_data: Dict[str, List[Dict]] = {}

    # Statistics
    normal_count: int = 0
    warning_count: int = 0
    critical_count: int = 0

    # UI State
    last_update: str = ""
    is_streaming: bool = False
    update_interval: int = 15  # 15 seconds

    # Loading state
    loading: bool = False
    error_message: str = ""

    # Database Session Management
    # =========================================================================

    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        """Get database session with proper cleanup"""
        async with get_async_session() as session:
            try:
                yield session
            except Exception as e:
                console.error(f"Session error: {e}")
                raise

    # =========================================================================
    # STREAMING CONTROL
    # =========================================================================

    @rx.event(background=True)
    async def start_streaming(self):
        """Start streaming - background event with proper state management"""
        # Set initial state
        async with self:
            self.is_streaming = True
            self.last_update = "Initializing..."
            yield  # Update UI

        console.info(f"Dashboard streaming started (interval: {self.update_interval}s)")

        # Initial load
        try:
            await asyncio.wait_for(
                self._fetch_data(),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            console.warning("Initial data load timeout")
            async with self:
                self.last_update = "Initial load timeout"
                yield
        except Exception as e:
            console.error(f"Initial load error: {e}")
            async with self:
                self.last_update = f"Error: {str(e)[:50]}"
                yield

        # Streaming loop
        while self.is_streaming:
            await asyncio.sleep(self.update_interval)

            try:
                # Use timeout to prevent long-running queries
                await asyncio.wait_for(
                    self._fetch_data(),
                    timeout=self.update_interval - 2  # Leave 2s buffer
                )
            except asyncio.TimeoutError:
                console.warn(f"Dashboard refresh timeout after {self.update_interval}s")
                async with self:
                    self.last_update = f"Timeout at {datetime.now(ZoneInfo('Asia/Seoul')).strftime('%H:%M:%S')}"
                    yield
            except Exception as e:
                console.error(f"Streaming error: {e}")
                async with self:
                    self.last_update = f"Error: {str(e)[:50]}"
                    yield

    async def stop_streaming(self):
        """Stop streaming"""
        async with self:
            self.is_streaming = False

        console.info("Dashboard streaming stopped")

    # =========================================================================
    # DATA FETCHING
    # =========================================================================

    async def _fetch_data(self):
        """Internal data fetch - updates state with async with self"""
        try:
            # Fetch data using service layer
            async with self.get_session() as session:
                service = SensorService(session)

                # Get sensor data WITH chart points (new method)
                db_sensors = await service.get_realtime_alarms_with_charts()

                if not db_sensors:
                    console.warning("No sensor data received")
                    return

                # Process sensors
                sensor_list = []
                for sensor in db_sensors:
                    min_val = 0
                    max_val = 100
                    gauge_percent = 50

                    if 'qc_rule' in sensor and sensor['qc_rule']:
                        min_val = sensor['qc_rule'].get('min_val', 0)
                        max_val = sensor['qc_rule'].get('max_val', 100)
                        value = sensor.get('value', 0)
                        if max_val > min_val:
                            gauge_percent = ((value - min_val) / (max_val - min_val)) * 100
                            gauge_percent = min(100, max(0, gauge_percent))

                    sensor_list.append({
                        "tag_name": sensor['tag_name'],
                        "value": sensor.get('value', 0),
                        "timestamp": sensor.get('timestamp', datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")),
                        "status": sensor.get('status', 0),
                        "gauge_percent": gauge_percent,
                        "min_val": min_val,
                        "max_val": max_val,
                        "chart_points": sensor.get('chart_points', []),  # Mini chart data
                        "chart_color": sensor.get('chart_color', '#10b981')  # Chart color
                    })

                # Get chart data for aggregate charts (separate from mini charts)
                tag_names = [s['tag_name'] for s in sensor_list]
                chart_data = await service.get_aggregated_chart_data(tag_names)

                # Calculate statistics
                stats = {
                    'normal': sum(1 for s in sensor_list if s['status'] == 0),
                    'warning': sum(1 for s in sensor_list if s['status'] == 1),
                    'critical': sum(1 for s in sensor_list if s['status'] == 2)
                }

            # Update state
            async with self:
                self.sensors = sensor_list
                self.chart_data = chart_data
                self.normal_count = stats['normal']
                self.warning_count = stats['warning']
                self.critical_count = stats['critical']
                self.last_update = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")

            console.debug(f"Dashboard updated: {len(sensor_list)} sensors")

        except Exception as e:
            console.error(f"Refresh data failed: {e}")
            async with self:
                self.error_message = str(e)

    @rx.event(background=True)
    async def refresh_data(self):
        """Refresh sensor data (manual refresh)"""
        await self._fetch_data()

    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================

    @rx.var
    def total_sensors(self) -> int:
        """Total number of sensors"""
        return len(self.sensors)

    @rx.var
    def system_status(self) -> str:
        """Overall system status"""
        if self.critical_count > 0:
            return "critical"
        elif self.warning_count > 0:
            return "warning"
        else:
            return "normal"

    @rx.var
    def status_color(self) -> str:
        """Status color for UI"""
        status_colors = {
            "normal": "green",
            "warning": "yellow",
            "critical": "red"
        }
        return status_colors.get(self.system_status, "gray")

    @rx.var
    def is_loading(self) -> bool:
        """Is data loading"""
        return self.loading or not self.sensors

    @rx.var
    def formatted_sensors(self) -> List[Dict]:
        """UI용 포맷된 센서 데이터"""
        formatted = []
        for sensor in self.sensors:
            # Get chart points for this sensor
            chart_points = self.chart_data.get(sensor['tag_name'], [])

            # Determine chart color based on status
            chart_color = ["green", "amber", "red"][sensor["status"]]

            formatted.append({
                **sensor,
                "value_str": f"{sensor['value']:.1f}",
                "status_color": ["green", "yellow", "red"][sensor["status"]],
                "chart_points": chart_points,
                "chart_color": chart_color
            })
        return formatted
