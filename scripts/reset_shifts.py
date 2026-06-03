"""
reset_shifts.py — Script xóa toàn bộ dữ liệu test và reset vòng xoay.

Chạy từ thư mục gốc của project:
    python scripts/reset_shifts.py

Script thực hiện 3 việc:
  1. Xóa tất cả DutyShiftNV (bảng phụ)
  2. Xóa tất cả DutyShift (ca trực)
  3. Xóa + khởi tạo lại RotationState năm chỉ định
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models.duty_models import DutyShift, DutyShiftNV, RotationState
from backend.services.scheduler_engine import init_rotation_for_year
from backend.config import CURRENT_YEAR


def reset(year: int = None):
    if year is None:
        year = CURRENT_YEAR

    print(f"\n⚠️  Bắt đầu reset dữ liệu (năm {year})...")
    db = SessionLocal()
    try:
        # 1. Xóa bảng phụ DutyShiftNV trước (FK → DutyShift)
        nv_count = db.query(DutyShiftNV).count()
        db.query(DutyShiftNV).delete(synchronize_session=False)
        print(f"   ✓ Đã xóa {nv_count} bản ghi DutyShiftNV")

        # 2. Xóa tất cả ca trực
        shift_count = db.query(DutyShift).count()
        db.query(DutyShift).delete(synchronize_session=False)
        print(f"   ✓ Đã xóa {shift_count} ca trực")

        # 3. Xóa rotation_state năm chỉ định
        rot_count = db.query(RotationState).filter_by(year=year).count()
        db.query(RotationState).filter_by(year=year).delete(synchronize_session=False)
        db.commit()
        print(f"   ✓ Đã xóa {rot_count} rotation_state năm {year}")

        # 4. Khởi tạo lại vòng xoay từ đầu
        init_rotation_for_year(db, year)
        print(f"   ✓ Đã khởi tạo lại vòng xoay năm {year} (tất cả shift_count = 0)")

        print(f"\n✅ Hoàn thành! DB đã sạch và sẵn sàng test.\n")
        print("📌 Bước tiếp theo:")
        print("   1. Khởi động lại backend: python run_backend.py")
        print("   2. Mở http://localhost:8081")
        print("   3. Vào Phân lịch trực → 'Phân tuần này'\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Lỗi: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 55)
    print("  RESET DỮ LIỆU TEST — Phân lịch trực Agribank TTTT")
    print("=" * 55)
    print(f"\nThao tác này sẽ XÓA TOÀN BỘ:")
    print(f"  • Tất cả ca trực (DutyShift)")
    print(f"  • Tất cả dữ liệu NV trong ca (DutyShiftNV)")
    print(f"  • Vòng xoay năm {CURRENT_YEAR} (RotationState) — sẽ khởi tạo lại\n")
    print("Dữ liệu GIỮ NGUYÊN:")
    print("  • Danh sách nhân sự")
    print("  • Ngày lễ / Ngày đặc biệt")
    print("  • Đăng ký xin trực / Khai báo vắng\n")

    confirm = input("Xác nhận? Gõ 'yes' để tiếp tục: ").strip()
    if confirm.lower() == "yes":
        reset()
    else:
        print("\nĐã hủy. Không có dữ liệu nào bị xóa.")
