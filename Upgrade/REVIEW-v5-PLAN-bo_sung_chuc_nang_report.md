# REVIEW v5 — Kế hoạch Hoàn thiện Phân lịch trực PTT
## Phân tích toàn diện codebase · Claude Sonnet 4.6 · 2026-05-29

> **Bối cảnh**: PLAN v4 (được upload) đã tích hợp đầy đủ REVIEW v1–v4 với 20 ngày dev ước tính.
> Review này **chỉ báo cáo những vấn đề chưa từng xuất hiện trong bất kỳ PLAN hay review nào**, phát hiện từ việc đọc kỹ luồng điều khiển `generate_schedule`, logic `delete_special_day`, `database.py`, và các edge-case operational chưa được xem xét.

---

## PHẦN 1 — XÁC NHẬN: PLAN v4 CHÍNH XÁC

Tất cả 18 bước trong Sprint 1 Checklist của PLAN v4 đều đúng về mặt kỹ thuật và theo đúng thứ tự tránh conflict. Không điều chỉnh.

---

## PHẦN 2 — 5 VẤN ĐỀ MỚI HOÀN TOÀN

### Q1. 🔴 Backend crash ngay khi chạy lần đầu — thư mục `database/` không tồn tại

**Phát hiện**: `.gitignore` có entry `database/duty_scheduler.db` (bỏ qua file DB) nhưng **không** có entry `database/` (giữ lại thư mục). Kết quả: khi clone từ git, thư mục `database/` **không được tạo** — không có file `.gitkeep` hay tương tự.

```python
# backend/config.py
DB_PATH = os.path.join(BASE_DIR, "database", "duty_scheduler.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# backend/database.py — KHÔNG có os.makedirs
engine = create_engine(DATABASE_URL, ...)
```

```python
# backend/main.py — lifespan trigger connection ngay khi start
Base.metadata.create_all(bind=engine)  # ← raises OperationalError nếu database/ không tồn tại
```

**Hậu quả**: Người mới clone repo → chạy `start.bat` → backend crash với `OperationalError: unable to open database file`. Người dùng hiện tại không gặp vì thư mục đã tồn tại từ trước.

**Fix — 2 dòng, trong `backend/config.py`**:
```python
DB_PATH = os.path.join(BASE_DIR, "database", "duty_scheduler.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)  # ← thêm dòng này
DATABASE_URL = f"sqlite:///{DB_PATH}"
```

**File cần sửa**: `backend/config.py`
**Sprint**: Sprint 1 — fix 2 dòng, rủi ro 0, ảnh hưởng first-run experience hoàn toàn.

---

### Q2. 🔴 `delete_special_day` không cascade xóa ca liên quan — cùng ngày xuất hiện 2 loại ca xung đột

**Cơ chế bug**:

Bảng `duty_shifts` có `UniqueConstraint("shift_date", "shift_type")` — tức là cùng ngày có thể có cả ca `"cutoff"` lẫn ca `"normal"` song song (2 giá trị shift_type khác nhau, không vi phạm constraint).

Luồng xảy ra bug:
1. Khai báo ngày `2025-01-31` là `cutoff` → confirm
2. Generate lịch → tạo ca `cutoff` ngày `2025-01-31` → confirm ca
3. User **xóa** ngày special_day `cutoff` này (vì nhập nhầm chẳng hạn)
4. `delete_special_day` chỉ xóa bảng `special_days`, **không xóa ca trong `duty_shifts`**
5. Generate lại tháng → `get_special_day(db, "2025-01-31")` trả `None` → ngày được coi là `normal`
6. Tạo thêm ca `normal` ngày `2025-01-31` (không vi phạm UniqueConstraint vì khác `shift_type`)
7. **Kết quả**: cùng ngày có 2 ca — `cutoff` (confirmed, từ bước 2) + `normal` (draft, từ bước 6)

**Hậu quả**: UI hiển thị 2 ô ca cho cùng 1 ngày — gây nhầm lẫn nghiêm trọng cho người lập lịch. Export Excel cũng render 2 hàng cho ngày đó. Tình huống tương tự xảy ra khi khai báo `holiday` sau khi đã generate ca.

**Fix**: Khi xóa special day, cảnh báo nếu ngày đó đang có ca, và/hoặc cascade xóa ca draft liên quan:

```python
# backend/services/constraint_service.py — delete_special_day()
def delete_special_day(db, special_day_id):
    obj = db.query(SpecialDay).filter_by(id=special_day_id).first()
    if not obj:
        return False
    # Xóa ca draft liên quan (giữ lại confirmed)
    db.query(DutyShift).filter(
        DutyShift.shift_date == obj.date,
        DutyShift.status == "draft",
    ).delete()
    db.delete(obj)
    db.commit()
    return True
```

**Hoặc** (conservative hơn): Ở router, trước khi xóa, check có ca confirmed không → nếu có, trả HTTP 409 với message yêu cầu xóa ca trước.

**File cần sửa**: `backend/services/constraint_service.py` (và/hoặc `backend/routers/constraints.py`)
**Sprint**: Sprint 1 — bug dữ liệu thực sự, xảy ra trong workflow thực tế.

---

### Q3. 🟠 `generate_schedule_for_week` skip toàn ngày nếu có BẤT KỲ ca confirmed — settlement_sub draft bị kẹt

**Cơ chế**:

```python
# scheduler_engine.py — generate_schedule_for_week()
existing = db.query(DutyShift).filter(DutyShift.shift_date == date_str).all()
if existing:
    has_confirmed = any(s.status == "confirmed" for s in existing)
    if has_confirmed and not overwrite_confirmed:
        skipped += len(existing)
        continue   # ← skip TOÀN BỘ ngày
```

**Tình huống bug** (thực tế với ngày quyết toán):

1. Ngày quyết toán được generate → tạo `settlement_main` (draft) + `settlement_sub` (draft)
2. Admin xác nhận `settlement_main` → status = "confirmed"
3. `settlement_sub` vẫn là "draft" (có thể cần sửa nhân sự)
4. Admin muốn re-generate để cập nhật `settlement_sub`
5. `generate_schedule_for_week` gặp `settlement_main` confirmed → `has_confirmed = True` → **skip toàn ngày**
6. `settlement_sub` draft **không được regenerate** — admin phải xóa thủ công rồi generate lại

**Hậu quả**: Người dùng không hiểu tại sao "Phân tuần này" không cập nhật lịch cho ngày quyết toán dù đã bấm "Ghi đè ca nháp".

**Fix đề xuất** (2 hướng):

*Hướng 1* — Thêm logic phân biệt: nếu có confirmed nhưng vẫn còn draft → cho phép regenerate draft:
```python
confirmed_shifts = [s for s in existing if s.status == "confirmed"]
draft_shifts     = [s for s in existing if s.status == "draft"]

if confirmed_shifts and not overwrite_confirmed:
    # Có confirmed: chỉ skip confirmed, xóa draft cũ rồi tạo draft mới
    if draft_shifts and overwrite_draft:
        for s in draft_shifts:
            db.delete(s)
        db.flush()
    elif draft_shifts and not overwrite_draft:
        skipped += len(draft_shifts)
        continue
    else:
        continue   # không có draft, không cần làm gì
```

*Hướng 2* (đơn giản hơn) — Thêm checkbox thứ 3 trong dialog generate: "Chỉ regenerate ca nháp (giữ nguyên ca confirmed)".

**File cần sửa**: `backend/services/scheduler_engine.py`, `frontend/pages/schedule_planner.py`
**Sprint**: Sprint 2 — quan trọng với ngày quyết toán, nhưng có workaround (xóa thủ công draft rồi generate lại).

---

### Q4. 🟡 Compact view không thể hiện rõ trường hợp "Lãnh đạo kiêm Song Phương"

**Vấn đề**:

Khi ca rơi vào trường hợp `leader_sp` (backup LD kiêm SP), dữ liệu được lưu như sau:
- `leader_id` = backup LD (Mỹ Linh hoặc Bích Phương)
- `sp_id` = `NULL`
- `sp_warning` = `"leader_sp"`

`render_shift_card_compact()` hiển thị:
```
LĐ: Trần Thị Mỹ Linh
SP: —
NV: Nguyễn Thị Phương, ...
```

Người đọc lịch thấy SP trống "—" mà không biết Mỹ Linh đang kiêm nhiệm. Chỉ có badge cảnh báo `"⚠️ LĐ kiêm SP"` mà PLAN v3 đã ghi nhận sẽ được thêm vào (FIX-2 / B1), nhưng **badge đó chỉ xuất hiện sau khi B1 DRY refactor được implement**.

Trong file Excel xuất ra thì đã có `"(kiêm SP)"` suffix sau tên — tốt hơn UI.

**Fix nhỏ**: Trong `render_shift_card_compact()`, nếu `sp_warning == "leader_sp"` thì thay `sp_name = "—"` bằng `sp_name = f"↑ {leader_name} (kiêm)"` để người đọc hiểu ngay:

```python
# shift_card.py — render_shift_card_compact()
sp = shift.get("sp") or {}
sp_warning = shift.get("sp_warning")
sp_name = sp.get("full_name", "—")
if sp_warning == "leader_sp" and not sp_name or sp_name == "—":
    leader_name_for_sp = (shift.get("leader") or {}).get("full_name", "")
    sp_name = f"↑ {leader_name_for_sp} (kiêm SP)" if leader_name_for_sp else "(LĐ kiêm SP)"
```

**File cần sửa**: `frontend/components/shift_card.py`
**Sprint**: Sprint 1 — 3 dòng, làm cùng lúc B1 refactor để không sửa lại.

---

### Q5. 🟡 `duty_requests` của người đang đi dự án vẫn hiển thị trong Settings Tab 4 — gây nhầm lẫn

**Vấn đề**:

Khi một người được đánh dấu `is_on_project = 1`, họ bị loại khỏi pool khi generate lịch. Tuy nhiên các `duty_requests` đã đăng ký trước đó **vẫn còn trong bảng** và **vẫn hiển thị trong Settings Tab "Đăng ký trực"**.

```python
# frontend/pages/settings.py — Tab 4
req_state["data"] = api_client.get_requests(year=req_state["year"]) or []
# ← get_requests() không filter is_on_project
```

Người quản lý thấy "Bùi Thị Thu Thủy đăng ký Thứ 4 hằng tuần" nhưng đăng ký này hoàn toàn vô hiệu vì cô đang đi dự án. Không có dấu hiệu trực quan nào để phân biệt.

**Fix**: Trong danh sách hiển thị, kiểm tra `is_on_project` của từng staff và thêm badge `"(Đang đi dự án)"` hoặc làm mờ dòng đó:

```python
# settings.py — _render_request_list()
staff_map = {s["id"]: s for s in all_staff}
for item in data:
    s = staff_map.get(item.get("staff_id"), {})
    is_inactive = s.get("is_on_project", 0)
    # Render dòng với opacity thấp hoặc badge "(Đi dự án)" nếu inactive
```

**File cần sửa**: `frontend/pages/settings.py`
**Sprint**: Sprint 2 — UX improvement, không phải bug logic.

---

## PHẦN 3 — PHÂN TÍCH LỘ TRÌNH CẬP NHẬT

### Sprint 1 — thêm Q1, Q2, Q4 (tổng ~6 ngày)

```
Bổ sung vào đầu Sprint 1 (trước tất cả fix khác):
  [Q1]  config.py: os.makedirs cho database/ directory                       (2 phút)
  [Q2]  constraint_service.py: delete_special_day cascade xóa draft shifts   (30 phút)

Bổ sung vào cuối Sprint 1 (cùng lúc với B1 refactor):
  [Q4]  shift_card.py: compact view hiển thị rõ leader_sp case               (15 phút)

[Giữ nguyên 18 bước còn lại từ PLAN v4]
```

### Sprint 2 — thêm Q3, Q5 (tổng ~8 ngày)

```
Bổ sung vào Sprint 2:
  [Q3]  scheduler_engine.py + schedule_planner.py:
        generate_schedule_for_week xử lý partial confirmed ngày               (3-4 giờ)
  [Q5]  settings.py: đánh dấu requests của người đang đi dự án               (1 giờ)

[Giữ nguyên các mục Sprint 2 từ PLAN v4]
```

---

## PHẦN 4 — CHECKLIST SPRINT 1 CẬP NHẬT (18 → 21 bước)

```
□  0. backend/config.py                      — Q1 (os.makedirs database/)       ← THÊM MỚI
□  1. backend/services/constraint_service.py — Q2 (delete_special_day cascade)  ← THÊM MỚI
□  2. backend/services/scheduler_engine.py   — P2 (position fix)
□  3. backend/services/staff_service.py      — P1 (rotation sync) + V6 (LIKE bug)
□  4. backend/services/schedule_service.py   — FIX-1 (confirmed filter)
□  5. frontend/pages/week_view.py            — FIX-2 (sp_warning badge)
□  6. backend/services/constraint_service.py — V2 (absence check) + N3 (dup request)
□  7. frontend/pages/settings.py             — N2 (filter NV dropdown)
     ⚠️ Chỉ implement sau xác nhận Q1 nghiệp vụ
□  8. frontend/components/common.py          — T2 (confirm color) + C5 (run_with_feedback)
□  9. backend/schemas/duty_schemas.py        — V1 (clear_sp field)
□ 10. backend/services/schedule_service.py   — V1 (update_shift clear_sp)
□ 11. frontend/pages/schedule_planner.py     — A3 (warnings dialog)
□ 12. frontend/components/week_grid.py (mới) — B1 (DRY component)
□ 13. frontend/pages/schedule_planner.py     — B1 (import week_grid)
□ 14. frontend/pages/week_view.py            — B1 (import week_grid)
□ 15. frontend/components/shift_card.py      — A4 + B6 + Q4 (edit, confirm, leader_sp display) ← Q4 THÊM
□ 16. frontend/pages/schedule_planner.py     — A4 + B6 (dialogs)
□ 17. frontend/pages/statistics.py           — B4 (echart bar chart)
□ 18. [Sau Q1 nghiệp vụ] backend/routers/constraints.py — N2 backend validation
□ 19. Verify Q2: tạo special_day → generate ca → xóa special_day → check duty_shifts
□ 20. Verify P1: tạo NV → đổi role LD → check rotation_state rows
```

---

## PHẦN 5 — TÓM TẮT CÁC PHÁT HIỆN MỚI SO VỚI PLAN v4

| # | Vấn đề | File | Sprint | Mức độ |
|---|--------|------|--------|--------|
| Q1 | `database/` không tồn tại khi clone → backend crash first-run | `config.py` | 1 | 🔴 Critical |
| Q2 | `delete_special_day` không xóa ca liên quan → 2 loại ca cùng ngày | `constraint_service.py` | 1 | 🔴 Cao |
| Q3 | Partial confirmed (settlement) → toàn ngày bị skip khi regenerate | `scheduler_engine.py` | 2 | 🟠 Trung bình |
| Q4 | Compact view không thể hiện rõ leader kiêm SP | `shift_card.py` | 1 | 🟡 Thấp |
| Q5 | Requests của người đi dự án hiển thị trong UI nhưng vô hiệu | `settings.py` | 2 | 🟡 Thấp |

**Tổng ước lượng hoàn thiện cập nhật**: ~21 ngày dev (+1 ngày do Q1+Q2 Sprint 1, Q3 Sprint 2).

---

## PHẦN 6 — CÂU HỎI NGHIỆP VỤ MỚI (kế thừa từ PLAN v4, thêm 1)

- **[Q1–Q5]** Giữ nguyên từ PLAN v4
- **[Q6]** *(Mới)* Khi xóa một ngày đặc biệt (cutoff, settlement) đã có ca liên quan, hành vi mong muốn là gì?
  - *Tùy chọn A*: Tự động xóa ca draft liên quan, cảnh báo nếu có ca confirmed
  - *Tùy chọn B*: Từ chối xóa nếu đang có ca (yêu cầu xóa ca trước)
  - *Tùy chọn C*: Cho phép xóa ngày đặc biệt mà không ảnh hưởng ca đã tạo

  → Ảnh hưởng cách implement Q2.
