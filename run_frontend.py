"""
run_frontend.py — Khởi động NiceGUI frontend, port 8081.

Chạy từ thư mục gốc:
    python run_frontend.py
"""
import sys
import os

if __name__ == "__main__":
    # Đảm bảo thư mục gốc trong sys.path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    import runpy
    runpy.run_path(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "main.py"),
        run_name="__main__",
    )
