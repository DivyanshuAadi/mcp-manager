# -*- coding: utf-8 -*-
"""Process discovery, memory commit tracking, surgical process tree termination, and server spawning."""
from __future__ import annotations
import os
import sys
import glob
import time
import subprocess
from typing import Any
import psutil
from .constants import IS_WIN, GENERIC_WORDS, GREEN, RED, RESET
from .utils import normalize_server_key

def derive_patterns(name: str, command: str | None, args: list[Any] | None) -> list[str]:
    """Derive command-line substrings to accurately identify server processes in Task Manager."""
    pats = [name.lower()]
    norm = normalize_server_key(name)
    if norm and norm not in GENERIC_WORDS:
        pats.append(norm)

    if command:
        base = os.path.basename(command).lower()
        noext = os.path.splitext(base)[0]
        if noext not in GENERIC_WORDS and len(noext) > 3:
            pats.append(noext)

    if args:
        for a in args:
            sa = str(a).lower()
            if any(ign in sa for ign in ("-y", "--stdio", "--port", "run", "start")):
                continue
            base = os.path.basename(sa.replace("\\", "/"))
            noext = os.path.splitext(base)[0]
            if noext not in GENERIC_WORDS and len(noext) > 3:
                pats.append(noext)
                pats.append(sa)

    return list(dict.fromkeys(pats))

def kill_pid_tree(pid: int) -> list[int]:
    """Forcefully terminate a process tree."""
    killed: list[int] = []
    if IS_WIN:
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            killed.append(pid)
        except Exception:
            pass
    else:
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for c in children:
                try:
                    c.kill()
                    killed.append(c.pid)
                except Exception:
                    pass
            parent.kill()
            killed.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed

def kill_server(server: dict[str, Any]) -> list[int]:
    """Terminate all running instances and children of a specific server."""
    pids = list(server.get("pids") or [])
    killed: list[int] = []
    for pid in pids:
        k = kill_pid_tree(pid)
        killed.extend(k)

    server["pids"] = []
    server["is_running"] = False
    server["commit_mb"] = 0.0
    server["cpu"] = 0.0
    server["status"] = "STOPPED"
    return list(set(killed))

def kill_all_servers(servers: list[dict[str, Any]]) -> list[int]:
    """Forcefully kill all running servers."""
    all_killed: list[int] = []
    for s in servers:
        if s.get("pids"):
            k = kill_server(s)
            all_killed.extend(k)
    return all_killed

def _find_venv_python(project_dir: str) -> str | None:
    """Find virtualenv python executable within a project directory."""
    if not project_dir or not os.path.isdir(project_dir):
        return None
    candidates = [
        os.path.join(project_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(project_dir, "venv", "Scripts", "python.exe"),
        os.path.join(project_dir, ".venv", "bin", "python"),
        os.path.join(project_dir, "venv", "bin", "python"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

def start_server(server: dict[str, Any]) -> int | None:
    """Spawn server process from its command definition or detected repository entry point."""
    cmd = server.get("command")
    args = server.get("args") or []
    env = os.environ.copy()
    if server.get("env"):
        env.update({str(k): str(v) for k, v in server["env"].items()})

    project_dir = server.get("path")
    full_cmd: list[str] = []

    if cmd:
        full_cmd = [cmd] + [str(a) for a in args]
    elif project_dir and os.path.isdir(project_dir):
        py = _find_venv_python(project_dir) or sys.executable
        for script in ("main.py", "server.py", "app.py", "index.js"):
            candidate = os.path.join(project_dir, script)
            if os.path.isfile(candidate):
                if script.endswith(".py"):
                    full_cmd = [py, candidate]
                else:
                    full_cmd = ["node", candidate]
                break

    if not full_cmd:
        print(f"{RED}No runnable command or script entrypoint found for [{server['name']}].{RESET}")
        return None

    try:
        proc = subprocess.Popen(
            full_cmd,
            cwd=project_dir if project_dir and os.path.isdir(project_dir) else None,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print(f"{GREEN}Spawned process for [{server['name']}] (PID {proc.pid}){RESET}")
        return proc.pid
    except Exception as e:
        print(f"{RED}Failed to start server: {e}{RESET}")
        return None

def restart_server(server: dict[str, Any]) -> None:
    """Stop server process tree and immediately launch a fresh instance."""
    print(f"\nRestarting [{server['name']}]...")
    kill_server(server)
    time.sleep(0.5)
    start_server(server)
