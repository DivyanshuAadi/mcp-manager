# -*- coding: utf-8 -*-
"""MCP 360° Engine - Modular Package"""
from .constants import VERSION
from .snapshot import get_snapshot
from .ui import render_cli, interactive_loop
from .cli import main

__version__ = VERSION
__all__ = ["get_snapshot", "render_cli", "interactive_loop", "main"]
