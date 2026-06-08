"""
SQLAlchemy ORM models cho Phân lịch trực — Phòng Thanh toán.
7 bảng: staff, absences, duty_requests, special_days,
        rotation_state, duty_shifts, duty_shift_nv, shift_config
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, UniqueConstraint,
    ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from backend.database import Base


class Staff(Base):
    """25 nhân sự cố định của phòng (LĐ / NV)."""
    __tablename__ = "staff"

    id            = Column(Integer, primary_key=True, index=True)
    full_name     = Column(String(100), nullable=False)
    role          = Column(String(10), nullable=False)   # 'LD' | 'NV'
    is_on_project = Column(Integer, default=0)           # 0/1
    is_sp_backup  = Column(Integer, default=0)           # T3: 1 = LD kiêm Song Phương khi thiếu
    can_do_sp     = Column(Integer, default=0)           # 1 = NV có thể xử lý nghiệp vụ Song Phương
    display_order = Column(Integer, default=0)
    created_at    = Column(String(30), default=lambda: datetime.now().isoformat(timespec="seconds"))

    __table_args__ = (
        CheckConstraint("role IN ('LD','NV')", name="chk_staff_role"),
    )

    # Relationships
    absences          = relationship("Absence",       back_populates="staff", cascade="all, delete-orphan")
    duty_requests     = relationship("DutyRequest",   back_populates="staff", cascade="all, delete-orphan")
    rotation_states   = relationship("RotationState", back_populates="staff", cascade="all, delete-orphan")


class Absence(Base):
    """Khai báo vắng mặt: person + date."""
    __tablename__ = "absences"

    id           = Column(Integer, primary_key=True, index=True)
    staff_id     = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    absence_date = Column(String(10), nullable=False)   # 'YYYY-MM-DD'
    created_at   = Column(String(30), default=lambda: datetime.now().isoformat(timespec="seconds"))

    staff = relationship("Staff", back_populates="absences")

    __table_args__ = (
        UniqueConstraint("staff_id", "absence_date", name="uq_absence"),
        Index("ix_absence_date", "absence_date"),
        Index("ix_absence_staff_date", "staff_id", "absence_date"),
    )


class DutyRequest(Base):
    """Đăng ký xin trực: một lần hoặc hàng tuần."""
    __tablename__ = "duty_requests"

    id            = Column(Integer, primary_key=True, index=True)
    staff_id      = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    request_type  = Column(String(10), nullable=False)   # 'once' | 'weekly'
    specific_date = Column(String(10))                   # 'YYYY-MM-DD' khi type='once'
    day_of_week   = Column(Integer)                      # 0=Mon..4=Fri khi type='weekly'
    year          = Column(Integer, nullable=False)
    is_active     = Column(Integer, default=1)
    created_at    = Column(String(30), default=lambda: datetime.now().isoformat(timespec="seconds"))

    staff = relationship("Staff", back_populates="duty_requests")

    __table_args__ = (
        CheckConstraint("request_type IN ('once','weekly')", name="chk_req_type"),
        Index("ix_req_staff_year", "staff_id", "year"),
        Index("ix_req_date", "specific_date"),
        Index("ix_req_dow_year", "day_of_week", "year"),
    )


class SpecialDay(Base):
    """Ngày đặc biệt: lễ, bù, cut-off, quyết toán."""
    __tablename__ = "special_days"

    id           = Column(Integer, primary_key=True, index=True)
    date         = Column(String(10), unique=True, nullable=False)   # 'YYYY-MM-DD'
    day_type     = Column(String(20), nullable=False)
    # 'holiday' | 'cutoff' | 'settlement' | 'makeup'
    label        = Column(String(100))
    is_confirmed = Column(Integer, default=0)   # cutoff/settlement cần user confirm
    created_at   = Column(String(30), default=lambda: datetime.now().isoformat(timespec="seconds"))

    __table_args__ = (
        CheckConstraint(
            "day_type IN ('holiday','cutoff','settlement','makeup')",
            name="chk_special_type"
        ),
    )


class RotationState(Base):
    """Trạng thái vòng xoay theo năm và loại ca (reset mỗi năm)."""
    __tablename__ = "rotation_state"

    id          = Column(Integer, primary_key=True, index=True)
    year        = Column(Integer, nullable=False)
    role        = Column(String(20), nullable=False)
    # 'LD' | 'SP' | 'NV' | 'LD_friday' | 'NV_friday' | 'LD_cutoff' | 'NV_cutoff'
    staff_id    = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    shift_count = Column(Integer, default=0)
    last_used   = Column(String(10))   # 'YYYY-MM-DD'
    position    = Column(Integer, default=0)   # tie-break: vị trí ban đầu

    staff = relationship("Staff", back_populates="rotation_states")

    __table_args__ = (
        UniqueConstraint("year", "role", "staff_id", name="uq_rotation"),
        Index("ix_rotation_year_role", "year", "role"),
    )


class DutyShift(Base):
    """Kết quả phân lịch — 1 ca trực."""
    __tablename__ = "duty_shifts"

    id         = Column(Integer, primary_key=True, index=True)
    shift_date = Column(String(10), nullable=False)   # 'YYYY-MM-DD'
    shift_type = Column(String(20), nullable=False)
    # 'normal' | 'friday' | 'cutoff' | 'settlement_main' | 'settlement_sub'
    leader_id  = Column(Integer, ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    sp_id      = Column(Integer, ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    sp_warning = Column(String(20))   # NULL | 'leader_sp' | 'no_sp'
    nv_ids     = Column(Text, default="[]")   # JSON array "[1,3,5]"
    nv_count   = Column(Integer, default=0)
    is_auto    = Column(Integer, default=1)   # 1=tự động, 0=sửa tay
    status     = Column(String(10), default="draft")   # 'draft' | 'confirmed'
    created_at = Column(String(30), default=lambda: datetime.now().isoformat(timespec="seconds"))

    # Relationships
    leader = relationship("Staff", foreign_keys=[leader_id])
    sp     = relationship("Staff", foreign_keys=[sp_id])
    nv_entries = relationship("DutyShiftNV", back_populates="shift", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("shift_date", "shift_type", name="uq_shift_date_type"),
        CheckConstraint(
            "shift_type IN ('normal','friday','cutoff','settlement_main','settlement_sub')",
            name="chk_shift_type"
        ),
        CheckConstraint("status IN ('draft','confirmed')", name="chk_shift_status"),
        Index("ix_shift_date", "shift_date"),
        Index("ix_shift_date_status", "shift_date", "status"),
    )


class DutyShiftNV(Base):
    """Bảng phụ: NV trong từng ca — để query hiệu quả."""
    __tablename__ = "duty_shift_nv"

    id         = Column(Integer, primary_key=True, index=True)
    shift_id   = Column(Integer, ForeignKey("duty_shifts.id", ondelete="CASCADE"), nullable=False)
    staff_id   = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    slot_index = Column(Integer, default=0)   # thứ tự trong ca

    shift = relationship("DutyShift", back_populates="nv_entries")
    staff = relationship("Staff")

    __table_args__ = (
        Index("ix_shiftnv_shift", "shift_id"),
        Index("ix_shiftnv_staff_shift", "staff_id", "shift_id"),
    )


class ShiftConfig(Base):
    """Cấu hình ca trực theo năm."""
    __tablename__ = "shift_config"

    id           = Column(Integer, primary_key=True, index=True)
    year         = Column(Integer, unique=True, nullable=False)
    nv_count     = Column(Integer, default=1)    # số NV mặc định mỗi ca
    signer_name  = Column(String(100), nullable=True)  # N1: tên người ký file Excel
