@echo off
setlocal enabledelayedexpansion
title FieldGuard Enterprise Platform

cd /d "%~dp0"
set PYTHONPATH=src
set PYTHONIOENCODING=utf-8

echo ======================================================================
echo    FieldGuard Enterprise Policy Verification Platform
echo ======================================================================
echo.

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_BIN=%~dp0.venv\Scripts\python.exe"
) else (
    set "PY_BIN=python"
)

:: Check if server is already running on port 8501
netstat -ano | findstr /R ":8501.*LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    echo [INFO] FieldGuard server is already running on http://localhost:8501
    echo [INFO] Opening web application in your default browser...
    start http://localhost:8501
    echo.
    echo Ready! You can close this launcher window anytime.
    ping 127.0.0.1 -n 3 >nul 2>&1
    exit /b 0
)

echo [INFO] Starting FieldGuard Uvicorn Server on port 8501...
start "FieldGuard Server (Port 8501)" "%PY_BIN%" -m uvicorn fieldguard.server:app --host 0.0.0.0 --port 8501

echo [INFO] Waiting for server startup...
ping 127.0.0.1 -n 3 >nul 2>&1

echo [INFO] Opening FieldGuard in your default browser at http://localhost:8501...
start http://localhost:8501

echo.
echo ======================================================================
echo   FieldGuard is now running at: http://localhost:8501
echo   Keep the 'FieldGuard Server' window open while using the app.
echo ======================================================================
echo.
echo Press any key to close this launcher...
pause >nul
