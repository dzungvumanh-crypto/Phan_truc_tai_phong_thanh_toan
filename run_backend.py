"""
run_backend.py — Khởi động FastAPI backend, port 8001.

Chạy từ thư mục gốc:
    python run_backend.py
"""
import sys
import os

if __name__ == "__main__":
    # Đảm bảo thư mục gốc trong sys.path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
    )
