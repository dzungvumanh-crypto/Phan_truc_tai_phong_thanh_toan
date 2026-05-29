# CLAUDE.md

## Dự án

**Phân lịch trực — Phòng Thanh toán Agribank TTTT**: Ứng dụng Python phân lịch trực hằng tuần cho 25 nhân sự, gồm 2 process — FastAPI backend (port 8001) và NiceGUI frontend (port 8081).

## Chạy ứng dụng

```bash
# Yêu cầu: Python 3.10+, cài requirements trước
pip install -r requirements.txt

# Terminal 1 — Backend
python run_backend.py

# Terminal 2 — Frontend
python run_frontend.py
```

- Giao diện: http://localhost:8081
- Swagger: http://localhost:8001/docs

## Kiến trúc

```
frontend/ (NiceGUI, port 8081)
  └─ api_client.py ──HTTP──► backend/ (FastAPI, port 8001)
                                └─ services/ ──ORM──► database/duty_scheduler.db (SQLite)
```

## Nhân sự

25 người cố định, 3 nhóm:
- **LĐ (7)**: Lãnh đạo phòng, mỗi ca cần 1 người
- **SP (5)**: Tác nghiệp Song Phương CITAD/SWIFT, mỗi ca cần 1 người (đặc thù)
- **NV (13)**: Nhân viên thường, mỗi ca ≥ 1 người

## Quy tắc nghiệp vụ quan trọng

- SP thiếu → Trần Thị Mỹ Linh / Trần Thị Bích Phương kiêm nhiệm (cảnh báo + thêm 1 NV)
- Thứ 6 và ngày cut-off: vòng xoay riêng (thống kê cuối năm tách biệt)
- Ngày quyết toán: 2 ca cùng ngày (trực chính + trực phụ)
- Dữ liệu giữ theo năm, vòng xoay reset đầu năm

## sys.path pattern

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```
