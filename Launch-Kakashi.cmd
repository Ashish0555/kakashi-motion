@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo First launch: creating the portable CPU environment.
  echo On a Snapdragon PC, run this launcher with x64 Python 3.12 installed.
  py -3.12 -m venv .venv
  if errorlevel 1 goto fail
)
if not exist .venv\.kakashi-ready (
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto fail
  type nul > .venv\.kakashi-ready
)
.venv\Scripts\python.exe run.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo Setup or launch failed. See README.md and docs\snapdragon.md.
pause
exit /b 1
