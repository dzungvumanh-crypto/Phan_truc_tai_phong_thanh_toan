"""Router: /api/v1/constraints"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.duty_schemas import (
    AbsenceCreate, AbsenceRangeCreate, AbsenceOut,
    RequestCreate, RequestOut, RequestValidateResult,
    SpecialDayCreate, SpecialDayOut, ComputeCutoffRequest,
    ShiftConfigOut, ShiftConfigUpsert, MessageOut,
)
from backend.services import constraint_service
from backend.services.calendar_utils import compute_cutoff_dates
from backend.services.staff_service import get_staff_by_id
from backend.config import CURRENT_YEAR

router = APIRouter(prefix="/constraints", tags=["Constraints"])


# ══════════════════════════════════════════════════════════════
# ABSENCES
# ══════════════════════════════════════════════════════════════

@router.get("/absences", response_model=List[AbsenceOut])
def list_absences(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    rows = constraint_service.list_absences(db, month=month, year=year)
    result = []
    for r in rows:
        s = get_staff_by_id(db, r.staff_id)
        result.append(AbsenceOut(
            id=r.id, staff_id=r.staff_id,
            staff_name=s.full_name if s else None,
            absence_date=r.absence_date,
            created_at=r.created_at or "",
        ))
    return result


@router.post("/absences/range", response_model=MessageOut)
def create_absence_range(body: AbsenceRangeCreate, db: Session = Depends(get_db)):
    result = constraint_service.create_absence_range(
        db, body.staff_id, body.from_date, body.to_date
    )
    return MessageOut(
        message=f"Da them {result['created']} ngay vang (bo qua {result['skipped']} da co)"
    )


@router.post("/absences", response_model=AbsenceOut)
def create_absence(body: AbsenceCreate, db: Session = Depends(get_db)):
    obj = constraint_service.create_absence(db, body.staff_id, body.absence_date)
    s = get_staff_by_id(db, obj.staff_id)
    return AbsenceOut(
        id=obj.id, staff_id=obj.staff_id,
        staff_name=s.full_name if s else None,
        absence_date=obj.absence_date,
        created_at=obj.created_at or "",
    )


@router.delete("/absences/range", response_model=MessageOut)
def delete_absence_range(
    staff_id: int = Query(...),
    from_date: str = Query(...),
    to_date: str = Query(...),
    db: Session = Depends(get_db),
):
    result = constraint_service.delete_absence_range(db, staff_id, from_date, to_date)
    return MessageOut(message=f"Đã xóa {result['deleted']} khai báo vắng")


@router.delete("/absences/{absence_id}", response_model=MessageOut)
def delete_absence(absence_id: int, db: Session = Depends(get_db)):
    ok = constraint_service.delete_absence(db, absence_id)
    if not ok:
        raise HTTPException(404, "Không tìm thấy khai báo vắng")
    return MessageOut(message="Đã xóa khai báo vắng")


# ══════════════════════════════════════════════════════════════
# DUTY REQUESTS
# ══════════════════════════════════════════════════════════════

@router.get("/requests", response_model=List[RequestOut])
def list_requests(
    year: Optional[int] = CURRENT_YEAR,
    staff_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    rows = constraint_service.list_requests(db, year=year, staff_id=staff_id)
    result = []
    for r in rows:
        s = get_staff_by_id(db, r.staff_id)
        result.append(RequestOut(
            id=r.id, staff_id=r.staff_id,
            staff_name=s.full_name if s else None,
            request_type=r.request_type,
            specific_date=r.specific_date,
            day_of_week=r.day_of_week,
            year=r.year,
            is_active=bool(r.is_active),
        ))
    return result


@router.get("/requests/validate", response_model=RequestValidateResult)
def validate_request(
    staff_id: int,
    date: str = Query(..., alias="date"),
    year: int = CURRENT_YEAR,
    db: Session = Depends(get_db),
):
    allowed, msg, current, max_slots = constraint_service.validate_nv_request(
        db, staff_id, date, year
    )
    return RequestValidateResult(
        allowed=allowed, message=msg,
        current_count=current, max_slots=max_slots,
    )


@router.post("/requests", response_model=RequestOut)
def create_request(body: RequestCreate, db: Session = Depends(get_db)):
    staff = get_staff_by_id(db, body.staff_id)
    if not staff:
        raise HTTPException(404, "Không tìm thấy nhân sự")

    # N2+V2: Validate absence + slot limit cho mọi role (LD/SP/NV)
    if body.request_type == "once" and body.specific_date:
        allowed, msg, _, _ = constraint_service.validate_nv_request(
            db, body.staff_id, body.specific_date, body.year
        )
        if not allowed:
            raise HTTPException(400, msg)

    try:
        obj = constraint_service.create_request(
            db, body.staff_id, body.request_type, body.year,
            specific_date=body.specific_date, day_of_week=body.day_of_week,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return RequestOut(
        id=obj.id, staff_id=obj.staff_id,
        staff_name=staff.full_name,
        request_type=obj.request_type,
        specific_date=obj.specific_date,
        day_of_week=obj.day_of_week,
        year=obj.year,
        is_active=bool(obj.is_active),
    )


@router.delete("/requests/{request_id}", response_model=MessageOut)
def delete_request(request_id: int, db: Session = Depends(get_db)):
    ok = constraint_service.delete_request(db, request_id)
    if not ok:
        raise HTTPException(404, "Không tìm thấy đăng ký xin trực")
    return MessageOut(message="Đã xóa đăng ký xin trực")


# ══════════════════════════════════════════════════════════════
# SPECIAL DAYS
# ══════════════════════════════════════════════════════════════

@router.get("/special-days", response_model=List[SpecialDayOut])
def list_special_days(
    month: Optional[int] = None,
    year: Optional[int] = None,
    day_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    rows = constraint_service.list_special_days(db, month=month, year=year, day_type=day_type)
    return [SpecialDayOut(
        id=r.id, date=r.date, day_type=r.day_type,
        label=r.label, is_confirmed=bool(r.is_confirmed),
    ) for r in rows]


@router.post("/special-days", response_model=SpecialDayOut)
def create_special_day(body: SpecialDayCreate, db: Session = Depends(get_db)):
    obj = constraint_service.create_special_day(
        db, body.date, body.day_type, label=body.label
    )
    return SpecialDayOut(
        id=obj.id, date=obj.date, day_type=obj.day_type,
        label=obj.label, is_confirmed=bool(obj.is_confirmed),
    )


@router.post("/special-days/compute-cutoff", response_model=List[SpecialDayOut])
def compute_cutoff(body: ComputeCutoffRequest, db: Session = Depends(get_db)):
    """Tính 2 ngày cut-off cuối tháng và insert vào DB (is_confirmed=0)."""
    holiday_dates = constraint_service.get_holiday_dates(db, body.year)
    dates = compute_cutoff_dates(body.month, body.year, holiday_dates)
    result = []
    for ds in dates:
        obj = constraint_service.create_special_day(
            db, ds, "cutoff",
            label=f"Cut-off {body.month:02d}/{body.year}",
            is_confirmed=0,
        )
        result.append(SpecialDayOut(
            id=obj.id, date=obj.date, day_type=obj.day_type,
            label=obj.label, is_confirmed=bool(obj.is_confirmed),
        ))
    return result


@router.put("/special-days/{special_day_id}/confirm", response_model=SpecialDayOut)
def confirm_special_day(special_day_id: int, db: Session = Depends(get_db)):
    obj = constraint_service.confirm_special_day(db, special_day_id)
    if not obj:
        raise HTTPException(404, "Không tìm thấy ngày đặc biệt")
    return SpecialDayOut(
        id=obj.id, date=obj.date, day_type=obj.day_type,
        label=obj.label, is_confirmed=bool(obj.is_confirmed),
    )


@router.delete("/special-days/{special_day_id}", response_model=MessageOut)
def delete_special_day(special_day_id: int, db: Session = Depends(get_db)):
    result = constraint_service.delete_special_day(db, special_day_id)
    if not result["deleted"]:
        raise HTTPException(404, "Không tìm thấy ngày đặc biệt")
    msg = "Đã xóa ngày đặc biệt"
    if result.get("warning"):
        msg += f". ⚠️ {result['warning']}"
    return MessageOut(message=msg)


# ══════════════════════════════════════════════════════════════
# SHIFT CONFIG
# ══════════════════════════════════════════════════════════════

@router.get("/shift-config/{year}", response_model=ShiftConfigOut)
def get_shift_config(year: int, db: Session = Depends(get_db)):
    obj = constraint_service.get_shift_config(db, year)
    if not obj:
        raise HTTPException(404, f"Chưa có cấu hình ca năm {year}")
    return ShiftConfigOut(year=obj.year, nv_count=obj.nv_count,
                          signer_name=obj.signer_name)


@router.put("/shift-config/{year}", response_model=ShiftConfigOut)
def upsert_shift_config(year: int, body: ShiftConfigUpsert,
                         db: Session = Depends(get_db)):
    obj = constraint_service.upsert_shift_config(
        db, year, body.nv_count, signer_name=body.signer_name
    )
    return ShiftConfigOut(year=obj.year, nv_count=obj.nv_count,
                          signer_name=obj.signer_name)
