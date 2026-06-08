"""
settings.py — Tab Cài đặt (/cai-dat).

5 tab:
  1. 🔧 Cấu hình ca  — nv_count theo năm
  2. 📅 Ngày đặc biệt — holiday / cutoff / settlement / makeup
  3. 🚫 Khai báo vắng — absences theo tháng
  4. 📝 Đăng ký trực  — duty requests (once / weekly) cho NV
  5. 🔄 Vòng xoay     — xem và reset rotation state
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nicegui import ui
from datetime import datetime
from frontend import api_client
from frontend.components import common

# Màu badge loại ngày đặc biệt
_SPECIAL_DAY_COLORS = {
    "holiday":    "red",
    "cutoff":     "orange",
    "settlement": "deep-purple",
    "makeup":     "blue",
}
_SPECIAL_DAY_LABELS = {
    "holiday":    "Nghỉ lễ",
    "cutoff":     "Cutoff",
    "settlement": "Quyết toán",
    "makeup":     "Bù lễ",
}

_DOW_LABELS = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6"}


def settings_page():
    """Tab Cài đặt với 5 tabs."""

    # ── State chung ────
    state = {
        "year":      datetime.now().year,
        "month":     datetime.now().month,
        "all_staff": api_client.get_staff() or [],
    }

    # ── Header ────
    common.create_navbar("/cai-dat")

    with ui.column().classes("w-full max-w-5xl mx-auto p-4"):
        common.section_title("⚙️ Cài đặt", "settings")

        # ── Tabs ────
        with ui.tabs().classes("w-full") as tabs:
            tab_config    = ui.tab("🔧 Cấu hình ca")
            tab_special   = ui.tab("📅 Ngày đặc biệt")
            tab_absence   = ui.tab("🚫 Khai báo vắng")
            tab_request   = ui.tab("📝 Đăng ký trực")
            tab_rotation  = ui.tab("🔄 Vòng xoay")

        with ui.tab_panels(tabs, value=tab_config).classes("w-full mt-4"):

            # ──────────────────────────────────────────────────────────────────
            # TAB 1: Cấu hình ca
            # ──────────────────────────────────────────────────────────────────
            with ui.tab_panel(tab_config):
                _render_tab_config(state)

            # ──────────────────────────────────────────────────────────────────
            # TAB 2: Ngày đặc biệt
            # ──────────────────────────────────────────────────────────────────
            with ui.tab_panel(tab_special):
                _render_tab_special(state)

            # ──────────────────────────────────────────────────────────────────
            # TAB 3: Khai báo vắng
            # ──────────────────────────────────────────────────────────────────
            with ui.tab_panel(tab_absence):
                _render_tab_absence(state)

            # ──────────────────────────────────────────────────────────────────
            # TAB 4: Đăng ký xin trực
            # ──────────────────────────────────────────────────────────────────
            with ui.tab_panel(tab_request):
                _render_tab_request(state)

            # ──────────────────────────────────────────────────────────────────
            # TAB 5: Vòng xoay
            # ──────────────────────────────────────────────────────────────────
            with ui.tab_panel(tab_rotation):
                _render_tab_rotation(state)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Cấu hình ca
# ══════════════════════════════════════════════════════════════════════════════

def _render_tab_config(state: dict):
    cfg_state = {
        "year":        state["year"],
        "nv_count":    1,
        "signer_name": "",
    }

    def load_config():
        cfg = api_client.get_shift_config(cfg_state["year"])
        cfg_state["nv_count"] = cfg.get("nv_count", 1) if cfg else 1
        cfg_state["signer_name"] = (cfg.get("signer_name") or "") if cfg else ""
        nv_input.set_value(cfg_state["nv_count"])
        signer_input.set_value(cfg_state["signer_name"])

    def save_config():
        result = api_client.upsert_shift_config(
            cfg_state["year"], cfg_state["nv_count"],
            signer_name=cfg_state["signer_name"] or None,
        )
        if result:
            common.show_notify(
                f"✅ Đã lưu: năm {cfg_state['year']}, NV/ca = {cfg_state['nv_count']}",
                type="positive"
            )
        else:
            common.show_notify("❌ Lỗi khi lưu cấu hình", type="negative")

    common.section_title("Số NV tối thiểu mỗi ca", "group")
    ui.label(
        "Cấu hình số Nhân viên (NV) tối thiểu cần có trong mỗi ca trực thường."
    ).classes("text-body2 text-grey-7 mb-3")

    with ui.row().classes("items-end gap-4 flex-wrap"):
        with ui.column().classes("gap-1"):
            ui.label("Năm:").classes("text-body2")
            year_sel = ui.select(
                options={y: str(y) for y in range(2024, 2030)},
                value=cfg_state["year"],
                on_change=lambda e: (
                    cfg_state.update({"year": e.value}),
                    load_config(),
                )
            ).classes("w-24")

        with ui.column().classes("gap-1"):
            ui.label("Số NV/ca (1–5):").classes("text-body2")
            nv_input = ui.number(
                value=cfg_state["nv_count"],
                min=1, max=5, step=1,
                on_change=lambda e: cfg_state.update({"nv_count": int(e.value or 1)})
            ).classes("w-24")

        with ui.column().classes("gap-1"):
            ui.label("Tên người ký (Excel):").classes("text-body2")
            signer_input = ui.input(
                placeholder="Nguyễn Quốc Hùng",
                value=cfg_state["signer_name"],
                on_change=lambda e: cfg_state.update({"signer_name": e.value or ""}),
            ).classes("w-52")

        ui.button("💾 Lưu cấu hình", on_click=save_config).props("color=blue-7").classes("mt-5")

    # Load giá trị hiện tại
    load_config()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Ngày đặc biệt
# ══════════════════════════════════════════════════════════════════════════════

def _render_tab_special(state: dict):
    sp_state = {
        "year":  state["year"],
        "month": state["month"],
        "data":  [],
        # form inputs
        "form_date":  "",
        "form_type":  "holiday",
        "form_label": "",
    }

    def load_data():
        sp_state["data"] = api_client.get_special_days(
            sp_state["month"], sp_state["year"]
        ) or []

    load_data()

    common.section_title("Quản lý ngày đặc biệt", "event_note")

    # ── Controls ────
    with ui.row().classes("items-center gap-3 mb-3 flex-wrap"):
        ui.label("Tháng:").classes("text-body2")
        ui.select(
            options={m: f"Tháng {m}" for m in range(1, 13)},
            value=sp_state["month"],
            on_change=lambda e: (
                sp_state.update({"month": e.value}),
                load_data(),
                render_list(),
            )
        ).classes("w-32")

        ui.label("Năm:").classes("text-body2")
        ui.select(
            options={y: str(y) for y in range(2024, 2030)},
            value=sp_state["year"],
            on_change=lambda e: (
                sp_state.update({"year": e.value}),
                load_data(),
                render_list(),
            )
        ).classes("w-24")

        ui.button(
            "🗓️ Tính ngày Cutoff",
            on_click=lambda: _do_compute_cutoff(sp_state, load_data, render_list)
        ).props("color=orange-7")

    # ── Form thêm ngày đặc biệt ────
    with ui.card().classes("p-4 bg-grey-1 w-full mb-3"):
        ui.label("Thêm ngày đặc biệt").classes("text-body2 font-bold mb-2")
        with ui.row().classes("items-end gap-3 flex-wrap"):
            with ui.column().classes("gap-1"):
                ui.label("Ngày:").classes("text-caption")
                date_input = ui.input(
                    on_change=lambda e: sp_state.update({"form_date": e.value or ""})
                ).props('type=date').classes("w-40")

            with ui.column().classes("gap-1"):
                ui.label("Loại:").classes("text-caption")
                type_sel = ui.select(
                    options={
                        "holiday":    "Nghỉ lễ",
                        "cutoff":     "Cutoff",
                        "settlement": "Quyết toán",
                        "makeup":     "Bù lễ",
                    },
                    value="holiday",
                    on_change=lambda e: sp_state.update({"form_type": e.value})
                ).classes("w-36")

            with ui.column().classes("gap-1"):
                ui.label("Nhãn (tuỳ chọn):").classes("text-caption")
                label_input = ui.input(
                    placeholder="VD: Tết Nguyên Đán",
                    on_change=lambda e: sp_state.update({"form_label": e.value or ""})
                ).classes("w-48")

            def add_special_day():
                d = sp_state["form_date"].strip()
                if not d:
                    common.show_notify("⚠️ Vui lòng nhập ngày", type="warning")
                    return
                result = api_client.create_special_day(
                    d, sp_state["form_type"],
                    sp_state["form_label"].strip() or None
                )
                if result:
                    common.show_notify("✅ Đã thêm ngày đặc biệt", type="positive")
                    date_input.set_value("")
                    label_input.set_value("")
                    sp_state.update({"form_date": "", "form_label": ""})
                    load_data()
                    render_list()
                else:
                    common.show_notify("❌ Lỗi thêm ngày (trùng?)", type="negative")

            ui.button("➕ Thêm", on_click=add_special_day).props("color=green-7").classes("mt-5")

    # ── List ────
    list_container = ui.column().classes("w-full")

    def render_list():
        list_container.clear()
        with list_container:
            _render_special_days_list(sp_state, load_data, render_list)

    render_list()


def _do_compute_cutoff(sp_state: dict, load_fn, render_fn):
    """Tính và lưu 2 ngày cutoff cho tháng."""
    def do_it():
        result = api_client.compute_cutoff(sp_state["month"], sp_state["year"])
        if result:
            dates = result if isinstance(result, list) else result.get("cutoff_dates", [])
            common.show_notify(
                f"✅ Đã tính cutoff: {dates}",
                type="positive"
            )
            load_fn()
            render_fn()
        else:
            common.show_notify("❌ Lỗi tính cutoff", type="negative")

    common.confirm_dialog(
        f"Tính 2 ngày cutoff cho tháng {sp_state['month']}/{sp_state['year']}?",
        on_confirm=do_it,
        confirm_label="Tính"
    )


def _render_special_days_list(sp_state: dict, load_fn, render_fn):
    """Render danh sách ngày đặc biệt."""
    data = sp_state.get("data", [])

    if not data:
        ui.label("(Không có ngày đặc biệt nào trong tháng này)").classes(
            "text-grey-6 italic"
        )
        return

    # Header
    with ui.row().classes("w-full border-b-2 border-grey-4 pb-1 px-2"):
        ui.label("Ngày").classes("font-bold text-body2 w-28")
        ui.label("Loại").classes("font-bold text-body2 w-28")
        ui.label("Nhãn").classes("font-bold text-body2 flex-1")
        ui.label("Trạng thái").classes("font-bold text-body2 w-28 text-center")
        ui.label("").classes("w-40")  # actions

    for item in sorted(data, key=lambda x: x.get("date", "")):
        item_id = item.get("id")
        date = item.get("date", "—")
        day_type = item.get("day_type", "")
        label = item.get("label") or "—"
        is_confirmed = item.get("is_confirmed", False)

        color = _SPECIAL_DAY_COLORS.get(day_type, "grey")
        type_label = _SPECIAL_DAY_LABELS.get(day_type, day_type)

        with ui.row().classes(
            "w-full border-b border-grey-2 px-2 py-2 items-center hover:bg-blue-1"
        ):
            ui.label(date).classes("w-28 text-body2 font-mono")

            with ui.column().classes("w-28 items-start"):
                ui.badge(type_label, color=color).classes("text-xs")

            ui.label(label).classes("flex-1 text-body2")

            with ui.column().classes("w-28 items-center"):
                if is_confirmed:
                    ui.badge("✓ Xác nhận", color="green").classes("text-xs")
                else:
                    ui.badge("Nháp", color="orange").classes("text-xs")

            with ui.row().classes("w-40 gap-1 justify-end"):
                # Nút xác nhận (chỉ khi chưa confirmed)
                if not is_confirmed and day_type in ("cutoff", "settlement"):
                    ui.button(
                        "✓",
                        on_click=lambda iid=item_id: _confirm_special_day(iid, load_fn, render_fn)
                    ).props("size=xs color=green flat dense")

                # Nút xóa
                ui.button(
                    "🗑",
                    on_click=lambda iid=item_id, d=date: common.confirm_dialog(
                        f"Xóa ngày đặc biệt {d}?",
                        on_confirm=lambda: _delete_special_day(iid, load_fn, render_fn),
                        confirm_label="Xóa"
                    )
                ).props("size=xs color=red flat dense")


def _confirm_special_day(item_id: int, load_fn, render_fn):
    result = api_client.confirm_special_day(item_id)
    if result:
        common.show_notify("✅ Đã xác nhận", type="positive")
        load_fn()
        render_fn()
    else:
        common.show_notify("❌ Lỗi xác nhận", type="negative")


def _delete_special_day(item_id: int, load_fn, render_fn):
    ok = api_client.delete_special_day(item_id)
    if ok:
        common.show_notify("✅ Đã xóa", type="positive")
        load_fn()
        render_fn()
    else:
        common.show_notify("❌ Lỗi xóa", type="negative")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Khai báo vắng
# ══════════════════════════════════════════════════════════════════════════════

def _render_tab_absence(state: dict):
    ab_state = {
        "year":           state["year"],
        "month":          state["month"],
        "data":           [],
        "form_staff_id":  None,
        "form_from_date": "",
        "form_to_date":   "",
    }

    all_staff = state["all_staff"]

    def load_data():
        ab_state["data"] = api_client.get_absences(ab_state["month"], ab_state["year"]) or []

    load_data()

    common.section_title("Khai báo vắng mặt", "event_busy")

    # ── Controls ────
    with ui.row().classes("items-center gap-3 mb-3"):
        ui.label("Tháng:").classes("text-body2")
        ui.select(
            options={m: f"Tháng {m}" for m in range(1, 13)},
            value=ab_state["month"],
            on_change=lambda e: (
                ab_state.update({"month": e.value}),
                load_data(),
                render_list(),
            )
        ).classes("w-32")

        ui.label("Năm:").classes("text-body2")
        ui.select(
            options={y: str(y) for y in range(2024, 2030)},
            value=ab_state["year"],
            on_change=lambda e: (
                ab_state.update({"year": e.value}),
                load_data(),
                render_list(),
            )
        ).classes("w-24")

    # ── Form thêm vắng ────
    staff_options = {
        s["id"]: f"{s['full_name']} ({s['role']})"
        for s in all_staff
    }

    with ui.card().classes("p-4 bg-grey-1 w-full mb-3"):
        ui.label("Thêm khai báo vắng").classes("text-body2 font-bold mb-2")
        with ui.row().classes("items-end gap-3 flex-wrap"):
            with ui.column().classes("gap-1"):
                ui.label("Nhân sự:").classes("text-caption")
                staff_sel = ui.select(
                    options=staff_options,
                    value=None,
                    on_change=lambda e: ab_state.update({"form_staff_id": e.value})
                ).classes("w-56")

            with ui.column().classes("gap-1"):
                ui.label("Từ ngày:").classes("text-caption")
                from_date_input = ui.input(
                    on_change=lambda e: ab_state.update({"form_from_date": e.value or ""})
                ).props('type=date').classes("w-36")

            with ui.column().classes("gap-1"):
                ui.label("Đến ngày:").classes("text-caption")
                to_date_input = ui.input(
                    on_change=lambda e: ab_state.update({"form_to_date": e.value or ""})
                ).props('type=date').classes("w-36")

            def add_absence():
                if not ab_state["form_staff_id"]:
                    common.show_notify("⚠️ Chọn nhân sự", type="warning")
                    return
                fd = ab_state["form_from_date"].strip()
                td = ab_state["form_to_date"].strip()
                if not fd or not td:
                    common.show_notify("⚠️ Nhập đầy đủ từ ngày và đến ngày", type="warning")
                    return
                if td < fd:
                    common.show_notify("⚠️ Đến ngày phải ≥ Từ ngày", type="warning")
                    return
                result = api_client.create_absence_range(ab_state["form_staff_id"], fd, td)
                if result:
                    msg = result.get("message", "✅ Đã thêm khai báo vắng")
                    common.show_notify(msg, type="positive")
                    staff_sel.set_value(None)
                    from_date_input.set_value("")
                    to_date_input.set_value("")
                    ab_state.update({"form_staff_id": None, "form_from_date": "", "form_to_date": ""})
                    load_data()
                    render_list()
                else:
                    common.show_notify("❌ Lỗi thêm khai báo vắng", type="negative")

            ui.button("➕ Thêm", on_click=add_absence).props("color=green-7").classes("mt-5")

    # ── N6: Xóa vắng theo khoảng ────
    with ui.card().classes("p-4 bg-orange-1 w-full mb-3"):
        ui.label("Xóa vắng theo khoảng").classes("text-body2 font-bold mb-2")
        del_state = {"staff_id": None, "from_date": "", "to_date": ""}
        with ui.row().classes("items-end gap-3 flex-wrap"):
            with ui.column().classes("gap-1"):
                ui.label("Nhân sự:").classes("text-caption")
                ui.select(
                    options={s["id"]: s["full_name"] for s in all_staff},
                    value=None,
                    on_change=lambda e: del_state.update({"staff_id": e.value})
                ).classes("w-44")
            with ui.column().classes("gap-1"):
                ui.label("Từ ngày:").classes("text-caption")
                ui.input(
                    on_change=lambda e: del_state.update({"from_date": e.value or ""})
                ).props("type=date").classes("w-36")
            with ui.column().classes("gap-1"):
                ui.label("Đến ngày:").classes("text-caption")
                ui.input(
                    on_change=lambda e: del_state.update({"to_date": e.value or ""})
                ).props("type=date").classes("w-36")

            def _confirm_delete_range():
                if not del_state["staff_id"]:
                    common.show_notify("⚠️ Chọn nhân sự", type="warning")
                    return
                if not del_state["from_date"] or not del_state["to_date"]:
                    common.show_notify("⚠️ Nhập đầy đủ khoảng ngày", type="warning")
                    return
                if del_state["to_date"] < del_state["from_date"]:
                    common.show_notify("⚠️ Ngày kết thúc phải sau ngày bắt đầu", type="warning")
                    return
                staff_name = next(
                    (s["full_name"] for s in all_staff if s["id"] == del_state["staff_id"]),
                    "nhân sự"
                )
                common.confirm_dialog(
                    f"Xóa vắng của {staff_name} từ {del_state['from_date']} đến {del_state['to_date']}?",
                    on_confirm=lambda: _do_delete_range(
                        del_state["staff_id"], del_state["from_date"], del_state["to_date"],
                        load_data, render_list
                    ),
                    confirm_label="Xóa",
                )

            ui.button("🗑 Xóa khoảng", on_click=_confirm_delete_range).props(
                "color=orange-7 outline"
            ).classes("mt-5")

    # ── List ────
    list_container = ui.column().classes("w-full")

    def render_list():
        list_container.clear()
        with list_container:
            _render_absence_list(ab_state, load_data, render_list)

    render_list()


def _render_absence_list(ab_state: dict, load_fn, render_fn):
    data = ab_state.get("data", [])

    if not data:
        ui.label("(Không có khai báo vắng nào trong tháng này)").classes(
            "text-grey-6 italic"
        )
        return

    # Header
    with ui.row().classes("w-full border-b-2 border-grey-4 pb-1 px-2"):
        ui.label("Nhân sự").classes("font-bold text-body2 flex-1")
        ui.label("Ngày vắng").classes("font-bold text-body2 w-36")
        ui.label("").classes("w-16")

    for item in sorted(data, key=lambda x: x.get("absence_date", "")):
        item_id = item.get("id")
        staff_name = item.get("staff_name", "—")
        absence_date = item.get("absence_date", "—")

        with ui.row().classes(
            "w-full border-b border-grey-2 px-2 py-2 items-center hover:bg-red-1"
        ):
            ui.label(staff_name).classes("flex-1 text-body2")
            ui.label(absence_date).classes("w-36 text-body2 font-mono")

            ui.button(
                "🗑",
                on_click=lambda iid=item_id, n=staff_name, d=absence_date: common.confirm_dialog(
                    f"Xóa khai báo vắng: {n} ngày {d}?",
                    on_confirm=lambda: _delete_absence(iid, load_fn, render_fn),
                    confirm_label="Xóa"
                )
            ).props("size=xs color=red flat dense")


def _delete_absence(item_id: int, load_fn, render_fn):
    ok = api_client.delete_absence(item_id)
    if ok:
        common.show_notify("✅ Đã xóa khai báo vắng", type="positive")
        load_fn()
        render_fn()
    else:
        common.show_notify("❌ Lỗi xóa", type="negative")


def _do_delete_range(staff_id: int, from_date: str, to_date: str, load_fn, render_fn):
    ok = api_client.delete_absence_range(staff_id, from_date, to_date)
    if ok:
        common.show_notify("✅ Đã xóa vắng theo khoảng", type="positive")
        load_fn()
        render_fn()
    else:
        common.show_notify("❌ Lỗi xóa khoảng vắng", type="negative")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Đăng ký xin trực
# ══════════════════════════════════════════════════════════════════════════════

def _render_tab_request(state: dict):
    all_staff = state["all_staff"]

    req_state = {
        "year":           state["year"],
        "data":           [],
        "form_staff_id":  None,
        "form_type":      "once",
        "form_date":      "",
        "form_dow":       0,
        "all_staff":      all_staff,
    }

    def load_data():
        req_state["data"] = api_client.get_requests(year=req_state["year"]) or []

    load_data()

    common.section_title("Đăng ký xin trực", "assignment_turned_in")
    ui.label(
        "NV đăng ký xin trực ca cụ thể (once) hoặc hằng tuần (weekly)."
    ).classes("text-body2 text-grey-7 mb-3")

    # ── Controls ────
    with ui.row().classes("items-center gap-3 mb-3"):
        ui.label("Năm:").classes("text-body2")
        ui.select(
            options={y: str(y) for y in range(2024, 2030)},
            value=req_state["year"],
            on_change=lambda e: (
                req_state.update({"year": e.value}),
                load_data(),
                render_list(),
            )
        ).classes("w-24")

    # ── Form thêm ────
    staff_options = {
        s["id"]: f"{s['full_name']} ({s['role']})"
        for s in all_staff
    }

    with ui.card().classes("p-4 bg-grey-1 w-full mb-3"):
        ui.label("Thêm đăng ký xin trực").classes("text-body2 font-bold mb-2")

        with ui.row().classes("items-end gap-3 flex-wrap"):
            with ui.column().classes("gap-1"):
                ui.label("Nhân sự:").classes("text-caption")
                staff_sel = ui.select(
                    options=staff_options,
                    value=None,
                    on_change=lambda e: req_state.update({"form_staff_id": e.value})
                ).classes("w-56")

            with ui.column().classes("gap-1"):
                ui.label("Loại:").classes("text-caption")
                ui.select(
                    options={"once": "Một lần (once)", "weekly": "Hằng tuần (weekly)"},
                    value="once",
                    on_change=lambda e: (
                        req_state.update({"form_type": e.value}),
                        render_form_detail(),
                    )
                ).classes("w-44")

        # Container cho date/dow input — re-render khi loại thay đổi (thay set_visibility)
        form_detail = ui.row().classes("items-end gap-3 flex-wrap mt-2")

        def render_form_detail():
            """Re-render input date hoặc dow selector tùy req_state['form_type']."""
            form_detail.clear()
            with form_detail:
                if req_state["form_type"] == "once":
                    with ui.column().classes("gap-1"):
                        ui.label("Ngày cụ thể:").classes("text-caption")
                        ui.input(
                            on_change=lambda e: req_state.update({"form_date": e.value or ""})
                        ).props('type=date').classes("w-44")
                else:
                    with ui.column().classes("gap-1"):
                        ui.label("Ngày trong tuần:").classes("text-caption")
                        ui.select(
                            options={i: _DOW_LABELS[i] for i in range(5)},
                            value=req_state["form_dow"],
                            on_change=lambda e: req_state.update({"form_dow": e.value})
                        ).classes("w-32")

        render_form_detail()  # Hiện date input mặc định

        def add_request():
            if not req_state["form_staff_id"]:
                common.show_notify("⚠️ Chọn nhân sự", type="warning")
                return

            rtype = req_state["form_type"]
            kwargs = {"staff_id": req_state["form_staff_id"],
                      "request_type": rtype,
                      "year": req_state["year"]}

            if rtype == "once":
                d = req_state["form_date"].strip()
                if not d:
                    common.show_notify("⚠️ Nhập ngày cụ thể", type="warning")
                    return
                kwargs["specific_date"] = d
            else:
                kwargs["day_of_week"] = req_state["form_dow"]

            result = api_client.create_request(**kwargs)
            if result:
                common.show_notify("✅ Đã thêm đăng ký", type="positive")
                staff_sel.set_value(None)
                req_state.update({"form_staff_id": None, "form_date": "", "form_dow": 0})
                render_form_detail()  # Reset form detail
                load_data()
                render_list()
            else:
                # T5: Hiện lỗi thực tế từ backend (slot limit, ngày lễ, cuối tuần, ...)
                err = api_client.get_last_api_error()
                common.show_notify(f"❌ {err}" if err else "❌ Lỗi thêm đăng ký (trùng?)", type="negative", timeout=8000)

        with ui.row().classes("mt-3"):
            ui.button("➕ Thêm đăng ký", on_click=add_request).props("color=green-7")

    # ── List ────
    list_container = ui.column().classes("w-full")

    def render_list():
        list_container.clear()
        with list_container:
            _render_request_list(req_state, load_data, render_list)

    render_list()


def _render_request_list(req_state: dict, load_fn, render_fn):
    data = req_state.get("data", [])

    if not data:
        ui.label("(Không có đăng ký xin trực nào)").classes("text-grey-6 italic")
        return

    # R5: map staff_id → is_on_project để hiển thị badge
    staff_map = {s["id"]: s for s in req_state.get("all_staff", [])}

    # Header
    with ui.row().classes("w-full border-b-2 border-grey-4 pb-1 px-2"):
        ui.label("Nhân sự").classes("font-bold text-body2 flex-1")
        ui.label("Loại").classes("font-bold text-body2 w-28")
        ui.label("Ngày / Thứ").classes("font-bold text-body2 w-40")
        ui.label("Trạng thái").classes("font-bold text-body2 w-24 text-center")
        ui.label("").classes("w-16")

    for item in sorted(data, key=lambda x: (x.get("staff_name", ""), x.get("request_type", ""))):
        item_id = item.get("id")
        staff_name = item.get("staff_name", "—")
        rtype = item.get("request_type", "")
        specific_date = item.get("specific_date")
        dow = item.get("day_of_week")
        is_active = item.get("is_active", True)
        is_on_project = staff_map.get(item.get("staff_id"), {}).get("is_on_project", 0)

        # Display ngày/thứ
        if rtype == "once" and specific_date:
            date_display = specific_date
        elif rtype == "weekly" and dow is not None:
            date_display = _DOW_LABELS.get(dow, f"Thứ {dow+2}")
        else:
            date_display = "—"

        row_class = "w-full border-b border-grey-2 px-2 py-2 items-center"
        row_class += " opacity-60" if is_on_project else " hover:bg-blue-1"
        with ui.row().classes(row_class):
            with ui.row().classes("flex-1 items-center gap-2"):
                ui.label(staff_name).classes("text-body2")
                if is_on_project:
                    ui.badge("Đi dự án", color="orange").classes("text-xs")

            with ui.column().classes("w-28"):
                color = "blue" if rtype == "once" else "teal"
                label = "Một lần" if rtype == "once" else "Hằng tuần"
                ui.badge(label, color=color).classes("text-xs")

            ui.label(date_display).classes("w-40 text-body2 font-mono")

            with ui.column().classes("w-24 items-center"):
                if is_active:
                    ui.badge("Đang dùng", color="green").classes("text-xs")
                else:
                    ui.badge("Tắt", color="grey").classes("text-xs")

            ui.button(
                "🗑",
                on_click=lambda iid=item_id, n=staff_name: common.confirm_dialog(
                    f"Xóa đăng ký của {n}?",
                    on_confirm=lambda: _delete_request(iid, load_fn, render_fn),
                    confirm_label="Xóa"
                )
            ).props("size=xs color=red flat dense")


def _delete_request(item_id: int, load_fn, render_fn):
    ok = api_client.delete_request(item_id)
    if ok:
        common.show_notify("✅ Đã xóa đăng ký", type="positive")
        load_fn()
        render_fn()
    else:
        common.show_notify("❌ Lỗi xóa", type="negative")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Vòng xoay
# ══════════════════════════════════════════════════════════════════════════════

def _render_tab_rotation(state: dict):
    rot_state = {
        "year": state["year"],
        "data": [],
    }

    def load_data():
        rot_state["data"] = api_client.get_rotation_state(rot_state["year"]) or []

    load_data()

    common.section_title("Trạng thái vòng xoay", "sync")
    ui.label(
        "Vòng xoay đảm bảo phân ca công bằng. Reset đầu mỗi năm."
    ).classes("text-body2 text-grey-7 mb-3")

    # ── Controls ────
    with ui.row().classes("items-center gap-3 mb-3"):
        ui.label("Năm:").classes("text-body2")
        ui.select(
            options={y: str(y) for y in range(2024, 2030)},
            value=rot_state["year"],
            on_change=lambda e: (
                rot_state.update({"year": e.value}),
                load_data(),
                render_table(),
            )
        ).classes("w-24")

        def do_reset():
            result = api_client.reset_rotation(rot_state["year"])
            if result:
                common.show_notify(
                    f"✅ Đã reset vòng xoay năm {rot_state['year']}",
                    type="positive"
                )
                load_data()
                render_table()
            else:
                common.show_notify("❌ Lỗi reset vòng xoay", type="negative")

        ui.button(
            f"🔄 Reset vòng xoay",
            on_click=lambda: common.confirm_dialog(
                f"Reset toàn bộ vòng xoay năm {rot_state['year']}?\n"
                "Hành động này không thể hoàn tác!",
                on_confirm=do_reset,
                confirm_label="Reset"
            )
        ).props("color=red-7")

    # ── Table ────
    table_container = ui.column().classes("w-full")

    def render_table():
        table_container.clear()
        with table_container:
            _render_rotation_table(rot_state)

    render_table()


def _render_rotation_table(rot_state: dict):
    data = rot_state.get("data", [])

    if not data:
        ui.label("(Chưa có dữ liệu vòng xoay — backend cần khởi tạo)").classes(
            "text-grey-6 italic"
        )
        return

    # Sort: role type → shift_count ASC → name
    _rot_order = {
        "LD": 0, "SP": 1, "NV": 2,
        "LD_friday": 3, "NV_friday": 4,
        "LD_cutoff": 5, "NV_cutoff": 6,
    }
    sorted_data = sorted(
        data,
        key=lambda x: (_rot_order.get(x.get("role", ""), 99), x.get("shift_count", 0))
    )

    _rotation_labels = {
        "LD":        ("LĐ thường",   "blue-7"),
        "SP":        ("SP thường",   "purple-7"),
        "NV":        ("NV thường",   "green-7"),
        "LD_friday": ("LĐ Thứ 6",   "orange-7"),
        "NV_friday": ("NV Thứ 6",   "orange-5"),
        "LD_cutoff": ("LĐ Cutoff",  "red-7"),
        "NV_cutoff": ("NV Cutoff",  "red-4"),
    }

    # Header
    with ui.row().classes("w-full border-b-2 border-blue-8 pb-1 px-2"):
        ui.label("Tên").classes("font-bold text-body2 flex-1")
        ui.label("Loại vòng xoay").classes("font-bold text-body2 w-32 text-center")
        ui.label("Số ca").classes("font-bold text-body2 w-20 text-center")
        ui.label("Lần trực cuối").classes("font-bold text-body2 w-36 text-center")

    current_role_type = None

    for item in sorted_data:
        staff_name = item.get("staff_name", "—")
        role_type = item.get("role", "")
        shift_count = item.get("shift_count", 0)
        last_used = item.get("last_used") or "—"

        rot_label, rot_color = _rotation_labels.get(role_type, (role_type, "grey"))

        # Group separator
        if role_type != current_role_type:
            current_role_type = role_type
            with ui.row().classes("w-full bg-grey-2 px-2 py-1 mt-2"):
                ui.badge(rot_label, color=rot_color).classes("text-xs mr-2")
                ui.label(f"— {rot_label}").classes(f"text-body2 font-bold text-{rot_color}")

        # Row
        with ui.row().classes(
            "w-full border-b border-grey-2 px-2 py-1 items-center hover:bg-blue-1"
        ):
            ui.label(staff_name).classes("flex-1 text-body2")

            with ui.column().classes("w-32 items-center"):
                ui.badge(rot_label, color=rot_color).classes("text-xs")

            ui.label(str(shift_count)).classes("w-20 text-center font-bold text-body2")
            ui.label(last_used).classes("w-36 text-center text-body2 text-grey-7 font-mono")
