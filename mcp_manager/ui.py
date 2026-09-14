# -*- coding: utf-8 -*-
"""Terminal rendering, ANSI tables, granular control menu, and interactive loop."""
from __future__ import annotations
import os
import sys
import time
from typing import Any
from .constants import (
    VERSION, PLATFORM, CORAL, AMBER, GREEN, CYAN, INDIGO, WHITE, GRAY,
    DARK_GRAY, RED, YELLOW, DIM, BOLD, RESET
)
from .utils import pad_visible, normalize_server_key, load_prefs, save_prefs, mask_secret
from .snapshot import get_snapshot
from .health import get_mcp_listening_ports, probe_mcp_http
from .config import run_config_repair, toggle_disable_server
from .process import kill_server, kill_all_servers, restart_server, start_server
from .repos import open_server_location, uninstall_server

def render_cli(data: dict[str, Any]) -> None:
    """Render full ANSI terminal dashboard."""
    os.system("cls" if os.name == "nt" else "clear")

    print(f"{CORAL}╭{'─' * 120}╮{RESET}")
    title = f"  ✦ MCP 360° ENGINE  {VERSION} "
    badge = f"{GREEN}● FAST ENGINE ACTIVE  {RESET}"
    pad_title = 120 - len(title) - 22
    print(f"{CORAL}│{RESET}{BOLD}{WHITE}{title}{RESET}{' ' * max(0, pad_title)}{badge}{CORAL}│{RESET}")
    sub = f"  Universal Coding Agent Inspector & Process Controller ({PLATFORM})"
    print(f"{CORAL}│{RESET}{DIM}{sub}{' ' * (120 - len(sub))}{RESET}{CORAL}│{RESET}")
    print(f"{CORAL}╰{'─' * 120}╯{RESET}")

    agents_str = ", ".join(data.get("agents", [])) or "None detected"
    if len(agents_str) > 75:
        agents_str = agents_str[:72] + "..."
    mode_str = f"View: {'Full (' + str(data.get('unconfigured_count', 0)) + ' Local Repos Included) [T]' if data.get('view_mode') == 'full' else 'Compact (Configured Only) [T]'}"

    print(f" {BOLD}Coding Agents  :{RESET} {CYAN}{agents_str}{RESET} │ {DIM}{mode_str}{RESET}")

    ram_pct = data["ram_percent"]
    blocks = int(ram_pct // 10)
    bar = f"{AMBER}{'█' * blocks}{DARK_GRAY}{'░' * (10 - blocks)}{RESET}"
    print(f" {BOLD}System RAM     :{RESET} [{bar}] {BOLD}{ram_pct}%{RESET} ({data['ram_free_gb']} GB free of {data['ram_total_gb']} GB)")

    total_mem = data["total_commit_mb"]
    active = data["active_count"]
    total = data["total_count"]
    print(f" {BOLD}Total Memory   :{RESET} {GREEN}{BOLD}{total_mem} MB{RESET} Commit Charge  │  {CYAN}{active} Active / {total} Total Servers{RESET}")

    print(f"{DARK_GRAY}{'─' * 122}{RESET}")
    h_num = " #"
    h_name = "Server Name"
    h_stat = "Status"
    h_src = "Discovery Sources"
    h_pid = "Port / PID"
    h_ram = "RAM Commit"
    h_cpu = "CPU"
    header_line = (
        f"{BOLD}{h_num:<4} {h_name:<24} {h_stat:<13} {h_src:<43} {h_pid:<15} {h_ram:>10} {h_cpu:>6}{RESET}"
    )
    print(header_line)
    print(f"{DARK_GRAY}{'─' * 122}{RESET}")

    for s in data["servers"]:
        num = f"{s['num']:02d}"
        name = s["name"]
        if len(name) > 23:
            name = name[:20] + "..."

        status = s["status"]
        if status == "ONLINE":
            status_badge = f"{CYAN}✦ ONLINE    {RESET}"
        elif status == "DEGRADED":
            status_badge = f"{YELLOW}⚠ DEGRADED  {RESET}"
        elif status == "OFFLINE":
            status_badge = f"{RED}✗ OFFLINE   {RESET}"
        elif status == "DISABLED (RUNNING)":
            status_badge = f"{CORAL}⊘ LINGERING {RESET}"
        elif status == "DISABLED":
            status_badge = f"{YELLOW}⊘ DISABLED  {RESET}"
        elif status == "RUNNING":
            status_badge = f"{GREEN}● RUNNING   {RESET}"
        elif status == "READY":
            status_badge = f"{WHITE}○ READY     {RESET}"
        elif "READY (D)" in status:
            status_badge = f"{GRAY}○ READY (D) {RESET}"
        elif "CACHED" in status:
            status_badge = f"{GRAY}○ CACHED (D){RESET}"
        else:
            status_badge = f"{DIM}? UNKNOWN   {RESET}"

        src_str = ", ".join(s.get("sources", [])) if isinstance(s.get("sources"), list) else s.get("source", "")
        if len(src_str) > 42:
            src_str = src_str[:39] + "..."

        pids = s.get("pids", [])
        if s["type"] == "remote":
            pid_str = f"{DIM}Cloud HTTPS{RESET}"
        elif pids:
            if len(pids) == 1:
                pid_str = f"PID {pids[0]}"
            else:
                pid_str = f"PID {pids[0]}+{len(pids)-1}"
        else:
            pid_str = f"{DARK_GRAY}─{RESET}"

        if s["type"] == "remote":
            ram_str = f"{DIM}Cloud{RESET}"
            cpu_str = f"{DIM}N/A{RESET}"
        else:
            ram_str = f"{s['commit_mb']:.1f} MB" if s["commit_mb"] > 0 else f"{DARK_GRAY}0.0 MB{RESET}"
            cpu_str = f"{s['cpu']:.1f}%" if s["cpu"] > 0 else f"{DARK_GRAY}0.0%{RESET}"

        row = (
            f" {DIM}{num}{RESET}  "
            f"{BOLD}{WHITE}{pad_visible(name, 23)}{RESET} "
            f"{status_badge} "
            f"{GRAY}{pad_visible(src_str, 43)}{RESET} "
            f"{pad_visible(pid_str, 15)} "
            f"{pad_visible(ram_str, 10, align='right')} "
            f"{pad_visible(cpu_str, 6, align='right')}"
        )
        print(row)

    print(f"{DARK_GRAY}{'─' * 122}{RESET}")
    print(f"{DIM}Tip: Enter server # (01-{data['total_count']:02d}) or name to open Granular Control Menu.{RESET}\n")

    actions_bar = (
        f"{CORAL}╭─ Actions & Shortcuts {'─' * 98}╮{RESET}\n"
        f"{CORAL}│{RESET}  {AMBER}[1-N]{RESET} Select    "
        f"{CYAN}[T]{RESET} Toggle (Hide Repos)    "
        f"{RED}[K]{RESET} Kill All    "
        f"{GREEN}[S]{RESET} Start All    "
        f"{CYAN}[P]{RESET} Ports    "
        f"{AMBER}[R]{RESET} Refresh    "
        f"{GREEN}[F]{RESET} Repair    "
        f"{DIM}[Q]{RESET} Quit  {CORAL}│{RESET}\n"
        f"{CORAL}╰{'─' * 121}╯{RESET}"
    )
    print(actions_bar)

def deep_port_audit(data: dict[str, Any], interactive: bool = True) -> None:
    """Scan all active TCP listening sockets and identify MCP endpoints."""
    print(f"\n{BOLD}Scanning system network ports for MCP / HTTP / SSE listeners...{RESET}")
    ports = get_mcp_listening_ports()
    if not ports:
        print(f"{GRAY}No non-system listening TCP ports found.{RESET}\n")
        if interactive:
            input(f"{DIM}Press Enter to return...{RESET}")
        return

    print(f"\n{BOLD}{'Port':<8} {'Address':<18} {'PID':<8} {'Process':<18} {'MCP Probe Result'}{RESET}")
    print(f"{DARK_GRAY}{'─' * 80}{RESET}")
    for p in ports:
        ip = p["ip"]
        port = p["port"]
        pid_str = str(p["pid"]) if p["pid"] else "-"
        pname = p["process_name"] or "-"
        is_mcp, clue = probe_mcp_http(ip, port, timeout=0.12)
        status_str = f"{GREEN}● MCP Active ({clue}){RESET}" if is_mcp else f"{DIM}Not MCP (Standard TCP){RESET}"
        print(f"{CYAN}{port:<8}{RESET} {ip:<18} {pid_str:<8} {pname:<18} {status_str}")
    print(f"{DARK_GRAY}{'─' * 80}{RESET}\n")
    if interactive:
        input(f"{DIM}Press Enter to return to overview...{RESET}")

def inspect_server_details(server: dict[str, Any], interactive: bool = True) -> None:
    """Display deep diagnostic information, arguments, and process tree."""
    os.system("cls" if os.name == "nt" else "clear")
    print(f"\n{CORAL}╭─ Deep Diagnostics: {server['name']} {'─' * (60 - len(server['name']))}╮{RESET}")
    print(f"{CORAL}│{RESET}  {BOLD}Name:{RESET}         {WHITE}{server['name']}{RESET}")
    print(f"{CORAL}│{RESET}  {BOLD}Status:{RESET}       {server['status']}")
    print(f"{CORAL}│{RESET}  {BOLD}Type:{RESET}         {server['type']}")
    print(f"{CORAL}│{RESET}  {BOLD}Config Mode:{RESET}  {'DISABLED' if server['disabled'] else 'ACTIVE'}")
    print(f"{CORAL}│{RESET}  {BOLD}RAM Commit:{RESET}   {server['commit_mb']} MB")
    print(f"{CORAL}│{RESET}  {BOLD}CPU Usage:{RESET}    {server['cpu']}%")

    pids_str = ", ".join(map(str, server.get("pids", []))) or "(none)"
    print(f"{CORAL}│{RESET}  {BOLD}Active PIDs:{RESET}  {pids_str}")

    cmd_val = server.get("command")
    args = server.get("args") or []
    cmd_full = (str(cmd_val) if cmd_val else "") + " " + " ".join(str(a) for a in args)
    print(f"{CORAL}│{RESET}  {BOLD}Command:{RESET}      {cmd_full.strip() or '(none - remote or repo)'}")

    if server.get("url"):
        print(f"{CORAL}│{RESET}  {BOLD}URL:{RESET}          {server['url']}")
    if server.get("path"):
        print(f"{CORAL}│{RESET}  {BOLD}Local Path:{RESET}   {server['path']}")

    env = server.get("env") or {}
    if env:
        print(f"{CORAL}│{RESET}  {BOLD}Env Variables:{RESET}")
        for k, v in env.items():
            print(f"{CORAL}│{RESET}    • {k} = {mask_secret(v)}")

    print(f"{CORAL}╰{'─' * 80}╯{RESET}\n")
    if interactive:
        input(f"{DIM}Press Enter to return to menu...{RESET}")

def server_control_menu(server_query: str) -> None:
    """Interactive granular control screen for a single server."""
    while True:
        data = get_snapshot()
        target = normalize_server_key(server_query)
        s = next((x for x in data["servers"] if normalize_server_key(x["name"]) == target), None)
        if not s:
            s = next((x for x in data["servers"] if target in normalize_server_key(x["name"])), None)

        if not s:
            print(f"{RED}Server '{server_query}' not found.{RESET}")
            time.sleep(1)
            return

        os.system("cls" if os.name == "nt" else "clear")
        name = s["name"]
        print(f"{CORAL}╭─ Granular Control: {name} {'─' * max(0, 80 - len(name) - 23)}╮{RESET}")

        status = s["status"]
        if status == "RUNNING":
            status_badge = f"{GREEN}● RUNNING (Active Process){RESET}"
        elif status == "ONLINE":
            status_badge = f"{CYAN}✦ ONLINE (Remote Cloud Reachable){RESET}"
        elif status == "DEGRADED":
            status_badge = f"{YELLOW}⚠ DEGRADED (Reachable with Errors){RESET}"
        elif status == "OFFLINE":
            status_badge = f"{RED}✗ OFFLINE (Cloud Endpoint Unreachable){RESET}"
        elif status == "DISABLED (RUNNING)":
            status_badge = f"{CORAL}⊘ LINGERING (Process running despite disabled config!){RESET}"
        elif status == "DISABLED":
            status_badge = f"{YELLOW}⊘ DISABLED (Excluded from agent configs){RESET}"
        elif "READY (D)" in status:
            status_badge = f"{WHITE}○ READY (Local Repo on Disk){RESET}"
        else:
            status_badge = f"{WHITE}○ STOPPED{RESET}"

        print(f"{CORAL}│{RESET}  {BOLD}Status:{RESET}       {status_badge}")
        print(f"{CORAL}│{RESET}  {BOLD}Resources:{RESET}    RAM Commit: {CYAN}{s['commit_mb']} MB{RESET}   |   CPU: {CYAN}{s['cpu']}%{RESET}")
        mode_label = "UNCONFIGURED (Downloaded to disk, not added to agent config)" if s.get("is_unconfigured") else ("DISABLED in config" if s["disabled"] else "ACTIVE (Enabled)")
        print(f"{CORAL}│{RESET}  {BOLD}Config Mode:{RESET}  {mode_label}")
        src_str = ", ".join(s.get("sources", [])) if isinstance(s.get("sources"), list) else s.get("source", "")
        print(f"{CORAL}│{RESET}  {BOLD}Sources:{RESET}      {src_str}")
        if s.get("path"):
            print(f"{CORAL}│{RESET}  {BOLD}Project Path:{RESET} {s['path']}")

        cmd_val = s.get("command")
        args = s.get("args") or []
        cmd_display = str(cmd_val) if cmd_val else "(none - not configured)"
        if args:
            cmd_display += " " + " ".join(str(a) for a in args)
        if len(cmd_display) > 65:
            cmd_display = cmd_display[:62] + "..."
        print(f"{CORAL}│{RESET}  {BOLD}Command:{RESET}      {DIM}{cmd_display}{RESET}")
        print(f"{CORAL}╰{'─' * 84}╯{RESET}\n")

        print(f" {BOLD}Available Operations for [{name}]:{RESET}")
        print(f"  {GREEN}[1] Start Server{RESET}           - Spawn process if runnable script detected")
        print(f"  {RED}[2] Stop / Kill Server{RESET}     - Forcefully terminate process & all child workers")
        print(f"  {AMBER}[3] Restart Server{RESET}         - Terminate tree and immediately re-launch")
        print(f"  {YELLOW}[4] Disable in Config{RESET}      - Set 'disabled: true' across all agent configs & kill")
        print(f"  {CYAN}[5] Enable in Config{RESET}       - Set 'disabled: false' across all agent configs")
        print(f"  {INDIGO}[6] Inspect Full Details{RESET}   - View args, masked env vars, full process tree")
        print(f"  {RED}[7] Clean Uninstall{RESET}        - Wipe directory, remove configs & kill (Zero Residue)")
        print(f"  {CYAN}[O] Open Folder{RESET}            - Open directory in Windows File Explorer")
        print(f"  {AMBER}[R] Refresh Status{RESET}         - Re-query live PIDs and memory commit")
        print(f"  {WHITE}[B] Back to Overview{RESET}       - Return to main server table\n")

        op = input(f"{BOLD}Select operation [1-7, O, R, B]: {RESET}").strip().lower()

        if op == "1":
            start_server(s)
            time.sleep(0.8)
        elif op == "2":
            k = kill_server(s)
            print(f"{GREEN}Terminated PIDs: {k}{RESET}")
            time.sleep(0.8)
        elif op == "3":
            restart_server(s)
            time.sleep(0.8)
        elif op == "4":
            toggle_disable_server(s, force_state=True)
            time.sleep(0.8)
        elif op == "5":
            toggle_disable_server(s, force_state=False)
            time.sleep(0.8)
        elif op == "6":
            inspect_server_details(s, interactive=True)
        elif op == "7":
            confirm = input(f"{RED}{BOLD}WARNING: Delete '{name}' from disk and configs? (y/N): {RESET}").strip().lower()
            if confirm == "y":
                uninstall_server(s)
                input(f"{DIM}Press Enter to return to overview...{RESET}")
                return
        elif op == "o":
            open_server_location(s)
            time.sleep(0.8)
        elif op == "r":
            continue
        elif op == "b":
            return

def interactive_loop() -> None:
    """Main interactive event loop."""
    prefs = load_prefs()
    show_local_repos = prefs.get("show_local_repos", True)

    while True:
        data = get_snapshot(show_local_repos=show_local_repos)
        render_cli(data)

        try:
            choice = input(f"{BOLD}Action or Server # > {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM}Exiting MCP Manager...{RESET}")
            break

        if not choice:
            continue

        c = choice.lower()
        if c in ("q", "quit", "exit"):
            break
        elif c == "r":
            continue
        elif c == "k":
            killed = kill_all_servers(data["servers"])
            print(f"\n{GREEN}Killed {len(killed)} process(es): {killed}{RESET}")
            time.sleep(0.8)
        elif c == "s":
            print(f"\n{GREEN}Starting all configured servers...{RESET}")
            for s in data["servers"]:
                if not s["disabled"] and not s["is_running"] and s["type"] != "remote":
                    start_server(s)
            time.sleep(0.8)
        elif c == "t":
            show_local_repos = not show_local_repos
            prefs["show_local_repos"] = show_local_repos
            save_prefs(prefs)
        elif c == "p":
            deep_port_audit(data, interactive=True)
        elif c == "f":
            run_config_repair()
            input(f"{DIM}Press Enter to return to overview...{RESET}")
        else:
            matched = None
            if choice.isdigit():
                val = int(choice)
                matched = [s for s in data["servers"] if s["num"] == val]
            else:
                target_key = normalize_server_key(choice)
                matched = [s for s in data["servers"] if normalize_server_key(s["name"]) == target_key]
                if not matched:
                    matched = [s for s in data["servers"] if target_key in normalize_server_key(s["name"])]

            if matched:
                server_control_menu(matched[0]["name"])
            else:
                print(f"{RED}Unrecognized input: '{choice}'. Enter server #, name, T, K, S, P, F, R, or Q.{RESET}")
                time.sleep(0.5)
