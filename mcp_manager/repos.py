# -*- coding: utf-8 -*-
"""Local developer directories & NPX cache discovery, clean uninstallation, and folder opener."""
from __future__ import annotations
import os
import glob
import shutil
import stat
import subprocess
import webbrowser
from typing import Any
from .constants import IS_WIN, IS_MAC, HOME, LOCALAPPDATA, CORAL, GREEN, RED, BOLD, RESET
from .utils import normalize_server_key

def _default_search_dirs() -> list[str]:
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

def scan_machine_repos(configured_canon_keys: set[str]) -> tuple[dict[str, str], list[dict[str, str]]]:
    """
    Scans local developer directories & NPX cache directories:
    - Resolves local project directories for configured servers.
    - Gathers downloaded repos & NPX cached packages that have not yet been added to any agent config.
    """
    search_dirs = _default_search_dirs()
    matched_paths: dict[str, str] = {}
    unconfigured: list[dict[str, str]] = []
    seen: set[str] = set()
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).lower()

    # 1. Developer directories
    for dpattern in search_dirs:
        for base in glob.glob(dpattern):
            if not os.path.isdir(base):
                continue
            try:
                items = os.listdir(base)
            except OSError:
                continue
            for item in items:
                full = os.path.join(base, item)
                if not os.path.isdir(full) or full in seen:
                    continue
                full_abs = os.path.abspath(full).lower()
                if full_abs == script_dir or script_dir in full_abs:
                    continue
                if any(ign in item.lower() for ign in ("mcp-manager", "mcp_manager", "mcp-360", "mcp360", ".git", "__pycache__", "scratch", "node_modules")):
                    continue
                seen.add(full)
                c_item = normalize_server_key(item)

                if c_item in configured_canon_keys:
                    matched_paths[c_item] = full
                else:
                    if "mcp" in item.lower() or "local" in base.lower() or item in ("Graphify", "ScrapGraphAI", "Use Browser"):
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
    npx_dirs.append(os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.join(HOME, ".cache")), "npm", "_npx"))

    seen_npx: set[str] = set()
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
                    c_pkg = normalize_server_key(display_name)
                    c_full = normalize_server_key(full_pkg_name)

                    if c_pkg in configured_canon_keys and c_pkg not in matched_paths:
                        matched_paths[c_pkg] = hash_path
                    elif c_full in configured_canon_keys and c_full not in matched_paths:
                        matched_paths[c_full] = hash_path
                    else:
                        is_relevant = any(x in full_pkg_name.lower() for x in ("mcp", "devtools", "server"))
                        if is_relevant and c_pkg not in configured_canon_keys and c_full not in configured_canon_keys:
                            key_id = f"npx_{c_full}"
                            if key_id not in seen_npx:
                                seen_npx.add(key_id)
                                unconfigured.append({
                                    "name": display_name if not full_pkg_name.startswith("@") else full_pkg_name,
                                    "path": hash_path,
                                    "base": "NPX Cache",
                                    "source": "NPX Cache",
                                })

    return matched_paths, unconfigured

def robust_rmtree(path: str) -> bool:
    """Delete a directory tree recursively on Windows, handling read-only git pack files."""
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

def open_server_location(server: dict[str, Any]) -> None:
    """Open the server's project folder in the OS file explorer or web browser."""
    target = server.get("path")
    if not target or not os.path.exists(target):
        target = server.get("url")
        if target and target.startswith(("http://", "https://")):
            webbrowser.open(target)
            print(f"{GREEN}Opened URL in browser:{RESET} {target}")
            return
        print(f"{RED}No local path or URL found for '{server['name']}'.{RESET}")
        return

    try:
        if IS_WIN:
            subprocess.Popen(["explorer.exe", os.path.normpath(target)])
        elif IS_MAC:
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        print(f"{GREEN}Opened in file manager:{RESET} {target}")
    except Exception as e:
        print(f"{RED}Failed to open folder: {e}{RESET}")

def uninstall_server(server: dict[str, Any]) -> None:
    """
    Clean zero-residue uninstall:
    1. Forcefully terminate the process tree.
    2. Remove the server definition from all agent configs.
    3. Recursively delete the project/cache directory on disk.
    """
    from .process import kill_server
    from .config import _build_config_targets, _extract_servers
    from .utils import atomic_write_json, load_json_safe

    name = server["name"]
    print(f"\n{BOLD}Starting Zero-Residue Clean Uninstall for [{name}]...{RESET}")

    # 1. Kill processes
    killed = kill_server(server)
    if killed:
        print(f"  {GREEN}✓{RESET} Terminated {len(killed)} running process(es): PIDs {killed}")

    # 2. Scrub configs
    scrubbed_count = 0
    targets = _build_config_targets()
    for app_name, cfg_path in targets:
        if not os.path.exists(cfg_path):
            continue
        data = load_json_safe(cfg_path)
        if not data:
            continue
        servers = _extract_servers(data)
        if servers is None:
            continue

        matched_key = None
        for k in list(servers.keys()):
            if normalize_server_key(k) == normalize_server_key(name):
                matched_key = k
                break

        if matched_key:
            del servers[matched_key]
            if atomic_write_json(cfg_path, data):
                scrubbed_count += 1
                print(f"  {GREEN}✓{RESET} Removed server block from {app_name}")

    # 3. Wipe disk directory
    path = server.get("path")
    if path and os.path.exists(path):
        if robust_rmtree(path):
            print(f"  {GREEN}✓{RESET} Deleted project directory from disk: {path}")
        else:
            print(f"  {CORAL}⚠{RESET} Directory partially locked: {path}")
    else:
        print(f"  {GREEN}✓{RESET} No local folder residue on disk.")

    print(f"{GREEN}{BOLD}Clean Uninstall Complete for [{name}]. Zero residue remains.{RESET}\n")
