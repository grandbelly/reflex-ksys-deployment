import reflex as rx


def _badge(status: str):
    icon_map = {
        "Completed": ("check", "green"),
        "Pending": ("loader", "yellow"),
        "Canceled": ("ban", "red"),
    }
    icon, color = icon_map.get(status, ("loader", "yellow"))
    label = status if status else "Pending"
    return rx.badge(
        rx.icon(icon, size=16),
        label,
        color_scheme=color,
        radius="large",
        variant="surface",
        size="2",
    )


def status_badge(status):
    # Use rx.match to avoid Python truthiness on Vars
    return rx.match(
        status,
        ("Completed", _badge("Completed")),
        ("Pending", _badge("Pending")),
        ("Canceled", _badge("Canceled")),
        _badge("Pending"),
    )


