@echo off
REM WSG Initiative Portfolio - one-click start on Windows (needs Python 3.11+ installed)
title Initiative Portfolio - %~dp0
cd /d "%~dp0backend"
netstat -ano | findstr ":8001" | findstr "LISTENING" >nul
if not errorlevel 1 (
  echo.
  echo   The Initiative Portfolio is already running on this computer.
  echo   Open http://127.0.0.1:8001 in your browser, or close the other black window first.
  echo.
  start "" http://127.0.0.1:8001
  pause
  exit /b
)
if not exist .venv (
  echo Creating Python environment - first run only...
  python -m venv .venv
)
.\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
echo.
echo   Starting the Initiative Portfolio from %~dp0
echo   Open http://127.0.0.1:8001   (keep this window open while you use it)
echo   Your data is in backend\portfolio.db  -  backups in backend\backups\
echo.
start "" http://127.0.0.1:8001
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
