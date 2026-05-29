"""Router: /api/v1/export"""
from datetime import datetime, timedelta, date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services import schedule_service, export_service

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/schedule/week")
def export_week_schedule(
    week_start: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
):
    """
    Xuất lịch trực 1 tuần ra file Excel (.xlsx).
    week_start: ngày thứ 2 đầu tuần, format YYYY-MM-DD
    """
    start: date = datetime.strptime(week_start, "%Y-%m-%d").date()
    end: date = start + timedelta(days=4)   # thứ 6

    shifts = schedule_service.get_shifts_for_week(db, week_start)
    excel_bytes = export_service.build_week_excel(shifts, start, end)

    filename = f"lich_truc_{start:%d%m%Y}_{end:%d%m%Y}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
