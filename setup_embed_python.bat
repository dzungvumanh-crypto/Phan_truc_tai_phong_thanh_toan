@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Chuan bi Python portable - PTT Agribank

echo.
echo  ============================================
echo    Chuan bi goi cai dat OFFLINE
echo    (Chay 1 lan tren may CO INTERNET)
echo  ============================================
echo.
echo  Script nay se:
echo    1. Tai Python 3.11.9 portable (~25 MB)
echo    2. Cau hinh Python portable
echo    3. Tai pip
echo    4. Cai thu vien vao Python portable
echo.
echo  Sau khi xong, copy toan bo thu muc nay sang
echo  may khac va chay start.bat la duoc.
echo.
pause

set BASE=%~dp0
set EMBED_DIR=%BASE%python_embed
set EMBED_ZIP=%BASE%_python_embed_tmp.zip
set EMBED_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
set GETPIP_URL=https://bootstrap.pypa.io/get-pip.py
set PACKAGES_DIR=%BASE%packages
set REQ_FILE=%BASE%requirements.txt

:: ── 1. Tai Python embedded ──────────────────────────────────
if exist "%EMBED_DIR%\python.exe" (
    echo  [1/4] Python portable da co. Bo qua.
    goto :check_pip
)

echo  [1/4] Dang tai Python 3.11.9 portable...
echo        URL: %EMBED_URL%
echo.
curl -L --progress-bar -o "%EMBED_ZIP%" "%EMBED_URL%"
if errorlevel 1 (
    echo.
    echo  [LOI] Khong tai duoc Python. Kiem tra ket noi internet!
    echo.
    pause
    exit /b 1
)

if not exist "%EMBED_DIR%" mkdir "%EMBED_DIR%"
echo  Giai nen Python portable...
powershell -Command "Expand-Archive -Path '%EMBED_ZIP%' -DestinationPath '%EMBED_DIR%' -Force"
del "%EMBED_ZIP%" 2>nul

if not exist "%EMBED_DIR%\python.exe" (
    echo  [LOI] Giai nen that bai!
    pause
    exit /b 1
)
echo  [OK] Python portable san sang.

:: ── 2. Kich hoat site-packages ─────────────────────────────
echo  [2/4] Kich hoat site-packages...
for %%f in ("%EMBED_DIR%\python3*._pth") do (
    powershell -Command "(Get-Content '%%f') -replace '#import site', 'import site' | Set-Content '%%f' -Encoding ascii"
)
echo  [OK] Cau hinh xong.

:check_pip
:: ── 3. Cai pip ─────────────────────────────────────────────
if exist "%EMBED_DIR%\Scripts\pip.exe" (
    echo  [3/4] Pip da co. Bo qua.
    goto :install_packages
)

echo  [3/4] Dang cai pip...
curl -L -o "%BASE%_get_pip.py" "%GETPIP_URL%"
if errorlevel 1 (
    echo  [LOI] Khong tai duoc pip!
    pause
    exit /b 1
)
"%EMBED_DIR%\python.exe" "%BASE%_get_pip.py" --no-warn-script-location -q
del "%BASE%_get_pip.py" 2>nul

if not exist "%EMBED_DIR%\Scripts\pip.exe" (
    echo  [LOI] Cai pip that bai!
    pause
    exit /b 1
)
echo  [OK] Pip da cai xong.

:install_packages
:: ── 4. Cai thu vien ────────────────────────────────────────
echo  [4/4] Cai thu vien vao Python portable...

:: Dem so whl trong packages/
set PKG_OK=0
if exist "%PACKAGES_DIR%\" (
    for %%f in ("%PACKAGES_DIR%\*.whl") do set PKG_OK=1
)

if "%PKG_OK%"=="1" (
    echo      Su dung packages\ co san (offline)...
    "%EMBED_DIR%\python.exe" -m pip install ^
        --no-index "--find-links=%PACKAGES_DIR%" ^
        -r "%REQ_FILE%" ^
        --no-warn-script-location -q --disable-pip-version-check
) else (
    echo      packages\ trong — tai tu PyPI...
    if not exist "%PACKAGES_DIR%" mkdir "%PACKAGES_DIR%"
    "%EMBED_DIR%\python.exe" -m pip download ^
        -r "%REQ_FILE%" -d "%PACKAGES_DIR%" ^
        --platform win_amd64 --python-version 3.11 ^
        --implementation cp --abi cp311 --only-binary :all: ^
        -q --disable-pip-version-check
    "%EMBED_DIR%\python.exe" -m pip install ^
        --no-index "--find-links=%PACKAGES_DIR%" ^
        -r "%REQ_FILE%" ^
        --no-warn-script-location -q --disable-pip-version-check
)

if errorlevel 1 (
    echo.
    echo  [LOI] Cai thu vien that bai!
    echo        Thu chay lai hoac kiem tra requirements.txt
    pause
    exit /b 1
)

echo  [OK] Thu vien da cai xong.

echo.
echo  ============================================
echo   HOAN TAT! Thu muc nay DA SAN SANG de
echo   copy sang may KHONG CO INTERNET.
echo.
echo   Cau truc can copy:
echo     python_embed\    Python portable
echo     packages\        Thu vien du phong
echo     backend\
echo     frontend\
echo     database\
echo     launcher.py
echo     start.bat
echo     ... (cac file khac)
echo.
echo   Tren may dich: chi can chay start.bat
echo  ============================================
echo.
pause
