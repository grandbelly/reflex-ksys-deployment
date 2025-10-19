"""
Forecast Player State - Real-time prediction monitoring
"""
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional
import reflex as rx
from reflex.utils import console

from ksys_app.states.base_state import BaseState
from ksys_app.services.forecast_service import ForecastService
from ksys_app.db_orm import get_async_session


class ForecastPlayerState(BaseState):
    """State for forecast player page - monitors online predictions"""

    # Data
    deployed_models: List[Dict] = []
    selected_model_id: Optional[int] = None
    selected_tag_name: str = ""
    predictions: List[Dict] = []
    latest_value: Optional[float] = None  # FIX: Changed from Dict to float
    latest_forecast_time: Optional[str] = None  # ✅ FIX: Store forecast_time for T0 display

    # Cached metrics from forecast_player_cache (pre-calculated)
    cached_mape: Optional[float] = None
    cached_rmse: Optional[float] = None
    cached_mae: Optional[float] = None
    cached_accuracy: Optional[float] = None

    # Playlist - 실시간 예측 중인 모든 태그 목록
    playlist_items: List[Dict] = []  # [{"model_id": 67, "tag_name": "INLET_PRESSURE", "next_forecast_at": datetime, "countdown": 120}, ...]
    show_playlist: bool = False  # Playlist 패널 표시 여부

    # UI State
    last_update: str = ""
    is_streaming: bool = False
    update_interval: int = 600  # 10 minutes (600 seconds) - 실시간 10분 갱신
    countdown_seconds: int = 600  # Countdown timer for next refresh (서버에서 계산됨)

    # Step Navigation (Phase 3 Extension - Forecast Playback)
    forecast_steps: List[Dict] = []  # List of all forecast steps
    current_step_index: int = 0  # 0-based index into forecast_steps
    step_data: Optional[Dict] = None  # Combined actual + forecast data for current step
    view_mode: str = "realtime"  # "realtime" or "playback"

    # Chart-ready data from Service (Dashboard pattern - no computation in State)
    realtime_chart_data: List[Dict] = []  # DEPRECATED - 기존 grouped 방식
    rolling_window_data: List[Dict] = []  # NEW - Rolling Window (동적 horizons)
    timeline_chart_data_cache: List[Dict] = []  # From ForecastService.get_step_data()

    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================

    @rx.var
    def has_deployed_models(self) -> bool:
        return len(self.deployed_models) > 0

    @rx.var
    def has_predictions(self) -> bool:
        """Check if rolling window data exists (not using predictions list anymore)"""
        return len(self.rolling_window_data) > 0

    @rx.var
    def chart_data(self) -> List[Dict]:
        """
        Returns Rolling Window chart data (Dashboard pattern)
        Service provides fully formatted data - no computation needed
        """
        return self.rolling_window_data

    @rx.var
    def accuracy_metrics(self) -> Dict:
        """
        Get accuracy metrics - use pre-calculated values from cache if available.
        Fall back to calculating from predictions if cached values don't exist.
        """
        # Use cached metrics if available (from forecast_player_cache)
        if self.cached_mape is not None or self.cached_rmse is not None or self.cached_mae is not None:
            return {
                "mae": round(self.cached_mae, 2) if self.cached_mae is not None else None,
                "mape": round(self.cached_mape, 2) if self.cached_mape is not None else None,
                "rmse": round(self.cached_rmse, 2) if self.cached_rmse is not None else None,
                "r2": 0.93,  # Placeholder - can calculate from accuracy if needed
                "count": len([p for p in self.predictions if p.get("has_actual")]) if self.predictions else 0
            }

        # Fallback: Calculate from predictions (old logic)
        if not self.predictions:
            return {"mae": None, "mape": None, "rmse": None, "count": 0}
        completed = [p for p in self.predictions if p.get("has_actual")]
        if not completed:
            return {"mae": None, "mape": None, "rmse": None, "count": 0}
        errors = [abs(p["prediction_error"]) for p in completed if p.get("prediction_error") is not None]
        mape_values = [p["absolute_percentage_error"] for p in completed if p.get("absolute_percentage_error") is not None]
        squared_errors = [p["prediction_error"] ** 2 for p in completed if p.get("prediction_error") is not None]
        mae = sum(errors) / len(errors) if errors else None
        mape = sum(mape_values) / len(mape_values) if mape_values else None
        rmse = (sum(squared_errors) / len(squared_errors)) ** 0.5 if squared_errors else None
        return {
            "mae": round(mae, 2) if mae is not None else None,
            "mape": round(mape, 2) if mape is not None else None,
            "rmse": round(rmse, 2) if rmse is not None else None,
            "count": len(completed)
        }

    @rx.var
    def selected_model_info(self) -> Dict:
        if not self.selected_model_id:
            return {}
        for model in self.deployed_models:
            if model["model_id"] == self.selected_model_id:
                return model
        return {}

    @rx.var
    def has_accuracy_data(self) -> bool:
        """Check if there are completed predictions for accuracy metrics"""
        metrics = self.accuracy_metrics
        return metrics.get("count", 0) > 0

    @rx.var
    def mape_formatted(self) -> str:
        """Format MAPE with % sign"""
        mape = self.accuracy_metrics.get("mape")
        if mape is None:
            return "N/A"
        return f"{mape}%"

    # Step Navigation Computed Properties
    @rx.var
    def has_steps(self) -> bool:
        """Check if forecast steps are available"""
        return len(self.forecast_steps) > 0

    @rx.var
    def total_steps(self) -> int:
        """Total number of forecast steps"""
        return len(self.forecast_steps)

    @rx.var
    def current_step_number(self) -> int:
        """Current step number (1-indexed for display)"""
        return self.current_step_index + 1

    @rx.var
    def current_step_info(self) -> Dict:
        """Get info for current step"""
        if not self.has_steps or self.current_step_index >= len(self.forecast_steps):
            return {}
        return self.forecast_steps[self.current_step_index]

    @rx.var
    def can_go_prev(self) -> bool:
        """Check if can navigate to previous step"""
        return self.current_step_index > 0

    @rx.var
    def can_go_next(self) -> bool:
        """Check if can navigate to next step"""
        return self.current_step_index < len(self.forecast_steps) - 1

    @rx.var
    def timeline_chart_data(self) -> List[Dict]:
        """
        Returns chart-ready timeline data from Service (Dashboard pattern)
        Service provides fully formatted data - no computation needed
        """
        return self.timeline_chart_data_cache

    @rx.var
    def current_time_marker(self) -> str:
        """
        Current time marker for reference line (Past | Present | Future)
        Returns formatted time string matching chart x-axis format
        """
        from datetime import datetime
        from zoneinfo import ZoneInfo
        kst = ZoneInfo("Asia/Seoul")
        now = datetime.now(kst)
        # Match the format used in chart data (e.g., "10-17 15:24")
        return now.strftime("%m-%d %H:%M")

    @rx.var
    def total_predictions_count(self) -> int:
        """Total number of predictions (including future predictions without actual values)"""
        return len(self.predictions)

    @rx.var
    def mape_display(self) -> str:
        """Display MAPE value with proper formatting"""
        if self.accuracy_metrics and 'mape' in self.accuracy_metrics:
            mape_val = self.accuracy_metrics['mape']
            if mape_val is not None:
                return f"{mape_val:.2f}%"
        return "N/A"

    @rx.var
    def r2_display(self) -> str:
        """Display R² value - approximate from accuracy percentage"""
        # Use cached accuracy if available
        if self.cached_accuracy is not None:
            # Approximate R² from accuracy (accuracy% / 100)
            r2_approx = self.cached_accuracy / 100.0
            return f"{r2_approx:.3f}"

        if self.accuracy_metrics and 'r2' in self.accuracy_metrics:
            r2_val = self.accuracy_metrics['r2']
            if r2_val is not None:
                return f"{r2_val:.3f}"

        # Calculate R² from predictions if not in metrics
        if self.has_accuracy_data:
            completed = [p for p in self.predictions if p.get("has_actual")]
            if len(completed) > 1:
                # Simple R² calculation
                actual_vals = [p.get("actual_value", 0) for p in completed]
                predicted_vals = [p.get("predicted_value", 0) for p in completed]
                mean_actual = sum(actual_vals) / len(actual_vals)
                ss_res = sum((a - p) ** 2 for a, p in zip(actual_vals, predicted_vals))
                ss_tot = sum((a - mean_actual) ** 2 for a in actual_vals)
                if ss_tot > 0:
                    r2 = 1 - (ss_res / ss_tot)
                    return f"{r2:.3f}"
        return "N/A"

    @rx.var
    def accuracy_percentage_display(self) -> str:
        """Display accuracy percentage - use cached value if available"""
        # Use cached accuracy directly
        if self.cached_accuracy is not None:
            return f"{self.cached_accuracy:.2f}%"

        # Fallback: Calculate from MAPE
        if self.accuracy_metrics and 'mape' in self.accuracy_metrics:
            mape_val = self.accuracy_metrics['mape']
            if mape_val is not None:
                accuracy = 100 - mape_val
                return f"{accuracy:.1f}%"
        return "N/A"

    @rx.var
    def chart_data_with_errors(self) -> List[Dict]:
        """Add error rate calculation to chart data for table display"""
        data = []
        for row in self.chart_data:
            row_copy = dict(row)
            # Calculate error percentage if both values exist
            if row.get("actual_value") is not None and row.get("predicted_value") is not None:
                actual = row["actual_value"]
                predicted = row["predicted_value"]
                if actual != 0:
                    error_pct = abs((actual - predicted) / actual * 100)
                    row_copy["error_rate"] = f"{error_pct:.1f}%"
                    # Add color scheme based on error rate
                    if error_pct < 5:
                        row_copy["error_color"] = "green"
                    elif error_pct < 10:
                        row_copy["error_color"] = "yellow"
                    else:
                        row_copy["error_color"] = "red"
                else:
                    row_copy["error_rate"] = "-"
                    row_copy["error_color"] = "gray"
            else:
                row_copy["error_rate"] = "-"
                row_copy["error_color"] = "gray"

            # Add zone info if not present
            if "zone" not in row_copy:
                if row.get("actual_value") is not None and row.get("predicted_value") is None:
                    row_copy["zone"] = "past"
                elif row.get("actual_value") is None and row.get("predicted_value") is not None:
                    row_copy["zone"] = "future"
                else:
                    row_copy["zone"] = "present"

            data.append(row_copy)
        return data

    @rx.var
    def table_time_columns(self) -> List[Dict]:
        """Generate column headers for horizontal table (ALL data points with scroll)"""
        if not self.chart_data:
            return []

        # Find T0 index (current time) for highlighting
        t0_index = -1
        for i, point in enumerate(self.chart_data):
            if point.get("time_label", "").startswith("T0") or point.get("time_label", "") == "T":
                t0_index = i
                break

        if t0_index == -1:
            # If no T0, use middle point
            t0_index = len(self.chart_data) // 2

        # Generate columns for ALL data points (not just T-3 to T+3)
        columns = []
        for idx, point in enumerate(self.chart_data):
            offset = idx - t0_index
            label = f"T{offset:+d}" if offset != 0 else "T (현재)"
            columns.append({
                "label": label,
                "index": idx,
                "is_present": offset == 0,
                "is_future": offset > 0
            })

        return columns

    @rx.var
    def time_row_data(self) -> List[str]:
        """Actual datetime for horizontal table (MM-DD HH:MM format)"""
        if not self.chart_data or not self.table_time_columns:
            return []
        result = []
        for col in self.table_time_columns:
            idx = col["index"]
            if idx < len(self.chart_data):
                point = self.chart_data[idx]
                timestamp_iso = point.get("timestamp")
                if timestamp_iso:
                    try:
                        from datetime import datetime
                        ts = datetime.fromisoformat(timestamp_iso)
                        # Format as MM-DD HH:MM
                        result.append(ts.strftime("%m-%d %H:%M"))
                    except (ValueError, AttributeError):
                        result.append("-")
                else:
                    result.append("-")
        return result

    @rx.var
    def plan_row_data(self) -> List[str]:
        """Plan values for horizontal table"""
        if not self.chart_data or not self.table_time_columns:
            return []
        result = []
        for col in self.table_time_columns:
            idx = col["index"]
            if idx < len(self.chart_data):
                point = self.chart_data[idx]
                plan_val = point.get("predicted_value") if point.get("predicted_value") is not None else point.get("actual_value")
                result.append(f"{plan_val:.2f}" if plan_val is not None else "-")
        return result

    @rx.var
    def actual_row_data(self) -> List[str]:
        """Actual values for horizontal table"""
        if not self.chart_data or not self.table_time_columns:
            return []
        result = []
        for col in self.table_time_columns:
            idx = col["index"]
            if idx < len(self.chart_data):
                actual = self.chart_data[idx].get("actual_value")
                result.append(f"{actual:.2f}" if actual is not None else "-")
        return result

    @rx.var
    def predicted_row_data(self) -> List[str]:
        """Predicted values for horizontal table"""
        if not self.chart_data or not self.table_time_columns:
            return []
        result = []
        for col in self.table_time_columns:
            idx = col["index"]
            if idx < len(self.chart_data):
                pred = self.chart_data[idx].get("predicted_value")
                result.append(f"{pred:.2f}" if pred is not None else "-")
        return result

    @rx.var
    def error_row_data(self) -> List[str]:
        """Absolute error values for horizontal table"""
        if not self.chart_data or not self.table_time_columns:
            return []
        result = []
        for col in self.table_time_columns:
            idx = col["index"]
            if idx < len(self.chart_data):
                point = self.chart_data[idx]
                actual = point.get("actual_value")
                pred = point.get("predicted_value")
                if actual is not None and pred is not None:
                    result.append(f"{abs(actual - pred):.2f}")
                else:
                    result.append("-")
        return result

    @rx.var
    def error_pct_row_data(self) -> List[str]:
        """Relative error percentage for horizontal table"""
        if not self.chart_data or not self.table_time_columns:
            return []
        result = []
        for col in self.table_time_columns:
            idx = col["index"]
            if idx < len(self.chart_data):
                point = self.chart_data[idx]
                actual = point.get("actual_value")
                pred = point.get("predicted_value")
                if actual is not None and pred is not None and actual != 0:
                    rel_err = abs((actual - pred) / actual * 100)
                    result.append(f"{rel_err:.1f}%")
                else:
                    result.append("-")
        return result

    @rx.var
    def ci_row_data(self) -> List[str]:
        """Confidence interval for horizontal table"""
        if not self.chart_data or not self.table_time_columns:
            return []
        result = []
        for col in self.table_time_columns:
            idx = col["index"]
            if idx < len(self.chart_data):
                point = self.chart_data[idx]
                ci_lower = point.get("ci_lower")
                ci_upper = point.get("ci_upper")
                if ci_lower is not None and ci_upper is not None:
                    result.append(f"[{ci_lower:.1f}, {ci_upper:.1f}]")
                else:
                    result.append("-")
        return result

    @rx.var
    def mae_metric(self) -> Optional[float]:
        """Mean Absolute Error calculated from chart data"""
        if not self.chart_data:
            return None
        errors = []
        for point in self.chart_data:
            actual = point.get("actual_value")
            pred = point.get("predicted_value")
            if actual is not None and pred is not None:
                errors.append(abs(actual - pred))
        return sum(errors) / len(errors) if errors else None

    @rx.var
    def mape_metric(self) -> Optional[float]:
        """Mean Absolute Percentage Error calculated from chart data"""
        if not self.chart_data:
            return None
        errors = []
        for point in self.chart_data:
            actual = point.get("actual_value")
            pred = point.get("predicted_value")
            if actual is not None and pred is not None and actual != 0:
                errors.append(abs((actual - pred) / actual * 100))
        return sum(errors) / len(errors) if errors else None

    @rx.var
    def status_row_data(self) -> List[str]:
        """Status for horizontal table"""
        if not self.chart_data or not self.table_time_columns:
            return []
        result = []
        for col in self.table_time_columns:
            idx = col["index"]
            if idx < len(self.chart_data):
                point = self.chart_data[idx]
                actual = point.get("actual_value")
                pred = point.get("predicted_value")
                if actual is not None:
                    if pred is not None and actual != 0:
                        err_pct = abs((actual - pred) / actual * 100)
                        if err_pct < 2:
                            result.append("양호")
                        else:
                            result.append("주의")
                    else:
                        result.append("양호")
                elif pred is not None:
                    result.append("예측")
                else:
                    result.append("-")
        return result

    @rx.var
    def table_data_rows(self) -> Dict[str, List]:
        """Generate horizontal table data (metrics as rows) - DEPRECATED"""
        if not self.chart_data or not self.table_time_columns:
            return {
                "time_row": [],
                "plan_row": [],
                "actual_row": [],
                "predicted_row": [],
                "error_row": [],
                "error_pct_row": [],
                "ci_row": [],
                "status_row": []
            }

        time_row = []
        plan_row = []
        actual_row = []
        predicted_row = []
        error_row = []
        error_pct_row = []
        ci_row = []
        status_row = []

        for col in self.table_time_columns:
            idx = col["index"]
            if idx < len(self.chart_data):
                point = self.chart_data[idx]

                # Time
                time_row.append(point.get("time_label", "-"))

                # Plan value (using predicted as plan for now)
                plan_val = point.get("predicted_value") if point.get("predicted_value") is not None else point.get("actual_value")
                plan_row.append(f"{plan_val:.2f}" if plan_val is not None else "-")

                # Actual value
                actual = point.get("actual_value")
                actual_row.append(f"{actual:.2f}" if actual is not None else "-")

                # Predicted value
                pred = point.get("predicted_value")
                predicted_row.append(f"{pred:.2f}" if pred is not None else "-")

                # Absolute error
                if actual is not None and pred is not None:
                    error_row.append(f"{abs(actual - pred):.2f}")
                else:
                    error_row.append("-")

                # Relative error %
                if actual is not None and pred is not None and actual != 0:
                    rel_err = abs((actual - pred) / actual * 100)
                    error_pct_row.append(f"{rel_err:.1f}%")
                else:
                    error_pct_row.append("-")

                # Confidence interval
                ci_lower = point.get("ci_lower")
                ci_upper = point.get("ci_upper")
                if ci_lower is not None and ci_upper is not None:
                    ci_row.append(f"[{ci_lower:.1f}, {ci_upper:.1f}]")
                else:
                    ci_row.append("-")

                # Status
                if actual is not None:
                    if pred is not None and actual != 0:
                        err_pct = abs((actual - pred) / actual * 100)
                        if err_pct < 2:
                            status_row.append("양호")
                        else:
                            status_row.append("주의")
                    else:
                        status_row.append("양호")
                elif pred is not None:
                    status_row.append("예측")
                else:
                    status_row.append("-")

        return {
            "time_row": time_row,
            "plan_row": plan_row,
            "actual_row": actual_row,
            "predicted_row": predicted_row,
            "error_row": error_row,
            "error_pct_row": error_pct_row,
            "ci_row": ci_row,
            "status_row": status_row
        }

    @rx.var
    def countdown_display(self) -> str:
        """Format countdown timer as MM:SS"""
        minutes = self.countdown_seconds // 60
        seconds = self.countdown_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    @rx.var
    def countdown_percentage(self) -> float:
        """Calculate countdown progress percentage (0-100)"""
        return (self.countdown_seconds / self.update_interval) * 100

    @rx.var
    def has_playlist(self) -> bool:
        """Check if playlist has items"""
        return len(self.playlist_items) > 0

    @rx.var
    def playlist_count(self) -> int:
        """Number of active forecasts in playlist"""
        return len(self.playlist_items)

    @rx.var
    def model_horizons(self) -> List[int]:
        """
        Extract horizons from selected model's pipeline_config.
        Returns list of horizon minutes (e.g., [10, 20, 30, ..., 360])
        """
        if not self.selected_model_id:
            return []

        model_info = self.selected_model_info
        if not model_info:
            return []

        pipeline_config_raw = model_info.get("pipeline_config")
        if not pipeline_config_raw:
            return []

        # Parse JSON string if needed (PostgreSQL returns JSONB as string)
        import json
        try:
            if isinstance(pipeline_config_raw, str):
                pipeline_config = json.loads(pipeline_config_raw)
            else:
                pipeline_config = pipeline_config_raw
        except (json.JSONDecodeError, TypeError):
            console.error(f"❌ Failed to parse pipeline_config: {pipeline_config_raw}")
            return []

        forecast_config = pipeline_config.get("forecast_config", {})
        horizons = forecast_config.get("horizons", [])

        console.debug(f"🔍 [HORIZONS] Extracted {len(horizons)} horizons from pipeline_config: {horizons[:5] if horizons else 'None'}...")

        return horizons if horizons else []

    @rx.var
    def representative_horizons(self) -> List[int]:
        """
        Get representative horizons for chart display (avoid overcrowding).
        If model has many horizons, select 4-5 representative ones.

        Examples:
        - [10, 20, ..., 360] (36 steps) → [10, 60, 180, 360]
        - [5, 10, ..., 1440] (288 steps) → [5, 60, 360, 720, 1440]
        """
        horizons = self.model_horizons
        if not horizons:
            return []

        if len(horizons) <= 5:
            return horizons  # Show all if 5 or fewer

        # Select first, 1/6, 1/2, 5/6, and last
        indices = [
            0,  # First horizon
            len(horizons) // 6,  # ~1 hour if 10-min steps
            len(horizons) // 2,  # Mid-point
            (5 * len(horizons)) // 6,  # ~5/6
            len(horizons) - 1  # Last horizon
        ]

        result = [horizons[i] for i in indices if i < len(horizons)]
        console.debug(f"📊 [REPRESENTATIVE] Selected {len(result)} representative horizons from {len(horizons)}: {result}")

        return result

    @rx.var
    def past_zone_start(self) -> str:
        """First time_label in chart data for Past zone ReferenceArea x1"""
        if not self.rolling_window_data or len(self.rolling_window_data) == 0:
            return ""
        return self.rolling_window_data[0].get("time_label", "")

    @rx.var
    def t0_label(self) -> str:
        """T0 time_label for ReferenceArea boundary (Past/Future divider) - Point with zone='present'"""
        if not self.rolling_window_data:
            return ""

        # ✅ FIX: Find point with zone="present" (T0 boundary point at forecast_time)
        # This is the correct T0 - the time when forecast was generated
        for point in self.rolling_window_data:
            if point.get("zone") == "present":
                return point.get("time_label", "")

        # Fallback 1: Find FIRST point with prediction but no actual value (T+1)
        for point in self.rolling_window_data:
            pred = point.get("predicted_value")
            actual = point.get("actual_value")
            if pred is not None and actual is None:
                return point.get("time_label", "")

        # Fallback 2: middle point
        mid = len(self.rolling_window_data) // 2
        return self.rolling_window_data[mid].get("time_label", "") if mid < len(self.rolling_window_data) else ""

    @rx.var
    def future_zone_end(self) -> str:
        """Last time_label in chart data for Future zone ReferenceArea x2"""
        if not self.rolling_window_data or len(self.rolling_window_data) == 0:
            return ""
        return self.rolling_window_data[-1].get("time_label", "")

    # =========================================================================
    # NEW COMPUTED VARS FOR REALTIME PAGE
    # =========================================================================

    @rx.var
    def available_models(self) -> List[str]:
        """Convert deployed_models to Select options format"""
        return [f"{m['model_id']}" for m in self.deployed_models]

    @rx.var
    def has_data(self) -> bool:
        """Check if rolling window data exists"""
        return len(self.rolling_window_data) > 0

    @rx.var
    def current_tag_name(self) -> str:
        """Alias for selected_tag_name"""
        return self.selected_tag_name

    @rx.var
    def current_model_type(self) -> str:
        """Get model type from selected model info"""
        model_info = self.selected_model_info
        return model_info.get("model_type", "AUTO_ARIMA") if model_info else "AUTO_ARIMA"

    @rx.var
    def mape(self) -> float:
        """Extract MAPE value from accuracy_metrics"""
        metrics = self.accuracy_metrics
        mape_val = metrics.get("mape")
        return mape_val if mape_val is not None else 0.0

    # NOTE: present_zone_start/end removed - Present는 T0 한 점만 (ReferenceArea 불필요)
    # Future zone은 T0부터 시작하여 future_zone_end까지

    @rx.var
    def t0_time_label(self) -> str:
        """Alias for t0_label (for consistency with forecast_player_realtime.py)"""
        return self.t0_label

    @rx.var
    def scheduler_running(self) -> bool:
        """Scheduler running status - check Docker container"""
        try:
            import subprocess
            # Check if forecast-scheduler container is running
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=forecast-scheduler", "--filter", "status=running", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return "forecast-scheduler" in result.stdout
        except Exception:
            # If Docker command fails, assume scheduler is running
            return True

    @rx.var
    def next_forecast_time_display(self) -> str:
        """
        Display next forecast time as absolute time (HH:MM:SS format)
        Calculates next forecast time by adding countdown_seconds to current time
        """
        if self.countdown_seconds <= 0:
            return "곧 실행 예정"

        # Calculate next forecast time (current time + countdown_seconds)
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        kst = ZoneInfo("Asia/Seoul")
        now = datetime.now(kst)
        next_forecast = now + timedelta(seconds=self.countdown_seconds)

        # Format as HH:MM:SS (same format as last_update)
        return next_forecast.strftime("%H:%M:%S")

    @rx.var
    def last_forecast_time_display(self) -> str:
        """Display last forecast time from last_update"""
        return self.last_update if self.last_update else "N/A"

    @rx.var
    def t0_reference_time_display(self) -> str:
        """
        Display T0 reference time with date (YYYY-MM-DD HH:MM:SS format).
        Uses timestamp from rolling_window zone='present' point (T0 boundary).
        """
        # ✅ FIX: Find point with zone="present" and use its timestamp
        if self.rolling_window_data:
            for point in self.rolling_window_data:
                if point.get("zone") == "present":
                    timestamp_iso = point.get("timestamp")
                    if timestamp_iso:
                        try:
                            ts = datetime.fromisoformat(timestamp_iso)
                            return ts.strftime("%Y-%m-%d %H:%M:%S")
                        except (ValueError, AttributeError):
                            pass

        # Fallback: Use stored forecast_time from database
        if self.latest_forecast_time:
            return self.latest_forecast_time

        # Ultimate fallback
        return "N/A"

    @rx.var
    def y_axis_domain(self) -> List:
        """Y축 범위 계산 - 실측값, 예측값, CI 상하한 모두 고려하여 ±5% 마진 추가"""
        if not self.rolling_window_data:
            return [0, 100]  # 기본값

        # ✅ FIX: 모든 실측값, 예측값, CI 상하한 수집 (CI 범위까지 포함)
        values = []
        for point in self.rolling_window_data:
            actual = point.get("actual_value")
            predicted = point.get("predicted_value")
            ci_lower = point.get("ci_lower")
            ci_upper = point.get("ci_upper")

            if actual is not None:
                values.append(float(actual))
            if predicted is not None:
                values.append(float(predicted))
            # ✅ CI 범위도 Y축 계산에 포함 (CI 밴드가 잘리지 않도록)
            if ci_lower is not None:
                values.append(float(ci_lower))
            if ci_upper is not None:
                values.append(float(ci_upper))

        if not values:
            return [0, 100]  # 기본값

        data_min = min(values)
        data_max = max(values)

        # ±5% 마진 추가 (CI 범위까지 포함했으므로 마진은 작게)
        margin = (data_max - data_min) * 0.05 if data_max != data_min else 10
        y_min = data_min - margin
        y_max = data_max + margin

        return [round(y_min, 2), round(y_max, 2)]

    @rx.var
    def forecast_horizon_display(self) -> str:
        """
        Display forecast horizon dynamically from model's pipeline_config.
        Format: "X시간 (Y points)"
        Example: "10.6시간 (64 points)"
        """
        horizons = self.model_horizons
        if not horizons:
            return "N/A"

        # Calculate time span from horizons
        # horizons is a list of minutes: [10, 20, 30, ..., 360, 370, ..., 640]
        max_horizon = max(horizons) if horizons else 0
        num_horizons = len(horizons)

        # Convert minutes to hours (with 1 decimal place)
        hours = max_horizon / 60.0

        return f"{hours:.1f}시간 ({num_horizons} points)"

    @rx.var
    def forecast_interval_minutes(self) -> int:
        """
        Get forecast interval in minutes from model's horizons.
        Returns the step size between consecutive horizons.
        Example: [10, 20, 30, ...] → 10 minutes
        """
        horizons = self.model_horizons
        if not horizons or len(horizons) < 2:
            return 10  # Default 10분

        # Calculate interval from first two horizons
        interval = horizons[1] - horizons[0]
        return interval

    @rx.var
    def forecast_interval_display(self) -> str:
        """
        Display forecast interval dynamically.
        Example: "10분", "5분", "1시간"
        """
        interval = self.forecast_interval_minutes
        if interval < 60:
            return f"{interval}분"
        else:
            hours = interval / 60
            return f"{hours:.0f}시간"

    @rx.var
    def chart_x_axis_interval(self) -> int:
        """
        Calculate dynamic X-axis label interval for chart.
        Shows ~10-15 labels regardless of data points.
        """
        total_points = len(self.chart_data)
        if total_points <= 15:
            return 0  # Show all labels if 15 or fewer points

        # Target ~12 labels
        return max(1, total_points // 12)

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    @rx.event(background=True)
    async def load_deployed_models(self):
        """Load list of deployed models on page mount - Dashboard pattern"""
        console.info("🔄 [FORECAST] Loading deployed models...")
        try:
            # Fetch models
            async with get_async_session() as session:
                service = ForecastService(session)
                models = await service.get_deployed_models()

            console.info(f"✅ [FORECAST] Found {len(models)} deployed models")

            # Update state
            async with self:
                self.deployed_models = models
                if models:
                    self.selected_model_id = models[0]["model_id"]
                    self.selected_tag_name = models[0]["tag_name"]
                    console.info(f"📌 [FORECAST] Auto-selected: {models[0]['model_name']} ({models[0]['tag_name']})")
                yield  # Update UI

            # Load playlist (모든 활성 모델의 실시간 상태)
            await self._load_playlist_internal()

            # Load predictions for first model if available (Dashboard pattern)
            if models:
                console.info(f"🔄 [FORECAST] Loading initial predictions for {models[0]['tag_name']}...")
                await self._load_predictions_internal()
                async with self:
                    yield  # Update UI after predictions load

            # ✅ FIX Bug 4: Start countdown monitor in the background after initial data load
            # This will update countdown display and check for new forecasts every 30 seconds
            # Note: Cannot use 'return' in async generator, so we spawn a background task instead
            if models:
                console.info("🚀 [FORECAST] Starting countdown monitor in background...")
                import asyncio
                asyncio.create_task(self.start_countdown_monitor())

        except Exception as e:
            console.error(f"❌ [FORECAST] Error loading deployed models: {e}")
            async with self:
                self.error_message = f"Failed to load models: {str(e)}"
                yield

    def select_model(self, model_id: str):
        """User selects a model from dropdown"""
        try:
            model_id_int = int(model_id)
            model_info = None
            for model in self.deployed_models:
                if model["model_id"] == model_id_int:
                    model_info = model
                    break
            if model_info:
                self.selected_model_id = model_id_int
                self.selected_tag_name = model_info["tag_name"]
                console.info(f"Selected model: {model_info.get('model_name', 'Unknown')} ({self.selected_tag_name})")
                # Trigger background event to load predictions
                return ForecastPlayerState.load_predictions
        except ValueError:
            console.error(f"Invalid model_id: {model_id}")

    async def _load_playlist_internal(self):
        """
        Load playlist - 모든 활성 모델의 실시간 예측 상태
        Playlist shows ALL active forecasts with their countdowns
        """
        console.info("🔄 [PLAYLIST] Loading playlist...")
        try:
            kst = ZoneInfo("Asia/Seoul")
            now = datetime.now(kst)

            async with get_async_session() as session:
                from sqlalchemy import text

                # Get latest cache for ALL active models
                playlist_query = text("""
                    SELECT DISTINCT ON (c.model_id)
                        c.model_id,
                        c.tag_name,
                        m.model_type,
                        m.model_name,
                        c.next_forecast_at,
                        c.latest_value,
                        c.forecast_time
                    FROM forecast_player_cache c
                    INNER JOIN model_registry m ON c.model_id = m.model_id
                    WHERE m.is_deployed = TRUE
                      AND m.is_active = TRUE
                    ORDER BY c.model_id, c.forecast_time DESC
                """)

                result = await session.execute(playlist_query)
                rows = result.mappings().all()

                # Build playlist items with countdown
                playlist = []
                for row in rows:
                    next_forecast = row["next_forecast_at"]
                    countdown = 0
                    if next_forecast:
                        time_until_next = (next_forecast - now).total_seconds()
                        countdown = max(0, int(time_until_next))

                    playlist.append({
                        "model_id": row["model_id"],
                        "tag_name": row["tag_name"],
                        "model_type": row["model_type"],
                        "model_name": row["model_name"],
                        "next_forecast_at": next_forecast,
                        "countdown_seconds": countdown,
                        "latest_value": float(row["latest_value"]) if row["latest_value"] else None,
                        "forecast_time": row["forecast_time"]
                    })

                console.info(f"✅ [PLAYLIST] Loaded {len(playlist)} active forecast(s)")

            # Update state
            async with self:
                self.playlist_items = playlist

        except Exception as e:
            console.error(f"❌ [PLAYLIST] Error loading playlist: {e}")
            import traceback
            console.error(traceback.format_exc())

    async def _load_predictions_internal(self):
        """
        Internal data fetch - DIRECT from predictions table (no cache)
        This ensures we always get the latest data from the source of truth.
        """
        if not self.selected_model_id:
            console.warn("⚠️ [FORECAST] No model selected")
            return

        console.info(f"🔄 [FORECAST] Loading predictions DIRECTLY from predictions table for model {self.selected_model_id}...")

        try:
            kst = ZoneInfo("Asia/Seoul")
            update_time = datetime.now(kst).strftime("%H:%M:%S")

            # ✅ DIRECT QUERY: Get rolling window from ForecastService
            async with get_async_session() as session:
                service = ForecastService(session)

                # Get rolling window data (uses get_rolling_window_data which queries predictions table directly)
                rolling_data = await service.get_rolling_window_data(
                    model_id=self.selected_model_id,
                    lookback_intervals=30  # ✅ FIX: 30 past intervals (T-30 to T-1) + T0 + 36 horizons = 67 total points
                )

                console.debug(f"🪟 [DIRECT] Loaded {len(rolling_data)} rolling window points from predictions table")

                # Get latest sensor value from influx_latest
                from sqlalchemy import text
                latest_query = text("""
                    SELECT value
                    FROM influx_latest
                    WHERE tag_name = (SELECT tag_name FROM model_registry WHERE model_id = :model_id)
                    LIMIT 1
                """)
                latest_result = await session.execute(latest_query, {"model_id": self.selected_model_id})
                latest_row = latest_result.mappings().first()
                latest_value = float(latest_row["value"]) if latest_row and latest_row["value"] else None

                # ✅ FIX: Get latest forecast_time for T0 display
                forecast_time_query = text("""
                    SELECT MAX(forecast_time) AT TIME ZONE 'Asia/Seoul' as ft
                    FROM predictions
                    WHERE model_id = :model_id
                """)
                forecast_time_result = await session.execute(forecast_time_query, {"model_id": self.selected_model_id})
                forecast_time_row = forecast_time_result.mappings().first()
                latest_forecast_time_str = None
                if forecast_time_row and forecast_time_row["ft"]:
                    latest_forecast_time_str = forecast_time_row["ft"].strftime("%Y-%m-%d %H:%M:%S")
                    console.debug(f"🕐 [T0] Latest forecast_time: {latest_forecast_time_str}")

                # Calculate metrics from rolling_window_data
                mape_values = []
                mae_values = []
                squared_errors = []

                for point in rolling_data:
                    actual = point.get("actual_value")
                    pred = point.get("predicted_value")
                    if actual is not None and pred is not None and actual != 0:
                        error = abs(actual - pred)
                        pct_error = (error / abs(actual)) * 100
                        mape_values.append(pct_error)
                        mae_values.append(error)
                        squared_errors.append(error ** 2)

                cached_mape = sum(mape_values) / len(mape_values) if mape_values else None
                cached_mae = sum(mae_values) / len(mae_values) if mae_values else None
                cached_rmse = (sum(squared_errors) / len(squared_errors)) ** 0.5 if squared_errors else None
                cached_accuracy = (100 - cached_mape) if cached_mape is not None else None

                mape_str = f"{cached_mape:.2f}" if cached_mape is not None else "N/A"
                mae_str = f"{cached_mae:.2f}" if cached_mae is not None else "N/A"
                rmse_str = f"{cached_rmse:.2f}" if cached_rmse is not None else "N/A"
                console.debug(f"📈 [CALCULATED] MAPE={mape_str}%, MAE={mae_str}, RMSE={rmse_str}")

            # Update state (NO yield here - caller will yield)
            async with self:
                self.rolling_window_data = rolling_data
                self.predictions = []  # Not using predictions list anymore
                self.latest_value = latest_value
                self.latest_forecast_time = latest_forecast_time_str  # ✅ FIX: Store forecast_time for T0 display
                self.last_update = update_time
                self.error_message = ""

                # Store calculated metrics
                self.cached_mape = cached_mape
                self.cached_rmse = cached_rmse
                self.cached_mae = cached_mae
                self.cached_accuracy = cached_accuracy

                # Calculate countdown (next forecast in 10 minutes from latest forecast_time)
                # Assume 10-minute interval
                self.countdown_seconds = 600  # 10 minutes default

            console.info(f"✅ [FORECAST] Loaded {len(rolling_data)} points directly from predictions table")

        except Exception as e:
            console.error(f"❌ [FORECAST] Error loading predictions: {e}")
            import traceback
            console.error(f"📋 [FORECAST] Traceback:\n{traceback.format_exc()}")
            async with self:
                self.error_message = f"Failed to load predictions: {str(e)}"

    @rx.event(background=True)
    async def load_predictions(self):
        """Load predictions for selected model - called from select_model"""
        await self._load_predictions_internal()
        # Yield to update UI
        yield

    @rx.event(background=True)
    async def start_streaming(self):
        """Start real-time streaming updates - Dashboard pattern with 10-minute countdown"""
        async with self:
            self.is_streaming = True
            self.last_update = "Initializing..."
            self.countdown_seconds = self.update_interval  # Reset countdown
            yield  # Update UI immediately

        console.info(f"✅ Forecast streaming started (interval: {self.update_interval}s = 10분)")

        # Initial load
        try:
            await asyncio.wait_for(
                self._load_predictions_internal(),
                timeout=10.0
            )
            async with self:
                self.countdown_seconds = self.update_interval  # Reset after initial load
                yield  # CRITICAL: yield after initial load to update UI
        except asyncio.TimeoutError:
            console.warn("Initial prediction load timeout")
            async with self:
                self.last_update = "Initial load timeout"
                yield
        except Exception as e:
            console.error(f"Initial load error: {e}")
            async with self:
                self.last_update = f"Error: {str(e)[:50]}"
                yield

        # Streaming loop with countdown timer
        while self.is_streaming:
            # Countdown loop (decrement every second)
            for remaining in range(self.update_interval, 0, -1):
                if not self.is_streaming:
                    break

                async with self:
                    self.countdown_seconds = remaining
                    yield  # Update countdown display

                await asyncio.sleep(1)  # Wait 1 second

            if not self.is_streaming:
                break

            # Refresh predictions when countdown reaches 0
            console.info(f"⏰ [FORECAST] 10분 경과 - 예측 데이터 갱신 시작...")
            try:
                # Use timeout to prevent long-running queries
                await asyncio.wait_for(
                    self._load_predictions_internal(),
                    timeout=30  # 30 second timeout for query
                )
                # Reset countdown after successful refresh
                async with self:
                    self.countdown_seconds = self.update_interval
                    yield  # CRITICAL: yield after successful fetch to update UI
                console.info(f"✅ [FORECAST] 예측 데이터 갱신 완료 - 다음 갱신: 10분 후")
            except asyncio.TimeoutError:
                console.warn(f"⚠️ [FORECAST] Prediction refresh timeout after 30s")
                async with self:
                    kst = ZoneInfo("Asia/Seoul")
                    self.last_update = f"Timeout at {datetime.now(kst).strftime('%H:%M:%S')}"
                    self.countdown_seconds = self.update_interval  # Reset countdown anyway
                    yield
            except Exception as e:
                console.error(f"❌ [FORECAST] Streaming error: {e}")
                async with self:
                    self.last_update = f"Error: {str(e)[:50]}"
                    self.countdown_seconds = self.update_interval  # Reset countdown anyway
                    yield

    def stop_streaming(self):
        """Stop streaming updates"""
        self.is_streaming = False
        console.info("Forecast streaming stopped")

    def toggle_playlist(self):
        """Toggle playlist panel visibility"""
        self.show_playlist = not self.show_playlist
        console.info(f"📋 [PLAYLIST] Panel {'opened' if self.show_playlist else 'closed'}")

    def select_from_playlist(self, model_id: int):
        """Select a model from playlist - same as select_model but with int"""
        return self.select_model(str(model_id))

    # =========================================================================
    # STEP NAVIGATION EVENT HANDLERS (Phase 3 Extension)
    # =========================================================================

    @rx.event(background=True)
    async def load_forecast_steps(self):
        """Load available forecast steps for selected model - Dashboard pattern"""
        if not self.selected_model_id:
            console.warn("⚠️ [FORECAST STEPS] No model selected")
            return

        console.info(f"🔄 [FORECAST STEPS] Loading steps for model {self.selected_model_id}...")

        try:
            async with get_async_session() as session:
                service = ForecastService(session)
                steps = await service.get_forecast_steps(model_id=self.selected_model_id)

            console.info(f"✅ [FORECAST STEPS] Found {len(steps)} forecast steps")

            async with self:
                self.forecast_steps = steps
                self.current_step_index = len(steps) - 1 if steps else 0  # Start at latest step
                yield

            # Load data for latest step if available
            if steps:
                await self._load_step_data_internal()
                # CRITICAL: yield after loading step data to update UI
                async with self:
                    yield

        except Exception as e:
            console.error(f"❌ [FORECAST STEPS] Error loading steps: {e}")
            async with self:
                self.error_message = f"Failed to load forecast steps: {str(e)}"
                yield

    async def _load_step_data_internal(self):
        """Internal data fetch for step data - Dashboard pattern (no yield)"""
        if not self.has_steps or self.current_step_index >= len(self.forecast_steps):
            console.warn("⚠️ [STEP DATA] Invalid step index")
            return

        current_step = self.forecast_steps[self.current_step_index]
        forecast_time = current_step.get("forecast_time")

        if not forecast_time:
            console.warn("⚠️ [STEP DATA] No forecast_time in step")
            return

        console.info(f"🔄 [STEP DATA] Loading data for step {self.current_step_number}/{self.total_steps} (forecast_time: {forecast_time})")

        try:
            async with get_async_session() as session:
                service = ForecastService(session)
                step_data = await service.get_step_data(
                    model_id=self.selected_model_id,
                    forecast_time=forecast_time,
                    lookback_days=7
                )

            console.info(f"✅ [STEP DATA] Loaded {len(step_data.get('actual_data', []))} actual + {len(step_data.get('forecast_data', []))} forecast points")

            # Dashboard pattern: Get chart-ready combined data from Service
            timeline_data = await service.get_timeline_chart_data(
                model_id=self.selected_model_id,
                forecast_time=forecast_time,
                lookback_days=7
            )

            async with self:
                self.step_data = step_data  # Keep raw data for reference
                self.timeline_chart_data_cache = timeline_data  # Chart-ready combined format

            console.info(f"✅ [TIMELINE] Combined timeline data: {len(timeline_data)} points")

        except Exception as e:
            console.error(f"❌ [STEP DATA] Error loading step data: {e}")
            async with self:
                self.error_message = f"Failed to load step data: {str(e)}"

    @rx.event(background=True)
    async def go_to_step(self, step_index: int):
        """Navigate to specific step by index"""
        if step_index < 0 or step_index >= len(self.forecast_steps):
            console.warn(f"⚠️ [STEP NAV] Invalid step index: {step_index}")
            return

        async with self:
            self.current_step_index = step_index
            yield

        console.info(f"🔄 [STEP NAV] Navigating to step {step_index + 1}/{len(self.forecast_steps)}")
        await self._load_step_data_internal()
        # CRITICAL: yield after loading step data to update UI
        async with self:
            yield

    def go_first_step(self):
        """Navigate to first step"""
        if self.has_steps:
            return ForecastPlayerState.go_to_step(0)

    def go_prev_step(self):
        """Navigate to previous step"""
        if self.can_go_prev:
            return ForecastPlayerState.go_to_step(self.current_step_index - 1)

    def go_next_step(self):
        """Navigate to next step"""
        if self.can_go_next:
            return ForecastPlayerState.go_to_step(self.current_step_index + 1)

    def go_last_step(self):
        """Navigate to last step"""
        if self.has_steps:
            return ForecastPlayerState.go_to_step(len(self.forecast_steps) - 1)

    def switch_to_playback_mode(self):
        """Switch to playback mode"""
        self.view_mode = "playback"
        console.info("📼 [VIEW MODE] Switched to playback mode")
        # Load forecast steps when switching to playback
        return ForecastPlayerState.load_forecast_steps

    def switch_to_realtime_mode(self):
        """Switch to real-time mode"""
        self.view_mode = "realtime"
        console.info("📡 [VIEW MODE] Switched to realtime mode")

    # =========================================================================
    # NEW METHODS FOR REALTIME PAGE
    # =========================================================================

    @rx.event(background=True)
    async def load_initial_data(self):
        """Load initial data when page mounts - alias for load_deployed_models"""
        await self.load_deployed_models()

    def set_selected_model_id(self, model_id: str):
        """Set selected model ID from dropdown - wrapper for select_model"""
        return self.select_model(model_id)

    @rx.event(background=True)
    async def load_selected_model_forecast(self):
        """Load forecast for selected model - called from Load button"""
        if not self.selected_model_id:
            console.warn("⚠️ [FORECAST] No model selected")
            async with self:
                self.error_message = "모델을 먼저 선택해주세요."
                yield
            return

        console.info(f"🔄 [FORECAST] Loading forecast for model {self.selected_model_id}...")
        await self._load_predictions_internal()
        async with self:
            yield  # Update UI

    @rx.event(background=True)
    async def trigger_forecast_now(self):
        """Trigger forecast generation immediately - manual execution"""
        console.info("🚀 [MANUAL TRIGGER] Starting manual forecast generation...")

        try:
            import subprocess

            # Execute forecast scheduler's run_once method via docker exec
            cmd = [
                "docker", "exec", "forecast-scheduler",
                "python", "-c",
                "import asyncio; from ksys_app.schedulers.forecast_scheduler import ForecastScheduler; asyncio.run(ForecastScheduler().run_once())"
            ]

            async with self:
                self.last_update = "Manual execution started..."
                yield

            # Run in background (don't block UI)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                console.info("✅ [MANUAL TRIGGER] Forecast generation completed successfully")
                async with self:
                    self.last_update = "Manual execution completed"
                    yield

                # Reload predictions after manual trigger
                await asyncio.sleep(2)  # Wait 2 seconds for cache update
                await self._load_predictions_internal()
                async with self:
                    yield  # Update UI with new data
            else:
                console.error(f"❌ [MANUAL TRIGGER] Failed: {result.stderr}")
                async with self:
                    self.error_message = f"Manual execution failed: {result.stderr[:100]}"
                    yield

        except subprocess.TimeoutExpired:
            console.error("❌ [MANUAL TRIGGER] Timeout after 60s")
            async with self:
                self.error_message = "Manual execution timeout (60s)"
                yield
        except Exception as e:
            console.error(f"❌ [MANUAL TRIGGER] Error: {e}")
            async with self:
                self.error_message = f"Manual execution error: {str(e)[:100]}"
                yield

    def start_scheduler(self):
        """Start forecast scheduler - placeholder for future implementation"""
        console.warn("⚠️ [SCHEDULER] Start/stop functionality not yet implemented")
        # TODO: Implement docker-compose up forecast-scheduler
        pass

    def stop_scheduler(self):
        """Stop forecast scheduler - placeholder for future implementation"""
        console.warn("⚠️ [SCHEDULER] Start/stop functionality not yet implemented")
        # TODO: Implement docker-compose stop forecast-scheduler
        pass

    @rx.event(background=True)
    async def start_countdown_monitor(self):
        """
        Monitor countdown and refresh data when scheduler generates new forecast.
        Updates countdown every 5 seconds, checks for new forecasts every 5 seconds.
        """
        console.info("⏱️ [COUNTDOWN] Starting countdown monitor...")

        # Get initial forecast_time from predictions table (source of truth)
        last_forecast_time = None
        try:
            async with get_async_session() as session:
                from sqlalchemy import text
                init_query = text("""
                    SELECT MAX(forecast_time) AT TIME ZONE 'Asia/Seoul' as ft
                    FROM predictions
                    WHERE model_id = :model_id
                """)
                result = await session.execute(init_query, {"model_id": self.selected_model_id})
                row = result.mappings().first()
                if row and row["ft"]:
                    last_forecast_time = row["ft"]
                    console.info(f"🕐 [COUNTDOWN] Initial forecast_time from predictions: {last_forecast_time}")

            # Load predictions data
            await self._load_predictions_internal()
            async with self:
                yield  # Update UI with initial data

        except Exception as e:
            console.error(f"❌ [COUNTDOWN] Initial load error: {e}")
            async with self:
                self.last_update = f"Error: {str(e)[:50]}"
                yield

        # ✅ FIX: Countdown loop - updates every 30 seconds to minimize chart re-renders
        # Only update UI when checking for new forecasts (30-second intervals)
        poll_counter = 0
        while True:
            await asyncio.sleep(30)  # ✅ Update every 30 seconds (minimize UI thrashing)
            poll_counter += 1

            async with self:
                # Decrement countdown by 30 seconds
                if self.countdown_seconds > 30:
                    self.countdown_seconds -= 30
                else:
                    self.countdown_seconds = 0
                # Don't yield here - will yield after cache check

            # Check for new forecasts every iteration (30 seconds)
            if True:  # Always check (every 30 seconds)
                poll_counter = 0  # Reset poll counter

                try:
                    # Quick check: Query predictions table for latest forecast_time (source of truth)
                    async with get_async_session() as session:
                        from sqlalchemy import text
                        check_query = text("""
                            SELECT MAX(forecast_time) AT TIME ZONE 'Asia/Seoul' as ft
                            FROM predictions
                            WHERE model_id = :model_id
                        """)
                        result = await session.execute(check_query, {"model_id": self.selected_model_id})
                        row = result.mappings().first()

                        if row and row["ft"]:
                            current_forecast_time = row["ft"]

                            # Check if forecast_time has changed (new forecast generated)
                            if last_forecast_time is None or current_forecast_time != last_forecast_time:
                                console.info(f"🆕 [COUNTDOWN] New forecast detected! Updating data... (prev: {last_forecast_time}, new: {current_forecast_time})")

                                # ✅ FIX: Wait for next countdown loop to yield (reduces UI thrashing)
                                # Reload full data
                                await self._load_predictions_internal()

                                # Update last_forecast_time BEFORE yield to prevent duplicate refreshes
                                last_forecast_time = current_forecast_time

                                # Yield after data is loaded
                                async with self:
                                    console.info("✅ [COUNTDOWN] Data refreshed with new forecast")
                                    yield
                            else:
                                # ✅ No new forecast - just update countdown display (lightweight yield)
                                async with self:
                                    yield

                except Exception as e:
                    console.error(f"❌ [COUNTDOWN] Poll error: {e}")
                    async with self:
                        yield  # Still yield to update countdown display
            else:
                # ✅ Just update countdown display without checking database (lightweight)
                async with self:
                    yield

