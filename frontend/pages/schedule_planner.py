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


def schedule_planner_page():
    """Tab Phân lịch."""

    state = {
        "current_week_start": _get_monday_of_week(datetime.now()),
        "schedule": [],
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
            _render_week_grid(state)

    # ── refresh_week defined after week_container and week_label exist ────
    def refresh_week():
        load_week()
        week_end = state["current_week_start"] + timedelta(days=4)
        week_label.set_text(
            f"{state['current_week_start'].strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}"
        )
        week_container.clear()
        with week_container:
            _render_week_grid(state)

    state["refresh"] = refresh_week


def _get_monday_of_week(date: datetime) -> datetime:
    return date - timedelta(days=date.weekday())


def _prev_week(state: dict):
    state["current_week_start"] -= timedelta(days=7)


def _next_week(state: dict):
    state["current_week_start"] += timedelta(days=7)


def _today_week(state: dict):
    state["current_week_start"] = _get_monday_of_week(datetime.now())


def _render_week_grid(state: dict):
    """Render 5-column grid Mon-Fri."""
    weekdays = [
        ("Thứ 2 (T2)", 0),
        ("Thứ 3 (T3)", 1),
        ("Thứ 4 (T4)", 2),
        ("Thứ 5 (T5)", 3),
        ("Thứ 6 (T6)", 4),
    ]

    with ui.row().classes("w-full border-b-2 border-blue-8 gap-2 mb-4"):
        for day_label, _ in weekdays:
            ui.label(day_label).classes("text-h6 text-center font-bold flex-1")

    with ui.row().classes("w-full gap-2"):
        for day_label, day_offset in weekdays:
            col_date = state["current_week_start"] + timedelta(days=day_offset)
            date_str = col_date.strftime("%Y-%m-%d")
            shifts = [s for s in state["schedule"] if s.get("shift_date") == date_str]

            with ui.column().classes("flex-1 border border-grey-3 p-3 rounded-md bg-white"):
                ui.label(col_date.strftime("%d/%m")).classes("text-h6 text-blue-8 font-bold")
                if shifts:
                    for shift in shifts:
                        render_shift_card_compact(shift)
                        if shift.get("sp_warning"):
                            warn_label, warn_color = common.SP_WARNING_LABELS.get(
                                shift["sp_warning"], (shift["sp_warning"], "grey")
                            )
                            ui.badge(warn_label, color=warn_color).classes("text-xs")
                else:
                    render_empty_day_card()


def _compute_cutoff(state: dict):
    week_start = state["current_week_start"]
    month, year = week_start.month, week_start.year
    common.confirm_dialog(
        f"Tinh 2 ngay cutoff cho thang {month}/{year}?",
        on_confirm=lambda: _do_compute_cutoff(month, year, state),
        confirm_label="Tinh",
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
                    common.show_notify(f"Phân lịch thành công: {created} ca", type="positive")
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
