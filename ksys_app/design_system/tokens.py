"""
Design Tokens - Single source of truth for design values
Based on Tailwind CSS and modern design principles
"""

from typing import Dict, Any


class DesignTokens:
    """Centralized design tokens for consistent styling"""

    # Typography
    FONT_FAMILY = {
        "heading": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "body": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "mono": "'JetBrains Mono', 'Consolas', monospace"
    }

    FONT_SIZE = {
        "xs": "12px",    # 0.75rem
        "sm": "14px",    # 0.875rem
        "md": "16px",    # 1rem (base)
        "lg": "18px",    # 1.125rem
        "xl": "20px",    # 1.25rem
        "2xl": "24px",   # 1.5rem
        "3xl": "30px",   # 1.875rem
        "4xl": "36px",   # 2.25rem
        "5xl": "48px",   # 3rem
    }

    FONT_WEIGHT = {
        "normal": "400",
        "medium": "500",
        "semibold": "600",
        "bold": "700"
    }

    LINE_HEIGHT = {
        "tight": "1.25",
        "normal": "1.5",
        "relaxed": "1.75"
    }

    # Colors - Based on Tailwind palette
    COLORS = {
        "primary": {
            "50": "#eff6ff",
            "100": "#dbeafe",
            "200": "#bfdbfe",
            "300": "#93c5fd",
            "400": "#60a5fa",
            "500": "#3b82f6",  # Main primary
            "600": "#2563eb",
            "700": "#1d4ed8",
            "800": "#1e40af",
            "900": "#1e3a8a"
        },
        "gray": {
            "50": "#f9fafb",
            "100": "#f3f4f6",
            "200": "#e5e7eb",
            "300": "#d1d5db",
            "400": "#9ca3af",
            "500": "#6b7280",
            "600": "#4b5563",
            "700": "#374151",
            "800": "#1f2937",
            "900": "#111827"
        },
        "green": {
            "50": "#f0fdf4",
            "100": "#dcfce7",
            "200": "#bbf7d0",
            "300": "#86efac",
            "400": "#4ade80",
            "500": "#10b981",  # Success
            "600": "#059669",
            "700": "#047857",
            "800": "#065f46",
            "900": "#064e3b"
        },
        "amber": {
            "50": "#fffbeb",
            "100": "#fef3c7",
            "200": "#fde68a",
            "300": "#fcd34d",
            "400": "#fbbf24",
            "500": "#f59e0b",  # Warning
            "600": "#d97706",
            "700": "#b45309",
            "800": "#92400e",
            "900": "#78350f"
        },
        "red": {
            "50": "#fef2f2",
            "100": "#fee2e2",
            "200": "#fecaca",
            "300": "#fca5a5",
            "400": "#f87171",
            "500": "#ef4444",  # Error
            "600": "#dc2626",
            "700": "#b91c1c",
            "800": "#991b1b",
            "900": "#7f1d1d"
        }
    }

    # Semantic colors
    SEMANTIC = {
        "success": COLORS["green"]["500"],
        "warning": COLORS["amber"]["500"],
        "error": COLORS["red"]["500"],
        "info": COLORS["primary"]["500"]
    }

    # Spacing scale (8px base)
    SPACING = {
        "0": "0",
        "0.5": "2px",   # 0.125rem
        "1": "4px",     # 0.25rem
        "1.5": "6px",   # 0.375rem
        "2": "8px",     # 0.5rem
        "2.5": "10px",  # 0.625rem
        "3": "12px",    # 0.75rem
        "3.5": "14px",  # 0.875rem
        "4": "16px",    # 1rem
        "5": "20px",    # 1.25rem
        "6": "24px",    # 1.5rem
        "7": "28px",    # 1.75rem
        "8": "32px",    # 2rem
        "9": "36px",    # 2.25rem
        "10": "40px",   # 2.5rem
        "12": "48px",   # 3rem
        "14": "56px",   # 3.5rem
        "16": "64px",   # 4rem
        "20": "80px",   # 5rem
        "24": "96px",   # 6rem
    }

    # Border radius
    BORDER_RADIUS = {
        "none": "0",
        "sm": "2px",    # 0.125rem
        "md": "6px",    # 0.375rem
        "lg": "8px",    # 0.5rem
        "xl": "12px",   # 0.75rem
        "2xl": "16px",  # 1rem
        "3xl": "24px",  # 1.5rem
        "full": "9999px"
    }

    # Shadows
    SHADOWS = {
        "none": "none",
        "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        "2xl": "0 25px 50px -12px rgba(0, 0, 0, 0.25)"
    }

    # Transitions
    TRANSITIONS = {
        "fast": "150ms cubic-bezier(0.4, 0, 0.2, 1)",
        "normal": "250ms cubic-bezier(0.4, 0, 0.2, 1)",
        "slow": "350ms cubic-bezier(0.4, 0, 0.2, 1)"
    }

    # Breakpoints (for responsive design)
    BREAKPOINTS = {
        "sm": "640px",
        "md": "768px",
        "lg": "1024px",
        "xl": "1280px",
        "2xl": "1536px"
    }

    @classmethod
    def get_color(cls, color_path: str) -> str:
        """
        Get color by path (e.g., 'primary.500', 'gray.200')

        Args:
            color_path: Color path in format 'category.shade'

        Returns:
            Hex color code
        """
        parts = color_path.split(".")
        if len(parts) == 2:
            category, shade = parts
            return cls.COLORS.get(category, {}).get(shade, "#000000")
        return "#000000"

    @classmethod
    def get_spacing(cls, key: str) -> str:
        """Get spacing value by key"""
        return cls.SPACING.get(key, "0")

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Export all tokens as dictionary"""
        return {
            "typography": {
                "fontFamily": cls.FONT_FAMILY,
                "fontSize": cls.FONT_SIZE,
                "fontWeight": cls.FONT_WEIGHT,
                "lineHeight": cls.LINE_HEIGHT
            },
            "colors": cls.COLORS,
            "semantic": cls.SEMANTIC,
            "spacing": cls.SPACING,
            "borderRadius": cls.BORDER_RADIUS,
            "shadows": cls.SHADOWS,
            "transitions": cls.TRANSITIONS,
            "breakpoints": cls.BREAKPOINTS
        }
