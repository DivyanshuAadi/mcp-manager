# MCP Manager

A lightweight CLI & Windows Batch utility to monitor, manage, start, and terminate **Model Context Protocol (MCP)** servers with true OS memory and CPU tracking.

---

## Features

- **True Resource Tracking**: Reports both active physical RAM and Windows **Commit Charge** (allocated private bytes), preventing idle worker processes from hiding their true memory footprint.
- **3-Layer Auto-Detection**:
  1. **MCP Router Database**: Dynamically reads configured servers from mcprouter.db.
  2. **Claude Configs**: Scans ~/.claude.json, ~/.claude/mcp.json, and Claude Desktop configs for installed servers.
  3. **Live Process Scanner**: Discovers any ad-hoc running MCP server processes (e.g. chrome-devtools-mcp, custom python/node servers) even if unconfigured.
- **Interactive Keyboard Menu**:
  - [1-N] : Toggle individual server (Start if stopped, Kill if running).
  - [K] : Kill all running MCP servers instantly.
  - [S] : Start all stopped local MCP servers.
  - [R] : Refresh and re-scan live processes and configs.
  - [Q] : Quit.
- **Non-Interactive Terminal Flags**:
  - mcp-manager.bat status -> Print 1-second status table and exit.
  - mcp-manager.bat kill <name> -> Kill a specific server by name.
  - mcp-manager.bat start <name> -> Start a specific server by name.
  - mcp-manager.bat kill-all -> Kill all running MCP servers.

---

## File Structure

- **mcp-manager.bat**: Double-click launcher for the interactive CLI menu.
- **mcp-status.bat**: Instant status viewer.
- **mcp_cli_manager.py**: Python backend script using psutil.

---

## Requirements

- Windows 10/11
- Python 3.9+ with psutil installed:
  `ash
  pip install psutil
  `

---

## License

MIT License
