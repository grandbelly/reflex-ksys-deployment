"""
VTScada-style History Table Component
"""
import reflex as rx
from typing import List, Dict

def severity_badge(level: int) -> rx.Component:
    """Severity badge based on level"""
    severity_map = {
        5: ("Critical", "red"),
        4: ("High", "orange"),
        3: ("Medium", "yellow"),
        2: ("Low", "blue"),
        1: ("Info", "gray"),
    }

    label, color = severity_map.get(level, ("Unknown", "gray"))

    return rx.badge(label, color_scheme=color, variant="solid")

def history_table(alarms: List[Dict]) -> rx.Component:
    """
    VTScada-style History Table

    Columns:
    - Time (triggered_at)
    - Severity (level)
    - Message (message)
    - Active Time (triggered_at time only)
    - Inactive Time (resolved_at time only)
    """

    return rx.box(
        rx.table.root(
            # Header
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Time", width="180px"),
                    rx.table.column_header_cell("Severity", width="100px"),
                    rx.table.column_header_cell("Message", width="auto"),
                    rx.table.column_header_cell("Active Time", width="120px"),
                    rx.table.column_header_cell("Inactive Time", width="120px"),
                ),
            ),

            # Body
            rx.table.body(
                rx.foreach(
                    alarms,
                    lambda alarm: rx.table.row(
                        # Time
                        rx.table.cell(
                            rx.text(
                                alarm.get("triggered_at_full", ""),
                                size="2",
                                font_family="monospace",
                            ),
                        ),

                        # Severity
                        rx.table.cell(
                            severity_badge(alarm.get("level", 1)),
                        ),

                        # Message (truncated)
                        rx.table.cell(
                            rx.text(
                                alarm.get("message", ""),
                                size="2",
                                overflow="hidden",
                                text_overflow="ellipsis",
                                white_space="nowrap",
                            ),
                        ),

                        # Active Time (time only)
                        rx.table.cell(
                            rx.text(
                                alarm.get("triggered_time", ""),
                                size="2",
                                font_family="monospace",
                                color="gray",
                            ),
                        ),

                        # Inactive Time (time only)
                        rx.table.cell(
                            rx.text(
                                alarm.get("resolved_time", "-"),
                                size="2",
                                font_family="monospace",
                                color="gray",
                            ),
                        ),

                        _hover={"bg": "gray.50"},
                    ),
                ),
            ),

            variant="surface",
            size="2",
        ),

        width="100%",
        overflow_x="auto",
    )
