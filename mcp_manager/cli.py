# -*- coding: utf-8 -*-
"""CLI argument dispatcher and execution entry point."""
from __future__ import annotations
import sys
from .constants import RED, RESET
from .utils import load_prefs, save_prefs, normalize_server_key
from .snapshot import get_snapshot
from .ui import render_cli, deep_port_audit, inspect_server_details, server_control_menu, interactive_loop
from .config import run_config_repair, toggle_disable_server
from .process import kill_all_servers, kill_server, start_server, restart_server
from .repos import open_server_location, uninstall_server

def main() -> None:
    prefs = load_prefs()
    show_local_repos = prefs.get("show_local_repos", True)

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        data = get_snapshot(show_local_repos=show_local_repos)

        if cmd == "status":
            render_cli(data)
        elif cmd == "ports":
            deep_port_audit(data, interactive=False)
        elif cmd in ("toggle", "view"):
            if len(sys.argv) > 2:
                sub = sys.argv[2].lower()
                show_local_repos = sub in ("full", "all", "1", "true", "on")
            else:
                show_local_repos = not show_local_repos
            prefs["show_local_repos"] = show_local_repos
            save_prefs(prefs)
            mode_name = "FULL" if show_local_repos else "COMPACT"
            print(f"View mode set to: {mode_name}")
            data = get_snapshot(show_local_repos=show_local_repos)
            render_cli(data)
        elif cmd == "repair":
            run_config_repair()
        elif cmd == "kill-all":
            killed = kill_all_servers(data["servers"])
            print(f"Killed {len(killed)} process(es): {killed}")
        elif cmd in ("select", "control", "manage") and len(sys.argv) > 2:
            server_control_menu(sys.argv[2])
        elif cmd in ("open", "folder", "uninstall", "remove", "delete", "restart", "inspect", "info", "kill", "start", "disable", "enable") and len(sys.argv) > 2:
            target = sys.argv[2]
            target_key = normalize_server_key(target)
            s = next((x for x in data["servers"] if normalize_server_key(x["name"]) == target_key), None)
            if not s:
                s = next((x for x in data["servers"] if target_key in normalize_server_key(x["name"])), None)

            if not s:
                print(f"{RED}Server '{target}' not found.{RESET}")
            elif cmd in ("open", "folder"):
                open_server_location(s)
            elif cmd in ("uninstall", "remove", "delete"):
                uninstall_server(s)
            elif cmd == "restart":
                restart_server(s)
            elif cmd in ("inspect", "info"):
                inspect_server_details(s, interactive=False)
            elif cmd == "kill":
                killed = kill_server(s)
                print(f"Killed '{s['name']}' (PIDs: {killed})")
            elif cmd == "start":
                pid = start_server(s)
                print(f"Started '{s['name']}' (PID {pid})")
            elif cmd == "disable":
                toggle_disable_server(s, force_state=True)
            elif cmd == "enable":
                toggle_disable_server(s, force_state=False)
        else:
            print("Usage:")
            print("  mcp-manager                 (Interactive menu)")
            print("  mcp-manager status          (Show table once)")
            print("  mcp-manager toggle [full|compact]")
            print("  mcp-manager repair          (Auto-repair all agent configs)")
            print("  mcp-manager ports           (Deep port audit)")
            print("  mcp-manager select <name>   (Granular control)")
            print("  mcp-manager open <name>")
            print("  mcp-manager uninstall <name>")
            print("  mcp-manager restart|kill|start|disable|enable|inspect <name>")
            print("  mcp-manager kill-all")
    else:
        interactive_loop()

if __name__ == "__main__":
    main()
