@echo off
setlocal

rem Run from the repository root regardless of where the script was called from
cd /d "%~dp0"

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo ERROR: No virtual environment found at "%VENV_PYTHON%".
    echo Create it first:
    echo     py -3.14 -m venv .venv
    echo     .venv\Scripts\python -m pip install -e . build twine
    exit /b 1
)

"%VENV_PYTHON%" -c "import build, twine" 2>nul
if errorlevel 1 (
    echo ERROR: build and twine are missing in the virtual environment.
    echo     .venv\Scripts\python -m pip install build twine
    exit /b 1
)

echo === Building with "%VENV_PYTHON%"

echo === Delete distribution and log directories
if exist "dist" rmdir /s /q "dist"
if exist "Log" rmdir /s /q "Log"

echo === Build Python package
"%VENV_PYTHON%" -m build
if errorlevel 1 (
    echo ERROR: Build failed, nothing was uploaded.
    exit /b 1
)

echo === Upload python package to PIP
"%VENV_PYTHON%" -m twine upload dist/*
