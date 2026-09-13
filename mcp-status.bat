@echo off
title MCP Server Status
pushd "%~dp0"
"D:\Tools & MCP\Local\Scrapling\.venv\Scripts\python.exe" "%~dp0mcp_cli_manager.py" status
pause
popd
