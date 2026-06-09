"""
launcher.py — Khởi động Backend + Frontend, poll đến khi thực sự ready, rồi mở browser.

Gọi từ start.bat:
    python launcher.py

Luồng (chế độ embedded — python_embed có sẵn):
  1. Dùng ngay python_embed/python.exe (bỏ qua venv)
  2. Khởi động Backend (port 8001)
  3. Khởi động Frontend (port 8081)
  4. Mở trình duyệt

Luồng (chế độ system Python — fallback):
  1. Tạo venv (nếu chưa có)
  2. Cài packages từ packages/ (offline) hoặc PyPI (online)
  3-4. Như trên
"""
import sys
import os
import subprocess
import time
import webbrowser
import socket
from urllib.parse import urlparse

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
VENV_DIR     = os.path.join(BASE_DIR, "venv")
PACKAGES_DIR = os.path.join(BASE_DIR, "packages")
REQ_FILE     = os.path.join(BASE_DIR, "requirements.txt")

EMBED_PYTHON = os.path.join(BASE_DIR, "python_embed", "python.exe")
VENV_PYTHON  = os.path.join(VENV_DIR, "Scripts", "python.exe")   # Windows only
BACKEND_URL  = "http://localhost:8001"
FRONTEND_URL = "http://localhost:8081"

# Kiểm tra đang chạy từ embedded Python hay không
_exe = os.path.abspath(sys.executable).lower()
IS_EMBEDDED = _exe.startswith(os.path.join(BASE_DIR, "python_embed").lower())


# ─── helpers ──────────────────────────────────────────────────────────────────

def server_ready(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 80
    try:
        s = socket.create_connection((host, port), timeout=3)
        s.close()
        return True
    except Exception:
        return False


def wait_for(url: str, label: str, timeout: int = 120) -> bool:
    print(f"  Đang chờ {label}", end="", flush=True)
    for _ in range(timeout):
        if server_ready(url):
            print(" OK")
            return True
        print(".", end="", flush=True)
        time.sleep(1)
    print(" TIMEOUT!")
    return False


def run(cmd, **kwargs):
    return subprocess.run(cmd, cwd=BASE_DIR, **kwargs)


# ─── setup venv ───────────────────────────────────────────────────────────────

def get_python_exe() -> str:
    """
    Trả về đường dẫn Python sẽ dùng để chạy backend/frontend.
    - Nếu đang chạy từ embedded Python → dùng luôn sys.executable.
    - Nếu không → tạo/dùng venv, cài packages, trả về venv Python.
    """
    if IS_EMBEDDED:
        print("  [OK] Dang dung Python portable (khong can cai dat them).")
        return sys.executable

    return _setup_venv()


def _setup_venv() -> str:
    """Tạo venv + cài packages khi dùng system Python."""
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 10):
        print(f"  [LOI] Can Python 3.10+, dang dung {major}.{minor}")
        print("         Tai Python tai: https://www.python.org/downloads/")
        input("  Nhan Enter de thoat...")
        sys.exit(1)

    if not os.path.exists(VENV_PYTHON):
        print("  [*] Tao moi truong ao (venv)...", flush=True)
        r = run([sys.executable, "-m", "venv", VENV_DIR])
        if r.returncode != 0:
            print("  [LOI] Khong tao duoc venv!")
            input("  Nhan Enter de thoat...")
            sys.exit(1)
        print("  [OK] Venv da tao.")

    pip = VENV_PYTHON

    run([pip, "-m", "pip", "install", "--upgrade", "pip",
         "-q", "--disable-pip-version-check"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    offline_ok = (os.path.isdir(PACKAGES_DIR)
                  and len(os.listdir(PACKAGES_DIR)) > 0)

    if offline_ok:
        print("  [*] Cai thu vien tu packages/ (offline)...", flush=True)
        r = run([pip, "-m", "pip", "install",
                 "--no-index", f"--find-links={PACKAGES_DIR}",
                 "-r", REQ_FILE, "-q", "--disable-pip-version-check"])
    else:
        print("  [*] Cai thu vien tu PyPI (can internet)...", flush=True)
        r = run([pip, "-m", "pip", "install",
                 "-r", REQ_FILE, "-q", "--disable-pip-version-check"])

    if r.returncode == 0:
        print("  [OK] Thu vien san sang.")
    else:
        print("  [!]  Co loi khi cai thu vien — thu tiep tuc...")

    return pip


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    os.chdir(BASE_DIR)

    print()
    print("  ============================================")
    print("    Phan lich truc  --  PTT Agribank TTTT")
    print("  ============================================")
    print()

    # ── 0. Chuẩn bị môi trường ────────────────────────────────
    print("  [0/3] Kiem tra moi truong...", flush=True)
    python_exe = get_python_exe()
    print()

    # ── 1. Backend ────────────────────────────────────────────
    print("  [1/3] Khoi dong Backend   (port 8001)...")
    backend = subprocess.Popen(
        [python_exe, os.path.join(BASE_DIR, "run_backend.py")],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    if not wait_for(BACKEND_URL, "Backend  :8001"):
        print()
        print("  [LOI] Backend khong khoi dong duoc!")
        print("         Xem chi tiet trong cua so 'Backend'.")
        input("  Nhan Enter de thoat...")
        backend.kill()
        sys.exit(1)

    # ── 2. Frontend ───────────────────────────────────────────
    print()
    print("  [2/3] Khoi dong Frontend  (port 8081)...")
    frontend = subprocess.Popen(
        [python_exe, os.path.join(BASE_DIR, "run_frontend.py")],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    if not wait_for(FRONTEND_URL, "Frontend :8081"):
        print()
        print("  [LOI] Frontend khong khoi dong duoc!")
        print("         Xem chi tiet trong cua so 'Frontend'.")
        input("  Nhan Enter de thoat...")
        frontend.kill()
        backend.kill()
        sys.exit(1)

    # ── 3. Mở trình duyệt ────────────────────────────────────
    print()
    print("  [3/3] Mo trinh duyet...")
    webbrowser.open(FRONTEND_URL)

    print()
    print("  ============================================")
    print("   OK  Ung dung dang chay!")
    print("  ============================================")
    print()
    print(f"   Giao dien  :  {FRONTEND_URL}")
    print(f"   Swagger API:  {BACKEND_URL}/docs")
    print()
    print("   Nhan  Enter  de TAT ung dung va dong cua so nay.")
    print()

    try:
        input()
    except KeyboardInterrupt:
        pass

    print("  Dang tat...")
    for proc in (frontend, backend):
        try:
            proc.kill()
        except Exception:
            pass
    print("  Da tat. Ban co the dong cua so nay.")


if __name__ == "__main__":
    main()
