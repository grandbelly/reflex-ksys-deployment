import reflex as rx

from ..states.dashboard import DashboardState as D


def _fmt_num(v: rx.Var, digits: int) -> rx.Var:
    vs = v.to_string()
    return rx.Var.create(f"(isFinite(Number({vs})) ? Number({vs}).toFixed({digits}) : '0')")


def _fmt_ts(v: rx.Var) -> rx.Var:
    # Render as 'YYYY-MM-DD HH:mm:ss+09:00' in Asia/Seoul (align with Measurement history)
    vs = v.to_string()
    return rx.Var.create(
        "(new Date(" + vs + ")).toLocaleString('sv-SE', { timeZone: 'Asia/Seoul', hour12: false }) + '+09:00'"
    )


def indicators_table() -> rx.Component:
    return rx.card(
        rx.flex(
            rx.heading("Technical Indicators", size="4", weight="bold"),
            rx.badge("Moving Averages & Bands", color_scheme="purple"),
            justify="between",
            align="center",
            class_name="mb-4",
        ),
        
        rx.cond(
            D.indicators_for_tag_desc,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("No.", justify="end"),
                        rx.table.column_header_cell("TAG"),
                        rx.table.column_header_cell("Timestamp"),
                        rx.table.column_header_cell("Average", justify="end"),
                        rx.table.column_header_cell("SMA 10", justify="end"),
                        rx.table.column_header_cell("SMA 60", justify="end"),
                        rx.table.column_header_cell("BB Top", justify="end"),
                        rx.table.column_header_cell("BB Bottom", justify="end"),
                        rx.table.column_header_cell("Slope 60", justify="end"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        D.indicators_for_tag_desc_with_num,
                        lambda r: rx.table.row(
                            rx.table.cell(r.get("num"), justify="end"),
                            rx.table.cell(
                                rx.badge(r["tag_name"], variant="soft", color_scheme="purple")
                            ),
                            rx.table.cell(r.get("bucket_s")),
                            rx.table.cell(r["avg_s"], justify="end"),
                            rx.table.cell(r["sma_10_s"], justify="end"),
                            rx.table.cell(r["sma_60_s"], justify="end"),
                            rx.table.cell(r["bb_top_s"], justify="end"),
                            rx.table.cell(r["bb_bot_s"], justify="end"),
                            rx.table.cell(r["slope_60_s"], justify="end"),
                        ),
                    ),
                ),
                variant="surface",
                size="2",
            ),
            rx.flex(
                rx.icon("trending-up", size=48, color="gray"),
                rx.text("No indicators data available", size="3", color="gray"),
                direction="column",
                align="center",
                gap="3",
                class_name="py-12",
            ),
        ),
        class_name="w-full min-h-[400px] max-h-[600px] overflow-auto",
    )


