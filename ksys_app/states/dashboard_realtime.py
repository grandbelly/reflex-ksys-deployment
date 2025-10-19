"""
Dashboard Realtime State - Refactored with BaseState
- Inherits common utilities from BaseState
- Clean separation of concerns
- Proper background event usage
"""
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List
import reflex as rx
from reflex.utils import console

from ksys_app.states.base_state import BaseState
from ksys_app.services.sensor_service import SensorService
from ksys_app.db_orm import get_async_session


class DashboardRealtimeState(BaseState):
    """Real-time dashboard state with streaming updates"""

    # Data
    sensors: List[Dict] = []
    chart_data: Dict[str, List[Dict]] = {}

    # Forecast data
    forecast_data: Dict[str, Dict] = {}  # {tag_name: {predictions, timestamps, model_info}}

    # Statistics (기존)
    normal_count: int = 0
    warning_count: int = 0
    critical_count: int = 0

    # Statistics (새로 추가 - Dashboard Summary Bar용)
    total_devices: int = 0
    critical_percentage: float = 0.0
    avg_critical_deviation: float = 0.0
    max_alarm_sensor: str = ""
    max_alarm_value: float = 0.0

    # UI State
    last_update: str = ""
    is_streaming: bool = False
    update_interval: int = 15  # 15 seconds

    # Edit Dialog State
    show_edit_dialog: bool = False
    edit_tag_name: str = ""
    edit_description: str = ""
    edit_unit: str = ""
    edit_min_val: float = 0.0
    edit_max_val: float = 100.0
    edit_warning_low: float = 0.0
    edit_warning_high: float = 100.0
    edit_critical_low: float = 0.0
    edit_critical_high: float = 120.0

    # Full-Screen Chart Dialog State
    show_chart_dialog: bool = False
    chart_dialog_tag_name: str = ""
    chart_dialog_data: List[Dict] = []
    chart_dialog_sensor: Dict = {}

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
            console.log("Initial data load timeout")
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
                # IMPORTANT: yield after successful fetch to update UI
                yield
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
        """Internal data fetch - no yield, pure async"""
        try:
            # Fetch data using service layer
            async with get_async_session() as session:
                service = SensorService(session)

                # Get sensor data WITH chart points (new method)
                db_sensors = await service.get_realtime_alarms_with_charts()

                # Get dashboard statistics
                stats_data = await service.get_dashboard_statistics()

                # Get forecast data for deployed models
                forecast_results = await self._fetch_forecast_data(session)

                if not db_sensors:
                    console.log("No sensor data received")
                    return

                # Process sensors
                sensor_list = []
                for sensor in db_sensors:
                    min_val = 0
                    max_val = 100
                    gauge_percent = 50
                    warning_low = None
                    warning_high = None
                    critical_low = 0
                    critical_high = 120

                    if 'qc_rule' in sensor and sensor['qc_rule']:
                        min_val = sensor["qc_rule"].get("min_val") or 0
                        max_val = sensor["qc_rule"].get("max_val") or 100
                        warning_low = sensor['qc_rule'].get('warning_low')
                        warning_high = sensor['qc_rule'].get('warning_high')
                        critical_low = sensor["qc_rule"].get("critical_low") or 0
                        critical_high = sensor["qc_rule"].get("critical_high") or 120
                        value = sensor.get('value', 0)
                        # Calculate gauge percent with division by zero protection
                        range_val = max_val - min_val
                        if range_val > 0:
                            gauge_percent = ((value - min_val) / range_val) * 100
                            gauge_percent = round(min(100, max(0, gauge_percent)))
                        else:
                            # If range is 0 (min == max), set gauge to 0%
                            gauge_percent = 0

                    # Calculate deviation and risk percentage for table
                    deviation = 0
                    risk_percentage = 0

                    if sensor.get('status', 0) == 2:  # Critical
                        if value > max_val:
                            deviation = value - max_val
                        elif value < min_val:
                            deviation = value - min_val
                    elif sensor.get('status', 0) == 1:  # Warning
                        qc_rule = sensor.get('qc_rule', {})
                        warning_high = qc_rule.get('warning_high', max_val)
                        warning_low = qc_rule.get('warning_low', min_val)
                        if value > warning_high:
                            deviation = value - warning_high
                        elif value < warning_low:
                            deviation = value - warning_low

                    # Calculate risk percentage
                    if max_val > min_val:
                        range_size = max_val - min_val
                        if deviation > 0:
                            risk_percentage = min(100, (abs(deviation) / range_size) * 100)
                        elif deviation < 0:
                            risk_percentage = min(100, (abs(deviation) / range_size) * 100)

                    # Determine trend icon based on chart data
                    trend_icon = "→"
                    chart_points = sensor.get('chart_points', [])
                    if len(chart_points) >= 3:
                        recent_values = [p['value'] for p in chart_points[-3:]]
                        if all(recent_values[i] < recent_values[i+1] for i in range(len(recent_values)-1)):
                            if recent_values[-1] - recent_values[0] > range_size * 0.2:
                                trend_icon = "↑↑↑"
                            elif recent_values[-1] - recent_values[0] > range_size * 0.1:
                                trend_icon = "↑↑"
                            else:
                                trend_icon = "↑"
                        elif all(recent_values[i] > recent_values[i+1] for i in range(len(recent_values)-1)):
                            if recent_values[0] - recent_values[-1] > range_size * 0.2:
                                trend_icon = "↓↓↓"
                            elif recent_values[0] - recent_values[-1] > range_size * 0.1:
                                trend_icon = "↓↓"
                            else:
                                trend_icon = "↓"

                    # Format strings for display
                    unit = sensor.get('unit', '')
                    value_str = f"{sensor.get('value', 0):.2f}"
                    if unit:
                        value_str += f" {unit}"

                    range_str = f"{min_val:.2f} ~ {max_val:.2f}"
                    if unit:
                        range_str += f" {unit}"

                    deviation_str = f"{deviation:.2f}" if deviation != 0 else "-"
                    risk_pct_str = f"{risk_percentage:.2f}%"

                    # Determine trend color
                    if trend_icon.startswith("↑"):
                        trend_color = "red"
                    elif trend_icon.startswith("↓"):
                        trend_color = "blue"
                    else:
                        trend_color = "gray"

                    sensor_list.append({
                        "tag_name": sensor['tag_name'],
                        "description": sensor.get('description', sensor['tag_name']),
                        "unit": unit,
                        "value": sensor.get('value', 0),
                        "value_str": value_str,
                        "timestamp": sensor.get('timestamp', datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")),
                        "status": sensor.get('status', 0),
                        "gauge_percent": gauge_percent,
                        "min_val": min_val,
                        "max_val": max_val,
                        "warning_low": warning_low,
                        "warning_high": warning_high,
                        "critical_low": critical_low,
                        "critical_high": critical_high,
                        "range_str": range_str,
                        "chart_points": sensor.get('chart_points', []),  # Mini chart data
                        "chart_color": sensor.get('chart_color', '#10b981'),  # Chart color
                        "deviation": deviation,
                        "deviation_str": deviation_str,
                        "risk_percentage": risk_percentage,
                        "risk_pct_str": risk_pct_str,
                        "trend_icon": trend_icon,
                        "trend_color": trend_color
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
                self.forecast_data = forecast_results
                self.normal_count = stats['normal']
                self.warning_count = stats['warning']
                self.critical_count = stats['critical']

                # Update dashboard statistics (새로 추가)
                self.total_devices = stats_data['total_devices']
                self.critical_percentage = stats_data['critical_percentage']
                self.avg_critical_deviation = stats_data['avg_critical_deviation']
                self.max_alarm_sensor = stats_data['max_alarm_sensor']
                self.max_alarm_value = stats_data['max_alarm_value']

                self.last_update = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
                # UI update will be triggered by refresh_data()

            console.debug(f"Dashboard updated: {len(sensor_list)} sensors")

        except Exception as e:
            console.error(f"Refresh data failed: {e}")
            async with self:
                self.error_message = str(e)

    async def _fetch_forecast_data(self, session) -> Dict[str, Dict]:
        """배포된 모델의 예측 데이터를 가져옴"""
        try:
            from sqlalchemy import select, text
            from ..models.forecasting_orm import ModelRegistry, Prediction
            from datetime import datetime, timedelta

            # 배포된 모델 조회
            deployed_query = select(ModelRegistry).where(
                ModelRegistry.is_deployed == True,
                ModelRegistry.is_active == True
            )

            result = await session.execute(deployed_query)
            deployed_models = result.scalars().all()

            forecast_results = {}
            current_time = datetime.now()

            for model in deployed_models:
                # 해당 모델의 최신 예측 조회
                prediction_query = select(Prediction).where(
                    Prediction.model_id == model.model_id,
                    Prediction.tag_name == model.tag_name,
                    Prediction.target_time > current_time,
                    Prediction.target_time < current_time + timedelta(hours=24)
                ).order_by(Prediction.target_time)

                pred_result = await session.execute(prediction_query)
                predictions = pred_result.scalars().all()

                if predictions:
                    forecast_results[model.tag_name] = {
                        'model_name': model.model_name,
                        'model_type': model.model_type,
                        'predictions': [float(p.predicted_value) for p in predictions],
                        'timestamps': [p.target_time.isoformat() for p in predictions],
                        'confidence_lower': [float(p.ci_lower) if p.ci_lower else None for p in predictions],
                        'confidence_upper': [float(p.ci_upper) if p.ci_upper else None for p in predictions],
                        'horizon_hours': len(predictions)
                    }

            console.debug(f"Fetched forecasts for {len(forecast_results)} sensors")
            return forecast_results

        except Exception as e:
            console.error(f"Error fetching forecast data: {e}")
            return {}

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

            # Determine chart color based on status (hex colors for gradient mapping)
            # Status: 0=Normal(green), 1=Warning(yellow), 2=Critical(red)
            chart_color = ["#10b981", "#eab308", "#ef4444"][sensor["status"]]

            formatted.append({
                **sensor,
                "status_color": ["green", "yellow", "red"][sensor["status"]],
                "chart_points": chart_points,
                "chart_color": chart_color
            })
        return formatted

    @rx.var
    def critical_percentage_display(self) -> str:
        """Format critical percentage for display"""
        return f"{self.critical_percentage:.2f}%"

    @rx.var
    def avg_deviation_display(self) -> str:
        """Format average deviation for display"""
        return f"{self.avg_critical_deviation:.2f}%"

    @rx.var
    def max_alarm_display(self) -> str:
        """Format max alarm value for display"""
        return f"{self.max_alarm_value:.2f}"

    @rx.var
    def warning_percentage(self) -> float:
        """Calculate warning percentage for status distribution bar"""
        if self.total_devices == 0:
            return 0.0
        return (self.warning_count / self.total_devices) * 100

    @rx.var
    def normal_percentage(self) -> float:
        """Calculate normal percentage for status distribution bar"""
        if self.total_devices == 0:
            return 0.0
        return (self.normal_count / self.total_devices) * 100

    @rx.event(background=True)
    async def refresh_data(self):
        """Refresh sensor data - implements BaseState abstract method with yield"""
        await self._fetch_data()
        # Yield to trigger UI update
        async with self:
            yield

    # =========================================================================
    # SENSOR EDIT DIALOG HANDLERS
    # =========================================================================

    def open_edit_dialog(self, tag_name: str, description: str = "", unit: str = "", min_val: float = 0.0, max_val: float = 100.0, warning_low: float = 0.0, warning_high: float = 100.0, critical_low: float = 0.0, critical_high: float = 120.0):
        """Open edit dialog with sensor data"""
        self.edit_tag_name = tag_name
        self.edit_description = description
        self.edit_unit = unit
        self.edit_min_val = min_val
        self.edit_max_val = max_val
        self.edit_warning_low = warning_low
        self.edit_warning_high = warning_high
        self.edit_critical_low = critical_low
        self.edit_critical_high = critical_high
        self.show_edit_dialog = True

    def close_edit_dialog(self):
        """Close edit dialog"""
        self.show_edit_dialog = False

    def update_min_val(self, value: str):
        """Convert string to float for min_val"""
        try:
            self.edit_min_val = float(value) if value.strip() else 0.0
        except ValueError:
            self.edit_min_val = 0.0

    def update_max_val(self, value: str):
        """Convert string to float for max_val"""
        try:
            self.edit_max_val = float(value) if value.strip() else 0.0
        except ValueError:
            self.edit_max_val = 0.0

    def update_warning_low(self, value: str):
        """Convert string to float for warning_low"""
        try:
            self.edit_warning_low = float(value) if value.strip() else 0.0
        except ValueError:
            self.edit_warning_low = 0.0

    def update_warning_high(self, value: str):
        """Convert string to float for warning_high"""
        try:
            self.edit_warning_high = float(value) if value.strip() else 0.0
        except ValueError:
            self.edit_warning_high = 0.0

    def update_critical_low(self, value: str):
        """Convert string to float for critical_low"""
        try:
            self.edit_critical_low = float(value) if value.strip() else 0.0
        except ValueError:
            self.edit_critical_low = 0.0

    def update_critical_high(self, value: str):
        """Convert string to float for critical_high"""
        try:
            self.edit_critical_high = float(value) if value.strip() else 0.0
        except ValueError:
            self.edit_critical_high = 0.0


    @rx.event(background=True)
    async def save_sensor_info(self):
        """Save sensor information to database"""
        console.info(f"Saving sensor info: {self.edit_tag_name}")
        console.debug(f"State values: warning_high={self.edit_warning_high}, critical_high={self.edit_critical_high}")

        try:
            async with get_async_session() as session:
                service = SensorService(session)

                # Update sensor metadata (description, unit, range)
                # Note: This assumes influx_tag table has these columns
                # You may need to add them if they don't exist
                await service.update_sensor_metadata(
                    tag_name=self.edit_tag_name,
                    description=self.edit_description,
                    unit=self.edit_unit,
                    min_val=self.edit_min_val,
                    max_val=self.edit_max_val,
                    warning_low=self.edit_warning_low,
                    warning_high=self.edit_warning_high,
                    critical_low=self.edit_critical_low,
                    critical_high=self.edit_critical_high
                )

            async with self:
                self.show_edit_dialog = False
                yield

            # Refresh data to show updated info
            await self._fetch_data()

            console.info(f"Sensor {self.edit_tag_name} updated successfully")

        except Exception as e:
            console.error(f"Failed to save sensor info: {e}")
            async with self:
                self.last_update = f"Save error: {str(e)[:50]}"
                yield

    # =========================================================================
    # FULL-SCREEN CHART DIALOG HANDLERS
    # =========================================================================

    def open_chart_dialog(self, tag_name: str):
        """Open full-screen chart dialog for a sensor (wrapper for background event)"""
        console.info(f"Opening chart dialog for {tag_name}")

        # Find sensor data immediately
        sensor = next((s for s in self.sensors if s['tag_name'] == tag_name), None)

        if not sensor:
            console.warn(f"Sensor {tag_name} not found")
            return

        # Set dialog state immediately for responsive UI
        self.chart_dialog_tag_name = tag_name
        self.chart_dialog_sensor = sensor
        self.show_chart_dialog = True

        # Trigger background data load
        return DashboardRealtimeState.load_chart_data(tag_name)

    @rx.event(background=True)
    async def load_chart_data(self, tag_name: str):
        """Background task to load detailed chart data"""
        try:
            # Get detailed chart data (last 24 hours)
            async with get_async_session() as session:
                service = SensorService(session)
                chart_data = await service.get_sensor_chart_data(tag_name, hours=24)

            async with self:
                self.chart_dialog_data = chart_data
                yield

        except Exception as e:
            console.error(f"Failed to load chart data: {e}")

    def close_chart_dialog(self):
        """Close full-screen chart dialog"""
        self.show_chart_dialog = False
        self.chart_dialog_tag_name = ""
        self.chart_dialog_data = []
        self.chart_dialog_sensor = {}
