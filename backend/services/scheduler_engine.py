"""
Scheduler Engine — Thuật toán phân lịch trực tự động.

Thứ tự ưu tiên:
  1. Người đã đăng ký xin trực (duty_requests)
  2. Vòng xoay cân bằng (rotation_state: shift_count → last_used → position)

Loại ca:
  - normal: ca thường (T2-T5)
  - friday: thứ Sáu (vòng xoay riêng LD_friday, NV_friday)
  - cutoff: ngày cut-off cuối tháng (vòng xoay riêng LD_cutoff, NV_cutoff)
  - settlement_main / settlement_sub: ngày quyết toán (2 cụm cùng ngày)
"""
import json
import calendar as _cal
from datetime import datetime, date as _date, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.config import SP_BACKUP_LEADERS, DEFAULT_NV_COUNT
from backend.models.duty_models import Staff, DutyShift, DutyShiftNV, RotationState, ShiftConfig
from backend.services.staff_service import get_available_pool
from backend.services.constraint_service import (
    get_requests_for_date, get_special_day, get_holiday_dates,
    get_shift_config, get_week_assignees,
)
from backend.services.calendar_utils import (
    get_month_working_days, get_week_dates, is_friday,
)


# ══════════════════════════════════════════════════════════════
# VÒNG XOAY — helpers nội bộ
# ══════════════════════════════════════════════════════════════

def _get_rotation_state(db: Session, staff_id: int, year: int, role: str) -> RotationState:
    """Lấy hoặc tạo mới rotation_state cho (year, role, staff_id)."""
    obj = db.query(RotationState).filter_by(
        year=year, role=role, staff_id=staff_id
    ).first()
    if not obj:
        # P2: Dùng display_order*10+id như init_rotation_for_year, không dùng staff_id trực tiếp
        staff_obj = db.query(Staff).filter_by(id=staff_id).first()
        pos = (staff_obj.display_order * 10 + staff_id) if staff_obj else staff_id
        obj = RotationState(
            year=year, role=role, staff_id=staff_id,
            shift_count=0, last_used=None, position=pos,
        )
        db.add(obj)
        db.flush()
    return obj


def _preferred_day_mismatch(last_used: Optional[str], current_date: Optional[str]) -> int:
    """
    Tính độ lệch giữa ngày mong muốn tiếp theo và ngày hiện tại.
    - last_used = 'YYYY-MM-DD' ngày trực lần trước
    - current_date = 'YYYY-MM-DD' ngày đang xét
    Trả 0 nếu hôm nay đúng là ngày tiếp theo sau last_used (ưu tiên cao nhất).
    Trả khoảng cách vòng tròn Mon-Fri (1-4) nếu không khớp.
    Trả 5 nếu thiếu dữ liệu (last_used hoặc current_date là None).
    """
    if not last_used or not current_date:
        return 5
    try:
        last_wd = datetime.strptime(last_used, "%Y-%m-%d").weekday()   # 0=Mon..4=Fri
        curr_wd = datetime.strptime(current_date, "%Y-%m-%d").weekday()
        preferred_next = (last_wd + 1) % 5   # vòng trong Mon-Fri (0-4)
        # Khoảng cách vòng tròn từ preferred_next đến curr_wd
        diff = (curr_wd - preferred_next) % 5
        return diff  # 0 = khớp hoàn hảo, 1-4 = lệch
    except (ValueError, AttributeError):
        return 5


def _sort_by_rotation(db: Session, candidates: List[Staff],
                      year: int, role: str,
                      current_date: str = None) -> List[Staff]:
    """
    Sắp xếp candidates theo vòng xoay:
    shift_count ASC                  (công bằng tổng ca — ưu tiên nhất)
    → day_mismatch ASC               (xoay ngày trong tuần: 0=đúng thứ tiếp theo)
    → last_used ASC (cũ hơn ưu tiên)
    → position ASC → id ASC
    """
    def sort_key(p: Staff):
        s = _get_rotation_state(db, p.id, year, role)
        day_miss = _preferred_day_mismatch(s.last_used, current_date)
        return (
            s.shift_count,
            day_miss,
            s.last_used or "0000-00-00",
            s.position,
            p.id,
        )
    return sorted(candidates, key=sort_key)


def _pick_by_rotation(db: Session, candidates: List[Staff],
                      year: int, role: str,
                      current_date: str = None) -> Optional[Staff]:
    """Chọn 1 người theo vòng xoay (người đầu danh sách sau sort)."""
    if not candidates:
        return None
    return _sort_by_rotation(db, candidates, year, role, current_date)[0]


def _update_rotation(db: Session, staff_id: int, year: int,
                     role: str, date_str: str) -> None:
    """Tăng shift_count, cập nhật last_used. Gọi sau khi chọn xong."""
    obj = _get_rotation_state(db, staff_id, year, role)
    obj.shift_count += 1
    obj.last_used = date_str
    db.flush()


# ══════════════════════════════════════════════════════════════
# CHỌN TỪNG VAI TRÒ
# ══════════════════════════════════════════════════════════════

def _pick_leader(db: Session, pool_ld: List[Staff], requests: dict,
                 year: int, date_str: str,
                 rotation_role: str = "LD") -> Optional[Staff]:
    """
    Chọn 1 Lãnh đạo. Ưu tiên người chưa trực tuần này (fresh) trước.
    rotation_role: 'LD' | 'LD_friday' | 'LD_cutoff'
    Fix: thêm week_ids để tránh phân LĐ đã kiêm SP backup cùng tuần.
    """
    if not pool_ld:
        return None

    week_ids = get_week_assignees(db, date_str)

    # Ưu tiên LĐ chưa trực tuần này (kể cả chưa làm SP backup)
    fresh_ld   = [p for p in pool_ld if p.id not in week_ids]
    repeat_ld  = [p for p in pool_ld if p.id in week_ids]

    requested_ids = set(requests.get("LD", []))

    if fresh_ld:
        requested = [p for p in fresh_ld if p.id in requested_ids]
        candidates = requested if requested else fresh_ld
    else:
        # Fallback: tất cả LĐ đã trực — bình thường khi 4 LĐ cho 5 ngày
        requested = [p for p in repeat_ld if p.id in requested_ids]
        candidates = requested if requested else repeat_ld

    if not candidates:
        return None

    winner = _pick_by_rotation(db, candidates, year, rotation_role, current_date=date_str)
    if winner:
        _update_rotation(db, winner.id, year, rotation_role, date_str)
    return winner


def _pick_sp(db: Session, pool: dict, requests: dict,
             year: int, date_str: str,
             ld_role: str = "LD") -> Tuple[Optional[Staff], Optional[str]]:
    """
    Chọn người tác nghiệp Song Phương. Logic 5 cấp (ưu tiên fresh trong tuần).
    Trả (person, warning_code):
      warning_code = None | 'leader_sp' | 'no_sp'
    ld_role: rotation role dùng khi backup leader kiêm nhiệm ('LD' | 'LD_friday' | 'LD_cutoff')

    Thứ tự ưu tiên:
      1a. SP sẵn + chưa trực tuần này
      2a. Backup LD (Mỹ Linh/Bích Phương) chưa trực tuần này
      2b. Backup LD đã trực tuần (vẫn ưu tiên hơn SP tổ trực lần 2) ← SP-FIX-1
      1b. SP đã trực tuần này (fallback khi cả SP và backup đều kiệt)
      3.  Không ai → no_sp
    """
    pool_sp = pool["SP"]
    pool_ld = pool["LD"]
    week_ids = get_week_assignees(db, date_str)

    # Cấp 1a: SP sẵn + chưa trực tuần này
    fresh_sp = [p for p in pool_sp if p.id not in week_ids]
    if fresh_sp:
        requested_ids = set(requests.get("SP", []))
        requested = [p for p in fresh_sp if p.id in requested_ids]
        candidates = requested if requested else fresh_sp
        winner = _pick_by_rotation(db, candidates, year, "SP", current_date=date_str)
        if winner:
            _update_rotation(db, winner.id, year, "SP", date_str)
        return winner, None

    # Cấp 2a: backup LD chưa trực tuần này — kiêm Lãnh đạo + Song Phương
    # T3: dùng is_sp_backup từ DB (admin có thể toggle qua Roster List UI)
    backup = [p for p in pool_ld
              if getattr(p, "is_sp_backup", 0) == 1 and p.id not in week_ids]
    if backup:
        winner = _pick_by_rotation(db, backup, year, ld_role, current_date=date_str)
        if winner:
            _update_rotation(db, winner.id, year, ld_role, date_str)
        return winner, "leader_sp"

    # Cấp 2b: backup LD đã trực tuần (SP-FIX-1: vẫn ưu tiên hơn SP tổ trực lần 2)
    backup_repeat = [p for p in pool_ld if getattr(p, "is_sp_backup", 0) == 1]
    if backup_repeat:
        winner = _pick_by_rotation(db, backup_repeat, year, ld_role, current_date=date_str)
        if winner:
            _update_rotation(db, winner.id, year, ld_role, date_str)
        return winner, "leader_sp"

    # Cấp 1b: fallback — dùng lại SP đã trực (tất cả fresh đã hết, cả backup cũng kiệt)
    if pool_sp:
        requested_ids = set(requests.get("SP", []))
        requested = [p for p in pool_sp if p.id in requested_ids]
        candidates = requested if requested else pool_sp
        winner = _pick_by_rotation(db, candidates, year, "SP", current_date=date_str)
        if winner:
            _update_rotation(db, winner.id, year, "SP", date_str)
        return winner, None

    # Cấp 3: không ai
    return None, "no_sp"


def _pick_nvs(db: Session, pool_nv: List[Staff], requests: dict,
              year: int, date_str: str,
              nv_slots: int, sp_warning: Optional[str],
              rotation_role: str = "NV") -> List[Staff]:
    """
    Chọn danh sách NV cho ca.
    - sp_warning='leader_sp' → cố định 2 NV
    - Ưu tiên: NV chưa trực tuần này (fresh) → NV đã trực tuần (fallback)
    - Trong mỗi nhóm: người đăng ký trước, sau đó vòng xoay
    rotation_role: 'NV' | 'NV_friday' | 'NV_cutoff'
    """
    actual_slots = 2 if sp_warning == "leader_sp" else nv_slots

    week_ids = get_week_assignees(db, date_str)
    fresh_nv    = [p for p in pool_nv if p.id not in week_ids]
    repeated_nv = [p for p in pool_nv if p.id in week_ids]

    requested_ids = set(requests.get("NV", []))

    # Xây dựng ordered_pool: fresh (có đăng ký → vòng xoay) rồi repeated
    ordered_pool: List[Staff] = (
        [p for p in fresh_nv if p.id in requested_ids]
        + _sort_by_rotation(db, [p for p in fresh_nv if p.id not in requested_ids],
                            year, rotation_role, current_date=date_str)
        + [p for p in repeated_nv if p.id in requested_ids]
        + _sort_by_rotation(db, [p for p in repeated_nv if p.id not in requested_ids],
                            year, rotation_role, current_date=date_str)
    )

    selected: List[Staff] = []
    seen: set = set()
    for p in ordered_pool:
        if len(selected) >= actual_slots:
            break
        if p.id not in seen:
            seen.add(p.id)
            selected.append(p)
            _update_rotation(db, p.id, year, rotation_role, date_str)

    return selected


# ══════════════════════════════════════════════════════════════
# BUILD SHIFT DICT
# ══════════════════════════════════════════════════════════════

def _build_shift(shift_date: str, shift_type: str, leader: Optional[Staff],
                 sp: Optional[Staff], sp_warning: Optional[str],
                 nvs: List[Staff]) -> dict:
    return {
        "shift_date": shift_date,
        "shift_type": shift_type,
        "leader_id": leader.id if leader else None,
        "sp_id": sp.id if sp else None,
        "sp_warning": sp_warning,
        "nv_ids": json.dumps([p.id for p in nvs]),
        "nv_count": len(nvs),
        "is_auto": 1,
        "status": "draft",
    }


# ══════════════════════════════════════════════════════════════
# GENERATE TỪNG LOẠI CA
# ══════════════════════════════════════════════════════════════

def _generate_normal_or_friday(db: Session, date_str: str, year: int,
                                nv_count: int,
                                ld_role: str, nv_role: str,
                                shift_type: str) -> Tuple[List[dict], List[dict]]:
    """
    Sinh ca thường hoặc thứ Sáu.
    Trả (shifts, warnings).
    """
    pool = get_available_pool(db, date_str)
    requests = get_requests_for_date(db, date_str, year)
    warnings = []

    sp, sp_warn = _pick_sp(db, pool, requests, year, date_str, ld_role)

    if sp_warn == "leader_sp":
        leader = sp          # backup LD là leader của ca, kiêm Song Phương
        sp = None            # slot SP để trống
        name = leader.full_name if leader else "?"
        warnings.append({"date": date_str, "type": "leader_sp",
                         "msg": f"{name} (LĐ) kiêm Song Phương ngày {date_str} — ghép 2 NV"})
    else:
        leader = _pick_leader(db, pool["LD"], requests, year, date_str, ld_role)
        if not leader:
            warnings.append({"date": date_str, "type": "no_leader",
                             "msg": f"Không có Lãnh đạo khả dụng ngày {date_str}"})
        if sp_warn == "no_sp":
            warnings.append({"date": date_str, "type": "no_sp",
                             "msg": f"Không có ai tác nghiệp Song Phương ngày {date_str}"})

    nvs = _pick_nvs(db, pool["NV"], requests, year, date_str, nv_count, sp_warn, nv_role)

    shift = _build_shift(date_str, shift_type, leader, sp, sp_warn, nvs)
    return [shift], warnings


def _generate_cutoff(db: Session, date_str: str, year: int,
                     nv_count: int) -> Tuple[List[dict], List[dict]]:
    """Ca cut-off — vòng xoay LD_cutoff, NV_cutoff."""
    sd = get_special_day(db, date_str)
    if not sd or not sd.is_confirmed:
        return [], [{"date": date_str, "type": "cutoff_unconfirmed",
                     "msg": f"Ngày cut-off {date_str} chưa được xác nhận — bỏ qua"}]

    pool = get_available_pool(db, date_str)
    requests = get_requests_for_date(db, date_str, year)
    warnings = []

    sp, sp_warn = _pick_sp(db, pool, requests, year, date_str, "LD_cutoff")

    if sp_warn == "leader_sp":
        leader = sp
        sp = None
        name = leader.full_name if leader else "?"
        warnings.append({"date": date_str, "type": "leader_sp",
                         "msg": f"{name} (LĐ) kiêm SP ngày cutoff {date_str} — ghép 2 NV"})
    else:
        leader = _pick_leader(db, pool["LD"], requests, year, date_str, "LD_cutoff")
        if not leader:
            warnings.append({"date": date_str, "type": "no_leader",
                             "msg": f"Không có Lãnh đạo khả dụng ngày cutoff {date_str}"})
        if sp_warn == "no_sp":
            warnings.append({"date": date_str, "type": "no_sp",
                             "msg": f"Không có SP ngày cutoff {date_str}"})

    nvs = _pick_nvs(db, pool["NV"], requests, year, date_str, nv_count, sp_warn, "NV_cutoff")
    shift = _build_shift(date_str, "cutoff", leader, sp, sp_warn, nvs)
    return [shift], warnings


def _generate_settlement(db: Session, date_str: str, year: int,
                          nv_count: int) -> Tuple[List[dict], List[dict]]:
    """
    Ca quyết toán: 2 cụm cùng ngày.
    - settlement_main: LĐ + SP + NV chính (vòng xoay bình thường)
    - settlement_sub: ~1/2 NV còn lại, không LĐ, không SP (không ghi rotation)
    """
    sd = get_special_day(db, date_str)
    if not sd or not sd.is_confirmed:
        return [], [{"date": date_str, "type": "settlement_unconfirmed",
                     "msg": f"Ngày quyết toán {date_str} chưa được xác nhận — bỏ qua"}]

    pool = get_available_pool(db, date_str)
    requests = get_requests_for_date(db, date_str, year)
    warnings = []

    # ─── CA CHÍNH ────────────────────────────────────────────
    sp, sp_warn = _pick_sp(db, pool, requests, year, date_str, "LD")

    if sp_warn == "leader_sp":
        leader = sp
        sp = None
        name = leader.full_name if leader else "?"
        warnings.append({"date": date_str, "type": "leader_sp",
                         "msg": f"{name} kiêm SP ngày quyết toán {date_str} — ghép 2 NV"})
    else:
        leader = _pick_leader(db, pool["LD"], requests, year, date_str, "LD")
        if sp_warn == "no_sp":
            warnings.append({"date": date_str, "type": "no_sp",
                             "msg": f"Không có SP ngày quyết toán {date_str}"})

    nvs_main = _pick_nvs(db, pool["NV"], requests, year, date_str,
                          nv_count, sp_warn, "NV")
    shift_main = _build_shift(date_str, "settlement_main", leader, sp, sp_warn, nvs_main)

    # ─── CA PHỤ ──────────────────────────────────────────────
    used_ids = {p.id for p in nvs_main}
    remaining_nv = [p for p in pool["NV"] if p.id not in used_ids]
    sub_count = max(1, len(remaining_nv) // 2)
    nvs_sub = remaining_nv[:sub_count]   # không cập nhật rotation

    shift_sub = _build_shift(date_str, "settlement_sub", None, None, None, nvs_sub)

    return [shift_main, shift_sub], warnings


# ══════════════════════════════════════════════════════════════
# ENTRY POINT: generate_schedule
# ══════════════════════════════════════════════════════════════

def generate_schedule(db: Session, month: int, year: int,
                      overwrite_draft: bool = False) -> dict:
    """
    Sinh lịch trực theo tuần cho tháng chỉ định.
    Mở rộng: bao phủ tuần đầy đủ chứa ngày 1 và ngày cuối tháng
    (nối cuối tháng - đầu tháng để phân lịch theo đơn vị tuần).
    Bỏ qua: T7/CN, ngày lễ, ngày đã confirmed.
    Trả: {'created': N, 'skipped': M, 'warnings': [...]}
    """
    config = get_shift_config(db, year)
    nv_count = config.nv_count if config else DEFAULT_NV_COUNT

    holiday_dates = get_holiday_dates(db, year)

    # Mở rộng sang tuần đầy đủ: từ Thứ 2 tuần đầu đến Thứ 6 tuần cuối
    first_day = _date(year, month, 1)
    start_monday = first_day - timedelta(days=first_day.weekday())
    last_day = _date(year, month, _cal.monthrange(year, month)[1])
    end_friday = last_day + timedelta(days=(4 - last_day.weekday()) % 7)

    # Bổ sung holiday của năm liền kề nếu end_friday sang năm mới
    if end_friday.year != year:
        holiday_dates = holiday_dates | get_holiday_dates(db, end_friday.year)

    working_days = []
    cur = start_monday
    while cur <= end_friday:
        ds = cur.isoformat()
        if cur.weekday() < 5 and ds not in holiday_dates:
            working_days.append(ds)
        cur += timedelta(days=1)

    all_warnings: List[dict] = []
    created = 0
    skipped = 0

    for date_str in working_days:
        # Kiểm tra ca đã có
        existing = db.query(DutyShift).filter(
            DutyShift.shift_date == date_str
        ).all()

        if existing:
            # Bỏ qua nếu có bất kỳ ca đã confirmed
            if any(s.status == "confirmed" for s in existing):
                skipped += len(existing)
                continue
            # Bỏ qua draft nếu không cho phép ghi đè
            if not overwrite_draft:
                skipped += len(existing)
                continue
            # Xóa draft cũ trước khi tạo mới
            for s in existing:
                db.delete(s)
            db.flush()

        # Xác định loại ca
        sd = get_special_day(db, date_str)
        day_type = sd.day_type if sd else None

        if day_type == "settlement":
            shifts, warns = _generate_settlement(db, date_str, year, nv_count)
        elif day_type == "cutoff":
            shifts, warns = _generate_cutoff(db, date_str, year, nv_count)
        elif is_friday(date_str):
            shifts, warns = _generate_normal_or_friday(
                db, date_str, year, nv_count,
                ld_role="LD_friday", nv_role="NV_friday", shift_type="friday"
            )
        else:
            shifts, warns = _generate_normal_or_friday(
                db, date_str, year, nv_count,
                ld_role="LD", nv_role="NV", shift_type="normal"
            )

        # Lưu các ca vừa sinh
        for shift_data in shifts:
            _save_shift(db, shift_data)
            created += 1

        all_warnings.extend(warns)

    db.commit()
    return {"created": created, "skipped": skipped, "warnings": all_warnings,
            "month": month, "year": year}


def generate_schedule_for_week(db: Session, week_start_str: str,
                               overwrite_draft: bool = False,
                               overwrite_confirmed: bool = False) -> dict:
    """
    Sinh lịch trực cho 1 tuần (5 ngày Mon-Fri, bỏ ngày lễ).
    Trả: {'created': N, 'skipped': M, 'warnings': [...], 'week_start': week_start_str}
    """
    year = int(week_start_str[:4])
    config = get_shift_config(db, year)
    nv_count = config.nv_count if config else DEFAULT_NV_COUNT

    holiday_dates = get_holiday_dates(db, year)
    week_dates = get_week_dates(week_start_str)
    working_days = [d for d in week_dates if d not in holiday_dates]

    all_warnings: List[dict] = []
    created = 0
    skipped = 0

    for date_str in working_days:
        existing = db.query(DutyShift).filter(DutyShift.shift_date == date_str).all()

        # R3: Tách confirmed / draft để xử lý độc lập
        confirmed_shifts = [s for s in existing if s.status == "confirmed"]
        draft_shifts = [s for s in existing if s.status == "draft"]
        confirmed_types = {s.shift_type for s in confirmed_shifts}

        if existing:
            if confirmed_shifts and not overwrite_confirmed:
                if draft_shifts and overwrite_draft:
                    # Xóa chỉ draft — giữ nguyên confirmed
                    for s in draft_shifts:
                        db.delete(s)
                    db.flush()
                    # Tiếp tục generate nhưng skip các shift_type đã confirmed
                elif draft_shifts:
                    skipped += len(existing)
                    continue
                else:
                    # Chỉ có confirmed, không có draft
                    skipped += len(confirmed_shifts)
                    continue
            elif not overwrite_draft:
                skipped += len(existing)
                continue
            else:
                # overwrite_draft=True và không có confirmed bị bảo vệ
                for s in existing:
                    if not overwrite_confirmed and s.status == "confirmed":
                        continue
                    db.delete(s)
                if overwrite_confirmed:
                    confirmed_types = set()
                db.flush()

        sd = get_special_day(db, date_str)
        day_type = sd.day_type if sd else None

        if day_type == "settlement":
            shifts, warns = _generate_settlement(db, date_str, year, nv_count)
        elif day_type == "cutoff":
            shifts, warns = _generate_cutoff(db, date_str, year, nv_count)
        elif is_friday(date_str):
            shifts, warns = _generate_normal_or_friday(
                db, date_str, year, nv_count,
                ld_role="LD_friday", nv_role="NV_friday", shift_type="friday"
            )
        else:
            shifts, warns = _generate_normal_or_friday(
                db, date_str, year, nv_count,
                ld_role="LD", nv_role="NV", shift_type="normal"
            )

        for shift_data in shifts:
            # R3: Không ghi đè shift_type đã confirmed
            if shift_data["shift_type"] in confirmed_types:
                skipped += 1
            else:
                _save_shift(db, shift_data)
                created += 1

        all_warnings.extend(warns)

    db.commit()
    return {"created": created, "skipped": skipped, "warnings": all_warnings,
            "week_start": week_start_str}


def _save_shift(db: Session, data: dict) -> DutyShift:
    """Lưu 1 ca vào DB, kèm bảng duty_shift_nv."""
    shift = DutyShift(
        shift_date=data["shift_date"],
        shift_type=data["shift_type"],
        leader_id=data["leader_id"],
        sp_id=data["sp_id"],
        sp_warning=data["sp_warning"],
        nv_ids=data["nv_ids"],
        nv_count=data["nv_count"],
        is_auto=data["is_auto"],
        status=data["status"],
    )
    db.add(shift)
    db.flush()   # để có shift.id

    # Ghi bảng phụ duty_shift_nv
    nv_id_list = json.loads(data["nv_ids"])
    for idx, nv_id in enumerate(nv_id_list):
        db.add(DutyShiftNV(shift_id=shift.id, staff_id=nv_id, slot_index=idx))

    # Flush DutyShiftNV để get_week_assignees() thấy NV của ngày này
    # khi generate ngày tiếp theo (autoflush=False trong SessionLocal)
    db.flush()

    return shift


# ══════════════════════════════════════════════════════════════
# ROTATION INIT
# ══════════════════════════════════════════════════════════════

ALL_ROTATION_ROLES = ["LD", "SP", "NV", "LD_friday", "NV_friday", "LD_cutoff", "NV_cutoff"]

ROLE_MAP = {
    "LD": ["LD", "LD_friday", "LD_cutoff"],
    "SP": ["SP"],
    "NV": ["NV", "NV_friday", "NV_cutoff"],
}


def init_rotation_for_year(db: Session, year: int) -> None:
    """
    Tạo rotation_state rows cho tất cả staff × role nếu chưa có.
    Gọi khi startup hoặc khi sang năm mới.
    """
    from backend.models.duty_models import Staff
    all_staff = db.query(Staff).all()

    for person in all_staff:
        for rotation_role in ROLE_MAP.get(person.role, []):
            existing = db.query(RotationState).filter_by(
                year=year, role=rotation_role, staff_id=person.id
            ).first()
            if not existing:
                db.add(RotationState(
                    year=year, role=rotation_role, staff_id=person.id,
                    shift_count=0, last_used=None, position=person.display_order * 10 + person.id,
                ))
    db.commit()


def reset_rotation(db: Session, year: int) -> None:
    """Reset vòng xoay: xóa tất cả rotation_state của năm, rồi init lại."""
    db.query(RotationState).filter_by(year=year).delete()
    db.commit()
    init_rotation_for_year(db, year)
