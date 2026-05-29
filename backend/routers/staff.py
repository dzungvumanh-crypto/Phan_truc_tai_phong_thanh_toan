"""Router: /api/v1/staff"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.duty_schemas import StaffOut, StaffCreate, StaffUpdate, MessageOut
from backend.services import staff_service

router = APIRouter(prefix="/staff", tags=["Staff"])


@router.get("/", response_model=List[StaffOut])
def list_staff(
    role: Optional[str] = None,
    is_on_project: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    return staff_service.get_all_staff(db, role=role, is_on_project=is_on_project)


@router.get("/{staff_id}", response_model=StaffOut)
def get_staff(staff_id: int, db: Session = Depends(get_db)):
    s = staff_service.get_staff_by_id(db, staff_id)
    if not s:
        raise HTTPException(404, "Không tìm thấy nhân sự")
    return s


@router.post("/", response_model=StaffOut, status_code=201)
def create_staff(body: StaffCreate, db: Session = Depends(get_db)):
    return staff_service.create_staff(
        db, body.full_name, body.role, body.is_on_project, body.display_order
    )


@router.put("/{staff_id}/project-toggle", response_model=StaffOut)
def toggle_project(staff_id: int, db: Session = Depends(get_db)):
    s = staff_service.toggle_project_status(db, staff_id)
    if not s:
        raise HTTPException(404, "Không tìm thấy nhân sự")
    return s


@router.put("/{staff_id}", response_model=StaffOut)
def update_staff(staff_id: int, body: StaffUpdate, db: Session = Depends(get_db)):
    s = staff_service.update_staff(
        db, staff_id,
        full_name=body.full_name,
        role=body.role,
        is_on_project=body.is_on_project,
        display_order=body.display_order,
    )
    if not s:
        raise HTTPException(404, "Không tìm thấy nhân sự")
    return s


@router.delete("/{staff_id}", response_model=MessageOut)
def delete_staff(staff_id: int, db: Session = Depends(get_db)):
    ok = staff_service.delete_staff(db, staff_id)
    if not ok:
        raise HTTPException(404, "Không tìm thấy nhân sự")
    return MessageOut(message="Da xoa nhan su")
