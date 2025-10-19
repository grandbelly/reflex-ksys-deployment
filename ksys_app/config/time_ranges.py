"""
Time range configurations for the application
"""

# Simplified time ranges for better UX
TIME_RANGES = [
    # Real-time (minutes)
    {"label": "5분", "value": "5 min", "category": "realtime"},
    {"label": "1시간", "value": "60 min", "category": "realtime"},
    
    # Short-term (hours/days)
    {"label": "24시간", "value": "24 hour", "category": "short"},
    {"label": "7일", "value": "7 days", "category": "short"},
    
    # Long-term (weeks/months)
    {"label": "30일", "value": "30 days", "category": "long"},
    {"label": "3개월", "value": "3 months", "category": "long"},
    {"label": "1년", "value": "12 months", "category": "long"},
]

# Default time range
DEFAULT_TIME_RANGE = "24 hour"

# Time range groups for UI
TIME_RANGE_GROUPS = {
    "realtime": {"name": "실시간", "icon": "activity"},
    "short": {"name": "단기", "icon": "calendar"},
    "long": {"name": "장기", "icon": "trending-up"},
}

# Quick select presets (like stock chart)
QUICK_PRESETS = [
    {"label": "1H", "value": "60 min"},
    {"label": "1D", "value": "24 hour"},
    {"label": "1W", "value": "7 days"},
    {"label": "1M", "value": "30 days"},
    {"label": "3M", "value": "3 months"},
    {"label": "1Y", "value": "12 months"},
]