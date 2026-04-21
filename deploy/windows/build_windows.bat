@echo off
REM Build BinhAnHMI PyInstaller onedir bundle
REM Run from any directory — script resolves to repo root automatically

cd /d "%~dp0..\.."
echo Building BinhAnHMI from: %CD%
echo.

REM Ensure PyInstaller is installed
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller not found. Run: pip install pyinstaller pyinstaller-hooks-contrib
    exit /b 1
)

REM Generate icon if missing
if not exist "deploy\windows\BinhAnHMI.ico" (
    echo Generating icon...
    python deploy\windows\gen_icon.py
)

REM Run PyInstaller
python -m PyInstaller deploy\windows\BinhAnHMI.spec --clean --noconfirm

echo.
if exist "dist\BinhAnHMI\BinhAnHMI.exe" (
    echo BUILD SUCCESSFUL
    echo Output: dist\BinhAnHMI\BinhAnHMI.exe
) else (
    echo BUILD FAILED -- check output above for errors
    exit /b 1
)
