# REVIEW v3 — Kế hoạch Hoàn thiện Phân lịch trực PTT
## Phân tích toàn diện codebase · Claude Sonnet 4.6 · 2026-05-29

> **Bối cảnh**: PLAN v2 (được upload) đã tích hợp đầy đủ REVIEW v1 và REVIEW v2. Review này **chỉ tập trung vào những vấn đề chưa từng được đề cập trước đó**, phát hiện từ việc đọc các file chưa được phân tích kỹ: `export_service.py`, `settings.py` (đầy đủ), `constraint_service.py` (phần request), và kiểm tra cross-cutting concerns.

---

## PHẦN 1 — XÁC NHẬN PLAN v2: ĐÚNG & ĐẦY ĐỦ

PLAN v2 đã chính xác và đầy đủ về tất cả các mục đã đề cập. Không có điểm nào trong PLAN v2 sai về mặt kỹ thuật. Review này bổ sung thêm.

---

## PHẦN 2 — 8 VẤN ĐỀ MỚI HOÀN TOÀN (chưa có trong bất kỳ review nào)

### N1. 🔴 Hard-coded tên người ký trong file Excel xuất — nghiệp vụ dễ sai

```python
# backend/services/export_service.py — dòng 288
ws.cell(row=note_row, column=5).value = "Nguyễn Quốc Hùng"
```

Tên người ký lịch trực bị hard-code thẳng vào `export_service.py`. Nếu người ký thay đổi (nhân sự nghỉ, bổ nhiệm mới), phải sửa code và restart backend. Đây là loại thay đổi mà người dùng cuối không thể tự làm.

**Fix đề xuất**: Thêm field `signer_name` vào bảng `shift_config` (hoặc tạo bảng `app_config` key-value), expose qua UI Settings Tab 1, và đọc động khi build Excel:

```python
# Thay dòng hard-code bằng:
config = get_shift_config(db, year)
signer = getattr(config, "signer_name", None) or "Nguyễn Quốc Hùng"
ws.cell(row=note_row, column=5).value = signer
```

**File cần sửa**: `backend/models/duty_models.py` (thêm column), `backend/services/export_service.py`, `frontend/pages/settings.py` (Tab 1 thêm field), `backend/schemas/duty_schemas.py`.

**Sprint**: Sprint 2 — không blocking nhưng dễ bị phát hiện khi dùng thực tế.

---

### N2. 🔴 Settings Tab "Đăng ký trực" cho phép LD và SP đăng ký — vi phạm nghiệp vụ

```python
# frontend/pages/settings.py — form đăng ký trực
staff_options = {
    s["id"]: f"{s['full_name']} ({s['role']})"
    for s in all_staff          # ← tất cả nhân sự, kể cả LD và SP
}
```

```python
# backend/routers/constraints.py — create_request()
if staff.role == "NV" and body.request_type == "once" and body.specific_date:
    allowed, msg, _, _ = constraint_service.validate_nv_request(...)
    if not allowed:
        raise HTTPException(400, msg)
# ← LD và SP không bị validate gì → có thể đăng ký không giới hạn
```

**Hậu quả nghiệp vụ**: LD và SP có thể "đăng ký xin trực" vào bất kỳ ngày nào, vô hạn lần, không qua bất kỳ validation nào. Scheduler engine sẽ ưu tiên họ ngày đó — làm lệch vòng xoay. Đây là lỗ hổng nghiệp vụ quan trọng.

**Câu hỏi nghiệp vụ cần xác nhận**: LD và SP có được phép "đăng ký xin trực" không? Nếu có → cần thêm validation tương tự NV. Nếu không → dropdown chỉ hiện NV.

**Fix an toàn nhất** (nếu chỉ NV được đăng ký):
```python
# settings.py — lọc chỉ NV
staff_options = {
    s["id"]: s["full_name"]
    for s in all_staff if s["role"] == "NV"
}
```

**Sprint**: Sprint 1 — ảnh hưởng trực tiếp đến tính đúng đắn của vòng xoay.

---

### N3. 🔴 `create_request` không có idempotency check — tạo duplicate đăng ký

```python
# backend/services/constraint_service.py — create_request()
def create_request(db, staff_id, request_type, year, ...):
    obj = DutyRequest(staff_id=staff_id, request_type=request_type, ...)
    db.add(obj)  # ← không check existing
    db.commit()
    return obj
```

Không có `UniqueConstraint` trên `(staff_id, request_type, specific_date, year)` và không có check trước khi tạo. User bấm nút "Thêm" 2 lần → 2 bản ghi identical → scheduler engine đọc đăng ký lần nào cũng thấy người này, ưu tiên kép.

So sánh: `create_absence` có check idempotent, `create_special_day` có check upsert — nhưng `create_request` không có.

**Fix**:
```python
def create_request(db, staff_id, request_type, year, specific_date=None, day_of_week=None):
    # Check duplicate trước
    existing = db.query(DutyRequest).filter_by(
        staff_id=staff_id, request_type=request_type,
        specific_date=specific_date, day_of_week=day_of_week, year=year
    ).first()
    if existing:
        return existing   # idempotent
    obj = DutyRequest(...)
    db.add(obj)
    db.commit()
    return obj
```

**Sprint**: Sprint 1 — dễ fix, ít rủi ro.

---

### N4. 🟠 Export Excel không hiển thị ngày lễ — file xuất thiếu thông tin quan trọng

```python
# backend/services/export_service.py — build_week_excel()
# Chỉ iterate Mon-Fri, không biết ngày nào là lễ
while current <= week_end:
    wd = current.weekday()
    if wd >= 5:   # bỏ qua T7, CN
        current += timedelta(days=1)
        continue
    date_str = current.strftime("%Y-%m-%d")
    day_shifts = shift_by_date.get(date_str, [])
    # ← nếu ngày lễ (không có shift), hiện ô trắng
    if main_shift is None and sub_shift is None:
        _apply_row(ws, current_row, [thu_label, date_label, "", "", "", "", "", ""])
```

Khi tuần có ngày lễ, file Excel xuất ra có hàng trắng — người đọc không biết đó là "trống chưa phân" hay "nghỉ lễ". Trong thực tế vận hành, đây là thông tin quan trọng phân biệt.

**Fix**: Truyền thêm `holiday_dates: set` vào `build_week_excel()`, hiển thị "(Nghỉ lễ: {tên lễ})" trong cột SP/NV với màu xám:

```python
# export_router.py — thêm:
holiday_dates = constraint_service.get_holiday_dates(db, start.year)
excel_bytes = export_service.build_week_excel(shifts, start, end, holiday_dates)

# export_service.py — build_week_excel() thêm tham số holiday_dates:
if main_shift is None and sub_shift is None:
    label = holiday_label_map.get(date_str, "")
    note = f"(Nghỉ lễ: {label})" if label else ""
    _apply_row(ws, current_row, [thu_label, date_label, note, "", "", "", "", ""],
               fill_hex="E8E8E8")
```

**Sprint**: Sprint 2.

---

### N5. 🟠 Week View và Schedule Planner không hiển thị ngày lễ trong lịch UI

Tương tự N4 nhưng ở frontend. Khi user dùng `render_empty_day_card()` cho ngày lễ, không có dấu hiệu gì phân biệt "trống chưa phân" vs "nghỉ lễ". User không biết tại sao không có ca ngày đó.

```python
# schedule_planner.py và week_view.py
if shifts:
    for shift in shifts:
        render_shift_card_compact(shift)
else:
    render_empty_day_card()  # ← giống hệt nhau dù là lễ hay chưa phân
```

**Fix**: Load `special_days` một lần khi `load_week()`, truyền vào `_render_week_grid()`. Khi ngày không có shift:
- Nếu là ngày lễ → hiện chip màu xám "🎌 {tên lễ}"
- Nếu chưa phân → hiện `render_empty_day_card()` như hiện tại

```python
# week_grid.py (component mới theo B1):
def render_week_grid(state, holiday_map=None, ...):
    ...
    if shifts:
        ...
    elif holiday_map and date_str in holiday_map:
        ui.chip(f"🎌 {holiday_map[date_str]}", color="grey").classes("text-xs")
    else:
        render_empty_day_card()
```

**Sprint**: Sprint 2 — làm cùng B1 (DRY refactor) để tránh sửa 2 lần.

---

### N6. 🟠 Không có tính năng xóa vắng theo range — chỉ xóa từng dòng

```python
# backend/routers/constraints.py
@router.delete("/absences/{absence_id}", ...)  # chỉ xóa 1 record
# Không có: DELETE /absences/range hoặc DELETE /absences?staff_id=&from=&to=
```

```python
# frontend/api_client.py
def delete_absence(absence_id: int) -> bool: ...
# Không có: delete_absence_range()
```

Khi user khai báo vắng 30 ngày cho một người đi công tác dài hạn, rồi người đó về sớm → phải xóa từng dòng một. Với 25 nhân sự và vắng dài ngày đây là UX pain point thực tế.

**Fix backend** (1 endpoint mới, không thay đổi existing):
```python
@router.delete("/absences/range", response_model=MessageOut)
def delete_absence_range(
    staff_id: int,
    from_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    to_date:   str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
):
    count = db.query(Absence).filter(
        Absence.staff_id == staff_id,
        Absence.absence_date >= from_date,
        Absence.absence_date <= to_date,
    ).delete()
    db.commit()
    return MessageOut(message=f"Đã xóa {count} ngày vắng")
```

**Fix frontend**: Thêm form "Xóa khoảng" trong Tab Khai báo vắng, bên cạnh form thêm.

**Sprint**: Sprint 2.

---

### N7. 🟡 `create_request` cho phép đăng ký ngày T7/CN và ngày lễ

```python
# Không có validation ngày hợp lệ trong create_request
obj = DutyRequest(staff_id=staff_id, specific_date=specific_date, ...)
```

User có thể đăng ký xin trực ngày Thứ 7, ngày Chủ Nhật, hay ngày lễ — những ngày không bao giờ có ca. Scheduler engine bỏ qua ngày lễ/cuối tuần khi generate, nên đăng ký này vô hiệu nhưng gây nhầm lẫn cho user.

**Fix**:
```python
# backend/services/constraint_service.py — create_request():
if specific_date:
    d = date.fromisoformat(specific_date)
    if d.weekday() >= 5:
        raise ValueError(f"Ngày {specific_date} là cuối tuần, không có ca trực")
    holiday_dates = get_holiday_dates(db, d.year)
    if specific_date in holiday_dates:
        raise ValueError(f"Ngày {specific_date} là ngày lễ, không có ca trực")
```

**Sprint**: Sprint 2.

---

### N8. 🟡 `export_service.py` chỉ có 1 format cột — không phân biệt ca Cutoff vs Normal vs Friday

Nhìn vào code `build_week_excel()`:

```python
else:
    # ── Hàng bình thường ──────────────────────────────
    shift = main_shift
    # ← normal, friday, cutoff đều xử lý giống nhau
    nv_col_c = sp_name    # Cột C: SP
    nv_col_d = "\n".join(nv_names)  # Cột D: NV
```

Ca Cutoff và ca Friday có vòng xoay riêng và ý nghĩa nghiệp vụ khác, nhưng trong file Excel đầu ra trông hoàn toàn giống ca thường. Người đọc file không biết ngày nào là Cutoff để đặc biệt chú ý.

**Fix đơn giản**: Thêm label vào cột THỨ hoặc NGÀY:
```python
# Trong _apply_row, cột A (THỨ):
shift_type_suffix = {
    "cutoff":  " (C/O)",
    "friday":  " (T6)",
    "settlement_main": " (QT)",
}.get(main_shift.get("shift_type", ""), "")
thu_label = WEEKDAY_VI.get(wd, "") + shift_type_suffix
```

**Sprint**: Sprint 2 — làm cùng N4 (export improvements).

---

## PHẦN 3 — ĐÁNH GIÁ LẠI SPRINT VÀ THỨ TỰ ƯU TIÊN

### Điều chỉnh so với PLAN v2

| Mục | PLAN v2 | Review v3 | Lý do |
|-----|---------|-----------|-------|
| **N2** LD/SP đăng ký không giới hạn | Chưa có | **Thêm Sprint 1** 🆕🔴 | Ảnh hưởng vòng xoay ngay |
| **N3** Duplicate DutyRequest | Chưa có | **Thêm Sprint 1** 🆕🔴 | Fix 5 dòng, rủi ro cao |
| **N1** Hard-code tên ký | Chưa có | **Thêm Sprint 2** 🆕🟠 | Dễ bị phát hiện khi dùng |
| **N4** Export thiếu ngày lễ | Chưa có | **Thêm Sprint 2** 🆕🟠 | Làm cùng export improvements |
| **N5** UI lịch không hiện ngày lễ | Chưa có | **Thêm Sprint 2** 🆕🟠 | Làm cùng B1 DRY refactor |
| **N6** Xóa vắng range | Chưa có | **Thêm Sprint 2** 🆕🟠 | UX pain point thực tế |
| **N7** Đăng ký xin trực T7/lễ | Chưa có | **Thêm Sprint 2** 🆕🟡 | Validation UX |
| **N8** Export không label Cutoff | Chưa có | **Thêm Sprint 2** 🆕🟡 | Làm cùng N4 |

### Sprint 1 cập nhật — ~5 ngày dev

```
Ngày 1 — Bug fixes (ưu tiên nhất, ít rủi ro):
  [FIX-1]  schedule_service.py: filter confirmed trong get_monthly_summary       (10 phút)
  [FIX-2]  week_view.py: sp_warning badge trong render_week_grid                 (15 phút)
  [V2]     constraint_service.py: check absence trước validate_nv_request        (15 phút)
  [V6]     staff_service.py: delete_staff dùng DutyShiftNV thay LIKE             (30 phút)
  [N3]     constraint_service.py: check duplicate trước create_request            (20 phút)
  [T2]     common.py: confirm_color param cho confirm_dialog                      (15 phút)

Ngày 1 cuối — Nghiệp vụ request:
  [N2]     settings.py: filter chỉ NV trong dropdown đăng ký xin trực            (15 phút)
           (Lưu ý: cần xác nhận với người dùng trước khi implement)

Ngày 2 — Warnings + Loading:
  [A3]     schedule_planner.py: warnings dialog sau generate                      (3-4 giờ)
  [C5]     common.py: run_with_feedback wrapper                                   (2-3 giờ)

Ngày 3 — DRY Refactor:
  [B1]     frontend/components/week_grid.py (mới): component dùng chung          (1 ngày)

Ngày 4 — Schema fix + Edit dialog:
  [V1]     duty_schemas.py + schedule_service.py: clear_sp field                  (1 giờ)
  [A4+B6]  shift_card.py + schedule_planner.py: edit dialog + confirm đơn lẻ    (1 ngày)

Ngày 5 — Chart:
  [B4]     statistics.py: ui.echart bar chart                                     (3-4 giờ)
```

### Sprint 2 cập nhật — ~7 ngày dev (tăng từ 5.5)

```
[N1]  Tên người ký trong export: thêm signer_name vào shift_config + UI          (3 giờ)
[N4+N8] Export: hiện ngày lễ + label Cutoff/Friday trong file Excel              (4 giờ)
[N5]  Week Grid: hiện ngày lễ trong lịch UI (làm cùng B1 component)              (2 giờ)
[N6]  Xóa vắng theo range: endpoint + UI                                          (3 giờ)
[N7]  Validate ngày hợp lệ khi đăng ký xin trực                                  (1 giờ)
[B5]  Unconfirm ca: endpoint + UI
[T3]  is_sp_backup field + UI toggle
[V4]  get_week_assignees: xác nhận nghiệp vụ rồi fix
[B2]  Month Calendar View (/lich-thang)
[C2]  Filter nhân sự trong lịch tuần
[T4]  Transaction rollback scheduler_engine
[T5]  Error handling api_client
```

---

## PHẦN 4 — CHECKLIST SPRINT 1 CẬP NHẬT (14 → 16 bước)

```
□  1. backend/services/schedule_service.py    — FIX-1 (confirmed filter)
□  2. frontend/pages/week_view.py             — FIX-2 (sp_warning badge)
□  3. backend/services/constraint_service.py  — V2 (absence check) + N3 (duplicate request)
□  4. backend/services/staff_service.py       — V6 (delete LIKE bug)
□  5. frontend/pages/settings.py              — N2 (filter NV trong dropdown đăng ký)
□  6. frontend/components/common.py           — T2 (confirm color) + C5 (run_with_feedback)
□  7. backend/schemas/duty_schemas.py         — V1 (clear_sp field)
□  8. backend/services/schedule_service.py    — V1 (update_shift handle clear_sp)
□  9. frontend/pages/schedule_planner.py      — A3 (warnings dialog trong do_gen)
□ 10. frontend/components/week_grid.py (mới) — B1 (component dùng chung)
□ 11. frontend/pages/schedule_planner.py      — B1 (import week_grid, xóa code cũ)
□ 12. frontend/pages/week_view.py             — B1 (import week_grid, xóa code cũ)
□ 13. frontend/components/shift_card.py       — A4 + B6 (on_edit_click, on_confirm)
□ 14. frontend/pages/schedule_planner.py      — A4 + B6 (implement dialogs)
□ 15. frontend/pages/statistics.py            — B4 (ui.echart bar chart)
□ 16. [Sau khi xác nhận nghiệp vụ] constraint_service.py — N2 backend validation nếu cần
```

---

## PHẦN 5 — TÓM TẮT CÁC PHÁT HIỆN MỚI SO VỚI PLAN v2

| # | Vấn đề | File | Sprint | Mức độ |
|---|--------|------|--------|--------|
| N1 | Hard-code `"Nguyễn Quốc Hùng"` trong export Excel | `export_service.py:288` | 2 | 🟠 Trung bình |
| N2 | LD/SP đăng ký xin trực không giới hạn — lệch vòng xoay | `settings.py`, `constraints.py:123` | 1 | 🔴 Cao |
| N3 | `create_request` không check duplicate — ưu tiên kép | `constraint_service.py:176` | 1 | 🔴 Cao |
| N4 | Export Excel: ngày lễ hiện ô trắng, không ghi "(Nghỉ lễ)" | `export_service.py` | 2 | 🟠 Trung bình |
| N5 | Lịch tuần UI: không phân biệt "chưa phân" vs "ngày lễ" | `schedule_planner.py`, `week_view.py` | 2 | 🟠 Trung bình |
| N6 | Không có xóa vắng theo date range — phải xóa từng dòng | `constraints.py`, `api_client.py` | 2 | 🟠 Trung bình |
| N7 | Cho phép đăng ký xin trực ngày T7/CN/lễ — vô nghĩa | `constraint_service.py` | 2 | 🟡 Thấp |
| N8 | Export Excel: ca Cutoff/Friday không có nhãn phân biệt | `export_service.py` | 2 | 🟡 Thấp |

**Tổng ước lượng hoàn thiện cập nhật**: ~18 ngày dev (+2 ngày so với PLAN v2 do bổ sung Sprint 2).

---

## PHẦN 6 — CÂU HỎI NGHIỆP VỤ CẦN XÁC NHẬN TRƯỚC KHI CODE

Những điểm sau cần hỏi người dùng cuối trước khi implement để tránh phải làm lại:

**Q1 (cho N2)**: LD và SP có được phép "đăng ký xin trực" không? Hay chỉ NV mới cần tính năng này?

**Q2 (cho V4)**: Ca đang ở trạng thái `draft` có được coi là "đã trực trong tuần" khi generate lịch hay không? (Ảnh hưởng đến `get_week_assignees`)

**Q3 (cho N1)**: Người ký lịch trực có thể thay đổi không, hay luôn cố định là 1 người?

**Q4 (cho N5/N4)**: Trong file Excel và lịch UI, khi có ngày lễ giữa tuần, có muốn hiển thị tên ngày lễ (VD: "Giỗ Tổ Hùng Vương") không?
