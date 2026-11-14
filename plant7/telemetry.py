"""Real device counters. Unknown or inaccessible values are null, never estimates."""
import asyncio
import json
import os
import re
import time
from pathlib import Path

import httpx

from .clients import MEASUREMENTS
from .settings import MODELS, ROOT

ACTIVE_SESSIONS = 0
JOBS = {}
PREVIOUS_TOKENS = {}


def default_interface():
    override = os.environ.get('P7_EXTERNAL_INTERFACE')
    if override:
        return override
    for line in Path('/proc/net/route').read_text().splitlines()[1:]:
        fields = line.split()
        if fields[1] == '00000000' and fields[0] != 'lo':
            return fields[0]
    return None


def transmitted(interface):
    for line in Path('/proc/net/dev').read_text().splitlines()[2:]:
        name, rest = line.split(':', 1)
        if name.strip() == interface:
            return int(rest.split()[8])
    return None


INTERFACE = default_interface()
BASELINE_TX = transmitted(INTERFACE) if INTERFACE else None
BASELINE_AT = time.time()


def reset_demo_counter():
    global BASELINE_TX, BASELINE_AT
    BASELINE_TX = transmitted(INTERFACE) if INTERFACE else None
    BASELINE_AT = time.time()
    return {'baseline_at': BASELINE_AT, 'interface': INTERFACE, 'scope': 'Interface TX since explicit demo counter reset'}


async def probe(role, model):
    out = {'role': role, 'model': model['repo'], 'port': model['port'], 'healthy': False, 'tokens_per_second': None}
    async with httpx.AsyncClient(trust_env=False, timeout=1.0) as api:
        try:
            response = await api.get(f"http://127.0.0.1:{model['port']}/health")
            out['healthy'] = response.status_code == 200
            metrics = await api.get(f"http://127.0.0.1:{model['port']}/metrics")
            if metrics.status_code == 200:
                values = re.findall(r'^vllm:generation_tokens_total(?:\{[^\n]*\})?\s+([\d.eE+\-]+)', metrics.text, flags=re.M)
                if values:
                    counter, now = sum(map(float, values)), time.monotonic()
                    previous = PREVIOUS_TOKENS.get(role)
                    if previous and counter >= previous[1] and now > previous[0]:
                        out['tokens_per_second'] = (counter-previous[1])/(now-previous[0])
                    PREVIOUS_TOKENS[role] = (now, counter)
        except Exception as error:
            out['error'] = str(error)[:180]
    return out


async def smi(arguments):
    process = await asyncio.create_subprocess_exec('nvidia-smi', *arguments,
                  stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), 3)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise RuntimeError('nvidia-smi query timed out')
    if process.returncode:
        raise RuntimeError(stderr.decode()[:300])
    return stdout.decode().strip()


def role_for_pid(pid):
    mapping = ROOT / 'runtime/containers.json'
    try:
        cgroup = Path(f'/proc/{pid}/cgroup').read_text()
        for role, container_id in json.loads(mapping.read_text()).items():
            if container_id[:12] in cgroup or container_id in cgroup:
                return role
    except (OSError, ValueError):
        pass
    return 'unattributed'


async def snapshot():
    models = await asyncio.gather(*(probe(role, model) for role, model in MODELS.items()))
    gpu = {'used_gb': None, 'total_gb': None, 'by_model_gb': {}, 'processes': []}
    try:
        raw, processes = await asyncio.gather(
            smi(['--query-gpu=memory.used,memory.total,utilization.gpu,power.draw', '--format=csv,noheader,nounits']),
            smi(['--query-compute-apps=pid,process_name,used_memory', '--format=csv,noheader,nounits']))
        used, total, utilization, power = map(float, raw.splitlines()[0].split(','))
        gpu.update(used_gb=used*2**20/1e9, total_gb=total*2**20/1e9, utilization_pct=utilization, power_w=power)
        for row in processes.splitlines():
            if not row.strip():
                continue
            pid, name, memory = [item.strip() for item in row.split(',', 2)]
            try:
                gb = float(memory)*2**20/1e9
            except ValueError:
                continue
            role = role_for_pid(int(pid))
            gpu['by_model_gb'][role] = gpu['by_model_gb'].get(role, 0) + gb
            gpu['processes'].append({'pid': int(pid), 'role': role, 'name': name, 'gb': gb})
        gpu['by_model_gb']['other or file cache'] = max(0, gpu['used_gb']-sum(gpu['by_model_gb'].values()))
    except Exception as error:
        gpu['error'] = str(error)
    mem = {line.split(':')[0]: int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()}
    tx = transmitted(INTERFACE) if INTERFACE else None
    rates = [row['tokens_per_second'] for row in models if row['tokens_per_second'] is not None]
    return {'sampled_at': time.time(), 'gpu': gpu, 'models': models,
            'ram': {'total_gb': mem['MemTotal']/1e9, 'available_gb': mem['MemAvailable']/1e9},
            'active_sessions': ACTIVE_SESSIONS, 'total_tokens_per_second': sum(rates) if rates else None,
            'network': {'interface': INTERFACE, 'transmitted_bytes_since_start': max(0, tx-BASELINE_TX) if tx is not None and BASELINE_TX is not None else None,
                        'baseline_at': BASELINE_AT, 'scope': 'Interface TX, including unrelated control traffic. Does not inspect payloads.'},
            'jobs': JOBS, 'recent_requests': list(MEASUREMENTS)[-20:]}
