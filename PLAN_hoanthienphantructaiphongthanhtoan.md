# 🏦 Phân tích Codebase & Brainstorm Hoàn thiện
## Dự án: Phân lịch trực — Phòng Thanh toán Agribank TTTT

---

## 1. NGHIÊN CỨU CODEBASE — Tổng quan kiến trúc

### 1.1 Sơ đồ kiến trúc hiện tại

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND  (NiceGUI · port 8081)                            │
│                                                             │
│  Pages:                    Components:                      │
│  ├─ schedule_planner.py    ├─ common.py (navbar, titles)    │
│  ├─ week_view.py           └─ shift_card.py                 │
│  ├─ roster_list.py                                          │
│  ├─ statistics.py          api_client.py (HTTP → backend)   │
│  └─ settings.py (5 tabs)                                    │
└────────────────────────┬────────────────────────────────────┘
                         │  HTTP REST
┌────────────────────────▼────────────────────────────────────┐
│  BACKEND  (FastAPI · port 8001)                             │
│                                                             │
│  Routers:                  Services:                        │
│  ├─ /schedule              ├─ scheduler_engine.py (core)    │
│  ├─ /constraints           ├─ schedule_service.py           │
│  ├─ /staff                 ├─ constraint_service.py         │
│  ├─ /stats                 ├─ staff_service.py              │
│  └─ /export                ├─ export_service.py             │
│                            └─ calendar_utils.py             │
│                                                             │
│  Models (SQLAlchemy ORM) ──► SQLite (duty_scheduler.db)     │
│  8 bảng: staff, absences, duty_requests, special_days,      │
│          rotation_state, duty_shifts, duty_shift_nv,        │
│          shift_config                                       │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Dữ liệu nhân sự (25 người cố định)

| Nhóm | Số lượng | Ghi chú |
|------|----------|---------|
| LĐ (Lãnh đạo) | 7 | 3 đi dự án; Mỹ Linh & Bích Phương là SP backup |
| SP (Song Phương CITAD/SWIFT) | 5 | 1 đi dự án |
| NV (Nhân viên thường) | 13 | 5 đi dự án |
| **Sẵn sàng trực** | **~16** | Sau khi loại is_on_project=1 |

### 1.3 Logic nghiệp vụ cốt lõi

#### Loại ca (shift_type)
- `normal` — T2–T5 thông thường (vòng xoay LD, NV)
- `friday` — Thứ Sáu (vòng xoay riêng: LD_friday, NV_friday)
- `cutoff` — Ngày cut-off cuối tháng (LD_cutoff, NV_cutoff)
- `settlement_main` / `settlement_sub` — Ngày quyết toán (2 cụm/ngày)

#### Thuật toán phân lịch (scheduler_engine.py)
```
Thứ tự ưu tiên chọn người:
  1. Người đã đăng ký xin trực (duty_requests) → ưu tiên nhất
  2. Vòng xoay cân bằng: shift_count ASC → day_mismatch ASC → last_used ASC → position ASC

SP — 4 cấp fallback:
  Cấp 1a: SP sẵn + chưa trực tuần này     → bình thường
  Cấp 2:  Backup LD (Mỹ Linh/Bích Phương) → cảnh báo "leader_sp", +2 NV
  Cấp 1b: SP đã trực tuần (fallback cuối)
  Cấp 3:  Không ai → cảnh báo "no_sp"
```

#### Trạng thái ca
- `draft` — Tự động sinh, chưa duyệt
- `confirmed` — Đã xác nhận (không ghi đè tự động)

---

## 2. PHÂN TÍCH NHỮNG GÌ ĐÃ CÓ ✅

| Module | Trạng thái | Mức độ hoàn thiện |
|--------|-----------|-------------------|
| DB models (8 bảng) | ✅ Xong | ~100% |
| Scheduler engine (thuật toán vòng xoay) | ✅ Xong | ~95% |
| API: CRUD nhân sự | ✅ Xong | ~90% |
| API: Absences, Duty Requests | ✅ Xong | ~90% |
| API: Special Days (holiday/cutoff/settlement) | ✅ Xong | ~90% |
| API: Generate schedule (tháng + tuần) | ✅ Xong | ~90% |
| API: Confirm/Delete shifts | ✅ Xong | ~85% |
| API: Export Excel (export_service) | ✅ Xong | ~80% |
| API: Stats (shift_count, monthly_summary, rotation) | ✅ Xong | ~80% |
| Frontend: Export Excel (nút UI trong Planner + Week View) | ✅ Xong | ~90% |
| Frontend: UI xác nhận ngày đặc biệt (Settings Tab 2) | ✅ Xong | ~85% |
| Frontend: Schedule Planner (tuần) | ✅ Cơ bản | ~80% |
| Frontend: Week View (read-only + export) | ✅ Cơ bản | ~75% |
| Frontend: Roster List (danh sách NV) | ✅ Cơ bản | ~70% |
| Frontend: Statistics | ✅ Cơ bản | ~65% |
| Frontend: Settings (5 tabs) | ✅ Cơ bản | ~75% |

---

## 3. BRAINSTORM — Phân tích Yêu cầu Hoàn thiện

### 🔴 NHÓM A — Lỗi / Thiếu sót nghiệp vụ (Critical)

#### ✅ A1. Export Excel — ĐÃ HOÀN THÀNH
**Thực trạng**: Nút "📥 Xuất Excel" đã có trong `frontend/pages/schedule_planner.py:74-81` và `frontend/pages/week_view.py:66-73`. Gọi `api_client.get_week_export_url()` mở tab mới tải file `.xlsx`.

#### ✅ A2. Xác nhận ngày cut-off/quyết toán — ĐÃ HOÀN THÀNH
**Thực trạng**: `frontend/pages/settings.py` Tab 2 "📅 Ngày đặc biệt" đã có cột trạng thái Draft/Confirmed và nút "✅ Xác nhận" trực tiếp trên từng dòng, gọi `api_client.confirm_special_day()`.

#### FIX-1. Bug: `get_monthly_summary` đếm cả ca draft
**Vấn đề**: `backend/services/schedule_service.py` — query trong `get_monthly_summary()` không filter `status == "confirmed"`, trong khi `get_shift_count_by_person()` chỉ đếm confirmed. Hai endpoint thống kê trả số liệu không nhất quán — người dùng thấy tổng tháng khác tổng theo người.
**Sửa**: Thêm `.filter(DutyShift.status == "confirmed")` vào query của `get_monthly_summary`.
**File cần sửa**: `backend/services/schedule_service.py`

#### FIX-2. Bug: `week_view.py` thiếu hiển thị `sp_warning` badge
**Vấn đề**: `frontend/pages/week_view.py:render_week_grid()` không có đoạn hiển thị badge cảnh báo SP, trong khi `schedule_planner.py:148-152` có. Người dùng xem `/lich-tuan` (read-only) sẽ không thấy cảnh báo `leader_sp` / `no_sp` — thông tin quan trọng bị ẩn.
**Sửa**: Thêm đoạn kiểm tra `shift.get("sp_warning")` và render badge tương tự như `schedule_planner.py`.
**File cần sửa**: `frontend/pages/week_view.py`

#### A3. Cảnh báo sau generate chưa hiển thị tổng hợp
**Vấn đề**: Badge `sp_warning` trên từng shift card đã có (`schedule_planner.py:148-152`), nhưng `warnings[]` trả về từ API generate-week bị bỏ qua hoàn toàn tại `schedule_planner.py:200-206` — không có banner/dialog tổng hợp sau khi nhấn "Phân tuần này".
**Yêu cầu**: Sau generate, nếu `result.get("warnings")` không rỗng → hiển thị `ui.notify` màu cam hoặc dialog liệt kê từng cảnh báo (leader_sp, no_sp, no_leader).
**Vị trí code chính xác**: Lỗi nằm trong closure `do_gen()` bên trong hàm `_generate_week()` của `schedule_planner.py`. Sau dòng `show_notify(f"Phân lịch thành công: {created} ca")`, thêm xử lý `warnings = result.get("warnings", [])` và gọi dialog nếu không rỗng.
**File cần sửa**: `frontend/pages/schedule_planner.py` — closure `do_gen()` bên trong `_generate_week()`

#### V1. Bug: `ShiftUpdate` schema không thể xóa SP — block A4
**Vấn đề**: `backend/schemas/duty_schemas.py` — `sp_id: Optional[int] = None` bị hiểu là "không truyền" chứ không phải "xóa SP". `backend/services/schedule_service.py` trong `update_shift()` dùng `if sp_id is not None: shift.sp_id = sp_id` → không bao giờ có thể xóa SP về NULL.
**Hậu quả**: Dialog sửa tay ca (A4) sẽ không cho phép bỏ trống slot SP nếu không fix V1 trước.
**Fix**: Thêm `clear_sp: bool = False` vào `ShiftUpdate` schema; service kiểm tra `if body.clear_sp: shift.sp_id = None elif body.sp_id is not None: shift.sp_id = body.sp_id`.
**File cần sửa**: `backend/schemas/duty_schemas.py`, `backend/services/schedule_service.py`
**Mức độ**: 🔴 Critical — phải fix TRƯỚC khi implement A4

#### V2. Bug: `validate_nv_request` không kiểm tra bảng `absences`
**Vấn đề**: `backend/services/constraint_service.py` — `validate_nv_request()` không cross-check với bảng `absences` — chỉ kiểm tra slot limit.
**Hậu quả**: NV có thể đăng ký xin trực vào ngày đã khai báo vắng — vi phạm nghiệp vụ rõ ràng.
**Fix**: 3 dòng — gọi `get_absent_staff_ids(db, date_str)` (đã có trong `staff_service.py`) rồi kiểm tra `if staff_id in absent_ids`.
**File cần sửa**: `backend/services/constraint_service.py`
**Mức độ**: 🔴 Critical (3 dòng, ít rủi ro)

#### V6. Bug: `delete_staff` dùng LIKE string-match để tìm NV trong ca
**Vấn đề**: `backend/services/staff_service.py` — `delete_staff()` dùng `DutyShift.nv_ids.like(f'%{staff_id}%')` để tìm ca có NV này. Vì `nv_ids` lưu JSON string, `staff_id=1` sẽ match cả `"[11, 13, 21]"` — xóa nhầm NV không liên quan.
**Fix**: Dùng bảng `DutyShiftNV` (đã có sẵn): `query(DutyShiftNV.shift_id).filter_by(staff_id=staff_id)` thay vì LIKE.
**File cần sửa**: `backend/services/staff_service.py`
**Mức độ**: 🔴 Critical (bug dữ liệu thực sự, fix đơn giản)

#### N2. Bug nghiệp vụ: LD/SP đăng ký xin trực không có giới hạn
**Vấn đề**: `frontend/pages/settings.py` — dropdown đăng ký xin trực hiển thị tất cả nhân sự (kể cả LD, SP). `backend/routers/constraints.py` — `create_request()` chỉ validate khi `role == "NV"` — LD/SP không bị kiểm tra gì, có thể đăng ký vô hạn số ngày.
**Hậu quả**: Scheduler engine ưu tiên người đăng ký → LD/SP đăng ký nhiều ngày sẽ làm lệch vòng xoay của nhóm mình.
**⚠️ Cần xác nhận nghiệp vụ [Q1]**: LD/SP có được phép đăng ký xin trực không? Nếu không → filter chỉ NV trong dropdown; nếu có → thêm validation tương tự NV.
**Fix (nếu chỉ NV đăng ký)**: Lọc `s["role"] == "NV"` trong `settings.py`.
**File cần sửa**: `frontend/pages/settings.py`, `backend/routers/constraints.py`
**Mức độ**: 🔴 Critical (ảnh hưởng vòng xoay ngay)

#### N3. Bug: `create_request` không check duplicate — tạo đăng ký trùng
**Vấn đề**: `backend/services/constraint_service.py:create_request()` — không có `UniqueConstraint` hay check trước `db.add()`. So sánh: `create_absence` và `create_special_day` có check idempotent — nhưng `create_request` không có.
**Hậu quả**: Bấm nút "Thêm" 2 lần → 2 bản ghi identical → scheduler engine thấy người này 2 lần → ưu tiên kép.
**Fix**: Check `existing = db.query(DutyRequest).filter_by(staff_id, request_type, specific_date, day_of_week, year).first()` trước khi add.
**File cần sửa**: `backend/services/constraint_service.py`
**Mức độ**: 🔴 Critical (5 dòng fix, rủi ro thấp)

#### P1. Bug: `update_staff` không sync `rotation_state` khi đổi role
**Vấn đề**: `backend/services/staff_service.py:update_staff()` — khi đổi role (VD: NV→LD), chỉ cập nhật `s.role` trong bảng `staff`. KHÔNG xóa rotation_state cũ (NV/NV_friday/NV_cutoff) và KHÔNG tạo rotation_state mới (LD/LD_friday/LD_cutoff).
**Hậu quả**: Người vừa đổi role có rotation_state orphan + thiếu; khi lần đầu được phân ca với role mới, `_get_rotation_state()` tạo row với `position=staff_id` (xem P2) — sắp xếp vị trí vòng xoay không nhất quán.
**Fix**: Trong `update_staff()`, nếu `role != old_role` → xóa rotation rows cũ, tạo rows mới với `position = display_order*10 + staff_id`.
**File cần sửa**: `backend/services/staff_service.py`
**Mức độ**: 🔴 Critical — Sprint 1

#### P2. Bug: `_get_rotation_state` tạo row với `position=staff_id` — sai thứ tự vòng xoay
**Vấn đề**: `backend/services/scheduler_engine.py:_get_rotation_state()` — khi tạo row mới (fallback path), dùng `position=staff_id` (giá trị 1-25). Trong khi `init_rotation_for_year()` và `create_staff()` đều dùng `position = display_order*10 + staff_id` (giá trị 10x-99x).
**Hậu quả**: Người được tạo rotation qua fallback có `position` thấp hơn nhiều → luôn được ưu tiên trong tie-break → phá vỡ thứ tự vòng xoay ban đầu.
**Fix**: 3 dòng — query `Staff.display_order` rồi tính `pos = display_order*10 + staff_id`.
**File cần sửa**: `backend/services/scheduler_engine.py`
**Mức độ**: 🔴 Critical — Sprint 1 (cùng lúc với P1)

#### R1. Bug: `database/` directory không tồn tại khi clone mới → backend crash
**Vấn đề**: `.gitignore` bỏ qua `database/duty_scheduler.db` nhưng không có `.gitkeep` → khi clone từ git, thư mục `database/` không được tạo. `backend/config.py` không có `os.makedirs()` → `Base.metadata.create_all()` raise `OperationalError: unable to open database file` ngay khi start.
**Hậu quả**: Người mới clone repo → chạy `start.bat` → backend crash ngay. Người dùng hiện tại không gặp vì thư mục đã có từ trước.
**Fix**: 1 dòng trong `backend/config.py`: `os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)` sau khai báo `DB_PATH`.
```python
# backend/config.py
DB_PATH = os.path.join(BASE_DIR, "database", "duty_scheduler.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)  # ← thêm dòng này
DATABASE_URL = f"sqlite:///{DB_PATH}"
```
**File cần sửa**: `backend/config.py`
**Mức độ**: 🔴 Critical — phải làm ĐẦU TIÊN trong Sprint 1

#### R2. Bug: `delete_special_day` không cascade xóa ca liên quan → 2 loại ca cùng ngày
**Vấn đề**: `backend/services/constraint_service.py:delete_special_day()` chỉ xóa bảng `special_days`, không xóa `duty_shifts` cùng ngày. Bảng `duty_shifts` có `UniqueConstraint("shift_date", "shift_type")` → cùng ngày có thể tồn tại cả `cutoff` lẫn `normal` (shift_type khác nhau).
**Luồng bug 7 bước** (tái hiện trong workflow thực tế):
1. Khai báo ngày `2025-01-31` là `cutoff` → confirm
2. Generate lịch → tạo ca `cutoff` ngày `2025-01-31` → confirm ca
3. User **xóa** ngày special_day `cutoff` (vì nhập nhầm)
4. `delete_special_day` chỉ xóa bảng `special_days`, **không xóa ca trong `duty_shifts`**
5. Generate lại tháng → `get_special_day(db, "2025-01-31")` trả `None` → ngày được coi là `normal`
6. Tạo thêm ca `normal` ngày `2025-01-31` (không vi phạm UniqueConstraint vì khác `shift_type`)
7. **Kết quả**: cùng ngày có 2 ca — `cutoff` (confirmed) + `normal` (draft) — UI hiện 2 ô, Excel 2 hàng

**⚠️ Cần xác nhận [Q6]**: Hành vi khi xóa special_day có ca liên quan?
- **Option A** (đề xuất): Tự động xóa ca draft + cảnh báo HTTP 409 nếu có ca confirmed
- **Option B**: Từ chối xóa nếu có bất kỳ ca nào
- **Option C**: Cho phép xóa tự do (không cascade)

**Code fix mẫu** (Option A — cascade xóa draft, block nếu có confirmed):
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
**File cần sửa**: `backend/services/constraint_service.py`, `backend/routers/constraints.py`
**Mức độ**: 🔴 Critical (bug dữ liệu, xảy ra trong workflow thực tế)

#### R4. UX: Compact view không hiển thị rõ "Lãnh đạo kiêm Song Phương"
**Vấn đề**: `frontend/components/shift_card.py:render_shift_card_compact()` — khi `sp_warning == "leader_sp"`, SP slot hiển thị "—" thay vì chỉ rõ ai đang kiêm nhiệm. Người đọc lịch thấy SP trống mà không biết Mỹ Linh/Bích Phương đang kiêm (trong khi file Excel xuất đã có `"(kiêm SP)"` suffix — nhất quán hơn).
**Fix**: Nếu `sp_warning == "leader_sp"` và `sp_name == "—"` → hiển thị `"↑ {leader_name} (kiêm SP)"`.
```python
# frontend/components/shift_card.py — render_shift_card_compact()
sp = shift.get("sp") or {}
sp_warning = shift.get("sp_warning")
sp_name = sp.get("full_name", "—")
if sp_warning == "leader_sp" and (not sp_name or sp_name == "—"):
    leader_name_for_sp = (shift.get("leader") or {}).get("full_name", "")
    sp_name = f"↑ {leader_name_for_sp} (kiêm SP)" if leader_name_for_sp else "(LĐ kiêm SP)"
```
**File cần sửa**: `frontend/components/shift_card.py`
**Mức độ**: 🟡 Low — 3 dòng, làm cùng B1 refactor để không sửa 2 lần

#### A4. Sửa tay ca trực (Manual Override) chưa có UI
**Vấn đề**: `shift_card.py:94-97` có button "Sửa" nhưng là stub — `on_edit_click` callback chưa bao giờ được truyền vào. `schedule_planner.py` dùng `render_shift_card_compact()` vốn không nhận `on_edit_click`. Không có dialog nào với dropdown chọn LĐ/SP/NV. `api_client.update_shift()` tồn tại nhưng chưa được gọi từ các trang.
**Yêu cầu**: (1) Thêm `on_edit_click=None` vào `render_shift_card_compact()`, (2) implement dialog chọn lại LĐ/SP/NV từ dropdown, (3) gọi `api_client.update_shift()` khi lưu. Lưu ý: nếu NV list trống phải hiện warning.
**Phụ thuộc**: Fix V1 trước (cần `clear_sp` để có thể bỏ trống SP).
**File cần sửa**: `frontend/pages/schedule_planner.py`, `frontend/components/shift_card.py`

#### A5. Dữ liệu từ file Excel mẫu (dulieu/) chưa được import vào hệ thống
**Vấn đề**: Có 2 file Excel lịch trực 2025 mẫu nhưng không có chức năng import.
**Yêu cầu** (tùy chọn): Thêm chức năng import lịch lịch sử từ Excel để khởi tạo rotation_state ban đầu chính xác hơn.

---

### 🟠 NHÓM B — Tính năng còn thiếu (High Priority)

#### B1. DRY Violation — Code trùng lặp giữa Week View và Schedule Planner (Nâng lên Sprint 1)
**Vấn đề**: `schedule_planner.py` và `week_view.py` có ~60 dòng code lặp 100%: toàn bộ `_render_week_grid`, cùng navigation helpers (`_get_monday_of_week`, `_prev_week`, `_next_week`, `_today_week`). Đây là DRY violation — fix bug ở một file phải nhớ fix cả file kia. FIX-2 là bằng chứng trực tiếp: `week_view.py` thiếu sp_warning badge vì code không được đồng bộ từ `schedule_planner.py`.
**Yêu cầu**: Tách `render_week_grid()` thành `frontend/components/week_grid.py` dùng chung, nhận tham số `show_edit_button=False` và `show_warnings=True`. Cả 2 trang import từ đây. Xóa ~60 dòng duplicate.
**Ưu tiên**: Nâng lên Sprint 1 — là technical debt có bug đi kèm, không phải chỉ UX.

#### B2. Chưa có Trang Tháng (Month Calendar View)
**Vấn đề**: Chỉ xem theo tuần, không xem tổng quan cả tháng.
**Yêu cầu**: Thêm tab/trang xem lịch theo tháng dạng calendar grid — hiện tên LĐ/SP/cảnh báo trên từng ô ngày.

#### B3. Quản lý trạng thái "đi dự án" chưa linh hoạt
**Vấn đề**: `is_on_project` được seed cứng, chỉ thay đổi qua trang Danh sách NV → toggle.
**Yêu cầu**: Thêm chức năng "Đi dự án từ ngày... đến ngày..." (date range) thay vì toggle cứng on/off — hiện tại dùng Absence để workaround nhưng không tường minh.

#### B4. Chưa có thống kê so sánh công bằng phân ca
**Vấn đề**: Tab Thống kê hiện có shift_count nhưng chưa có visual chart.
**Yêu cầu**: Thêm biểu đồ cột (bar chart) so sánh số ca từng người theo nhóm (LD/SP/NV), highlight người lệch nhiều so với trung bình.

#### N4. Export Excel không hiển thị ngày lễ
**Vấn đề**: `backend/services/export_service.py:build_week_excel()` — khi tuần có ngày lễ (không có shift), hàng trong Excel để trắng hoàn toàn. Người đọc không phân biệt được "trống chưa phân" hay "nghỉ lễ".
**Fix**: Truyền `holiday_map: dict` vào `build_week_excel()`; hiển thị `"(Nghỉ lễ: {tên})"` màu xám cho ngày lễ.
**Làm cùng N8**.
**File cần sửa**: `backend/services/export_service.py`, `backend/routers/export.py`

#### N5. Lịch tuần UI không phân biệt "chưa phân" vs "ngày lễ"
**Vấn đề**: `schedule_planner.py` và `week_view.py` — khi ngày không có shift đều hiện `render_empty_day_card()` — không có cách biết đó là ngày lễ hay chưa được phân ca.
**Fix**: Khi load tuần, gọi thêm `api_client.get_special_days()` để lấy ngày lễ. Truyền `holiday_map` vào `week_grid.py` component (B1). Khi ngày lễ → hiện chip màu xám "🎌 {tên lễ}"; khi chưa phân → `render_empty_day_card()`.
**Làm cùng B1** (DRY refactor) để tránh sửa 2 file riêng.
**File cần sửa**: `frontend/components/week_grid.py`, `frontend/pages/schedule_planner.py`, `frontend/pages/week_view.py`

#### N6. Không có tính năng xóa vắng theo date range
**Vấn đề**: Backend chỉ có `DELETE /absences/{absence_id}` (xóa 1 record). Không có xóa theo khoảng ngày.
**UX pain point thực tế**: Khai báo vắng 30 ngày cho người đi công tác, người về sớm → phải xóa từng dòng một.
**Fix**: Thêm `DELETE /absences/range?staff_id=&from_date=&to_date=` + form "Xóa khoảng" trong Settings Tab 3 (Khai báo vắng).
**File cần sửa**: `backend/routers/constraints.py`, `frontend/api_client.py`, `frontend/pages/settings.py`

#### B6. Confirm ca đơn lẻ từ shift card (Quick win — implement cùng A4)
**Vấn đề**: Có `confirm_week` (xác nhận cả tuần) và `confirm_all` (cả tháng) nhưng không có cách confirm 1 ca riêng lẻ từ UI. Usecase thực tế: trong 1 tuần có 1 ca cần chỉnh lại — muốn confirm 4 ca còn lại trước.
**Thực trạng**: `PUT /schedule/{shift_id}/confirm` ĐÃ CÓ trong backend; `api_client.confirm_shift()` ĐÃ CÓ — chỉ thiếu nút UI.
**Yêu cầu**: Thêm nút "✅" nhỏ vào `render_shift_card_compact()` khi `status == "draft"`, tương tự nút sửa.
**File cần sửa**: `frontend/components/shift_card.py`, `frontend/pages/schedule_planner.py`

#### R3. `generate_schedule_for_week` skip toàn ngày nếu có ca confirmed → settlement_sub draft bị kẹt
**Vấn đề**: `backend/services/scheduler_engine.py` — logic hiện tại: nếu bất kỳ ca nào trong ngày có `status == "confirmed"` → skip toàn bộ ngày đó, kể cả các ca draft cùng ngày.

**Code hiện tại (bug)**:
```python
# scheduler_engine.py — generate_schedule_for_week()
existing = db.query(DutyShift).filter(DutyShift.shift_date == date_str).all()
if existing:
    has_confirmed = any(s.status == "confirmed" for s in existing)
    if has_confirmed and not overwrite_confirmed:
        skipped += len(existing)
        continue   # ← skip TOÀN BỘ ngày, kể cả draft
```

**Tình huống thực tế**: Ngày quyết toán generate ra `settlement_main` (confirmed) + `settlement_sub` (draft). Admin muốn re-generate `settlement_sub` (thay đổi NV) → bấm "Ghi đè ca nháp" → toàn ngày vẫn bị skip vì `settlement_main` đã confirmed → `settlement_sub` không được regenerate.
**Workaround hiện tại**: Xóa thủ công `settlement_sub` draft rồi generate lại.

**Fix — 2 hướng**:

*Hướng 1* — Tách logic confirmed/draft:
```python
confirmed_shifts = [s for s in existing if s.status == "confirmed"]
draft_shifts     = [s for s in existing if s.status == "draft"]

if confirmed_shifts and not overwrite_confirmed:
    if draft_shifts and overwrite_draft:
        for s in draft_shifts:
            db.delete(s)
        db.flush()
    elif draft_shifts and not overwrite_draft:
        skipped += len(draft_shifts)
        continue
    else:
        continue  # không có draft, không cần làm gì
```

*Hướng 2* (đơn giản hơn) — Thêm checkbox "Chỉ regenerate ca nháp (giữ nguyên ca confirmed)" vào dialog generate trong `schedule_planner.py`.

**File cần sửa**: `backend/services/scheduler_engine.py`, `frontend/pages/schedule_planner.py`

#### P3. `generate_schedule` tháng không có UI — phải phân từng tuần thủ công
**Vấn đề**: `frontend/api_client.py:generate_schedule()` tồn tại nhưng không trang nào gọi. Người dùng phải click "Phân tuần này" 4-5 lần để lập lịch cả tháng.
**Lưu ý kỹ thuật**: `GenerateRequest` schema không có `overwrite_confirmed` (khác `GenerateWeekRequest`) — confirmed ca luôn được bảo vệ khi generate tháng — behavior này đúng.
**Fix**: Thêm nút "🗓️ Phân cả tháng" vào `schedule_planner.py`, kèm dialog chọn tháng/năm và option `overwrite_draft`.
**File cần sửa**: `frontend/pages/schedule_planner.py`

#### B5. Không có Undo/History cho thao tác Confirm
**Vấn đề**: Sau khi confirm ca, không thể undo — chỉ có thể xóa rồi tạo lại.
**Yêu cầu**: Thêm endpoint `PATCH /schedule/{shift_id}/unconfirm` và nút "Huỷ xác nhận" trong UI (với warning).

---

### 🟡 NHÓM C — Cải thiện UX/Trải nghiệm (Medium Priority)

#### C1. Thiếu trang Dashboard/Home thực sự
**Vấn đề**: Trang chủ (`/`) hiện là Schedule Planner — không có overview nhanh.
**Yêu cầu**: Dashboard với 3 widget: (1) Lịch tuần này, (2) Cảnh báo pending, (3) Tóm tắt tháng hiện tại.

#### C2. Không có tìm kiếm/filter theo tên NV
**Vấn đề**: Khi xem lịch, không thể lọc "ca nào có Nguyễn Thị Phương tham gia?"
**Yêu cầu**: Thêm filter nhân sự trong Schedule Planner → highlight các ca có người được chọn.

#### N1. Hard-code tên người ký trong file Excel xuất
**Vấn đề**: `backend/services/export_service.py:288` — `"Nguyễn Quốc Hùng"` được hard-code. Nếu người ký thay đổi (nghỉ, bổ nhiệm mới), phải sửa code và restart backend.
**Fix**: Thêm field `signer_name` vào `shift_config` table; hiển thị ô nhập trong Settings Tab 1; đọc động khi build Excel. Có thể dùng fallback `"Nguyễn Quốc Hùng"` nếu field trống.
**⚠️ Cần xác nhận nghiệp vụ [Q3]**: Người ký có thể thay đổi không?
**File cần sửa**: `backend/models/duty_models.py`, `backend/services/export_service.py`, `backend/schemas/duty_schemas.py`, `frontend/pages/settings.py`

#### R5. Requests của người đang đi dự án hiển thị trong Tab 4 mà không có dấu hiệu vô hiệu
**Vấn đề**: `frontend/pages/settings.py` Tab 4 "Đăng ký trực" — `get_requests()` không filter `is_on_project`. Người đang đi dự án (`is_on_project=1`) vẫn có đăng ký hiển thị bình thường dù scheduler hoàn toàn bỏ qua họ khi generate lịch.
**Hậu quả**: Người quản lý thấy "Nguyễn Thị X đăng ký Thứ 4 hằng tuần" nhưng đăng ký đó vô hiệu — không có dấu hiệu nào để biết.
**Fix**: Với mỗi dòng đăng ký, kiểm tra `is_on_project` của staff và hiển thị badge "(Đang đi dự án)" hoặc làm mờ dòng đó.
```python
# frontend/pages/settings.py — _render_request_list()
staff_map = {s["id"]: s for s in all_staff}
for item in data:
    s = staff_map.get(item.get("staff_id"), {})
    is_inactive = s.get("is_on_project", 0)
    # Render dòng với opacity thấp hoặc badge "(Đi dự án)" nếu inactive
```
**File cần sửa**: `frontend/pages/settings.py`

#### N7. Cho phép đăng ký xin trực ngày T7/CN/ngày lễ
**Vấn đề**: `backend/services/constraint_service.py:create_request()` — không validate `specific_date` là ngày làm việc hợp lệ. User có thể đăng ký T7, CN, ngày lễ — những ngày không bao giờ có ca. Đăng ký này vô hiệu nhưng gây nhầm lẫn.
**Fix**: Kiểm tra `d.weekday() >= 5` (cuối tuần) và `specific_date in holiday_dates` trước khi tạo request; trả lỗi rõ ràng.
**File cần sửa**: `backend/services/constraint_service.py`

#### N8. Export Excel không label ca Cutoff/Friday — khó phân biệt
**Vấn đề**: `backend/services/export_service.py:build_week_excel()` — ca Cutoff và Friday có vòng xoay riêng nhưng trong file Excel trông giống ca thường — người đọc không biết ngày nào là Cutoff.
**Fix**: Thêm suffix vào cột THỨ: `"(C/O)"` cho cutoff, `"(T6)"` cho friday, `"(QT)"` cho settlement.
**File cần sửa**: `backend/services/export_service.py`
**Làm cùng N4** (export improvements).

#### C3. Chưa có thông báo realtime khi có conflict
**Vấn đề**: Nếu 2 user cùng thao tác, không có cơ chế conflict detection.
**Yêu cầu**: (Medium-term) Thêm WebSocket notification khi ca được cập nhật/confirm bởi user khác.

#### C4. Mobile responsive chưa được xem xét
**Vấn đề**: NiceGUI layout hiện tại dùng `max-w-5xl` nhưng trên mobile sẽ bị vỡ.
**Yêu cầu**: Kiểm tra và thêm responsive breakpoints cho giao diện shift_card và bảng NV.

#### C5. Thiếu loading state và error handling trong API client
**Vấn đề**: `api_client.py` wrap try/except nhưng frontend không hiện loading spinner hay error toast đồng nhất.
**Yêu cầu**: Thêm `ui.notify()` toast cho mọi thao tác CRUD (thành công xanh, lỗi đỏ), và spinner khi đang tải.

---

### 🟢 NHÓM D — Tính năng Nâng cao (Low Priority / Future)

#### D1. Import lịch sử từ Excel (.xls)
Đọc file `dulieu/LICH TRUC 2025.xls` để pre-populate rotation_state ban đầu, giúp vòng xoay tiếp nối chính xác từ dữ liệu thực.

#### D2. Gửi lịch qua Email/Zalo OA
Tích hợp SMTP hoặc Zalo OA API để gửi lịch trực tuần tới người liên quan tự động sau khi Confirm.

#### D3. Multi-year comparison
So sánh số ca trực năm này vs năm trước để đánh giá tính công bằng dài hạn.

#### D4. Print-friendly view
Trang in lịch tháng dạng A4, không có sidebar/navbar, sẵn sàng gửi cho phòng ban.

#### D5. Backup/Restore database
Nút xuất toàn bộ DB ra file JSON hoặc SQLite backup, và import lại.

#### P4. `launcher.py` dùng flag Windows-only — không chạy được trên Linux/macOS
`launcher.py` dùng `subprocess.CREATE_NEW_CONSOLE` — hằng số chỉ tồn tại trên Windows. Chạy trên Linux/macOS sẽ raise `AttributeError`. Tuy ứng dụng này chủ yếu dùng trên Windows (Agribank), developer có thể cần test trên macOS/Linux.
**Fix**: Thêm `platform.system() == "Windows"` check; fallback dùng `stdout=DEVNULL` trên Linux/macOS.
**File cần sửa**: `launcher.py`

#### P5. `BASE_URL` và CORS `allow_origins` hardcode `localhost` — không deploy được lên mạng nội bộ
`frontend/api_client.py:BASE_URL = "http://localhost:8001/api/v1"` và `backend/main.py:allow_origins` hardcode. Nếu deploy lên máy chủ mạng nội bộ (để nhiều máy truy cập), phải sửa code thủ công.
**Fix**: Đọc từ env var với fallback `localhost`; thêm `.env.example` hướng dẫn cấu hình.
**⚠️ Cần xác nhận [Q5]**: Hệ thống có cần deploy ra mạng nội bộ không?
**File cần sửa**: `frontend/api_client.py`, `backend/main.py`

---

## 4. ĐỀ XUẤT LỘ TRÌNH HOÀN THIỆN

### Sprint 1 — Sửa bug & Nghiệp vụ thiết yếu (~6 ngày)
```
~~[A1] Kết nối nút Export Excel — ĐÃ XONG~~
~~[A2] UI xác nhận cutoff/settlement — ĐÃ XONG~~
[R1]    Bug database/ directory không tồn tại (2 phút) — backend/config.py ← ĐẦU TIÊN
[R2]    Bug delete_special_day không cascade ca (30 phút) — backend/services/constraint_service.py
        ⚠️ Cần xác nhận Q6 trước khi chọn implementation (Option A/B/C)
[P2]    Bug _get_rotation_state dùng position=staff_id sai (15 phút) — backend/services/scheduler_engine.py
[P1]    Bug update_staff không sync rotation_state khi đổi role (1 giờ) — backend/services/staff_service.py
[FIX-1] Bug monthly_summary đếm cả draft (10 phút) — backend/services/schedule_service.py
[FIX-2] Bug week_view thiếu sp_warning badge (15 phút) — frontend/pages/week_view.py
[V2]    Bug validate_nv_request không check absence (15 phút) — backend/services/constraint_service.py
[N3]    Bug create_request không check duplicate (20 phút) — backend/services/constraint_service.py
[V6]    Bug delete_staff LIKE string-match (30 phút) — backend/services/staff_service.py
[N2]    Bug LD/SP đăng ký xin trực không giới hạn (15 phút) — frontend/pages/settings.py
        ⚠️ Cần xác nhận Q1 trước khi implement: LD/SP có được đăng ký không?
[T2]    Fix confirm_dialog color param (15 phút) — frontend/components/common.py
[A3]    Warnings dialog sau generate — closure do_gen() trong schedule_planner.py (3-4 giờ)
[C5]    run_with_feedback wrapper + áp dụng actions chính — frontend/components/common.py (3-4 giờ)
[B1]    Tách week_grid component dùng chung (REFACTOR) — frontend/components/week_grid.py mới (1 ngày)
[V1]    ShiftUpdate thêm clear_sp field — duty_schemas.py + schedule_service.py (1 giờ)
[A4+B6+R4] Dialog sửa tay ca + nút confirm đơn lẻ + compact view leader_sp — schedule_planner.py + shift_card.py (1 ngày)
[B4]    Biểu đồ bar chart thống kê (ui.echart built-in) — statistics.py (3-4 giờ)
```

### Sprint 2 — Tính năng còn thiếu (~8 ngày)
```
[R3]    scheduler_engine.py: xử lý partial confirmed ngày quyết toán (3-4 giờ)
        schedule_planner.py: UI hỗ trợ nếu cần thêm option
[R5]    settings.py: badge người đi dự án trong danh sách requests (1 giờ)
[P3]    Thêm nút "🗓️ Phân cả tháng" + dialog — frontend/pages/schedule_planner.py (3-4 giờ)
[N1]    Tên người ký: thêm signer_name vào shift_config + Settings Tab 1 (3 giờ)
        ⚠️ Cần xác nhận Q3 trước khi implement
[N4+N8] Export: hiện ngày lễ + label Cutoff/Friday trong file Excel (4 giờ)
        ⚠️ Cần xác nhận Q4: có muốn hiển thị tên ngày lễ không?
[N5]    Week Grid: phân biệt ngày lễ vs chưa phân ca trong lịch UI (2 giờ)
        Làm cùng B1 component để tránh sửa 2 lần
[N6]    Xóa vắng theo range: DELETE /absences/range + form UI (3 giờ)
[N7]    Validate ngày hợp lệ khi đăng ký xin trực (T7/CN/lễ) (1 giờ)
[B5]    Unconfirm endpoint + UI — backend/routers/schedule.py + schedule_planner.py
[T3]    is_sp_backup field + UI toggle — thay thế SP_BACKUP_LEADERS hard-code
[V4]    get_week_assignees: xác nhận nghiệp vụ Q2 rồi fix — constraint_service.py
[B2]    Trang xem lịch tháng (Month Calendar) — trang mới /lich-thang + navbar
[C2]    Filter nhân sự trong lịch tuần (client-side) — schedule_planner.py
[T4]    Transaction rollback scheduler_engine — backend/services/scheduler_engine.py
[T5]    Error handling api_client — frontend/api_client.py
```

### Sprint 3 — Cải thiện & Nâng cao (~7 ngày)
```
[P4]  launcher.py: cross-platform subprocess (Windows/Linux/macOS) (1 giờ)
[P5]  api_client.py + main.py: env var cho BASE_URL và CORS origins (1 giờ)
      ⚠️ Cần xác nhận Q5 trước
[C1]  Dashboard tổng quan (/ hoặc /dashboard)
[B3]  Quản lý đi dự án theo date range (cần bảng project_assignments mới)
[V3]  startup_init multi-year seeding
[V5]  Refactor confirm_shifts_for_week (ORM events awareness)
[T4]  Transaction rollback scheduler_engine (giảm ưu tiên — WAL mode đã giảm thiểu rủi ro)
[C4]  Mobile responsive
[D4]  Print view (?print=1 param, không cần route mới)
[D5]  DB backup endpoint GET /export/db-backup
[D1]  Import lịch sử Excel
```

### Sprint 1 — Thứ tự implement (tránh conflict)
```
 0. backend/config.py                       — R1 (os.makedirs database/) ← ĐẦU TIÊN
 1. backend/services/constraint_service.py  — R2 (delete_special_day cascade)
    ⚠️ Cần xác nhận Q6 trước khi chọn Option A/B/C
 2. backend/services/scheduler_engine.py    — P2 (fix position trong _get_rotation_state)
 3. backend/services/staff_service.py       — P1 (sync rotation khi đổi role) + V6 (LIKE bug)
 4. backend/services/schedule_service.py    — FIX-1 (confirmed filter)
 5. frontend/pages/week_view.py             — FIX-2 (sp_warning badge)
 6. backend/services/constraint_service.py  — V2 (absence check) + N3 (duplicate request)
 7. frontend/pages/settings.py              — N2 (filter NV trong dropdown đăng ký)
    ⚠️ Chỉ implement sau khi xác nhận Q1
 8. frontend/components/common.py           — T2 (confirm color) + C5 (run_with_feedback)
 9. backend/schemas/duty_schemas.py         — V1 (thêm clear_sp field)
10. backend/services/schedule_service.py    — V1 (update_shift handle clear_sp)
11. frontend/pages/schedule_planner.py      — A3 (warnings dialog trong do_gen)
12. frontend/components/week_grid.py (mới)  — B1 (tách component dùng chung)
13. frontend/pages/schedule_planner.py      — B1 (import week_grid, xóa code cũ)
14. frontend/pages/week_view.py             — B1 (import week_grid, xóa code cũ)
15. frontend/components/shift_card.py       — A4 + B6 + R4 (edit, confirm, leader_sp compact view)
16. frontend/pages/schedule_planner.py      — A4 + B6 (implement dialogs)
17. frontend/pages/statistics.py            — B4 (thêm ui.echart bar chart)
18. [Sau xác nhận Q1] backend/routers/constraints.py — N2 backend validation nếu cần
19. Verify R2: khai báo special_day → generate → xóa special_day → kiểm tra duty_shifts không có 2 ca cùng ngày
20. Verify P1: tạo NV → đổi role LD → kiểm tra rotation_state rows đúng
```

### Câu hỏi nghiệp vụ cần xác nhận trước khi implement

> Những điểm dưới đây cần hỏi người dùng cuối để tránh làm lại:

- **[Q1]** LD và SP có được phép "đăng ký xin trực" không? → Ảnh hưởng N2 (filter dropdown settings)
- **[Q2]** Ca đang ở trạng thái `draft` có được coi là "đã trực trong tuần" khi generate không? → Ảnh hưởng V4 (get_week_assignees)
- **[Q3]** Người ký lịch trực có thể thay đổi không, hay cố định là 1 người? → Ảnh hưởng N1 (signer_name field)
- **[Q4]** Trong file Excel và lịch UI, khi có ngày lễ giữa tuần, có muốn hiển thị tên ngày lễ (VD: "Giỗ Tổ Hùng Vương") không? → Ảnh hưởng N4, N5
- **[Q5]** Hệ thống có cần chạy trên máy chủ mạng nội bộ (nhiều người dùng đồng thời từ nhiều máy) hay chỉ chạy cục bộ 1 máy? → Ảnh hưởng P5 (env var cho URL), và quyết định có cần authentication hay không
- **[Q6]** Khi xóa special day (cutoff, settlement) đã có ca liên quan, hành vi mong muốn là gì? → Ảnh hưởng cách implement R2:
  - *Option A*: Tự động xóa ca draft + cảnh báo HTTP 409 nếu có ca confirmed (đề xuất)
  - *Option B*: Từ chối xóa nếu đang có bất kỳ ca nào (yêu cầu xóa ca trước)
  - *Option C*: Cho phép xóa tự do mà không ảnh hưởng ca đã tạo

---

## 5. CÁC ĐIỂM KỸ THUẬT CẦN LƯU Ý

### 5.1 Vấn đề tiềm ẩn trong scheduler_engine

1. **`_preferred_day_mismatch` logic**: ✅ Logic đúng — `calendar_utils.compute_cutoff_dates()` chỉ chọn ngày làm việc T2-T6, nên `current_date.weekday()` khi generate cutoff luôn nằm trong 0-4, phép tính `% 5` cho kết quả chính xác.

2. **Settlement sub-shift không cập nhật rotation**: `nvs_sub = remaining_nv[:sub_count]` — không gọi `_update_rotation`, đúng theo thiết kế nhưng cần document rõ.

3. **Race condition khi generate đồng thời**: `db.flush()` trong loop không có transaction-level lock — nếu 2 request generate cùng lúc, rotation_state có thể sai. Tuy nhiên `database.py` đã bật **WAL mode** (`PRAGMA journal_mode=WAL`) — giảm lock contention đáng kể; với 1-2 user thực tế, race condition rất khó xảy ra → T4 (rollback) giảm ưu tiên xuống Sprint 3.

4. **Hard-coded SP_BACKUP_LEADERS**: Tên "Trần Thị Mỹ Linh" và "Trần Thị Bích Phương" trong `config.py` — nếu thêm/đổi tên cần sửa code.

5. **T2. `confirm_dialog` dùng màu sai**: `frontend/components/common.py` — hàm `confirm_dialog()` hard-code `color=negative` (đỏ) cho nút xác nhận, kể cả các thao tác tích cực như "Xác nhận tuần". Cần thêm tham số `confirm_color` vào hàm.

6. **T3. `SP_BACKUP_LEADERS` hard-coded** (Sprint 2): `backend/config.py` — nếu nhân sự thay đổi phải sửa code và restart. Đề xuất: thêm field `is_sp_backup: bool` vào bảng `staff` và UI toggle trong trang Danh sách NV. Không cần bảng mới, chỉ thêm 1 cột.

7. **T4. `generate_schedule_for_week` thiếu transaction rollback**: `backend/services/scheduler_engine.py` — nếu sinh ca thứ 3/5 bị lỗi, 2 ca đầu đã `db.flush()`. Cần bọc loop trong `try/except` với `db.rollback()` khi exception.

8. **T5. `api_client._delete()` không phân biệt lỗi**: Trả `bool` nhưng không phân biệt 404 (không tìm thấy) vs network error — frontend không thể hiển thị thông báo lỗi chính xác.

9. **V3. `startup_init` chỉ seed dữ liệu cho `CURRENT_YEAR`** (Sprint 3): `backend/services/schedule_service.py` — `startup_init()` gọi `init_rotation_for_year(db, CURRENT_YEAR)` chỉ cho năm hiện tại. Nếu có staff mới tạo giữa năm, họ không có rotation rows. Edge case thấp tác động.

10. **V4. `get_week_assignees` đọc cả ca draft** (Sprint 2 — cần quyết định nghiệp vụ): `backend/services/constraint_service.py` — `get_week_assignees()` không filter `status`. Nếu có ca draft cũ trong DB, người đó bị coi là "đã trực tuần" và bị bỏ qua khi generate. Cần xác nhận: draft có tính là "đã phân" không?

11. **V5. `confirm_shifts_for_week` dùng bulk `.update()` bypass ORM events** (Sprint 3 — ghi chú): `backend/services/schedule_service.py` — bulk `.update()` bỏ qua SQLAlchemy ORM layer. Nếu sau này thêm audit log trên `DutyShift`, events sẽ không trigger.

### 5.2 Thiếu validation

- ~~Chưa validate: NV đăng ký xin trực ngày mà họ đã khai báo vắng~~ → **Đã xếp vào Sprint 1 [V2]**: fix trong `constraint_service.py:validate_nv_request()`.
- Chưa validate: Một người không thể vừa là LĐ vừa là SP trong cùng một ca (trừ leader_sp case).
- API `PUT /schedule/{shift_id}` không kiểm tra conflict trùng người trong cùng ca.

### 5.3 Database

- SQLite phù hợp cho 25 người, ~250 ca/năm → không cần migrate sang PostgreSQL.
- Thiếu migration tool (Alembic) — nếu schema thay đổi phải recreate DB.

---

## 6. TÓM TẮT NHANH

| Ưu tiên | Việc cần làm | Ước lượng effort |
|---------|-------------|-----------------|
| ✅ Done | Export Excel UI + UI xác nhận cutoff/settlement | — |
| 🔴 Bug fix | R1 (db dir), R2 (cascade), P1,P2 (rotation), FIX-1,2, V1,2,6, N2,N3 + T2 | ~4 giờ |
| 🔴 Critical | A3 warnings + A4 edit dialog + B1 DRY refactor + B6 + R4 compact view | ~3.5 ngày |
| 🟠 Sprint 2 | R3 (partial confirmed) + R5 (on-project badge) + P3 + B4,C5,N1,N4,N5,N6,N8,B2,B5 | ~8 ngày |
| 🟡 Medium | C1 Dashboard + C2 Filter + T3 is_sp_backup + N7 validate + V4 | ~4 ngày |
| 🟢 Low | P4,P5 (platform/env) + D1-D5, V3, V5 ORM, T4 (WAL giảm ưu tiên), T5 | ~7 ngày |

**Tổng ước lượng hoàn thiện**: ~21 ngày dev (1 developer, full-time)
