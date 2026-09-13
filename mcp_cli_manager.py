# -*- coding: utf-8 -*-
"""
=============================================================================
  ✦ MCP 360° ENGINE v3.5 - CROSS-PLATFORM UNIVERSAL MCP CONTROL & MONITOR
=============================================================================
  Changes from v3.4:
  • Real remote-server health checks (HTTP + MCP-style probe)
  • Automatic config repair with atomic writes + .bak backups
  • Full Linux / macOS / Windows portability
  • Fixed missing `url` storage, silent exceptions, cpu sampling, paths
  • Safer process kill (no shell=True), safer open helpers
  • Expanded CONFIG_TARGETS for all major OSes
=============================================================================
"""

from __future__ import annotations

import os
import sys
import re
import json
import time
import glob
import shutil
import stat
import subprocess
import platform
import tempfile
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    import psutil
except ImportError:
    print("psutil is required: pip install psutil")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")
PLATFORM = platform.system().lower()

if IS_WIN:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ANSI Color Palette
CORAL     = "\033[38;2;240;100;70m"
AMBER     = "\033[38;2;250;180;60m"
GREEN     = "\033[38;2;80;220;120m"
CYAN      = "\033[38;2;70;200;240m"
INDIGO    = "\033[38;2;130;120;250m"
WHITE     = "\033[38;2;245;245;245m"
GRAY      = "\033[38;2;140;140;140m"
DARK_GRAY = "\033[38;2;70;70;70m"
RED       = "\033[38;2;255;85;85m"
YELLOW    = "\033[38;2;255;215;0m"
DIM       = "\033[2m"
BOLD      = "\033[1m"
RESET     = "\033[0m"


def len_visible(s: str) -> int:
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def pad_visible(s: str, width: int, align: str = "left") -> str:
    vis_len = len_visible(s)
    pad = max(0, width - vis_len)
    if align == "right":
        return (" " * pad) + s
    if align == "center":
        left = pad // 2
        return (" " * left) + s + (" " * (pad - left))
    return s + (" " * pad)


def canon_key(name: Any) -> str:
    if not name:
        return ""
    return str(name).lower().replace("_", "-").replace("-mcp", "").replace("_mcp", "").strip()


HOME = os.path.expanduser("~")
APPDATA = os.environ.get("APPDATA", "")
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
XDG_CONFIG = os.environ.get("XDG_CONFIG_HOME", os.path.join(HOME, ".config"))

PREFS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".mcp_prefs.json")


def load_prefs() -> Dict[str, Any]:
    prefs: Dict[str, Any] = {"show_local_repos": True}
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                prefs.update(json.load(f))
        except Exception as e:
            print(f"{DIM}[prefs] load warning: {e}{RESET}")
    return prefs


def save_prefs(prefs: Dict[str, Any]) -> None:
    try:
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
    except Exception as e:
        print(f"{DIM}[prefs] save warning: {e}{RESET}")


# ---------------------------------------------------------------------------
# Expanded, cross-platform CONFIG_TARGETS
# ---------------------------------------------------------------------------
def _build_config_targets() -> List[Tuple[str, str]]:
    targets: List[Tuple[str, str]] = [
        # Claude family
        ("Claude Code", os.path.join(HOME, ".claude.json")),
        ("Claude Global", os.path.join(HOME, ".claude", "mcp.json")),
        ("Claude Desktop (Win)", os.path.join(APPDATA, "Claude", "claude_desktop_config.json")),
        ("Claude Desktop (Mac)", os.path.join(HOME, "Library", "Application Support", "Claude", "claude_desktop_config.json")),
        ("Claude Desktop (Linux)", os.path.join(XDG_CONFIG, "Claude", "claude_desktop_config.json")),
        # Cursor
        ("Cursor", os.path.join(HOME, ".cursor", "mcp.json")),
        ("Cursor Global (Win)", os.path.join(APPDATA, "Cursor", "User", "globalStorage", "mcp.json")),
        ("Cursor Global (Mac)", os.path.join(HOME, "Library", "Application Support", "Cursor", "User", "globalStorage", "mcp.json")),
        ("Cursor Global (Linux)", os.path.join(XDG_CONFIG, "Cursor", "User", "globalStorage", "mcp.json")),
        # Windsurf / Codeium
        ("Windsurf", os.path.join(HOME, ".codeium", "windsurf", "mcp_config.json")),
        ("Windsurf User (Win)", os.path.join(APPDATA, "Windsurf", "User", "mcp.json")),
        ("Windsurf User (Mac)", os.path.join(HOME, "Library", "Application Support", "Windsurf", "User", "mcp.json")),
        # Cline / Roo
        ("Cline (Win)", os.path.join(APPDATA, "Code", "User", "globalStorage", "saoudrizwan.claude-dev", "settings", "cline_mcp_settings.json")),
        ("Cline (Mac)", os.path.join(HOME, "Library", "Application Support", "Code", "User", "globalStorage", "saoudrizwan.claude-dev", "settings", "cline_mcp_settings.json")),
        ("Roo Code (Win)", os.path.join(APPDATA, "Code", "User", "globalStorage", "rooveterinaryinc.roo-cline", "settings", "cline_mcp_settings.json")),
        ("Roo Code (Mac)", os.path.join(HOME, "Library", "Application Support", "Code", "User", "globalStorage", "rooveterinaryinc.roo-cline", "settings", "cline_mcp_settings.json")),
        # Continue / Zed / VS Code workspace
        ("Continue", os.path.join(HOME, ".continue", "config.json")),
        ("Zed", os.path.join(HOME, ".config", "zed", "settings.json")),
        ("Zed (Mac)", os.path.join(HOME, "Library", "Application Support", "Zed", "settings.json")),
        ("VS Code Workspace", os.path.join(os.getcwd(), ".vscode", "mcp.json")),
        ("Workspace", os.path.join(os.getcwd(), "mcp.json")),
        # Antigravity / Gemini
        ("Antigravity IDE", os.path.join(HOME, ".gemini", "config", "mcp_config.json")),
    ]
    # Filter to only existing paths at runtime (keeps the list honest)
    return targets


CONFIG_TARGETS = _build_config_targets()

GENERIC_WORDS = {
    "dist", "src", "build", "bin", "lib", "out", "release", "debug", "scripts",
    "vendor", "target", "app", "core", "index", "main", "cli", "server", "client",
    "node_modules", "index.js", "cli.js", "main.js", "index.py", "main.py",
    "python.exe", "node.exe", "python", "node", "tools", "local", "mcp", "common",
    "usr", "home", "opt", "var", "tmp", "etc",
}

# Cross-platform runner names (no .exe required on Unix)
ALLOWED_RUNNERS = {
    "node.exe", "node", "python.exe", "python", "python3", "pythonw.exe",
    "uvx.exe", "uvx", "scrapling.exe", "scrapling",
    "deno.exe", "deno", "bun.exe", "bun",
    "cargo.exe", "cargo", "go.exe", "go", "dotnet.exe", "dotnet",
    "java.exe", "java",
}


# ---------------------------------------------------------------------------
# Safe JSON I/O with backup + atomic write
# ---------------------------------------------------------------------------
def atomic_write_json(path: str, data: Any, make_backup: bool = True) -> bool:
    """Write JSON atomically. Optionally keep a .bak of the previous file."""
    try:
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, exist_ok=True)

        if make_backup and os.path.exists(path):
            bak = path + ".bak"
            try:
                shutil.copy2(path, bak)
            except Exception:
                pass

        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp, path)
            return True
        except Exception:
            try:
                os.unlink(tmp)
            except Exception:
                pass
            raise
    except Exception as e:
        print(f"{RED}[atomic_write] failed for {path}: {e}{RESET}")
        return False


def load_json_safe(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return None
    except Exception as e:
        print(f"{DIM}[load_json] {path}: {e}{RESET}")
        return None


# ---------------------------------------------------------------------------
# LAYER 1: Network Prober + Remote Health Check
# ---------------------------------------------------------------------------
def probe_mcp_http(ip: str, port: int, timeout: float = 0.15) -> Tuple[bool, Optional[str]]:
    """Probe common MCP HTTP/SSE endpoints on a local listening socket."""
    target_ip = "127.0.0.1" if ip in ("0.0.0.0", "::", "") else ip
    endpoints = ["/mcp", "/sse", "/", "/jsonrpc", "/health", "/status"]

    for ep in endpoints:
        url = f"http://{target_ip}:{port}{ep}"
        try:
            req = Request(
                url,
                headers={
                    "Accept": "text/event-stream, application/json, text/plain",
                    "User-Agent": "MCP-Manager/3.5",
                },
            )
            with urlopen(req, timeout=timeout) as resp:
                status = resp.status
                ct = (resp.headers.get("Content-Type") or "").lower()
                body = resp.read(512).decode("utf-8", errors="ignore").lower()
                if any(x in ct for x in ("text/event-stream", "mcp", "json")) or any(
                    x in body for x in ("jsonrpc", "mcp", "server")
                ):
                    return True, f"HTTP/SSE {status} ({ep})"
        except HTTPError as e:
            body = ""
            try:
                body = e.read(512).decode("utf-8", errors="ignore").lower()
            except Exception:
                pass
            if any(x in body for x in ("mcp", "jsonrpc", "method not allowed")):
                return True, f"HTTP {e.code} ({ep})"
        except Exception:
            pass
    return False, None


def check_remote_health(url: str, timeout: float = 1.5) -> Tuple[str, str]:
    """
    Real health check for remote MCP servers.
    Returns (status, detail) where status is ONLINE | DEGRADED | OFFLINE | UNKNOWN.
    """
    if not url or not url.startswith(("http://", "https://")):
        return "UNKNOWN", "no valid URL"

    # 1. Simple reachability
    try:
        req = Request(
            url.rstrip("/") + "/",
            headers={"User-Agent": "MCP-Manager/3.5", "Accept": "application/json, text/event-stream"},
            method="GET",
        )
        with urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read(1024).decode("utf-8", errors="ignore")
            if 200 <= status < 400:
                # Optional: try a minimal MCP initialize-style payload on /mcp or root
                if "jsonrpc" in body.lower() or "mcp" in body.lower() or status == 200:
                    return "ONLINE", f"HTTP {status}"
                return "DEGRADED", f"HTTP {status} (unexpected body)"
            return "DEGRADED", f"HTTP {status}"
    except HTTPError as e:
        # Many MCP servers return 405/400 on plain GET – still considered alive
        if e.code in (400, 401, 403, 405, 406):
            return "ONLINE", f"HTTP {e.code} (reachable)"
        return "DEGRADED", f"HTTP {e.code}"
    except (URLError, TimeoutError, OSError) as e:
        return "OFFLINE", str(e)[:60]
    except Exception as e:
        return "UNKNOWN", str(e)[:60]


def get_mcp_listening_ports(mcp_pids: Set[int]) -> Dict[int, int]:
    ports: Dict[int, int] = {}
    if not mcp_pids:
        return ports
    try:
        conns = psutil.net_connections(kind="tcp")
        for c in conns:
            if c.status == "LISTEN" and c.laddr and c.pid in mcp_pids:
                ports[c.pid] = c.laddr.port
    except (psutil.AccessDenied, PermissionError):
        pass
    except Exception:
        pass
    return ports


# ---------------------------------------------------------------------------
# LAYER 2: Filesystem Repository Inspector (cross-platform)
# ---------------------------------------------------------------------------
def normalize_mcp_key(name: str) -> str:
    clean = name.lower()
    for prefix in ("@modelcontextprotocol/server-", "@modelcontextprotocol/", "server-", "mcp-"):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
    for suffix in ("-mcp", "_mcp", "-server", "_server"):
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)]
    return clean.replace("-", "").replace("_", "").replace(" ", "").replace("@", "").replace("/", "")


def _default_search_dirs() -> List[str]:
    dirs = [
        os.path.join(HOME, "mcp"),
        os.path.join(HOME, "Tools"),
        os.path.join(HOME, "tools"),
        os.path.join(HOME, "Desktop", "MCP*"),
        os.path.join(HOME, "Projects", "MCP*"),
        os.path.join(HOME, "dev", "mcp*"),
    ]
    if IS_WIN:
        dirs = [
            r"D:\Tools & MCP\Local",
            r"D:\Tools & MCP",
            r"C:\Tools\MCP",
        ] + dirs
    return dirs


def scan_machine_repos(configured_canon_keys: Set[str]) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
    search_dirs = _default_search_dirs()
    matched_paths: Dict[str, str] = {}
    unconfigured: List[Dict[str, str]] = []
    seen: Set[str] = set()
    norm_configured = {normalize_mcp_key(k) for k in configured_canon_keys}

    # 1. Developer directories
    for dpattern in search_dirs:
        for base in glob.glob(dpattern):
            if not os.path.isdir(base):
                continue
            try:
                items = os.listdir(base)
            except OSError:
                continue
            script_dir = os.path.dirname(os.path.abspath(__file__)).lower()
            for item in items:
                full = os.path.join(base, item)
                if not os.path.isdir(full) or full in seen:
                    continue
                # Never self-detect MCP Manager or its subdirectories
                full_abs = os.path.abspath(full).lower()
                if full_abs == script_dir or script_dir in full_abs:
                    continue
                if any(ign in item.lower() for ign in ("mcp-manager", "mcp_manager", "mcp-360", "mcp360", ".git", "__pycache__", "scratch", "node_modules")):
                    continue
                seen.add(full)
                c_item = canon_key(item)
                n_item = normalize_mcp_key(item)

                if c_item in configured_canon_keys or n_item in norm_configured:
                    matched_paths[c_item] = full
                    matched_paths[n_item] = full
                else:
                    if "mcp" in item.lower() or "local" in base.lower() or item in (
                        "Graphify", "ScrapGraphAI", "Use Browser"
                    ):
                        unconfigured.append({
                            "name": item,
                            "path": full,
                            "base": base,
                            "source": "Local Disk",
                        })

    # 2. NPX cache
    npx_dirs = []
    if IS_WIN and LOCALAPPDATA:
        npx_dirs.append(os.path.join(LOCALAPPDATA, "npm-cache", "_npx"))
    npx_dirs.append(os.path.expanduser("~/.npm/_npx"))
    # Also check XDG
    npx_dirs.append(os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.join(HOME, ".cache")), "npm", "_npx"))

    seen_npx: Set[str] = set()
    for npx_base in npx_dirs:
        if not os.path.exists(npx_base):
            continue
        try:
            hash_dirs = os.listdir(npx_base)
        except OSError:
            continue
        for hash_dir in hash_dirs:
            hash_path = os.path.join(npx_base, hash_dir)
            nm = os.path.join(hash_path, "node_modules")
            if not os.path.isdir(nm) or hash_path in seen:
                continue
            try:
                pkgs = os.listdir(nm)
            except OSError:
                continue
            for pkg in pkgs:
                if pkg.startswith("."):
                    continue
                pkg_path = os.path.join(nm, pkg)
                candidate_list = []
                if pkg.startswith("@"):
                    try:
                        for sub in os.listdir(pkg_path):
                            candidate_list.append((f"{pkg}/{sub}", sub, os.path.join(pkg_path, sub)))
                    except OSError:
                        pass
                else:
                    candidate_list.append((pkg, pkg, pkg_path))

                for full_pkg_name, display_name, _ in candidate_list:
                    c_pkg = canon_key(display_name)
                    c_full = canon_key(full_pkg_name)
                    n_pkg = normalize_mcp_key(display_name)
                    n_full = normalize_mcp_key(full_pkg_name)

                    if (c_pkg in configured_canon_keys or n_pkg in norm_configured) and c_pkg not in matched_paths:
                        matched_paths[c_pkg] = hash_path
                    elif (c_full in configured_canon_keys or n_full in norm_configured) and c_full not in matched_paths:
                        matched_paths[c_full] = hash_path
                    else:
                        is_relevant = any(
                            x in full_pkg_name.lower() for x in ("mcp", "devtools", "server")
                        )
                        if is_relevant and n_pkg not in norm_configured and n_full not in norm_configured:
                            key_id = f"npx_{n_full}"
                            if key_id not in seen_npx:
                                seen_npx.add(key_id)
                                unconfigured.append({
                                    "name": display_name if not full_pkg_name.startswith("@") else full_pkg_name,
                                    "path": hash_path,
                                    "base": "NPX Cache",
                                    "source": "NPX Cache",
                                })

    return matched_paths, unconfigured


# ---------------------------------------------------------------------------
# Config scanning + automatic repair
# ---------------------------------------------------------------------------
def _extract_servers(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Try known keys used by different agents."""
    for key in ("mcpServers", "mcp_servers", "mcp", "context_servers", "servers"):
        val = data.get(key)
        if isinstance(val, dict):
            return val
    # Continue.dev sometimes nests under "experimental"
    exp = data.get("experimental")
    if isinstance(exp, dict):
        for key in ("mcpServers", "mcp"):
            val = exp.get(key)
            if isinstance(val, dict):
                return val
    return None


def repair_config(path: str, dry_run: bool = False) -> List[str]:
    """
    Automatic config repair:
    - Ensure mcpServers (or equivalent) exists and is a dict
    - Ensure every server entry is a dict
    - Ensure 'disabled' is a boolean if present
    - Write atomically + keep .bak
    Returns list of repair messages.
    """
    messages: List[str] = []
    data = load_json_safe(path)
    if data is None:
        messages.append(f"unreadable or non-object JSON: {path}")
        return messages

    servers = _extract_servers(data)
    if servers is None:
        # Nothing to repair
        return messages

    changed = False
    for sname, sdata in list(servers.items()):
        if not isinstance(sdata, dict):
            messages.append(f"{path}: '{sname}' was not a dict → removed")
            del servers[sname]
            changed = True
            continue
        if "disabled" in sdata and not isinstance(sdata["disabled"], bool):
            sdata["disabled"] = bool(sdata["disabled"])
            messages.append(f"{path}: '{sname}'.disabled coerced to bool")
            changed = True
        # Ensure command or url exists (warn only)
        if not sdata.get("command") and not (sdata.get("url") or sdata.get("serverUrl")):
            messages.append(f"{path}: '{sname}' has neither command nor url")

    if changed and not dry_run:
        if atomic_write_json(path, data, make_backup=True):
            messages.append(f"repaired & written: {path}")
        else:
            messages.append(f"repair failed to write: {path}")

    return messages


def scan_agent_configs() -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    discovered: Dict[str, Dict[str, Any]] = {}
    found_agents: Set[str] = set()

    for agent_name, path in CONFIG_TARGETS:
        if not os.path.exists(path):
            continue

        found_agents.add(agent_name)
        data = load_json_safe(path)
        if data is None:
            continue

        servers = _extract_servers(data)
        if not isinstance(servers, dict):
            continue

        for sname, sdata in servers.items():
            if not isinstance(sdata, dict):
                continue

            c_name = canon_key(sname)
            is_disabled = bool(sdata.get("disabled", False))
            cmd = sdata.get("command")
            args = sdata.get("args", [])
            env = sdata.get("env", {})
            url = sdata.get("url") or sdata.get("serverUrl")

            if c_name in discovered:
                entry = discovered[c_name]
                if agent_name not in entry["sources_list"]:
                    entry["sources_list"].append(agent_name)
                    entry["source"] = ", ".join(entry["sources_list"])
                if is_disabled:
                    entry["disabled_in"].append(agent_name)
                else:
                    entry["enabled_in"].append(agent_name)
                # Backfill missing fields
                if not entry.get("command") and cmd:
                    entry["command"] = cmd
                    entry["args"] = json.dumps(args) if isinstance(args, list) else args
                    entry["env"] = json.dumps(env) if isinstance(env, dict) else env
                if not entry.get("url") and url:
                    entry["url"] = url
                continue

            stype = "remote" if url and not cmd else "local"
            discovered[c_name] = {
                "name": sname,
                "canon_key": c_name,
                "source": agent_name,
                "sources_list": [agent_name],
                "type": stype,
                "command": cmd,
                "args": json.dumps(args) if isinstance(args, list) else args,
                "env": json.dumps(env) if isinstance(env, dict) else env,
                "url": url,  # FIXED: now stored
                "disabled_in": [agent_name] if is_disabled else [],
                "enabled_in": [] if is_disabled else [agent_name],
                "disabled": is_disabled,
                "description": f"Configured in {agent_name}",
            }

    result: Dict[str, Dict[str, Any]] = {}
    for c_name, entry in discovered.items():
        entry["disabled"] = len(entry["enabled_in"]) == 0
        result[entry["name"]] = entry

    return result, sorted(found_agents)


# ---------------------------------------------------------------------------
# Pattern derivation (zero false-positives)
# ---------------------------------------------------------------------------
def derive_patterns(name: str, command: Optional[str], args_str: Any) -> List[str]:
    patterns: Set[str] = set()
    c_name = canon_key(name)
    if len(c_name) >= 3:
        patterns.add(c_name)
    if len(name) >= 3:
        patterns.add(name.lower())

    if args_str:
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
            if not isinstance(args, list):
                args = [args]
            for a in args:
                if not isinstance(a, str):
                    continue
                clean_a = a.replace("\\", "/")
                base = os.path.basename(clean_a).lower()
                if base not in GENERIC_WORDS and base.endswith((".py", ".js", ".mjs", ".ts", ".exe", ".cjs")):
                    patterns.add(base)
                parts = [
                    p.lower()
                    for p in clean_a.split("/")
                    if p and p not in GENERIC_WORDS and not p.endswith(":") and len(p) > 2
                ]
                if parts:
                    pkg_candidate = parts[-1]
                    if pkg_candidate.endswith((".py", ".js", ".mjs", ".ts", ".cjs")):
                        pkg_candidate = parts[-2] if len(parts) >= 2 else ""
                    if pkg_candidate and pkg_candidate not in GENERIC_WORDS and len(pkg_candidate) >= 4:
                        patterns.add(pkg_candidate)
        except Exception:
            pass

    if command:
        base_cmd = os.path.basename(command).lower()
        if any(k in base_cmd for k in ("scrapling", "mcp")):
            patterns.add(base_cmd)

    return [p for p in patterns if p not in GENERIC_WORDS and len(p) >= 3]


# ---------------------------------------------------------------------------
# Snapshot engine
# ---------------------------------------------------------------------------
def get_snapshot(show_local_repos: Optional[bool] = None, check_remotes: bool = True) -> Dict[str, Any]:
    if show_local_repos is None:
        prefs = load_prefs()
        show_local_repos = prefs.get("show_local_repos", True)

    agent_servers, found_agents = scan_agent_configs()
    configured_keys = {canon_key(k): k for k in agent_servers}

    matched_paths, unconfigured_repos = scan_machine_repos(set(configured_keys.keys()))

    master_catalog: Dict[str, Dict[str, Any]] = {}
    for s_name, s_data in agent_servers.items():
        ck = canon_key(s_name)
        if ck in matched_paths:
            s_data["path"] = matched_paths[ck]
        master_catalog[s_name] = s_data

    candidate_runners = set(ALLOWED_RUNNERS)
    for s_data in master_catalog.values():
        if s_data.get("command"):
            cmd_name = os.path.basename(s_data["command"]).lower()
            if cmd_name:
                candidate_runners.add(cmd_name)

    # Collect candidate processes
    candidate_processes = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            pname = (p.info["name"] or "").lower()
            if pname in candidate_runners or "mcp" in pname:
                cmd_tokens = p.cmdline() or []
                cmd_str = " ".join(cmd_tokens).lower()
                if any(ign in cmd_str for ign in ("mcp_cli_manager", "mcp-manager", "mcp-status", "deploy_", "inspect_")):
                    continue
                candidate_processes.append({
                    "pid": p.info["pid"],
                    "name": p.info["name"],
                    "cmdline": cmd_str,
                    "proc": p,
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    assigned_pids: Set[int] = set()
    servers_list: List[Dict[str, Any]] = []
    total_commit = 0.0
    idx = 1

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
        pids: List[int] = []
        for mp in matched_procs:
            try:
                mi = mp["proc"].memory_info()
                priv = getattr(mi, "private", mi.rss) / (1024 * 1024)
                commit_mb += priv
                # Second sample for non-zero CPU (first call is often 0)
                cpu_pct += mp["proc"].cpu_percent(interval=None)
                pids.append(mp["pid"])
            except Exception:
                pass

        total_commit += commit_mb
        is_running = len(pids) > 0
        is_disabled = bool(s_data.get("disabled", False))

        # Remote health check
        remote_status = None
        remote_detail = ""
        if s_type == "remote" and check_remotes:
            url = s_data.get("url")
            if url:
                remote_status, remote_detail = check_remote_health(url)
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

    if show_local_repos:
        for u in unconfigured_repos:
            u_name = u["name"]
            if canon_key(u_name) in configured_keys:
                continue
            patterns = derive_patterns(u_name, None, [u["path"]])
            matched_procs = []
            for cp in candidate_processes:
                if cp["pid"] in assigned_pids:
                    continue
                if any(pat in cp["cmdline"] for pat in patterns):
                    matched_procs.append(cp)
                    assigned_pids.add(cp["pid"])

            commit_mb = 0.0
            cpu_pct = 0.0
            pids = []
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
            status = "RUNNING" if is_running else "READY"

            servers_list.append({
                "num": idx,
                "name": u_name,
                "source": f"Local Disk ({u['base']})",
                "sources": ["Local Disk"],
                "type": "local",
                "status": status,
                "remote_detail": "",
                "is_running": is_running,
                "disabled": False,
                "disabled_in": [],
                "enabled_in": [],
                "pids": pids,
                "port": "",
                "commit_mb": round(commit_mb, 1),
                "cpu": round(cpu_pct, 1),
                "command": None,
                "args": None,
                "env": None,
                "url": None,
                "path": u["path"],
                "description": f"Downloaded repository at {u['path']}",
                "matched_procs": matched_procs,
                "patterns": patterns,
                "is_unconfigured": True,
            })
            idx += 1

    all_mcp_pids: Set[int] = set()
    for s in servers_list:
        all_mcp_pids.update(s["pids"])

    port_map = get_mcp_listening_ports(all_mcp_pids)
    for s in servers_list:
        for pid in s["pids"]:
            if pid in port_map:
                s["port"] = f":{port_map[pid]}"
                break

    try:
        vm = psutil.virtual_memory()
        ram_pct = vm.percent
        ram_free_gb = round(vm.available / (1024 ** 3), 1)
        ram_total_gb = round(vm.total / (1024 ** 3), 1)
    except Exception:
        ram_pct = ram_free_gb = ram_total_gb = 0.0

    return {
        "servers": servers_list,
        "unconfigured_repos": unconfigured_repos,
        "found_agents": found_agents,
        "system_ram_used_pct": ram_pct,
        "system_ram_free_gb": ram_free_gb,
        "system_ram_total_gb": ram_total_gb,
        "total_servers_ram": round(total_commit, 1),
        "active_pids": list(all_mcp_pids),
        "show_local_repos": show_local_repos,
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
def render_cli(data: Dict[str, Any]) -> None:
    os.system("cls" if IS_WIN else "clear")

    all_sources = [s.get("source", "") for s in data["servers"]]
    max_src_len = max([len_visible(src) for src in all_sources] + [17])
    col_src_w = max(34, max_src_len)
    W = max(112, 3 + 1 + 24 + 1 + 13 + 1 + col_src_w + 1 + 14 + 1 + 11 + 1 + 6 + 2)

    print(f"\n{CORAL}╭{'─' * (W - 2)}╮{RESET}")
    title_line = f"  {BOLD}{WHITE}✦ MCP 360° ENGINE{RESET}  {DIM}v3.5 (Cross-Platform + Remote Health){RESET}"
    status_line = f"{GREEN}● FAST ENGINE ACTIVE{RESET}  "
    space_len = W - 2 - len_visible(title_line) - len_visible(status_line)
    print(f"{CORAL}│{RESET}{title_line}{' ' * max(0, space_len)}{status_line}{CORAL}│{RESET}")
    sub_line = f"  {DIM}Universal Coding Agent Inspector & Process Controller ({PLATFORM}){RESET}"
    space_sub = W - 2 - len_visible(sub_line)
    print(f"{CORAL}│{RESET}{sub_line}{' ' * max(0, space_sub)}{CORAL}│{RESET}")
    print(f"{CORAL}╰{'─' * (W - 2)}╯{RESET}")

    running_count = sum(1 for s in data["servers"] if s["is_running"])
    total_count = len(data["servers"])
    ram_pct = data["system_ram_used_pct"]
    bar_len = 10
    filled = int((ram_pct / 100.0) * bar_len)
    bar_str = f"[{'█' * filled}{'░' * (bar_len - filled)}]"
    agents_str = ", ".join(data["found_agents"]) if data["found_agents"] else "None"
    unconf_count = len(data.get("unconfigured_repos", []))
    view_mode_str = (
        f"{GREEN}Full ({unconf_count} Local Repos Included){RESET}"
        if data["show_local_repos"]
        else f"{AMBER}Compact (Configured Only){RESET}"
    )

    print(f" {BOLD}Coding Agents {RESET} : {CYAN}{agents_str}{RESET} │ View: {view_mode_str} {DIM}[T]{RESET}")
    print(f" {BOLD}System RAM    {RESET} : {AMBER}{bar_str} {ram_pct}%{RESET} ({data['system_ram_free_gb']} GB free of {data['system_ram_total_gb']} GB)")
    print(f" {BOLD}Total Memory  {RESET} : {BOLD}{GREEN}{data['total_servers_ram']} MB{RESET} Commit Charge  │  {BOLD}{running_count}{RESET} Active / {total_count} Total Servers")
    print(f"{GRAY}{'─' * W}{RESET}")

    header = (
        f" {pad_visible('#', 3)} "
        f"{pad_visible('Server Name', 24)} "
        f"{pad_visible('Status', 13)} "
        f"{pad_visible('Discovery Sources', col_src_w)} "
        f"{pad_visible('Port / PID', 14)} "
        f"{pad_visible('RAM Commit', 11, 'right')} "
        f"{pad_visible('CPU', 6, 'right')}"
    )
    print(f"{BOLD}{WHITE}{header}{RESET}")
    print(f"{GRAY}{'─' * W}{RESET}")

    for s in data["servers"]:
        num_str = f"{s['num']:02d}"
        s_name = s["name"][:24]

        st = s["status"]
        if st == "RUNNING":
            status_badge = f"{GREEN}● RUNNING   {RESET}"
        elif st == "DISABLED (RUNNING)":
            status_badge = f"{CORAL}⊘ LINGERING {RESET}"
        elif st == "DISABLED":
            status_badge = f"{YELLOW}⊘ DISABLED  {RESET}"
        elif st in ("INSTALLED", "READY"):
            status_badge = f"{DIM}○ READY (D) {RESET}" if s.get("is_unconfigured") else f"{DIM}○ READY     {RESET}"
        elif st == "ONLINE":
            status_badge = f"{CYAN}✦ ONLINE    {RESET}"
        elif st == "DEGRADED":
            status_badge = f"{AMBER}⚠ DEGRADED  {RESET}"
        elif st == "OFFLINE":
            status_badge = f"{RED}✗ OFFLINE   {RESET}"
        elif st == "UNKNOWN":
            status_badge = f"{DIM}? UNKNOWN   {RESET}"
        else:
            status_badge = f"{DIM}○ STOPPED   {RESET}"

        source_str = f"{DIM}{pad_visible(s['source'], col_src_w)}{RESET}"

        if s["port"]:
            loc_str = f"{CYAN}{s['port']}{RESET} {DIM}P:{s['pids'][0] if s['pids'] else ''}{RESET}"
        elif s["pids"]:
            loc_str = f"PID {s['pids'][0]}" + (f"+{len(s['pids'])-1}" if len(s["pids"]) > 1 else "")
        elif s["type"] == "remote":
            loc_str = f"{DIM}Cloud HTTPS{RESET}"
        else:
            loc_str = f"{DIM}─{RESET}"

        if s["type"] == "remote":
            ram_display = f"{DIM}Cloud{RESET}"
        else:
            mb = s["commit_mb"]
            if mb > 500:
                ram_color = RED
            elif mb > 150:
                ram_color = CORAL
            elif mb > 50:
                ram_color = AMBER
            elif mb > 0:
                ram_color = GREEN
            else:
                ram_color = DIM
            ram_display = f"{ram_color}{mb:>6.1f} MB{RESET}"

        cpu_str = f"{s['cpu']:>4.1f}%" if s["type"] != "remote" else f"{DIM}N/A{RESET}"

        row_str = (
            f" {pad_visible(num_str, 3)} "
            f"{pad_visible(s_name, 24)} "
            f"{pad_visible(status_badge, 13)} "
            f"{source_str} "
            f"{pad_visible(loc_str, 14)} "
            f"{pad_visible(ram_display, 11, 'right')} "
            f"{pad_visible(cpu_str, 6, 'right')}"
        )
        print(row_str)

    print(f"{GRAY}{'─' * W}{RESET}")
    print(f"{DIM}Tip: Enter server # (01-{len(data['servers']):02d}) or name to open Granular Control Menu.{RESET}\n")

    print(f"{DARK_GRAY}╭─ {BOLD}{WHITE}Actions & Shortcuts{RESET}{DARK_GRAY} {'─' * (W - 25)}╮{RESET}")
    toggle_txt = "Hide Repos" if data["show_local_repos"] else "Show Repos"
    bar = (
        f"  {CORAL}[1-N]{RESET} Select    {CYAN}[T]{RESET} Toggle ({toggle_txt})    "
        f"{RED}[K]{RESET} Kill All    {GREEN}[S]{RESET} Start All    "
        f"{CYAN}[P]{RESET} Ports    {AMBER}[R]{RESET} Refresh    "
        f"{INDIGO}[F]{RESET} Repair    {WHITE}[Q]{RESET} Quit  "
    )
    space_bar = W - 2 - len_visible(bar)
    print(f"{DARK_GRAY}│{RESET}{bar}{' ' * max(0, space_bar)}{DARK_GRAY}│{RESET}")
    print(f"{DARK_GRAY}╰{'─' * (W - 2)}╯{RESET}")


# ---------------------------------------------------------------------------
# Control operations (cross-platform kill / open / start)
# ---------------------------------------------------------------------------
def kill_pid_tree(pid: int) -> bool:
    """Force-kill a process tree without shell=True."""
    if IS_WIN:
        try:
            # Prefer list form – no shell injection surface
            res = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return res.returncode == 0
        except Exception:
            pass
    # Universal fallback via psutil
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except Exception:
                pass
        parent.kill()
        return True
    except Exception:
        return False


def kill_server(server_obj: Dict[str, Any]) -> List[int]:
    killed: List[int] = []
    for pid in server_obj.get("pids", []):
        try:
            if kill_pid_tree(pid):
                killed.append(pid)
        except Exception:
            pass

    patterns = derive_patterns(server_obj["name"], server_obj.get("command"), server_obj.get("args"))
    if patterns:
        for p in psutil.process_iter(["pid", "name"]):
            try:
                pname = (p.info["name"] or "").lower()
                if pname in ALLOWED_RUNNERS or "mcp" in pname:
                    cmd_str = " ".join(p.cmdline() or []).lower()
                    if any(ign in cmd_str for ign in ("mcp_cli_manager", "mcp-manager", "mcp-status", "deploy_", "inspect_")):
                        continue
                    if any(pat in cmd_str for pat in patterns):
                        if kill_pid_tree(p.info["pid"]) and p.info["pid"] not in killed:
                            killed.append(p.info["pid"])
            except Exception:
                pass
    return killed


def toggle_disable_server(s: Dict[str, Any], force_state: Optional[bool] = None) -> None:
    name = s["name"]
    cname = canon_key(name)
    currently_disabled = s.get("disabled", False)
    new_disabled = not currently_disabled if force_state is None else force_state

    updated_configs: List[str] = []
    for agent_label, path in CONFIG_TARGETS:
        if not os.path.exists(path):
            continue
        data = load_json_safe(path)
        if data is None:
            continue
        servers = _extract_servers(data)
        if not isinstance(servers, dict):
            continue
        matched_keys = [k for k in servers if canon_key(k) == cname]
        if matched_keys:
            for mk in matched_keys:
                servers[mk]["disabled"] = new_disabled
            if atomic_write_json(path, data, make_backup=True):
                updated_configs.append(agent_label)

    if new_disabled:
        killed = kill_server(s)
        print(f"\n{YELLOW}✓ Disabled '{name}' in: {', '.join(updated_configs) if updated_configs else 'configs'}.{RESET}")
        if killed:
            print(f"{DIM}Terminated process tree ({len(killed)} PIDs: {killed}).{RESET}")
    else:
        print(f"\n{GREEN}✓ Enabled '{name}' in: {', '.join(updated_configs) if updated_configs else 'configs'}.{RESET}")
    time.sleep(0.4)


def robust_rmtree(path: str) -> bool:
    def remove_readonly(func, fpath, _excinfo):
        try:
            os.chmod(fpath, stat.S_IWRITE | stat.S_IREAD)
            func(fpath)
        except Exception:
            pass

    if os.path.exists(path):
        shutil.rmtree(path, onerror=remove_readonly)
        return not os.path.exists(path)
    return True


def uninstall_server(s: Dict[str, Any], confirm: bool = True) -> bool:
    name = s["name"]
    cname = canon_key(name)
    path = s.get("path")

    print(f"\n{RED}{BOLD}╔══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{RED}{BOLD}║         ⚠️  PERMANENT CLEAN UNINSTALL & ZERO-RESIDUE WIPE        ║{RESET}")
    print(f"{RED}{BOLD}╚══════════════════════════════════════════════════════════════════╝{RESET}")
    print(f" Target Server : {BOLD}{WHITE}{name}{RESET}")
    if path:
        print(f" Disk Location : {AMBER}{path}{RESET}")
    print(" This action will:")
    print("   1. Forcefully kill all running worker processes & child trees.")
    print(f"   2. Cleanly strip '{name}' from ALL agent configs.")
    if path and os.path.exists(path):
        print("   3. Permanently wipe the directory from disk.")

    if confirm:
        ans = input(f"\n {RED}{BOLD}Are you sure you want to permanently delete and wipe '{name}'? [y/N]:{RESET} ").strip().lower()
        if ans not in ("y", "yes"):
            print(f"\n{DIM}Uninstallation cancelled.{RESET}")
            time.sleep(0.4)
            return False

    killed = kill_server(s)
    if killed:
        print(f"{RED}✓ Terminated {len(killed)} running process(es): {killed}{RESET}")

    removed_from: List[str] = []
    for agent_label, config_path in CONFIG_TARGETS:
        if not os.path.exists(config_path):
            continue
        data = load_json_safe(config_path)
        if data is None:
            continue
        servers = _extract_servers(data)
        if not isinstance(servers, dict):
            continue
        matched_keys = [k for k in list(servers.keys()) if canon_key(k) == cname]
        if matched_keys:
            for mk in matched_keys:
                del servers[mk]
            if atomic_write_json(config_path, data, make_backup=True):
                removed_from.append(agent_label)

    if removed_from:
        print(f"{GREEN}✓ Removed from agent configs: {', '.join(removed_from)}{RESET}")
    else:
        print(f"{DIM}No agent config entries found for '{name}'.{RESET}")

    if path and os.path.exists(path):
        success = robust_rmtree(path)
        if success:
            print(f"{GREEN}✓ Permanently deleted folder from disk: {path}{RESET}")
        else:
            print(f"{RED}⚠️ Could not completely delete {path}. Check for open file locks.{RESET}")
    elif path:
        print(f"{DIM}Folder {path} was not found on disk.{RESET}")

    print(f"\n{GREEN}{BOLD}✓ Clean uninstallation complete!{RESET}")
    time.sleep(0.8)
    return True


def open_server_location(s: Dict[str, Any]) -> None:
    """Cross-platform open of folder or remote URL."""
    if s["type"] == "remote":
        url = s.get("url")
        if url and url.startswith(("http://", "https://")):
            webbrowser.open(url)
            print(f"\n{CYAN}✓ Opened {url} in default browser.{RESET}")
        else:
            print(f"\n{DIM}No URL available for remote server '{s['name']}'.{RESET}")
        time.sleep(0.4)
        return

    path = s.get("path")
    if not path or not os.path.exists(path):
        raw_args = s.get("args", [])
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or [])
        except Exception:
            args = []
        for a in args:
            if isinstance(a, str) and os.path.exists(a):
                path = os.path.dirname(os.path.abspath(a))
                break

    if path and os.path.exists(path):
        if os.path.isfile(path):
            path = os.path.dirname(path)
        path = os.path.normpath(path)
        try:
            if IS_WIN:
                subprocess.Popen(["explorer.exe", path])
            elif IS_MAC:
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            print(f"\n{CYAN}✓ Opened folder: {path}{RESET}")
        except Exception as e:
            print(f"\n{AMBER}Could not open folder: {e}{RESET}")
    else:
        print(f"\n{AMBER}No local directory path found for '{s['name']}'.{RESET}")
    time.sleep(0.4)


def _find_venv_python(project_path: str) -> Optional[str]:
    candidates = [
        os.path.join(project_path, ".venv", "Scripts", "python.exe"),  # Windows
        os.path.join(project_path, ".venv", "bin", "python"),           # Unix
        os.path.join(project_path, "venv", "Scripts", "python.exe"),
        os.path.join(project_path, "venv", "bin", "python"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def start_server(s: Dict[str, Any]) -> Optional[int]:
    if s["type"] == "remote":
        print(f"{AMBER}Cannot spawn remote cloud server '{s['name']}' locally.{RESET}")
        return None

    cmd = s.get("command")
    path = s.get("path")

    if not cmd and path and os.path.exists(path):
        venv_py = _find_venv_python(path)
        if venv_py:
            for py_name in ("server.py", "main.py", "mcp_server.py", "app.py"):
                cand = os.path.join(path, py_name)
                if os.path.exists(cand):
                    cmd = venv_py
                    s["command"] = cmd
                    s["args"] = json.dumps([cand])
                    break
        if not cmd:
            pkg_json = os.path.join(path, "package.json")
            if os.path.exists(pkg_json):
                cmd = "npm"
                s["command"] = cmd
                s["args"] = json.dumps(["start"])

    if not cmd:
        print(f"{RED}No executable command found for '{s['name']}'.{RESET}")
        return None

    raw_args = s.get("args", [])
    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or [])
    except Exception:
        args = []
    raw_env = s.get("env", {})
    try:
        env_vars = json.loads(raw_env) if isinstance(raw_env, str) else (raw_env or {})
    except Exception:
        env_vars = {}

    full_env = os.environ.copy()
    full_env.update({k: str(v) for k, v in env_vars.items()})

    cmd_list = [cmd] + [str(a) for a in args]
    cwd = path if (path and os.path.exists(path)) else None

    try:
        kwargs: Dict[str, Any] = {
            "env": full_env,
            "cwd": cwd,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.PIPE,
        }
        if IS_WIN:
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(cmd_list, **kwargs)
        return proc.pid
    except Exception as e:
        print(f"{RED}Failed to start server: {e}{RESET}")
        return None


def kill_all_servers(servers: List[Dict[str, Any]]) -> List[int]:
    all_killed: List[int] = []
    for s in servers:
        if s["is_running"] and s["type"] != "remote":
            all_killed.extend(kill_server(s))
    return all_killed


def restart_server(s: Dict[str, Any]) -> None:
    print(f"\n{AMBER}Stopping server '{s['name']}'...{RESET}")
    kill_server(s)
    time.sleep(0.4)
    print(f"{CYAN}Starting server '{s['name']}'...{RESET}")
    pid = start_server(s)
    if pid:
        print(f"{GREEN}✓ Successfully restarted '{s['name']}' (New PID: {pid}){RESET}")
    time.sleep(0.4)


def run_config_repair() -> None:
    print(f"\n{INDIGO}Running automatic config repair across all agent configs...{RESET}\n")
    total_msgs = 0
    for agent, path in CONFIG_TARGETS:
        if not os.path.exists(path):
            continue
        msgs = repair_config(path, dry_run=False)
        for m in msgs:
            print(f"  {CYAN}{agent}{RESET}: {m}")
            total_msgs += 1
    if total_msgs == 0:
        print(f"  {GREEN}All readable configs look healthy. No repairs needed.{RESET}")
    else:
        print(f"\n{GREEN}Repair pass complete ({total_msgs} notes). Backups written as *.bak where changes were made.{RESET}")
    input("\nPress Enter to return...")


# ---------------------------------------------------------------------------
# Deep port audit
# ---------------------------------------------------------------------------
def deep_port_audit(data: Dict[str, Any], interactive: bool = True) -> None:
    os.system("cls" if IS_WIN else "clear")
    W = 92
    print(f"\n{CYAN}╭{'─' * (W - 2)}╮{RESET}")
    print(f"{CYAN}│  🔍 DEEP MCP NETWORK PORT AUDITOR                                                   │{RESET}")
    print(f"{CYAN}╰{'─' * (W - 2)}╯{RESET}\n")
    print(" Scanning listening TCP sockets for MCP SSE / JSON-RPC endpoints...")

    try:
        conns = [c for c in psutil.net_connections(kind="tcp") if c.status == "LISTEN" and c.laddr]
    except Exception:
        conns = []

    print(f" Found {len(conns)} listening system sockets. Probing...\n")
    results = []
    for c in conns:
        ip, port = c.laddr.ip, c.laddr.port
        # Skip very common non-MCP ports to reduce noise
        if port in (22, 53, 80, 443, 3306, 5432, 6379, 27017):
            continue
        is_mcp, clue = probe_mcp_http(ip, port, timeout=0.12)
        if is_mcp:
            pname = "unknown"
            if c.pid:
                try:
                    pname = psutil.Process(c.pid).name()
                except Exception:
                    pass
            results.append({"port": port, "ip": ip, "pid": c.pid, "pname": pname, "clue": clue})

    if not results:
        print(f" {DIM}No active MCP-like HTTP/SSE endpoints responded.{RESET}")
    else:
        print(f" {'Port':<8} {'IP':<16} {'PID':<8} {'Process':<20} {'Probe Result'}")
        print(f" {'─' * (W - 2)}")
        for r in results:
            print(f" {CYAN}:{r['port']:<7}{RESET} {r['ip']:<16} {r['pid'] or '─':<8} {r['pname']:<20} {GREEN}{r['clue']}{RESET}")

    if interactive:
        input("\nPress Enter to return to main overview...")


# ---------------------------------------------------------------------------
# Inspect / control menus
# ---------------------------------------------------------------------------
def mask_secret(val: Any) -> str:
    s = str(val)
    if len(s) > 12:
        return s[:4] + "••••••••" + s[-4:]
    if len(s) > 4:
        return s[:2] + "••••" + s[-2:]
    return "••••"


def inspect_server_details(s: Dict[str, Any], interactive: bool = True) -> None:
    os.system("cls" if IS_WIN else "clear")
    W = 86
    print(f"\n{INDIGO}╭{'─' * (W - 2)}╮{RESET}")
    print(f"{INDIGO}│  🔍 SERVER METADATA INSPECTION: {WHITE}{s['name']:<50}{RESET}{INDIGO}│{RESET}")
    print(f"{INDIGO}╰{'─' * (W - 2)}╯{RESET}\n")

    if s["type"] == "remote":
        status_str = f"{CYAN}✦ {s['status']}{RESET}  {DIM}({s.get('remote_detail', '')}){RESET}"
    else:
        status_str = (
            f"{GREEN}● RUNNING{RESET}"
            if s["is_running"]
            else (f"{YELLOW}⊘ DISABLED{RESET}" if s.get("disabled") else f"{DIM}○ READY / STOPPED{RESET}")
        )
    cfg_mode_str = (
        f"{YELLOW}DISABLED (Auto-start blocked){RESET}"
        if s.get("disabled")
        else (f"{DIM}UNCONFIGURED (Local Repo){RESET}" if s.get("is_unconfigured") else f"{GREEN}ACTIVE (Enabled){RESET}")
    )

    print(f" {BOLD}Server Name   :{RESET} {s['name']}")
    print(f" {BOLD}Current Status:{RESET} {status_str}")
    print(f" {BOLD}Config Mode   :{RESET} {cfg_mode_str}")
    print(f" {BOLD}Agent Sources :{RESET} {s.get('source')}")
    print(f" {BOLD}Server Type   :{RESET} {s['type'].upper()}")
    print(f" {BOLD}Project Folder:{RESET} {s.get('path') or 'N/A'}")
    print(f" {BOLD}URL           :{RESET} {s.get('url') or 'N/A'}")
    print(f" {BOLD}Launch Command:{RESET} {s.get('command') or 'N/A'}")

    raw_args = s.get("args", [])
    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or [])
    except Exception:
        args = []
    if args:
        print(f" {BOLD}Arguments     :{RESET}")
        for a in args:
            print(f"   • {a}")
    else:
        print(f" {BOLD}Arguments     :{RESET} (none)")

    raw_env = s.get("env", {})
    try:
        env_vars = json.loads(raw_env) if isinstance(raw_env, str) else (raw_env or {})
    except Exception:
        env_vars = {}
    if env_vars:
        print(f" {BOLD}Environment Variables:{RESET}")
        for k, v in env_vars.items():
            k_lower = k.lower()
            if any(sec in k_lower for sec in ("token", "key", "secret", "auth", "pass", "pat")):
                val_disp = f"{AMBER}{mask_secret(v)}{RESET} {DIM}(Protected Secret){RESET}"
            else:
                val_disp = str(v)
            print(f"   • {k} = {val_disp}")
    else:
        print(f" {BOLD}Environment   :{RESET} (standard system environment)")

    if s["pids"]:
        print(f"\n {BOLD}Active Process Tree ({len(s['pids'])} PIDs):{RESET}")
        for pid in s["pids"]:
            try:
                p = psutil.Process(pid)
                mi = p.memory_info()
                priv = getattr(mi, "private", mi.rss) / (1024 * 1024)
                print(f"   • PID {CYAN}{pid}{RESET} [{p.name()}] - RAM: {GREEN}{priv:.1f} MB{RESET} - CMD: {DIM}{' '.join(p.cmdline()[:3])}{RESET}")
            except Exception:
                print(f"   • PID {CYAN}{pid}{RESET} (Process terminated)")

    if interactive:
        input("\nPress Enter to return to Server Control Menu...")


def server_control_menu(target_identifier: Any) -> None:
    while True:
        data = get_snapshot()
        s = None
        if isinstance(target_identifier, int) or (isinstance(target_identifier, str) and target_identifier.isdigit()):
            t_num = int(target_identifier)
            s = next((x for x in data["servers"] if x["num"] == t_num), None)
        else:
            q = canon_key(target_identifier)
            s = next((x for x in data["servers"] if q == canon_key(x["name"])), None)
            if not s:
                s = next((x for x in data["servers"] if q in canon_key(x["name"])), None)

        if not s:
            print(f"\n{RED}Server '{target_identifier}' not found.{RESET}")
            time.sleep(0.4)
            break

        target_identifier = s["name"]
        os.system("cls" if IS_WIN else "clear")
        W = 86

        if s["status"] == "RUNNING":
            status_badge = f"{GREEN}● RUNNING{RESET}  (PIDs: {s.get('pids', [])})"
        elif s["status"] == "DISABLED (RUNNING)":
            status_badge = f"{CORAL}⊘ LINGERING (Process running despite disabled config!){RESET}"
        elif s.get("disabled"):
            status_badge = f"{YELLOW}■ DISABLED IN CONFIG{RESET}"
        elif s.get("is_unconfigured"):
            status_badge = f"{DIM}○ READY (Local Repo on Disk){RESET}"
        elif s["type"] == "remote":
            status_badge = f"{CYAN}✦ {s['status']}{RESET}  {DIM}{s.get('remote_detail', '')}{RESET}"
        else:
            status_badge = f"{DIM}○ STOPPED{RESET}"

        if s.get("is_unconfigured"):
            cfg_status = f"{DIM}UNCONFIGURED (Downloaded to disk, not added to agent config){RESET}"
        elif s.get("disabled"):
            cfg_status = f"{YELLOW}DISABLED (Auto-start blocked across all agents){RESET}"
        else:
            cfg_status = f"{GREEN}ACTIVE (Enabled in agent configs){RESET}"

        print(f"\n{CORAL}╭─ {BOLD}Granular Control: {WHITE}{s['name']}{RESET}{CORAL} {'─' * max(0, W - 22 - len(s['name']))}╮{RESET}")
        print(f"{CORAL}│{RESET}  {BOLD}Status:{RESET}       {status_badge}")
        print(f"{CORAL}│{RESET}  {BOLD}Resources:{RESET}    RAM Commit: {CYAN}{s.get('commit_mb', 0.0):.1f} MB{RESET}   |   CPU: {CYAN}{s.get('cpu', 0.0):.1f}%{RESET}")
        print(f"{CORAL}│{RESET}  {BOLD}Config Mode:{RESET}  {cfg_status}")
        src_str = ", ".join(s.get("sources", [])) if s.get("sources") else "Local Disk"
        print(f"{CORAL}│{RESET}  {BOLD}Sources:{RESET}      {src_str}")
        path_display = s.get("path") or s.get("url") or "(none)"
        if len(str(path_display)) > 65:
            path_display = str(path_display)[:62] + "..."
        print(f"{CORAL}│{RESET}  {BOLD}Path / URL:{RESET}   {DIM}{path_display}{RESET}")
        cmd_val = s.get("command")
        cmd_display = str(cmd_val) if cmd_val else "(none - not configured)"
        raw_args = s.get("args", [])
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or [])
        except Exception:
            args = []
        if args and cmd_val:
            cmd_display += " " + " ".join(str(a) for a in args)
        if len(cmd_display) > 65:
            cmd_display = cmd_display[:62] + "..."
        print(f"{CORAL}│{RESET}  {BOLD}Command:{RESET}      {DIM}{cmd_display}{RESET}")
        print(f"{CORAL}╰{'─' * (W - 2)}╯{RESET}\n")

        print(f" {BOLD}{WHITE}Available Operations for [{s['name']}]:{RESET}")
        print(f"  {GREEN}[1]{RESET} {BOLD}Start Server{RESET}           {DIM}- Spawn process if runnable script detected{RESET}")
        print(f"  {RED}[2]{RESET} {BOLD}Stop / Kill Server{RESET}     {DIM}- Forcefully terminate process & all child workers{RESET}")
        print(f"  {AMBER}[3]{RESET} {BOLD}Restart Server{RESET}         {DIM}- Terminate tree and immediately re-launch{RESET}")
        print(f"  {YELLOW}[4]{RESET} {BOLD}Disable in Config{RESET}      {DIM}- Set 'disabled: true' across all agent configs & kill{RESET}")
        print(f"  {CYAN}[5]{RESET} {BOLD}Enable in Config{RESET}       {DIM}- Set 'disabled: false' across all agent configs{RESET}")
        print(f"  {INDIGO}[6]{RESET} {BOLD}Inspect Full Details{RESET}   {DIM}- View args, masked env vars, full process tree{RESET}")
        print(f"  {RED}[7]{RESET} {BOLD}Clean Uninstall{RESET}        {DIM}- Wipe directory, remove configs & kill (Zero Residue){RESET}")
        print(f"  {CYAN}[O]{RESET} {BOLD}Open Folder / URL{RESET}      {DIM}- Open directory or remote URL{RESET}")
        print(f"  {AMBER}[R]{RESET} {BOLD}Refresh Status{RESET}         {DIM}- Re-query live PIDs, memory, remote health{RESET}")
        print(f"  {WHITE}[B]{RESET} {BOLD}Back to Overview{RESET}       {DIM}- Return to main server table{RESET}\n")

        try:
            choice = input(f" {BOLD}{CORAL}Select operation [1-7, O, R, B]:{RESET} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if choice in ("b", "back", "q", "exit"):
            break
        elif choice in ("r", "refresh"):
            continue
        elif choice in ("o", "open", "folder"):
            open_server_location(s)
        elif choice in ("1", "start"):
            if s["is_running"] and s["type"] != "remote":
                print(f"\n{AMBER}'{s['name']}' is already running (PIDs: {s.get('pids')}).{RESET}")
                time.sleep(0.4)
            else:
                pid = start_server(s)
                if pid:
                    print(f"\n{GREEN}✓ Started '{s['name']}' (New PID: {pid}){RESET}")
                time.sleep(0.4)
        elif choice in ("2", "stop", "kill"):
            killed = kill_server(s)
            if killed:
                print(f"\n{RED}✓ Stopped '{s['name']}' (Forcefully terminated PIDs: {killed}){RESET}")
            else:
                print(f"\n{DIM}'{s['name']}' was not running.{RESET}")
            time.sleep(0.4)
        elif choice in ("3", "restart"):
            restart_server(s)
        elif choice in ("4", "disable"):
            toggle_disable_server(s, force_state=True)
        elif choice in ("5", "enable"):
            toggle_disable_server(s, force_state=False)
        elif choice in ("6", "inspect", "info", "details"):
            inspect_server_details(s)
        elif choice in ("7", "uninstall", "delete", "remove", "wipe"):
            deleted = uninstall_server(s)
            if deleted:
                break
        else:
            print(f"\n{RED}Invalid selection. Choose 1-7, O, R, or B.{RESET}")
            time.sleep(0.4)


# ---------------------------------------------------------------------------
# Interactive loop + CLI entry
# ---------------------------------------------------------------------------
def interactive_loop() -> None:
    prefs = load_prefs()
    show_local_repos = prefs.get("show_local_repos", True)

    while True:
        data = get_snapshot(show_local_repos=show_local_repos)
        render_cli(data)

        try:
            choice = input(f" {BOLD}{CORAL}Select server # (1-{len(data['servers'])}) or action:{RESET} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting MCP Manager.")
            break

        if choice in ("q", "exit", "quit"):
            print("\nExiting MCP Manager.")
            break
        elif choice in ("r", "refresh", ""):
            continue
        elif choice in ("t", "toggle"):
            show_local_repos = not show_local_repos
            prefs["show_local_repos"] = show_local_repos
            save_prefs(prefs)
            continue
        elif choice in ("p", "ports"):
            deep_port_audit(data, interactive=True)
        elif choice in ("f", "fix", "repair"):
            run_config_repair()
        elif choice in ("k", "kill-all"):
            confirm = input(f"\n{RED}{BOLD}Force kill ALL running MCP servers? [y/N]:{RESET} ").strip().lower()
            if confirm == "y":
                killed = kill_all_servers(data["servers"])
                print(f"{RED}Terminated {len(killed)} process(es): {killed}{RESET}")
                time.sleep(0.4)
        elif choice in ("s", "start-all"):
            for s in data["servers"]:
                if not s["is_running"] and not s.get("disabled") and s["type"] != "remote":
                    start_server(s)
            print(f"{GREEN}Spawned all enabled servers.{RESET}")
            time.sleep(0.4)
        elif choice.isdigit():
            server_control_menu(int(choice))
        else:
            matched = [s for s in data["servers"] if canon_key(choice) in canon_key(s["name"])]
            if matched:
                server_control_menu(matched[0]["name"])
            else:
                print(f"{RED}Unrecognized input: '{choice}'. Enter server #, name, T, K, S, P, F, R, or Q.{RESET}")
                time.sleep(0.4)


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
        elif cmd in ("open", "folder") and len(sys.argv) > 2:
            target = sys.argv[2]
            s = next((x for x in data["servers"] if canon_key(target) in canon_key(x["name"])), None)
            if s:
                open_server_location(s)
            else:
                print(f"Server '{target}' not found.")
        elif cmd in ("uninstall", "remove", "delete") and len(sys.argv) > 2:
            target = sys.argv[2]
            s = next((x for x in data["servers"] if canon_key(target) in canon_key(x["name"])), None)
            if s:
                uninstall_server(s)
            else:
                print(f"Server '{target}' not found.")
        elif cmd == "restart" and len(sys.argv) > 2:
            target = sys.argv[2]
            s = next((x for x in data["servers"] if canon_key(target) in canon_key(x["name"])), None)
            if s:
                restart_server(s)
            else:
                print(f"Server '{target}' not found.")
        elif cmd in ("inspect", "info") and len(sys.argv) > 2:
            target = sys.argv[2]
            s = next((x for x in data["servers"] if canon_key(target) in canon_key(x["name"])), None)
            if s:
                inspect_server_details(s, interactive=False)
            else:
                print(f"Server '{target}' not found.")
        elif cmd == "kill" and len(sys.argv) > 2:
            target = sys.argv[2]
            s = next((x for x in data["servers"] if canon_key(target) in canon_key(x["name"])), None)
            if s:
                killed = kill_server(s)
                print(f"Killed '{s['name']}' (PIDs: {killed})")
            else:
                print(f"Server '{target}' not found.")
        elif cmd == "start" and len(sys.argv) > 2:
            target = sys.argv[2]
            s = next((x for x in data["servers"] if canon_key(target) in canon_key(x["name"])), None)
            if s:
                pid = start_server(s)
                print(f"Started '{s['name']}' (PID {pid})")
            else:
                print(f"Server '{target}' not found.")
        elif cmd == "disable" and len(sys.argv) > 2:
            target = sys.argv[2]
            s = next((x for x in data["servers"] if canon_key(target) in canon_key(x["name"])), None)
            if s:
                toggle_disable_server(s, force_state=True)
            else:
                print(f"Server '{target}' not found.")
        elif cmd == "enable" and len(sys.argv) > 2:
            target = sys.argv[2]
            s = next((x for x in data["servers"] if canon_key(target) in canon_key(x["name"])), None)
            if s:
                toggle_disable_server(s, force_state=False)
            else:
                print(f"Server '{target}' not found.")
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
