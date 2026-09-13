✦ MCP 360° ENGINE (v3.1)
===========================

Double-click to use:
1. mcp-manager.bat  -> Interactive Claude-styled menu with Granular Server Control.
2. mcp-status.bat   -> Quick 1-second status table of all running MCP servers and RAM usage.

What's New in v3.1:
- Granular Control Menu: Select any server by # (1-N) or name to open dedicated operations:
  [1] Start Server
  [2] Stop / Kill Server (force process tree kill)
  [3] Restart Server (clean tree-kill + fresh spawn)
  [4] Disable in Config (blocks supervisor auto-restart)
  [5] Enable in Config
  [6] Inspect Full Details (args, masked env vars, process tree)
  [R] Refresh Status
  [B] Back to Overview Table

Main Table Shortcuts:
- [1-N] : Select Server to open its Granular Control Menu
- [K]   : Kill All Running MCP Servers
- [S]   : Start All Stopped Servers
- [P]   : Deep Port Audit (view every open port on host)
- [R]   : Refresh
- [Q]   : Quit

CLI Usage:
- mcp-manager.bat status
- mcp-manager.bat select <name>
- mcp-manager.bat restart <name>
- mcp-manager.bat inspect <name>
- mcp-manager.bat disable <name>
- mcp-manager.bat enable <name>
- mcp-manager.bat kill <name>
- mcp-manager.bat start <name>
- mcp-manager.bat kill-all
- mcp-manager.bat ports
