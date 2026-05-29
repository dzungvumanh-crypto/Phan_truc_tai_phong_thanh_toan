"""
Staff service: quản lý nhân sự, pool khả dụng.
"""
from typing import List, Optional
from sqlalchemy.orm import Session

import json
from backend.models.duty_models import Staff, Absence, DutyShift


def get_all_staff(db: Session, role: Optional[str] = None,
                  is_on_project: Optional[bool] = None) -> List[Staff]:
    q = db.query(Staff)
    if role:
        q = q.filter(Staff.role == role)
    if is_on_project is not None:
        q = q.filter(Staff.is_on_project == (1 if is_on_project else 0))
    return q.order_by(Staff.display_order, Staff.id).all()


def get_staff_by_id(db: Session, staff_id: int) -> Optional[Staff]:
    return db.query(Staff).filter(Staff.id == staff_id).first()


def toggle_project_status(db: Session, staff_id: int) -> Optional[Staff]:
    s = get_staff_by_id(db, staff_id)
    if not s:
        return None
    s.is_on_project = 0 if s.is_on_project else 1
    db.commit()
    db.refresh(s)
    return s


def get_absent_staff_ids(db: Session, date_str: str) -> set:
    """Trả set staff_id vắng mặt ngày date_str."""
    rows = db.query(Absence.staff_id).filter(Absence.absence_date == date_str).all()
    return {r[0] for r in rows}


_ROLE_MAP = {
    "LD": ["LD", "LD_friday", "LD_cutoff"],
    "SP": ["SP"],
    "NV": ["NV", "NV_friday", "NV_cutoff"],
}


def create_staff(db: Session, full_name: str, role: str,
                 is_on_project: bool = False, display_order: int = 99) -> Staff:
    s = Staff(
        full_name=full_name, role=role,
        is_on_project=1 if is_on_project else 0,
        display_order=display_order,
    )
    db.add(s)
    db.flush()
    # Init rotation states for the new staff member
    from backend.models.duty_models import RotationState
    from backend.config import CURRENT_YEAR
    for rotation_role in _ROLE_MAP.get(role, []):
        db.add(RotationState(
            year=CURRENT_YEAR, role=rotation_role, staff_id=s.id,
            shift_count=0, last_used=None, position=display_order * 10 + s.id,
        ))
    db.commit()
    db.refresh(s)
    return s


def update_staff(db: Session, staff_id: int, full_name: Optional[str] = None,
                 role: Optional[str] = None, is_on_project: Optional[bool] = None,
                 display_order: Optional[int] = None) -> Optional[Staff]:
    s = get_staff_by_id(db, staff_id)
    if not s:
        return None
    if full_name is not None:
        s.full_name = full_name
    if role is not None:
        s.role = role
    if is_on_project is not None:
        s.is_on_project = 1 if is_on_project else 0
    if display_order is not None:
        s.display_order = display_order
    db.commit()
    db.refresh(s)
    return s


def delete_staff(db: Session, staff_id: int) -> bool:
    s = get_staff_by_id(db, staff_id)
    if not s:
        return False
    shifts = db.query(DutyShift).filter(
        DutyShift.nv_ids.like(f'%{staff_id}%')
    ).all()
    for shift in shifts:
        nv_list = json.loads(shift.nv_ids or "[]")
        nv_list = [nid for nid in nv_list if nid != staff_id]
        shift.nv_ids = json.dumps(nv_list)
        shift.nv_count = len(nv_list)
    db.delete(s)
    db.commit()
    return True


def get_available_pool(db: Session, date_str: str) -> dict:
    """
    Pool người có mặt hôm date_str, phân theo role.
    Loại: đi dự án + có khai báo vắng.
    Trả: {'LD': [...], 'SP': [...], 'NV': [...]}
    """
    absent_ids = get_absent_staff_ids(db, date_str)
    all_staff = db.query(Staff).filter(Staff.is_on_project == 0).order_by(
        Staff.display_order, Staff.id
    ).all()

    pool: dict = {"LD": [], "SP": [], "NV": []}
    for person in all_staff:
        if person.id in absent_ids:
            continue
        pool[person.role].append(person)
    return pool
