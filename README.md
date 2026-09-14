# ✦ MCP 360° ENGINE (v3.6)
### Sub-Second Responsive UI, Toggleable Machine Repos, Zero-Residue Clean Uninstall & File Explorer Opener

A standalone, high-performance CLI utility for Windows styled after the **Claude Code CLI** (Anthropic Coral/Emerald palette, rounded box framing, and pixel-perfect ANSI alignment). 

Zero dependency on third-party daemon apps like MCP Router. Pure on-demand, non-blocking execution with sub-second response times.

---

## ⚡ What's New in v3.6: Machine Repos Toggle, Clean Uninstall & Explorer Opener

1. **Toggleable Local Machine Repos (`[T]`)**:
   - Easily switch between **`Full 360° View`** (showing both configured agent servers and unconfigured downloaded repos on disk) and **`Compact View`** (configured coding agent servers only).
   - Press **`[T]`** anytime in the CLI to toggle the view in `<0.3s`. Preferences are automatically saved in `.mcp_prefs.json`.
   - Downloaded repositories discovered on your disk (like `mcp-google-sheets`, `ScrapGraphAI`, `Use Browser`, `Graphify`) are seamlessly integrated into the table with `○ READY (D)` status so you can inspect, configure, or launch them directly.

2. **Clean Zero-Residue Uninstall (`[7]`)**:
   - In the Granular Control Menu for any server, choose **`[7] Clean Uninstall`**:
     1. Forcefully terminates any running worker processes and child trees (`taskkill /F /T`).
     2. Cleanly removes the server configuration from **all 14 agent config files** (`Antigravity IDE`, `Claude Code`, `Claude Global`, `Cursor`, `Windsurf`, etc.).
     3. Permanently wipes the project repository directory from disk, clearing read-only attributes on `.git` and virtualenvs with **zero residue left on the machine**.
   - Also available via CLI: `mcp-manager.bat uninstall <name>`.

3. **Open Server Folder in File Explorer (`[O]`)**:
   - Choose **`[O] Open Folder`** in the server menu to immediately launch Windows File Explorer directly to the server's repository or script path.
   - For remote cloud servers, opens the URL in your default browser.
   - Also available via CLI: `mcp-manager.bat open <name>`.

4. **Sub-Second Performance (<0.4s Refresh)**:
   - Replaced heavy blocking HTTP socket probes with instant PID-matched TCP socket resolution (`0.002s`).
   - Implemented name-first runtime process filtering (`0.3s`), reducing refresh and menu transition times from **10+ seconds down to sub-second** speeds.

5. **Bulletproof Multi-Agent Config Disabling & Lingering Process Detection**:
   - Universal synchronization across **all 14 agent config locations**.
   - If a server process is running while disabled in config, it is clearly flagged as `⊘ LINGERING` with active PIDs and RAM so you have 100% visibility.
   - Disabling a server forcefully terminates all child workers immediately.

---

## 💡 Architecture & Design: Evaluating Discovery Strategies

| Detection Strategy | Strengths | Critical Flaws / Blindspots |
| :--- | :--- | :--- |
| **Strategy A: Network Port Probing**<br>*(Scanning all open ports)* | Detects HTTP, SSE, FastMCP, and remote network-bound MCP servers regardless of how they were launched. | **Misses Stdio Servers**: The majority of local MCP servers (Claude, Cursor, Cline) communicate over `stdin`/`stdout` pipes and **never bind a TCP port**. |
| **Strategy B: Agent Config Harvester**<br>*(Reading `claude.json`, Cursor, etc.)* | Knows the exact launch commands, CLI arguments, and environment variables configured for each agent. | **The Unconfigured Server Flaw**: If you download, git-clone, or `pip/npm install` a new MCP server on your drive, but **have not yet added it** to an agent config file, it remains completely invisible. |
| **⭐ The 360° Hybrid Engine** | **Solves all blindspots**: Merges live Network Socket Probing + OS Stdio Process Tree Tracking + Machine Filesystem Discovery + Universal Multi-Agent Harvesting. | **Zero Blindspots**: Discovers active network sockets, running Stdio pipes, configured agent servers, and unconfigured local repos. Toggle between Full and Compact views with **`[T]`**. |

---

## 🎯 Granular Server Control Menu

Selecting any server by number (`1-N`) or name opens its dedicated control interface:

```text
╭─ Granular Control: mcp-google-sheets ───────────────────────────────────────────────╮
│  Status:       ○ READY (Local Repo on Disk)                                         │
│  Resources:    RAM Commit: 0.0 MB   |   CPU: 0.0%                                   │
│  Config Mode:  UNCONFIGURED (Downloaded to disk, not added to agent config)         │
│  Sources:      Local Disk                                                           │
│  Project Path: D:\Tools & MCP\Local\mcp-google-sheets                               │
│  Command:      (none - not configured)                                              │
╰─────────────────────────────────────────────────────────────────────────────────────╯

 Available Operations for [mcp-google-sheets]:
  [1] Start Server           - Spawn process if runnable script detected
  [2] Stop / Kill Server     - Forcefully terminate process & all child workers
  [3] Restart Server         - Terminate tree and immediately re-launch
  [4] Disable in Config      - Set 'disabled: true' across all agent configs & kill
  [5] Enable in Config       - Set 'disabled: false' across all agent configs
  [6] Inspect Full Details   - View args, masked env vars, full process tree
  [7] Clean Uninstall        - Wipe directory, remove configs & kill (Zero Residue)
  [O] Open Folder            - Open directory in Windows File Explorer
  [R] Refresh
- [F] **Repair Configs**: Auto-detects and repairs malformed agent JSON files with .bak backups. Status         - Re-query live PIDs and memory commit
  [B] Back to Overview       - Return to main server table
```

---

## 🚀 Usage

### Interactive Menu
Double-click **`mcp-manager.bat`**:

```text
╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│  ✦ MCP 360° ENGINE  v3.6 (Sub-Second UI & Universal Control)                                     ● FAST ENGINE ACTIVE  │
│  Universal Coding Agent Inspector & Process Controller                                                                 │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
 Coding Agents  : Antigravity IDE, Claude Code, Claude Desktop, Claude Global │ View: Full (4 Local Repos Included) [T]
 System RAM     : [████████░░] 86.9% (1.0 GB free of 7.7 GB)
 Total Memory   : 226.2 MB Commit Charge  │  3 Active / 12 Total Servers
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 #   Server Name              Status        Discovery Sources                           Port / PID      RAM Commit    CPU
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 01  stitch                   ✦ REMOTE      Antigravity IDE, Claude Code, Claude Global Cloud HTTPS          Cloud    N/A
 02  github                   ● RUNNING     Antigravity IDE, Claude Code, Claude Global PID 19004+3       109.6 MB   0.0%
 03  excalidraw               ○ READY       Antigravity IDE, Claude Code, Claude Global ─                   0.0 MB   0.0%
 04  facebook-ads-library     ● RUNNING     Antigravity IDE, Claude Code, Claude Global PID 12404+1        69.5 MB   0.0%
 05  agent-reach              ● RUNNING     Antigravity IDE, Claude Code, Claude Global PID 1712+1         47.1 MB   0.0%
 06  tinyfish                 ✦ REMOTE      Antigravity IDE, Claude Code                Cloud HTTPS          Cloud    N/A
 07  scrapling                ○ READY       Antigravity IDE, Claude Code                ─                   0.0 MB   0.0%
 08  scrcpy-mcp               ⊘ DISABLED    Antigravity IDE, Claude Code, Claude Global ─                   0.0 MB   0.0%
 09  mcp-google-sheets        ○ READY (D)   Local Disk (D:\Tools & MCP\Local)           ─                   0.0 MB   0.0%
 10  ScrapGraphAI             ○ READY (D)   Local Disk (D:\Tools & MCP\Local)           ─                   0.0 MB   0.0%
 11  Use Browser              ○ READY (D)   Local Disk (D:\Tools & MCP\Local)           ─                   0.0 MB   0.0%
 12  Graphify                 ○ READY (D)   Local Disk (D:\Tools & MCP)                 ─                   0.0 MB   0.0%
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Tip: Enter server # (01-12) or name to open Granular Control Menu.

╭─ Actions & Shortcuts ─────────────────────────────────────────────────────────────────────────────────────────────────╮
│  [1-N] Select Server    [T] Toggle (Hide Repos)    [K] Kill All    [S] Start All    [P] Ports    [R] Refresh
- [F] **Repair Configs**: Auto-detects and repairs malformed agent JSON files with .bak backups.    [Q] Quit  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Quick Status
Double-click **`mcp-status.bat`** for a fast sub-second status table of all MCP servers and RAM usage.

### CLI Commands
Run directly from PowerShell or Command Prompt:
```cmd
mcp-manager.bat status           # Sub-second status snapshot
mcp-manager.bat toggle           # Toggle between Full and Compact views
mcp-manager.bat select <name>    # Open granular menu for server directly
mcp-manager.bat open <name>      # Open server directory in Windows File Explorer
mcp-manager.bat uninstall <name> # Clean zero-residue uninstall of server
mcp-manager.bat restart <name>   # Restart specific server process tree
mcp-manager.bat inspect <name>   # Show detailed diagnostics & process hierarchy
mcp-manager.bat disable <name>   # Disable server in all configs & kill process tree
mcp-manager.bat enable <name>    # Enable server across all agent configs
mcp-manager.bat kill <name>      # Kill specific server process tree
mcp-manager.bat kill-all         # Kill all running MCP servers
mcp-manager.bat start <name>     # Start specific server
mcp-manager.bat ports            # Deep system-wide port & socket audit
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
