@echo off
cd /d "%~dp0"
.venv\Scripts\python -m pip install pyinstaller
if errorlevel 1 exit /b 1
.venv\Scripts\python -m PyInstaller --noconfirm --onedir --windowed --collect-all rembg --collect-all onnxruntime --name ThienDaoMapStudio main.py
pause
