@echo off
title MCP Servers Manager
pushd "%~dp0"
"D:\Tools & MCP\Local\Scrapling\.venv\Scripts\python.exe" "%~dp0mcp_cli_manager.py" %*
if "%1"=="" pause
popd
