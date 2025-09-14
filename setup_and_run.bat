@echo off
setlocal EnableExtensions

rem Move to this script directory
cd /d "%~dp0"

rem ---- Stop any running processes locking .venv (python/streamlit from this venv) ----
if exist ".venv" (
  echo Checking for running processes using .venv ...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$vd=(Resolve-Path '.\\.venv').Path; Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path -like \"$vd*\" } | ForEach-Object { try { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue } catch {} }"
  echo Attempting to remove existing .venv ...
  for /L %%i in (1,1,5) do (
    if exist ".venv" (
      rmdir /s /q .venv >nul 2>&1
      if exist ".venv" (
        echo Waiting for handles to release (retry %%i/5) ...
        timeout /t 2 /nobreak >nul
      ) else (
        goto venv_removed
      )
    )
  )
  :venv_removed
  if exist ".venv" (
    echo ERROR: Could not remove .venv. Close any running Streamlit/Python using this folder and retry.
    exit /b 1
  )
)

rem ---- Find Python 3.11 via py launcher ----
set "PY311="
py -3.11 -c "print('ok')" >nul 2>nul && set "PY311=py -3.11"
if not defined PY311 (
  echo ERROR: Python 3.11 not found by py launcher.
  echo Please install Python 3.11 from https://www.python.org/downloads/release/python-3110/
  exit /b 1
)

rem ---- Recreate venv to ensure Python 3.11 ----
echo Creating virtual environment with Python 3.11 ...
%PY311% -m venv .venv
if errorlevel 1 (
  echo ERROR: Failed to create virtual environment.
  exit /b 1
)

set "VENV_PY=.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo ERROR: venv python missing.
  exit /b 1
)

echo Upgrading pip/setuptools/wheel ...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
  echo ERROR: Failed to upgrade pip/setuptools/wheel.
  exit /b 1
)

echo Installing requirements ...
if not exist "requirements.txt" (
  echo ERROR: requirements.txt not found.
  exit /b 1
)
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: Failed to install dependencies.
  exit /b 1
)

echo Launching Streamlit ...
"%VENV_PY%" -m streamlit run "app\main.py"
exit /b %errorlevel%
