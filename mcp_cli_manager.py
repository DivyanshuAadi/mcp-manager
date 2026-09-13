import os
import sys
import json
import time
import socket
import sqlite3
import subprocess

try:
    import psutil
except ImportError:
    print("Error: psutil is required. Please run using the environment with psutil.")
    sys.exit(1)

ROUTER_DB_PATH = r'C:\Users\lenovo\AppData\Roaming\MCP Router\mcprouter.db'
CLAUDE_JSON_PATH = os.path.expanduser(r'~/.claude.json')
CLAUDE_MCP_PATH = os.path.expanduser(r'~/.claude/mcp.json')
CLAUDE_DESKTOP_PATH = os.path.expanduser(r'~/AppData/Roaming/Claude/claude_desktop_config.json')

def check_port(host, port, timeout=0.3):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def derive_patterns(name, command, args_str):
    patterns = {name.lower()}
    if args_str:
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
            for a in args:
                if isinstance(a, str):
                    base = os.path.basename(a).lower()
                    if base.endswith(('.py', '.js', '.mjs', '.ts', '.exe')):
                        # e.g. facebook_ads_mcp_complete.py, cli.js, index.js
                        if base not in ('index.js', 'cli.js', 'main.js', 'python.exe', 'node.exe'):
                            patterns.add(base)
                        else:
                            # include directory parent if generic filename
                            parent = os.path.basename(os.path.dirname(a)).lower()
                            if parent:
                                patterns.add(parent)
                    if '@modelcontextprotocol' in a.lower():
                        patterns.add(a.lower())
                    if '.' in a and not a.startswith('-') and not os.path.exists(a):
                        # python module like agent_reach.integrations.mcp_server
                        patterns.add(a.lower())
        except Exception:
            pass
    if command:
        base_cmd = os.path.basename(command).lower()
        if any(k in base_cmd for k in ['mcp', 'scrapling']):
            patterns.add(base_cmd)
    return list(patterns)

def get_servers_data():
    servers_dict = {}

    # 1. Load from MCP Router DB
    if os.path.exists(ROUTER_DB_PATH):
        try:
            conn = sqlite3.connect(ROUTER_DB_PATH, timeout=2.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            rows = cur.execute('SELECT id, name, server_type, command, args, env, description FROM servers').fetchall()
            for r in rows:
                servers_dict[r['name']] = {
                    'name': r['name'],
                    'source': 'MCP Router',
                    'type': r['server_type'],
                    'command': r['command'],
                    'args': r['args'],
                    'env': r['env'],
                    'description': r['description'] or ''
                }
            conn.close()
        except Exception as e:
            pass

    # 2. Check Claude configs for any extra servers
    for cpath in [CLAUDE_JSON_PATH, CLAUDE_MCP_PATH, CLAUDE_DESKTOP_PATH]:
        if os.path.exists(cpath):
            try:
                with open(cpath, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    mcp_servers = cfg.get('mcpServers', {})
                    if isinstance(mcp_servers, dict):
                        for sname, sdata in mcp_servers.items():
                            if sname not in servers_dict and sname != 'mcp-router':
                                servers_dict[sname] = {
                                    'name': sname,
                                    'source': 'Claude Config',
                                    'type': 'local' if sdata.get('command') else 'remote',
                                    'command': sdata.get('command'),
                                    'args': json.dumps(sdata.get('args', [])),
                                    'env': json.dumps(sdata.get('env', {})),
                                    'description': 'Auto-detected from ' + os.path.basename(cpath)
                                }
            except Exception:
                pass

    # 3. Discover all running system processes
    processes = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
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
                'name': name,
                'cmdline': cmdline,
                'cpu': cpu,
                'ram_commit_mb': round(private_mb, 1),
                'proc': p
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # 4. Router core process metrics
    router_pids = [p for p in processes if 'mcp router' in p['name'].lower()]
    router_commit = sum(p['ram_commit_mb'] for p in router_pids)
    gateway_up = check_port('127.0.0.1', 3282)

    # 5. Map processes to registered servers
    assigned_pids = set(p['pid'] for p in router_pids)
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
                    if not any(ign in cmd_lower for ign in ['mcp_cli_manager', 'test_', 'check_', 'inspect_']):
                        matched.append(p)
                        assigned_pids.add(p['pid'])

        is_running = len(matched) > 0
        if s_type == 'remote':
            status = "ONLINE"
        elif is_running:
            status = "RUNNING"
        else:
            status = "STOPPED"

        commit_mb = sum(p['ram_commit_mb'] for p in matched)
        cpu = sum(p['cpu'] for p in matched)
        pids = [p['pid'] for p in matched]

        total_commit += commit_mb

        servers_list.append({
            'num': idx,
            'name': s_name,
            'source': s_data['source'],
            'type': s_type,
            'status': status,
            'is_running': is_running,
            'pids': pids,
            'commit_mb': round(commit_mb, 1),
            'cpu': round(cpu, 1),
            'command': s_data['command'],
            'args': s_data['args'],
            'env': s_data['env'],
            'patterns': patterns
        })
        idx += 1

    # 6. Auto-detect any OTHER running MCP processes that aren't registered
    other_mcp_procs = []
    for p in processes:
        if p['pid'] in assigned_pids:
            continue
        cmd_lower = p['cmdline'].lower()
        if any(k in cmd_lower for k in ['mcp', 'modelcontextprotocol', 'fastmcp']) and not any(ign in cmd_lower for ign in ['mcp_cli_manager', 'mcp-manager', 'mcp-status', 'inspect_', 'test_', 'check_']):
            # Auto-determine server name from command line
            guess_name = "unknown-mcp"
            for token in p['cmdline'].split():
                clean_tok = os.path.basename(token).lower().replace('.exe', '').replace('.js', '').replace('.py', '').replace('.bat', '')
                if 'mcp' in clean_tok and clean_tok not in ('mcp-manager', 'mcp-status', 'mcp_cli_manager'):
                    guess_name = clean_tok
                    break
            if guess_name in ('mcp-manager', 'mcp-status', 'mcp_cli_manager'):
                continue
            other_mcp_procs.append({
                'pid': p['pid'],
                'name': p['name'],
                'guess_name': guess_name,
                'cmdline': p['cmdline'],
                'ram_commit_mb': p['ram_commit_mb'],
                'cpu': p['cpu']
            })
            total_commit += p['ram_commit_mb']

    # Add discovered unregistered servers into the list so user can control them!
    discovered_groups = {}
    for omp in other_mcp_procs:
        gname = omp['guess_name']
        if gname not in discovered_groups:
            discovered_groups[gname] = []
        discovered_groups[gname].append(omp)

    for gname, procs in discovered_groups.items():
        commit_mb = sum(p['ram_commit_mb'] for p in procs)
        cpu = sum(p['cpu'] for p in procs)
        pids = [p['pid'] for p in procs]
        servers_list.append({
            'num': idx,
            'name': f"*{gname}*",
            'source': 'Auto-Detected Process',
            'type': 'local',
            'status': 'RUNNING',
            'is_running': True,
            'pids': pids,
            'commit_mb': round(commit_mb, 1),
            'cpu': round(cpu, 1),
            'command': procs[0]['cmdline'].split()[0] if procs[0]['cmdline'] else None,
            'args': '[]',
            'env': '{}',
            'patterns': [gname]
        })
        idx += 1

    return {
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
        'gateway_up': gateway_up,
        'router_commit_mb': round(router_commit, 1),
        'router_pids': [p['pid'] for p in router_pids],
        'total_commit_mb': round(total_commit, 1),
        'servers': servers_list
    }

def print_table(data):
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 88)
    print("                      MCP SERVERS CLI MANAGER                         ")
    print(f" Time: {data['timestamp']}  |  MCP Router Gateway: {'ONLINE (127.0.0.1:3282)' if data['gateway_up'] else 'OFFLINE'}")
    print("=" * 88)
    print(f" #  | {'Server Name':<23} | {'Status':<9} | {'Source':<13} | {'PIDs':<14} | {'RAM Commit':<10} | {'CPU %':<5}")
    print("-" * 88)
    for s in data['servers']:
        pids_str = ", ".join(map(str, s['pids'][:2])) + ("..." if len(s['pids']) > 2 else "")
        ram_str = f"{s['commit_mb']:5.1f} MB" if s['type'] != 'remote' else "Cloud"
        cpu_str = f"{s['cpu']:4.1f}%" if s['type'] != 'remote' else "N/A"
        
        status_display = s['status']
        if s['status'] == 'RUNNING':
            status_display = "[RUNNING]"
        elif s['status'] == 'STOPPED':
            status_display = "[STOPPED]"
        elif s['status'] == 'ONLINE':
            status_display = "[ONLINE]"

        print(f" {s['num']:<2} | {s['name']:<23} | {status_display:<9} | {s['source']:<13} | {pids_str:<14} | {ram_str:<10} | {cpu_str:<5}")

    print("-" * 88)
    print(f" Total Servers RAM : {data['total_commit_mb']:6.1f} MB  |  MCP Router App: {data['router_commit_mb']:6.1f} MB")
    print(" Note: Servers with *name* were automatically detected from live OS processes.")
    print("=" * 88)

def kill_server(server_obj):
    killed = []
    # 1. Kill by PIDs if known
    for pid in server_obj.get('pids', []):
        try:
            p = psutil.Process(pid)
            p.kill()
            killed.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    # 2. Also search by patterns as safety
    patterns = server_obj.get('patterns', [server_obj['name'].lower()])
    for p in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmd = " ".join(p.info['cmdline'] or [])
            if any(pat.lower() in cmd.lower() for pat in patterns):
                if not any(ign in cmd.lower() for ign in ['mcp_cli_manager', 'test_', 'check_', 'inspect_']):
                    p.kill()
                    if p.info['pid'] not in killed:
                        killed.append(p.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed

def start_server(s):
    if s['type'] == 'remote':
        print(f"Cannot spawn remote cloud server '{s['name']}' locally.")
        return None
    if not s['command']:
        print(f"No command configured for '{s['name']}'.")
        return None

    cmd = s['command']
    args = json.loads(s['args'] or '[]')
    extra_env = json.loads(s['env'] or '{}')
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
        print(f"Error starting '{s['name']}': {e}")
        return None

def kill_all_servers(servers):
    total_killed = []
    for s in servers:
        if s['type'] != 'remote' and s['is_running']:
            k = kill_server(s)
            total_killed.extend(k)
    return total_killed

def interactive_loop():
    while True:
        data = get_servers_data()
        print_table(data)
        print("\nCommands:")
        print("  [1-N]   : Toggle Server (Start if Stopped, Kill if Running)")
        print("  [K]     : Kill ALL running MCP servers")
        print("  [S]     : Start ALL stopped local MCP servers")
        print("  [R]     : Refresh status (re-scans DB, Claude config & OS processes)")
        print("  [Q]     : Quit")
        
        try:
            choice = input("\nEnter choice: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if choice in ('q', 'exit'):
            print("Goodbye!")
            break
        elif choice == 'r':
            continue
        elif choice == 'k':
            killed = kill_all_servers(data['servers'])
            print(f"Killed {len(killed)} process(es): {killed}")
            time.sleep(1)
        elif choice == 's':
            for s in data['servers']:
                if s['type'] != 'remote' and not s['is_running']:
                    pid = start_server(s)
                    print(f"Started {s['name']} (PID {pid})")
            time.sleep(1)
        elif choice.isdigit():
            idx = int(choice)
            matched = [s for s in data['servers'] if s['num'] == idx]
            if not matched:
                print(f"Invalid server number: {idx}")
                time.sleep(1)
                continue
            s = matched[0]
            if s['type'] == 'remote':
                print(f"'{s['name']}' is a remote cloud server managed via HTTPS.")
                time.sleep(1.5)
            elif s['is_running']:
                killed = kill_server(s)
                print(f"Stopped '{s['name']}' (Terminated PIDs: {killed})")
                time.sleep(1)
            else:
                pid = start_server(s)
                print(f"Started '{s['name']}' (New PID: {pid})")
                time.sleep(1)
        else:
            print("Invalid input.")
            time.sleep(1)

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        data = get_servers_data()
        
        if cmd == 'status':
            print_table(data)
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
            print("  mcp-manager.bat              (Interactive menu)")
            print("  mcp-manager.bat status       (Show table once)")
            print("  mcp-manager.bat kill <name>  (Kill specific server)")
            print("  mcp-manager.bat kill-all     (Kill all servers)")
            print("  mcp-manager.bat start <name> (Start specific server)")
    else:
        interactive_loop()

if __name__ == '__main__':
    main()
