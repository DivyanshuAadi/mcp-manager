import os
import sys
import re
import json
import glob
import time
import socket
import sqlite3
import subprocess
import urllib.request
import urllib.error

# Ensure UTF-8 output and enable Windows ANSI virtual terminal
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

if os.name == 'nt':
    os.system('')  # enables ANSI colors in Windows cmd/powershell

try:
    import psutil
except ImportError:
    print("Error: psutil is required. Please install it with 'pip install psutil'.")
    sys.exit(1)

# ANSI Color Palette (Claude Code / Anthropic Inspired)
ESC = '\033['
RESET = f'{ESC}0m'
BOLD = f'{ESC}1m'
DIM = f'{ESC}2m'
ITALIC = f'{ESC}3m'
UNDERLINE = f'{ESC}4m'

# Theme Colors
CORAL = f'{ESC}38;2;249;115;22m'      # Anthropic Orange / Coral
AMBER = f'{ESC}38;2;245;158;11m'      # Warning / Accent Amber
YELLOW = AMBER                         # Yellow Alias
GREEN = f'{ESC}38;2;16;185;129m'      # Success / Running Emerald Green
CYAN = f'{ESC}38;2;56;189;248m'       # Info / Port Sky Blue
PURPLE = f'{ESC}38;2;168;85;247m'     # Purple Accent
INDIGO = f'{ESC}38;2;99;102;241m'     # Indigo
RED = f'{ESC}38;2;239;68;68m'         # Error / Kill Red
GRAY = f'{ESC}38;2;100;116;139m'      # Slate Gray (Borders / Dividers)
DARK_GRAY = f'{ESC}38;2;51;65;85m'    # Dark Slate
WHITE = f'{ESC}38;2;248;250;252m'     # Crisp White

ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

def len_visible(s):
    return len(ANSI_RE.sub('', str(s)))

def pad_visible(s, width, align='left'):
    s = str(s)
    vlen = len_visible(s)
    diff = max(0, width - vlen)
    if align == 'right':
        return (' ' * diff) + s
    elif align == 'center':
        left = diff // 2
        right = diff - left
        return (' ' * left) + s + (' ' * right)
    return s + (' ' * diff)

HOME = os.path.expanduser('~')
APPDATA = os.environ.get('APPDATA', '')
LOCALAPPDATA = os.environ.get('LOCALAPPDATA', '')

# ---------------------------------------------------------
# LAYER 1: Deep Network & Port Prober (Surface & Depth)
# ---------------------------------------------------------
def probe_mcp_http(ip, port, timeout=0.15):
    """Depth-level active probe for MCP SSE/HTTP JSON-RPC protocol."""
    target_ip = '127.0.0.1' if ip in ('0.0.0.0', '::', '') else ip
    endpoints = [
        ('/mcp/sse', 'GET'),
        ('/sse', 'GET'),
        ('/mcp', 'GET'),
        ('/mcp', 'POST')
    ]
    for ep, method in endpoints:
        url = f"http://{target_ip}:{port}{ep}"
        try:
            req = urllib.request.Request(
                url,
                data=b'{"jsonrpc":"2.0","method":"ping","id":1}' if method == 'POST' else None,
                headers={'Accept': 'text/event-stream, application/json', 'User-Agent': 'MCP-Probe'}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ct = resp.headers.get('Content-Type', '')
                if 'event-stream' in ct or 'json' in ct:
                    return True, f"MCP {ep} ({resp.status})"
        except urllib.error.HTTPError as e:
            try:
                ct = e.headers.get('Content-Type', '')
                body = e.read(150).decode('utf-8', errors='ignore')
                if any(k in body.lower() for k in ['token', 'mcp', 'session', 'unauthorized', 'jsonrpc']):
                    return True, f"MCP HTTP ({e.code})"
            except Exception:
                pass
        except Exception:
            pass
    return False, ""

def scan_all_ports(proc_map):
    """Scans every open listening TCP port on the system and identifies MCP sockets."""
    mcp_ports = []
    all_sockets = []

    try:
        conns = psutil.net_connections(kind='tcp')
    except Exception:
        conns = []

    for c in conns:
        if c.status == 'LISTEN' and c.laddr:
            ip, port = c.laddr.ip, c.laddr.port
            pid = c.pid
            p_info = proc_map.get(pid, {})
            pname = p_info.get('name', 'unknown')
            cmd = p_info.get('cmdline', '')
            ram = p_info.get('ram_commit_mb', 0.0)

            # Surface check: command line / name clues
            cmd_lower = cmd.lower()
            surface_mcp = any(k in cmd_lower for k in ['mcp', 'fastmcp', 'modelcontextprotocol'])
            
            # Depth check: probe endpoint
            depth_mcp, clue = probe_mcp_http(ip, port)

            is_mcp = surface_mcp or depth_mcp

            # Guess server title
            guess = None
            if is_mcp:
                for tok in cmd.split():
                    c_tok = os.path.basename(tok).lower().replace('.exe','').replace('.py','').replace('.js','')
                    if 'mcp' in c_tok and c_tok not in ('mcp-manager', 'mcp-status'):
                        guess = c_tok
                        break
                if not guess:
                    guess = f"{pname}:{port}"

                mcp_ports.append({
                    'port': port,
                    'ip': ip,
                    'pid': pid,
                    'name': guess,
                    'pname': pname,
                    'cmd': cmd,
                    'ram_commit_mb': ram,
                    'clue': clue or ('Process Match' if surface_mcp else '')
                })

            all_sockets.append({
                'port': port,
                'ip': ip,
                'pid': pid,
                'pname': pname,
                'cmd': cmd,
                'is_mcp': is_mcp,
                'clue': clue
            })

    return mcp_ports, all_sockets

# ---------------------------------------------------------
# LAYER 2: Filesystem & Local Machine Repository Scanner
# (Solves: "Installed but not configured in any coding agent")
# ---------------------------------------------------------
def scan_installed_machine_servers():
    """Discovers all MCP servers installed locally on the filesystem."""
    installed = {}

    # 1. Local Tool Directories (e.g. D:\Tools & MCP, C:\Users\<user>\mcp, etc.)
    search_dirs = [
        r'D:\Tools & MCP\Local',
        r'D:\Tools & MCP',
        os.path.join(HOME, 'mcp'),
        os.path.join(HOME, 'Tools'),
        os.path.join(HOME, 'Desktop', 'MCP*')
    ]

    for dpattern in search_dirs:
        for base in glob.glob(dpattern):
            if not os.path.isdir(base):
                continue
            for item in os.listdir(base):
                full = os.path.join(base, item)
                if not os.path.isdir(full):
                    continue

                item_lower = item.lower()
                # Check directory contents for markers
                try:
                    entries = [e.lower() for e in os.listdir(full)]
                except Exception:
                    continue

                is_mcp = (
                    'mcp' in item_lower or
                    'pyproject.toml' in entries or
                    'package.json' in entries or
                    'requirements.txt' in entries
                )

                if is_mcp:
                    # Detect launcher command
                    run_cmd = None
                    run_args = []

                    # Check for virtualenv Python
                    venv_python = os.path.join(full, '.venv', 'Scripts', 'python.exe')
                    if os.path.exists(venv_python):
                        # Find python script
                        scripts = [s for s in entries if s.endswith('.py') and not s.startswith('test_')]
                        if scripts:
                            run_cmd = venv_python
                            run_args = [os.path.join(full, scripts[0])]
                    elif 'package.json' in entries:
                        # Node project
                        cli_js = os.path.join(full, 'dist', 'index.js')
                        if not os.path.exists(cli_js):
                            cli_js = os.path.join(full, 'src', 'cli.js')
                        if not os.path.exists(cli_js):
                            cli_js = os.path.join(full, 'index.js')
                        if os.path.exists(cli_js):
                            run_cmd = 'node'
                            run_args = [cli_js]

                    installed[item] = {
                        'name': item,
                        'source': 'Local Disk',
                        'type': 'local',
                        'path': full,
                        'command': run_cmd,
                        'args': json.dumps(run_args),
                        'env': '{}',
                        'description': f"Installed at {full}"
                    }

    # 2. NPX Cache & Global NPM Packages
    npx_cache = os.path.join(LOCALAPPDATA, 'npm-cache', '_npx')
    if os.path.exists(npx_cache):
        for pkg_dir in glob.glob(os.path.join(npx_cache, '*', 'node_modules', '*')):
            bname = os.path.basename(pkg_dir)
            if 'mcp' in bname.lower() or bname.startswith('@modelcontextprotocol'):
                if bname not in installed:
                    installed[bname] = {
                        'name': bname,
                        'source': 'NPX Cache',
                        'type': 'local',
                        'path': pkg_dir,
                        'command': 'npx',
                        'args': json.dumps(['-y', bname]),
                        'env': '{}',
                        'description': f"Global NPX package ({bname})"
                    }

    return installed

# ---------------------------------------------------------
# LAYER 3: Dynamic Multi-Agent Config Harvester
# ---------------------------------------------------------
def scan_agent_configs():
    """Dynamically reads MCP configs across all installed coding agents."""
    targets = [
        ('Antigravity IDE', os.path.join(HOME, '.gemini', 'config', 'mcp_config.json')),
        ('Claude Code', os.path.join(HOME, '.claude.json')),
        ('Claude Global', os.path.join(HOME, '.claude', 'mcp.json')),
        ('Claude Desktop', os.path.join(APPDATA, 'Claude', 'claude_desktop_config.json')),
        ('Cursor', os.path.join(HOME, '.cursor', 'mcp.json')),
        ('Cursor Global', os.path.join(APPDATA, 'Cursor', 'User', 'globalStorage', 'mcp.json')),
        ('Windsurf', os.path.join(HOME, '.codeium', 'windsurf', 'mcp_config.json')),
        ('Windsurf User', os.path.join(APPDATA, 'Windsurf', 'User', 'mcp.json')),
        ('Cline', os.path.join(APPDATA, 'Code', 'User', 'globalStorage', 'saoudrizwan.claude-dev', 'settings', 'cline_mcp_settings.json')),
        ('Roo Code', os.path.join(APPDATA, 'Code', 'User', 'globalStorage', 'rooveterinaryinc.roo-cline', 'settings', 'cline_mcp_settings.json')),
        ('Continue', os.path.join(HOME, '.continue', 'config.json')),
        ('Zed', os.path.join(HOME, '.config', 'zed', 'settings.json')),
        ('VS Code', os.path.join(os.getcwd(), '.vscode', 'mcp.json')),
        ('Workspace', os.path.join(os.getcwd(), 'mcp.json'))
    ]

    discovered = {}
    found_agents = set()

    for agent_name, path in targets:
        if not os.path.exists(path):
            continue

        found_agents.add(agent_name)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            servers = data.get('mcpServers') or data.get('mcp_servers') or data.get('mcp')
            if isinstance(servers, dict):
                for sname, sdata in servers.items():
                    if not isinstance(sdata, dict):
                        continue
                    is_disabled = bool(sdata.get('disabled', False))
                    if sname in discovered:
                        if agent_name not in discovered[sname]['source']:
                            discovered[sname]['source'] += f", {agent_name}"
                        if is_disabled:
                            discovered[sname]['disabled'] = True
                        continue

                    cmd = sdata.get('command')
                    args = sdata.get('args', [])
                    env = sdata.get('env', {})
                    url = sdata.get('url') or sdata.get('serverUrl')

                    stype = 'remote' if url and not cmd else 'local'
                    discovered[sname] = {
                        'name': sname,
                        'source': agent_name,
                        'type': stype,
                        'command': cmd,
                        'args': json.dumps(args) if isinstance(args, list) else args,
                        'env': json.dumps(env) if isinstance(env, dict) else env,
                        'disabled': is_disabled,
                        'description': f"Configured in {agent_name}"
                    }
        except Exception:
            pass

    return discovered, sorted(list(found_agents))

# ---------------------------------------------------------
# Dynamic Pattern Derivation
# ---------------------------------------------------------
def derive_patterns(name, command, args_str):
    patterns = {name.lower().replace('-mcp', '').replace('_mcp', '')}
    patterns.add(name.lower())
    if args_str:
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
            for a in args:
                if isinstance(a, str):
                    base = os.path.basename(a).lower()
                    if base.endswith(('.py', '.js', '.mjs', '.ts', '.exe')):
                        if base not in ('index.js', 'cli.js', 'main.js', 'python.exe', 'node.exe'):
                            patterns.add(base)
                        else:
                            parent = os.path.basename(os.path.dirname(a)).lower()
                            if parent:
                                patterns.add(parent)
                    if '@modelcontextprotocol' in a.lower():
                        patterns.add(a.lower())
                    if '.' in a and not a.startswith('-') and not os.path.exists(a):
                        patterns.add(a.lower())
        except Exception:
            pass
    if command:
        base_cmd = os.path.basename(command).lower()
        if any(k in base_cmd for k in ['mcp', 'scrapling']):
            patterns.add(base_cmd)
    return list(patterns)

# ---------------------------------------------------------
# Full 360° Snapshot Engine
# ---------------------------------------------------------
def get_snapshot():
    # 1. Scan installed local repos on machine
    installed_servers = scan_installed_machine_servers()

    # 2. Scan coding agent configs
    agent_servers, found_agents = scan_agent_configs()

    # Merge: deduplicate intelligently using canonical server keys
    def canon_key(name):
        return name.lower().replace('_', '-').replace('-mcp', '').replace('_mcp', '').strip()

    master_catalog = {}
    canon_map = {}

    for name, s in installed_servers.items():
        ck = canon_key(name)
        canon_map[ck] = name
        master_catalog[name] = s

    for name, s in agent_servers.items():
        ck = canon_key(name)
        if ck in canon_map:
            existing_name = canon_map[ck]
            existing = master_catalog[existing_name]
            # Merge sources
            sources = []
            if 'Local Disk' in existing.get('source', ''):
                sources.append('Local Disk')
            if 'NPX Cache' in existing.get('source', ''):
                sources.append('NPX Cache')
            for a in s.get('source', '').split(','):
                a_clean = a.strip()
                if a_clean and a_clean not in sources:
                    sources.append(a_clean)
            s['source'] = ', '.join(sources)
            if not s.get('path') and existing.get('path'):
                s['path'] = existing['path']
            if not s.get('command') and existing.get('command'):
                s['command'] = existing['command']
                s['args'] = existing['args']
            if existing.get('disabled') or s.get('disabled'):
                s['disabled'] = True
            del master_catalog[existing_name]
            master_catalog[name] = s
            canon_map[ck] = name
        else:
            canon_map[ck] = name
            master_catalog[name] = s

    # 3. Scan all system processes
    processes = []
    proc_map = {}
    for p in psutil.process_iter(['pid', 'ppid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
        try:
            cmdline = " ".join(p.info['cmdline'] or [])
            name = p.info['name'] or ""
            mi = p.info['memory_info']
            if not mi:
                continue
            private_mb = getattr(mi, 'private', mi.rss) / (1024 * 1024)
            cpu = p.cpu_percent(interval=None)
            item = {
                'pid': p.info['pid'],
                'ppid': p.info['ppid'],
                'name': name,
                'cmdline': cmdline,
                'cpu': cpu,
                'ram_commit_mb': round(private_mb, 1),
                'proc': p
            }
            processes.append(item)
            proc_map[p.info['pid']] = item
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # 4. Deep port & socket scan
    mcp_ports, all_sockets = scan_all_ports(proc_map)

    # 5. Process matching
    assigned_pids = set()
    servers_list = []
    total_commit = 0.0

    idx = 1
    for s_name, s_data in master_catalog.items():
        s_type = s_data['type']
        patterns = derive_patterns(s_name, s_data.get('command'), s_data.get('args'))

        matched = []
        if s_type != 'remote':
            for p in processes:
                if p['pid'] in assigned_pids:
                    continue
                cmd_lower = p['cmdline'].lower()
                if any(pat in cmd_lower for pat in patterns):
                    if not any(ign in cmd_lower for ign in ['mcp_cli_manager', 'mcp-manager', 'mcp-status']):
                        matched.append(p)
                        assigned_pids.add(p['pid'])

        is_running = len(matched) > 0
        is_disabled = bool(s_data.get('disabled', False))
        if s_type == 'remote':
            status = "ONLINE"
        elif is_running:
            status = "RUNNING"
        elif is_disabled:
            status = "DISABLED"
        else:
            status = "READY"

        commit_mb = sum(p['ram_commit_mb'] for p in matched)
        cpu = sum(p['cpu'] for p in matched)
        pids = [p['pid'] for p in matched]

        total_commit += commit_mb

        # Check port
        ports_str = ""
        for mp in mcp_ports:
            if mp['pid'] in pids:
                ports_str = f":{mp['port']}"
                break

        servers_list.append({
            'num': idx,
            'name': s_name,
            'source': s_data.get('source', 'Local Machine'),
            'type': s_type,
            'status': status,
            'is_running': is_running,
            'disabled': is_disabled,
            'pids': pids,
            'port': ports_str,
            'commit_mb': round(commit_mb, 1),
            'cpu': round(cpu, 1),
            'command': s_data.get('command'),
            'args': s_data.get('args'),
            'env': s_data.get('env'),
            'patterns': patterns
        })
        idx += 1

    # 6. Check unassigned MCP processes (e.g. ad-hoc started processes)
    other_mcp = []
    for p in processes:
        if p['pid'] in assigned_pids:
            continue
        cmd_lower = p['cmdline'].lower()
        if any(k in cmd_lower for k in ['mcp', 'modelcontextprotocol', 'fastmcp']):
            if any(ign in cmd_lower for ign in ['mcp_cli_manager', 'mcp-manager', 'mcp-status', 'inspect_', 'test_', 'check_']):
                continue

            guess = "custom-mcp"
            for token in p['cmdline'].split():
                clean_tok = os.path.basename(token).lower().replace('.exe', '').replace('.js', '').replace('.py', '').replace('.bat', '')
                if 'mcp' in clean_tok and clean_tok not in ('mcp-manager', 'mcp-status', 'mcp_cli_manager'):
                    guess = clean_tok
                    break

            other_mcp.append({
                'pid': p['pid'],
                'name': p['name'],
                'guess_name': guess,
                'cmdline': p['cmdline'],
                'ram_commit_mb': p['ram_commit_mb'],
                'cpu': p['cpu']
            })
            total_commit += p['ram_commit_mb']

    # Group unassigned processes
    grouped = {}
    for omp in other_mcp:
        gn = omp['guess_name']
        if gn not in grouped:
            grouped[gn] = []
        grouped[gn].append(omp)

    for gn, procs in grouped.items():
        commit_mb = sum(p['ram_commit_mb'] for p in procs)
        cpu = sum(p['cpu'] for p in procs)
        pids = [p['pid'] for p in procs]

        p_str = ""
        for mp in mcp_ports:
            if mp['pid'] in pids:
                p_str = f":{mp['port']}"
                break

        servers_list.append({
            'num': idx,
            'name': f"*{gn}*",
            'source': 'Live OS Process',
            'type': 'local',
            'status': 'RUNNING',
            'is_running': True,
            'pids': pids,
            'port': p_str,
            'commit_mb': round(commit_mb, 1),
            'cpu': round(cpu, 1),
            'command': procs[0]['cmdline'].split()[0] if procs[0]['cmdline'] else None,
            'args': '[]',
            'env': '{}',
            'patterns': [gn]
        })
        idx += 1

    sys_mem = psutil.virtual_memory()

    return {
        'timestamp': time.strftime("%H:%M:%S"),
        'found_agents': found_agents,
        'installed_count': len(installed_servers),
        'mcp_ports': mcp_ports,
        'all_sockets_count': len(all_sockets),
        'all_sockets': all_sockets,
        'total_servers_ram': round(total_commit, 1),
        'system_ram_used_pct': sys_mem.percent,
        'system_ram_free_gb': round(sys_mem.available / (1024**3), 1),
        'system_ram_total_gb': round(sys_mem.total / (1024**3), 1),
        'servers': servers_list
    }

# ---------------------------------------------------------
# Claude Code CLI Presentation (High-End Aesthetic)
# ---------------------------------------------------------
def render_cli(data):
    os.system('cls' if os.name == 'nt' else 'clear')

    W = 94

    # Header Box
    print(f"\n{CORAL}╭{'─' * (W - 2)}╮{RESET}")
    title_line = f"  {BOLD}{WHITE}✦ MCP 360° ENGINE{RESET}  {DIM}v3.0 (Surface & Depth Scanner){RESET}"
    status_line = f"{GREEN}● ALL PORTS & PROCS ACTIVE{RESET}  "
    space_len = W - 2 - len_visible(title_line) - len_visible(status_line)
    print(f"{CORAL}│{RESET}{title_line}{' ' * max(0, space_len)}{status_line}{CORAL}│{RESET}")

    sub_line = f"  {DIM}Full-System Network Port Prober & Universal Agent Harvester{RESET}"
    space_sub = W - 2 - len_visible(sub_line)
    print(f"{CORAL}│{RESET}{sub_line}{' ' * max(0, space_sub)}{CORAL}│{RESET}")
    print(f"{CORAL}╰{'─' * (W - 2)}╯{RESET}")

    # System Status Ribbon
    running_count = sum(1 for s in data['servers'] if s['is_running'])
    total_count = len(data['servers'])

    ram_pct = data['system_ram_used_pct']
    bar_len = 10
    filled = int((ram_pct / 100.0) * bar_len)
    bar_str = f"[{'█' * filled}{'░' * (bar_len - filled)}]"

    agents_str = ', '.join(data['found_agents']) if data['found_agents'] else 'Zero Config Mode'
    print(f" {BOLD}Agents / Repos{RESET} : {CYAN}{agents_str}{RESET} │ {DIM}{data['installed_count']} Local Repos on Drive{RESET}")
    print(f" {BOLD}System RAM    {RESET} : {AMBER}{bar_str} {ram_pct}%{RESET} ({data['system_ram_free_gb']} GB free of {data['system_ram_total_gb']} GB)")
    print(f" {BOLD}Total Memory  {RESET} : {BOLD}{GREEN}{data['total_servers_ram']} MB{RESET} Commit Charge  │  {BOLD}{running_count}{RESET} Active / {total_count} Total Servers")

    if data['mcp_ports']:
        port_items = [f"{CYAN}:{p['port']}{RESET} ({p['name']} / PID {p['pid']})" for p in data['mcp_ports']]
        print(f" {BOLD}Active Ports  {RESET} : {' │ '.join(port_items)} ({data['all_sockets_count']} total system sockets)")
    else:
        print(f" {BOLD}Active Ports  {RESET} : {DIM}No dedicated MCP HTTP/SSE listener ports open ({data['all_sockets_count']} sockets scanned){RESET}")

    print(f"{GRAY}{'─' * W}{RESET}")

    # Table Header
    header = (
        f" {pad_visible('#', 3)} "
        f"{pad_visible('Server Name', 24)} "
        f"{pad_visible('Status', 11)} "
        f"{pad_visible('Discovery Source', 20)} "
        f"{pad_visible('Port / PID', 13)} "
        f"{pad_visible('RAM Commit', 11, 'right')} "
        f"{pad_visible('CPU', 6, 'right')}"
    )
    print(f"{BOLD}{WHITE}{header}{RESET}")
    print(f"{GRAY}{'─' * W}{RESET}")

    # Table Rows
    for s in data['servers']:
        num_str = f"{s['num']:02d}"
        s_name = s['name'][:23]

        if s['status'] == 'RUNNING':
            status_badge = f"{GREEN}● RUNNING{RESET}"
        elif s['status'] == 'DISABLED':
            status_badge = f"{YELLOW}⊘ DISABLED{RESET}"
        elif s['status'] in ('INSTALLED', 'READY'):
            status_badge = f"{DIM}○ READY  {RESET}"
        elif s['status'] == 'ONLINE':
            status_badge = f"{CYAN}✦ REMOTE {RESET}"
        else:
            status_badge = f"{DIM}○ STOPPED{RESET}"

        source_str = f"{DIM}{s['source'][:20]}{RESET}"

        if s['port']:
            loc_str = f"{CYAN}{s['port']}{RESET} {DIM}P:{s['pids'][0] if s['pids'] else ''}{RESET}"
        elif s['pids']:
            loc_str = f"PID {s['pids'][0]}" + (f"+{len(s['pids'])-1}" if len(s['pids']) > 1 else "")
        elif s['type'] == 'remote':
            loc_str = f"{DIM}Cloud HTTPS{RESET}"
        else:
            loc_str = f"{DIM}─{RESET}"

        if s['type'] == 'remote':
            ram_display = f"{DIM}Cloud{RESET}"
        else:
            mb = s['commit_mb']
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

        cpu_str = f"{s['cpu']:>4.1f}%" if s['type'] != 'remote' else f"{DIM}N/A{RESET}"

        row_str = (
            f" {pad_visible(num_str, 3)} "
            f"{pad_visible(s_name, 24)} "
            f"{pad_visible(status_badge, 11)} "
            f"{pad_visible(source_str, 20)} "
            f"{pad_visible(loc_str, 13)} "
            f"{pad_visible(ram_display, 11, 'right')} "
            f"{pad_visible(cpu_str, 6, 'right')}"
        )
        print(row_str)

    print(f"{GRAY}{'─' * W}{RESET}")
    print(f"{DIM}Tip: If a server auto-starts when using an IDE or agent, use [D] to Disable it in config.{RESET}\n")

    # Action Bar
    print(f"{DARK_GRAY}╭─ {BOLD}{WHITE}Actions & Shortcuts{RESET}{DARK_GRAY} {'─' * (W - 25)}╮{RESET}")
    bar = f"  {CORAL}[1-N]{RESET} Toggle    {YELLOW}[D]{RESET} Disable/Enable    {RED}[K]{RESET} Kill All    {GREEN}[S]{RESET} Start    {CYAN}[P]{RESET} Ports    {WHITE}[Q]{RESET} Quit  "
    space_bar = W - 2 - len_visible(bar)
    print(f"{DARK_GRAY}│{RESET}{bar}{' ' * max(0, space_bar)}{DARK_GRAY}│{RESET}")
    print(f"{DARK_GRAY}╰{'─' * (W - 2)}╯{RESET}")

# ---------------------------------------------------------
# Control Operations
# ---------------------------------------------------------
def kill_pid_tree(pid):
    """Forcefully terminates a PID and all its child/grandchild processes on Windows."""
    if os.name == 'nt':
        res = subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True, text=True)
        return res.returncode == 0
    else:
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            return True
        except Exception:
            return False

def kill_server(server_obj):
    """Kills a server and its entire process tree, leaving zero orphaned node/python workers."""
    killed = []
    for pid in server_obj.get('pids', []):
        try:
            kill_pid_tree(pid)
            killed.append(pid)
        except Exception:
            pass

    patterns = list(server_obj.get('patterns', [server_obj['name'].lower()]))
    s_clean = server_obj['name'].lower().replace('_', '-').replace('-mcp', '').replace('_mcp', '')
    patterns.extend([s_clean, f"server-{s_clean}", f"mcp-server-{s_clean}"])

    for p in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmd = " ".join(p.info['cmdline'] or [])
            if any(pat in cmd.lower() for pat in patterns):
                if not any(ign in cmd.lower() for ign in ['mcp_cli_manager', 'mcp-manager', 'mcp-status', 'deploy_', 'inspect_']):
                    kill_pid_tree(p.info['pid'])
                    if p.info['pid'] not in killed:
                        killed.append(p.info['pid'])
        except Exception:
            pass

    return killed

def toggle_disable_server(s, force_state=None):
    """Toggles 'disabled': true/false in agent configs so supervisors will NOT auto-start the server."""
    name = s['name']
    currently_disabled = s.get('disabled', False)
    new_disabled = not currently_disabled if force_state is None else force_state

    targets = [
        os.path.join(HOME, '.gemini', 'config', 'mcp_config.json'),
        os.path.join(HOME, '.claude.json'),
        os.path.join(APPDATA, 'Claude', 'claude_desktop_config.json'),
        os.path.join(HOME, '.cursor', 'mcp.json'),
        os.path.join(HOME, '.codeium', 'windsurf', 'mcp_config.json'),
        os.path.join(os.getcwd(), '.vscode', 'mcp.json'),
        os.path.join(os.getcwd(), 'mcp.json')
    ]
    updated_files = []
    for path in targets:
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            servers = data.get('mcpServers') or data.get('mcp_servers') or data.get('mcp')
            if isinstance(servers, dict):
                matched_key = None
                for k in servers:
                    if k.lower() == name.lower() or k.lower().replace('-mcp', '') == name.lower().replace('-mcp', ''):
                        matched_key = k
                        break
                if matched_key:
                    servers[matched_key]['disabled'] = new_disabled
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                    updated_files.append(os.path.basename(path))
        except Exception:
            pass

    if new_disabled:
        killed = kill_server(s)
        print(f"\n{YELLOW}Disabled '{name}' in: {', '.join(updated_files) if updated_files else 'config'}.{RESET}")
        print(f"{DIM}Terminated process tree ({len(killed)} PIDs: {killed}). Server will NOT auto-start.{RESET}")
    else:
        print(f"\n{GREEN}Enabled '{name}' in: {', '.join(updated_files) if updated_files else 'config'}.{RESET}")
        print(f"{DIM}Server is now enabled and ready to run on demand.{RESET}")

    time.sleep(1.6)

def start_server(s):
    if s['type'] == 'remote':
        print(f"{AMBER}Cannot spawn remote cloud server '{s['name']}' locally.{RESET}")
        return None
    if not s['command']:
        print(f"{RED}No executable command found for '{s['name']}'. Check pyproject.toml or package.json.{RESET}")
        return None

    # If it was disabled, auto-enable it upon start
    if s.get('disabled'):
        toggle_disable_server(s, force_state=False)

    cmd = s['command']
    args = json.loads(s['args'] or '[]') if isinstance(s['args'], str) else (s['args'] or [])
    extra_env = json.loads(s['env'] or '{}') if isinstance(s['env'], str) else (s['env'] or {})
    env = os.environ.copy()
    env.update(extra_env)

    full_cmd = [cmd] + args
    try:
        proc = subprocess.Popen(
            full_cmd,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return proc.pid
    except Exception as e:
        print(f"{RED}Error starting '{s['name']}': {e}{RESET}")
        return None

def kill_all_servers(servers):
    total_killed = []
    for s in servers:
        if s['type'] != 'remote' and s['is_running']:
            k = kill_server(s)
            total_killed.extend(k)
    return total_killed

def deep_port_audit(data, interactive=True):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"\n{CYAN}╭────────────────────────────────────────────────────────────────────────────────────────╮{RESET}")
    print(f"{CYAN}│  ⚡ DEEP SYSTEM PORT & SOCKET AUDIT (Every Listening Port Probed)                     │{RESET}")
    print(f"{CYAN}╰────────────────────────────────────────────────────────────────────────────────────────╯{RESET}\n")

    sockets = data.get('all_sockets', [])
    print(f" Audited {len(sockets)} open TCP sockets on host:\n")
    print(f" {'Port':<8} {'IP Address':<16} {'PID':<8} {'Process Name':<20} {'Status / MCP Protocol Clues'}")
    print(f" {'─'*78}")

    for s in sorted(sockets, key=lambda x: x['port']):
        port = s['port']
        ip = s['ip']
        pid = s['pid'] or '-'
        pname = s['pname']
        is_mcp = s['is_mcp']
        clue = s['clue'] or ('MCP Process' if is_mcp else 'Standard Socket')

        if is_mcp:
            line_color = GREEN
            badge = f"{GREEN}● ACTIVE MCP{RESET}"
        else:
            line_color = DIM
            badge = f"{DIM}○ listening {RESET}"

        print(f" {line_color}:{port:<7} {ip:<16} {str(pid):<8} {pname:<20}{RESET} {badge} {DIM}{clue}{RESET}")

    print(f"\n{DIM}Port audit complete.{RESET}")
    if interactive:
        input("\nPress Enter to return to main menu...")

# ---------------------------------------------------------
# Interactive CLI Loop
# ---------------------------------------------------------
def interactive_loop():
    while True:
        data = get_snapshot()
        render_cli(data)

        try:
            choice = input(f" {BOLD}{CORAL}Enter action:{RESET} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if choice in ('q', 'exit'):
            print(f"\n{GREEN}Goodbye!{RESET}")
            break
        elif choice == 'r':
            continue
        elif choice == 'p':
            deep_port_audit(data, interactive=True)
        elif choice == 'k':
            killed = kill_all_servers(data['servers'])
            print(f"\n{RED}Killed {len(killed)} process(es): {killed}{RESET}")
            time.sleep(1.2)
        elif choice == 's':
            for s in data['servers']:
                if s['type'] != 'remote' and not s['is_running'] and not s.get('disabled'):
                    pid = start_server(s)
                    if pid:
                        print(f"{GREEN}Started '{s['name']}' (PID {pid}){RESET}")
            time.sleep(1.2)
        elif choice == 'd' or choice.startswith('d ') or choice.startswith('disable ') or choice.startswith('enable '):
            parts = choice.split()
            t_idx = -1
            if len(parts) > 1 and parts[1].isdigit():
                t_idx = int(parts[1])
            elif len(parts) > 1:
                query = parts[1].lower()
                m = next((x for x in data['servers'] if query in x['name'].lower()), None)
                if m:
                    t_idx = m['num']
            else:
                try:
                    val = input(f" {BOLD}{YELLOW}Enter server # or name to toggle Disable/Enable:{RESET} ").strip()
                    if val.isdigit():
                        t_idx = int(val)
                    else:
                        m = next((x for x in data['servers'] if val.lower() in x['name'].lower()), None)
                        if m:
                            t_idx = m['num']
                except Exception:
                    continue

            s_target = next((x for x in data['servers'] if x['num'] == t_idx), None)
            if s_target:
                force = True if choice.startswith('disable ') else (False if choice.startswith('enable ') else None)
                toggle_disable_server(s_target, force_state=force)
            else:
                print(f"{RED}Server not found.{RESET}")
                time.sleep(1)
        elif choice.isdigit():
            idx = int(choice)
            matched = [s for s in data['servers'] if s['num'] == idx]
            if not matched:
                print(f"{RED}Invalid server number: {idx}{RESET}")
                time.sleep(1)
                continue
            s = matched[0]
            if s['type'] == 'remote':
                print(f"\n{CYAN}'{s['name']}' is a remote cloud server managed via HTTPS.{RESET}")
                time.sleep(1.5)
            elif s['is_running']:
                killed = kill_server(s)
                print(f"\n{RED}Stopped '{s['name']}' (Killed PIDs: {killed}){RESET}")
                print(f"{DIM}Tip: If it auto-restarts when using an IDE/agent, press [D] to Disable it.{RESET}")
                time.sleep(1.5)
            else:
                pid = start_server(s)
                if pid:
                    print(f"\n{GREEN}Started '{s['name']}' (New PID: {pid}){RESET}")
                time.sleep(1.2)
        else:
            print(f"{RED}Unrecognized command. Enter 1-N, D, K, S, P, R, or Q.{RESET}")
            time.sleep(1)

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        data = get_snapshot()

        if cmd == 'status':
            render_cli(data)
        elif cmd == 'ports':
            deep_port_audit(data, interactive=False)
        elif cmd == 'kill-all':
            killed = kill_all_servers(data['servers'])
            print(f"Killed {len(killed)} process(es): {killed}")
        elif cmd == 'kill' and len(sys.argv) > 2:
            target = sys.argv[2]
            s = next((x for x in data['servers'] if target.lower() in x['name'].lower()), None)
            if s:
                killed = kill_server(s)
                print(f"Killed '{s['name']}' (PIDs: {killed})")
            else:
                print(f"Server '{target}' not found.")
        elif cmd == 'start' and len(sys.argv) > 2:
            target = sys.argv[2]
            s = next((x for x in data['servers'] if target.lower() in x['name'].lower()), None)
            if s:
                pid = start_server(s)
                print(f"Started '{s['name']}' (PID {pid})")
            else:
                print(f"Server '{target}' not found.")
        elif cmd == 'disable' and len(sys.argv) > 2:
            target = sys.argv[2]
            s = next((x for x in data['servers'] if target.lower() in x['name'].lower()), None)
            if s:
                toggle_disable_server(s, force_state=True)
            else:
                print(f"Server '{target}' not found.")
        elif cmd == 'enable' and len(sys.argv) > 2:
            target = sys.argv[2]
            s = next((x for x in data['servers'] if target.lower() in x['name'].lower()), None)
            if s:
                toggle_disable_server(s, force_state=False)
            else:
                print(f"Server '{target}' not found.")
        else:
            print("Usage:")
            print("  mcp-manager.bat                 (Interactive Claude-style menu)")
            print("  mcp-manager.bat status          (Show table once)")
            print("  mcp-manager.bat ports           (Deep scan all open ports)")
            print("  mcp-manager.bat disable <name>  (Disable server in config & kill process)")
            print("  mcp-manager.bat enable <name>   (Enable server in config)")
            print("  mcp-manager.bat kill <name>     (Kill specific server)")
            print("  mcp-manager.bat kill-all        (Kill all servers)")
            print("  mcp-manager.bat start <name>    (Start specific server)")
    else:
        interactive_loop()

if __name__ == '__main__':
    main()
