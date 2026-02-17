import os
import sys
import socket
import time
import configparser
import logging
from datetime import datetime, timezone

try:
    import psutil
except ImportError:
    sys.exit(1)

try:
    import docker
except ImportError:
    docker = None

try:
    from google.cloud import firestore
except ImportError:
    sys.exit(1)

if getattr(sys, 'frozen', False):
    script_dir = os.path.dirname(sys.executable)
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(script_dir, 'config.ini')
config = configparser.ConfigParser()
config.read(config_path, encoding='utf-8')  # UTF-8対応

log_path = os.path.join(script_dir, 'agent.log')
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

key_path = os.path.join(script_dir, 'agent-key.json')
if not os.path.exists(key_path):
    sys.exit(1)

try:
    db = firestore.Client.from_service_account_json(key_path)
except Exception:
    sys.exit(1)

def get_system_stats():
    disks = {}
    for part in psutil.disk_partitions(all=False):
        if 'fixed' in part.opts or (os.name != 'nt' and 'rw' in part.opts):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks[part.mountpoint] = usage.percent
            except Exception:
                pass
    return {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_partitions': disks
    }

def check_targets_status(monitor_type, config):
    results = {}
    if 'TARGET_NAMES' in config['Monitor']:
        target_str = config['Monitor']['TARGET_NAMES']
        target_list = [t.strip() for t in target_str.split(',') if t.strip()]
    else:
        old_target = config['Monitor'].get('PYTHON_SCRIPT_NAME')
        if old_target:
            target_list = [old_target]
        else:
            return {}

    if monitor_type == 'PC':
        running_processes = []
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                cmd = " ".join(p.info['cmdline']) if p.info['cmdline'] else ""
                name = p.info['name']
                running_processes.append((name.lower(), cmd.lower()))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        for target in target_list:
            target_lower = target.lower()
            is_running = False
            is_exe = target_lower.endswith('.exe')

            for proc_name, proc_cmd in running_processes:
                if is_exe:
                    if proc_name == target_lower:
                        is_running = True
                        break
                else:
                    if target_lower in proc_cmd:
                        is_running = True
                        break
            results[target] = is_running

    elif monitor_type == 'SERVER':
        if docker is None:
            return {}
        try:
            client = docker.from_env(timeout=5)
            for target in target_list:
                try:
                    container = client.containers.get(target)
                    results[target] = (container.status == 'running')
                except Exception:
                    results[target] = False
        except Exception:
            pass
    return results

def main():
    try:
        conf = config['General']
        monitor_conf = config['Monitor']
    except KeyError:
        return

    PC_ID = conf.get('PC_ID') or socket.gethostname()
    COLLECTION = conf.get('COLLECTION_NAME', 'computers')
    INTERVAL = int(conf.get('UPDATE_INTERVAL', 60))
    MONITOR_TYPE = monitor_conf.get('TYPE', 'PC').upper()

    print(f"--- エージェント開始 (ID: {PC_ID}) ---")

    while True:
        try:
            stats = get_system_stats()
            targets_status = check_targets_status(MONITOR_TYPE, config)
            
            data = {
                'cpu_percent': stats['cpu_percent'],
                'memory_percent': stats['memory_percent'],
                'disk_partitions': stats['disk_partitions'],
                'targets_status': targets_status,
                'last_seen': datetime.now(timezone.utc)
            }
            
            doc_ref = db.collection(COLLECTION).document(PC_ID)
            doc_ref.set(data)  # merge=True を削除済み
            
            logging.info(f"送信完了: Targets={list(targets_status.keys())}")
        
        except Exception as e:
            logging.error(f"Error: {e}")
            print(f"Error: {e}")
        
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()