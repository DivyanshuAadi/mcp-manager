# ✦ MCP 360° ENGINE (v3.2)
### Sub-Second Responsive UI, Universal Multi-Agent Disabling & Surgical Process Tree Termination

A standalone, high-performance CLI utility for Windows styled after the **Claude Code CLI** (Anthropic Coral/Emerald palette, rounded box framing, and pixel-perfect ANSI alignment). 

Zero dependency on third-party daemon apps like MCP Router. Pure on-demand, non-blocking execution with sub-second response times.

---

## ⚡ What's New in v3.2: Sub-Second Performance & Bulletproof Disabling

1. **Sub-Second Real-Time Response (<0.4s Refresh)**:
   - Replaced heavy blocking HTTP JSON-RPC socket probes on every keystroke with instant PID-matched TCP socket resolution (`0.002s`).
   - Implemented name-first runtime process filtering (`0.3s`), reducing refresh and menu transition times from **10+ seconds down to sub-second** speeds.
   - Reduced artificial menu wait timers from 1.6s to 0.4s for snappy, immediate user interactions.

2. **Bulletproof Multi-Agent Config Disabling & Enabling**:
   - Universal synchronization across **all 14 agent config locations**:
     - **Antigravity IDE / Gemini** (`~/.gemini/config/mcp_config.json`)
     - **Claude Code** (`~/.claude.json`)
     - **Claude Global** (`~/.claude/mcp.json`)
     - **Claude Desktop** (`claude_desktop_config.json`)
     - **Cursor & Cursor Global** (`~/.cursor/mcp.json`, global storage)
     - **Windsurf & Windsurf User** (`~/.codeium/windsurf/mcp_config.json`)
     - **Cline & Roo Code** (`cline_mcp_settings.json`)
     - **Continue.dev** (`~/.continue/config.json`)
     - **Zed Editor** (`~/.config/zed/settings.json`)
     - **VS Code Workspace** (`.vscode/mcp.json`, `mcp.json`)
   - Symmetric canonical name resolution (`canon_key`) ensures consistent matching regardless of dashes, underscores, or `-mcp` suffixes.
   - When disabling a server, its entire process tree is **forcefully terminated immediately** so no orphaned Node or Python workers linger in RAM.

3. **Zero False-Positive Process Matching**:
   - Banned generic directory words (`dist`, `src`, `lib`, `build`, `node_modules`) from acting as standalone substring search patterns.
   - Restricts process candidates strictly to recognized language runtimes (`node.exe`, `python.exe`, `scrapling.exe`, `uvx.exe`, etc.) and configured server binaries, preventing false matches against browsers (Brave, Chrome) or OS utilities.

4. **Clean Active Server Table vs. Downloaded Repos on Disk**:
   - Removed phantom servers and indiscriminate cache entries from the primary active table.
   - Downloaded repositories not yet added to any agent config are accessible via **`[U] Downloaded Repos on Disk`**.

5. **Full Dynamic Column Expansion**:
   - The `Discovery Sources` column dynamically sizes to fit all active agent names without text truncation.

---

## 💡 Architecture & Design: Evaluating Discovery Strategies

| Detection Strategy | Strengths | Critical Flaws / Blindspots |
| :--- | :--- | :--- |
| **Strategy A: Network Port Probing**<br>*(Scanning all open ports)* | Detects HTTP, SSE, FastMCP, and remote network-bound MCP servers regardless of how they were launched. | **Misses Stdio Servers**: The majority of local MCP servers (Claude, Cursor, Cline) communicate over `stdin`/`stdout` pipes and **never bind a TCP port**. |
| **Strategy B: Agent Config Harvester**<br>*(Reading `claude.json`, Cursor, etc.)* | Knows the exact launch commands, CLI arguments, and environment variables configured for each agent. | **The Unconfigured Server Flaw**: If you download, git-clone, or `pip/npm install` a new MCP server on your drive, but **have not yet added it** to an agent config file, it remains completely invisible. |
| **⭐ The 360° Hybrid Engine** | **Solves all blindspots**: Merges live Network Socket Probing + OS Stdio Process Tree Tracking + Machine Filesystem Discovery + Universal Multi-Agent Harvesting. | **Zero Blindspots**: Discovers active network sockets, running Stdio pipes, configured agent servers, and unconfigured local repos. |

---

## 🎯 Granular Server Control Menu

Selecting any server by number (`1-N`) or name opens its dedicated control interface:

```text
╭─ Granular Control: github ───────────────────────────────────────────────────────────╮
│  Status:       ● RUNNING  (PIDs: [19004, 27276])                                     │
│  Resources:    RAM Commit: 109.6 MB   |   CPU: 0.0%                                  │
│  Config Mode:  ACTIVE (Enabled)                                                      │
│  Sources:      Antigravity IDE, Claude Code, Claude Global                           │
│  Command:      node C:\Users\...\server-github\dist\index.js                    │
╰──────────────────────────────────────────────────────────────────────────────────────╯

 Available Operations for [github]:
  [1] Start Server           - Spawn process if currently stopped
  [2] Stop / Kill Server     - Forcefully terminate process & all child workers
  [3] Restart Server         - Terminate tree and immediately re-launch
  [4] Disable in Config      - Set 'disabled: true' across all agent configs & kill
  [5] Enable in Config       - Set 'disabled: false' across all agent configs
  [6] Inspect Full Details   - View args, masked env vars, full process tree
  [R] Refresh Status         - Re-query live PIDs and memory commit
  [B] Back to Overview       - Return to main server table
```

---

## 🚀 Usage

### Interactive Menu
Double-click **`mcp-manager.bat`**:

```text
╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│  ✦ MCP 360° ENGINE  v3.2 (Sub-Second UI & Universal Control)                                     ● FAST ENGINE ACTIVE  │
│  Universal Coding Agent Inspector & Process Controller                                                                 │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
 Coding Agents  : Antigravity IDE, Claude Code, Claude Desktop, Claude Global │ 4 Downloaded Repos on Disk [U]
 System RAM     : [████████░░] 86.9% (1.0 GB free of 7.7 GB)
 Total Memory   : 226.2 MB Commit Charge  │  3 Active / 8 Total Servers
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
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Tip: Enter server # (01-08) or name to open Granular Control Menu.

╭─ Actions & Shortcuts ─────────────────────────────────────────────────────────────────────────────────────────────────╮
│  [1-N] Select Server    [U] Local Repos (4)    [K] Kill All    [S] Start All    [P] Ports    [R] Refresh    [Q] Quit   │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Quick Status
Double-click **`mcp-status.bat`** for a fast sub-second status table of all MCP servers and RAM usage.

### CLI Commands
Run directly from PowerShell or Command Prompt:
```cmd
mcp-manager.bat status          # Sub-second status snapshot
mcp-manager.bat select <name>   # Open granular menu for server directly
mcp-manager.bat restart <name>  # Restart specific server process tree
mcp-manager.bat inspect <name>  # Show detailed diagnostics & process hierarchy
mcp-manager.bat disable <name>  # Disable server in all configs & kill process tree
mcp-manager.bat enable <name>   # Enable server across all agent configs
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
