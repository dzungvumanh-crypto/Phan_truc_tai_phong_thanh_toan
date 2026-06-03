# REVIEW v2 — Kế hoạch Hoàn thiện Phân lịch trực PTT
## Phân tích toàn diện codebase · Claude Sonnet 4.6 · 2026-05-29

> **Phương pháp**: Đọc trực tiếp 100% file source (backend + frontend), đối chiếu từng mục PLAN v2 với code thực tế. PLAN v2 đã tích hợp tốt các phát hiện từ REVIEW v1. Review này tập trung vào **những gì còn bỏ sót** và **đề xuất phương án implement cụ thể nhất**.

---

## PHẦN 1 — XÁC NHẬN PLAN v2

PLAN v2 chính xác và đầy đủ ở các mục sau — **không cần điều chỉnh**:

| Mục | Nội dung | Xác nhận |
|-----|---------|----------|
| A1, A2 | Export Excel & Confirm cutoff đã xong | ✅ Chính xác |
| FIX-1 | `get_monthly_summary` thiếu filter confirmed | ✅ Chính xác — 1 dòng fix |
| FIX-2 | `week_view.py` thiếu sp_warning badge | ✅ Chính xác |
| A3 | Warnings bỏ qua trong `do_gen()` closure | ✅ Chính xác |
| A4 | `on_edit_click` stub, `update_shift()` chưa được gọi | ✅ Chính xác |
| B1 | DRY violation ~60 dòng giữa 2 trang | ✅ Chính xác |
| T2–T5 | Các vấn đề kỹ thuật nhỏ | ✅ Chính xác |

---

## PHẦN 2 — BỔ SUNG: 6 VẤN ĐỀ PLAN v2 CHƯA ĐỀ CẬP

### V1. `ShiftUpdate` schema có bug tiềm ẩn: không thể xóa SP

```python
# backend/schemas/duty_schemas.py
class ShiftUpdate(BaseModel):
    leader_id: Optional[int] = None
    sp_id:     Optional[int] = None   # ← None = "không truyền" hay "xóa SP"?
    nv_ids:    List[int] = []
    sp_warning: Optional[str] = None
```

```python
# backend/services/schedule_service.py — update_shift()
if sp_id is not None:
    shift.sp_id = sp_id   # ← chỉ update nếu truyền, KHÔNG BAO GIỜ xóa được
```

**Hậu quả**: Nếu người dùng muốn bỏ trống slot SP (chuyển từ ca có SP sang `no_sp`), không có cách nào làm điều đó qua UI. Truyền `sp_id=None` sẽ bị bỏ qua. Đây là bug ảnh hưởng trực tiếp đến tính năng A4 (dialog sửa tay) đang lên kế hoạch implement.

**Fix**: Dùng sentinel value hoặc thêm field `clear_sp: bool = False` vào schema:
```python
class ShiftUpdate(BaseModel):
    leader_id:  Optional[int] = None
    sp_id:      Optional[int] = None
    clear_sp:   bool = False           # True = đặt sp_id = NULL
    nv_ids:     List[int] = []
    sp_warning: Optional[str] = None

# service:
if body.clear_sp:
    shift.sp_id = None
elif body.sp_id is not None:
    shift.sp_id = body.sp_id
```

---

### V2. `validate_nv_request` KHÔNG cross-check với bảng `absences`

```python
# backend/services/constraint_service.py — validate_nv_request()
def validate_nv_request(db, staff_id, date_str, year):
    config = get_shift_config(db, year)
    max_slots = config.nv_count if config else DEFAULT_NV_COUNT
    current = count_nv_requests_for_date(db, date_str, year)
    # ← Không có dòng nào kiểm tra absences của staff_id
    if current >= max_slots:
        return False, msg, current, max_slots
    return True, "OK", current, max_slots
```

**Hậu quả**: NV có thể đăng ký xin trực vào ngày mà họ đã khai báo vắng — PLAN v2 đã ghi nhận trong mục "Thiếu validation" nhưng chưa xếp vào sprint nào và chưa có code fix.

**Fix đề xuất** (thêm vào Sprint 1 cùng FIX-1, FIX-2 — chỉ 3 dòng):
```python
# Trong validate_nv_request, trước khi check max_slots:
from backend.services.staff_service import get_absent_staff_ids
absent_ids = get_absent_staff_ids(db, date_str)
if staff_id in absent_ids:
    return False, f"Nhân sự đã khai báo vắng ngày {date_str}", 0, max_slots
```

---

### V3. `startup_init` chỉ seed dữ liệu cho `CURRENT_YEAR` — bỏ sót năm cũ khi nâng cấp

```python
# backend/services/schedule_service.py — startup_init()
def startup_init(db):
    year = CURRENT_YEAR   # ← chỉ năm hiện tại
    seed_staff(db)
    upsert_shift_config(db, year, DEFAULT_NV_COUNT)
    seed_holidays(db, year)
    init_rotation_for_year(db, year)
```

**Vấn đề**: Khi deploy đầu năm 2027, hệ thống sẽ seed ngày lễ 2027 nhưng dữ liệu 2026 không có ngày lễ đầy đủ (nếu chạy lần đầu vào 2026). Quan trọng hơn: `init_rotation_for_year` chỉ tạo rotation cho năm hiện tại — nếu có staff mới tạo giữa năm, họ sẽ không có rotation rows cho các loại ca.

Tuy nhiên, đây là edge case thấp tác động. Đưa vào **Sprint 3** như một defensive improvement.

---

### V4. `get_week_assignees` trong `constraint_service.py` đọc **cả ca draft** khi tính "đã trực trong tuần"

```python
# constraint_service.py — get_week_assignees()
shifts = db.query(DutyShift).filter(
    DutyShift.shift_date >= week_start.isoformat(),
    DutyShift.shift_date < date_str,
    # ← không có filter status
).all()
```

**Hậu quả**: Khi generate lịch theo ngày trong tuần, thuật toán tránh phân cùng người 2 lần/tuần bằng cách đọc "ai đã được phân rồi". Nếu có ca `draft` từ tuần trước (chưa confirm, chưa xóa) rơi vào cùng tuần, người đó sẽ bị coi là "đã trực" và bị bỏ qua — ngay cả khi ca draft đó sẽ bị overwrite.

**Mức độ**: Trung bình. Chỉ xảy ra khi có draft cũ trong DB. Fix: thêm `.filter(DutyShift.status == "confirmed")` hoặc không filter (coi draft cũng hợp lệ — đây là quyết định nghiệp vụ cần confirm với người dùng).

---

### V5. `confirm_shifts_for_week` dùng `.update()` bulk — bỏ qua ORM events

```python
# schedule_service.py
count = db.query(DutyShift).filter(...).update(
    {"status": "confirmed"}, synchronize_session=False
)
```

Bulk `.update()` bypass SQLAlchemy ORM layer — nếu sau này thêm `@event.listens_for` trên `DutyShift` (ví dụ: ghi audit log khi status thay đổi), những event đó sẽ không được trigger. Đây là technical debt nhỏ nhưng cần biết trước khi mở rộng.

---

### V6. `delete_staff` dùng `LIKE` string-match để dọn NV trong shifts — unsafe với ID > 9

```python
# staff_service.py — delete_staff()
shifts = db.query(DutyShift).filter(
    DutyShift.nv_ids.like(f'%{staff_id}%')
).all()
```

Nếu `staff_id = 1`, query này sẽ match cả ca có `nv_ids = "[11, 13, 21]"` (vì `"1"` có trong chuỗi `"11"`). Kết quả: `nv_id = 1` sẽ bị filter ra khỏi một ca mà anh ta không có mặt, nhưng `nv_id = 11` cũng bị loại nhầm.

**Fix đúng**: Dùng `DutyShiftNV` table (đã có sẵn!) thay vì LIKE trên JSON string:
```python
# Thay toàn bộ đoạn LIKE bằng:
shift_ids_with_staff = db.query(DutyShiftNV.shift_id).filter_by(staff_id=staff_id).all()
shift_ids = [row[0] for row in shift_ids_with_staff]
if shift_ids:
    for shift in db.query(DutyShift).filter(DutyShift.id.in_(shift_ids)).all():
        nv_list = json.loads(shift.nv_ids or "[]")
        nv_list = [nid for nid in nv_list if nid != staff_id]
        shift.nv_ids = json.dumps(nv_list)
        shift.nv_count = len(nv_list)
    db.query(DutyShiftNV).filter_by(staff_id=staff_id).delete()
```

**Mức độ**: Cao nếu staff_id có chữ số trùng nhau (1, 10, 11, 21...). Hiện tại với 25 người fixed thì ít gặp, nhưng là bug thực sự.

---

## PHẦN 3 — ĐÁNH GIÁ LẠI & ĐỀ XUẤT PHƯƠNG ÁN TỐI ƯU

### 3.1 Điều chỉnh ưu tiên Sprint

| Mục | PLAN v2 | Review v2 | Lý do |
|-----|---------|-----------|-------|
| FIX-1 + FIX-2 | Sprint 1 | ✅ Giữ | Đúng |
| **V1** ShiftUpdate clear_sp | Chưa có | **Thêm Sprint 1** 🆕 | Block A4 nếu thiếu |
| **V2** Validate absence | Chưa có sprint | **Thêm Sprint 1** 🆕 | 3 dòng fix, nghiệp vụ rõ |
| **V6** delete_staff LIKE bug | Chưa có | **Thêm Sprint 1** 🆕 | Bug thực sự, fix đơn giản |
| A3 | Sprint 1 | ✅ Giữ | Đúng |
| A4 | Sprint 1 | ✅ Giữ, nhưng làm sau V1 | V1 phải fix trước |
| B1 DRY refactor | Sprint 1 | ✅ Giữ | Đúng |
| B4 bar chart | Sprint 1 | ✅ Giữ | Quick win |
| C5 Toast/Loading | Sprint 1 | ✅ Giữ | Đúng |
| **V4** get_week_assignees | Chưa có | **Thêm Sprint 2** 🆕 | Cần quyết định nghiệp vụ |
| B5 Unconfirm | Sprint 2 | ✅ Giữ | Đúng |
| T3 is_sp_backup | Sprint 2 | ✅ Giữ | Đúng |
| B2 Month Calendar | Sprint 2 | ✅ Giữ | Đúng |
| **V3** startup multi-year | Chưa có | **Thêm Sprint 3** 🆕 | Edge case, thấp ưu tiên |

---

### 3.2 Phương án implement tối ưu cho từng hạng mục Sprint 1

#### [V1 + A4] ShiftUpdate fix + Dialog sửa tay — làm cùng lượt

**Nguyên tắc**: Fix schema trước, rồi implement UI. Thứ tự: `duty_schemas.py` → `schedule_service.py` → `shift_card.py` → `schedule_planner.py`.

**Lưu ý UX quan trọng cho A4 dialog**: `ShiftUpdate.nv_ids` có default `[]` — nếu dialog gửi `nv_ids=[]` (người dùng bỏ chọn hết NV), sẽ xóa sạch NV của ca. Cần hiện warning khi NV list trống.

#### [A3] Warnings dialog — phương án tối giản nhất

Thay vì tạo function riêng, dùng `ui.notify` nhiều lần (mỗi warning 1 toast):
```python
# Trong do_gen():
warnings = result.get("warnings", []) if isinstance(result, dict) else []
for w in warnings:
    icon = "🔴" if w.get("type") in ("no_sp", "no_leader") else "⚠️"
    common.show_notify(f"{icon} {w.get('msg', '')}", type="warning", timeout=8000)
```
Nếu có nhiều warnings (> 3), dùng dialog tổng hợp. Logic: `if len(warnings) > 3: _show_warnings_dialog(warnings) else: [show_notify for each]`.

#### [B1] DRY refactor — phương án an toàn nhất

**Không tách file mới ngay** — rủi ro import cycle trong NiceGUI. Thay vào đó:
1. Đưa `render_week_grid()` vào `frontend/components/shift_card.py` (đã có `render_shift_card_compact`)
2. Hoặc tạo `frontend/components/week_grid.py` và test import cẩn thận

**Tham số đề xuất**:
```python
def render_week_grid(
    state: dict,
    show_warnings: bool = True,      # week_view = True, schedule_planner = True
    on_edit_click=None,              # None = không hiện nút sửa
    highlight_staff_id: int = None,  # C2: filter nhân sự
):
```

#### [B4] Bar chart — dùng NiceGUI `ui.echart` built-in

`requirements.txt` không có `chart.js` hay `plotly` — nhưng NiceGUI ≥ 3.0.0 đã bundle **ECharts** (`ui.echart`). Dùng trực tiếp, không cần cài thêm:

```python
# statistics.py — thêm sau _render_shift_count_table()
def _render_shift_count_chart(state: dict):
    data = [d for d in state.get("shift_counts", []) if d.get("total", 0) > 0]
    if not data:
        return
    # Sort: LD trước, rồi theo total DESC
    data.sort(key=lambda x: (_ROLE_ORDER.get(x.get("role"), 99), -x.get("total", 0)))
    
    avg = sum(d["total"] for d in data) / len(data)
    names  = [d["full_name"] for d in data]
    totals = [d["total"] for d in data]
    colors = ["#1976D2" if d["role"]=="LD" else "#7B1FA2" if d["role"]=="SP" else "#388E3C"
              for d in data]

    opt = {
        "grid": {"left": "180px", "right": "40px"},
        "xAxis": {"type": "value", "name": "Số ca"},
        "yAxis": {"type": "category", "data": names, "axisLabel": {"fontSize": 11}},
        "series": [{
            "type": "bar",
            "data": [{"value": v, "itemStyle": {"color": c}} for v, c in zip(totals, colors)],
            "markLine": {"data": [{"xAxis": avg, "name": f"TB: {avg:.1f}"}]},
            "label": {"show": True, "position": "right"},
        }],
        "tooltip": {"trigger": "axis"},
    }
    ui.echart(opt).classes("w-full").style("height: 400px")
```

#### [C5] Toast + Loading — pattern đề xuất cho NiceGUI

NiceGUI không có async spinner đơn giản, nhưng `ui.notify` với `type="ongoing"` và `spinner=True` hoạt động tốt:

```python
# common.py — thêm:
def run_with_feedback(
    action_fn,
    loading_msg: str = "Đang xử lý...",
    success_msg: str = "Thành công",
    error_msg: str = "Có lỗi xảy ra",
    on_success=None,
):
    """Wrapper: hiện spinner → chạy action → notify kết quả."""
    notif = ui.notify(loading_msg, type="ongoing", spinner=True, timeout=0)
    try:
        result = action_fn()
        notif.dismiss()
        if result is not False and result is not None:
            show_notify(f"✅ {success_msg}", type="positive")
            if on_success:
                on_success(result)
        else:
            show_notify(f"❌ {error_msg}", type="negative")
        return result
    except Exception as e:
        notif.dismiss()
        show_notify(f"❌ {error_msg}: {e}", type="negative")
        return None
```

---

### 3.3 Phương án B2 Month Calendar — thiết kế chi tiết

**Route mới**: `/lich-thang` — thêm vào `frontend/main.py` và navbar.

**Data**: `api_client.get_schedule(month, year)` đã có, trả `List[dict]` với `shift_date`, không cần API mới.

**UI layout** (calendar grid 5 cột × N hàng):
```
[Thứ 2] [Thứ 3] [Thứ 4] [Thứ 5] [Thứ 6]
  01/01   02/01   03/01   04/01   05/01
  LĐ: X   LĐ: Y   🔴Thiếu  LĐ: Z  ⚠️LĐ+SP
  SP: A   SP: B   SP: ?   SP: C   
  NV: D,E  NV: F  NV: G   NV: H,I
─────────────────────────────────────────
  08/01   09/01  ...
```

**Tối ưu hiệu năng**: Gọi API 1 lần cho cả tháng (đã có), không gọi per-day. Render ngày nghỉ lễ màu xám (cần gọi thêm `api_client.get_special_days(month, year, day_type="holiday")`).

---

### 3.4 Đề xuất bổ sung ngoài PLAN: `B6` — Confirm ca đơn lẻ từ shift card

**Hiện trạng**: Có `confirm_week` (xác nhận cả tuần) và `confirm_all` (cả tháng), nhưng không có cách xác nhận **1 ca riêng lẻ** từ UI.

**Usecase thực tế**: Trong 1 tuần, 4 ca đã OK nhưng 1 ca cần chỉnh lại — người dùng muốn confirm 4 ca còn lại trước.

**Backend**: `PUT /schedule/{shift_id}/confirm` đã có trong `routers/schedule.py` và `api_client.confirm_shift()` đã có.

**Frontend**: Chỉ cần thêm nút "✅ Confirm" nhỏ vào `render_shift_card_compact()` khi `status == "draft"`, tương tự nút sửa. Ưu tiên thấp hơn A4 nhưng implement cùng lúc sẽ rẻ hơn.

---

## PHẦN 4 — LỘ TRÌNH TỐI ƯU ĐỀ XUẤT (cập nhật)

### Sprint 1 — ~4.5 ngày dev

```
Ngày 1 — Bug fixes (ít rủi ro nhất, làm đầu tiên):
  [FIX-1]  schedule_service.py: thêm filter confirmed vào get_monthly_summary        (10 phút)
  [FIX-2]  week_view.py: thêm sp_warning badge vào render_week_grid                  (15 phút)
  [V2]     constraint_service.py: validate absence trước khi cho đăng ký xin trực    (15 phút)
  [V6]     staff_service.py: fix delete_staff LIKE bug — dùng DutyShiftNV table      (30 phút)
  [T2]     common.py: thêm confirm_color param vào confirm_dialog                    (15 phút)

Ngày 2 — Warnings + Loading:
  [A3]     schedule_planner.py: hiển thị warnings[] sau generate                     (3-4 giờ)
  [C5]     common.py: run_with_feedback wrapper + áp dụng cho các actions chính      (3-4 giờ)

Ngày 3 — DRY Refactor:
  [B1]     Tách week_grid component dùng chung                                        (1 ngày)

Ngày 4-4.5 — Sửa tay ca:
  [V1]     duty_schemas.py + schedule_service.py: fix ShiftUpdate clear_sp            (1 giờ)
  [A4]     shift_card.py + schedule_planner.py: edit dialog + callback               (1 ngày)
  [B6]     Confirm ca đơn lẻ từ shift card (làm cùng A4)                             (1 giờ)

Ngày 4.5 — Quick win chart:
  [B4]     statistics.py: thêm ui.echart bar chart                                   (3-4 giờ)
```

### Sprint 2 — ~5.5 ngày dev

```
[B5]  backend: PATCH /schedule/{shift_id}/unconfirm + frontend UI               (4 giờ)
[T3]  Thêm is_sp_backup field vào Staff + UI toggle + replace config.py          (1 ngày)
[V4]  Xác nhận nghiệp vụ: get_week_assignees có filter confirmed không?          (2 giờ)
[B2]  Month Calendar View — trang /lich-thang mới                                (1.5 ngày)
[C2]  Filter nhân sự trong lịch tuần (client-side, highlight)                    (4 giờ)
[T4]  scheduler_engine.py: rollback khi exception                                (2 giờ)
[T5]  api_client.py: phân biệt error types                                       (2 giờ)
```

### Sprint 3 — ~6 ngày dev

```
[C1]  Dashboard tổng quan (/ hoặc route mới)
[B3]  Project date-range (cần DB migration, đề xuất dùng bảng project_assignments mới)
[V3]  startup_init: seed multi-year
[D4]  Print view (?print=1 param, không cần route mới)
[D5]  DB backup endpoint GET /export/db-backup
[D1]  Import lịch sử Excel (phức tạp nhất, làm cuối)
```

---

## PHẦN 5 — TÓM TẮT ĐIỂM KHÁC BIỆT SO VỚI PLAN v2

| # | Phát hiện mới | Sprint | Mức độ |
|---|---------------|--------|--------|
| V1 | `ShiftUpdate` không thể xóa SP — block A4 | Sprint 1 | 🔴 Cao |
| V2 | `validate_nv_request` không check absence | Sprint 1 | 🔴 Cao (3 dòng fix) |
| V6 | `delete_staff` LIKE bug với ID trùng chữ số | Sprint 1 | 🔴 Cao |
| V4 | `get_week_assignees` đọc cả draft shifts | Sprint 2 | 🟠 Trung bình |
| V3 | `startup_init` chỉ seed năm hiện tại | Sprint 3 | 🟡 Thấp |
| V5 | Bulk `.update()` bypass ORM events | Sprint 3 | 🟡 Thấp (note kỹ thuật) |
| B6 | Confirm ca đơn lẻ từ shift card | Sprint 1 (cùng A4) | 🟢 Quick win |
| B2 | Thiết kế chi tiết Month Calendar | Sprint 2 | — |
| A4 | Fix V1 trước khi implement dialog | Sprint 1 | — |

**Tổng ước lượng**: ~16 ngày dev (tăng 1 ngày do thêm V1/V2/V6/B6), chất lượng nghiệp vụ tốt hơn đáng kể.

---

## PHẦN 6 — CHECKLIST IMPLEMENT SPRINT 1 (sẵn sàng code)

Thứ tự thực hiện đề xuất để tránh conflict:

```
□ 1. backend/services/schedule_service.py   — FIX-1 (confirmed filter)
□ 2. frontend/pages/week_view.py            — FIX-2 (sp_warning badge)
□ 3. backend/services/constraint_service.py — V2 (absence check)
□ 4. backend/services/staff_service.py      — V6 (delete LIKE bug)
□ 5. frontend/components/common.py          — T2 + C5 (confirm color + run_with_feedback)
□ 6. backend/schemas/duty_schemas.py        — V1 (clear_sp field)
□ 7. backend/services/schedule_service.py   — V1 (update_shift handle clear_sp)
□ 8. frontend/pages/schedule_planner.py     — A3 (warnings dialog trong do_gen)
□ 9. frontend/components/week_grid.py       — B1 (tách component mới)
□ 10. frontend/pages/schedule_planner.py    — B1 (import từ week_grid)
□ 11. frontend/pages/week_view.py           — B1 (import từ week_grid, xóa code cũ)
□ 12. frontend/components/shift_card.py     — A4 + B6 (thêm on_edit_click, on_confirm)
□ 13. frontend/pages/schedule_planner.py    — A4 + B6 (implement dialogs)
□ 14. frontend/pages/statistics.py          — B4 (thêm ui.echart chart)
```
