#!/usr/bin/env python3
"""Only containers labeled for this project can be started or stopped here."""
import hashlib
import json
import os
import shlex
import signal
import socket
import stat
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plant7.audit import log, run
from plant7.settings import MANIFEST, MODELS, APP_PORT
from scripts.docker_access import docker_command


def docker(args):
    return run(docker_command(args), merge_output=bool(args and args[0] == 'logs'))


def owned_containers():
    ids = docker(['ps', '-aq', '--filter', 'label=p7.project=' + str(ROOT)]).split()
    if not ids:
        return []
    containers = json.loads(docker(['inspect'] + ids))
    for item in containers:
        name = item['Name'].lstrip('/')
        labels = item['Config'].get('Labels', {})
        known_media = name in ('p7-media', 'p7-media-video-v2') and item['Config'].get('User') == f'{os.getuid()}:{os.getgid()}'
        if not name.startswith('p7-') or (labels.get('p7.owner') != str(os.getuid()) and not known_media):
            raise RuntimeError('Refusing container with unverified project ownership: ' + name)
    return containers


def port_available(port):
    with socket.socket() as connection:
        return connection.connect_ex(('127.0.0.1', port)) != 0


def start_model(role):
    import httpx
    model = MODELS[role]
    weights = ROOT / 'models' / role
    if not (ROOT / 'logs' / ('download-' + role + '.json')).exists():
        log('BLOCKED ' + role + ': verified checkpoint missing')
        print('BLOCKED', role, 'checkpoint unavailable', flush=True)
        return False
    args = ['serve', '/model', '--served-model-name', model['repo'], '--host', '127.0.0.1',
            '--uds', '/sockets/model.sock', '--tensor-parallel-size', '1',
            '--gpu-memory-utilization', str(model['gpu_fraction']), '--max-model-len', str(model['max_model_len']),
            '--max-num-seqs', str(model['max_num_seqs']), '--max-num-batched-tokens', '4096',
            '--disable-log-requests']
    if model.get('runner') == 'pooling' or model.get('benchmark_eager'):
        args += ['--enforce-eager']
    else:
        sizes = [n for n in (1, 2, 4, 8, 16, 20) if n <= model['max_num_seqs']]
        args += ['--compilation-config', json.dumps({'mode': 0, 'cudagraph_mode': 'FULL_DECODE_ONLY',
                                                       'cudagraph_capture_sizes': sizes})]
    if model.get('runner'):
        args += ['--runner', model['runner']]
    else:
        args += ['--enable-chunked-prefill', '--enable-prefix-caching']
    if model.get('kv_dtype'):
        args += ['--kv-cache-dtype', model['kv_dtype']]
    if model.get('reasoning_parser'):
        args += ['--reasoning-parser', model['reasoning_parser']]
    if model.get('tool_parser'):
        args += ['--enable-auto-tool-choice', '--tool-call-parser', model['tool_parser']]
    if role == 'rerank':
        args += ['--hf-overrides', json.dumps({'architectures': ['Qwen3ForSequenceClassification'],
                 'classifier_from_token': ['no', 'yes'], 'is_original_qwen3_reranker': True}),
                 '--chat-template', '/project/config/qwen3_reranker.jinja']
    if 'Flash-Next' in model['repo']:
        args += ['--engram-config', '{"cpu_offload":false}']
    if role == 'vision':
        args += ['--allowed-local-media-path', '/project/data/video', '--limit-mm-per-prompt', '{"video":1,"image":0}',
                 '--media-io-kwargs', '{"video":{"num_frames":-1}}', '--mm-processor-kwargs',
                 '{"fps":2,"size":{"shortest_edge":131072,"longest_edge":262144}}']
    elif role in ('brain', 'worker'):
        # All visual work goes to the physical-reasoning model; skip VLM profiling.
        args += ['--limit-mm-per-prompt', '{"image":0,"video":0}']
    cache_digest = hashlib.sha256(json.dumps([MANIFEST['image'], args]).encode()).hexdigest()[:8]
    digest = hashlib.sha256(json.dumps([MANIFEST['image'], args, 'video-config-only-v2']).encode()).hexdigest()[:8]
    name = 'p7-' + role + '-' + digest
    existing = None
    for item in owned_containers():
        if item['Config'].get('Labels', {}).get('p7.role') != role:
            continue
        if item['Name'].lstrip('/') == name:
            existing = item
        elif item['State']['Running']:
            docker(['stop', '-t', '60', item['Id']])
    if not existing or not existing['State']['Running']:
        path = ROOT / 'runtime/sockets' / role / 'model.sock'
        if path.exists():
            info = path.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise RuntimeError('Refusing to remove a non-owned or non-socket path: ' + str(path))
            with socket.socket(socket.AF_UNIX) as connection:
                if connection.connect_ex(str(path)) == 0:
                    raise RuntimeError('A live service still owns the model socket: ' + str(path))
            path.unlink()
            log('Removed stale project Unix socket ' + str(path))
    if existing and existing['State']['Running']:
        container_id = existing['Id']
    elif existing:
        docker(['start', name])
        container_id = existing['Id']
    else:
        cache = ROOT / '.cache/models' / (role + '-' + cache_digest)
        cache.mkdir(parents=True, exist_ok=True)
        sockets = ROOT / 'runtime/sockets' / role
        sockets.mkdir(parents=True, exist_ok=True)
        from scripts.gpu_config import gpu_arguments
        gpu = gpu_arguments(ROOT)
        options = ['run', '-d', '--name', name, '--network', 'none', '--ipc', 'host',
                   '--user', f'{os.getuid()}:{os.getgid()}',
                   '--label', 'p7.project=' + str(ROOT), '--label', 'p7.owner=' + str(os.getuid()),
                   '--label', 'p7.role=' + role, '--log-opt', 'max-size=100m', '--log-opt', 'max-file=3',
                   '-v', str(weights) + ':/model:ro',
                   '-v', str(ROOT / 'data/video') + ':/project/data/video:ro',
                   '-v', str(ROOT / 'config') + ':/project/config:ro',
                   '-v', str(cache) + ':/cache', '-v', str(sockets) + ':/sockets',
                   '-e', 'HOME=/cache', '-e', 'HF_HOME=/cache/huggingface',
                   '-e', 'VLLM_CACHE_ROOT=/cache/vllm', '-e', 'TRITON_CACHE_DIR=/cache/triton',
                   '-e', 'XDG_CACHE_HOME=/cache', '-e', 'HF_HUB_OFFLINE=1', '-e', 'TRANSFORMERS_OFFLINE=1',
                   '-e', 'HF_HUB_DISABLE_TELEMETRY=1', '-e', 'VLLM_NO_USAGE_STATS=1',
                   '-e', 'DO_NOT_TRACK=1', '-e', 'TORCH_CUDA_ARCH_LIST=10.3a',
                   '-e', 'FLASHINFER_CUDA_ARCH_LIST=10.3a', '-e', 'CUTE_DSL_ARCH=sm_103a']
        options += gpu + ['--entrypoint', 'vllm', MANIFEST['image']] + args
        container_id = docker(options).strip()
    state_path = ROOT / 'runtime/containers.json'
    state_path.parent.mkdir(exist_ok=True)
    mapping = json.loads(state_path.read_text()) if state_path.exists() else {}
    mapping[role] = container_id
    state_path.write_text(json.dumps(mapping, indent=2))
    print('STARTING', role, name, flush=True)
    deadline = time.monotonic() + 900
    with httpx.Client(trust_env=False, timeout=2) as api:
        while time.monotonic() < deadline:
            try:
                if api.get(f"http://127.0.0.1:{model['port']}/health").status_code == 200:
                    print('HEALTHY', role, flush=True)
                    return True
            except httpx.HTTPError:
                pass
            state = json.loads(docker(['inspect', '--format', '{{json .State}}', name]))
            if not state['Running']:
                failure = docker(['logs', '--tail', '120', name])
                (ROOT / 'logs' / ('failure-' + role + '.log')).write_text(failure)
                with (ROOT / 'logs/blockers.md').open('a') as log_file:
                    log_file.write('\n' + role + ': failed startup; see failure-' + role + '.log.\n')
                print(failure, flush=True)
                return False
            time.sleep(3)
    raise RuntimeError('Model health timed out: ' + role)


def start_models(roles):
    start_proxy()
    if sum(model['gpu_fraction'] for model in MODELS.values()) > .920001:
        raise RuntimeError('Combined GPU fractions exceed 0.92')
    ordered = sorted((m for role, m in MODELS.items() if not roles or role in roles), key=lambda m: -m['weight_bytes'])
    success = True
    for model in ordered:
        ready = start_model(model['role'])
        success = success and ready
        if model['role'] == 'brain' and not ready:
            break
    return success


def start_proxy():
    path = ROOT / 'runtime/proxy.json'
    if path.exists():
        old = json.loads(path.read_text())
        proc = Path('/proc') / str(old['pid'])
        try:
            if proc.stat().st_uid == os.getuid() and (proc / 'cwd').resolve() == ROOT and (proc / 'stat').read_text().rsplit(')', 1)[1].split()[19] == old['start_ticks']:
                return
        except FileNotFoundError:
            pass
    for port in [m['port'] for m in MODELS.values()] + [8013]:
        if not port_available(port):
            raise RuntimeError('Cannot start loopback proxy: port occupied ' + str(port))
    path.parent.mkdir(exist_ok=True)
    args = [str(ROOT / '.venv/bin/python'), '-m', 'plant7.proxy']
    log('COMMAND ' + shlex.join(args))
    with (ROOT / 'logs/proxy.log').open('ab') as output:
        proc = subprocess.Popen(args, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=output, stderr=output, start_new_session=True)
    path.write_text(json.dumps({'pid': proc.pid, 'start_ticks': Path(f'/proc/{proc.pid}/stat').read_text().rsplit(')', 1)[1].split()[19]}))
    time.sleep(.5)
    if proc.poll() is not None:
        raise RuntimeError('Loopback proxy exited; inspect logs/proxy.log')


def start_app():
    state_path = ROOT / 'runtime/app.json'
    if state_path.exists():
        old = json.loads(state_path.read_text())
        p = Path('/proc') / str(old['pid'])
        try:
            if p.exists() and p.stat().st_uid == os.getuid() and (p / 'cwd').resolve() == ROOT and b'plant7.app:app' in (p / 'cmdline').read_bytes() and (p / 'stat').read_text().rsplit(')', 1)[1].split()[19] == old['start_ticks']:
                if old.get('port', 8097) != APP_PORT:
                    raise RuntimeError('This checkout is already running on another port. Stop it before changing P7_PORT.')
                print(f'App already running at http://127.0.0.1:{APP_PORT}', flush=True)
                return
        except FileNotFoundError:
            pass
    if not port_available(APP_PORT):
        raise RuntimeError(f'App port {APP_PORT} is already occupied; choose P7_PORT or stop that application yourself')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    args = [str(ROOT / '.venv/bin/python'), '-m', 'uvicorn', 'plant7.app:app', '--host', '0.0.0.0', '--port', str(APP_PORT), '--timeout-graceful-shutdown', '15']
    log('COMMAND ' + shlex.join(args))
    with (ROOT / 'logs/app.log').open('ab') as output:
        proc = subprocess.Popen(args, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=output, start_new_session=True)
    state_path.parent.mkdir(exist_ok=True)
    state_path.write_text(json.dumps({'pid': proc.pid, 'port': APP_PORT, 'start_ticks': Path(f'/proc/{proc.pid}/stat').read_text().rsplit(')', 1)[1].split()[19]}))
    log('START APP pid=' + str(proc.pid))
    import httpx
    with httpx.Client(trust_env=False, timeout=1) as api:
        for _ in range(30):
            if proc.poll() is not None:
                raise RuntimeError('App exited; inspect logs/app.log')
            try:
                if api.get(f'http://127.0.0.1:{APP_PORT}/api/config').status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(.5)
        else:
            raise RuntimeError('App readiness timed out')
    print(f'http://127.0.0.1:{APP_PORT}', flush=True)


def stop():
    # Cancel only exact, same-user project controllers before they can start another model.
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            args = [x.decode() for x in (proc / 'cmdline').read_bytes().split(b'\0') if x]
            controller = len(args) > 2 and args[1:3] == ['scripts/manage.py', 'models']
            benchmark = len(args) > 1 and args[1] in ('scripts/compare_workers.py', 'scripts/benchmark_workers.py', 'scripts/benchmark.py')
            if (controller or benchmark) and proc.stat().st_uid == os.getuid() and (proc / 'cwd').resolve() == ROOT:
                os.kill(int(proc.name), signal.SIGTERM)
                log('SIGTERM project controller ' + proc.name)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    for item in (owned_containers() if (ROOT / 'runtime/containers.json').exists() else []):
        if item['State']['Running']:
            docker(['stop', '-t', '60', item['Id']])
    stopped = []
    for state_path in [ROOT / 'runtime/app.json', ROOT / 'runtime/proxy.json']:
      if state_path.exists():
        saved = json.loads(state_path.read_text())
        p = Path('/proc') / str(saved['pid'])
        try:
            if p.stat().st_uid == os.getuid() and (p / 'cwd').resolve() == ROOT and (p / 'stat').read_text().rsplit(')', 1)[1].split()[19] == saved['start_ticks']:
                os.kill(saved['pid'], signal.SIGTERM)
                stopped.append(saved)
                log('SIGTERM project service ' + str(saved['pid']))
        except FileNotFoundError:
            pass
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        alive = []
        for saved in stopped:
            try:
                fields = Path(f"/proc/{saved['pid']}/stat").read_text().rsplit(')', 1)[1].split()
                if fields[19] == saved['start_ticks'] and fields[0] != 'Z':
                    alive.append(saved)
            except FileNotFoundError:
                pass
        if not alive:
            break
        time.sleep(.25)
    else:
        raise RuntimeError('A project service is still stopping; inspect runtime state before restoring previous services')
    print('Stopped only this project. Containers and weights preserved.', flush=True)


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'models':
        raise SystemExit(0 if start_models(sys.argv[2:]) else 2)
    if action == 'app':
        start_app()
    elif action == 'stop':
        stop()
