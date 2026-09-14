# -*- coding: utf-8 -*-
"""Remote server health probing, SSE endpoint detection, and persistent health cache."""
from __future__ import annotations
import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import Any
import psutil
from .constants import HEALTH_CACHE_FILE

_REMOTE_HEALTH_CACHE: dict[str, tuple[float, str, str]] = {}
_REMOTE_CACHE_LOCK = threading.Lock()

def _load_disk_health_cache() -> None:
    global _REMOTE_HEALTH_CACHE
    if os.path.exists(HEALTH_CACHE_FILE):
        try:
            with open(HEALTH_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list) and len(v) == 3:
                        _REMOTE_HEALTH_CACHE[k] = (float(v[0]), str(v[1]), str(v[2]))
        except Exception:
            pass

def _save_disk_health_cache() -> None:
    try:
        data = {k: list(v) for k, v in _REMOTE_HEALTH_CACHE.items()}
        with open(HEALTH_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

_load_disk_health_cache()

def probe_mcp_http(ip: str, port: int, timeout: float = 0.15) -> tuple[bool, str | None]:
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
                    "User-Agent": "MCP-Manager/3.7",
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

def check_remote_health(url: str, timeout: float = 1.5) -> tuple[str, str]:
    """Check reachability and response code for remote MCP server."""
    if not url or not url.startswith(("http://", "https://")):
        return "UNKNOWN", "no valid URL"

    try:
        req = Request(
            url.rstrip("/") + "/",
            headers={"User-Agent": "MCP-Manager/3.7", "Accept": "application/json, text/event-stream"},
            method="GET",
        )
        with urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read(1024).decode("utf-8", errors="ignore")
            if 200 <= status < 400:
                if "jsonrpc" in body.lower() or "mcp" in body.lower() or status == 200:
                    return "ONLINE", f"HTTP {status}"
                return "DEGRADED", f"HTTP {status} (unexpected body)"
            return "DEGRADED", f"HTTP {status}"
    except HTTPError as e:
        if e.code in (400, 401, 403, 405, 406):
            return "ONLINE", f"HTTP {e.code} (reachable)"
        return "DEGRADED", f"HTTP {e.code}"
    except (URLError, TimeoutError, OSError) as e:
        return "OFFLINE", str(e)[:60]

def batch_check_remote_health(urls: list[str], timeout: float = 0.8) -> dict[str, tuple[str, str]]:
    """Check remote server endpoints concurrently with 60s persistent disk cache."""
    results: dict[str, tuple[str, str]] = {}
    now = time.time()
    to_fetch: list[str] = []

    with _REMOTE_CACHE_LOCK:
        for u in urls:
            if u in _REMOTE_HEALTH_CACHE:
                ts, st, dt = _REMOTE_HEALTH_CACHE[u]
                if now - ts < 60.0:
                    results[u] = (st, dt)
                    continue
            to_fetch.append(u)

    if not to_fetch:
        return results

    def _worker(u: str) -> tuple[str, str, str]:
        st, dt = check_remote_health(u, timeout=timeout)
        return u, st, dt

    with ThreadPoolExecutor(max_workers=min(4, len(to_fetch))) as executor:
        futures = [executor.submit(_worker, u) for u in to_fetch]
        for f in as_completed(futures):
            try:
                u, st, dt = f.result()
                results[u] = (st, dt)
                with _REMOTE_CACHE_LOCK:
                    _REMOTE_HEALTH_CACHE[u] = (time.time(), st, dt)
            except Exception:
                pass

    with _REMOTE_CACHE_LOCK:
        for u in to_fetch:
            if u not in results:
                results[u] = ("UNKNOWN", "timeout")
        _save_disk_health_cache()

    return results

def get_mcp_listening_ports() -> list[dict[str, Any]]:
    """Enumerate all active TCP listening ports and check for MCP servers."""
    ports: list[dict[str, Any]] = []
    try:
        conns = psutil.net_connections(kind="tcp")
    except Exception:
        return ports

    seen: set[int] = set()
    for c in conns:
        if c.status != psutil.CONN_LISTEN:
            continue
        port = c.laddr.port
        if port in seen or port < 1024:
            continue
        seen.add(port)
        pname = ""
        if c.pid:
            try:
                pname = psutil.Process(c.pid).name()
            except Exception:
                pass
        ports.append({
            "port": port,
            "ip": c.laddr.ip,
            "pid": c.pid,
            "process_name": pname,
        })
    return ports
