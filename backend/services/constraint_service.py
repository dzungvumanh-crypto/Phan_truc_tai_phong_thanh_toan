"""
Constraint service: vắng mặt, đăng ký xin trực, special days, shift config.
"""
from datetime import datetime, date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models.duty_models import Absence, DutyRequest, SpecialDay, ShiftConfig
from backend.config import DEFAULT_NV_COUNT


# ══════════════════════════════════════════════════════════════
# ABSENCES
# ══════════════════════════════════════════════════════════════

def list_absences(db: Session, month: Optional[int] = None,
                  year: Optional[int] = None) -> List[Absence]:
    q = db.query(Absence)
    if month and year:
        prefix = f"{year}-{month:02d}"
        q = q.filter(Absence.absence_date.like(f"{prefix}%"))
    elif year:
        q = q.filter(Absence.absence_date.like(f"{year}%"))
    return q.order_by(Absence.absence_date).all()


def create_absence(db: Session, staff_id: int, absence_date: str) -> Absence:
    # Idempotent: nếu đã có thì trả về luôn
    existing = db.query(Absence).filter_by(
        staff_id=staff_id, absence_date=absence_date
    ).first()
    if existing:
        return existing
    obj = Absence(staff_id=staff_id, absence_date=absence_date)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def create_absence_range(db: Session, staff_id: int,
                         from_date: str, to_date: str) -> dict:
    """Tạo absence records cho từng ngày trong khoảng from_date..to_date (inclusive)."""
    start = date.fromisoformat(from_date)
    end   = date.fromisoformat(to_date)
    created = 0
    skipped = 0
    d = start
    while d <= end:
        ds = d.isoformat()
        existing = db.query(Absence).filter_by(staff_id=staff_id, absence_date=ds).first()
        if existing:
            skipped += 1
        else:
            db.add(Absence(staff_id=staff_id, absence_date=ds))
            created += 1
        d += timedelta(days=1)
    db.commit()
    return {"created": created, "skipped": skipped}


def delete_absence_range(db: Session, staff_id: int,
                         from_date: str, to_date: str) -> dict:
    """N6: Xóa tất cả absence records trong khoảng from_date..to_date (inclusive)."""
    rows = db.query(Absence).filter(
        Absence.staff_id == staff_id,
        Absence.absence_date >= from_date,
        Absence.absence_date <= to_date,
    ).all()
    count = len(rows)
    for r in rows:
        db.delete(r)
    db.commit()
    return {"deleted": count}


def delete_absence(db: Session, absence_id: int) -> bool:
    obj = db.query(Absence).filter_by(id=absence_id).first()
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ══════════════════════════════════════════════════════════════
# DUTY REQUESTS (đăng ký xin trực)
# ══════════════════════════════════════════════════════════════

def list_requests(db: Session, year: Optional[int] = None,
                  staff_id: Optional[int] = None) -> List[DutyRequest]:
    q = db.query(DutyRequest).filter(DutyRequest.is_active == 1)
    if year:
        q = q.filter(DutyRequest.year == year)
    if staff_id:
        q = q.filter(DutyRequest.staff_id == staff_id)
    return q.order_by(DutyRequest.id).all()


def get_requests_for_date(db: Session, date_str: str, year: int) -> dict:
    """
    Trả {'LD': [staff_id,...], 'SP': [...], 'NV': [...]}
    cho ngày date_str — kết hợp cả 'once' (exact date) và 'weekly' (day_of_week).
    """
    from backend.models.duty_models import Staff
    from datetime import date

    dow = date.fromisoformat(date_str).weekday()  # 0=Mon

    rows = db.query(DutyRequest).filter(
        DutyRequest.is_active == 1,
        DutyRequest.year == year,
    ).all()

    staff_ids: set = set()
    for r in rows:
        if r.request_type == "once" and r.specific_date == date_str:
            staff_ids.add(r.staff_id)
        elif r.request_type == "weekly" and r.day_of_week == dow:
            staff_ids.add(r.staff_id)

    result: dict = {"LD": [], "SP": [], "NV": []}
    if staff_ids:
        people = db.query(Staff).filter(Staff.id.in_(staff_ids)).all()
        for p in people:
            result[p.role].append(p.id)
    return result


def count_nv_requests_for_date(db: Session, date_str: str, year: int) -> int:
    """Đếm số NV đã đăng ký xin trực ngày date_str."""
    from backend.models.duty_models import Staff
    from datetime import date

    dow = date.fromisoformat(date_str).weekday()
    rows = db.query(DutyRequest).filter(
        DutyRequest.is_active == 1,
        DutyRequest.year == year,
    ).all()

    nv_ids: set = set()
    for r in rows:
        if r.request_type == "once" and r.specific_date == date_str:
            nv_ids.add(r.staff_id)
        elif r.request_type == "weekly" and r.day_of_week == dow:
            nv_ids.add(r.staff_id)

    if not nv_ids:
        return 0

    from backend.models.duty_models import Staff
    count = db.query(Staff).filter(
        Staff.id.in_(nv_ids), Staff.role == "NV"
    ).count()
    return count


def validate_nv_request(db: Session, staff_id: int, date_str: str,
                         year: int) -> tuple[bool, str, int, int]:
    """
    Kiểm tra xem có thể đăng ký xin trực ngày date_str không.
    Áp dụng cho mọi role: kiểm tra vắng mặt trước.
    Giới hạn slot chỉ áp dụng cho NV: số đăng ký NV ≤ nv_count.
    Trả (allowed, message, current_count, max_slots).
    """
    # V2: Kiểm tra vắng mặt trước — áp dụng cho mọi role
    from backend.services.staff_service import get_absent_staff_ids
    absent_ids = get_absent_staff_ids(db, date_str)
    if staff_id in absent_ids:
        return False, f"Nhân sự đã khai báo vắng ngày {date_str}", 0, 0

    config = get_shift_config(db, year)
    max_slots = config.nv_count if config else DEFAULT_NV_COUNT

    current = count_nv_requests_for_date(db, date_str, year)
    if current >= max_slots:
        from backend.models.duty_models import Staff
        existing_requesters = []
        from datetime import date
        dow = date.fromisoformat(date_str).weekday()
        rows = db.query(DutyRequest).filter(
            DutyRequest.is_active == 1, DutyRequest.year == year
        ).all()
        for r in rows:
            if (r.request_type == "once" and r.specific_date == date_str) or \
               (r.request_type == "weekly" and r.day_of_week == dow):
                s = db.query(Staff).filter_by(id=r.staff_id, role="NV").first()
                if s:
                    existing_requesters.append(s.full_name)

        names = ", ".join(existing_requesters) if existing_requesters else "..."
        msg = f"Đã có {current} người đăng ký NV: {names}. Đề nghị chọn ngày khác."
        return False, msg, current, max_slots

    return True, "OK", current, max_slots


def create_request(db: Session, staff_id: int, request_type: str,
                   year: int, specific_date: Optional[str] = None,
                   day_of_week: Optional[int] = None) -> DutyRequest:
    # N3: Idempotent — tránh tạo bản ghi trùng khi bấm 2 lần
    existing = db.query(DutyRequest).filter_by(
        staff_id=staff_id,
        request_type=request_type,
        specific_date=specific_date,
        day_of_week=day_of_week,
        year=year,
        is_active=1,
    ).first()
    if existing:
        return existing

    # N7: Từ chối đăng ký T7/CN (ngày không bao giờ có ca)
    if request_type == "once" and specific_date:
        from datetime import date as _date
        d = _date.fromisoformat(specific_date)
        if d.weekday() >= 5:
            raise ValueError(f"Không thể đăng ký cuối tuần ({specific_date})")

    obj = DutyRequest(
        staff_id=staff_id,
        request_type=request_type,
        specific_date=specific_date,
        day_of_week=day_of_week,
        year=year,
        is_active=1,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_request(db: Session, request_id: int) -> bool:
    obj = db.query(DutyRequest).filter_by(id=request_id).first()
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ══════════════════════════════════════════════════════════════
# SPECIAL DAYS
# ══════════════════════════════════════════════════════════════

def list_special_days(db: Session, month: Optional[int] = None,
                      year: Optional[int] = None,
                      day_type: Optional[str] = None) -> List[SpecialDay]:
    q = db.query(SpecialDay)
    if month and year:
        q = q.filter(SpecialDay.date.like(f"{year}-{month:02d}%"))
    elif year:
        q = q.filter(SpecialDay.date.like(f"{year}%"))
    if day_type:
        q = q.filter(SpecialDay.day_type == day_type)
    return q.order_by(SpecialDay.date).all()


def get_holiday_dates(db: Session, year: int) -> set:
    rows = db.query(SpecialDay.date).filter(
        SpecialDay.day_type == "holiday",
        SpecialDay.date.like(f"{year}%"),
    ).all()
    return {r[0] for r in rows}


def get_special_day(db: Session, date_str: str) -> Optional[SpecialDay]:
    return db.query(SpecialDay).filter_by(date=date_str).first()


def get_special_day_type(db: Session, date_str: str) -> Optional[str]:
    sd = get_special_day(db, date_str)
    return sd.day_type if sd else None


def create_special_day(db: Session, date_str: str, day_type: str,
                       label: Optional[str] = None,
                       is_confirmed: int = 0) -> SpecialDay:
    existing = db.query(SpecialDay).filter_by(date=date_str).first()
    if existing:
        existing.day_type = day_type
        existing.label = label or existing.label
        db.commit()
        db.refresh(existing)
        return existing
    obj = SpecialDay(date=date_str, day_type=day_type, label=label,
                     is_confirmed=is_confirmed)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def confirm_special_day(db: Session, special_day_id: int) -> Optional[SpecialDay]:
    obj = db.query(SpecialDay).filter_by(id=special_day_id).first()
    if not obj:
        return None
    obj.is_confirmed = 1
    db.commit()
    db.refresh(obj)
    return obj


def delete_special_day(db: Session, special_day_id: int) -> dict:
    """
    Xóa ngày đặc biệt. Q6=Option C: cho phép xóa tự do.
    Trả {"deleted": bool, "warning": str|None}.
    Warning nếu ngày đó đang có ca đã confirmed.
    """
    obj = db.query(SpecialDay).filter_by(id=special_day_id).first()
    if not obj:
        return {"deleted": False, "warning": None}

    from backend.models.duty_models import DutyShift
    confirmed_count = db.query(DutyShift).filter(
        DutyShift.shift_date == obj.date,
        DutyShift.status == "confirmed",
    ).count()

    warning = None
    if confirmed_count > 0:
        warning = (
            f"Ngày {obj.date} đang có {confirmed_count} ca đã xác nhận. "
            "Ca đó vẫn được giữ nguyên sau khi xóa ngày đặc biệt."
        )

    db.delete(obj)
    db.commit()
    return {"deleted": True, "warning": warning}


def upsert_special_days_bulk(db: Session, days: List[dict]) -> List[SpecialDay]:
    """Insert nhiều special days một lúc (dùng cho seed holidays)."""
    result = []
    for d in days:
        obj = create_special_day(
            db, d["date"], d["day_type"],
            label=d.get("label"), is_confirmed=d.get("is_confirmed", 0)
        )
        result.append(obj)
    return result


# ══════════════════════════════════════════════════════════════
# SHIFT CONFIG
# ══════════════════════════════════════════════════════════════

def get_shift_config(db: Session, year: int) -> Optional[ShiftConfig]:
    return db.query(ShiftConfig).filter_by(year=year).first()


def upsert_shift_config(db: Session, year: int, nv_count: int,
                         signer_name: Optional[str] = None) -> ShiftConfig:
    obj = db.query(ShiftConfig).filter_by(year=year).first()
    if obj:
        obj.nv_count = nv_count
        if signer_name is not None:
            obj.signer_name = signer_name
    else:
        obj = ShiftConfig(year=year, nv_count=nv_count, signer_name=signer_name)
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ══════════════════════════════════════════════════════════════
# WEEK ASSIGNEES
# ══════════════════════════════════════════════════════════════

def get_week_assignees(db: Session, date_str: str) -> set:
    """
    Trả set staff_id đã được phân trực trong tuần hiện tại,
    từ thứ Hai đến ngày trước date_str (không kể ngày hiện tại).
    Dùng để tránh phân cùng người 2 lần trong 1 tuần.
    """
    from backend.models.duty_models import DutyShift, DutyShiftNV

    d = date.fromisoformat(date_str)
    week_start = d - timedelta(days=d.weekday())  # thứ Hai
    if week_start >= d:
        return set()

    # SP-FIX-2: đọc cả draft + confirmed để tránh phân trùng khi generate tuần mới.
    # Khi overwrite_draft=True: draft cũ đã bị xóa trước khi gọi hàm này → an toàn.
    # Khi generate tuần mới: ca draft T2 phải "chặn" T3 khỏi chọn lại cùng người.
    shifts = db.query(DutyShift).filter(
        DutyShift.shift_date >= week_start.isoformat(),
        DutyShift.shift_date < date_str,
        DutyShift.status.in_(["confirmed", "draft"]),
    ).all()

    ids: set = set()
    for s in shifts:
        if s.leader_id:
            ids.add(s.leader_id)
        if s.sp_id:
            ids.add(s.sp_id)
        for nv in db.query(DutyShiftNV).filter_by(shift_id=s.id).all():
            ids.add(nv.staff_id)
    return ids
