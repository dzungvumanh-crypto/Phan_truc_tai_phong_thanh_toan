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
from frontend import api_client


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
        
        # ── Song Phương ────
        sp = shift.get("sp")
        sp_warning = shift.get("sp_warning")
        
        if sp:
            with ui.row().classes("items-center gap-1"):
                ui.icon("person", size="xs")
                ui.chip(
                    sp.get("full_name", "—"),
                    removable=False
                ).classes("text-purple-7 bg-purple-1 text-xs")
            if sp_warning:
                warn_label, warn_color = SP_WARNING_LABELS.get(sp_warning, (sp_warning, "grey"))
                ui.badge(warn_label, color=warn_color).classes("text-xs")
        else:
            with ui.row().classes("items-center"):
                if sp_warning:
                    warn_label, warn_color = SP_WARNING_LABELS.get(sp_warning, (sp_warning, "grey"))
                    ui.badge(warn_label, color=warn_color).classes("text-xs")
                else:
                    ui.label("(Không có SP)").classes("text-xs text-orange-7 italic")
        
        # ── Nhân viên ────
        nvs = shift.get("nvs", [])
        if nvs:
            with ui.row().classes("flex-wrap gap-1 mt-2"):
                for nv in nvs:
                    ui.chip(
                        nv.get("full_name", "—"),
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


def render_shift_card_compact(shift: dict):
    """
    Render compact version cho calendar/tuần view.
    Hiển thị tên LĐ, SP và danh sách tên NV.
    """
    leader = shift.get("leader") or {}
    sp = shift.get("sp") or {}
    nvs = shift.get("nvs") or []

    leader_name = leader.get("full_name", "?")
    sp_name = sp.get("full_name", "—")

    # Hiển thị tên NV — rút gọn nếu quá nhiều (tối đa 3 người + "...")
    nv_names_list = [nv.get("full_name", "?") for nv in nvs]
    if len(nv_names_list) > 3:
        nv_text = ", ".join(nv_names_list[:3]) + f" (+{len(nv_names_list)-3})"
    else:
        nv_text = ", ".join(nv_names_list) if nv_names_list else "—"

    with ui.column().classes("gap-0"):
        ui.label(leader_name).classes("text-xs text-blue-8 font-medium")
        ui.label(sp_name).classes("text-xs text-purple-7")
        ui.label(nv_text).classes("text-xs text-green-8")


def render_empty_day_card():
    """Render ô ngày trống (không có ca trực)."""
    with ui.card().classes("p-3 bg-grey-1 border border-dashed border-grey-3 rounded-md"):
        ui.label("(Trống)").classes("text-xs text-grey-6 text-center")
