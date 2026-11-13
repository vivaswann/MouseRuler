@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0MouseMeasure.exe" (
    "%~dp0MouseMeasure.exe" %*
    exit /b
)
if not exist "%~dp0.venv\Scripts\python.exe" (
    py -3 -m venv "%~dp0.venv"
    if errorlevel 1 goto :failed
)
"%~dp0.venv\Scripts\python.exe" -c "import PySide6, numpy, pyqtgraph, serial" >nul 2>&1
if errorlevel 1 (
    "%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 goto :failed
)
"%~dp0.venv\Scripts\python.exe" "%~dp0bootstrap.py" %*
if errorlevel 1 goto :failed
exit /b 0
:failed
echo MouseMeasure could not launch. Read the error above and README.md.
pause
exit /b 1
