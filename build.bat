@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Create .venv and install requirements.txt and requirements-build.txt first.
    exit /b 1
)
if not exist "%ROOT%assets\app.png" (
    echo Place the application icon at assets\app.png first.
    exit /b 1
)

"%PYTHON%" -c "from pathlib import Path; from PIL import Image; import sys; output=Path(sys.argv[2]); output.parent.mkdir(parents=True, exist_ok=True); Image.open(sys.argv[1]).convert('RGBA').save(output, format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])" "%ROOT%assets\app.png" "%ROOT%build\Cyclone2Tray.ico"
if errorlevel 1 exit /b %ERRORLEVEL%

"%PYTHON%" -m PyInstaller --clean --noconfirm --onedir --windowed --name Cyclone2Tray ^
    --distpath "%ROOT%dist" ^
    --workpath "%ROOT%build\pyinstaller" ^
    --specpath "%ROOT%build" ^
    --icon "%ROOT%build\Cyclone2Tray.ico" ^
    --add-binary "%ROOT%vendor\hidapi.dll;vendor" ^
    --add-data "%ROOT%vendor\HIDAPI-LICENSE.txt;vendor" ^
    "%ROOT%run_tray.py"
if errorlevel 1 exit /b %ERRORLEVEL%

"%PYTHON%" -c "import shutil,sys; shutil.make_archive(sys.argv[1], 'zip', root_dir=sys.argv[2], base_dir='Cyclone2Tray')" "%ROOT%dist\Cyclone2Tray-portable" "%ROOT%dist"
exit /b %ERRORLEVEL%
