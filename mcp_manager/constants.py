# -*- coding: utf-8 -*-
"""Constants, ANSI color palettes, platform detection, and default paths."""
from __future__ import annotations
import os
import sys
import platform

VERSION = "v3.7 (Modular Architecture & Engine Package)"

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
PLATFORM = platform.system().lower()

if IS_WIN:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
        os.system("")
    except Exception:
        pass

CORAL = "\033[38;2;255;110;110m"
AMBER = "\033[38;2;255;170;51m"
GREEN = "\033[38;2;80;220;120m"
CYAN = "\033[38;2;77;208;225m"
INDIGO = "\033[38;2;129;140;248m"
WHITE = "\033[38;2;240;240;245m"
GRAY = "\033[38;2;140;140;150m"
DARK_GRAY = "\033[38;2;70;70;80m"
RED = "\033[38;2;255;85;85m"
YELLOW = "\033[38;2;255;215;0m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

HOME = os.path.expanduser("~")
APPDATA = os.environ.get("APPDATA", "")
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
XDG_CONFIG = os.environ.get("XDG_CONFIG_HOME", os.path.join(HOME, ".config"))

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFS_FILE = os.path.join(_ROOT_DIR, ".mcp_prefs.json")
HEALTH_CACHE_FILE = os.path.join(_ROOT_DIR, ".mcp_health_cache.json")

GENERIC_WORDS = {
    "server", "mcp", "service", "app", "tool", "run", "start",
    "python", "node", "cmd", "powershell", "bash", "sh", "npx",
    "uvx", "local", "remote", "index", "main", "cli", "core",
}

ALLOWED_RUNNERS = {
    "node.exe", "node", "python.exe", "python", "python3", "python3.exe",
    "uvx.exe", "uvx", "npx.exe", "npx", "deno.exe", "deno", "bun.exe", "bun",
    "cmd.exe", "powershell.exe", "pwsh.exe", "pwsh", "bash", "sh",
}
