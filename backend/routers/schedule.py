"""Router: /api/v1/schedule"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.duty_schemas import (
    ShiftOut, ShiftUpdate, GenerateRequest, GenerateResult,
    GenerateWeekRequest, GenerateWeekResult,
    RotationStateOut, MessageOut,
)
from backend.services import schedule_service
from backend.services.scheduler_engine import generate_schedule, generate_schedule_for_week, reset_rotation
from backend.config import CURRENT_YEAR

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.get("/", response_model=List[dict])
def list_shifts(
    month: int = Query(..., ge=1, le=12),
    year: int = CURRENT_YEAR,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return schedule_service.get_shifts_for_month(db, month, year, status=status)


@router.get("/week", response_model=List[dict])
def get_week_schedule(
    start_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
):
    return schedule_service.get_shifts_for_week(db, start_date)


@router.get("/date/{date_str}", response_model=List[dict])
def get_shifts_for_date(date_str: str, db: Session = Depends(get_db)):
    return schedule_service.get_shifts_for_date(db, date_str)


@router.post("/generate", response_model=GenerateResult)
def generate(body: GenerateRequest, db: Session = Depends(get_db)):
    result = generate_schedule(
        db, body.month, body.year,
        overwrite_draft=body.overwrite_draft
    )
    return GenerateResult(**result)


@router.post("/generate-week", response_model=GenerateWeekResult)
def generate_week(body: GenerateWeekRequest, db: Session = Depends(get_db)):
    result = generate_schedule_for_week(
        db, body.week_start,
        overwrite_draft=body.overwrite_draft,
        overwrite_confirmed=body.overwrite_confirmed,
    )
    return GenerateWeekResult(**result)


@router.post("/confirm-week", response_model=MessageOut)
def confirm_week(
    week_start: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
):
    count = schedule_service.confirm_shifts_for_week(db, week_start)
    return MessageOut(message=f"Da xac nhan {count} ca truc trong tuan")


@router.delete("/week", response_model=MessageOut)
def delete_week(
    week_start: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
):
    count = schedule_service.delete_shifts_for_week(db, week_start)
    return MessageOut(message=f"Đã xóa {count} ca trong tuần {week_start}")


@router.put("/{shift_id}", response_model=dict)
def update_shift(shift_id: int, body: ShiftUpdate, db: Session = Depends(get_db)):
    result = schedule_service.update_shift(
        db, shift_id,
        leader_id=body.leader_id,
        sp_id=body.sp_id,
        nv_ids=body.nv_ids,
        sp_warning=body.sp_warning,
        clear_sp=body.clear_sp,
    )
    if not result:
        raise HTTPException(404, "Không tìm thấy ca trực")
    return result


@router.put("/{shift_id}/confirm", response_model=dict)
def confirm_shift(shift_id: int, db: Session = Depends(get_db)):
    result = schedule_service.confirm_shift(db, shift_id)
    if not result:
        raise HTTPException(404, "Không tìm thấy ca trực")
    return result


@router.put("/{shift_id}/unconfirm", response_model=dict)
def unconfirm_shift(shift_id: int, db: Session = Depends(get_db)):
    """B5: Hủy xác nhận ca — trả về trạng thái draft."""
    result = schedule_service.unconfirm_shift(db, shift_id)
    if not result:
        raise HTTPException(404, "Không tìm thấy ca trực")
    return result


@router.post("/confirm-all", response_model=MessageOut)
def confirm_all(
    month: int = Query(..., ge=1, le=12),
    year: int = CURRENT_YEAR,
    db: Session = Depends(get_db),
):
    count = schedule_service.confirm_all_shifts(db, month, year)
    return MessageOut(message=f"Đã xác nhận {count} ca trực tháng {month}/{year}")


@router.delete("/{shift_id}", response_model=MessageOut)
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    ok = schedule_service.delete_shift(db, shift_id)
    if not ok:
        raise HTTPException(404, "Không tìm thấy ca trực")
    return MessageOut(message="Đã xóa ca trực")


@router.get("/rotation-state", response_model=List[dict])
def get_rotation_state(
    year: int = CURRENT_YEAR,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return schedule_service.get_rotation_state(db, year, role=role)


@router.post("/reset-rotation", response_model=MessageOut)
def reset_rotation_endpoint(year: int = CURRENT_YEAR, db: Session = Depends(get_db)):
    reset_rotation(db, year)
    return MessageOut(message=f"Đã reset vòng xoay năm {year}")
