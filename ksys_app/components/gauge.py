import reflex as rx


def radial_gauge(percent: rx.Var, value_text: rx.Var, label: rx.Var | str = "Current", color: rx.Var | str = "#2563eb", min_text: rx.Var | str | None = None, max_text: rx.Var | str | None = None, track_css: rx.Var | None = None) -> rx.Component:
    # percent: 0..100, color: stroke color
    p = percent.to_string()
    col = color if isinstance(color, str) else color.to_string()
    track = track_css.to_string() if track_css is not None else "conic-gradient(#e5e7eb 0 100%)"
    bg = rx.Var.create(f"conic-gradient({col} {p}%, transparent {p}% 100%), {track}")
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                value_text,
                class_name="w-16 h-16 rounded-full bg-white flex items-center justify-center text-sm font-semibold text-gray-700",
                style={"margin": "8px"},
            ),
            class_name="w-24 h-24 rounded-full",
            style={"background": bg},
        ),
        rx.el.div(label, class_name="text-xs text-gray-500 mt-2"),
        rx.el.div(
            rx.el.span(min_text if min_text is not None else "", class_name="text-[10px] text-gray-400 mr-1"),
            rx.el.span("~", class_name="text-[10px] text-gray-300 mr-1"),
            rx.el.span(max_text if max_text is not None else "", class_name="text-[10px] text-gray-400"),
            class_name="mt-1"
        ),
        class_name="p-4 bg-white border border-gray-200 rounded-lg flex flex-col items-center justify-center",
    )


