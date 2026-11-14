#!/usr/bin/env python3
"""Read-only installation checks with actionable failures; never modifies the host."""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.docker_access import docker_command


def checks(live=False, pre_install=False, root=ROOT):
    results = []
    def check(name, passed, remedy=''):
        results.append({'check': name, 'ready': bool(passed), 'action': '' if passed else remedy})
    check('Linux / Python 3.12', platform.system() == 'Linux' and sys.version_info[:2] == (3, 12), 'Use Linux and Python 3.12.')
    if not pre_install:
        for path in ['static/inside/app.js', 'static/inside/index.html', 'data/mes.duckdb', 'data/maintenance_log.csv',
                     'data/shift_notes.md', 'static/inside/assembly.mp4', 'docs/captures/replay-run.json']:
            check(path, (root / path).is_file(), 'Extract a complete bundle and rerun ./scripts/install.sh.')
        for module in ['fastapi', 'uvicorn', 'duckdb', 'lancedb', 'openai', 'av', 'rank_bm25']:
            check('Python module: ' + module, importlib.util.find_spec(module) is not None, 'Rerun ./scripts/install.sh in this folder.')
    if live:
        check('aarch64 serving image target', platform.machine() in ('aarch64', 'arm64'), 'This pinned live stack targets an ARM64 Fury. Use replay mode on other machines.')
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=compute_cap,memory.total', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=10, check=True)
            capability, memory = result.stdout.splitlines()[0].split(',')
            check('Compatible GPU / memory', capability.strip() == '10.3' and float(memory) >= 240000, 'The pinned live stack requires the tested SM 10.3 Fury with at least 240000 MiB. Use replay mode or validate a separate model configuration.')
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            check('GPU driver visibility', False, 'Ask the machine administrator to provide the compatible NVIDIA driver stack, or use replay mode.')
        try:
            result = subprocess.run(docker_command(['info', '--format', '{{json .Runtimes}}']), capture_output=True, text=True, timeout=15, check=True)
            sys.path.insert(0, str(ROOT))
            from scripts.gpu_config import gpu_arguments
            try:
                compatible = bool(gpu_arguments(root))
            except RuntimeError:
                compatible = False
            check('Docker / GPU access', compatible, 'Docker access and NVIDIA Container Toolkit must be configured by the machine administrator. Replay mode requires neither.')
        except (OSError, subprocess.SubprocessError, ValueError):
            check('Docker access', False, 'Provide Docker group access and an operational NVIDIA container runtime, or use replay mode.')
        if not pre_install:
            manifest = json.loads((root / 'config/models.json').read_text())
            image = subprocess.run(docker_command(['image', 'inspect', manifest['image']]), capture_output=True, text=True, timeout=15)
            check('Pinned serving image', image.returncode == 0, 'Load the pinned image from the source Fury or use --download-models during live installation.')
            for model in manifest['models']:
                if model['role'] == 'vision':
                    continue
                path = root / 'models' / model['role']
                record = root / 'logs' / ('download-' + model['role'] + '.json')
                try:
                    metadata = json.loads(record.read_text())
                    valid = all(metadata.get(k) == model[k] for k in ('repo', 'revision')) and sum(p.stat().st_size for p in path.glob('*.safetensors')) == model['weight_bytes']
                except (OSError, ValueError):
                    valid = False
                check('Pinned weights: ' + model['role'], valid, 'Use --model-source with a complete Plant 7 source or --download-models.')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--pre-install', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    results = checks(args.live or args.pre_install, args.pre_install)
    if args.json:
        print(json.dumps({'ready': all(x['ready'] for x in results), 'checks': results}, indent=2))
    else:
        for item in results:
            print(('READY  ' if item['ready'] else 'FIX    ') + item['check'] + (': ' + item['action'] if item['action'] else ''))
        print('Vision is outside the working telemetry/document slice. No vision readiness is implied.')
    return 0 if all(x['ready'] for x in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
