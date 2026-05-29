"""
week_view.py — Tab Lịch tuần (Grid 5 cột Mon-Fri).

Chức năng:
- Hiển thị lịch 1 tuần (Mon-Fri)
- Điều hướng: ◀ Tuần trước | Tuần này | Tuần sau ▶
- Hiển thị week date range
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nicegui import ui
from datetime import datetime, timedelta
from frontend import api_client
from frontend.components import common
from frontend.components.shift_card import render_shift_card_compact, render_empty_day_card


def week_view_page():
    """Tab Lịch tuần."""

    # ── State ────
    state = {
        "current_week_start": _get_monday_of_week(datetime.now()),
        "schedule": [],
    }

    def load_week_schedule():
        """Load schedule cho tuần hiện tại."""
        start_date = state["current_week_start"].strftime("%Y-%m-%d")
        state["schedule"] = api_client.get_week_schedule(start_date) or []

    load_week_schedule()

    # ── Header ────
    common.create_navbar("/lich-tuan")

    with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
        common.section_title("📅 Lịch tuần", "calendar_month")

        # ── Week navigation ────
        # Buttons dùng lambda: refresh_week() — resolve lúc click (late-binding safe)
        with ui.row().classes("items-center justify-center gap-4 mb-4"):
            ui.button(
                "◀ Tuần trước",
                on_click=lambda: (_prev_week(state), refresh_week())
            ).props("flat")

            week_end = state["current_week_start"] + timedelta(days=4)
            week_label = ui.label(
                f"{state['current_week_start'].strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}"
            ).classes("text-h6 text-blue-8 font-bold min-w-48 text-center")

            ui.button(
                "Tuần sau ▶",
                on_click=lambda: (_next_week(state), refresh_week())
            ).props("flat")

            ui.button(
                "Hôm nay 📍",
                on_click=lambda: (_today_week(state), refresh_week())
            ).props("outline color=blue")

            ui.button(
                "📥 Xuất Excel",
                on_click=lambda: ui.navigate.to(
                    api_client.get_week_export_url(
                        state["current_week_start"].strftime("%Y-%m-%d")
                    ),
                    new_tab=True,
                )
            ).props("outline color=teal")

        # ── Week container — TẠO TRƯỚC, refresh_week định nghĩa SAU ────
        # Pattern an toàn: container + label tồn tại trước khi hàm clear/re-render chúng.
        week_container = ui.column().classes("w-full")
        with week_container:
            render_week_grid(state)

    # ── Định nghĩa refresh SAU KHI week_container và week_label đã tồn tại ────
    def refresh_week():
        load_week_schedule()
        week_end = state["current_week_start"] + timedelta(days=4)
        week_label.set_text(
            f"{state['current_week_start'].strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}"
        )
        week_container.clear()
        with week_container:
            render_week_grid(state)


def _get_monday_of_week(date: datetime) -> datetime:
    """Get Monday of the week containing date."""
    return date - timedelta(days=date.weekday())


def _prev_week(state: dict):
    """Go to previous week."""
    state["current_week_start"] -= timedelta(days=7)


def _next_week(state: dict):
    """Go to next week."""
    state["current_week_start"] += timedelta(days=7)


def _today_week(state: dict):
    """Go to current week."""
    state["current_week_start"] = _get_monday_of_week(datetime.now())


def render_week_grid(state: dict):
    """Render 5-column grid: Mon-Fri."""
    weekdays = [
        ("Thứ 2 (T2)", 0),
        ("Thứ 3 (T3)", 1),
        ("Thứ 4 (T4)", 2),
        ("Thứ 5 (T5)", 3),
        ("Thứ 6 (T6)", 4),
    ]

    # ── Header row ────
    with ui.row().classes("w-full border-b-2 border-blue-8 gap-2 mb-4"):
        for day_label, _ in weekdays:
            ui.label(day_label).classes("text-h6 text-center font-bold flex-1")

    # ── Data rows ────
    with ui.row().classes("w-full gap-2"):
        for day_label, day_offset in weekdays:
            date = state["current_week_start"] + timedelta(days=day_offset)
            date_str = date.strftime("%Y-%m-%d")

            # Get shifts for this date
            shifts = [s for s in state["schedule"] if s.get("shift_date") == date_str]

            with ui.column().classes("flex-1 border border-grey-3 p-3 rounded-md bg-white"):
                # ── Date & day number ────
                ui.label(f"{date.strftime('%d/%m')}").classes("text-h6 text-blue-8 font-bold")

                # ── Shifts ────
                if shifts:
                    for shift in shifts:
                        render_shift_card_compact(shift)
                else:
                    render_empty_day_card()
