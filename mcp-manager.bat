@echo off
title MCP Servers Manager
pushd "%~dp0"
setlocal enabledelayedexpansion

set "PY_EXE="
if exist "D:\Tools & MCP\Local\Scrapling\.venv\Scripts\python.exe" (
    set "PY_EXE=D:\Tools & MCP\Local\Scrapling\.venv\Scripts\python.exe"
)
if "!PY_EXE!"=="" (
    where python >nul 2>&1 && set "PY_EXE=python"
)
if "!PY_EXE!"=="" (
    where py >nul 2>&1 && set "PY_EXE=py -3"
)
if "!PY_EXE!"=="" (
    echo [ERROR] Python not found in PATH or dedicated virtualenv.
    pause
    popd
    exit /b 1
)

"!PY_EXE!" "%~dp0mcp_cli_manager.py" %*
if "%1"=="" pause
popd
