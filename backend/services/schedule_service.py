"""
Schedule service: CRUD ca trực + startup initialization.
"""
import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models.duty_models import (
    DutyShift, DutyShiftNV, RotationState, Staff, ShiftConfig, SpecialDay
)
from backend.services.calendar_utils import get_vn_holidays
from backend.services.constraint_service import upsert_shift_config
from backend.services.scheduler_engine import init_rotation_for_year
from backend.config import DEFAULT_NV_COUNT, CURRENT_YEAR


# ══════════════════════════════════════════════════════════════
# SEED DATA — 25 nhân sự cố định
# ══════════════════════════════════════════════════════════════

_STAFF_SEED = [
    # (full_name, role, is_on_project, display_order)
    # ── Lãnh đạo (LĐ) ──────────────────────────────────────
    ("Đào Tiến Thành",       "LD", 0, 10),
    ("Tô Thị Lan Anh",       "LD", 0, 11),
    ("Trần Thị Mỹ Linh",    "LD", 0, 12),   # SP backup
    ("Trần Thị Bích Phương", "LD", 0, 13),   # SP backup
    ("Vũ Văn Ngân",          "LD", 1, 14),   # đi dự án
    ("Nguyễn Thị Hiền",      "LD", 1, 15),   # đi dự án
    ("Lê Thị Thu Hằng",      "LD", 1, 16),   # đi dự án
    # ── Song Phương (SP) ────────────────────────────────────
    ("Đoàn Thị Huyền Trang", "SP", 0, 20),
    ("Từ Diệu Hương",         "SP", 0, 21),
    ("Đặng Thị Hương Ly",    "SP", 0, 22),
    ("Tạ Thị Thúy Hà",       "SP", 0, 23),
    ("Nguyễn Thị Ngọc Hà",  "SP", 1, 24),   # đi dự án
    # ── Nhân viên (NV) ──────────────────────────────────────
    ("Nguyễn Thị Phương",    "NV", 0, 30),
    ("Tô Phương Thảo",        "NV", 0, 31),
    ("Bùi Quốc Khánh",        "NV", 0, 32),
    ("Vũ Mạnh Dũng",          "NV", 0, 33),
    ("Nguyễn Minh Việt",      "NV", 0, 34),
    ("Nguyễn Thu Phương",     "NV", 0, 35),
    ("Nguyễn Thị Hà Dương",  "NV", 0, 36),
    ("Hoàng Thị Lan Anh",    "NV", 0, 37),
    ("Bùi Thị Thu Thủy",     "NV", 1, 38),   # đi dự án
    ("Phan Duy Đạt",          "NV", 1, 39),   # đi dự án
    ("Hà Phương Thu",          "NV", 1, 40),   # đi dự án
    ("Nguyễn Thị Ánh Nguyệt","NV", 1, 41),   # đi dự án
    ("Đặng Thị Thương Nhi",  "NV", 1, 42),   # đi dự án
]


def seed_staff(db: Session) -> None:
    """Seed 25 nhân sự nếu bảng staff chưa có dữ liệu."""
    count = db.query(Staff).count()
    if count > 0:
        return
    for name, role, on_project, order in _STAFF_SEED:
        db.add(Staff(
            full_name=name, role=role,
            is_on_project=on_project, display_order=order,
        ))
    db.commit()


def seed_holidays(db: Session, year: int) -> None:
    """Seed ngày nghỉ lễ VN năm `year` vào bảng special_days."""
    holidays = get_vn_holidays(year)
    for h in holidays:
        existing = db.query(SpecialDay).filter_by(date=h["date"]).first()
        if not existing:
            db.add(SpecialDay(
                date=h["date"],
                day_type="holiday",
                label=h["label"],
                is_confirmed=1,
            ))
    db.commit()


def startup_init(db: Session) -> None:
    """
    Khởi tạo dữ liệu khi backend start.
    1. Seed nhân sự
    2. Seed shift_config năm hiện tại
    3. Seed ngày nghỉ lễ
    4. Init rotation state
    5. Seed is_sp_backup cho LD backup (T3)
    """
    from backend.config import SP_BACKUP_LEADERS
    year = CURRENT_YEAR
    seed_staff(db)
    upsert_shift_config(db, year, DEFAULT_NV_COUNT)
    seed_holidays(db, year)
    init_rotation_for_year(db, year)
    # T3: Đảm bảo LD backup có is_sp_backup=1 (idempotent)
    for name in SP_BACKUP_LEADERS:
        s = db.query(Staff).filter_by(full_name=name).first()
        if s and not s.is_sp_backup:
            s.is_sp_backup = 1
    db.commit()


# ══════════════════════════════════════════════════════════════
# CRUD CA TRỰC
# ══════════════════════════════════════════════════════════════

def _enrich_shift(db: Session, shift: DutyShift) -> dict:
    """Thêm thông tin leader, sp, nvs vào dict của ca."""
    def staff_dict(s: Optional[Staff]) -> Optional[dict]:
        if not s:
            return None
        return {"id": s.id, "full_name": s.full_name,
                "role": s.role, "is_on_project": bool(s.is_on_project),
                "display_order": s.display_order}

    nv_id_list = json.loads(shift.nv_ids or "[]")
    nvs = []
    if nv_id_list:
        nv_staff = db.query(Staff).filter(Staff.id.in_(nv_id_list)).all()
        nv_map = {s.id: s for s in nv_staff}
        nvs = [staff_dict(nv_map[nv_id]) for nv_id in nv_id_list if nv_id in nv_map]

    return {
        "id": shift.id,
        "shift_date": shift.shift_date,
        "shift_type": shift.shift_type,
        "leader": staff_dict(shift.leader),
        "sp": staff_dict(shift.sp),
        "sp_warning": shift.sp_warning,
        "nvs": nvs,
        "nv_count": shift.nv_count,
        "is_auto": bool(shift.is_auto),
        "status": shift.status,
        "created_at": shift.created_at or "",
    }


def get_shifts_for_month(db: Session, month: int, year: int,
                          status: Optional[str] = None) -> List[dict]:
    prefix = f"{year}-{month:02d}"
    q = db.query(DutyShift).filter(DutyShift.shift_date.like(f"{prefix}%"))
    if status:
        q = q.filter(DutyShift.status == status)
    shifts = q.order_by(DutyShift.shift_date, DutyShift.shift_type).all()
    return [_enrich_shift(db, s) for s in shifts]


def get_shifts_for_week(db: Session, start_date: str) -> List[dict]:
    """Lịch tuần: từ start_date đến start_date+4 ngày."""
    from backend.services.calendar_utils import get_week_dates
    dates = get_week_dates(start_date)
    q = db.query(DutyShift).filter(DutyShift.shift_date.in_(dates))
    shifts = q.order_by(DutyShift.shift_date, DutyShift.shift_type).all()
    return [_enrich_shift(db, s) for s in shifts]


def get_shifts_for_date(db: Session, date_str: str) -> List[dict]:
    shifts = db.query(DutyShift).filter_by(shift_date=date_str).all()
    return [_enrich_shift(db, s) for s in shifts]


def delete_shifts_for_week(db: Session, week_start_str: str) -> int:
    from backend.services.calendar_utils import get_week_dates
    dates = get_week_dates(week_start_str)
    shifts = db.query(DutyShift).filter(DutyShift.shift_date.in_(dates)).all()
    count = len(shifts)
    for s in shifts:
        db.delete(s)
    db.commit()
    return count


def update_shift(db: Session, shift_id: int, leader_id: Optional[int],
                 sp_id: Optional[int], nv_ids: List[int],
                 sp_warning: Optional[str] = None,
                 clear_sp: bool = False) -> Optional[dict]:
    shift = db.query(DutyShift).filter_by(id=shift_id).first()
    if not shift:
        return None

    if leader_id is not None:
        shift.leader_id = leader_id
    # V1: clear_sp=True xóa SP về NULL; sp_id=None riêng không đủ để phân biệt "không truyền" vs "xóa"
    if clear_sp:
        shift.sp_id = None
    elif sp_id is not None:
        shift.sp_id = sp_id
    if sp_warning is not None:
        shift.sp_warning = sp_warning
    if nv_ids is not None:
        shift.nv_ids = json.dumps(nv_ids)
        shift.nv_count = len(nv_ids)
        # Cập nhật bảng phụ
        db.query(DutyShiftNV).filter_by(shift_id=shift_id).delete()
        for idx, nv_id in enumerate(nv_ids):
            db.add(DutyShiftNV(shift_id=shift_id, staff_id=nv_id, slot_index=idx))

    shift.is_auto = 0   # đánh dấu đã sửa tay
    db.commit()
    db.refresh(shift)
    return _enrich_shift(db, shift)


def confirm_shift(db: Session, shift_id: int) -> Optional[dict]:
    shift = db.query(DutyShift).filter_by(id=shift_id).first()
    if not shift:
        return None
    shift.status = "confirmed"
    db.commit()
    db.refresh(shift)
    return _enrich_shift(db, shift)


def unconfirm_shift(db: Session, shift_id: int) -> Optional[dict]:
    """B5: Hủy xác nhận ca — trả về trạng thái draft."""
    shift = db.query(DutyShift).filter_by(id=shift_id).first()
    if not shift:
        return None
    shift.status = "draft"
    db.commit()
    db.refresh(shift)
    return _enrich_shift(db, shift)


def confirm_shifts_for_week(db: Session, week_start_str: str) -> int:
    """Xác nhận tất cả ca draft trong tuần."""
    from backend.services.calendar_utils import get_week_dates
    dates = get_week_dates(week_start_str)
    count = db.query(DutyShift).filter(
        DutyShift.shift_date.in_(dates),
        DutyShift.status == "draft",
    ).update({"status": "confirmed"}, synchronize_session=False)
    db.commit()
    return count


def confirm_all_shifts(db: Session, month: int, year: int) -> int:
    prefix = f"{year}-{month:02d}"
    count = db.query(DutyShift).filter(
        DutyShift.shift_date.like(f"{prefix}%"),
        DutyShift.status == "draft",
    ).update({"status": "confirmed"})
    db.commit()
    return count


def delete_shift(db: Session, shift_id: int) -> bool:
    shift = db.query(DutyShift).filter_by(id=shift_id).first()
    if not shift:
        return False
    db.delete(shift)
    db.commit()
    return True


# ══════════════════════════════════════════════════════════════
# ROTATION STATE — read only (write ở scheduler_engine)
# ══════════════════════════════════════════════════════════════

def get_rotation_state(db: Session, year: int,
                        role: Optional[str] = None) -> List[dict]:
    q = db.query(RotationState, Staff).join(Staff, RotationState.staff_id == Staff.id)
    q = q.filter(RotationState.year == year)
    if role:
        q = q.filter(RotationState.role == role)
    rows = q.order_by(RotationState.role, RotationState.shift_count, Staff.display_order).all()

    return [
        {
            "staff_id": rs.staff_id,
            "staff_name": s.full_name,
            "role": rs.role,
            "year": rs.year,
            "shift_count": rs.shift_count,
            "last_used": rs.last_used,
        }
        for rs, s in rows
    ]


# ══════════════════════════════════════════════════════════════
# STATISTICS
# ══════════════════════════════════════════════════════════════

def get_shift_count_by_person(db: Session, year: int) -> List[dict]:
    """Số ca trực mỗi người, breakdown theo loại ca."""
    all_staff = db.query(Staff).order_by(Staff.role, Staff.display_order).all()
    prefix = f"{year}-%"
    shifts = db.query(DutyShift).filter(
        DutyShift.shift_date.like(prefix),
        DutyShift.status == "confirmed",
    ).all()

    # Xây map: staff_id → {type: count}
    counts: dict = {s.id: {"normal": 0, "friday": 0, "cutoff": 0,
                            "settlement_main": 0, "settlement_sub": 0}
                    for s in all_staff}

    for shift in shifts:
        # Leader
        if shift.leader_id and shift.leader_id in counts:
            counts[shift.leader_id][shift.shift_type] = \
                counts[shift.leader_id].get(shift.shift_type, 0) + 1
        # SP
        if shift.sp_id and shift.sp_id in counts:
            counts[shift.sp_id][shift.shift_type] = \
                counts[shift.sp_id].get(shift.shift_type, 0) + 1
        # NV
        nv_ids = json.loads(shift.nv_ids or "[]")
        for nv_id in nv_ids:
            if nv_id in counts:
                counts[nv_id][shift.shift_type] = \
                    counts[nv_id].get(shift.shift_type, 0) + 1

    result = []
    for s in all_staff:
        c = counts[s.id]
        total = sum(c.values())
        result.append({
            "staff_id": s.id,
            "full_name": s.full_name,
            "role": s.role,
            **c,
            "total": total,
        })
    return result


def get_monthly_summary(db: Session, month: int, year: int) -> dict:
    prefix = f"{year}-{month:02d}"
    # FIX-1: Chỉ đếm ca confirmed để nhất quán với get_shift_count_by_person
    shifts = db.query(DutyShift).filter(
        DutyShift.shift_date.like(f"{prefix}%"),
        DutyShift.status == "confirmed",
    ).all()

    by_type: dict = {}
    sp_warnings = 0
    for s in shifts:
        by_type[s.shift_type] = by_type.get(s.shift_type, 0) + 1
        if s.sp_warning:
            sp_warnings += 1

    return {
        "month": month,
        "year": year,
        "total_shifts": len(shifts),
        "sp_warnings": sp_warnings,
        "by_type": by_type,
    }
