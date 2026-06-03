"""
week_grid.py — Component lịch tuần dùng chung (B1: DRY refactor).

Dùng trong:
  - schedule_planner.py: show_warnings=True, on_edit_click=..., on_confirm_click=..., on_unconfirm_click=...
  - week_view.py: show_warnings=True (read-only)
"""
from nicegui import ui
from datetime import timedelta

from frontend.components import common
from frontend.components.shift_card import render_shift_card_compact, render_empty_day_card


_WEEKDAYS = [
    ("Thứ 2 (T2)", 0),
    ("Thứ 3 (T3)", 1),
    ("Thứ 4 (T4)", 2),
    ("Thứ 5 (T5)", 3),
    ("Thứ 6 (T6)", 4),
]


def render_week_grid(
    state: dict,
    show_warnings: bool = True,
    on_edit_click=None,
    on_confirm_click=None,
    on_unconfirm_click=None,
):
    """
    Render grid 5 cột Mon-Fri từ state["schedule"] và state["current_week_start"].

    state cần có:
      - current_week_start: datetime
      - schedule: List[dict] của shifts

    show_warnings: Hiển thị sp_warning badge dưới mỗi shift card.
    on_edit_click: Callback (shift) -> None — hiện nút ✏️ trong compact card.
    on_confirm_click: Callback (shift) -> None — hiện nút ✅ cho ca draft.
    on_unconfirm_click: Callback (shift) -> None — hiện nút 🔄 cho ca confirmed (B5).
    """
    week_start = state["current_week_start"]

    # ── Header row ────
    with ui.row().classes("w-full border-b-2 border-blue-8 gap-2 mb-4"):
        for day_label, _ in _WEEKDAYS:
            ui.label(day_label).classes("text-h6 text-center font-bold flex-1")

    # ── Data rows ────
    with ui.row().classes("w-full gap-2"):
        for _, day_offset in _WEEKDAYS:
            col_date = week_start + timedelta(days=day_offset)
            date_str = col_date.strftime("%Y-%m-%d")
            shifts = [s for s in state["schedule"] if s.get("shift_date") == date_str]

            with ui.column().classes("flex-1 border border-grey-3 p-3 rounded-md bg-white"):
                ui.label(col_date.strftime("%d/%m")).classes("text-h6 text-blue-8 font-bold")

                if shifts:
                    for shift in shifts:
                        render_shift_card_compact(
                            shift,
                            on_edit_click=on_edit_click,
                            on_confirm_click=on_confirm_click,
                            on_unconfirm_click=on_unconfirm_click,
                        )
                        if show_warnings and shift.get("sp_warning"):
                            warn_label, warn_color = common.SP_WARNING_LABELS.get(
                                shift["sp_warning"], (shift["sp_warning"], "grey")
                            )
                            ui.badge(warn_label, color=warn_color).classes("text-xs")
                else:
                    # N5: phân biệt ngày lễ vs chưa phân ca
                    holiday_label = state.get("holiday_map", {}).get(date_str)
                    if holiday_label:
                        with ui.column().classes("items-center justify-center py-4 gap-1"):
                            ui.icon("celebration").classes("text-h5 text-grey-5")
                            ui.label(holiday_label).classes(
                                "text-caption text-grey-6 italic text-center"
                            )
                    else:
                        render_empty_day_card()
