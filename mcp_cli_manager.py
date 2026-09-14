#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✦ MCP 360° ENGINE (v3.7 Modular Architecture Runner)
Universal Coding Agent Inspector & Process Controller.
"""
from __future__ import annotations
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_manager.cli import main

if __name__ == "__main__":
    main()
