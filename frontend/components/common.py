"""
Common UI components và constants cho frontend.
"""
from nicegui import ui

# ── Constants ─────────────────────────────────────────────────────────────────
ROLE_LABELS = {"LD": "Lãnh đạo", "SP": "Song Phương", "NV": "Nhân viên"}
ROLE_COLORS = {"LD": "blue-7", "SP": "purple-7", "NV": "green-7"}

SHIFT_TYPE_LABELS = {
    "normal": ("Ca thường", "grey-7"),
    "friday": ("Thứ Sáu", "orange-7"),
    "cutoff": ("Cut-off", "red-7"),
    "settlement_main": ("Quyết toán chính", "deep-purple-7"),
    "settlement_sub": ("Quyết toán phụ", "deep-purple-4"),
}

SP_WARNING_LABELS = {
    "leader_sp": ("⚠️ LĐ kiêm SP", "orange"),
    "no_sp": ("🔴 Thiếu SP", "red"),
}

DOW_LABELS = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6"}

VN_WEEKDAY = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


# ── Navbar ────────────────────────────────────────────────────────────────────
def create_navbar(current: str = ""):
    nav_items = [
        ("📋 Phân lịch",  "/"),
        ("👥 Danh sách",  "/danh-sach"),
        ("📅 Lịch tuần",  "/lich-tuan"),
        ("📊 Thống kê",   "/thong-ke"),
        ("⚙️ Cài đặt",    "/cai-dat"),
    ]
    with ui.header().classes("bg-blue-8 text-white q-px-md"):
        with ui.row().classes("items-center w-full gap-2"):
            ui.label("🏦 Phân lịch trực — PTT").classes("text-h6 font-bold mr-4")
            for label, path in nav_items:
                is_active = (current == path)
                btn = ui.button(label, on_click=lambda p=path: ui.navigate.to(p))
                btn.classes(
                    "text-white font-bold" if is_active
                    else "text-white"
                )
                btn.props("flat")
                if is_active:
                    btn.classes("underline")


# ── Notifications ─────────────────────────────────────────────────────────────
def show_notify(msg: str, type: str = "positive", timeout: int = 3000):
    ui.notify(msg, type=type, timeout=timeout, position="top-right")


# ── Confirm dialog ────────────────────────────────────────────────────────────
def confirm_dialog(message: str, on_confirm, confirm_label: str = "Xác nhận",
                   cancel_label: str = "Hủy", confirm_color: str = "negative"):
    # T2: confirm_color param — destructive actions dùng "negative", tích cực dùng "primary"
    with ui.dialog() as dialog, ui.card().classes("p-4 min-w-[300px]"):
        ui.label(message).classes("text-body1 mb-4")
        with ui.row().classes("justify-end gap-2"):
            ui.button(cancel_label, on_click=dialog.close).props("flat")
            ui.button(confirm_label, on_click=lambda: (on_confirm(), dialog.close())).props(
                f"color={confirm_color}"
            )
    dialog.open()


# ── Section title ─────────────────────────────────────────────────────────────
def section_title(text: str, icon: str = ""):
    with ui.row().classes("items-center gap-2 mb-2"):
        if icon:
            ui.icon(icon).classes("text-blue-7")
        ui.label(text).classes("text-h6 text-blue-8 font-bold")


# ── Month/Year selector ───────────────────────────────────────────────────────
def month_year_selector(state: dict, on_change=None):
    """
    Render month + year selectors. state phải có keys 'month', 'year'.
    """
    months = {m: f"Tháng {m}" for m in range(1, 13)}
    years = {y: str(y) for y in range(2024, 2030)}

    with ui.row().classes("items-center gap-3"):
        ui.label("Tháng:").classes("text-body2")
        month_sel = ui.select(
            options=months, value=state["month"],
            on_change=lambda e: _on_month_change(e, state, on_change)
        ).classes("w-32")

        ui.label("Năm:").classes("text-body2")
        year_sel = ui.select(
            options=years, value=state["year"],
            on_change=lambda e: _on_year_change(e, state, on_change)
        ).classes("w-24")

    return month_sel, year_sel


def _on_month_change(e, state, callback):
    state["month"] = e.value
    if callback:
        callback()


def _on_year_change(e, state, callback):
    state["year"] = e.value
    if callback:
        callback()
