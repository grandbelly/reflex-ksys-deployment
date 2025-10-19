"""
Improved time range selector components
"""
import reflex as rx
from ..config.time_ranges import TIME_RANGES, QUICK_PRESETS
from typing import Callable


def time_range_dropdown(value: str, on_change: Callable) -> rx.Component:
    """Simplified time range dropdown"""
    return rx.el.select(
        *[
            rx.el.option(tr["label"], value=tr["value"]) 
            for tr in TIME_RANGES
        ],
        value=value,
        on_change=on_change,
        class_name="bg-white text-gray-900 px-3 py-2 rounded-lg border-2 border-blue-200 w-32 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-sm",
    )


def quick_time_buttons(selected: str, on_change: Callable) -> rx.Component:
    """Quick time selection buttons like stock charts"""
    return rx.hstack(
        *[
            rx.button(
                preset["label"],
                size="1",
                variant="solid" if selected == preset["value"] else "soft",
                color_scheme="blue" if selected == preset["value"] else "gray",
                on_click=lambda v=preset["value"]: on_change(v),
                class_name="min-w-[45px]",
            )
            for preset in QUICK_PRESETS
        ],
        spacing="1",
    )


def enhanced_time_selector(value: str, on_change: Callable) -> rx.Component:
    """Enhanced time selector with both buttons and dropdown"""
    return rx.vstack(
        # Quick select buttons
        rx.box(
            quick_time_buttons(value, on_change),
            class_name="hidden md:block",  # Show on desktop only
        ),
        
        # Dropdown for mobile or additional options
        rx.box(
            time_range_dropdown(value, on_change),
            class_name="block md:hidden",  # Show on mobile only
        ),
        
        spacing="2",
        width="100%",
    )


def time_selector_with_icon(value: str, on_change: Callable) -> rx.Component:
    """Time selector with icon and label"""
    return rx.flex(
        rx.icon("clock", size=16, color="gray"),
        rx.text("조회기간", size="2", weight="medium", color="gray"),
        time_range_dropdown(value, on_change),
        spacing="2",
        align="center",
    )