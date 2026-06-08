"""
statistics.py — Tab Thống kê (/thong-ke).

3 section:
  1. Thống kê số ca từng người (breakdown by type) — theo năm
  2. Tóm tắt tháng (total_shifts, by_type)
  3. Trạng thái vòng xoay (rotation_state) — lọc theo role
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nicegui import ui
from datetime import datetime
from frontend import api_client
from frontend.components import common


# Thứ tự hiển thị role: LD → NV
_ROLE_ORDER = {"LD": 0, "NV": 1}

# Nhãn các loại vòng xoay
_ROTATION_ROLE_OPTIONS = {
    None:         "Tất cả",
    "LD":         "LD",
    "NV":         "NV",
    "LD_friday":  "LD Thứ 6",
    "NV_friday":  "NV Thứ 6",
    "LD_cutoff":  "LD Cutoff",
    "NV_cutoff":  "NV Cutoff",
}


def statistics_page():
    """Tab Thống kê."""

    # ── State ────
    state = {
        "year":   datetime.now().year,
        "month":  datetime.now().month,
        "shift_counts":    [],
        "monthly_summary": None,
        "rotation_data":   [],
        "rotation_role_filter": None,
    }

    # ── Load functions ────
    def load_shift_counts():
        state["shift_counts"] = api_client.get_shift_count(state["year"]) or []

    def load_monthly_summary():
        state["monthly_summary"] = api_client.get_monthly_summary(
            state["month"], state["year"]
        )

    def load_rotation():
        state["rotation_data"] = api_client.get_rotation_state(
            state["year"],
            role=state["rotation_role_filter"]
        ) or []

    def load_all():
        load_shift_counts()
        load_monthly_summary()
        load_rotation()

    load_all()

    # ── Header ────
    common.create_navbar("/thong-ke")

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-6"):
        common.section_title("📊 Thống kê ca trực", "bar_chart")

        # ── Controls row ────
        with ui.row().classes("items-center gap-3 mb-2"):
            ui.label("Năm:").classes("text-body2")
            ui.select(
                options={y: str(y) for y in range(2024, 2030)},
                value=state["year"],
                on_change=lambda e: (
                    state.update({"year": e.value}),
                    load_all(),
                    render_section1(state),
                    render_section2(state),
                    render_section3(state),
                )
            ).classes("w-24")

            ui.button(
                "🔄 Làm mới",
                on_click=lambda: (
                    load_all(),
                    render_section1(state),
                    render_section2(state),
                    render_section3(state),
                )
            ).props("flat color=blue-7")

        # ── Section 1: Thống kê theo người ────
        common.section_title("👤 Số ca theo từng người", "people")
        section1_container = ui.column().classes("w-full")

        # ── Section 2: Tóm tắt tháng ────
        common.section_title("📆 Tóm tắt tháng", "calendar_today")

        with ui.row().classes("items-center gap-3"):
            ui.label("Tháng:").classes("text-body2")
            ui.select(
                options={m: f"Tháng {m}" for m in range(1, 13)},
                value=state["month"],
                on_change=lambda e: (
                    state.update({"month": e.value}),
                    load_monthly_summary(),
                    render_section2(state),
                )
            ).classes("w-32")

        section2_container = ui.column().classes("w-full")

        # ── Section 3: Vòng xoay ────
        common.section_title("🔄 Trạng thái vòng xoay", "sync")

        with ui.row().classes("items-center gap-3"):
            ui.label("Lọc loại:").classes("text-body2")
            ui.select(
                options=_ROTATION_ROLE_OPTIONS,
                value=None,
                on_change=lambda e: (
                    state.update({"rotation_role_filter": e.value}),
                    load_rotation(),
                    render_section3(state),
                )
            ).classes("w-36")

        section3_container = ui.column().classes("w-full")

    # ── Render functions ────
    def render_section1(s: dict):
        section1_container.clear()
        with section1_container:
            _render_shift_count_chart(s)
            _render_shift_count_table(s)

    def render_section2(s: dict):
        section2_container.clear()
        with section2_container:
            _render_monthly_summary(s)

    def render_section3(s: dict):
        section3_container.clear()
        with section3_container:
            _render_rotation_table(s)

    # Initial render
    render_section1(state)
    render_section2(state)
    render_section3(state)


# ── Section 1 helpers ──────────────────────────────────────────────────────────

# Màu theo role cho bar chart
_ROLE_COLORS_CHART = {"LD": "#1976D2", "NV": "#388E3C"}


def _render_shift_count_chart(state: dict):
    """B4: Biểu đồ bar chart ngang — so sánh số ca từng người."""
    data = [d for d in state.get("shift_counts", []) if d.get("total", 0) > 0]
    if not data:
        return

    data.sort(key=lambda x: (_ROLE_ORDER.get(x.get("role"), 99), -x.get("total", 0)))
    avg = sum(d["total"] for d in data) / len(data)
    names = [d["full_name"] for d in data]
    totals = [d["total"] for d in data]
    colors = [_ROLE_COLORS_CHART.get(d.get("role"), "#9E9E9E") for d in data]

    opt = {
        "grid": {"left": "180px", "right": "60px", "top": "20px", "bottom": "30px"},
        "xAxis": {"type": "value", "name": "Số ca"},
        "yAxis": {"type": "category", "data": names, "axisLabel": {"fontSize": 11}},
        "series": [{
            "type": "bar",
            "data": [{"value": v, "itemStyle": {"color": c}} for v, c in zip(totals, colors)],
            "markLine": {
                "data": [{"xAxis": round(avg, 1), "name": f"TB: {avg:.1f}"}],
                "label": {"formatter": f"TB: {avg:.1f}"},
            },
            "label": {"show": True, "position": "right", "fontSize": 11},
        }],
        "tooltip": {"trigger": "axis"},
    }
    ui.echart(opt).classes("w-full").style("height: 400px")


def _render_shift_count_table(state: dict):
    """Bảng số ca từng người, nhóm theo role."""
    data = state.get("shift_counts", [])

    if not data:
        ui.label("(Chưa có dữ liệu)").classes("text-grey-6 italic")
        return

    # Sort: LD → SP → NV, rồi theo tên
    sorted_data = sorted(
        data,
        key=lambda x: (_ROLE_ORDER.get(x.get("role", "NV"), 99), x.get("full_name", ""))
    )

    # Header
    with ui.row().classes("w-full border-b-2 border-blue-8 pb-1 px-2"):
        ui.label("Tên").classes("font-bold text-body2 flex-1")
        ui.label("Vai trò").classes("font-bold text-body2 w-24 text-center")
        ui.label("Thường").classes("font-bold text-body2 w-16 text-center")
        ui.label("Thứ 6").classes("font-bold text-body2 w-16 text-center")
        ui.label("Cutoff").classes("font-bold text-body2 w-16 text-center")
        ui.label("QT Chính").classes("font-bold text-body2 w-20 text-center")
        ui.label("QT Phụ").classes("font-bold text-body2 w-16 text-center")
        ui.label("Tổng").classes("font-bold text-body2 w-16 text-center text-blue-8")

    current_role = None

    for item in sorted_data:
        role = item.get("role", "")
        full_name = item.get("full_name", "—")
        normal = item.get("normal", 0)
        friday = item.get("friday", 0)
        cutoff = item.get("cutoff", 0)
        settlement_main = item.get("settlement_main", 0)
        settlement_sub = item.get("settlement_sub", 0)
        total = item.get("total", 0)

        # Role separator
        if role != current_role:
            current_role = role
            role_label = common.ROLE_LABELS.get(role, role)
            with ui.row().classes("w-full bg-blue-1 px-2 py-1 mt-2"):
                ui.label(f"── {role_label} ──").classes(
                    f"text-body2 font-bold text-{common.ROLE_COLORS.get(role, 'grey')}"
                )

        # Row
        row_bg = "bg-green-1" if total > 0 else "bg-white"
        with ui.row().classes(
            f"w-full border-b border-grey-2 px-2 py-1 items-center {row_bg} hover:bg-blue-1"
        ):
            ui.label(full_name).classes("text-body2 flex-1")

            with ui.column().classes("w-24 items-center"):
                color = common.ROLE_COLORS.get(role, "grey")
                label = common.ROLE_LABELS.get(role, role)
                ui.badge(label, color=color).classes("text-xs")

            ui.label(str(normal)).classes("w-16 text-center text-body2")
            ui.label(str(friday)).classes("w-16 text-center text-body2 text-orange-7")
            ui.label(str(cutoff)).classes("w-16 text-center text-body2 text-red-7")
            ui.label(str(settlement_main)).classes("w-20 text-center text-body2 text-purple-7")
            ui.label(str(settlement_sub)).classes("w-16 text-center text-body2 text-deep-purple-4")
            ui.label(str(total)).classes(
                "w-16 text-center font-bold text-blue-8 text-body1"
            )


# ── Section 2 helpers ──────────────────────────────────────────────────────────

def _render_monthly_summary(state: dict):
    """Tóm tắt tháng: tổng ca, breakdown theo loại."""
    summary = state.get("monthly_summary")

    if not summary:
        ui.label("(Không có dữ liệu tháng này)").classes("text-grey-6 italic")
        return

    month = summary.get("month", state["month"])
    year = summary.get("year", state["year"])
    total_shifts = summary.get("total_shifts", 0)
    by_type: dict = summary.get("by_type", {})

    with ui.row().classes("gap-4 flex-wrap"):
        # Total shifts card
        with ui.card().classes("p-4 bg-blue-1 min-w-[140px] text-center"):
            ui.label("Tổng số ca").classes("text-body2 text-grey-7")
            ui.label(str(total_shifts)).classes("text-h4 font-bold text-blue-8")
            ui.label(f"Tháng {month}/{year}").classes("text-xs text-grey-6")

    # Breakdown by type
    if by_type:
        ui.label("Breakdown theo loại ca:").classes("text-body2 font-bold mt-4 mb-1")
        with ui.row().classes("gap-3 flex-wrap"):
            type_display = {
                "normal":          ("Ca thường",        "grey-7"),
                "friday":          ("Thứ Sáu",          "orange-7"),
                "cutoff":          ("Cutoff",            "red-7"),
                "settlement_main": ("Quyết toán chính", "deep-purple-7"),
                "settlement_sub":  ("Quyết toán phụ",   "deep-purple-4"),
            }
            for key, count in by_type.items():
                label, color = type_display.get(key, (key, "grey-7"))
                with ui.card().classes("p-3 text-center min-w-[120px]"):
                    ui.badge(label, color=color).classes("text-xs mb-1")
                    ui.label(str(count)).classes(f"text-h5 font-bold text-{color}")


# ── Section 3 helpers ──────────────────────────────────────────────────────────

def _render_rotation_table(state: dict):
    """Bảng trạng thái vòng xoay."""
    data = state.get("rotation_data", [])

    if not data:
        ui.label("(Chưa có dữ liệu vòng xoay)").classes("text-grey-6 italic")
        return

    # Sort theo role, rồi shift_count ASC
    sorted_data = sorted(data, key=lambda x: (x.get("role", ""), x.get("shift_count", 0)))

    # Header
    with ui.row().classes("w-full border-b-2 border-blue-8 pb-1 px-2"):
        ui.label("Tên").classes("font-bold text-body2 flex-1")
        ui.label("Vai trò").classes("font-bold text-body2 w-24 text-center")
        ui.label("Loại vòng xoay").classes("font-bold text-body2 w-32 text-center")
        ui.label("Số ca").classes("font-bold text-body2 w-20 text-center")
        ui.label("Lần trực cuối").classes("font-bold text-body2 w-36 text-center")

    for item in sorted_data:
        staff_name = item.get("staff_name", "—")
        rotation_role = item.get("role", "")
        shift_count = item.get("shift_count", 0)
        last_used = item.get("last_used") or "—"

        # Base role cho badge (lấy phần trước dấu _)
        base_role = rotation_role.split("_")[0] if "_" in rotation_role else rotation_role

        with ui.row().classes(
            "w-full border-b border-grey-2 px-2 py-1 items-center hover:bg-blue-1"
        ):
            ui.label(staff_name).classes("text-body2 flex-1")

            with ui.column().classes("w-24 items-center"):
                color = common.ROLE_COLORS.get(base_role, "grey")
                label = common.ROLE_LABELS.get(base_role, base_role)
                ui.badge(label, color=color).classes("text-xs")

            # Loại vòng xoay
            rotation_labels = {
                "LD":         ("LĐ thường",   "blue-7"),
                "NV":         ("NV thường",   "green-7"),
                "LD_friday":  ("LĐ Thứ 6",    "orange-7"),
                "NV_friday":  ("NV Thứ 6",    "orange-5"),
                "LD_cutoff":  ("LĐ Cutoff",   "red-7"),
                "NV_cutoff":  ("NV Cutoff",   "red-4"),
            }
            rot_label, rot_color = rotation_labels.get(rotation_role, (rotation_role, "grey"))
            with ui.column().classes("w-32 items-center"):
                ui.badge(rot_label, color=rot_color).classes("text-xs")

            ui.label(str(shift_count)).classes("w-20 text-center font-bold text-body2")
            ui.label(last_used).classes("w-36 text-center text-body2 text-grey-7")
