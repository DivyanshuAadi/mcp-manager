# -*- coding: utf-8 -*-
"""Multi-agent configuration discovery, JSON validation, repair, and toggle control."""
from __future__ import annotations
import os
import glob
from typing import Any
from .constants import IS_WIN, IS_MAC, HOME, APPDATA, LOCALAPPDATA, XDG_CONFIG, GREEN, RED, AMBER, BOLD, RESET
from .utils import normalize_server_key, load_json_safe, atomic_write_json

def _build_config_targets() -> list[tuple[str, str]]:
    """Build complete list of agent configuration files across Windows, macOS, and Linux."""
    targets: list[tuple[str, str]] = []

    # Windows Roaming/Local
    if IS_WIN:
        if APPDATA:
            targets.extend([
                ("Claude Desktop (Win)", os.path.join(APPDATA, "Claude", "claude_desktop_config.json")),
                ("Cursor (Global)", os.path.join(APPDATA, "Cursor", "User", "globalStorage", "cursor.mcp", "config.json")),
                ("Windsurf", os.path.join(APPDATA, "Code", "User", "globalStorage", "codeium.windsurf", "mcp_config.json")),
                ("Cline (VS Code)", os.path.join(APPDATA, "Code", "User", "globalStorage", "saoudrizwan.claude-dev", "settings", "cline_mcp_settings.json")),
                ("Roo Code (VS Code)", os.path.join(APPDATA, "Code", "User", "globalStorage", "rooveterinaryinc.roo-cline", "settings", "cline_mcp_settings.json")),
            ])
        if LOCALAPPDATA:
            targets.extend([
                ("Claude Code (Win)", os.path.join(LOCALAPPDATA, "Anthropic", "ClaudeCode", "config.json")),
            ])

    # macOS
    if IS_MAC:
        mac_app_support = os.path.join(HOME, "Library", "Application Support")
        targets.extend([
            ("Claude Desktop (Mac)", os.path.join(mac_app_support, "Claude", "claude_desktop_config.json")),
            ("Cursor (Mac)", os.path.join(mac_app_support, "Cursor", "User", "globalStorage", "cursor.mcp", "config.json")),
            ("Windsurf (Mac)", os.path.join(mac_app_support, "Code", "User", "globalStorage", "codeium.windsurf", "mcp_config.json")),
            ("Cline (Mac)", os.path.join(mac_app_support, "Code", "User", "globalStorage", "saoudrizwan.claude-dev", "settings", "cline_mcp_settings.json")),
            ("Roo Code (Mac)", os.path.join(mac_app_support, "Code", "User", "globalStorage", "rooveterinaryinc.roo-cline", "settings", "cline_mcp_settings.json")),
        ])

    # Linux / XDG
    if XDG_CONFIG:
        targets.extend([
            ("Claude Desktop (Linux)", os.path.join(XDG_CONFIG, "Claude", "claude_desktop_config.json")),
            ("Cursor (Linux)", os.path.join(XDG_CONFIG, "Cursor", "User", "globalStorage", "cursor.mcp", "config.json")),
            ("Zed", os.path.join(XDG_CONFIG, "zed", "settings.json")),
            ("Continue", os.path.join(HOME, ".continue", "config.json")),
        ])

    # Universal / Cross-Platform User Home
    targets.extend([
        ("Claude Code", os.path.join(HOME, ".claude", "config.json")),
        ("Claude Global", os.path.join(HOME, ".claude.json")),
        ("Antigravity IDE", os.path.join(HOME, ".gemini", "config", "mcp_config.json")),
        ("Antigravity Fallback", os.path.join(HOME, ".antigravity", "mcp_config.json")),
    ])

    return targets

def _extract_servers(data: Any) -> dict[str, Any] | None:
    """Extract server dictionary from various agent JSON schemas."""
    if not isinstance(data, dict):
        return None
    for key in ("mcpServers", "mcp_servers", "servers"):
        val = data.get(key)
        if isinstance(val, dict):
            return val
    return None

def scan_agent_configs() -> tuple[dict[str, Any], list[str]]:
    """Scan all installed coding agent configs and aggregate server declarations."""
    aggregated: dict[str, Any] = {}
    active_agents: list[str] = []
    targets = _build_config_targets()

    for app_name, cfg_path in targets:
        data = load_json_safe(cfg_path)
        if not data:
            continue
        servers = _extract_servers(data)
        if servers is None:
            continue

        if app_name not in active_agents:
            active_agents.append(app_name)

        for s_name, s_cfg in servers.items():
            if not isinstance(s_cfg, dict):
                continue
            norm_name = s_name.strip()
            is_dis = bool(s_cfg.get("disabled", False))

            if norm_name not in aggregated:
                is_remote = "url" in s_cfg or s_cfg.get("type") in ("sse", "remote", "http")
                aggregated[norm_name] = {
                    "command": s_cfg.get("command"),
                    "args": s_cfg.get("args") or [],
                    "env": s_cfg.get("env") or {},
                    "url": s_cfg.get("url"),
                    "type": "remote" if is_remote else "stdio",
                    "disabled": is_dis,
                    "disabled_in": [app_name] if is_dis else [],
                    "enabled_in": [] if is_dis else [app_name],
                    "sources_list": [app_name],
                    "source": app_name,
                    "description": s_cfg.get("description", ""),
                }
            else:
                existing = aggregated[norm_name]
                if app_name not in existing["sources_list"]:
                    existing["sources_list"].append(app_name)
                if is_dis:
                    if app_name not in existing["disabled_in"]:
                        existing["disabled_in"].append(app_name)
                else:
                    if app_name not in existing["enabled_in"]:
                        existing["enabled_in"].append(app_name)

                existing["disabled"] = (len(existing["enabled_in"]) == 0) and (len(existing["disabled_in"]) > 0)
                if not existing["command"] and s_cfg.get("command"):
                    existing["command"] = s_cfg.get("command")
                if not existing["url"] and s_cfg.get("url"):
                    existing["url"] = s_cfg.get("url")

    return aggregated, active_agents

def repair_config(path: str, dry_run: bool = False) -> list[str]:
    """Inspect and repair malformed JSON agent configurations atomically."""
    messages: list[str] = []
    data = load_json_safe(path)
    if data is None:
        messages.append(f"unreadable or non-object JSON: {path}")
        return messages

    servers = _extract_servers(data)
    if servers is None:
        return messages

    changed = False
    for sname, sdata in list(servers.items()):
        if not isinstance(sdata, dict):
            messages.append(f"removed invalid server '{sname}' (not a dict)")
            del servers[sname]
            changed = True
            continue

        if "disabled" in sdata and not isinstance(sdata["disabled"], bool):
            sdata["disabled"] = bool(sdata["disabled"])
            messages.append(f"coerced 'disabled' to boolean for '{sname}'")
            changed = True

        if "command" in sdata and not isinstance(sdata["command"], str):
            messages.append(f"coerced 'command' to str for '{sname}'")
            sdata["command"] = str(sdata["command"])
            changed = True

        if "args" in sdata and not isinstance(sdata["args"], list):
            messages.append(f"wrapped non-list 'args' for '{sname}'")
            sdata["args"] = [str(sdata["args"])]
            changed = True

    if changed and not dry_run:
        if atomic_write_json(path, data):
            messages.append(f"saved repaired configuration: {path}")
        else:
            messages.append(f"FAILED to save: {path}")

    return messages

def run_config_repair() -> None:
    """Scan and repair all discovered agent config files across the system."""
    targets = _build_config_targets()
    found = 0
    repaired = 0

    print(f"\n{BOLD}=== Automatic MCP Configuration Repair ==={RESET}")
    for app_name, path in targets:
        if not os.path.exists(path):
            continue
        found += 1
        msgs = repair_config(path, dry_run=False)
        if msgs:
            repaired += 1
            print(f"  {GREEN}✓{RESET} {BOLD}{app_name}{RESET} ({path}):")
            for m in msgs:
                print(f"      • {m}")

    if repaired == 0:
        print(f"  {GREEN}All {found} discovered configuration files are healthy.{RESET}\n")
    else:
        print(f"\n  {GREEN}Repaired {repaired} / {found} configuration file(s).{RESET}\n")

def toggle_disable_server(server: dict[str, Any], force_state: bool | None = None) -> bool:
    """Toggle or set the 'disabled' field across all agent configs holding this server."""
    from .process import kill_server

    name = server["name"]
    current_disabled = server.get("disabled", False)
    new_state = (not current_disabled) if force_state is None else force_state

    targets = _build_config_targets()
    modified_count = 0

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
        for k in servers:
            if normalize_server_key(k) == normalize_server_key(name):
                matched_key = k
                break

        if matched_key:
            servers[matched_key]["disabled"] = new_state
            if atomic_write_json(cfg_path, data):
                modified_count += 1

    if new_state:
        kill_server(server)

    action_label = "DISABLED" if new_state else "ENABLED"
    print(f"\n{GREEN}Successfully {action_label} [{name}] across {modified_count} agent config(s).{RESET}")
    return new_state
