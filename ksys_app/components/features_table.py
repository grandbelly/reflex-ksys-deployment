import reflex as rx

from ..states.dashboard import DashboardState as D


def _fmt_num(v: rx.Var, digits: int) -> rx.Var:
    # 숫자가 아니면 0으로 표시, 숫자면 지정 소수점
    vs = v.to_string()
    return rx.Var.create(f"(isFinite(Number({vs})) ? Number({vs}).toFixed({digits}) : '0')")


def _fmt_ts(v: rx.Var) -> rx.Var:
    # Render as 'YYYY-MM-DD HH:mm:ss+09:00' in Asia/Seoul
    return rx.Var.create(
        "(new Date(" + v.to_string() + ")).toLocaleString('sv-SE', { timeZone: 'Asia/Seoul', hour12: false }) + '+09:00'"
    )


def features_table() -> rx.Component:
    return rx.card(
        rx.flex(
            rx.heading("History", size="4", weight="bold"),
            rx.badge("Historical Data", color_scheme="green"),
            justify="between",
            align="center",
            class_name="mb-4",
        ),
        
        rx.cond(
            D.series_for_tag_desc_with_num,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("No.", justify="end"),
                        rx.table.column_header_cell("TAG"),
                        rx.table.column_header_cell("Timestamp"),
                        rx.table.column_header_cell("Average", justify="end"),
                        rx.table.column_header_cell("Min", justify="end"),
                        rx.table.column_header_cell("Max", justify="end"),
                        rx.table.column_header_cell("Last", justify="end"),
                        rx.table.column_header_cell("First", justify="end"),
                        rx.table.column_header_cell("Count", justify="end"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        D.series_for_tag_desc_with_num,
                        lambda r: rx.table.row(
                            rx.table.cell(r.get("num"), justify="end"),
                            rx.table.cell(
                                rx.badge(r["tag_name"], variant="soft", color_scheme="blue")
                            ),
                            rx.table.cell(r["bucket"]),
                            rx.table.cell(r["avg_s"], justify="end"),
                            rx.table.cell(r["min_s"], justify="end"),
                            rx.table.cell(r["max_s"], justify="end"),
                            rx.table.cell(r["last_s"], justify="end"),
                            rx.table.cell(r["first_s"], justify="end"),
                            rx.table.cell(r["n_s"], justify="end"),
                        ),
                    ),
                ),
                variant="surface",
                size="2",
            ),
            rx.flex(
                rx.icon("database", size=48, color="gray"),
                rx.text("No measurement data available", size="3", color="gray"),
                direction="column",
                align="center",
                gap="3",
                class_name="py-12",
            ),
        ),
        class_name="w-full min-h-[400px] max-h-[600px] overflow-auto",
    )


