@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Phan lich truc - PTT Agribank

:: Kiem tra Python co trong PATH khong
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [LOI] Khong tim thay Python!
    echo.
    echo  Vui long cai Python 3.11 truoc khi chay chuong trinh.
    echo  Tai ve tai: https://www.python.org/downloads/release/python-3110/
    echo.
    echo  Luu y: Trong khi cai dat, chon "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

python launcher.py
if errorlevel 1 (
    echo.
    echo  [LOI] Chuong trinh ket thuc voi loi.
    pause
)
