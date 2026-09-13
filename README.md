# ✦ MCP 360° ENGINE (v3.0)
### Full-System Network Port Prober, Stdio Process Inspector & Universal Machine Harvester

A standalone, high-performance CLI utility for Windows styled after the **Claude Code CLI** (Anthropic Coral/Emerald palette, rounded box framing, and pixel-perfect ANSI alignment). 

Zero dependency on third-party daemon apps like MCP Router. Pure on-demand, non-blocking execution.

---

## 💡 Architecture & Design: Evaluating Discovery Strategies

When managing Model Context Protocol (MCP) servers, two primary detection approaches are often proposed. The **v3.0 360° Engine** evaluates both and integrates their strengths to eliminate their respective flaws:

| Detection Strategy | Strengths | Critical Flaws / Blindspots |
| :--- | :--- | :--- |
| **Strategy A: Network Port Probing**<br>*(Scanning all open ports)* | Detects HTTP, SSE, FastMCP, and remote network-bound MCP servers regardless of how they were launched. | **Misses Stdio Servers**: The majority of local MCP servers (Claude, Cursor, Cline) communicate over `stdin`/`stdout` pipes and **never bind a TCP port**. |
| **Strategy B: Agent Config Harvester**<br>*(Reading `claude.json`, Cursor, etc.)* | Knows the exact launch commands, CLI arguments, and environment variables configured for each agent. | **The Unconfigured Server Flaw**: If you download, git-clone, or `pip/npm install` a new MCP server on your drive (e.g. `D:\Tools & MCP\Local\mcp-google-sheets`), but **have not yet added it** to an agent config file, it remains completely invisible. |
| **⭐ The v3.0 360° Hybrid Engine** | **Solves all blindspots**: Merges live Network Socket Probing + OS Stdio Process Tree Tracking + Machine Filesystem Discovery + Universal Multi-Agent Harvesting. | **Zero Blindspots**: Discovers active network sockets, running Stdio pipes, configured agent servers, and unconfigured local repos. |

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
│  ✦ MCP 360° ENGINE  v3.0 (Surface & Depth Scanner)             ● ALL PORTS & PROCS ACTIVE  │
│  Full-System Network Port Prober & Universal Agent Harvester                               │
╰────────────────────────────────────────────────────────────────────────────────────────────╯
 Agents / Repos : Claude Code, Claude Desktop, Claude Global │ 11 Local Repos on Drive
 System RAM     : [███████░░░] 70.8% (2.2 GB free of 7.7 GB)
 Total Memory   : 168.9 MB Commit Charge  │  1 Active / 15 Total Servers
 Active Ports   : :53826 (Antigravity IDE.exe / PID 7636) (43 total system sockets)
──────────────────────────────────────────────────────────────────────────────────────────────
 #   Server Name              Status      Discovery Source     Port / PID     RAM Commit    CPU
──────────────────────────────────────────────────────────────────────────────────────────────
 01  mcp-google-sheets        ○ READY     Local Disk           ─                  0.0 MB   0.0%
 02  ScrapGraphAI             ○ READY     Local Disk           ─                  0.0 MB   0.0%
 03  Use Browser              ○ READY     Local Disk           ─                  0.0 MB   0.0%
 04  Graphify                 ○ READY     Local Disk           ─                  0.0 MB   0.0%
 05  chrome-devtools-mcp      ○ READY     NPX Cache            ─                  0.0 MB   0.0%
 06  @modelcontextprotocol    ○ READY     NPX Cache            ─                  0.0 MB   0.0%
 07  stitch                   ✦ REMOTE    Claude Code, Claude  Cloud HTTPS         Cloud    N/A
 08  excalidraw               ○ READY     Local Disk, Claude C ─                  0.0 MB   0.0%
 09  facebook-ads-library     ○ READY     Local Disk, Claude C ─                  0.0 MB   0.0%
 10  agent-reach              ○ READY     Local Disk, Claude C ─                  0.0 MB   0.0%
 11  github                   ● RUNNING   Claude Code, Claude  PID 16440+3      168.9 MB   0.0%
 12  tinyfish                 ✦ REMOTE    Claude Code          Cloud HTTPS         Cloud    N/A
 13  scrapling                ○ READY     Local Disk, Claude C ─                  0.0 MB   0.0%
 14  scrcpy-mcp               ○ READY     Local Disk, Claude C ─                  0.0 MB   0.0%
 15  mcp-router               ○ READY     Claude Desktop       ─                  0.0 MB   0.0%
──────────────────────────────────────────────────────────────────────────────────────────────
```

- **`[1-N]`** : Toggle individual server (Starts if stopped, Kills if running).
- **`[K]`** : Kill all running MCP servers immediately.
- **`[S]`** : Start all stopped local MCP servers.
- **`[P]`** : Deep port scan & protocol probe of every listening TCP socket on the system.
- **`[R]`** : Instant refresh and re-scan.
- **`[Q]`** : Quit.

### Quick Status
Double-click **`mcp-status.bat`** for a fast 1-second system status table.

### CLI Commands
Run directly from PowerShell or Command Prompt:
```cmd
mcp-manager.bat status       # 1-second status snapshot
mcp-manager.bat ports        # Deep system-wide port & socket audit
mcp-manager.bat kill <name>  # Kill a specific server
mcp-manager.bat start <name> # Start a specific server
mcp-manager.bat kill-all     # Kill all running MCP servers
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
