@echo off
REM ============================================================
REM  BUILD_NOW.bat - Builds ControlIt.exe in a path without Hebrew
REM  Just double-click this file and wait!
REM ============================================================

echo ============================================
echo   ControlIt - Building EXE
echo ============================================
echo.

REM Step 1: Create build directory outside Hebrew path
echo [1/5] Creating C:\ControlItBuild...
if exist C:\ControlItBuild rmdir /S /Q C:\ControlItBuild
mkdir C:\ControlItBuild

REM Step 2: Copy all Python files
echo [2/5] Copying source files...
xcopy "%~dp0*.py" C:\ControlItBuild\ /Y >nul

REM Step 3: Move to build directory
cd /D C:\ControlItBuild

REM Step 4: Install/upgrade dependencies
echo [3/5] Installing dependencies (1-2 min)...
py -m pip install --upgrade pyinstaller >nul 2>&1
py -m pip install --upgrade cryptography customtkinter pillow psutil bcrypt >nul 2>&1

REM Step 5: Build with all the right flags
echo [4/5] Building EXE (3-5 min)...
echo.

py -m PyInstaller ^
    --onedir ^
    --windowed ^
    --noconfirm ^
    --name ControlIt ^
    --collect-all cryptography ^
    --collect-all customtkinter ^
    --collect-all PIL ^
    --collect-all psutil ^
    --hidden-import bcrypt ^
    --hidden-import main_menu ^
    --hidden-import agent_gui ^
    --hidden-import login_page ^
    --hidden-import my_connector ^
    --hidden-import net_utils ^
    --hidden-import crypto ^
    --hidden-import discovery_utils ^
    --hidden-import discovery_store ^
    --hidden-import script ^
    --hidden-import file_transfer ^
    launcher.py

echo.
echo [5/5] Done!
echo.
echo ============================================
echo   SUCCESS!
echo ============================================
echo.
echo   Your EXE is at:
echo   C:\ControlItBuild\dist\ControlIt\ControlIt.exe
echo.
echo   To share: ZIP the entire ControlIt folder
echo   (the EXE needs the other files in the folder)
echo.
echo ============================================
echo.

REM Open the dist folder so they can see it
explorer C:\ControlItBuild\dist\ControlIt

pause
