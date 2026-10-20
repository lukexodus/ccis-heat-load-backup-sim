@echo off
setlocal
rem =========================================================================
rem manage-decisions.bat — Windows Command Prompt wrapper for manage-decisions.py
rem =========================================================================

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    py -3 "%~dp0manage-decisions.py" %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python "%~dp0manage-decisions.py" %*
    exit /b %ERRORLEVEL%
)

where python3 >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python3 "%~dp0manage-decisions.py" %*
    exit /b %ERRORLEVEL%
)

echo ERROR: Python is not found on PATH. Please install Python 3.10+ and add it to PATH. >&2
exit /b 1
