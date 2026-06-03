"""
schedule_planner.py — Tab Phân lịch (Week view với action buttons).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nicegui import ui
from datetime import datetime, timedelta
from frontend import api_client
from frontend.components import common
from frontend.components.shift_card import render_shift_card_compact, render_empty_day_card
from frontend.components.week_grid import render_week_grid


def schedule_planner_page():
    """Tab Phân lịch."""

    state = {
        "current_week_start": _get_monday_of_week(datetime.now()),
        "schedule": [],
        "holiday_map": {
            h["date"]: (h.get("label") or "Ngày lễ")
            for h in (api_client.get_special_days(day_type="holiday") or [])
        },
    }

    def load_week():
        start_date = state["current_week_start"].strftime("%Y-%m-%d")
        state["schedule"] = api_client.get_week_schedule(start_date) or []

    load_week()

    common.create_navbar("/")

    with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
        common.section_title("📋 Phân lịch trực", "calendar_month")

        # ── Week navigation ────
        with ui.row().classes("items-center justify-center gap-4 mb-4"):
            ui.button(
                "◀ Tuần trước",
                on_click=lambda: (_prev_week(state), refresh_week()),
            ).props("flat")

            week_end = state["current_week_start"] + timedelta(days=4)
            week_label = ui.label(
                f"{state['current_week_start'].strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}"
            ).classes("text-h6 text-blue-8 font-bold min-w-48 text-center")

            ui.button(
                "Tuần sau ▶",
                on_click=lambda: (_next_week(state), refresh_week()),
            ).props("flat")

            ui.button(
                "Hôm nay 📍",
                on_click=lambda: (_today_week(state), refresh_week()),
            ).props("outline color=blue")

        # ── Action buttons ────
        with ui.row().classes("gap-2 mb-4"):
            ui.button(
                "🗓️ Tính Cutoff",
                on_click=lambda: _compute_cutoff(state),
            ).props("color=orange-7")

            ui.button(
                "⚙️ Phân tuần này",
                on_click=lambda: _generate_week(state),
            ).props("color=blue-7")

            ui.button(
                "📅 Phân cả tháng",
                on_click=lambda: _generate_month(state),
            ).props("color=purple-7")

            ui.button(
                "✅ Xác nhận tuần",
                on_click=lambda: _confirm_week(state),
            ).props("color=green-7")

            ui.button(
                "📥 Xuất Excel",
                on_click=lambda: ui.navigate.to(
                    api_client.get_week_export_url(
                        state["current_week_start"].strftime("%Y-%m-%d")
                    ),
                    new_tab=True,
                ),
            ).props("outline color=teal")

            ui.button(
                "🗑️ Xóa tuần này",
                on_click=lambda: _delete_week(state),
            ).props("outline color=red")

        # ── Week grid container — created before refresh_week is defined ────
        week_container = ui.column().classes("w-full")
        with week_container:
            render_week_grid(
                state,
                on_edit_click=lambda s: _open_edit_dialog(s, state),
                on_confirm_click=lambda s: _confirm_single_shift(s["id"], state),
                on_unconfirm_click=lambda s: _unconfirm_single_shift(s["id"], state),
            )

    # ── refresh_week defined after week_container and week_label exist ────
    def refresh_week():
        load_week()
        week_end = state["current_week_start"] + timedelta(days=4)
        week_label.set_text(
            f"{state['current_week_start'].strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}"
        )
        week_container.clear()
        with week_container:
            render_week_grid(
                state,
                on_edit_click=lambda s: _open_edit_dialog(s, state),
                on_confirm_click=lambda s: _confirm_single_shift(s["id"], state),
                on_unconfirm_click=lambda s: _unconfirm_single_shift(s["id"], state),
            )

    state["refresh"] = refresh_week


def _get_monday_of_week(date: datetime) -> datetime:
    return date - timedelta(days=date.weekday())


def _prev_week(state: dict):
    state["current_week_start"] -= timedelta(days=7)


def _next_week(state: dict):
    state["current_week_start"] += timedelta(days=7)


def _today_week(state: dict):
    state["current_week_start"] = _get_monday_of_week(datetime.now())



def _compute_cutoff(state: dict):
    week_start = state["current_week_start"]
    month, year = week_start.month, week_start.year
    common.confirm_dialog(
        f"Tinh 2 ngay cutoff cho thang {month}/{year}?",
        on_confirm=lambda: _do_compute_cutoff(month, year, state),
        confirm_label="Tinh",
        confirm_color="primary",
    )


def _do_compute_cutoff(month: int, year: int, state: dict):
    result = api_client.compute_cutoff(month, year)
    if result:
        cutoff_dates = result if isinstance(result, list) else result.get("cutoff_dates", [])
        common.show_notify(f"Tinh cutoff thanh cong: {cutoff_dates}", type="positive")
        if state.get("refresh"):
            state["refresh"]()
    else:
        common.show_notify("Loi tinh cutoff", type="negative")


def _generate_week(state: dict):
    ws = state["current_week_start"]
    we = (ws + timedelta(days=4)).strftime("%d/%m/%Y")
    week_start_str = ws.strftime("%Y-%m-%d")

    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-80"):
        ui.label(f"Phân lịch tuần {ws.strftime('%d/%m')} - {we}").classes(
            "text-lg font-bold mb-2"
        )
        ow_draft = ui.checkbox("Ghi đè ca nháp (draft)")
        ow_confirmed = ui.checkbox("Ghi đè ca đã xác nhận ⚠️")

        with ui.row().classes("gap-2 mt-4 justify-end"):
            ui.button("Hủy", on_click=dlg.close).props("flat")

            def do_gen():
                dlg.close()
                result = api_client.generate_week_schedule(
                    week_start_str,
                    overwrite_draft=ow_draft.value,
                    overwrite_confirmed=ow_confirmed.value,
                )
                if result:
                    created = result.get("created", 0) if isinstance(result, dict) else 0
                    warnings = result.get("warnings", []) if isinstance(result, dict) else []
                    common.show_notify(f"Phân lịch thành công: {created} ca", type="positive")
                    # A3: Hiển thị warnings sau generate
                    if warnings:
                        if len(warnings) <= 3:
                            for w in warnings:
                                msg = w.get("msg", str(w)) if isinstance(w, dict) else str(w)
                                wtype = w.get("type", "") if isinstance(w, dict) else ""
                                icon = "🔴" if wtype in ("no_sp", "no_leader") else "⚠️"
                                common.show_notify(f"{icon} {msg}", type="warning", timeout=8000)
                        else:
                            _show_warnings_dialog(warnings)
                    if state.get("refresh"):
                        state["refresh"]()
                else:
                    common.show_notify("Lỗi phân lịch tuần", type="negative")

            ui.button("Phân lịch", on_click=do_gen).props("color=primary")

    dlg.open()


def _confirm_week(state: dict):
    ws = state["current_week_start"]
    we = (ws + timedelta(days=4)).strftime("%d/%m/%Y")
    common.confirm_dialog(
        f"Xac nhan tat ca ca trong tuan {ws.strftime('%d/%m')} - {we}?",
        on_confirm=lambda: _do_confirm_week(state),
        confirm_label="Xac nhan",
        confirm_color="primary",
    )


def _do_confirm_week(state: dict):
    week_start_str = state["current_week_start"].strftime("%Y-%m-%d")
    result = api_client.confirm_week_shifts(week_start_str)
    if result:
        common.show_notify("Xac nhan tuan thanh cong", type="positive")
        if state.get("refresh"):
            state["refresh"]()
    else:
        common.show_notify("Loi xac nhan tuan", type="negative")


def _delete_week(state: dict):
    ws = state["current_week_start"]
    we = (ws + timedelta(days=4)).strftime("%d/%m/%Y")
    common.confirm_dialog(
        f"Xóa toàn bộ ca trong tuần {ws.strftime('%d/%m')} - {we}?",
        on_confirm=lambda: _do_delete_week(state),
        confirm_label="Xóa",
    )


def _do_delete_week(state: dict):
    week_start_str = state["current_week_start"].strftime("%Y-%m-%d")
    ok = api_client.delete_week_schedule(week_start_str)
    if ok:
        common.show_notify("Đã xóa tất cả ca trong tuần", type="positive")
        if state.get("refresh"):
            state["refresh"]()
    else:
        common.show_notify("Lỗi xóa ca tuần", type="negative")


def _open_edit_dialog(shift: dict, state: dict):
    """A4: Dialog sửa tay ca trực."""
    all_staff = api_client.get_staff() or []
    ld_options = {s["id"]: s["full_name"] for s in all_staff if s.get("role") == "LD"}
    sp_options = {0: "(Bỏ trống SP)"}
    sp_options.update({s["id"]: s["full_name"] for s in all_staff if s.get("role") == "SP"})
    nv_options = {s["id"]: s["full_name"] for s in all_staff if s.get("role") == "NV"}

    current_leader_id = (shift.get("leader") or {}).get("id")
    current_sp_id = (shift.get("sp") or {}).get("id") or 0
    current_nv_ids = [nv["id"] for nv in (shift.get("nvs") or [])]

    shift_date = shift.get("shift_date", "")
    shift_type_label = shift.get("shift_type", "").replace("_", " ").title()

    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-96"):
        ui.label(f"✏️ Sửa ca {shift_type_label} — {shift_date}").classes(
            "text-lg font-bold mb-4"
        )

        sel_ld = ui.select(
            ld_options, value=current_leader_id, label="Lãnh đạo"
        ).classes("w-full mb-2")

        sel_sp = ui.select(
            sp_options, value=current_sp_id, label="Song Phương (0 = bỏ trống)"
        ).classes("w-full mb-2")

        sel_nv = ui.select(
            nv_options, value=current_nv_ids, label="Nhân viên", multiple=True
        ).classes("w-full mb-4")

        with ui.row().classes("justify-end gap-2"):
            ui.button("Hủy", on_click=dlg.close).props("flat")

            def save():
                nv_ids = sel_nv.value or []
                if isinstance(nv_ids, int):
                    nv_ids = [nv_ids]
                if not nv_ids:
                    common.show_notify("⚠️ Cần chọn ít nhất 1 NV", type="warning")
                    return
                sp_val = sel_sp.value
                result = api_client.update_shift(
                    shift["id"],
                    leader_id=sel_ld.value,
                    sp_id=sp_val if sp_val and sp_val != 0 else None,
                    clear_sp=(sp_val == 0),
                    nv_ids=nv_ids,
                )
                dlg.close()
                if result:
                    common.show_notify("Đã cập nhật ca trực", type="positive")
                    if state.get("refresh"):
                        state["refresh"]()
                else:
                    common.show_notify("Lỗi cập nhật ca", type="negative")

            ui.button("Lưu", on_click=save).props("color=primary")

    dlg.open()


def _confirm_single_shift(shift_id: int, state: dict):
    """B6: Xác nhận 1 ca trực riêng lẻ."""
    result = api_client.confirm_shift(shift_id)
    if result:
        common.show_notify("Đã xác nhận ca", type="positive")
        if state.get("refresh"):
            state["refresh"]()
    else:
        common.show_notify("Lỗi xác nhận ca", type="negative")


def _unconfirm_single_shift(shift_id: int, state: dict):
    """B5: Hủy xác nhận 1 ca trực — trả về trạng thái draft."""
    def do_unconfirm():
        result = api_client.unconfirm_shift(shift_id)
        if result:
            common.show_notify("Đã hủy xác nhận ca", type="warning")
            if state.get("refresh"):
                state["refresh"]()
        else:
            common.show_notify("Lỗi hủy xác nhận ca", type="negative")

    common.confirm_dialog(
        "Hủy xác nhận ca này? Ca sẽ trở về trạng thái Nháp.",
        on_confirm=do_unconfirm,
        confirm_label="Hủy xác nhận",
        confirm_color="orange",
    )


def _generate_month(state: dict):
    """P3: Dialog phân lịch cả tháng."""
    cur = state["current_week_start"]
    gen_state = {
        "month": cur.month,
        "year": cur.year,
        "overwrite_draft": False,
    }

    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-96"):
        ui.label("📅 Phân lịch cả tháng").classes("text-lg font-bold text-purple-7 mb-4")

        with ui.row().classes("gap-4 items-end mb-3"):
            with ui.column().classes("gap-1"):
                ui.label("Tháng:").classes("text-caption")
                ui.number(value=gen_state["month"], min=1, max=12, step=1,
                          on_change=lambda e: gen_state.update({"month": int(e.value)}),
                ).classes("w-24")
            with ui.column().classes("gap-1"):
                ui.label("Năm:").classes("text-caption")
                ui.number(value=gen_state["year"], min=2024, max=2030, step=1,
                          on_change=lambda e: gen_state.update({"year": int(e.value)}),
                ).classes("w-28")

        ui.checkbox(
            "Ghi đè ca nháp (giữ nguyên ca đã xác nhận)",
            value=False,
            on_change=lambda e: gen_state.update({"overwrite_draft": e.value}),
        ).classes("mb-2")

        result_label = ui.label("").classes("text-body2 text-green-7")

        def do_gen():
            result_label.set_text("Đang phân lịch...")
            result = api_client.generate_schedule(
                gen_state["month"], gen_state["year"],
                overwrite_draft=gen_state["overwrite_draft"],
            )
            if result:
                created = result.get("created", 0)
                skipped = result.get("skipped", 0)
                result_label.set_text(
                    f"✅ Hoàn thành: {created} ca mới, {skipped} ca bỏ qua"
                )
                common.show_notify(
                    f"Phân tháng {gen_state['month']}/{gen_state['year']}: {created} ca",
                    type="positive",
                )
                if state.get("refresh"):
                    state["refresh"]()
            else:
                result_label.set_text("❌ Có lỗi xảy ra")
                common.show_notify("Lỗi phân lịch tháng", type="negative")

        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button("Hủy", on_click=dlg.close).props("flat")
            ui.button("▶ Phân lịch", on_click=do_gen).props("color=purple-7")

    dlg.open()


def _show_warnings_dialog(warnings: list):
    """A3: Dialog tổng hợp warnings khi có nhiều hơn 3 cảnh báo."""
    with ui.dialog() as dlg_warn, ui.card().classes("p-6 min-w-96 max-w-lg"):
        ui.label("⚠️ Cảnh báo sau phân lịch").classes("text-lg font-bold text-orange-7 mb-3")
        for w in warnings:
            msg = w.get("msg", str(w)) if isinstance(w, dict) else str(w)
            wtype = w.get("type", "") if isinstance(w, dict) else ""
            icon = "🔴" if wtype in ("no_sp", "no_leader") else "⚠️"
            ui.label(f"{icon} {msg}").classes("text-body2 text-grey-8 mb-1")
        with ui.row().classes("justify-end mt-4"):
            ui.button("Đã hiểu", on_click=dlg_warn.close).props("color=orange")
    dlg_warn.open()
