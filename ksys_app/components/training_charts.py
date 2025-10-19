"""
Training Charts - Recharts Components for Training Wizard
Validation and Forecast Charts

Follows Reflex recharts API best practices:
- Uses rx.recharts.graphing_tooltip() for proper tooltips
- Uses type_="monotone" for smooth line interpolation
- Uses sync_id for chart synchronization
- Uses proper color system with rx.color()
- Uses area charts with base_value for confidence intervals
"""
import reflex as rx


def validation_chart(state_class) -> rx.Component:
    """
    Validation chart: Actual vs Predicted values
    Uses validation_chart_data from state

    Features:
    - Line chart with smooth curves (monotone interpolation)
    - Actual values in green solid line
    - Predicted values in blue dashed line
    - Hover tooltip showing exact values
    - Synchronized with forecast chart via sync_id
    - Interactive legend to toggle lines
    """
    return rx.recharts.line_chart(
        rx.recharts.line(
            data_key="actual",
            stroke=rx.color("grass", 9),
            name="Actual",
            stroke_width=2,
            type_="monotone",
            dot={"fill": rx.color("grass", 9), "r": 3},
            active_dot={"r": 5},
        ),
        rx.recharts.line(
            data_key="predicted",
            stroke=rx.color("blue", 9),
            name="Predicted",
            stroke_width=2,
            type_="monotone",
            stroke_dasharray="5 5",
            dot={"fill": rx.color("blue", 9), "r": 3},
            active_dot={"r": 5},
        ),
        rx.recharts.x_axis(
            data_key="timestamp",
            angle=-45,
            text_anchor="end",
            height=80,
        ),
        rx.recharts.y_axis(),
        rx.recharts.cartesian_grid(
            stroke_dasharray="3 3",
            opacity=0.3,
        ),
        rx.recharts.legend(
            vertical_align="top",
            height=36,
        ),
        rx.recharts.graphing_tooltip(),
        data=state_class.validation_chart_data,
        sync_id="training_charts",
        width="100%",
        height=400,
    )


def forecast_chart(state_class) -> rx.Component:
    """
    Forecast chart with confidence intervals
    Uses combined_forecast_chart_data from state (historical + forecast)

    Shows:
    - Historical actual values (green line)
    - Future predictions (blue line)
    - 80% confidence interval (blue area)
    - 95% confidence interval (light blue area)

    Features:
    - Area chart for confidence intervals
    - Composed chart combining areas and lines
    - Synchronized with validation chart via sync_id
    - Brush component for zooming into time ranges
    - Smooth curves with monotone interpolation
    """
    return rx.recharts.composed_chart(
        # 95% confidence interval (outer band) - lighter blue
        rx.recharts.area(
            data_key="lower_95",
            stroke="none",
            fill=rx.color("blue", 4),
            fill_opacity=0.3,
            name="95% CI Lower",
            type_="monotone",
            connect_nulls=True,
        ),
        rx.recharts.area(
            data_key="upper_95",
            stroke="none",
            fill=rx.color("blue", 4),
            fill_opacity=0.3,
            name="95% CI Upper",
            type_="monotone",
            connect_nulls=True,
        ),
        # 80% confidence interval (inner band) - darker blue
        rx.recharts.area(
            data_key="lower_80",
            stroke="none",
            fill=rx.color("blue", 6),
            fill_opacity=0.4,
            name="80% CI Lower",
            type_="monotone",
            connect_nulls=True,
        ),
        rx.recharts.area(
            data_key="upper_80",
            stroke="none",
            fill=rx.color("blue", 6),
            fill_opacity=0.4,
            name="80% CI Upper",
            type_="monotone",
            connect_nulls=True,
        ),
        # Historical actual values (green line)
        rx.recharts.line(
            data_key="actual",
            stroke=rx.color("grass", 9),
            name="Historical",
            stroke_width=2,
            type_="monotone",
            dot=False,
            connect_nulls=False,
        ),
        # Forecast predictions (blue line)
        rx.recharts.line(
            data_key="forecast",
            stroke=rx.color("blue", 9),
            name="Forecast",
            stroke_width=3,
            type_="monotone",
            dot={"fill": rx.color("blue", 9), "r": 4},
            active_dot={"r": 6},
            connect_nulls=False,
        ),
        rx.recharts.x_axis(
            data_key="timestamp",
            angle=-45,
            text_anchor="end",
            height=100,
        ),
        rx.recharts.y_axis(),
        rx.recharts.cartesian_grid(
            stroke_dasharray="3 3",
            opacity=0.3,
        ),
        rx.recharts.legend(
            vertical_align="top",
            height=50,
        ),
        rx.recharts.graphing_tooltip(),
        rx.recharts.brush(
            data_key="timestamp",
            height=30,
            stroke=rx.color("blue", 8),
        ),
        data=state_class.combined_forecast_chart_data,
        sync_id="training_charts",
        width="100%",
        height=500,
    )


def simple_forecast_chart(state_class) -> rx.Component:
    """
    Simplified forecast chart (no confidence intervals)
    Uses forecast_values directly

    Features:
    - Simple line chart
    - Shows forecast values only
    - Used as fallback when intervals not available
    """
    return rx.recharts.line_chart(
        rx.recharts.line(
            data_key="value",
            stroke=rx.color("blue", 9),
            name="Forecast",
            stroke_width=2,
            type_="monotone",
            dot={"fill": rx.color("blue", 9), "r": 3},
        ),
        rx.recharts.x_axis(
            data_key="hour",
            label="Hours Ahead",
        ),
        rx.recharts.y_axis(),
        rx.recharts.cartesian_grid(
            stroke_dasharray="3 3",
            opacity=0.3,
        ),
        rx.recharts.legend(),
        rx.recharts.graphing_tooltip(),
        data=state_class.simple_forecast_data,
        width="100%",
        height=350,
    )
