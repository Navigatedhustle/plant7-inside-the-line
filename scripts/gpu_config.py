"""Select GPU access for this machine without changing Docker or driver configuration."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.docker_access import docker_command


def legacy_bindings_valid(args):
    if not args:
        return False
    for i, value in enumerate(args):
        if value == '--device' and (i + 1 >= len(args) or not Path(args[i + 1].split(':')[0]).exists()):
            return False
        if value == '--mount':
            mounts = dict(x.split('=', 1) for x in args[i + 1].split(',') if '=' in x)
            if 'src' in mounts and not Path(mounts['src']).exists():
                return False
    return True


def gpu_arguments(root=ROOT):
    # Explicit tested bindings belong to the development machine and are never distributed.
    existing = root / 'config/gpu_args.json'
    if existing.exists():
        args = json.loads(existing.read_text())
        if legacy_bindings_valid(args):
            return args
    result = subprocess.run(docker_command(['info', '--format', '{{json .Runtimes}}']), capture_output=True, text=True, timeout=15, check=True)
    if 'nvidia' not in json.loads(result.stdout):
        raise RuntimeError('NVIDIA container runtime is not configured on this machine. Ask its administrator to configure GPU access, or use recorded mode.')
    return ['--gpus', 'all']
