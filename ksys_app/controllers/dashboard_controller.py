"""Dashboard Controller - Clean state management"""
import reflex as rx
from typing import List, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo
from reflex.utils import console
import asyncio

from ..models.dashboard import DashboardModel, SensorData


class DashboardController(rx.State):
    """대시보드 컨트롤러 - MVC의 C"""

    # View에서 사용할 데이터
    sensor_tiles: List[Dict[str, Any]] = []
    sensor_stats: Dict[str, int] = {"normal": 0, "warning": 0, "critical": 0}

    # UI 상태
    is_loading: bool = False
    has_error: bool = False
    error_message: str = ""
    last_update: str = "Not updated"
    auto_refresh: bool = False

    # Private
    _refresh_task: Any = None

    async def on_load(self):
        """페이지 로드 시 초기화"""
        console.info("Dashboard loading...")
        await self.fetch_dashboard_data()

    async def fetch_dashboard_data(self):
        """대시보드 데이터 가져오기 - Model 사용"""
        self.is_loading = True
        self.has_error = False

        try:
            # Model에서 데이터 가져오기
            sensors = await DashboardModel.get_latest_sensor_data()
            tag_names = [s.tag_name for s in sensors]
            chart_data = await DashboardModel.get_chart_data(tag_names)
            stats = await DashboardModel.get_sensor_stats()

            # View용 데이터로 변환
            tiles = []
            for sensor in sensors:
                tiles.append(self._format_sensor_tile(sensor, chart_data.get(sensor.tag_name, [])))

            # State 업데이트
            self.sensor_tiles = tiles
            self.sensor_stats = stats
            self.last_update = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%H:%M:%S")

            console.info(f"Dashboard updated: {len(tiles)} sensors")

        except Exception as e:
            console.error(f"Dashboard fetch failed: {e}")
            self.has_error = True
            self.error_message = f"Failed to load dashboard: {str(e)}"

        finally:
            self.is_loading = False

    def _format_sensor_tile(self, sensor: SensorData, chart_points: List) -> Dict:
        """센서 데이터를 View용으로 포맷"""
        return {
            "tag_name": sensor.tag_name,
            "value_text": f"{sensor.value:.1f}",
            "timestamp": sensor.timestamp.strftime("%H:%M:%S") if sensor.timestamp else "",
            "gauge_percent": sensor.gauge_percent,
            "range_text": f"{sensor.min_val:.0f}-{sensor.max_val:.0f}",
            "status": sensor.status,
            "chart_color": "#ef4444" if sensor.status == 2 else "#f59e0b" if sensor.status == 1 else "#10b981",
            "has_chart": len(chart_points) > 0,
            "chart_data": [{"time": p.time, "value": p.value} for p in chart_points]
        }

    @rx.event
    async def manual_refresh(self):
        """수동 새로고침"""
        console.info("Manual refresh triggered")
        await self.fetch_dashboard_data()

    @rx.event
    def toggle_auto_refresh(self):
        """자동 새로고침 토글"""
        if self.auto_refresh:
            self.auto_refresh = False
            console.info("Auto-refresh stopped")
        else:
            self.auto_refresh = True
            console.info("Auto-refresh started")
            return DashboardController.start_auto_refresh

    @rx.event(background=True)
    async def start_auto_refresh(self):
        """자동 새로고침 시작 - Background task"""
        async with self:
            self.auto_refresh = True

        # Initial update
        yield

        while True:
            # Check if still enabled
            async with self:
                if not self.auto_refresh:
                    break

            try:
                # Fetch data
                sensors = await DashboardModel.get_latest_sensor_data()
                tag_names = [s.tag_name for s in sensors]
                chart_data = await DashboardModel.get_chart_data(tag_names)
                stats = await DashboardModel.get_sensor_stats()

                # Format for view
                tiles = []
                for sensor in sensors:
                    tiles.append(self._format_sensor_tile(sensor, chart_data.get(sensor.tag_name, [])))

                # Update state
                async with self:
                    self.sensor_tiles = tiles
                    self.sensor_stats = stats
                    self.last_update = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%H:%M:%S")

                # Update UI
                yield

            except Exception as e:
                console.error(f"Auto-refresh failed: {e}")
                async with self:
                    self.has_error = True
                    self.error_message = f"Auto-refresh failed: {str(e)}"
                    self.auto_refresh = False
                yield
                break

            # Wait before next update
            await asyncio.sleep(10)

    def cleanup(self):
        """정리 작업"""
        self.auto_refresh = False
        console.info("Dashboard controller cleaned up")