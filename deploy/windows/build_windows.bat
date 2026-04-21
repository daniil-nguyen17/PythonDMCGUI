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

REM ---------------------------------------------------------------------------
REM Inno Setup: compile .iss into installer .exe
REM Non-fatal: PyInstaller bundle is usable even without ISCC installed
REM ---------------------------------------------------------------------------

echo.
echo Looking for Inno Setup compiler (ISCC.exe)...

set "ISCC="

REM Try default install location first
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    goto :iscc_found
)

REM Try PATH-based install
where iscc >nul 2>&1
if not errorlevel 1 (
    set ISCC=iscc
    goto :iscc_found
)

REM ISCC not found — warn and skip (non-fatal)
echo WARNING: Inno Setup 6 not found. Installer .exe will NOT be built.
echo          To build the installer, download and install Inno Setup 6 from:
echo          https://jrsoftware.org/isdl.php
echo          Then re-run this script.
exit /b 0

:iscc_found
echo Using ISCC: %ISCC%
echo Compiling deploy\windows\BinhAnHMI.iss...
"%ISCC%" /Q "deploy\windows\BinhAnHMI.iss"
if errorlevel 1 (
    echo INSTALLER BUILD FAILED -- check ISCC output above for errors
    exit /b 1
)

echo.
echo INSTALLER BUILD SUCCESSFUL
echo Output: dist\BinhAn_HMI_v4.0.0_Setup.exe
