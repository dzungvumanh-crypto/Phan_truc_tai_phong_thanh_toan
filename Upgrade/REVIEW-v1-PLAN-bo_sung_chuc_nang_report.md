# REVIEW v1 — Kế hoạch Hoàn thiện Phân lịch trực PTT
## Người review: Claude Sonnet 4.6 | Ngày: 2026-05-29

> **Phương pháp**: Đọc trực tiếp từng file trong codebase (không phỏng đoán), đối chiếu từng mục trong PLAN với code thực tế, rồi đề xuất bổ sung/điều chỉnh.

---

## PHẦN 1 — XÁC NHẬN ĐỘ CHÍNH XÁC CỦA PLAN HIỆN TẠI

### ✅ Những điều PLAN nhận xét đúng

| Mục | Nhận xét trong PLAN | Xác nhận từ code |
|-----|--------------------|--------------------|
| A1 Export Excel | Đã có nút `📥 Xuất Excel` | `schedule_planner.py:74-81` + `week_view.py:66-73` — ĐÚNG |
| A2 Confirm cutoff | Đã có UI trong Settings Tab 2 | `settings.py` Tab ngày đặc biệt + `api_client.confirm_special_day()` — ĐÚNG |
| A4 Sửa tay ca | `on_edit_click` là stub, chưa implement | `shift_card.py:94-97` — nút "Sửa" chỉ hiện khi `on_edit_click` được truyền vào, nhưng `schedule_planner.py` dùng `render_shift_card_compact()` không có nút sửa — ĐÚNG |
| A3 Warnings bị bỏ qua | `warnings[]` từ generate-week bị drop | `schedule_planner.py` hàm `do_gen()` chỉ lấy `created`, bỏ `warnings` — ĐÚNG |
| api_client.update_shift() | Có nhưng chưa được gọi | Hàm tồn tại trong `api_client.py:180-191` nhưng không trang nào gọi — ĐÚNG |

### ⚠️ Những điều PLAN nhận xét CHƯA CHÍNH XÁC hoặc cần làm rõ

#### 1. A3 — Vị trí lỗi được chỉ định sai
PLAN viết: *"schedule_planner.py:200-210"* — thực tế hàm `do_gen()` nằm ở scope **bên trong** `_generate_week()`, không phải dòng 200-210. Code thực tế:

```python
# schedule_planner.py — bên trong _generate_week() → do_gen()
result = api_client.generate_week_schedule(...)
if result:
    created = result.get("created", 0) if isinstance(result, dict) else 0
    common.show_notify(f"Phân lịch thành công: {created} ca", type="positive")
    # ← warnings[] ở đây bị bỏ qua hoàn toàn
```

**Chỉnh lại**: Lỗi nằm trong closure `do_gen` bên trong hàm `_generate_week()`.

#### 2. B1 — PLAN đánh giá "không cần hợp nhất" nhưng bỏ sót vấn đề code trùng lặp
`schedule_planner.py` và `week_view.py` có **code lặp 100%** cho `_render_week_grid` / `render_week_grid`. Cả 2 đều:
- Import và dùng `render_shift_card_compact`
- Cùng logic 5-column Mon-Fri với `timedelta`
- Cùng `_get_monday_of_week`, `_prev_week`, `_next_week`, `_today_week`

Đây là **DRY violation** — không chỉ là vấn đề UX mà còn là debt kỹ thuật. Nếu fix bug trong `render_week_grid` của `week_view.py`, phải nhớ fix cả `_render_week_grid` trong `schedule_planner.py`.

#### 3. PLAN bỏ sót: `week_view.py` THIẾU hiển thị `sp_warning` badge
`schedule_planner.py:_render_week_grid` có đoạn:
```python
if shift.get("sp_warning"):
    warn_label, warn_color = common.SP_WARNING_LABELS.get(...)
    ui.badge(warn_label, color=warn_color).classes("text-xs")
```
Nhưng `week_view.py:render_week_grid` **không có** đoạn này — người dùng xem `/lich-tuan` sẽ không thấy cảnh báo SP trên lịch read-only. Đây là bug thầm lặng.

#### 4. PLAN bỏ sót: `_generate_week` dialog thiếu feedback warning cho `overwrite_confirmed`
Checkbox "Ghi đè ca đã xác nhận ⚠️" không có giải thích rõ nguy cơ, và `show_notify` sau generate chỉ hiện số ca tạo được, không cảnh báo nếu có confirmed bị xóa.

#### 5. PLAN bỏ sót: `statistics.py` không có biểu đồ — nhưng API data đã sẵn sàng
`get_shift_count_by_person()` trả đủ `{full_name, role, normal, friday, cutoff, settlement_main, settlement_sub, total}`. Frontend chỉ đang render bảng text. Đây là quick win: thêm bar chart vào trang thống kê mà không cần sửa backend.

#### 6. PLAN bỏ sót: `schedule_service.get_monthly_summary` đếm CẢ draft lẫn confirmed
```python
# schedule_service.py
shifts = db.query(DutyShift).filter(
    DutyShift.shift_date.like(f"{prefix}%"),
    # ← không filter status
).all()
```
Trong khi `get_shift_count_by_person` chỉ đếm `status == "confirmed"`. Hai endpoint thống kê không nhất quán — người dùng sẽ thấy số liệu tháng khác số liệu theo người. **Đây là bug nghiệp vụ.**

---

## PHẦN 2 — ĐÁNH GIÁ LẠI ƯU TIÊN

### Điều chỉnh so với PLAN

| Mục | PLAN đề xuất | Review đề xuất | Lý do |
|-----|-------------|---------------|-------|
| A3 Warnings | Sprint 1 | **Giữ Sprint 1** ✅ | Đúng, nhưng cần sửa đúng vị trí trong code |
| A4 Edit dialog | Sprint 1 | **Giữ Sprint 1** ✅ | Đúng ưu tiên |
| B1 Week dedup | Giảm xuống Low | **Nâng lên Sprint 1** ⬆️ | Là DRY violation + bug (missing sp_warning badge) |
| B4 Bar chart | Sprint 2 | **Nâng lên Sprint 1** ⬆️ | Quick win: data đã có, chỉ thêm Chart.js |
| Bug monthly_summary | Không đề cập | **Thêm vào Sprint 1** 🆕 | Bug số liệu không nhất quán |
| B5 Unconfirm | Sprint 2 | **Giữ Sprint 2** ✅ | Đúng |
| B2 Month Calendar | Sprint 2 | **Giữ Sprint 2** ✅ | Đúng |
| C5 Toast/Loading | Sprint 1 | **Giữ Sprint 1** ✅ | Đúng |

---

## PHẦN 3 — ĐỀ XUẤT PHƯƠNG ÁN TỐI ƯU

### SPRINT 1 — Hoàn thiện nghiệp vụ & sửa bug (ưu tiên nhất)

#### [FIX-1] Bug: `get_monthly_summary` đếm cả draft
**File**: `backend/services/schedule_service.py`
**Thay đổi**: Thêm `.filter(DutyShift.status == "confirmed")` — 1 dòng, 5 phút.
```python
# TRƯỚC
shifts = db.query(DutyShift).filter(DutyShift.shift_date.like(f"{prefix}%")).all()
# SAU
shifts = db.query(DutyShift).filter(
    DutyShift.shift_date.like(f"{prefix}%"),
    DutyShift.status == "confirmed",
).all()
```

#### [FIX-2] Bug: `week_view.py` thiếu `sp_warning` badge
**File**: `frontend/pages/week_view.py` → hàm `render_week_grid()`
**Thay đổi**: Sau `render_shift_card_compact(shift)`, thêm:
```python
if shift.get("sp_warning"):
    warn_label, warn_color = common.SP_WARNING_LABELS.get(
        shift["sp_warning"], (shift["sp_warning"], "grey")
    )
    ui.badge(warn_label, color=warn_color).classes("text-xs")
```

#### [A3] Hiển thị warnings sau generate
**File**: `frontend/pages/schedule_planner.py` → closure `do_gen()` bên trong `_generate_week()`
**Thay đổi**: Sau `show_notify`, kiểm tra và hiển thị warnings:
```python
def do_gen():
    dlg.close()
    result = api_client.generate_week_schedule(...)
    if result:
        created = result.get("created", 0) if isinstance(result, dict) else 0
        warnings = result.get("warnings", []) if isinstance(result, dict) else []
        common.show_notify(f"Phân lịch thành công: {created} ca", type="positive")
        # ── THÊM: Hiển thị warnings nếu có ──
        if warnings:
            _show_warnings_dialog(warnings)
        if state.get("refresh"):
            state["refresh"]()
    else:
        common.show_notify("Lỗi phân lịch tuần", type="negative")

def _show_warnings_dialog(warnings: list):
    with ui.dialog() as dlg_warn, ui.card().classes("p-6 min-w-96 max-w-lg"):
        ui.label("⚠️ Cảnh báo sau phân lịch").classes("text-lg font-bold text-orange-7 mb-3")
        for w in warnings:
            icon = "🔴" if w.get("type") == "no_sp" else "⚠️"
            ui.label(f"{icon} {w.get('msg', '')}").classes("text-body2 text-grey-8 mb-1")
        with ui.row().classes("justify-end mt-4"):
            ui.button("Đã hiểu", on_click=dlg_warn.close).props("color=orange")
    dlg_warn.open()
```

#### [A4] Dialog sửa tay ca trực
**Phương án tối ưu**: Không cần chuyển sang `render_shift_card()` toàn bộ — chỉ cần thêm nút "✏️ Sửa" vào `render_shift_card_compact()` có điều kiện, và implement dialog:

**File 1**: `frontend/components/shift_card.py` — thêm tham số `on_edit_click=None` vào `render_shift_card_compact()`:
```python
def render_shift_card_compact(shift: dict, on_edit_click=None):
    # ... code hiện tại ...
    # Cuối hàm, thêm:
    if on_edit_click:
        ui.button("✏️", on_click=lambda s=shift: on_edit_click(s)
        ).props("size=xs flat dense color=blue-7").classes("mt-1")
```

**File 2**: `frontend/pages/schedule_planner.py` — thêm dialog và truyền callback:
```python
# Trong _render_week_grid(), thay:
render_shift_card_compact(shift)
# Thành:
render_shift_card_compact(shift, on_edit_click=lambda s: _open_edit_dialog(s, state))

def _open_edit_dialog(shift: dict, state: dict):
    all_staff = api_client.get_staff()
    ld_options = {s["id"]: s["full_name"] for s in all_staff if s["role"] == "LD"}
    sp_options  = {0: "(Không)", **{s["id"]: s["full_name"] for s in all_staff if s["role"] == "SP"}}
    nv_options  = {s["id"]: s["full_name"] for s in all_staff if s["role"] == "NV"}

    current_leader_id = shift.get("leader", {}).get("id") if shift.get("leader") else None
    current_sp_id     = shift.get("sp", {}).get("id") if shift.get("sp") else 0
    current_nv_ids    = [nv["id"] for nv in (shift.get("nvs") or [])]

    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-96"):
        ui.label(f"✏️ Sửa ca {shift.get('shift_date')}").classes("text-lg font-bold mb-4")
        sel_ld = ui.select(ld_options, value=current_leader_id, label="Lãnh đạo").classes("w-full mb-2")
        sel_sp = ui.select(sp_options, value=current_sp_id, label="Song Phương").classes("w-full mb-2")
        sel_nv = ui.select(nv_options, value=current_nv_ids, label="Nhân viên", multiple=True).classes("w-full mb-4")
        with ui.row().classes("justify-end gap-2"):
            ui.button("Hủy", on_click=dlg.close).props("flat")
            def save():
                nv_ids = sel_nv.value if isinstance(sel_nv.value, list) else [sel_nv.value]
                sp_id = sel_sp.value if sel_sp.value else None
                result = api_client.update_shift(
                    shift["id"],
                    leader_id=sel_ld.value,
                    sp_id=sp_id,
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
```

#### [REFACTOR-1] Loại bỏ code trùng lặp Week Grid
**File mới**: `frontend/components/week_grid.py`
**Nội dung**: Tách `render_week_grid()` thành component dùng chung, nhận thêm tham số `show_edit_button=False` và `show_warnings=True`.
**Sau đó** `schedule_planner.py` và `week_view.py` đều import từ đây. Loại bỏ ~60 dòng code trùng lặp.

#### [B4-quick] Thêm biểu đồ thống kê (Quick Win)
**File**: `frontend/pages/statistics.py`
**Phương án**: Dùng `ui.echart()` của NiceGUI (đã built-in, không cần cài thêm) để vẽ horizontal bar chart từ data `shift_counts` hiện có:
```python
def _render_shift_count_chart(state: dict):
    data = state.get("shift_counts", [])
    if not data:
        return
    # Lọc chỉ lấy người có total > 0, sort theo role rồi total
    items = sorted([d for d in data if d.get("total", 0) > 0],
                   key=lambda x: (_ROLE_ORDER.get(x.get("role"), 99), -x.get("total", 0)))
    names  = [d["full_name"] for d in items]
    totals = [d["total"] for d in items]
    avg    = sum(totals) / len(totals) if totals else 0

    chart_opt = {
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "value"},
        "yAxis": {"type": "category", "data": names},
        "series": [{
            "type": "bar", "data": totals,
            "markLine": {"data": [{"type": "average", "name": "TB"}]},
        }],
    }
    ui.echart(chart_opt).classes("w-full h-96")
```

#### [C5] Toast + Loading state đồng nhất
**Phương án**: Bổ sung wrapper `_with_loading(label, fn)` vào `common.py`:
```python
def with_loading(label: str, fn, on_done=None):
    """Chạy fn() với spinner, notify kết quả."""
    notif = ui.notify(label, type="ongoing", spinner=True, timeout=0)
    try:
        result = fn()
        notif.dismiss()
        if on_done:
            on_done(result)
        return result
    except Exception as e:
        notif.dismiss()
        show_notify(f"Lỗi: {e}", type="negative")
        return None
```
Áp dụng cho: generate_week, confirm_week, delete_week, export.

---

### SPRINT 2 — Tính năng còn thiếu

#### [B5] Unconfirm ca
**Backend** (1 endpoint mới):
```python
# backend/routers/schedule.py
@router.patch("/{shift_id}/unconfirm", response_model=dict)
def unconfirm_shift(shift_id: int, db: Session = Depends(get_db)):
    shift = db.query(DutyShift).filter_by(id=shift_id).first()
    if not shift:
        raise HTTPException(404, "Không tìm thấy ca")
    shift.status = "draft"
    db.commit()
    return {"id": shift.id, "status": shift.status}
```
**Frontend**: Trong edit dialog (A4 đã có), thêm nút "Huỷ xác nhận" màu đỏ, chỉ hiện khi `shift["status"] == "confirmed"`.

#### [B2] Month Calendar View
**Phương án tối ưu**: Thêm route `/lich-thang` mới — không modify code hiện có.
**UI**: Grid 5 cột × N hàng (theo tuần trong tháng). Mỗi ô hiện tên LĐ + badge cảnh báo nếu có.
**API**: Dùng `api_client.get_schedule(month, year)` đã có sẵn.
**Navbar**: Thêm mục "📆 Lịch tháng" vào `common.create_navbar()`.

#### [C2] Filter nhân sự
**Phương án tối ưu**: Thêm combobox "Lọc theo người" vào schedule_planner — khi chọn, highlight các ô ngày có người đó bằng màu nền khác. Không cần API mới — lọc client-side từ data đã load.

---

### SPRINT 3 — Cải thiện dài hạn

#### [B3] Đi dự án theo date-range
**Phương án**: Thêm bảng `project_assignments` (staff_id, from_date, to_date) vào DB.
`staff_service.get_available_pool()` kiểm tra ngày hiện tại có trong range nào không, nếu có → loại khỏi pool. Cần Alembic migration.

#### [C1] Dashboard tổng quan
**Route**: `/` hoặc `/dashboard` (chuyển schedule_planner sang `/phan-lich`).
**3 widget**: tuần hiện tại (compact), cảnh báo pending (shifts có sp_warning), số liệu tháng (từ monthly_summary).

#### [D4] Print-friendly view
**Phương án**: Thêm parameter `?print=1` cho `/lich-tuan` — khi có param này, không render navbar và action buttons, thêm CSS `@media print`. Không cần route mới.

#### [D5] Backup/Restore DB
**Phương án đơn giản**: Endpoint `GET /export/db-backup` trả file `duty_scheduler.db` dưới dạng binary download. Restore = upload file, thay thế DB cũ (với cảnh báo).

---

## PHẦN 4 — CÁC VẤN ĐỀ KỸ THUẬT BỔ SUNG (chưa có trong PLAN)

### T1. Thiếu `delete_week` trong API endpoint nhưng có trong `api_client.py`
`api_client.delete_week_schedule()` gọi `DELETE /schedule/week?week_start=...` với `httpx.delete()` trực tiếp (bypass `_delete()` helper). Endpoint này **tồn tại** trong `backend/routers/schedule.py`. Không phải bug nhưng inconsistent coding style.

### T2. `confirm_dialog` trong `common.py` dùng `color=negative` cho nút confirm
```python
ui.button(confirm_label, on_click=...).props("color=negative")
```
Tất cả confirm actions (kể cả "Xác nhận tuần" — là hành động tích cực) đều có nút màu đỏ. Nên dùng `color` là tham số của `confirm_dialog()`.

### T3. Hard-coded `SP_BACKUP_LEADERS` không có UI quản lý
```python
# config.py
SP_BACKUP_LEADERS = ["Trần Thị Mỹ Linh", "Trần Thị Bích Phương"]
```
Nếu nhân sự thay đổi, phải sửa code và restart. **Đề xuất**: Thêm field `is_sp_backup: bool` vào bảng `staff` và UI toggle trong trang Danh sách. Không cần bảng mới, chỉ thêm 1 cột.

### T4. `generate_schedule_for_week` không có transaction rollback
Nếu sinh ca thứ 3/5 bị lỗi, 2 ca đầu đã được `db.flush()` nhưng `db.commit()` cuối sẽ không được gọi. Tuy nhiên, nếu có exception chưa bắt được, có thể dẫn đến partial write. **Đề xuất**: Bọc toàn bộ loop trong `try/except` với `db.rollback()` khi lỗi.

### T5. `api_client._delete()` trả `bool` nhưng không phân biệt 404 vs network error
Cả "không tìm thấy" và "không kết nối được backend" đều trả `False`. **Đề xuất**: Trả về `Optional[str]` với error message, hoặc ít nhất log HTTP status code.

---

## PHẦN 5 — LỘ TRÌNH TỐI ƯU ĐỀ XUẤT

### Sprint 1 — ~4 ngày dev
```
Ngày 1:
  [FIX-1] Bug monthly_summary đếm draft          (15 phút)
  [FIX-2] Bug week_view thiếu sp_warning badge    (15 phút)
  [T2]    Fix confirm_dialog color                (10 phút)
  [A3]    Warnings dialog sau generate            (2-3 giờ)

Ngày 2:
  [REFACTOR-1] Tách week_grid component dùng chung  (3-4 giờ)
  [C5]         Toast + loading wrapper              (2 giờ)

Ngày 3-4:
  [A4]    Dialog sửa tay ca (phức tạp nhất Sprint 1)  (1 ngày)
  [B4-quick] Biểu đồ bar chart thống kê               (3-4 giờ)
```

### Sprint 2 — ~5 ngày dev
```
Ngày 5:    [B5] Unconfirm endpoint + UI           (3-4 giờ)
Ngày 5:    [T3] is_sp_backup field + UI toggle    (3-4 giờ)
Ngày 6-7:  [B2] Month Calendar View               (1.5 ngày)
Ngày 8:    [C2] Filter nhân sự trong lịch tuần    (4 giờ)
Ngày 9:    [T4] Transaction rollback + [T5] Error handling  (4 giờ)
```

### Sprint 3 — ~6 ngày dev
```
Ngày 10-11: [C1] Dashboard tổng quan
Ngày 12-13: [B3] Project date-range (cần migration)
Ngày 14:    [D4] Print view
Ngày 15:    [D5] DB backup/restore
```

---

## PHẦN 6 — TÓM TẮT ĐIỂM KHÁC BIỆT SO VỚI PLAN GỐC

| # | Điểm khác biệt | Mức độ ảnh hưởng |
|---|---------------|-----------------|
| 1 | Thêm **2 bug fixes** không có trong PLAN (monthly_summary + week_view sp_warning) | 🔴 Cao — ảnh hưởng số liệu + UX |
| 2 | Nâng ưu tiên **B4 bar chart** lên Sprint 1 (quick win, data đã có) | 🟠 Trung bình |
| 3 | Nâng ưu tiên **B1 DRY refactor** lên Sprint 1 (không chỉ là UX) | 🟠 Trung bình |
| 4 | Chỉ định **đúng vị trí code** cho A3 (closure `do_gen`, không phải dòng 200-210) | 🟡 Nhỏ — quan trọng khi implement |
| 5 | Thêm **T3 is_sp_backup field** — loại bỏ hard-code tên người | 🟠 Trung bình — liên quan nghiệp vụ |
| 6 | Đề xuất **T4 rollback** cho scheduler_engine | 🟡 Nhỏ — defensive coding |
| 7 | **Print view**: đề xuất dùng `?print=1` param thay vì route mới | 🟡 Nhỏ — đơn giản hơn |
| 8 | **Unconfirm**: backend chỉ cần 1 PATCH endpoint, không cần thiết kế phức tạp | 🟡 Nhỏ |

---

*Tổng ước lượng hoàn thiện: **~15 ngày dev** (không đổi so với PLAN), nhưng Sprint 1 tăng từ 2 lên 4 ngày do bổ sung bug fixes + quick wins có giá trị cao.*
