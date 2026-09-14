# -*- coding: utf-8 -*-
"""State snapshot engine aggregating multi-agent configs, OS processes, repos, and health."""
from __future__ import annotations
import os
from typing import Any
import psutil
from .constants import ALLOWED_RUNNERS
from .utils import load_prefs, normalize_server_key
from .config import scan_agent_configs
from .repos import scan_machine_repos
from .health import batch_check_remote_health
from .process import derive_patterns

def get_snapshot(show_local_repos: bool | None = None, check_remotes: bool = True) -> dict[str, Any]:
    """Query live system state: returns snapshot dictionary with active and idle servers."""
    if show_local_repos is None:
        prefs = load_prefs()
        show_local_repos = prefs.get("show_local_repos", True)

    # 1. Scan agent configs
    agent_servers, found_agents = scan_agent_configs()
    configured_keys = {normalize_server_key(k): k for k in agent_servers}

    # 2. Match local machine repos & NPX cache
    matched_paths, unconfigured_repos = scan_machine_repos(set(configured_keys.keys()))

    master_catalog: dict[str, Any] = {}
    for s_name, s_data in agent_servers.items():
        ck = normalize_server_key(s_name)
        if ck in matched_paths:
            s_data["path"] = matched_paths[ck]
        master_catalog[s_name] = s_data

    candidate_runners = set(ALLOWED_RUNNERS)
    for s_data in master_catalog.values():
        if s_data.get("command"):
            cmd_name = os.path.basename(s_data["command"]).lower()
            if cmd_name:
                candidate_runners.add(cmd_name)

    # 3. Collect candidate processes
    candidate_processes = []
    my_pid = os.getpid()
    for p in psutil.process_iter(["pid", "name"]):
        try:
            if p.info["pid"] == my_pid:
                continue
            pname = (p.info["name"] or "").lower()
            if pname in candidate_runners or "mcp" in pname:
                cmd_tokens = p.cmdline() or []
                cmd_str = " ".join(cmd_tokens).lower()
                if any(ign in cmd_str for ign in ("mcp_cli_manager", "mcp-manager", "mcp-status")):
                    continue
                candidate_processes.append({
                    "pid": p.info["pid"],
                    "name": p.info["name"],
                    "cmdline": cmd_str,
                    "proc": p,
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    assigned_pids: set[int] = set()
    servers_list: list[dict[str, Any]] = []
    total_commit = 0.0
    idx = 1

    # 4. Concurrent pre-fetch of remote server health (sub-second persistent cache)
    remote_health_results: dict[str, tuple[str, str]] = {}
    if check_remotes:
        remote_urls = [s.get("url") for s in master_catalog.values() if s.get("type") == "remote" and s.get("url")]
        if remote_urls:
            remote_health_results = batch_check_remote_health(remote_urls, timeout=0.8)

    # 5. Process matching
    for s_name, s_data in master_catalog.items():
        s_type = s_data["type"]
        patterns = derive_patterns(s_name, s_data.get("command"), s_data.get("args"))

        matched_procs = []
        if s_type != "remote":
            for cp in candidate_processes:
                if cp["pid"] in assigned_pids:
                    continue
                if any(pat in cp["cmdline"] for pat in patterns):
                    matched_procs.append(cp)
                    assigned_pids.add(cp["pid"])

        commit_mb = 0.0
        cpu_pct = 0.0
        pids: list[int] = []
        for mp in matched_procs:
            try:
                mi = mp["proc"].memory_info()
                priv = getattr(mi, "private", mi.rss) / (1024 * 1024)
                commit_mb += priv
                cpu_pct += mp["proc"].cpu_percent(interval=None)
                pids.append(mp["pid"])
            except Exception:
                pass

        total_commit += commit_mb
        is_running = len(pids) > 0
        is_disabled = bool(s_data.get("disabled", False))

        remote_status = None
        remote_detail = ""
        if s_type == "remote" and check_remotes:
            url = s_data.get("url")
            if url:
                remote_status, remote_detail = remote_health_results.get(url, ("UNKNOWN", "no cache"))
            else:
                remote_status, remote_detail = "UNKNOWN", "no url stored"

        if s_type == "remote":
            if remote_status == "ONLINE":
                status = "ONLINE"
            elif remote_status == "DEGRADED":
                status = "DEGRADED"
            elif remote_status == "OFFLINE":
                status = "OFFLINE"
            else:
                status = "UNKNOWN"
        elif is_disabled and is_running:
            status = "DISABLED (RUNNING)"
        elif is_disabled:
            status = "DISABLED"
        elif is_running:
            status = "RUNNING"
        else:
            status = "READY"

        servers_list.append({
            "num": idx,
            "name": s_name,
            "source": s_data.get("source", "Local Machine"),
            "sources": s_data.get("sources_list", [s_data.get("source", "Local Machine")]),
            "type": s_type,
            "status": status,
            "remote_detail": remote_detail,
            "is_running": is_running if s_type != "remote" else (remote_status == "ONLINE"),
            "disabled": is_disabled,
            "disabled_in": s_data.get("disabled_in", []),
            "enabled_in": s_data.get("enabled_in", []),
            "pids": pids,
            "port": "",
            "commit_mb": round(commit_mb, 1),
            "cpu": round(cpu_pct, 1),
            "command": s_data.get("command"),
            "args": s_data.get("args"),
            "env": s_data.get("env"),
            "url": s_data.get("url"),
            "path": s_data.get("path"),
            "description": s_data.get("description"),
            "matched_procs": matched_procs,
            "patterns": patterns,
            "is_unconfigured": False,
        })
        idx += 1

    # 6. Unconfigured repos & NPX caches
    if show_local_repos:
        for repo in unconfigured_repos:
            r_name = repo["name"]
            if normalize_server_key(r_name) not in {normalize_server_key(x["name"]) for x in servers_list}:
                src = repo.get("source", "Local Disk")
                status_text = "○ READY (D)" if src == "Local Disk" else "○ READY (D)"
                servers_list.append({
                    "num": idx,
                    "name": r_name,
                    "source": f"{src} ({repo['base']})" if repo.get("base") else src,
                    "sources": [f"{src} ({repo.get('base', repo['path'])})"],
                    "type": "local",
                    "status": status_text,
                    "remote_detail": "",
                    "is_running": False,
                    "disabled": False,
                    "disabled_in": [],
                    "enabled_in": [],
                    "pids": [],
                    "port": "",
                    "commit_mb": 0.0,
                    "cpu": 0.0,
                    "command": None,
                    "args": [],
                    "env": {},
                    "url": None,
                    "path": repo["path"],
                    "description": "Downloaded to disk, not added to agent config",
                    "matched_procs": [],
                    "patterns": [r_name.lower()],
                    "is_unconfigured": True,
                })
                idx += 1

    vm = psutil.virtual_memory()
    return {
        "servers": servers_list,
        "agents": found_agents,
        "total_commit_mb": round(total_commit, 1),
        "active_count": sum(1 for s in servers_list if s["is_running"]),
        "total_count": len(servers_list),
        "ram_percent": vm.percent,
        "ram_free_gb": round(vm.available / (1024 ** 3), 1),
        "ram_total_gb": round(vm.total / (1024 ** 3), 1),
        "view_mode": "full" if show_local_repos else "compact",
        "unconfigured_count": len(unconfigured_repos),
    }
