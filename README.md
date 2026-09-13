# ✦ MCP 360° ENGINE (v3.1)
### Granular Server Control, Deep Port Prober, Process Tree Terminator & Multi-Agent Harvester

A standalone, high-performance CLI utility for Windows styled after the **Claude Code CLI** (Anthropic Coral/Emerald palette, rounded box framing, and pixel-perfect ANSI alignment). 

Zero dependency on third-party daemon apps like MCP Router. Pure on-demand, non-blocking execution.

---

## 🎯 What's New in v3.1: Granular Server Control

Rather than blindly toggling or killing processes on a single keystroke, the MCP Manager now features a **Granular Control Architecture**:

1. **Select Any Server**: Type its number (`1-N`) or name (e.g. `github`, `excalidraw`, `scrapling`) from the main overview table.
2. **Dedicated Granular Sub-Menu**: Each server gets its own Claude Code-styled control interface:
   - **`[1] Start Server`**: Spawns the MCP server process.
   - **`[2] Stop / Kill Server`**: Forcefully terminates the entire process hierarchy (`taskkill /F /T`) so zero orphaned Node or Python workers linger in RAM.
   - **`[3] Restart Server`**: Cleanly kills the process tree, pauses briefly, and immediately re-launches a fresh instance.
   - **`[4] Disable in Config`**: Sets `"disabled": true` in `mcp_config.json`, `.claude.json`, Cursor, etc., preventing the IDE or agent supervisor from automatically re-spawning it in the background.
   - **`[5] Enable in Config`**: Sets `"disabled": false` to allow the server to run when called by your tools.
   - **`[6] Inspect Full Details`**: Deep diagnostic inspection showing full CLI arguments, masked environment variables (`ghp_***`), live child process tree PIDs, RAM commit, and linked config file paths.
   - **`[R] Refresh Status`**: Live re-check of PIDs, CPU %, and RAM without leaving the menu.
   - **`[B] Back to Overview`**: Return to the main server table.

---

## 💡 Architecture & Design: Evaluating Discovery Strategies

When managing Model Context Protocol (MCP) servers, two primary detection approaches are often proposed. The **MCP 360° Engine** evaluates both and integrates their strengths to eliminate their respective flaws:

| Detection Strategy | Strengths | Critical Flaws / Blindspots |
| :--- | :--- | :--- |
| **Strategy A: Network Port Probing**<br>*(Scanning all open ports)* | Detects HTTP, SSE, FastMCP, and remote network-bound MCP servers regardless of how they were launched. | **Misses Stdio Servers**: The majority of local MCP servers (Claude, Cursor, Cline) communicate over `stdin`/`stdout` pipes and **never bind a TCP port**. |
| **Strategy B: Agent Config Harvester**<br>*(Reading `claude.json`, Cursor, etc.)* | Knows the exact launch commands, CLI arguments, and environment variables configured for each agent. | **The Unconfigured Server Flaw**: If you download, git-clone, or `pip/npm install` a new MCP server on your drive (e.g. `D:\Tools & MCP\Local\mcp-google-sheets`), but **have not yet added it** to an agent config file, it remains completely invisible. |
| **⭐ The 360° Hybrid Engine** | **Solves all blindspots**: Merges live Network Socket Probing + OS Stdio Process Tree Tracking + Machine Filesystem Discovery + Universal Multi-Agent Harvesting. | **Zero Blindspots**: Discovers active network sockets, running Stdio pipes, configured agent servers, and unconfigured local repos. |

---

## ⚡ 4-Layer 360° Discovery Engine

1. **Surface Network Socket Prober**:
   - Sweeps every listening TCP port across `127.0.0.1` and `0.0.0.0`.
   - Probes endpoints for MCP JSON-RPC protocol signatures (`/mcp`, `/sse`, `/ping`, `/status`).
   - Maps open listening ports directly to their parent process name and PID.

2. **Depth Stdio Process Inspector**:
   - Inspects the full OS process table for active Python, Node, FastMCP, and binary MCP workers.
   - Monitors true **Windows Commit Charge** (allocated private memory) alongside working-set RAM, ensuring idle subprocesses cannot hide their memory footprint.

3. **Machine-Wide Filesystem & Package Discovery**:
   - Proactively sweeps local developer repositories (`D:\Tools & MCP\Local`, `~\mcp`, etc.).
   - Discovers installed MCP servers (such as `mcp-google-sheets`, `ScrapGraphAI`, `Graphify`, `Use Browser`) even if they have **never been configured in any coding agent**.
   - Scans the global NPX cache (`%LOCALAPPDATA%\npm-cache\_npx`) for globally cached MCP servers (`chrome-devtools-mcp`, `@modelcontextprotocol/*`).

4. **Universal Agent Config Harvester**:
   - Dynamically parses configuration files without requiring any running agent:
     - **Antigravity IDE / Gemini** (`~/.gemini/config/mcp_config.json`)
     - **Claude Code** (`~/.claude.json`, `~/.claude/mcp.json`)
     - **Claude Desktop** (`claude_desktop_config.json`)
     - **Cursor** (`~/.cursor/mcp.json`, global storage)
     - **Windsurf** (`~/.codeium/windsurf/mcp_config.json`)
     - **Cline / Roo Code** (`cline_mcp_settings.json`)
     - **Continue.dev** (`~/.continue/config.json`)
     - **Zed Editor** (`~/.config/zed/settings.json`)
     - **VS Code Workspace** (`.vscode/mcp.json`, `mcp.json`)

---

## 🚀 Usage

### Interactive Menu
Double-click **`mcp-manager.bat`**:

```text
╭────────────────────────────────────────────────────────────────────────────────────────────╮
│  ✦ MCP 360° ENGINE  v3.1 (Surface & Depth Scanner)             ● ALL PORTS & PROCS ACTIVE  │
│  Full-System Network Port Prober & Universal Agent Harvester                               │
╰────────────────────────────────────────────────────────────────────────────────────────────╯
 Agents / Repos : Antigravity IDE, Claude Code, Claude Desktop │ 11 Local Repos on Drive
 System RAM     : [████████░░] 85.0% (1.2 GB free of 7.7 GB)
 Total Memory   : 610.4 MB Commit Charge  │  7 Active / 15 Total Servers
 Active Ports   : :53826 (PID 7636) │ :51560 (PID 16484) (43 total system sockets)
──────────────────────────────────────────────────────────────────────────────────────────────
 #   Server Name              Status      Discovery Source     Port / PID     RAM Commit    CPU
──────────────────────────────────────────────────────────────────────────────────────────────
 01  mcp-google-sheets        ○ READY     Local Disk           ─                  0.0 MB   0.0%
 02  ScrapGraphAI             ○ READY     Local Disk           ─                  0.0 MB   0.0%
 03  Use Browser              ○ READY     Local Disk           ─                  0.0 MB   0.0%
 04  Graphify                 ○ READY     Local Disk           ─                  0.0 MB   0.0%
 05  chrome-devtools-mcp      ○ READY     NPX Cache            ─                  0.0 MB   0.0%
 06  @modelcontextprotocol    ● RUNNING   NPX Cache            PID 1908+2       104.8 MB   0.0%
 07  stitch                   ✦ REMOTE    Antigravity IDE, Cla Cloud HTTPS         Cloud    N/A
 08  github                   ● RUNNING   Antigravity IDE, Cla PID 4736+1         72.5 MB   0.0%
 09  excalidraw               ● RUNNING   Local Disk, Antigrav PID 27868         66.2 MB   0.0%
 10  facebook-ads-library     ● RUNNING   Local Disk, Antigrav PID 12404+1       69.5 MB   0.0%
 11  agent-reach              ● RUNNING   Local Disk, Antigrav PID 1712+1        47.1 MB   0.0%
 12  tinyfish                 ✦ REMOTE    Antigravity IDE, Cla Cloud HTTPS         Cloud    N/A
 13  scrapling                ● RUNNING   Local Disk, Antigrav PID 17188+2       76.5 MB   0.0%
 14  scrcpy-mcp               ● RUNNING   Local Disk, Antigrav PID 10976+5      243.8 MB   0.0%
 15  mcp-router               ○ READY     Claude Desktop       ─                  0.0 MB   0.0%
──────────────────────────────────────────────────────────────────────────────────────────────
Tip: Enter server # (01-15) or name to open its Granular Control Menu.

╭─ Actions & Shortcuts ─────────────────────────────────────────────────────────────────────╮
│  [1-N] Select Server    [K] Kill All    [S] Start All    [P] Ports    [R] Refresh    [Q] Quit  │
╰────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Granular Server Menu Example:
Selecting `08` or typing `github`:

```text
╭─ Granular Control: github ───────────────────────────────────────────────────────────╮
│  Status:       ● RUNNING  (PIDs: [4736, 29912])                                      │
│  Resources:    RAM Commit: 72.5 MB   |   CPU: 0.1%                                   │
│  Config Mode:  ACTIVE (Enabled)                                                      │
│  Sources:      Antigravity IDE, Claude Code                                          │
│  Command:      cmd.exe /c npx -y @modelcontextprotocol/server-github                 │
╰──────────────────────────────────────────────────────────────────────────────────────╯

 Available Operations for [github]:
  [1] Start Server           - Spawn process if currently stopped
  [2] Stop / Kill Server     - Forcefully terminate process & all child workers
  [3] Restart Server         - Terminate tree and immediately re-launch
  [4] Disable in Config      - Set 'disabled: true' so IDE/agents won't auto-start it
  [5] Enable in Config       - Set 'disabled: false' to allow on-demand agent use
  [6] Inspect Full Details   - View args, masked env vars, full process tree
  [R] Refresh Status         - Re-query live PIDs and memory commit
  [B] Back to Overview       - Return to main server table

 Select operation [1-6, R, B]:
```

### Quick Status
Double-click **`mcp-status.bat`** for a fast 1-second system status table.

### CLI Commands
Run directly from PowerShell or Command Prompt:
```cmd
mcp-manager.bat status          # 1-second status snapshot
mcp-manager.bat select <name>   # Open granular menu for server directly
mcp-manager.bat restart <name>  # Restart specific server process tree
mcp-manager.bat inspect <name>  # Show detailed diagnostics & process hierarchy
mcp-manager.bat disable <name>  # Disable server in config & kill process tree
mcp-manager.bat enable <name>   # Enable server in config
mcp-manager.bat kill <name>     # Kill specific server process tree
mcp-manager.bat kill-all        # Kill all running MCP servers
mcp-manager.bat start <name>    # Start specific server
mcp-manager.bat ports           # Deep system-wide port & socket audit
```

---

## 🛠️ Requirements

- Windows 10 or 11
- Python 3.9+ with `psutil`:
  ```bash
  pip install psutil
  ```

---

## 📄 License

MIT License © 2026 Divyanshu Aadi
