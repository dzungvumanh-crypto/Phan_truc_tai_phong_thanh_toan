"""
frontend/main.py — NiceGUI entry point, khai báo 5 routes, port 8081.

Chạy trực tiếp:
    python frontend/main.py       (từ thư mục gốc)
    python run_frontend.py        (recommended — dùng runpy, set sys.path)

Routes:
    /           → schedule_planner_page()  (Tab Phân lịch)
    /danh-sach  → roster_list_page()       (Tab Danh sách)
    /lich-tuan  → week_view_page()         (Tab Lịch tuần)
    /thong-ke   → statistics_page()        (Tab Thống kê)
    /cai-dat    → settings_page()          (Tab Cài đặt)
"""
import sys
import os

# Đảm bảo project root trong sys.path khi chạy trực tiếp file này
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nicegui import ui

from frontend.pages.schedule_planner import schedule_planner_page
from frontend.pages.roster_list import roster_list_page
from frontend.pages.week_view import week_view_page
from frontend.pages.statistics import statistics_page
from frontend.pages.settings import settings_page


# ── Route declarations ─────────────────────────────────────────────────────────

@ui.page("/")
def index():
    """Tab Phân lịch — Calendar grid tháng."""
    schedule_planner_page()


@ui.page("/danh-sach")
def roster():
    """Tab Danh sách — Bảng nhân sự."""
    roster_list_page()


@ui.page("/lich-tuan")
def week():
    """Tab Lịch tuần — Grid 5 cột Mon-Fri."""
    week_view_page()


@ui.page("/thong-ke")
def stats():
    """Tab Thống kê — Số ca / người / loại, vòng xoay."""
    statistics_page()


@ui.page("/cai-dat")
def settings_view():
    """Tab Cài đặt — Special days, vắng, đăng ký trực, config, rotation."""
    settings_page()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ui.run(
        host="0.0.0.0",
        port=8081,
        title="Phân lịch trực — PTT Agribank",
        favicon="🏦",
        reload=False,
        show=False,   # start.bat tự mở browser sau khi server ready
    )
