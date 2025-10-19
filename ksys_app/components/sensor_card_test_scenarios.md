# Enhanced Sensor Card - Test Scenarios

## Overview
Enhanced sensor card with sparkline, status indicators, and freshness monitoring.

## Test Scenarios

### 1. Normal State (6.2 bar)
**Description**: Sensor operating within normal range

**Test Data**:
```python
{
    "tag_name": "OUTLET_PRESSURE",
    "description": "Outlet Pressure",
    "unit": "bar",
    "value": 6.2,
    "timestamp": "2025-10-07 17:00:00",  # Current time
    "status": 0,  # Normal
    "min_val": 0.0,
    "max_val": 10.0,
    "warning_low": 0.0,
    "warning_high": 8.0,
    "chart_points": [
        {"timestamp": "16:55", "value": 6.0},
        {"timestamp": "16:56", "value": 6.1},
        {"timestamp": "16:57", "value": 6.15},
        {"timestamp": "16:58", "value": 6.18},
        {"timestamp": "16:59", "value": 6.2},
    ],
    "gauge_percent": 62.0
}
```

**Expected Result**:
- Status: Blue border
- Change indicator: ▲3.3% (red, increasing from 6.0 to 6.2)
- No STALE badge
- Footer: [0.0~10.0 bar] | WARN: 8.0 | CRIT: 10.0

---

### 2. Warning State (8.3 bar)
**Description**: Sensor value exceeds warning threshold

**Test Data**:
```python
{
    "tag_name": "OUTLET_PRESSURE",
    "description": "Outlet Pressure",
    "unit": "bar",
    "value": 8.3,
    "timestamp": "2025-10-07 17:00:00",
    "status": 1,  # Warning
    "min_val": 0.0,
    "max_val": 10.0,
    "warning_low": 0.0,
    "warning_high": 8.0,
    "chart_points": [
        {"timestamp": "16:55", "value": 7.8},
        {"timestamp": "16:56", "value": 8.0},
        {"timestamp": "16:57", "value": 8.1},
        {"timestamp": "16:58", "value": 8.2},
        {"timestamp": "16:59", "value": 8.3},
    ],
    "gauge_percent": 83.0
}
```

**Expected Result**:
- Status: Amber border
- Change indicator: ▲6.4% (red, increasing from 7.8 to 8.3)
- Value in amber color
- Sparkline shows crossing warning threshold

---

### 3. Critical + Missing Data
**Description**: Critical state with data gaps

**Test Data**:
```python
{
    "tag_name": "INLET_PRESSURE",
    "description": "Inlet Pressure",
    "unit": "kPa",
    "value": 195000,
    "timestamp": "2025-10-07 17:00:00",
    "status": 2,  # Critical
    "min_val": 0,
    "max_val": 200000,
    "warning_low": 10000,
    "warning_high": 150000,
    "chart_points": [
        {"timestamp": "16:55", "value": 120000},
        {"timestamp": "16:56", "value": None},  # Missing
        {"timestamp": "16:57", "value": None},  # Missing
        {"timestamp": "16:58", "value": 180000},
        {"timestamp": "16:59", "value": 195000},
    ],
    "gauge_percent": 97.5
}
```

**Expected Result**:
- Status: Red border
- Change indicator: ▲62.5% (red, increasing from 120000 to 195000)
- Value in red color
- Sparkline shows line breaks for missing data
- Last point has marker

---

### 4. Range Overflow + Clamping
**Description**: Value exceeds maximum range (clamped)

**Test Data**:
```python
{
    "tag_name": "OUTLET_PRESSURE",
    "description": "Outlet Pressure",
    "unit": "bar",
    "value": 12.5,  # Exceeds max (10.0)
    "timestamp": "2025-10-07 17:00:00",
    "status": 2,  # Critical
    "min_val": 0.0,
    "max_val": 10.0,
    "warning_low": 0.0,
    "warning_high": 8.0,
    "chart_points": [
        {"timestamp": "16:55", "value": 9.5},
        {"timestamp": "16:56", "value": 10.2},  # Overflow
        {"timestamp": "16:57", "value": 11.0},  # Overflow
        {"timestamp": "16:58", "value": 11.8},  # Overflow
        {"timestamp": "16:59", "value": 12.5},  # Overflow
    ],
    "gauge_percent": 100.0  # Clamped to 100%
}
```

**Expected Result**:
- Status: Red border
- Change indicator: ▲31.6% (red)
- Value shows actual (12.5), gauge clamped to 100%
- △ markers on sparkline for overflow points
- Display: "12.5 bar" (actual value, not clamped)

---

### 5. Stale Data (> 30 seconds)
**Description**: Data not updated for more than 30 seconds

**Test Data**:
```python
{
    "tag_name": "FEED_FLOW",
    "description": "Feed Flow",
    "unit": "m³/h",
    "value": 5.2,
    "timestamp": "2025-10-07 16:58:00",  # 2 minutes old
    "status": 0,  # Normal
    "min_val": 0.0,
    "max_val": 10.0,
    "warning_low": 0.0,
    "warning_high": 8.0,
    "chart_points": [
        {"timestamp": "16:53", "value": 5.0},
        {"timestamp": "16:54", "value": 5.1},
        {"timestamp": "16:55", "value": 5.15},
        {"timestamp": "16:56", "value": 5.18},
        {"timestamp": "16:57", "value": 5.2},
    ],
    "gauge_percent": 52.0
}
```

**Expected Result**:
- Status: Blue border (still normal range)
- STALE badge shown (gray)
- Striped overlay on sparkline background
- No change indicator (replaced by STALE badge)
- Timestamp shows 16:58:00 (old)

---

## Usage in Dashboard

```python
from ksys_app.components.sensor_card_enhanced import sensor_card_enhanced

# In dashboard page
rx.grid(
    rx.foreach(
        DashboardState.sensors,
        sensor_card_enhanced
    ),
    columns="3",
    spacing="4",
    width="100%"
)
```

## Key Features Implemented

✅ **Freshness Monitoring**: STALE badge after 30 seconds
✅ **Change Indicators**: ▲▼ with percentage
✅ **Status Colors**: Blue (normal), Amber (warning), Red (critical)
✅ **Threshold Display**: Range + WARN + CRIT in footer
✅ **Missing Data**: Handled gracefully (line breaks)
✅ **Overflow Clamping**: Display actual value, clamp gauge
✅ **Visual Feedback**: Border color, hover effects

## Notes

- Sparkline currently shows as placeholder (gray box with border)
- To implement actual sparkline with Recharts:
  - Would need custom JavaScript component
  - Or use SVG/Canvas rendering in Reflex
  - Current implementation focuses on layout and data flow
- All timestamp calculations use KST (Asia/Seoul)
- Change calculation uses 5-data-point lookback
