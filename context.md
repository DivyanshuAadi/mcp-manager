# ✦ MCP 360° ENGINE — COMPLETE SYSTEM CONTEXT & ARCHITECTURE GUIDE
> **Purpose**: This document provides incoming AI agents and developers with the complete technical context, evolutionary history, design decisions, known bug resolutions, and configuration registry for the **MCP 360° Engine**.

---

## 1. Executive Summary & Mission

The **MCP 360° Engine** is a high-performance, standalone Windows CLI utility designed to manage, monitor, and configure **Model Context Protocol (MCP)** servers across all installed AI coding agents (Antigravity IDE, Claude Code, Claude Desktop, Cursor, Windsurf, Cline, Roo Code, etc.).

### Why it was created:
- Third-party apps like **MCP Router** ran heavy background daemons, had sluggish Electron/browser UIs, failed to reflect true Windows Commit Charge RAM usage, and created unneeded complexity.
- Coding agents (Claude, Cursor, Antigravity) manage MCP servers independently in separate configuration files. When servers malfunction, hang, or need to be stopped, developers had no single pane of glass to inspect running PIDs, monitor RAM/CPU, kill orphaned background workers, or cleanly disable servers so agents wouldn't immediately auto-restart them.
- The user requested a lightweight, zero-dependency, lightning-fast batch/CLI tool styled after the **Claude Code CLI** (Anthropic Coral/Emerald palette, rounded box framing, pixel-perfect ANSI alignment).

---

## 2. Environment & Machine Infrastructure

| Component | Path / Details | Notes |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 / 10 x64 | Requires Windows PowerShell & CMD |
| **Dedicated Python Runtime** | `D:\\Tools & MCP\\Local\\Scrapling\\.venv\\Scripts\\python.exe` | Pre-configured with `psutil` |
| **Deployed Working Folder** | `C:\\Users\\lenovo\\Desktop\\MCP Manager` | Contains scripts, batch launchers, and docs |
| **Developer Tools Root** | `D:\\Tools & MCP\\Local` & `D:\\Tools & MCP` | Source repos for local MCP servers |
| **GitHub Remote Repo** | `https://github.com/DivyanshuAadi/mcp-manager.git` | Main branch; remote sanitized after push |

---

## 3. Version History & Evolution (v1.0 → v3.2)

### 🔹 v1.0 — Initial CLI & Web App Prototype
- Built initial terminal status scanner and lightweight HTML dashboard.
- Proved that MCP servers could be tracked via system processes and ports.
- **Problem**: User wanted a pure Windows CLI batch launcher without web browser dependencies.

### 🔹 v2.0 — Claude Code CLI Design & Windows Memory Accuracies
- Replaced Web UI with a terminal-native Claude Code-inspired interface.
- Implemented **Windows Commit Charge** measurement (`psutil.Process.memory_info().private`) to accurately expose true allocated memory rather than misleading working-set figures.
- Cleaned up unneeded MCP Router processes and directories.

### 🔹 v3.0 — 360° Hybrid Discovery Engine
- Solved the **"Unconfigured Server Blindspot"**: Introduced a 4-layer detection architecture combining:
  1. Listening TCP socket probing.
  2. Stdio OS process tree tracking.
  3. Local filesystem developer repo scanning.
  4. Multi-agent configuration harvesting.
- Enabled auto-discovery of newly git-cloned or npm/pip installed MCP servers before being configured in any agent.

### 🔹 v3.1 — Granular Server Control Menu & Defect Repairs
- **Granular Control Architecture**: Replaced blind keystroke actions with dedicated server sub-menus (`[1-6, R, B]`):
  - `[1] Start`, `[2] Stop / Force Kill`, `[3] Restart`, `[4] Disable in Config`, `[5] Enable in Config`, `[6] Inspect Details`.
- **Bug Fix**: Fixed `TypeError: object of type 'NoneType' has no len()` when inspecting servers configured without launch commands.
- **Visual Repair**: Resolved text truncation on discovery source tags (e.g. `Antigravity IDE, Cla`).

### 🔹 v3.2 — Sub-Second Responsive UI & Bulletproof Disabling (CURRENT)
- **Eliminated 10-Second Freeze**:
  - *Root Cause*: In v3.1, `get_snapshot()` was probing 43 open TCP ports with 4 HTTP requests each (160 sequential requests with 0.15s timeouts), freezing the UI for 8–10s on every keystroke.
  - *Fix*: Normal snapshots now resolve listening ports by instant PID matching (`0.002s`). Full HTTP socket probing is restricted exclusively to `[P] Deep Port Audit`.
  - Process scanning was optimized to name-first candidate checks (`0.3s`), dropping total refresh latency from **10.5s to < 0.4s (25x faster)**.
- **Fixed Brave Browser False-Positive ("Scrappy Still Running")**:
  - *Root Cause*: Pattern derivation for `scrcpy-mcp/dist/index.js` extracted `'dist'` as a search pattern. Brave Browser launched with `--enable-distillability-service`. Because `'dist'` matched, Brave Browser (PID 2144 + 4 tabs, 201 MB) was falsely flagged as `scrcpy-mcp` running forever!
  - *Fix*: Banned generic directory words (`dist`, `src`, `lib`, `build`, `bin`, `node_modules`) from substring matching, and strictly restricted candidates to recognized language runtimes (`node.exe`, `python.exe`, `scrapling.exe`, `uvx.exe`).
- **Universal Multi-Agent Disabling**:
  - Added `~/.claude/mcp.json` (`Claude Global`) to config sync targets.
  - Implemented symmetric `canon_key()` matching across all 14 agent configs.
  - When disabling a server, all config files are set to `"disabled": true` AND all running worker processes are forcefully terminated immediately (`taskkill /F /T /PID`).
- **Clean Separation of Repos**:
  - Removed phantom entries (`@modelcontextprotocol`, `chrome-devtools-mcp` from NPX cache) from active server table.
  - Downloaded repositories on disk are grouped cleanly under `[U] Downloaded Repos on Disk`.

---

## 4. Multi-Agent Configuration Registry

The engine dynamically reads and synchronizes `"disabled": true/false` across all **14 standard agent locations**:

| Agent / Environment | Configuration Path | Scope |
| :--- | :--- | :--- |
| **Antigravity IDE** | `C:\\Users\\lenovo\\.gemini\\config\\mcp_config.json` | Gemini Antigravity IDE |
| **Claude Code** | `C:\\Users\\lenovo\\.claude.json` | Claude Code (CLI) |
| **Claude Global** | `C:\\Users\\lenovo\\.claude\\mcp.json` | Global Claude Code settings |
| **Claude Desktop** | `C:\\Users\\lenovo\\AppData\\Roaming\\Claude\\claude_desktop_config.json` | Claude Desktop App |
| **Cursor** | `C:\\Users\\lenovo\\.cursor\\mcp.json` | Cursor Editor Workspace |
| **Cursor Global** | `C:\\Users\\lenovo\\AppData\\Roaming\\Cursor\\User\\globalStorage\\mcp.json` | Cursor Global Settings |
| **Windsurf** | `C:\\Users\\lenovo\\.codeium\\windsurf\\mcp_config.json` | Windsurf Workspace |
| **Windsurf User** | `C:\\Users\\lenovo\\AppData\\Roaming\\Windsurf\\User\\mcp.json` | Windsurf Global Settings |
| **Cline** | `%APPDATA%\\Code\\User\\globalStorage\\saoudrizwan.claude-dev\\settings\\cline_mcp_settings.json` | VS Code Cline Extension |
| **Roo Code** | `%APPDATA%\\Code\\User\\globalStorage\\rooveterinaryinc.roo-cline\\settings\\cline_mcp_settings.json` | VS Code Roo Extension |
| **Continue.dev** | `C:\\Users\\lenovo\\.continue\\config.json` | Continue Extension |
| **Zed Editor** | `C:\\Users\\lenovo\\.config\\zed\\settings.json` | Zed Editor |
| **VS Code Project**| `<workspace>\\.vscode\\mcp.json` | Local Project Workspace |
| **Standard MCP** | `<workspace>\\mcp.json` | Root Workspace |

---

## 5. Active Servers & Configured State (Baseline)

As of version 3.2, the user has 8 primary configured MCP servers across their agents:

1. **`stitch`**: Google Cloud Remote HTTP MCP (`https://stitch.googleapis.com/mcp`).
2. **`github`**: Official GitHub MCP (`@modelcontextprotocol/server-github` via Node).
3. **`excalidraw`**: Local Node MCP (`D:\\Tools & MCP\\Local\\excalidraw-mcp\\src\\cli.js`).
4. **`facebook-ads-library`**: Local Python FastMCP (`facebook_ads_mcp_complete.py`).
5. **`agent-reach`**: Local Python Module (`agent_reach.integrations.mcp_server`).
6. **`tinyfish`**: Remote Cloud HTTPS MCP.
7. **`scrapling`**: Local Web Scraping MCP (`scrapling.exe mcp`).
8. **`scrcpy-mcp`**: Local Android Screen & Device Controller (`scrcpy-mcp\\dist\\index.js`).

### Downloaded Repos on Disk (Unconfigured):
- `mcp-google-sheets` (`D:\\Tools & MCP\\Local\\mcp-google-sheets`)
- `ScrapGraphAI` (`D:\\Tools & MCP\\Local\\ScrapGraphAI`)
- `Use Browser` (`D:\\Tools & MCP\\Local\\Use Browser`)
- `Graphify` (`D:\\Tools & MCP\\Graphify`)

---

## 6. Process Management & Termination Guardrails

1. **Dual-Kill Execution**:
   - On Windows, `psutil.Process.kill()` frequently leaves detached grandchild processes (`node.exe` or `python.exe` workers spawned via `cmd.exe /c npx`).
   - The engine uses native Windows command:
     ```cmd
     taskkill /F /T /PID <pid>
     ```
     `/F` = Forcefully terminate.  
     `/T` = Terminate the entire process tree (all children and grandchildren).
2. **Pattern Sweep Fallback**:
   - In addition to matched PIDs, `kill_server()` sweeps active processes matching unambiguous server script names, verifying all workers exit.
3. **Safety Blacklist**:
   - Management scripts (`mcp_cli_manager`, `mcp-manager`, `mcp-status`) and system tools (`powershell`, `cmd`, `explorer`, `brave`, `chrome`) are explicitly excluded from termination sweeps.

---

## 7. Operational Guidelines for Future AI Agents

When modifying or extending this codebase, follow these rules:

1. **Maintain Sub-Second Execution**:
   - NEVER add synchronous network HTTP requests or open port probes to `get_snapshot()`.
   - Any active network scanning MUST reside in `deep_port_audit()` (`[P]`).
   - In `get_snapshot()`, always use name-first process filtering (`p.info['name'] in candidate_runners`) before calling `p.cmdline()`.
2. **Maintain Universal Config Sync**:
   - When adding a feature that disables, enables, or edits servers, update **all 14 agent locations in `CONFIG_TARGETS`** so configurations stay 100% in sync.
   - Always normalize server names using `canon_key()` to prevent discrepancies between `my-server`, `my_server`, and `my-server-mcp`.
3. **Protect Sensitive Secrets**:
   - In `inspect_server_details()`, all keys containing `token`, `key`, `secret`, `auth`, `pass`, `pat` MUST be masked with `mask_secret()`.
   - Never commit raw personal access tokens to GitHub; always sanitize `.git/config` after git operations.
4. **ANSI String Alignment**:
   - When computing column padding for tables and menus, ALWAYS use `len_visible()` and `pad_visible()`. Direct `len(s)` will count ANSI escape codes and break terminal box alignment.

---

## 8. File Structure in `C:\\Users\\lenovo\\Desktop\\MCP Manager`

```text
C:\Users\lenovo\Desktop\MCP Manager\
├── mcp_cli_manager.py     # Main Python 360° Engine (v3.2)
├── mcp-manager.bat        # Interactive Claude Code-styled launcher
├── mcp-status.bat         # Fast 1-second status snapshot launcher
├── context.md             # This full system context document
├── README.md              # Public documentation for GitHub
├── README.txt             # Quick-start instructions for double-clicking
└── .gitignore             # Git ignore rules
```

---
*Generated: September 2026 | MCP 360° Engine v3.2 | Divyanshu Aadi*
