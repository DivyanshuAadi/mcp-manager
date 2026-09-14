# -*- coding: utf-8 -*-
"""String formatting, canonical keys, preference management, and atomic JSON I/O."""
from __future__ import annotations
import os
import re
import json
import tempfile
from typing import Any
from .constants import PREFS_FILE

_ANSI_STRIP_RE = re.compile(r"\x1b\[[0-9;]*m")

def len_visible(text: str) -> int:
    """Return visible length of string, ignoring ANSI escape codes."""
    return len(_ANSI_STRIP_RE.sub("", text))

def pad_visible(text: str, width: int, align: str = "left") -> str:
    """Pad string to visible width, preserving ANSI escape codes."""
    vlen = len_visible(text)
    pad = max(0, width - vlen)
    if align == "right":
        return (" " * pad) + text
    return text + (" " * pad)

def normalize_server_key(name: Any) -> str:
    """
    Unified canonical key for MCP servers.
    Strips npm scope, prefixes, suffixes, and non-alphanumeric characters.
    """
    if not name:
        return ""
    clean = str(name).lower().strip()
    for prefix in ("@modelcontextprotocol/server-", "@modelcontextprotocol/", "server-", "mcp-", "mcpserver-"):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
    for suffix in ("-mcp", "_mcp", "-server", "_server"):
        if clean.endswith(suffix):
            clean = clean[:-len(suffix)]
    clean_alpha = re.sub(r"[^a-z0-9]", "", clean)
    for prefix in ("mcpserver", "server", "mcp"):
        if clean_alpha.startswith(prefix) and len(clean_alpha) > len(prefix):
            clean_alpha = clean_alpha[len(prefix):]
    return clean_alpha

canon_key = normalize_server_key
normalize_mcp_key = normalize_server_key

def load_prefs() -> dict[str, Any]:
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"show_local_repos": True}

def save_prefs(prefs: dict[str, Any]) -> None:
    try:
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
    except Exception:
        pass

def atomic_write_json(path: str, data: Any, indent: int = 2) -> bool:
    """Write JSON to a temporary file in the same directory, then rename atomically with .bak backup."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)

    bak_path = path + ".bak"
    if os.path.exists(path):
        try:
            shutil.copy2(path, bak_path)
        except Exception:
            pass

    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, path)
        return True
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False

def load_json_safe(path: str) -> dict | list | None:
    """Safely load JSON, returning None if missing, malformed, or unreadable."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def mask_secret(val: Any) -> str:
    s = str(val)
    if len(s) <= 8:
        return "********"
    return s[:4] + "*" * (len(s) - 8) + s[-4:]
