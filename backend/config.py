import os
from datetime import datetime

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "duty_scheduler.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ── App ──────────────────────────────────────────────────────────────────────
APP_TITLE = "Phân lịch trực — Phòng Thanh toán"
API_PREFIX = "/api/v1"
BACKEND_PORT = 8001
FRONTEND_PORT = 8081

# ── Business constants ───────────────────────────────────────────────────────
CURRENT_YEAR: int = datetime.now().year

# Tên 2 lãnh đạo có thể kiêm nhiệm SP khi thiếu
SP_BACKUP_LEADERS = {"Trần Thị Mỹ Linh", "Trần Thị Bích Phương"}

# Số NV mặc định mỗi ca (có thể override qua shift_config)
DEFAULT_NV_COUNT = 1
