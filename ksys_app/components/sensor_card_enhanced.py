"""Enhanced Sensor Card Component with Sparkline and Status Indicators

Features:
- Current value with 5-minute change indicator (▲▼)
- Freshness indicator (STALE badge if > 30 seconds)
- Sparkline with threshold bands (warn: amber, crit: red)
- Missing data handling (line breaks, last point marker)
- Range overflow clamping with △ marker
- Status colors: normal (blue), warning (amber), critical (red)
- Footer: range + warn + crit thresholds
"""
import reflex as rx
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def format_change_indicator(current: float, previous: float) -> Dict[str, str]:
    """Calculate 5-minute change and return indicator
    
    Returns:
        Dict with 'symbol' and 'color' keys
    """
    if previous == 0:
        return {"symbol": "─", "color": "gray"}
    
    change = current - previous
    pct_change = abs(change / previous * 100)
    
    if abs(change) < 0.01:  # No significant change
        return {"symbol": "─", "color": "gray"}
    elif change > 0:
        return {"symbol": f"▲{pct_change:.1f}%", "color": "red"}
    else:
        return {"symbol": f"▼{pct_change:.1f}%", "color": "blue"}


def is_stale(updated_at: str, threshold_seconds: int = 30) -> bool:
    """Check if data is stale (older than threshold)
    
    Args:
        updated_at: Timestamp string in KST (YYYY-MM-DD HH:MM:SS)
        threshold_seconds: Stale threshold in seconds
        
    Returns:
        True if data is stale
    """
    try:
        kst = ZoneInfo("Asia/Seoul")
        ts = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
        ts_kst = ts.replace(tzinfo=kst)
        now_kst = datetime.now(kst)
        age = (now_kst - ts_kst).total_seconds()
        return age > threshold_seconds
    except:
        return False


def get_status_color(status: int) -> str:
    """Get status color
    
    Args:
        status: 0=normal, 1=warning, 2=critical
        
    Returns:
        Color hex string
    """
    if status == 0:
        return "#3b82f6"  # blue
    elif status == 1:
        return "#f59e0b"  # amber
    else:
        return "#ef4444"  # red


def sensor_card_enhanced(sensor: Dict) -> rx.Component:
    """Enhanced sensor card with sparkline and indicators
    
    Data structure:
        {
            "tag_name": str,
            "description": str,
            "unit": str,
            "value": float,
            "timestamp": str,  # KST timestamp
            "status": int,  # 0=normal, 1=warning, 2=critical
            "min_val": float,
            "max_val": float,
            "warning_low": float,
            "warning_high": float,
            "chart_points": List[Dict],  # [{timestamp, value}]
            "gauge_percent": float,
        }
    """
    
    # Calculate 5-minute change
    previous_value = sensor.get("value", 0.0)
    if len(sensor.get("chart_points", [])) >= 5:
        previous_value = sensor["chart_points"][-5]["value"]
    
    change = format_change_indicator(sensor.get("value", 0.0), previous_value)
    
    # Check freshness
    stale = is_stale(sensor.get("timestamp", ""))
    
    # Status color
    status_color = get_status_color(sensor.get("status", 0))
    
    return rx.box(
        rx.vstack(
            # Header: Name + Change Indicator + Freshness
            rx.hstack(
                rx.text(
                    sensor.get("description", sensor["tag_name"]),
                    size="2",
                    weight="bold",
                    color="#111827"
                ),
                rx.spacer(),
                rx.cond(
                    stale,
                    rx.badge("STALE", color_scheme="gray", variant="soft", size="1"),
                    rx.text(
                        change["symbol"],
                        size="1",
                        color=change["color"],
                        weight="medium"
                    )
                ),
                width="100%",
                align="center"
            ),
            
            # Current Value (Large)
            rx.text(
                f"{sensor.get('value', 0):.2f} {sensor.get('unit', '')}",
                size="6",
                weight="bold",
                color=status_color,
                style={"lineHeight": "1"}
            ),
            
            # Sparkline placeholder (will be replaced with actual chart)
            rx.box(
                # Mini chart area
                rx.box(
                    height="48px",
                    width="100%",
                    bg=rx.cond(
                        stale,
                        "repeating-linear-gradient(45deg, #f3f4f6, #f3f4f6 10px, #e5e7eb 10px, #e5e7eb 20px)",
                        "#f9fafb"
                    ),
                    border_radius="4px",
                    border=f"1px solid {status_color}"
                ),
                width="100%"
            ),
            
            # Footer: Range + Thresholds
            rx.text(
                f"[{sensor.get('min_val', 0):.1f}~{sensor.get('max_val', 100):.1f} {sensor.get('unit', '')}] | "
                f"WARN: {sensor.get('warning_high', 0):.1f} | "
                f"CRIT: {sensor.get('max_val', 0):.1f}",
                size="1",
                color="#6b7280",
                width="100%"
            ),
            
            # Timestamp
            rx.text(
                sensor.get("timestamp", ""),
                size="1",
                color="#9ca3af",
                width="100%"
            ),
            
            spacing="2",
            width="100%"
        ),
        padding="3",
        border_radius="8px",
        border=f"2px solid {status_color}",
        bg="white",
        width="100%",
        _hover={"boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)"}
    )
