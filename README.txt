✦ MCP 360° ENGINE (v3.3)
===========================

Double-click to use:
1. mcp-manager.bat  -> Interactive Claude-styled menu with Granular Server Control.
2. mcp-status.bat   -> Quick sub-second status table of all running MCP servers and RAM usage.

What's New in v3.3:
- Toggleable Local Repos [T]: Switch between Full View (Configured + Downloaded Repos) and Compact View.
- Clean Zero-Residue Uninstall [7]: Force kill, remove from all agent configs, and wipe disk directory.
- Open Folder [O]: Open server folder directly in Windows File Explorer.
- Sub-Second Performance (<0.4s): Fast PID-to-port mapping and candidate process filtering.
- Lingering Process Transparency: Clearly flags processes running despite disabled config.

Granular Control Menu:
  [1] Start Server
  [2] Stop / Kill Server (force process tree kill)
  [3] Restart Server (clean tree-kill + fresh spawn)
  [4] Disable in Config (blocks supervisor auto-restart)
  [5] Enable in Config
  [6] Inspect Full Details (args, masked env vars, process tree)
  [7] Clean Uninstall (Zero-Residue Wipe)
  [O] Open Folder in Explorer
  [R] Refresh Status
  [B] Back to Overview Table

Main Table Shortcuts:
- [1-N] : Select Server to open its Granular Control Menu
- [T]   : Toggle View (Full / Compact)
- [K]   : Kill All Running MCP Servers
- [S]   : Start All Stopped Servers
- [P]   : Deep Port Audit (view every open port on host)
- [R]   : Refresh
- [Q]   : Quit

CLI Usage:
- mcp-manager.bat status
- mcp-manager.bat toggle
- mcp-manager.bat select <name>
- mcp-manager.bat open <name>
- mcp-manager.bat uninstall <name>
- mcp-manager.bat restart <name>
- mcp-manager.bat inspect <name>
- mcp-manager.bat disable <name>
- mcp-manager.bat enable <name>
- mcp-manager.bat kill <name>
- mcp-manager.bat start <name>
- mcp-manager.bat kill-all
- mcp-manager.bat ports
