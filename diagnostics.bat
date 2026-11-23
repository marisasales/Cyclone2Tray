@echo off
title Cyclone2Tray Diagnostics
chcp 65001 >nul
"%~dp0.venv\Scripts\python.exe" "%~dp0probe.py" %*
echo.
pause
