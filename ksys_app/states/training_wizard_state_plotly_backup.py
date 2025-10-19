"""
Training Wizard State - Sequential Workflow State Management
"""

import reflex as rx
from reflex.utils import console

from .training_state import TrainingState
from ..db_orm import get_async_session
from ..services.feature_config_service_final import FeatureConfigService


class TrainingWizardState(TrainingState):
    """Training Wizard State - extends TrainingState with wizard logic"""

    # Wizard state
    wizard_step: int = 1

    @rx.var
    def can_proceed(self) -> bool:
        """현재 단계에서 다음 단계로 진행 가능한지 확인"""
        if self.wizard_step == 1:
            return bool(self.selected_tag)
        elif self.wizard_step == 2:
            return bool(self.selected_model)
        elif self.wizard_step == 3:
            return self.skip_feature_engineering or (bool(self.selected_feature_config and self.feature_config_loaded))
        elif self.wizard_step == 4:
            return True  # Parameters have defaults
        elif self.wizard_step == 5:
            return self.training_complete
        return True

    async def next_step(self):
        """다음 단계로 이동"""
        if self.can_proceed and self.wizard_step < 6:
            self.wizard_step += 1

            # Step 6 (results)은 training 완료 후에만 도달
            if self.wizard_step == 6 and not self.training_complete:
                self.wizard_step = 5

    async def previous_step(self):
        """이전 단계로 이동"""
        if self.wizard_step > 1:
            # Skip step 6 when going back
            if self.wizard_step == 6:
                self.wizard_step = 4
            else:
                self.wizard_step -= 1

    @rx.event(background=True)
    async def initialize_wizard(self):
        """Wizard 초기화"""
        async with self:
            self.wizard_step = 1
            self.error_message = ""
            yield

        try:
            async with get_async_session() as session:
                service = FeatureConfigService(session)
                from sqlalchemy import text

                # Load available tags from influx_tag
                tag_query = text("SELECT tag_name FROM influx_tag ORDER BY tag_name")
                tag_result = await session.execute(tag_query)
                tags = [row[0] for row in tag_result.fetchall()]


                # Load available feature configs
                configs = await service.list_configs()

                async with self:
                    self.available_tags = tags
                    self.available_feature_configs = [
                        f"{c['tag_name']}:{c['config_name']}"
                        for c in configs
                    ]
                    yield

        except Exception as e:
            console.error(f"Initialize wizard failed: {e}")
            async with self:
                self.error_message = f"Failed to initialize: {e}"
                yield

    async def reset_wizard(self):
        """Wizard 리셋 - 새로운 training 시작"""
        self.wizard_step = 1
        self.selected_tag = ""
        self.selected_model = ""
        self.selected_feature_config = ""
        self.feature_config_loaded = False
        self.training_complete = False
        self.error_message = ""
        self.result_metadata = {}
        self.training_progress = 0
        self.training_status = ""
        self.is_training = False

    # Start training and monitor completion
    async def start_wizard_training(self):
        """Wizard에서 training 시작 - 완료 후 자동으로 step 6로 이동"""
        # Start parent's training (returns EventSpec, can't await)
        return TrainingState.start_training

    @rx.event(background=True)
    async def monitor_training_completion(self):
        """Training 완료를 모니터링하고 완료 시 step 6로 이동"""
        import asyncio

        # Wait for training to complete (check every 500ms)
        while True:
            await asyncio.sleep(0.5)

            # Check if training is complete
            if self.training_complete:
                async with self:
                    self.wizard_step = 6
                    yield
                break

            # If training failed or was cancelled
            if not self.is_training and not self.training_complete:
                break

    @rx.var
    def raw_samples_display(self) -> str:
        """Raw samples count for display"""
        return str(self.result_metadata.get("raw_samples", 0))

    @rx.var
    def processed_samples_display(self) -> str:
        """Processed samples count for display"""
        return str(self.result_metadata.get("processed_samples", 0))

    @rx.var
    def original_features_display(self) -> str:
        """Original features count for display"""
        return str(self.result_metadata.get("original_features", 0))

    @rx.var
    def final_features_display(self) -> str:
        """Final features count for display"""
        return str(self.result_metadata.get("final_features", 0))

    # Safe accessors for model_diagnostics dict
    @rx.var
    def arima_string(self) -> str:
        """ARIMA string from diagnostics"""
        return str(self.model_diagnostics.get("arima_string", "N/A"))

    @rx.var
    def aic_value(self) -> str:
        """AIC value formatted"""
        val = self.model_diagnostics.get("aic")
        return f"{float(val):.2f}" if val is not None else "N/A"

    @rx.var
    def bic_value(self) -> str:
        """BIC value formatted"""
        val = self.model_diagnostics.get("bic")
        return f"{float(val):.2f}" if val is not None else "N/A"

    @rx.var
    def aicc_value(self) -> str:
        """AICc value formatted"""
        val = self.model_diagnostics.get("aicc")
        return f"{float(val):.2f}" if val is not None else "N/A"

    @rx.var
    def residuals_mean_value(self) -> str:
        """Residuals mean formatted"""
        val = self.model_diagnostics.get("residuals_mean")
        return f"{float(val):.4f}" if val is not None else "N/A"

    @rx.var
    def residuals_std_value(self) -> str:
        """Residuals std formatted"""
        val = self.model_diagnostics.get("residuals_std")
        return f"{float(val):.4f}" if val is not None else "N/A"

    # Safe accessors for evaluation_metrics dict
    @rx.var
    def mae_value(self) -> str:
        """MAE value formatted"""
        val = self.evaluation_metrics.get("mae")
        return f"{float(val):.2f}" if val is not None else "N/A"

    @rx.var
    def mape_value(self) -> str:
        """MAPE value formatted"""
        val = self.evaluation_metrics.get("mape")
        return f"{float(val):.2f}%" if val is not None else "N/A"

    @rx.var
    def rmse_value(self) -> str:
        """RMSE value formatted"""
        val = self.evaluation_metrics.get("rmse")
        return f"{float(val):.2f}" if val is not None else "N/A"

    @rx.var
    def smape_value(self) -> str:
        """SMAPE value formatted"""
        val = self.evaluation_metrics.get("smape")
        return f"{float(val):.2f}%" if val is not None else "N/A"

    @rx.var
    def mase_value(self) -> str:
        """MASE value formatted"""
        val = self.evaluation_metrics.get("mase")
        return f"{float(val):.2f}" if val is not None else "N/A"

    @rx.var
    def n_windows_display(self) -> str:
        """Number of windows display"""
        val = self.evaluation_metrics.get("n_windows")
        return f"{int(val)} windows" if val is not None else "N/A"

    @rx.var
    def n_predictions_display(self) -> str:
        """Number of predictions display"""
        val = self.evaluation_metrics.get("n_predictions")
        return f"{int(val)} predictions" if val is not None else ""

    # Safe accessors for residuals_stats dict
    @rx.var
    def residuals_mean_stat(self) -> str:
        """Residuals mean stat"""
        val = self.residuals_stats.get("mean")
        return f"{float(val):.4f}" if val is not None else "N/A"

    @rx.var
    def residuals_std_stat(self) -> str:
        """Residuals std stat"""
        val = self.residuals_stats.get("std")
        return f"{float(val):.4f}" if val is not None else "N/A"

    @rx.var
    def residuals_skewness(self) -> str:
        """Residuals skewness"""
        val = self.residuals_stats.get("skewness")
        return f"{float(val):.2f}" if val is not None else "N/A"

    @rx.var
    def residuals_kurtosis(self) -> str:
        """Residuals kurtosis"""
        val = self.residuals_stats.get("kurtosis")
        return f"{float(val):.2f}" if val is not None else "N/A"

    # Conditional flags
    @rx.var
    def has_model_diagnostics(self) -> bool:
        """Check if model diagnostics available"""
        return bool(self.model_diagnostics.get("arima_string"))

    @rx.var
    def has_evaluation_metrics(self) -> bool:
        """Check if evaluation metrics available"""
        return bool(self.evaluation_metrics.get("mae"))

    @rx.var
    def has_residuals_stats(self) -> bool:
        """Check if residuals stats available"""
        return bool(self.residuals_stats.get("mean") is not None)

    # ============================================================
    # Chart Data Properties
    # ============================================================

    @rx.var
    def forecast_chart_data(self) -> list[dict]:
        """Format forecast data for Recharts - supports all model types"""
        if not self.forecast_with_intervals:
            return []

        chart_data = []
        for point in self.forecast_with_intervals:
            # Dynamically detect model column name
            model_col = None
            for key in ['AutoARIMA', 'Prophet', 'XGBoost', 'yhat', 'forecast']:
                if key in point:
                    model_col = key
                    break
            
            if not model_col:
                continue
            
            # Get confidence interval column names
            lo_80 = f"{model_col}-lo-80"
            hi_80 = f"{model_col}-hi-80"
            lo_95 = f"{model_col}-lo-95"
            hi_95 = f"{model_col}-hi-95"
            
            chart_data.append({
                "timestamp": point.get("ds", point.get("timestamp", "")),
                "forecast": float(point.get(model_col, 0)),
                "lower_80": float(point.get(lo_80, point.get("lower_80", 0))),
                "upper_80": float(point.get(hi_80, point.get("upper_80", 0))),
                "lower_95": float(point.get(lo_95, point.get("lower_95", 0))),
                "upper_95": float(point.get(hi_95, point.get("upper_95", 0))),
            })
        return chart_data


    @rx.var
    def forecast_chart_html(self) -> str:
        """Generate Plotly chart HTML from data"""
        from ..components.forecast_chart_plotly import create_mlforecast_chart

        data = self.combined_forecast_chart_data
        if not data:
            return "<div style='padding: 20px; text-align: center; color: gray;'>Loading chart...</div>"

        try:
            return create_mlforecast_chart(data)
        except Exception as e:
            return f"<div style='padding: 20px; color: red;'>Error generating chart: {e}</div>"

    @rx.var
    def combined_forecast_chart_data(self) -> list[dict]:
        """
        Combined chart data: historical actual + future forecast
        Shows context before and after current time
        """
        chart_data = []

        # Add historical sensor data (recent actual measurements)
        for point in self.historical_data:  # Already limited to last 48 points
            chart_data.append({
                "timestamp": point.get("timestamp", "")[:16],  # YYYY-MM-DDTHH:MM
                "actual": float(point.get("value", 0)),
                "forecast": None,
                "lower_80": None,
                "upper_80": None,
                "lower_95": None,
                "upper_95": None,
            })

        # Add forecast data (future predictions)
        for point in self.forecast_with_intervals:
            # Dynamically detect model column name
            model_col = None
            for key in ['AutoARIMA', 'Prophet', 'XGBoost', 'yhat', 'forecast']:
                if key in point:
                    model_col = key
                    break

            if not model_col:
                continue

            # Get confidence interval column names
            lo_80 = f"{model_col}-lo-80"
            hi_80 = f"{model_col}-hi-80"
            lo_95 = f"{model_col}-lo-95"
            hi_95 = f"{model_col}-hi-95"

            forecast_val = float(point.get(model_col, 0))
            chart_data.append({
                "timestamp": point.get("ds", point.get("timestamp", ""))[:16],
                "actual": None,  # No actual values in future
                "forecast": forecast_val,
                # Use forecast value as fallback instead of 0
                "lower_80": float(point.get(lo_80, point.get("lower_80", forecast_val))),
                "upper_80": float(point.get(hi_80, point.get("upper_80", forecast_val))),
                "lower_95": float(point.get(lo_95, point.get("lower_95", forecast_val))),
                "upper_95": float(point.get(hi_95, point.get("upper_95", forecast_val))),
            })

        return chart_data

    @rx.var
    def validation_chart_data(self) -> list[dict]:
        """Format validation data (actual vs predicted) for Recharts"""
        validation_data = self.evaluation_metrics.get("validation_data", [])
        if not validation_data:
            return []

        return [
            {
                "timestamp": point.get("ds", ""),
                "actual": float(point.get("actual", 0)),
                "predicted": float(point.get("predicted", 0)),
            }
            for point in validation_data
        ]

    @rx.var
    def validation_table_data(self) -> list[dict]:
        """Format validation data for comparison table with error calculations"""
        validation_data = self.evaluation_metrics.get("validation_data", [])
        if not validation_data:
            return []
        
        table_rows = []
        for point in validation_data:
            actual = float(point.get("actual", 0))
            predicted = float(point.get("predicted", 0))
            error = predicted - actual
            error_pct = (abs(error) / actual * 100) if actual != 0 else 0
            
            table_rows.append({
                "timestamp": point.get("ds", "")[:16],  # Trim to minutes
                "actual": f"{actual:.2f}",
                "predicted": f"{predicted:.2f}",
                "error": f"{error:+.2f}",  # + prefix for positive numbers
                "error_pct": f"{error_pct:.1f}%",
            })
        
        return table_rows

    @rx.var
    def acf_chart_data(self) -> list[dict]:
        """Format ACF data for Recharts"""
        acf_data = self.residuals_analysis.get("acf", [])
        if not acf_data:
            return []

        return [
            {"lag": i, "acf": float(val)}
            for i, val in enumerate(acf_data)
        ]

    @rx.var
    def pacf_chart_data(self) -> list[dict]:
        """Format PACF data for Recharts"""
        pacf_data = self.residuals_analysis.get("pacf", [])
        if not pacf_data:
            return []

        return [
            {"lag": i, "pacf": float(val)}
            for i, val in enumerate(pacf_data)
        ]

    @rx.var
    def qq_chart_data(self) -> list[dict]:
        """Format Q-Q plot data for Recharts"""
        qq_data = self.residuals_analysis.get("qq_plot", {})
        theoretical = qq_data.get("theoretical", [])
        sample = qq_data.get("sample", [])

        if not theoretical or not sample:
            return []

        return [
            {"theoretical": float(t), "sample": float(s)}
            for t, s in zip(theoretical, sample)
        ]

    @rx.var
    def histogram_chart_data(self) -> list[dict]:
        """Format histogram data for Recharts"""
        hist_data = self.residuals_analysis.get("histogram", {})
        bins = hist_data.get("bins", [])
        counts = hist_data.get("counts", [])

        if not bins or not counts:
            return []

        # Use bin centers for x-axis
        return [
            {"bin": float(bins[i]), "count": int(counts[i])}
            for i in range(len(counts))
        ]
