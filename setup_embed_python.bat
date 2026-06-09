@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Chuan bi Python portable - PTT Agribank

echo.
echo  ============================================
echo    Chuan bi goi cai dat OFFLINE
echo    Chay 1 lan tren may CO INTERNET
echo  ============================================
echo.
echo  Script nay se:
echo    1. Tai Python 3.11.9 portable
echo    2. Kich hoat site-packages
echo    3. Cai pip
echo    4. Cai thu vien vao Python portable
echo.
echo  Sau khi xong, copy ca thu muc sang may
echo  khac va chay start.bat -- khong can internet.
echo.
pause

:: ── Khai bao duong dan (dung %~dp0 truc tiep, tranh loi khoang trang) ──
set "EMBED_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
set "GETPIP_URL=https://bootstrap.pypa.io/get-pip.py"
set "EMBED_DIR=%~dp0python_embed"
set "EMBED_ZIP=%~dp0_py_tmp.zip"
set "GETPIP_FILE=%~dp0_get_pip.py"
set "PACKAGES_DIR=%~dp0packages"
set "REQ_FILE=%~dp0requirements.txt"
set "PYTHON_EXE=%~dp0python_embed\python.exe"
set "PIP_EXE=%~dp0python_embed\Scripts\pip.exe"

echo  [INFO] EMBED_DIR : %EMBED_DIR%
echo  [INFO] PACKAGES  : %PACKAGES_DIR%
echo  [INFO] REQ_FILE  : %REQ_FILE%
echo.

:: ─────────────────────────────────────────────────────────────────────────────
:: BUOC 1: TAI PYTHON 3.11.9 PORTABLE
:: ─────────────────────────────────────────────────────────────────────────────
if exist "%PYTHON_EXE%" (
    echo  [1/4] Python portable da co. Bo qua.
    goto :step2
)

echo  [1/4] Dang tai Python 3.11.9 portable...
curl -L --progress-bar -o "%EMBED_ZIP%" "%EMBED_URL%"
if !errorlevel! neq 0 (
    echo.
    echo  [LOI] Khong tai duoc! Kiem tra ket noi internet.
    echo.
    pause
    exit /b 1
)

if not exist "%EMBED_DIR%" mkdir "%EMBED_DIR%"
echo  Giai nen...
powershell -Command "Expand-Archive -LiteralPath '%EMBED_ZIP%' -DestinationPath '%EMBED_DIR%' -Force"
if exist "%EMBED_ZIP%" del "%EMBED_ZIP%"

if not exist "%PYTHON_EXE%" (
    echo  [LOI] Giai nen that bai!
    pause
    exit /b 1
)
echo  [OK] Python portable san sang.

:: ─────────────────────────────────────────────────────────────────────────────
:: BUOC 2: KICH HOAT SITE-PACKAGES TRONG _pth FILE
:: ─────────────────────────────────────────────────────────────────────────────
:step2
echo  [2/4] Kich hoat site-packages...
powershell -Command "Get-ChildItem '%EMBED_DIR%\python3*._pth' | ForEach-Object { (Get-Content $_.FullName) -replace '#import site','import site' | Set-Content $_.FullName -Encoding ascii }"
echo  [OK] Kich hoat xong.

:: ─────────────────────────────────────────────────────────────────────────────
:: BUOC 3: CAI PIP
:: ─────────────────────────────────────────────────────────────────────────────
:step3
if exist "%PIP_EXE%" (
    echo  [3/4] Pip da co. Bo qua.
    goto :step4
)

echo  [3/4] Dang tai pip...
curl -L -o "%GETPIP_FILE%" "%GETPIP_URL%"
if !errorlevel! neq 0 (
    echo  [LOI] Khong tai duoc pip!
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%GETPIP_FILE%" --no-warn-script-location -q
if exist "%GETPIP_FILE%" del "%GETPIP_FILE%"

if not exist "%PIP_EXE%" (
    echo  [LOI] Cai pip that bai!
    pause
    exit /b 1
)
echo  [OK] Pip da cai xong.

:: ─────────────────────────────────────────────────────────────────────────────
:: BUOC 4: CAI THU VIEN
:: ─────────────────────────────────────────────────────────────────────────────
:step4
echo  [4/4] Dang cai thu vien vao Python portable...

:: Kiem tra co file whl trong packages/ khong (dung wildcard)
set "HAS_WHL=0"
if exist "%PACKAGES_DIR%\*.whl" set "HAS_WHL=1"

if "!HAS_WHL!"=="1" (
    echo       Tim thay packages\ -- cai offline...
    "%PYTHON_EXE%" -m pip install --no-index --find-links "%PACKAGES_DIR%" -r "%REQ_FILE%" --no-warn-script-location -q --disable-pip-version-check
    if !errorlevel! equ 0 goto :verify
    echo  [!] Cai offline co loi, thu tai tu PyPI...
)

:: Fallback: tai tu PyPI
echo       Dang tai tu PyPI...
if not exist "%PACKAGES_DIR%" mkdir "%PACKAGES_DIR%"
"%PYTHON_EXE%" -m pip download -r "%REQ_FILE%" -d "%PACKAGES_DIR%" --platform win_amd64 --python-version 3.11 --implementation cp --abi cp311 --only-binary :all: -q --disable-pip-version-check
if !errorlevel! neq 0 (
    echo  [LOI] Tai packages that bai! Kiem tra internet.
    pause
    exit /b 1
)
"%PYTHON_EXE%" -m pip install --no-index --find-links "%PACKAGES_DIR%" -r "%REQ_FILE%" --no-warn-script-location -q --disable-pip-version-check
if !errorlevel! neq 0 (
    echo  [LOI] Cai thu vien that bai!
    pause
    exit /b 1
)

:verify
echo  [OK] Thu vien da cai xong.
echo.
echo  Dang kiem tra...
"%PYTHON_EXE%" -c "import fastapi, nicegui, uvicorn, sqlalchemy; print('  [OK] Tat ca thu vien chinh san sang.')"
if !errorlevel! neq 0 (
    echo  [CANH BAO] Mot so thu vien co the chua duoc cai du.
)

echo.
echo  ============================================
echo   HOAN TAT!
echo.
echo   Ca thu muc nay san sang de copy sang
echo   may khac va chay khong can internet.
echo.
echo   Tren may dich: chi can chay start.bat
echo  ============================================
echo.
pause
endlocal
