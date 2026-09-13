import os
import sys
import re
import json
import time
import socket
import sqlite3
import subprocess

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

# ---------------------------------------------------------
# 1. Multi-Agent Config Discovery (Zero MCP Router dependency)
# ---------------------------------------------------------
HOME = os.path.expanduser('~')
APPDATA = os.environ.get('APPDATA', '')
LOCALAPPDATA = os.environ.get('LOCALAPPDATA', '')

AGENT_CONFIG_TARGETS = [
    # Claude Code & Desktop
    ('Claude Code', os.path.join(HOME, '.claude.json')),
    ('Claude Global', os.path.join(HOME, '.claude', 'mcp.json')),
    ('Claude Desktop', os.path.join(APPDATA, 'Claude', 'claude_desktop_config.json')),
    # Cursor
    ('Cursor', os.path.join(HOME, '.cursor', 'mcp.json')),
    ('Cursor Global', os.path.join(APPDATA, 'Cursor', 'User', 'globalStorage', 'mcp.json')),
    # Windsurf
    ('Windsurf', os.path.join(HOME, '.codeium', 'windsurf', 'mcp_config.json')),
    ('Windsurf User', os.path.join(APPDATA, 'Windsurf', 'User', 'mcp.json')),
    # Cline & Roo Code
    ('Cline', os.path.join(APPDATA, 'Code', 'User', 'globalStorage', 'saoudrizwan.claude-dev', 'settings', 'cline_mcp_settings.json')),
    ('Roo Code', os.path.join(APPDATA, 'Code', 'User', 'globalStorage', 'rooveterinaryinc.roo-cline', 'settings', 'cline_mcp_settings.json')),
    # Continue.dev
    ('Continue', os.path.join(HOME, '.continue', 'config.json')),
    # Zed
    ('Zed', os.path.join(HOME, '.config', 'zed', 'settings.json')),
    ('Zed AppData', os.path.join(APPDATA, 'Zed', 'settings.json')),
    # VS Code workspace
    ('VS Code', os.path.join(os.getcwd(), '.vscode', 'mcp.json')),
    # Current workspace
    ('Workspace', os.path.join(os.getcwd(), 'mcp.json')),
    ('Workspace .mcp', os.path.join(os.getcwd(), '.mcp.json')),
    # MCP Router (optional legacy source if present, but zero dependency)
    ('MCP Router', os.path.join(APPDATA, 'MCP Router', 'mcprouter.db'))
]

def load_agent_configs():
    discovered = {}
    active_sources = set()

    for agent_name, path in AGENT_CONFIG_TARGETS:
        if not os.path.exists(path):
            continue

        active_sources.add(agent_name)

        # 1. Handle SQLite DB (MCP Router if present)
        if path.endswith('.db'):
            try:
                conn = sqlite3.connect(path, timeout=1.0)
                conn.row_factory = sqlite3.Row
                rows = conn.execute('SELECT id, name, server_type, command, args, env, description FROM servers').fetchall()
                for r in rows:
                    if r['name'] not in discovered:
                        discovered[r['name']] = {
                            'name': r['name'],
                            'source': agent_name,
                            'type': r['server_type'] or 'local',
                            'command': r['command'],
                            'args': r['args'],
                            'env': r['env'],
                            'description': r['description'] or ''
                        }
                conn.close()
            except Exception:
                pass
            continue

        # 2. Handle JSON config files
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            servers = data.get('mcpServers') or data.get('mcp_servers') or data.get('mcp')
            if isinstance(servers, dict):
                for sname, sdata in servers.items():
                    if sname in discovered:
                        if agent_name not in discovered[sname]['source']:
                            discovered[sname]['source'] += f", {agent_name}"
                        continue

                    if not isinstance(sdata, dict):
                        continue

                    cmd = sdata.get('command')
                    args = sdata.get('args', [])
                    env = sdata.get('env', {})
                    url = sdata.get('url')

                    stype = 'remote' if url and not cmd else 'local'
                    discovered[sname] = {
                        'name': sname,
                        'source': agent_name,
                        'type': stype,
                        'command': cmd,
                        'args': json.dumps(args) if isinstance(args, list) else args,
                        'env': json.dumps(env) if isinstance(env, dict) else env,
                        'description': f"Configured in {agent_name}"
                    }
        except Exception:
            pass

    return discovered, sorted(list(active_sources))

# ---------------------------------------------------------
# 2. System Port Scanner for MCP Listeners
# ---------------------------------------------------------
def scan_mcp_ports(processes):
    proc_map = {p['pid']: p for p in processes}
    mcp_ports = []

    try:
        conns = psutil.net_connections(kind='tcp')
    except (psutil.AccessDenied, Exception):
        conns = []

    for c in conns:
        if c.status == 'LISTEN' and c.laddr:
            ip, port = c.laddr.ip, c.laddr.port
            pid = c.pid
            p_info = proc_map.get(pid, {})
            p_name = p_info.get('name', 'unknown')
            p_cmd = p_info.get('cmdline', '')
            p_ram = p_info.get('ram_commit_mb', 0.0)

            cmd_lower = p_cmd.lower()
            is_mcp = any(k in cmd_lower for k in ['mcp', 'fastmcp', 'sse', 'modelcontextprotocol'])

            if is_mcp:
                server_title = None
                for tok in p_cmd.split():
                    tok_clean = os.path.basename(tok).lower().replace('.exe','').replace('.py','').replace('.js','')
                    if 'mcp' in tok_clean and tok_clean not in ('mcp-manager', 'mcp-status'):
                        server_title = tok_clean
                        break
                if not server_title:
                    server_title = f"{p_name}:{port}"

                mcp_ports.append({
                    'port': port,
                    'ip': ip,
                    'pid': pid,
                    'name': server_title,
                    'proc_name': p_name,
                    'cmdline': p_cmd,
                    'ram_commit_mb': p_ram
                })

    return mcp_ports

# ---------------------------------------------------------
# 3. Dynamic Process Pattern Matching
# ---------------------------------------------------------
def derive_patterns(name, command, args_str):
    patterns = {name.lower()}
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
# 4. System Snapshot Aggregation
# ---------------------------------------------------------
def get_snapshot():
    servers_dict, active_sources = load_agent_configs()

    processes = []
    for p in psutil.process_iter(['pid', 'ppid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
        try:
            cmdline = " ".join(p.info['cmdline'] or [])
            name = p.info['name'] or ""
            mi = p.info['memory_info']
            if not mi:
                continue
            private_mb = getattr(mi, 'private', mi.rss) / (1024 * 1024)
            cpu = p.cpu_percent(interval=None)
            processes.append({
                'pid': p.info['pid'],
                'ppid': p.info['ppid'],
                'name': name,
                'cmdline': cmdline,
                'cpu': cpu,
                'ram_commit_mb': round(private_mb, 1),
                'proc': p
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    mcp_ports = scan_mcp_ports(processes)

    assigned_pids = set()
    servers_list = []
    total_commit = 0.0

    idx = 1
    for s_name, s_data in servers_dict.items():
        s_type = s_data['type']
        patterns = derive_patterns(s_name, s_data['command'], s_data['args'])

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
        status = "ONLINE" if s_type == 'remote' else ("RUNNING" if is_running else "STOPPED")

        commit_mb = sum(p['ram_commit_mb'] for p in matched)
        cpu = sum(p['cpu'] for p in matched)
        pids = [p['pid'] for p in matched]

        total_commit += commit_mb

        ports_str = ""
        for mp in mcp_ports:
            if mp['pid'] in pids:
                ports_str = f":{mp['port']}"
                break

        servers_list.append({
            'num': idx,
            'name': s_name,
            'source': s_data['source'],
            'type': s_type,
            'status': status,
            'is_running': is_running,
            'pids': pids,
            'port': ports_str,
            'commit_mb': round(commit_mb, 1),
            'cpu': round(cpu, 1),
            'command': s_data['command'],
            'args': s_data['args'],
            'env': s_data['env'],
            'patterns': patterns
        })
        idx += 1

    # Auto-discover other running MCP processes
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
        'active_sources': active_sources,
        'mcp_ports': mcp_ports,
        'total_servers_ram': round(total_commit, 1),
        'system_ram_used_pct': sys_mem.percent,
        'system_ram_free_gb': round(sys_mem.available / (1024**3), 1),
        'system_ram_total_gb': round(sys_mem.total / (1024**3), 1),
        'servers': servers_list
    }

# ---------------------------------------------------------
# 5. Claude Code Elegant CLI Rendering (Pixel-Perfect)
# ---------------------------------------------------------
def render_cli(data):
    os.system('cls' if os.name == 'nt' else 'clear')

    W = 92  # Width

    # Header Box
    print(f"\n{CORAL}╭{'─' * (W - 2)}╮{RESET}")
    title_line = f"  {BOLD}{WHITE}✦ MCP SERVERS MANAGER{RESET}  {DIM}v2.5{RESET}"
    status_line = f"{GREEN}● SYSTEM ACTIVE{RESET}  "
    space_len = W - 2 - len_visible(title_line) - len_visible(status_line)
    print(f"{CORAL}│{RESET}{title_line}{' ' * max(0, space_len)}{status_line}{CORAL}│{RESET}")

    sub_line = f"  {DIM}Universal Controller & Live Resource Monitor across all Coding Agents & Ports{RESET}"
    space_sub = W - 2 - len_visible(sub_line)
    print(f"{CORAL}│{RESET}{sub_line}{' ' * max(0, space_sub)}{CORAL}│{RESET}")
    print(f"{CORAL}╰{'─' * (W - 2)}╯{RESET}")

    # System Status Ribbon
    active_count = sum(1 for s in data['servers'] if s['is_running'] or s['status'] == 'ONLINE')
    total_count = len(data['servers'])

    ram_pct = data['system_ram_used_pct']
    bar_len = 10
    filled = int((ram_pct / 100.0) * bar_len)
    bar_str = f"[{'█' * filled}{'░' * (bar_len - filled)}]"

    print(f" {BOLD}Agents Found{RESET} : {CYAN}{', '.join(data['active_sources']) or 'Standalone'}{RESET}")
    print(f" {BOLD}System RAM  {RESET} : {AMBER}{bar_str} {ram_pct}%{RESET} ({data['system_ram_free_gb']} GB free of {data['system_ram_total_gb']} GB)")
    print(f" {BOLD}Total MCP   {RESET} : {BOLD}{GREEN}{data['total_servers_ram']} MB{RESET} Commit Charge  │  {BOLD}{active_count}/{total_count}{RESET} Servers Active")

    if data['mcp_ports']:
        port_items = [f"{CYAN}:{p['port']}{RESET} ({p['name']} / PID {p['pid']})" for p in data['mcp_ports']]
        print(f" {BOLD}Open Ports  {RESET} : {' │ '.join(port_items)}")
    else:
        print(f" {BOLD}Open Ports  {RESET} : {DIM}No dedicated MCP HTTP/SSE listener ports open{RESET}")

    print(f"{GRAY}{'─' * W}{RESET}")

    # Table Header
    header = (
        f" {pad_visible('#', 3)} "
        f"{pad_visible('Server Name', 24)} "
        f"{pad_visible('Status', 12)} "
        f"{pad_visible('Source', 16)} "
        f"{pad_visible('Port / PID', 14)} "
        f"{pad_visible('RAM Commit', 12, 'right')} "
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
        elif s['status'] == 'STOPPED':
            status_badge = f"{DIM}○ STOPPED{RESET}"
        elif s['status'] == 'ONLINE':
            status_badge = f"{CYAN}✦ REMOTE{RESET}"
        else:
            status_badge = f"{RED}✗ ERROR{RESET}"

        source_str = f"{DIM}{s['source'][:15]}{RESET}"

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
            f"{pad_visible(status_badge, 12)} "
            f"{pad_visible(source_str, 16)} "
            f"{pad_visible(loc_str, 14)} "
            f"{pad_visible(ram_display, 12, 'right')} "
            f"{pad_visible(cpu_str, 6, 'right')}"
        )
        print(row_str)

    print(f"{GRAY}{'─' * W}{RESET}")
    print(f"{DIM}Note: Servers marked with *name* were automatically detected from running processes.{RESET}\n")

    # Action Bar
    print(f"{DARK_GRAY}╭─ {BOLD}{WHITE}Actions & Shortcuts{RESET}{DARK_GRAY} {'─' * (W - 25)}╮{RESET}")
    bar = f"  {CORAL}[1-N]{RESET} Toggle Server    {RED}[K]{RESET} Kill All    {GREEN}[S]{RESET} Start All    {CYAN}[P]{RESET} Scan All Ports    {AMBER}[R]{RESET} Refresh    {WHITE}[Q]{RESET} Quit  "
    space_bar = W - 2 - len_visible(bar)
    print(f"{DARK_GRAY}│{RESET}{bar}{' ' * max(0, space_bar)}{DARK_GRAY}│{RESET}")
    print(f"{DARK_GRAY}╰{'─' * (W - 2)}╯{RESET}")

# ---------------------------------------------------------
# 6. Process Control Functions
# ---------------------------------------------------------
def kill_server(server_obj):
    killed = []
    for pid in server_obj.get('pids', []):
        try:
            p = psutil.Process(pid)
            p.kill()
            killed.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    patterns = server_obj.get('patterns', [server_obj['name'].lower()])
    for p in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmd = " ".join(p.info['cmdline'] or [])
            if any(pat in cmd.lower() for pat in patterns):
                if not any(ign in cmd.lower() for ign in ['mcp_cli_manager', 'mcp-manager', 'mcp-status']):
                    p.kill()
                    if p.info['pid'] not in killed:
                        killed.append(p.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return killed

def start_server(s):
    if s['type'] == 'remote':
        print(f"{AMBER}Cannot spawn remote cloud server '{s['name']}' locally.{RESET}")
        return None
    if not s['command']:
        print(f"{RED}No executable command configured for '{s['name']}'.{RESET}")
        return None

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

def deep_port_scan(interactive=True):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"\n{CYAN}=== Scanning All Open System Ports for MCP Listeners ==={RESET}\n")
    try:
        conns = psutil.net_connections(kind='tcp')
    except Exception as e:
        print(f"{RED}Error querying network connections: {e}{RESET}")
        if interactive:
            input("\nPress Enter to return...")
        return

    listening = [c for c in conns if c.status == 'LISTEN']
    print(f"Found {len(listening)} listening TCP sockets on host:\n")
    print(f" {'Port':<8} {'IP':<16} {'PID':<8} {'Process Name':<20} {'Command / Clues'}")
    print(f" {'─'*75}")

    for c in sorted(listening, key=lambda x: x.laddr.port if x.laddr else 0):
        if not c.laddr:
            continue
        port = c.laddr.port
        ip = c.laddr.ip
        pid = c.pid or '-'
        pname = '-'
        cmd = '-'
        if c.pid:
            try:
                p = psutil.Process(c.pid)
                pname = p.name()
                cmd = " ".join(p.cmdline())[:45]
            except Exception:
                pass

        highlight = CYAN if any(k in cmd.lower() for k in ['mcp', 'fastmcp', 'router']) else DIM
        print(f" {highlight}:{port:<7} {ip:<16} {str(pid):<8} {pname:<20} {cmd}{RESET}")

    print(f"\n{DIM}Scan complete.{RESET}")
    if interactive:
        input("\nPress Enter to return to main menu...")

# ---------------------------------------------------------
# 7. Interactive Loop & Entry Points
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
            deep_port_scan()
        elif choice == 'k':
            killed = kill_all_servers(data['servers'])
            print(f"\n{RED}Killed {len(killed)} process(es): {killed}{RESET}")
            time.sleep(1.2)
        elif choice == 's':
            for s in data['servers']:
                if s['type'] != 'remote' and not s['is_running']:
                    pid = start_server(s)
                    if pid:
                        print(f"{GREEN}Started '{s['name']}' (PID {pid}){RESET}")
            time.sleep(1.2)
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
                time.sleep(1.2)
            else:
                pid = start_server(s)
                if pid:
                    print(f"\n{GREEN}Started '{s['name']}' (New PID: {pid}){RESET}")
                time.sleep(1.2)
        else:
            print(f"{RED}Unrecognized command. Enter 1-N, K, S, P, R, or Q.{RESET}")
            time.sleep(1)

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        data = get_snapshot()

        if cmd == 'status':
            render_cli(data)
        elif cmd == 'ports':
            deep_port_scan(interactive=False)
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
        else:
            print("Usage:")
            print("  mcp-manager.bat              (Interactive Claude-style menu)")
            print("  mcp-manager.bat status       (Show table once)")
            print("  mcp-manager.bat ports        (Scan all open ports)")
            print("  mcp-manager.bat kill <name>  (Kill specific server)")
            print("  mcp-manager.bat kill-all     (Kill all servers)")
            print("  mcp-manager.bat start <name> (Start specific server)")
    else:
        interactive_loop()

if __name__ == '__main__':
    main()
