@echo off
if exist "%~dp0dist\Cyclone2Tray\Cyclone2Tray.exe" (
    start "" "%~dp0dist\Cyclone2Tray\Cyclone2Tray.exe"
) else (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0run_tray.py"
)
