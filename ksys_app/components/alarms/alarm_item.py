"""
알람 아이템 컴포넌트
Light Mode 디자인
"""
import reflex as rx
from typing import Dict, Optional


def alarm_item(alarm: Dict) -> rx.Component:
    """
    알람 아이템 컴포넌트 - 캡처 화면 기준 디자인

    Expected alarm dict structure:
    {
        "id": int,
        "severity": str,  # "CRITICAL", "WARNING", "INFO"
        "status": str,    # "ACTIVE", "UNACKNOWLEDGED", "ACKNOWLEDGED"
        "message": str,
        "tag_name": str,
        "value": float,
        "threshold": str,
        "location": str,
        "timestamp": str,
        "duration": str,
    }
    """

    # Severity color schemes - Light Mode
    severity_colors = {
        "CRITICAL": {"bg": "#dc2626", "text": "white"},
        "WARNING": {"bg": "#f97316", "text": "white"},
        "INFO": {"bg": "#3b82f6", "text": "white"},
    }

    severity_scheme = severity_colors.get(
        alarm.get("severity", "INFO"),
        severity_colors["INFO"]
    )

    return rx.box(
        rx.vstack(
            # Header row: Severity + Status badges + Timestamp + Action buttons
            rx.flex(
                # Left: Badges
                rx.flex(
                    rx.badge(
                        alarm["severity"],
                        bg=severity_scheme["bg"],
                        color=severity_scheme["text"],
                        variant="solid",
                        size="1",
                    ),
                    rx.badge(
                        alarm["status"],
                        color_scheme="gray",
                        variant="outline",
                        size="1",
                    ),
                    gap="2",
                    align="center",
                ),

                rx.spacer(),

                # Right: Timestamp + Duration + Buttons
                rx.flex(
                    rx.text(
                        alarm["timestamp"],
                        size="1",
                        color="#6b7280",
                    ),
                    rx.text(
                        "|",
                        size="1",
                        color="#d1d5db",
                    ),
                    rx.text(
                        alarm["duration"],
                        size="1",
                        color="#6b7280",
                    ),
                    rx.button(
                        "Acknowledge",
                        size="1",
                        variant="soft",
                        color_scheme="blue",
                    ),
                    rx.button(
                        "Details",
                        size="1",
                        variant="soft",
                        color_scheme="gray",
                    ),
                    gap="2",
                    align="center",
                ),

                justify="between",
                width="100%",
                align="center",
            ),

            # Message (Korean text from screenshot)
            rx.text(
                alarm["message"],
                size="2",
                weight="medium",
                color="#111827",
            ),

            # Sensor info row
            rx.flex(
                # Sensor tag
                rx.flex(
                    rx.text("Sensor:", size="1", color="#9ca3af"),
                    rx.badge(
                        alarm["tag_name"],
                        variant="soft",
                        color_scheme="blue",
                        size="1",
                    ),
                    gap="1",
                    align="center",
                ),

                # Value vs Threshold
                rx.flex(
                    rx.text("Value:", size="1", color="#9ca3af"),
                    rx.text(
                        f"{alarm['value']}",
                        size="1",
                        weight="bold",
                        color="#111827",
                    ),
                    rx.text("Threshold:", size="1", color="#9ca3af"),
                    rx.text(
                        alarm["threshold"],
                        size="1",
                        color="#6b7280",
                    ),
                    gap="2",
                    align="center",
                ),

                # Location
                rx.flex(
                    rx.text("Location:", size="1", color="#9ca3af"),
                    rx.text(
                        alarm["location"],
                        size="1",
                        color="#111827",
                    ),
                    gap="1",
                    align="center",
                ),

                gap="4",
                wrap="wrap",
            ),

            spacing="2",
        ),
        padding="4",
        border_radius="md",
        bg="white",
        border="1px solid #e5e7eb",
        _hover={"border_color": "#3b82f6", "box_shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.1)"},
        width="100%",
    )
