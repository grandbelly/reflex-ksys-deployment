"""
ISA-18.2 Alarm Management Standard Utilities
ANSI/ISA-18.2-2016: Management of Alarm Systems for the Process Industries
"""

# ISA-18.2 Priority Levels
ISA_PRIORITY_LOW = 1        # Advisory/Informational
ISA_PRIORITY_MEDIUM = 2     # Caution
ISA_PRIORITY_HIGH = 3       # Warning
ISA_PRIORITY_CRITICAL = 4   # Emergency

# ISA-18.2 Level Mapping (Database level -> ISA Priority)
# Level directly maps to Priority (1-4) for ISA-18.2 compliance
ISA_LEVEL_MAPPING = {
    1: {
        "priority": 1,
        "name": "LOW",
        "isa_name": "Advisory",
        "display_name": "Advisory",
        "color": "blue",
        "color_hex": "#3b82f6",
        "ack_required": False,
        "response_time": None,
    },
    2: {
        "priority": 2,
        "name": "MEDIUM",
        "isa_name": "Caution",
        "display_name": "Caution",
        "color": "yellow",
        "color_hex": "#eab308",
        "ack_required": True,
        "response_time": 600,
    },
    3: {
        "priority": 3,
        "name": "HIGH",
        "isa_name": "Warning",
        "display_name": "Warning",
        "color": "orange",
        "color_hex": "#f97316",
        "ack_required": True,
        "response_time": 180,
    },
    4: {
        "priority": 4,
        "name": "CRITICAL",
        "isa_name": "Emergency",
        "display_name": "Emergency",
        "color": "red",
        "color_hex": "#ef4444",
        "ack_required": True,
        "response_time": 60,
    },
}


def get_isa_priority(level: int) -> dict:
    """
    Get ISA-18.2 compliant priority information for a given level

    Args:
        level: Database alarm level (1-4)

    Returns:
        dict: ISA-18.2 priority information
    """
    return ISA_LEVEL_MAPPING.get(level, {
        "priority": 0,
        "name": "UNKNOWN",
        "isa_name": "Unknown",
        "display_name": "Unknown",
        "color": "gray",
        "color_hex": "#6b7280",
        "ack_required": False,
        "response_time": None,
    })


def get_priority_stats_fields():
    """Get field names for ISA-18.2 priority statistics"""
    return {
        "low": "Priority 1 (LOW)",
        "medium": "Priority 2 (MEDIUM)",
        "high": "Priority 3 (HIGH)",
        "critical": "Priority 4 (CRITICAL)",
    }


def map_level_to_priority(level: int) -> int:
    """Map database level to ISA priority (1-4)"""
    info = get_isa_priority(level)
    return info["priority"]
