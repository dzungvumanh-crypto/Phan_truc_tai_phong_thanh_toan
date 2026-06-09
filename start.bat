@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Phan lich truc - PTT Agribank

:: ── Uu tien Python portable (khong can cai Python tren may) ──
if exist "%~dp0python_embed\python.exe" (
    "%~dp0python_embed\python.exe" "%~dp0launcher.py"
    goto :end
)

:: ── Fallback: dung Python he thong ──
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [LOI] Khong tim thay Python!
    echo.
    echo  Chay setup_embed_python.bat de cai Python portable
    echo  ^(chi can chay 1 lan tren may co internet^).
    echo.
    echo  Hoac cai Python 3.11 tai:
    echo    https://www.python.org/downloads/release/python-3110/
    echo  ^(Luu y chon "Add Python to PATH" khi cai^)
    echo.
    pause
    exit /b 1
)

python "%~dp0launcher.py"

:end
if errorlevel 1 (
    echo.
    echo  [LOI] Chuong trinh ket thuc voi loi.
    pause
)
