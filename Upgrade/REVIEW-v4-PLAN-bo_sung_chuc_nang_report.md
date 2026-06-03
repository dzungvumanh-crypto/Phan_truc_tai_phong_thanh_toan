# REVIEW v4 — Kế hoạch Hoàn thiện Phân lịch trực PTT
## Phân tích toàn diện codebase · Claude Sonnet 4.6 · 2026-05-29

> **Bối cảnh**: PLAN v3 (được upload) đã tích hợp đầy đủ REVIEW v1, v2, v3. Review này **chỉ tập trung vào những vấn đề chưa từng xuất hiện trong bất kỳ review nào trước đó**, phát hiện từ việc đọc kỹ các file chưa được phân tích đủ sâu: `launcher.py`, `database.py`, logic đồng bộ `rotation_state` khi thay đổi nhân sự, và kiểm tra asymmetry giữa API và UI.

---

## PHẦN 1 — XÁC NHẬN: PLAN v3 CHÍNH XÁC VÀ ĐẦY ĐỦ

Tất cả các mục trong PLAN v3 đều đúng về mặt kỹ thuật và đã được ưu tiên hợp lý. Không có điểm nào sai. Review này bổ sung 5 vấn đề hoàn toàn mới.

---

## PHẦN 2 — 5 VẤN ĐỀ MỚI HOÀN TOÀN

### P1. 🔴 `update_staff` không đồng bộ `rotation_state` khi đổi role

```python
# backend/services/staff_service.py — update_staff()
def update_staff(db, staff_id, full_name=None, role=None, ...):
    s = get_staff_by_id(db, staff_id)
    if role is not None:
        s.role = role   # ← chỉ cập nhật cột role trong bảng staff
    db.commit()
    # ← KHÔNG xóa rotation_state cũ, KHÔNG tạo rotation_state mới
```

**Hậu quả cụ thể** khi đổi NV → LD:

- Các `rotation_state` rows cũ với `role IN ('NV', 'NV_friday', 'NV_cutoff')` **vẫn tồn tại** — orphan data.
- Các `rotation_state` rows mới với `role IN ('LD', 'LD_friday', 'LD_cutoff')` **chưa được tạo**.
- Lần đầu người này được phân ca với tư cách LD, `_get_rotation_state()` sẽ tạo row mới với `position=staff_id` — **không nhất quán** với giá trị `display_order * 10 + id` mà `init_rotation_for_year()` và `create_staff()` dùng.
- Kết quả: người vừa đổi role có thể bị sắp xếp vào vị trí sai trong vòng xoay.

Tình huống xảy ra thực tế: Lãnh đạo mới được bổ nhiệm từ nhân viên, hoặc nhân viên đặc thù được bổ sung vào nhóm SP.

**Fix**:
```python
def update_staff(db, staff_id, role=None, ...):
    old_role = s.role
    if role is not None and role != old_role:
        s.role = role
        # Xóa rotation_state cũ
        old_rot_roles = _ROLE_MAP.get(old_role, [])
        db.query(RotationState).filter(
            RotationState.staff_id == staff_id,
            RotationState.role.in_(old_rot_roles),
        ).delete()
        # Tạo rotation_state mới với position đúng
        for rot_role in _ROLE_MAP.get(role, []):
            db.add(RotationState(
                year=CURRENT_YEAR, role=rot_role, staff_id=staff_id,
                shift_count=0, last_used=None,
                position=s.display_order * 10 + staff_id,
            ))
    db.commit()
```

**File cần sửa**: `backend/services/staff_service.py`
**Sprint**: Sprint 1 — ảnh hưởng trực tiếp đến tính đúng đắn của vòng xoay khi có thay đổi nhân sự.

---

### P2. 🔴 `_get_rotation_state` tạo row mới với `position=staff_id` — không nhất quán

Liên quan đến P1 nhưng là vấn đề độc lập: `_get_rotation_state()` trong `scheduler_engine.py` được gọi bất cứ khi nào cần lấy trạng thái vòng xoay của một người. Nếu row chưa tồn tại (người mới, hoặc sau khi đổi role theo fix P1), nó tạo row với:

```python
# scheduler_engine.py — _get_rotation_state()
obj = RotationState(
    year=year, role=role, staff_id=staff_id,
    shift_count=0, last_used=None,
    position=staff_id,   # ← dùng staff_id (1-25) làm tiebreak
)
```

Trong khi `init_rotation_for_year()` và `create_staff()` đều dùng:
```python
position=person.display_order * 10 + person.id  # ← giá trị 10x-99x lớn hơn nhiều
```

**Hậu quả**: Người mới được tạo rotation qua `_get_rotation_state()` (fallback path) sẽ có `position` nhỏ hơn nhiều so với người được init đúng cách — dẫn đến họ luôn được ưu tiên hơn trong tie-break, phá vỡ thứ tự vòng xoay mong muốn.

**Fix**: Sửa `_get_rotation_state()` để lấy `display_order` từ bảng `Staff`:
```python
def _get_rotation_state(db, staff_id, year, role):
    obj = db.query(RotationState).filter_by(year=year, role=role, staff_id=staff_id).first()
    if not obj:
        staff = db.query(Staff).filter_by(id=staff_id).first()
        pos = (staff.display_order * 10 + staff_id) if staff else staff_id
        obj = RotationState(year=year, role=role, staff_id=staff_id,
                            shift_count=0, last_used=None, position=pos)
        db.add(obj)
        db.flush()
    return obj
```

**File cần sửa**: `backend/services/scheduler_engine.py`
**Sprint**: Sprint 1 — cùng lúc với P1, fix 3 dòng.

---

### P3. 🟠 `generate_schedule` (tháng) tồn tại trong backend và `api_client` nhưng **không có UI nào gọi**

```python
# frontend/api_client.py — hàm này tồn tại nhưng không trang nào gọi
def generate_schedule(month: int, year: int, overwrite_draft: bool = False):
    return _post("/schedule/generate", json={...})
```

Toàn bộ frontend chỉ dùng `generate_week_schedule()`. Người dùng muốn lập lịch nhanh cho cả tháng (thay vì click từng tuần 4-5 lần) không có cách nào làm được từ UI.

Thêm nữa, `GenerateRequest` schema **không có `overwrite_confirmed`** — khác với `GenerateWeekRequest`:
```python
class GenerateRequest(BaseModel):
    month: int
    year: int
    overwrite_draft: bool = False
    # ← KHÔNG có overwrite_confirmed — confirmed ca luôn bị bỏ qua khi generate tháng
```

**Đề xuất**: Thêm nút "🗓️ Phân cả tháng" vào schedule_planner (hoặc statistics page), kèm dialog chọn tháng/năm và option `overwrite_draft`. Không cần thêm `overwrite_confirmed` vào backend — behavior hiện tại (bảo vệ confirmed) là đúng.

**File cần sửa**: `frontend/pages/schedule_planner.py` (hoặc trang mới)
**Sprint**: Sprint 2 — tính năng quan trọng nhưng không blocking.

---

### P4. 🟠 `launcher.py` chỉ chạy được trên Windows — không có cross-platform support

```python
# launcher.py — dòng 76 và 94
backend = subprocess.Popen(
    [...],
    creationflags=subprocess.CREATE_NEW_CONSOLE,   # ← Windows-only flag
)
frontend = subprocess.Popen(
    [...],
    creationflags=subprocess.CREATE_NEW_CONSOLE,   # ← Windows-only flag
)
```

`subprocess.CREATE_NEW_CONSOLE` là hằng số chỉ tồn tại trên Windows. Nếu chạy `python launcher.py` trên Linux hoặc macOS sẽ raise `AttributeError: module 'subprocess' has no attribute 'CREATE_NEW_CONSOLE'`.

Tuy hệ thống này chủ yếu dùng trên Windows (Agribank môi trường Windows), nhưng developer có thể cần chạy trên macOS/Linux để test hoặc deploy.

**Fix**:
```python
import platform

def popen_args(cmd):
    kwargs = {"cwd": BASE_DIR}
    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    else:
        # macOS/Linux: chạy trong background, không tạo console mới
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    return kwargs

backend  = subprocess.Popen([PYTHON, "run_backend.py"],  **popen_args(None))
frontend = subprocess.Popen([PYTHON, "frontend/main.py"], **popen_args(None))
```

**File cần sửa**: `launcher.py`
**Sprint**: Sprint 3 — không urgent với môi trường Windows.

---

### P5. 🟡 `BASE_URL` và `allow_origins` hardcode `localhost` — không deploy được lên server nội bộ

```python
# frontend/api_client.py
BASE_URL = "http://localhost:8001/api/v1"   # hardcode

# backend/main.py
allow_origins=["http://localhost:8081", "http://127.0.0.1:8081"]  # hardcode
```

Nếu cần deploy lên một máy chủ trong mạng nội bộ Agribank (ví dụ `192.168.1.100`) để nhiều người dùng trên nhiều máy tính cùng truy cập, cả hai giá trị trên phải sửa thủ công trong code và restart.

**Fix**: Đọc từ biến môi trường với fallback về `localhost`:
```python
# frontend/api_client.py
import os
BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8001/api/v1")

# backend/main.py
import os
_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8081")
allow_origins = [_frontend_url, "http://127.0.0.1:8081"]
```

Thêm file `.env.example` hoặc ghi chú vào `CLAUDE.md` về cách cấu hình.

**Sprint**: Sprint 3 — chỉ cần thiết nếu deploy ra mạng nội bộ.

---

## PHẦN 3 — PHÂN TÍCH BỔ SUNG: CÁC VẤN ĐỀ NHẬN XÉT LẠI TỪ PLAN v3

### 3.1 Làm rõ về `_preferred_day_mismatch` và ca Cutoff/Settlement

PLAN v3 ghi chú: *"`_preferred_day_mismatch` logic có thể không chính xác với ngày cut-off/quyết toán"*. Sau khi phân tích kỹ:

**Kết luận**: Logic này **đúng** trong thực tế. Lý do: `compute_cutoff_dates()` trong `calendar_utils.py` chỉ chọn ngày làm việc (T2-T6, không lễ), và `generate_schedule()` cũng bỏ qua T7/CN và lễ. Vì thế `current_date.weekday()` khi generate cutoff luôn nằm trong 0-4 (T2-T6), và phép tính `% 5` vẫn cho kết quả đúng.

→ **Có thể bỏ mục này** khỏi danh sách technical debt hoặc chuyển vào "đã kiểm tra, OK".

### 3.2 Làm rõ về WAL mode trong `database.py`

`database.py` đã bật `PRAGMA journal_mode=WAL` — đây là cấu hình tốt cho SQLite, giúp giảm lock contention và cải thiện hiệu năng đọc đồng thời. Điều này cũng giảm thiểu (nhưng không loại bỏ hoàn toàn) race condition được đề cập trong PLAN v3 (V4/T4). WAL cho phép nhiều reader đồng thời với 1 writer — nên trong thực tế với 1-2 user, race condition rất khó xảy ra.

→ **Giảm ưu tiên** T4 (transaction rollback) xuống Sprint 3.

### 3.3 Roster List vs Statistics — dữ liệu shift_count có nhất quán không?

`roster_list.py` dùng `api_client.get_shift_count(year)` để hiện cột "Số ca" cho từng người — đây là **tổng confirmed shifts** phân theo người (cùng API với Statistics page). Dữ liệu nhất quán, không có vấn đề.

Tuy nhiên, `roster_list.py` chỉ hiện **số tổng** (không breakdown theo loại ca) vì layout bảng chật. Đây không phải bug — chỉ là feature gap so với Statistics. Không cần xử lý.

---

## PHẦN 4 — LỘ TRÌNH CẬP NHẬT

### Sprint 1 — thêm P1 và P2 vào (tổng ~5.5 ngày)

```
Bổ sung vào đầu Sprint 1 (trước các fix khác):
  [P1]  staff_service.py: đồng bộ rotation_state khi update_staff đổi role      (1 giờ)
  [P2]  scheduler_engine.py: _get_rotation_state dùng display_order*10+id       (15 phút)

[Giữ nguyên] FIX-1, FIX-2, V2, V6, N3, T2, N2, C5, V1, A3, B1, A4, B6, B4
```

### Sprint 2 — thêm P3 (tổng ~7.5 ngày)

```
Bổ sung vào Sprint 2:
  [P3]  schedule_planner.py: thêm nút "🗓️ Phân cả tháng" + dialog              (3-4 giờ)

[Giữ nguyên] N1, N4+N8, N5, N6, N7, B5, T3, V4, B2, C2, T5
```

### Sprint 3 — thêm P4 và P5 (tổng ~7 ngày)

```
Bổ sung vào Sprint 3:
  [P4]  launcher.py: cross-platform subprocess (Windows/Linux/macOS)             (1 giờ)
  [P5]  api_client.py + backend/main.py: env var cho BASE_URL và CORS origin     (1 giờ)

[Giữ nguyên] C1, B3, V3, V5, C4, D4, D5, D1
[Giảm ưu tiên T4] T4 xuống Sprint 3 do WAL mode đã giảm thiểu rủi ro
```

---

## PHẦN 5 — CHECKLIST SPRINT 1 CẬP NHẬT (16 → 18 bước)

```
□  1. backend/services/scheduler_engine.py   — P2 (fix position trong _get_rotation_state)
□  2. backend/services/staff_service.py      — P1 (sync rotation khi đổi role) + V6 (LIKE bug)
□  3. backend/services/schedule_service.py   — FIX-1 (confirmed filter)
□  4. frontend/pages/week_view.py            — FIX-2 (sp_warning badge)
□  5. backend/services/constraint_service.py — V2 (absence check) + N3 (duplicate request)
□  6. frontend/pages/settings.py             — N2 (filter NV trong dropdown đăng ký)
     ⚠️ Chỉ implement sau khi xác nhận Q1
□  7. frontend/components/common.py          — T2 (confirm color) + C5 (run_with_feedback)
□  8. backend/schemas/duty_schemas.py        — V1 (thêm clear_sp field)
□  9. backend/services/schedule_service.py   — V1 (update_shift handle clear_sp)
□ 10. frontend/pages/schedule_planner.py     — A3 (warnings dialog trong do_gen)
□ 11. frontend/components/week_grid.py (mới) — B1 (component dùng chung)
□ 12. frontend/pages/schedule_planner.py     — B1 (import week_grid, xóa code cũ)
□ 13. frontend/pages/week_view.py            — B1 (import week_grid, xóa code cũ)
□ 14. frontend/components/shift_card.py      — A4 + B6 (on_edit_click, on_confirm)
□ 15. frontend/pages/schedule_planner.py     — A4 + B6 (implement dialogs)
□ 16. frontend/pages/statistics.py           — B4 (ui.echart bar chart)
□ 17. [Sau xác nhận Q1] backend/routers/constraints.py — N2 backend validation
□ 18. Verify: chạy test tạo mới staff → đổi role → check rotation_state rows   — P1 manual test
```

---

## PHẦN 6 — TÓM TẮT CÁC PHÁT HIỆN MỚI SO VỚI PLAN v3

| # | Vấn đề | File | Sprint | Mức độ |
|---|--------|------|--------|--------|
| P1 | `update_staff` không sync `rotation_state` khi đổi role | `staff_service.py` | 1 | 🔴 Cao |
| P2 | `_get_rotation_state` tạo row với `position=staff_id` sai | `scheduler_engine.py` | 1 | 🔴 Cao |
| P3 | `generate_schedule` tháng: API + `api_client` có nhưng không có UI | `schedule_planner.py` | 2 | 🟠 Trung bình |
| P4 | `launcher.py` dùng `CREATE_NEW_CONSOLE` — Windows-only | `launcher.py` | 3 | 🟡 Thấp |
| P5 | `BASE_URL` và CORS `allow_origins` hardcode `localhost` | `api_client.py`, `main.py` | 3 | 🟡 Thấp |

**Làm rõ từ PLAN v3**:

| Mục | Kết luận |
|-----|----------|
| `_preferred_day_mismatch % 5` với cutoff | ✅ Logic đúng — cutoff chỉ rơi T2-T6 |
| WAL mode trong database.py | ✅ Đã bật, giảm thiểu race condition |
| Roster vs Statistics inconsistency | ✅ Dữ liệu nhất quán — roster chỉ hiện total |

**Tổng ước lượng hoàn thiện cập nhật**: ~20 ngày dev (+2 ngày do thêm P1+P2 Sprint 1, P3 Sprint 2).

---

## PHẦN 7 — CÂU HỎI NGHIỆP VỤ CÒN LẠI (kế thừa từ PLAN v3, thêm 1 mới)

> Những điểm sau cần hỏi người dùng cuối trước khi implement để tránh làm lại:

- **[Q1]** LD và SP có được phép "đăng ký xin trực" không? → Ảnh hưởng N2
- **[Q2]** Ca `draft` có được coi là "đã trực trong tuần" khi generate không? → Ảnh hưởng V4
- **[Q3]** Người ký lịch trực có thể thay đổi không? → Ảnh hưởng N1 (signer_name)
- **[Q4]** Khi có ngày lễ giữa tuần, có muốn hiển thị tên lễ trong Excel và UI không? → Ảnh hưởng N4, N5
- **[Q5]** *(Mới)* Hệ thống có cần chạy trên máy chủ mạng nội bộ (nhiều người dùng) hay chỉ chạy cục bộ 1 máy? → Ảnh hưởng P5 (env var cho URL), và quyết định có cần authentication không
