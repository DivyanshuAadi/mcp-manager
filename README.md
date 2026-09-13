# ✦ MCP Servers Manager

A standalone, elegant **Claude Code CLI-styled** utility for Windows to discover, monitor, start, and terminate **Model Context Protocol (MCP)** servers across all coding agents and open network ports.

Zero dependency on external apps. Pure on-demand execution.

---

## Key Capabilities

- **Universal Multi-Agent Discovery**:
  Automatically discovers servers configured across all popular coding agents without manual setup:
  - **Claude Code** (`~/.claude.json`, `~/.claude/mcp.json`)
  - **Claude Desktop** (`claude_desktop_config.json`)
  - **Cursor** (`~/.cursor/mcp.json`)
  - **Windsurf** (`~/.codeium/windsurf/mcp_config.json`)
  - **Cline / Roo Code** (`cline_mcp_settings.json`)
  - **Continue.dev** (`~/.continue/config.json`)
  - **Zed Editor** (`~/.config/zed/settings.json`)
  - **VS Code** (`.vscode/mcp.json` & workspace configs)
  - **Current Workspace** (`mcp.json`)

- **Full System Port & Network Scanner**:
  - Scans all listening TCP ports on `127.0.0.1` and `0.0.0.0`.
  - Automatically identifies which open ports are running MCP listeners (HTTP/SSE transports, FastMCP, etc.) and maps them directly to their Process ID and RAM usage.
  - Interactive deep port scan tool via `[P]` or `mcp-manager.bat ports`.

- **True Memory & CPU Tracking**:
  - Monitors **Windows Commit Charge** (allocated private memory) alongside working set RAM, ensuring idle worker processes (Python/Node) cannot hide their memory footprint.
  - Live CPU percentage per server.

- **Claude Code CLI Aesthetic**:
  - Anthropic Coral & Emerald ANSI styling.
  - Rounded box borders and status indicators (`● RUNNING`, `○ STOPPED`, `✦ REMOTE`).
  - Pixel-perfect Unicode column alignment.

---

## Usage

### Interactive Menu
Double-click **`mcp-manager.bat`**:

- **`[1-N]`** : Toggle individual server (Starts if stopped, Kills if running).
- **`[K]`** : Kill all running MCP servers immediately.
- **`[S]`** : Start all stopped local MCP servers.
- **`[P]`** : Deep port scan of all open sockets on the system.
- **`[R]`** : Refresh and re-scan processes, ports, and agent configs.
- **`[Q]`** : Quit.

### Quick Status
Double-click **`mcp-status.bat`** for an instant 1-second status snapshot.

### Command Line Flags
Run from PowerShell or Command Prompt:
```cmd
mcp-manager.bat status       # 1-second status snapshot
mcp-manager.bat ports        # Scan all open TCP ports on host
mcp-manager.bat kill <name>  # Kill a specific server
mcp-manager.bat start <name> # Start a specific server
mcp-manager.bat kill-all     # Kill all running MCP servers
```

---

## Requirements

- Windows 10/11
- Python 3.9+ with `psutil`:
  ```bash
  pip install psutil
  ```

---

## License

MIT License
