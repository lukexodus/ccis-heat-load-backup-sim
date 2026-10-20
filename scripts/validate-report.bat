@echo off
setlocal
rem =========================================================================
rem validate-report.bat — Windows Command Prompt wrapper for validate-report.py
rem =========================================================================

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    py -3 "%~dp0validate-report.py" %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python "%~dp0validate-report.py" %*
    exit /b %ERRORLEVEL%
)

where python3 >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python3 "%~dp0validate-report.py" %*
    exit /b %ERRORLEVEL%
)

echo ERROR: Python is not found on PATH. Please install Python 3.10+ and add it to PATH. >&2
exit /b 1
