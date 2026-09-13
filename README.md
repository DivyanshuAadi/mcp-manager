# ✦ MCP 360° ENGINE (v3.1)
### Full-System Network Port Prober, Stdio Tree-Killer & Universal Machine Harvester

A standalone, high-performance CLI utility for Windows styled after the **Claude Code CLI** (Anthropic Coral/Emerald palette, rounded box framing, and pixel-perfect ANSI alignment). 

Zero dependency on third-party daemon apps like MCP Router. Pure on-demand, non-blocking execution.

---

## ⚡ Why Do MCP Servers Auto-Start? (Kill vs. Disable)

When working with modern AI IDEs (Antigravity IDE, Cursor, Windsurf) and CLI agents (Claude Code, Cline), you may notice that after you terminate an MCP process, **it suddenly starts right back up**.

### Understanding Process Supervisors
1. **Background Supervisors**:
   - IDEs run background language servers and process supervisors (e.g. `language_server_windows_x64.exe` or `claude.exe`).
   - When a conversation turn begins or when tools are loaded, the supervisor checks configured MCP servers in `mcp_config.json` or `~/.claude.json`.
   - If an enabled server's pipe closes or is terminated, the supervisor's auto-reconnect logic **resurrects the server**!
2. **Orphaned Process Trees**:
   - Servers launched via NPX (like `@modelcontextprotocol/server-github`) spawn nested process hierarchies (`cmd.exe` ➔ `node.exe` ➔ `cmd.exe` ➔ `node.exe`).
   - Standard kill commands often terminate only the outer wrapper, leaving the internal Node worker running and consuming 170–250 MB RAM.

### The Solution in v3.1:
- **Tree-Kill Engine**: Employs native Windows `taskkill /F /T /PID` to terminate the entire process tree recursively, leaving zero orphaned workers.
- **`[D]` Disable / Enable Toggle**:
  - Toggling **Disable** writes `"disabled": true` directly into the agent's config (`mcp_config.json`, `.claude.json`, Cursor, etc.) and immediately terminates the process tree.
  - **Because it is marked disabled, the IDE supervisor will NEVER automatically resurrect it!**
  - Toggling **Enable** restores it so you can use it again whenever you wish.

---

## 💡 Architecture & Design: Evaluating Discovery Strategies

| Detection Strategy | Strengths | Critical Flaws / Blindspots |
| :--- | :--- | :--- |
| **Strategy A: Network Port Probing**<br>*(Scanning all open ports)* | Detects HTTP, SSE, FastMCP, and remote network-bound MCP servers regardless of how they were launched. | **Misses Stdio Servers**: The majority of local MCP servers (Claude, Cursor, Cline) communicate over `stdin`/`stdout` pipes and **never bind a TCP port**. |
| **Strategy B: Agent Config Harvester**<br>*(Reading `claude.json`, Cursor, etc.)* | Knows the exact launch commands, CLI arguments, and environment variables configured for each agent. | **The Unconfigured Server Flaw**: If you download, git-clone, or `pip/npm install` a new MCP server on your drive (e.g. `D:\Tools & MCP\Local\mcp-google-sheets`), but **have not yet added it** to an agent config file, it remains completely invisible. |
| **⭐ The v3.1 360° Hybrid Engine** | **Solves all blindspots**: Merges live Network Socket Probing + OS Stdio Process Tree Tracking + Machine Filesystem Discovery + Universal Multi-Agent Harvesting. | **Zero Blindspots**: Discovers active network sockets, running Stdio pipes, configured agent servers, and unconfigured local repos. |

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
 Total Memory   : 557.5 MB Commit Charge  │  1 Active / 15 Total Servers
 Active Ports   : :51560 (Antigravity IDE.exe / PID 16484) │ :53826 (PID 7636) (43 sockets)
──────────────────────────────────────────────────────────────────────────────────────────────
 #   Server Name              Status      Discovery Source     Port / PID     RAM Commit    CPU
──────────────────────────────────────────────────────────────────────────────────────────────
 01  mcp-google-sheets        ○ READY     Local Disk           ─                  0.0 MB   0.0%
 02  ScrapGraphAI             ○ READY     Local Disk           ─                  0.0 MB   0.0%
 03  Use Browser              ○ READY     Local Disk           ─                  0.0 MB   0.0%
 04  Graphify                 ○ READY     Local Disk           ─                  0.0 MB   0.0%
 05  chrome-devtools-mcp      ○ READY     NPX Cache            ─                  0.0 MB   0.0%
 06  @modelcontextprotocol    ○ READY     NPX Cache            ─                  0.0 MB   0.0%
 07  stitch                   ✦ REMOTE    Antigravity IDE, Cla Cloud HTTPS         Cloud    N/A
 08  github                   ⊘ DISABLED  Antigravity IDE, Cla ─                  0.0 MB   0.0%
 09  excalidraw               ⊘ DISABLED  Local Disk, Antigrav ─                  0.0 MB   0.0%
 10  facebook-ads-library     ⊘ DISABLED  Local Disk, Antigrav ─                  0.0 MB   0.0%
 11  agent-reach              ⊘ DISABLED  Local Disk, Antigrav ─                  0.0 MB   0.0%
 12  tinyfish                 ✦ REMOTE    Antigravity IDE, Cla Cloud HTTPS         Cloud    N/A
 13  scrapling                ⊘ DISABLED  Local Disk, Antigrav ─                  0.0 MB   0.0%
 14  scrcpy-mcp               ● RUNNING   Local Disk, Antigrav PID 932+11       557.5 MB   0.0%
 15  mcp-router               ○ READY     Claude Desktop       ─                  0.0 MB   0.0%
──────────────────────────────────────────────────────────────────────────────────────────────
Tip: If a server auto-starts when using an IDE or agent, use [D] to Disable it in config.

╭─ Actions & Shortcuts ─────────────────────────────────────────────────────────────────────╮
│  [1-N] Toggle    [D] Disable/Enable    [K] Kill All    [S] Start    [P] Ports    [Q] Quit  │
╰───────────────────────────────────────────────────────────────────────────────────────────╯
```

- **`[1-N]`** : Toggle individual server (Starts if stopped, Kills process tree if running).
- **`[D]`** : **Disable / Enable Server in Config** — Prevents supervisors from auto-starting the server.
- **`[K]`** : Kill all active MCP servers immediately.
- **`[S]`** : Start all stopped local MCP servers (that are not disabled).
- **`[P]`** : Deep port scan & protocol probe of every listening TCP socket on the system.
- **`[R]`** : Instant refresh and re-scan.
- **`[Q]`** : Quit.

### Quick Status
Double-click **`mcp-status.bat`** for a fast 1-second system status table.

### CLI Commands
Run directly from PowerShell or Command Prompt:
```cmd
mcp-manager.bat status          # 1-second status snapshot
mcp-manager.bat ports           # Deep system-wide port & socket audit
mcp-manager.bat disable <name>  # Permanently disable server in configs & kill process
mcp-manager.bat enable <name>   # Re-enable server in configs
mcp-manager.bat kill <name>     # Kill server process tree
mcp-manager.bat start <name>    # Start server process
mcp-manager.bat kill-all        # Kill all running MCP servers
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
