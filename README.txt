MCP Servers Manager
===================

Double-click to use:
1. mcp-manager.bat  -> Interactive menu to see status, start, or kill servers.
2. mcp-status.bat   -> Quick 1-second status table of all running MCP servers and RAM usage.

Command Line Usage (from CMD or PowerShell):
- mcp-manager.bat status       (View status table once)
- mcp-manager.bat kill <name>  (Kill specific server)
- mcp-manager.bat kill-all     (Kill all running MCP servers)
- mcp-manager.bat start <name> (Start specific server)

Auto-Detection:
- Automatically detects servers from MCP Router (mcprouter.db).
- Automatically detects servers from Claude configs (~/.claude.json, Claude Desktop).
- Automatically detects any other ad-hoc running MCP server process on your system.
