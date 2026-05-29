"""
launcher.py — Khởi động Backend + Frontend, poll đến khi thực sự ready, rồi mở browser.

Gọi từ start.bat:
    python launcher.py
"""
import sys
import os
import subprocess
import time
import webbrowser
import socket
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON   = sys.executable

BACKEND_URL  = "http://localhost:8001"
FRONTEND_URL = "http://localhost:8081"


def server_ready(url: str) -> bool:
    """Kiểm tra server có lắng nghe trên port không (TCP connect — không phụ thuộc HTTP)."""
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        sock = socket.create_connection((host, port), timeout=3)
        sock.close()
        return True
    except Exception:
        return False


def wait_for(url: str, label: str, timeout: int = 90) -> bool:
    """Chờ server sẵn sàng, hiện dấu chấm theo giây, tối đa `timeout` giây."""
    print(f"  Đang chờ {label}", end="", flush=True)
    for _ in range(timeout):
        if server_ready(url):
            print(" ✓")
            return True
        print(".", end="", flush=True)
        time.sleep(1)
    print("  TIMEOUT!")
    return False


def main():
    os.chdir(BASE_DIR)
    sys.path.insert(0, BASE_DIR)

    print()
    print("  ==========================================")
    print("    Phân lịch trực  —  PTT Agribank")
    print("  ==========================================")
    print()

    # ── 0. Cài thư viện (nếu thiếu) ──────────────────────────
    print("  [0/3] Kiểm tra thư viện Python...", flush=True)
    ret = subprocess.run(
        [PYTHON, "-m", "pip", "install", "-r", "requirements.txt",
         "-q", "--disable-pip-version-check"],
        cwd=BASE_DIR,
    )
    if ret.returncode == 0:
        print("  [OK]  Thư viện sẵn sàng.")
    else:
        print("  [!]   Có lỗi khi cài thư viện — thử tiếp tục...")
    print()

    # ── 1. Khởi động Backend ──────────────────────────────────
    print("  [1/3] Khởi động Backend   (port 8001)...")
    backend = subprocess.Popen(
        [PYTHON, os.path.join(BASE_DIR, "run_backend.py")],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    if not wait_for(BACKEND_URL, "Backend  :8001"):
        print()
        print("  [LỖI] Backend không khởi động được!")
        print("         Xem chi tiết trong cửa sổ 'Backend'.")
        print()
        input("  Nhấn Enter để thoát...")
        backend.kill()
        sys.exit(1)

    # ── 2. Khởi động Frontend ─────────────────────────────────
    print()
    print("  [2/3] Khởi động Frontend  (port 8081)...")
    frontend = subprocess.Popen(
        [PYTHON, os.path.join(BASE_DIR, "frontend", "main.py")],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    if not wait_for(FRONTEND_URL, "Frontend :8081"):
        print()
        print("  [LỖI] Frontend không khởi động được!")
        print("         Xem chi tiết trong cửa sổ 'Frontend'.")
        print()
        input("  Nhấn Enter để thoát...")
        frontend.kill()
        backend.kill()
        sys.exit(1)

    # ── 3. Mở trình duyệt ────────────────────────────────────
    print()
    print("  [3/3] Mở trình duyệt...")
    webbrowser.open(FRONTEND_URL)

    print()
    print("  ==========================================")
    print("   ✓  Ứng dụng đang chạy!")
    print("  ==========================================")
    print()
    print(f"   Giao diện  :  {FRONTEND_URL}")
    print(f"   Swagger API:  {BACKEND_URL}/docs")
    print()
    print("   Nhấn  Enter  để TẮT ứng dụng và đóng cửa sổ này.")
    print()

    try:
        input()
    except KeyboardInterrupt:
        pass

    print("  Đang tắt...")
    try:
        frontend.kill()
    except Exception:
        pass
    try:
        backend.kill()
    except Exception:
        pass
    print("  Đã tắt. Bạn có thể đóng cửa sổ này.")


if __name__ == "__main__":
    main()
