✦ MCP 360° ENGINE (v3.0)
===========================

Double-click to use:
1. mcp-manager.bat  -> Interactive Claude-styled menu to see status, start, or kill servers.
2. mcp-status.bat   -> Quick 1-second status table of all running MCP servers and RAM usage.

Key Capabilities:
- Full-System Network Port Prober: Scans all listening TCP ports on the machine.
- Stdio Process Inspector: Monitors CPU and Windows Commit RAM for active processes.
- Machine Filesystem Discovery: Discovers unconfigured MCP repos on your drive (e.g. D:\Tools & MCP).
- Universal Agent Harvester: Auto-detects servers in Claude Code, Claude Desktop, Cursor, Windsurf, Cline, etc.

Interactive Shortcuts (inside mcp-manager.bat):
- [1-N] : Toggle Server (Start / Stop)
- [K]   : Kill All Running MCP Servers
- [S]   : Start All Stopped Servers
- [P]   : Deep Port Audit (view every open port on host)
- [R]   : Refresh
- [Q]   : Quit

CLI Usage:
- mcp-manager.bat status
- mcp-manager.bat ports
- mcp-manager.bat kill <name>
- mcp-manager.bat start <name>
- mcp-manager.bat kill-all
