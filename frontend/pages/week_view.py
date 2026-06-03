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
from frontend.components.week_grid import render_week_grid


def week_view_page():
    """Tab Lịch tuần."""

    # ── State ────
    state = {
        "current_week_start": _get_monday_of_week(datetime.now()),
        "schedule": [],
        "holiday_map": {
            h["date"]: (h.get("label") or "Ngày lễ")
            for h in (api_client.get_special_days(day_type="holiday") or [])
        },
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


# render_week_grid đã được tách sang frontend/components/week_grid.py (B1 DRY refactor)
