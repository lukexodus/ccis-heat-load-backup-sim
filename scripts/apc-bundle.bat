@echo off
setlocal
rem =========================================================================
rem apc-bundle.bat — Windows Command Prompt wrapper for apc-bundle.ps1
rem Run from ccis-heat-load-backup-sim repository root.
rem =========================================================================

set "PS_BIN=powershell.exe"
where pwsh >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PS_BIN=pwsh"
)

%PS_BIN% -NoProfile -ExecutionPolicy Bypass -File "%~dp0apc-bundle.ps1" %*
exit /b %ERRORLEVEL%
