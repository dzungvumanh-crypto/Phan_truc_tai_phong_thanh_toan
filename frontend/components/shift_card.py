"""
shift_card.py — Component hiển thị 1 ô ca trực (shift).

Hiển thị: LĐ (badge blue), SP (badge purple), NV list (green chips)
         + badge loại ca (normal/friday/cutoff/settlement)
         + warning badges (leader_sp / no_sp)
"""
from nicegui import ui
from frontend.components.common import (
    ROLE_LABELS, ROLE_COLORS, SHIFT_TYPE_LABELS, SP_WARNING_LABELS
)


def render_shift_card(shift: dict, on_edit_click=None):
    """
    Render 1 ô ca trực.
    
    shift schema:
    {
        "id": int,
        "shift_date": "YYYY-MM-DD",
        "shift_type": "normal" | "friday" | "cutoff" | "settlement_main" | "settlement_sub",
        "leader": {"id": int, "full_name": str, "role": "LD"},
        "sp": {"id": int, "full_name": str, "role": "SP"} | None,
        "sp_warning": None | "leader_sp" | "no_sp",
        "nvs": [{"id": int, "full_name": str, "role": "NV"}, ...],
        "nv_count": int,
        "status": "draft" | "confirmed"
    }
    """
    with ui.card().classes("p-3 bg-white border border-grey-3 rounded-md shadow-sm"):
        
        # ── Loại ca (badge) ────
        shift_type = shift.get("shift_type", "normal")
        label, color = SHIFT_TYPE_LABELS.get(shift_type, (shift_type, "grey"))
        ui.badge(label, color=color).classes("text-xs")
        
        # ── Lãnh đạo ────
        leader = shift.get("leader")
        if leader:
            with ui.row().classes("items-center gap-1 mt-2"):
                ui.icon("person", size="xs")
                ui.chip(
                    leader.get("full_name", "—"),
                    removable=False
                ).classes("text-blue-7 bg-blue-1 text-xs")
        else:
            ui.label("(Chưa có LĐ)").classes("text-xs text-red-7 italic")
        
        # ── Nhan vien (gop SP person + NV thuong) ────
        sp = shift.get("sp")
        sp_warning = shift.get("sp_warning")
        nvs = shift.get("nvs", [])
        all_nv = ([sp] if sp else []) + nvs
        if all_nv:
            with ui.row().classes("flex-wrap gap-1 mt-2"):
                for person in all_nv:
                    ui.chip(
                        person.get("full_name", "—"),
                        removable=False
                    ).classes("text-green-7 bg-green-1 text-xs")
        # ── Trạng thái & Edit button ────
        status = shift.get("status", "draft")
        status_color = "green" if status == "confirmed" else "orange"
        
        with ui.row().classes("items-center justify-between mt-2"):
            ui.badge(
                "✓ Xác nhận" if status == "confirmed" else "📝 Nháp",
                color=status_color
            ).classes("text-xs")
            
            if on_edit_click:
                ui.button(
                    "Sửa",
                    on_click=lambda: on_edit_click(shift)
                ).props("size=xs flat dense color=blue-7")


def _shift_has_staff(shift: dict, staff_id: int) -> bool:
    """C2: Kiểm tra ca có chứa staff_id (với vai trò LĐ, SP hoặc NV) không."""
    leader = shift.get("leader") or {}
    sp = shift.get("sp") or {}
    nvs = shift.get("nvs") or []
    return (
        leader.get("id") == staff_id
        or sp.get("id") == staff_id
        or any(nv.get("id") == staff_id for nv in nvs)
    )


def render_shift_card_compact(shift: dict, on_edit_click=None,
                              on_confirm_click=None, on_unconfirm_click=None,
                              highlight_staff_id=None):
    """
    Render compact version cho calendar/tuần view.
    Hiển thị tên LĐ, SP và danh sách tên NV.
    A4: on_edit_click — callback khi click nút ✏️ Sửa
    B6: on_confirm_click — callback khi click nút ✅ (chỉ hiện khi ca ở trạng thái draft)
    B5: on_unconfirm_click — callback khi click nút 🔄 (chỉ hiện khi ca ở trạng thái confirmed)
    C2: highlight_staff_id — highlight ca có người này, mờ ca không có
    """
    leader = shift.get("leader") or {}
    sp = shift.get("sp") or {}
    nvs = shift.get("nvs") or []
    sp_warning = shift.get("sp_warning")

    leader_name = leader.get("full_name", "?")

    # Gop SP person (neu co) + NV thuong thanh 1 danh sach nhan vien
    all_nv = ([sp.get("full_name", "?")] if sp else []) + [nv.get("full_name", "?") for nv in nvs]
    if len(all_nv) > 3:
        nv_text = ", ".join(all_nv[:3]) + f" (+{len(all_nv)-3})"
    else:
        nv_text = ", ".join(all_nv) if all_nv else "—"

    # C2: Xac dinh trang thai highlight/dim
    col_classes = "gap-0"
    if highlight_staff_id is not None:
        if _shift_has_staff(shift, highlight_staff_id):
            col_classes += " rounded p-1 bg-blue-1 outline outline-2 outline-blue-5"
        else:
            col_classes += " opacity-30"

    with ui.column().classes(col_classes):
        ui.label(leader_name).classes("text-xs text-blue-8 font-medium")
        ui.label(nv_text).classes("text-xs text-green-8")

        # A4 + B6 + B5: Nút hành động compact
        has_action = (
            on_edit_click
            or (on_confirm_click and shift.get("status") == "draft")
            or (on_unconfirm_click and shift.get("status") == "confirmed")
        )
        if has_action:
            with ui.row().classes("gap-1 mt-1"):
                if on_confirm_click and shift.get("status") == "draft":
                    ui.button(
                        "✅",
                        on_click=lambda s=shift: on_confirm_click(s),
                    ).props("size=xs flat dense color=green-7").tooltip("Xác nhận ca này")
                if on_unconfirm_click and shift.get("status") == "confirmed":
                    ui.button(
                        "🔄",
                        on_click=lambda s=shift: on_unconfirm_click(s),
                    ).props("size=xs flat dense color=orange-7").tooltip("Huỷ xác nhận ca này")
                if on_edit_click:
                    ui.button(
                        "✏️",
                        on_click=lambda s=shift: on_edit_click(s),
                    ).props("size=xs flat dense color=blue-7").tooltip("Sửa ca")


def render_empty_day_card():
    """Render ô ngày trống (không có ca trực)."""
    with ui.card().classes("p-3 bg-grey-1 border border-dashed border-grey-3 rounded-md"):
        ui.label("(Trống)").classes("text-xs text-grey-6 text-center")
