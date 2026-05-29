"""Router: /api/v1/stats"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.duty_schemas import PersonShiftCount, MonthlySummary
from backend.services import schedule_service
from backend.config import CURRENT_YEAR

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/shift-count", response_model=List[dict])
def shift_count_by_person(year: int = CURRENT_YEAR, db: Session = Depends(get_db)):
    """Số ca trực từng người, breakdown theo loại ca (chỉ tính confirmed)."""
    return schedule_service.get_shift_count_by_person(db, year)


@router.get("/monthly-summary", response_model=dict)
def monthly_summary(
    month: int = Query(..., ge=1, le=12),
    year: int = CURRENT_YEAR,
    db: Session = Depends(get_db),
):
    return schedule_service.get_monthly_summary(db, month, year)


@router.get("/rotation-state", response_model=List[dict])
def rotation_state(
    year: int = CURRENT_YEAR,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return schedule_service.get_rotation_state(db, year, role=role)
