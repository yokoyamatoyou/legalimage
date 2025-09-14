@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "STREAMLIT_EXE=.venv\Scripts\streamlit.exe"
if not exist "%STREAMLIT_EXE%" (
  echo ERROR: %STREAMLIT_EXE% not found. Run setup_and_run.bat first.
  exit /b 1
)

"%STREAMLIT_EXE%" run "app\main.py"
exit /b %errorlevel%
