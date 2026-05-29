"""
roster_list.py — Tab Danh sách (Bảng nhân sự + CRUD).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nicegui import ui
from datetime import datetime
from frontend import api_client
from frontend.components import common


def roster_list_page():
    """Tab Danh sách."""

    state = {
        "staff": [],
        "staff_shifts": {},
        "filter_role": None,
        "year": datetime.now().year,
    }

    def load_staff_and_shifts():
        state["staff"] = api_client.get_staff() or []
        shifts_data = api_client.get_shift_count(state["year"]) or []
        state["staff_shifts"] = {
            item.get("staff_id"): item.get("total", 0)
            for item in shifts_data
        }

    load_staff_and_shifts()

    common.create_navbar("/danh-sach")

    with ui.column().classes("w-full max-w-4xl mx-auto p-4"):
        common.section_title("👥 Danh sách nhân sự", "people_alt")

        # ── Filter row + Add button ────
        with ui.row().classes("items-center gap-3 mb-4"):
            ui.label("Vai trò:").classes("text-body2")
            ui.select(
                options={
                    None: "Tất cả",
                    "LD": "Lãnh đạo (LD)",
                    "SP": "Song Phương (SP)",
                    "NV": "Nhân viên (NV)",
                },
                value=state["filter_role"],
                on_change=lambda e: (state.update({"filter_role": e.value}), render_table()),
            ).classes("w-48")

            ui.label("Năm:").classes("text-body2 ml-4")
            ui.select(
                options={y: str(y) for y in range(2024, 2030)},
                value=state["year"],
                on_change=lambda e: (
                    state.update({"year": e.value}),
                    load_staff_and_shifts(),
                    render_table(),
                ),
            ).classes("w-24")

            ui.space()

            ui.button(
                "+ Thêm nhân viên",
                on_click=lambda: _open_add_dialog(state, render_table),
            ).props("color=blue-7")

        table_container = ui.column().classes("w-full")

    def render_table():
        table_container.clear()

        with table_container:
            # Header
            with ui.row().classes("w-full border-b-2 border-blue-8 mb-2 px-4"):
                ui.label("Tên").classes("text-body2 font-bold w-[35%]")
                ui.label("Vai trò").classes("text-body2 font-bold w-[18%]")
                ui.label("Số ca").classes("text-body2 font-bold w-[12%] text-center")
                ui.label("Dự án").classes("text-body2 font-bold w-[12%] text-center")
                ui.label("Thao tác").classes("text-body2 font-bold flex-1 text-right pr-2")

            filtered = [
                s for s in state["staff"]
                if state["filter_role"] is None or s.get("role") == state["filter_role"]
            ]

            for staff in filtered:
                sid = staff.get("id")
                full_name = staff.get("full_name", "—")
                role = staff.get("role", "")
                is_on_project = staff.get("is_on_project", 0)
                shift_count = state["staff_shifts"].get(sid, 0)

                with ui.row().classes(
                    "w-full border-b border-grey-2 px-4 py-2 items-center hover:bg-blue-1"
                ):
                    ui.label(full_name).classes("w-[35%] text-body1")

                    with ui.column().classes("w-[18%]"):
                        role_label = common.ROLE_LABELS.get(role, role)
                        color = common.ROLE_COLORS.get(role, "grey")
                        ui.badge(role_label, color=color).classes("text-xs")

                    ui.label(str(shift_count)).classes(
                        "w-[12%] text-center text-body2 font-bold"
                    )

                    with ui.column().classes("w-[12%] items-center"):
                        ui.checkbox(
                            value=bool(is_on_project),
                            on_change=lambda _e, s=sid: _toggle_project(s, state, render_table),
                        ).props("dense")

                    with ui.row().classes("flex-1 justify-end gap-1"):
                        ui.button(
                            "✏️",
                            on_click=lambda s=staff: _open_edit_dialog(s, state, render_table),
                        ).props("flat dense size=sm color=blue-7")
                        ui.button(
                            "🗑️",
                            on_click=lambda s=staff: _open_delete_dialog(s, state, render_table),
                        ).props("flat dense size=sm color=red-7")

    render_table()


def _toggle_project(staff_id: int, state: dict, render_callback):
    result = api_client.toggle_project(staff_id)
    if result:
        common.show_notify("Cap nhat thanh cong", type="positive")
        for s in state["staff"]:
            if s.get("id") == staff_id:
                s["is_on_project"] = result.get("is_on_project", 0)
                break
        render_callback()
    else:
        common.show_notify("Cap nhat that bai", type="negative")


def _open_add_dialog(state: dict, render_callback):
    with ui.dialog() as dialog, ui.card().classes("w-96 p-4"):
        ui.label("Thêm nhân viên").classes("text-h6 mb-4")

        name_input = ui.input("Họ tên *").classes("w-full")
        role_select = ui.select(
            options={"LD": "Lãnh đạo", "SP": "Song Phương", "NV": "Nhân viên"},
            label="Vai trò",
            value="NV",
        ).classes("w-full")
        project_check = ui.checkbox("Đi dự án")
        order_input = ui.number("Thứ tự hiển thị", value=99, min=1, max=999).classes("w-full")

        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button("Hủy", on_click=dialog.close).props("flat")

            def do_add():
                full_name = (name_input.value or "").strip()
                if not full_name:
                    common.show_notify("Vui long nhap ho ten", type="warning")
                    return
                result = api_client.create_staff(
                    full_name=full_name,
                    role=role_select.value,
                    is_on_project=bool(project_check.value),
                    display_order=int(order_input.value or 99),
                )
                if result:
                    common.show_notify("Them nhan vien thanh cong", type="positive")
                    state["staff"] = api_client.get_staff() or []
                    render_callback()
                    dialog.close()
                else:
                    common.show_notify("Loi them nhan vien", type="negative")

            ui.button("Lưu", on_click=do_add).props("color=blue-7")

    dialog.open()


def _open_edit_dialog(staff: dict, state: dict, render_callback):
    with ui.dialog() as dialog, ui.card().classes("w-96 p-4"):
        ui.label("Sửa nhân viên").classes("text-h6 mb-4")

        name_input = ui.input("Họ tên *", value=staff.get("full_name", "")).classes("w-full")
        role_select = ui.select(
            options={"LD": "Lãnh đạo", "SP": "Song Phương", "NV": "Nhân viên"},
            label="Vai trò",
            value=staff.get("role", "NV"),
        ).classes("w-full")
        project_check = ui.checkbox("Đi dự án", value=bool(staff.get("is_on_project", 0)))
        order_input = ui.number(
            "Thứ tự hiển thị", value=staff.get("display_order", 99), min=1, max=999
        ).classes("w-full")

        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button("Hủy", on_click=dialog.close).props("flat")

            def do_edit():
                full_name = (name_input.value or "").strip()
                if not full_name:
                    common.show_notify("Vui long nhap ho ten", type="warning")
                    return
                result = api_client.update_staff(
                    staff_id=staff["id"],
                    full_name=full_name,
                    role=role_select.value,
                    is_on_project=bool(project_check.value),
                    display_order=int(order_input.value or 99),
                )
                if result:
                    common.show_notify("Cap nhat thanh cong", type="positive")
                    state["staff"] = api_client.get_staff() or []
                    render_callback()
                    dialog.close()
                else:
                    common.show_notify("Loi cap nhat", type="negative")

            ui.button("Lưu", on_click=do_edit).props("color=blue-7")

    dialog.open()


def _open_delete_dialog(staff: dict, state: dict, render_callback):
    full_name = staff.get("full_name", "")
    with ui.dialog() as dialog, ui.card().classes("w-80 p-4"):
        ui.label(f"Xóa {full_name}?").classes("text-h6 mb-2")
        ui.label("Các ca trực cũ sẽ mất tên người này.").classes(
            "text-body2 text-grey-7 mb-4"
        )

        with ui.row().classes("justify-end gap-2"):
            ui.button("Hủy", on_click=dialog.close).props("flat")

            def do_delete():
                ok = api_client.delete_staff(staff["id"])
                if ok:
                    common.show_notify(f"Da xoa {full_name}", type="positive")
                    state["staff"] = api_client.get_staff() or []
                    render_callback()
                    dialog.close()
                else:
                    common.show_notify("Loi xoa nhan vien", type="negative")

            ui.button("Xóa", on_click=do_delete).props("color=red-7")

    dialog.open()
