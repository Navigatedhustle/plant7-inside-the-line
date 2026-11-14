#!/usr/bin/env python3
"""Download pinned accessible checkpoints, keeping all caches inside the project."""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def checkpoint_ready(model, path, record):
    try:
        measured = json.loads(record.read_text())
        return (all(measured.get(k) == model[k] for k in ('repo', 'revision'))
                and (path / 'config.json').is_file()
                and sum(f.stat().st_size for f in path.glob('*.safetensors')) == model['weight_bytes'])
    except (OSError, ValueError):
        return False


def main():
    os.environ['HF_HOME'] = str(ROOT / '.cache/huggingface')
    os.environ['HF_HUB_CACHE'] = str(ROOT / '.cache/huggingface/hub')
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    from huggingface_hub import snapshot_download
    (ROOT / 'logs').mkdir(exist_ok=True)
    (ROOT / 'models').mkdir(exist_ok=True)
    manifest = json.loads((ROOT / 'config/models.json').read_text())
    roles = sys.argv[1:] or [m['role'] for m in sorted(manifest['models'], key=lambda m: -m['weight_bytes'])]
    for role in roles:
        model = (dict(manifest['challenger_worker'], role=role) if role == 'challenger_worker'
                 else next(m for m in manifest['models'] if m['role'] == role))
        path = ROOT / 'models' / role
        record = ROOT / 'logs' / ('download-' + role + '.json')
        if checkpoint_ready(model, path, record):
            print('REUSING', role, 'verified local checkpoint', flush=True)
            continue
        token = os.environ.get('HF_TOKEN')
        if model.get('gated') and not token:
            with (ROOT / 'logs/blockers.md').open('a') as log:
                log.write('\n' + role + ': gated checkpoint skipped because HF_TOKEN is absent.\n')
            print('BLOCKED', role, 'gated model without HF_TOKEN', flush=True)
            continue
        existing = sum(f.stat().st_size for f in path.glob('*.safetensors'))
        missing = max(0, model['weight_bytes'] - existing)
        if shutil.disk_usage(ROOT).free - missing < 20 * 1024**3:
            raise SystemExit('STOP: remaining checkpoint download would breach 20 GiB free-space reserve')
        print('DOWNLOADING', role, model['repo'], model['revision'], flush=True)
        snapshot_download(repo_id=model['repo'], revision=model['revision'], local_dir=str(path),
                          token=token or False, max_workers=6,
                          allow_patterns=['*.safetensors', '*.json', '*.jinja', '*.txt', '*.model', 'LICENSE*'],
                          ignore_patterns=['original/*', '*/*.safetensors'])
        logical = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        weight_bytes = sum(f.stat().st_size for f in path.glob('*.safetensors'))
        if weight_bytes != model['weight_bytes']:
            raise RuntimeError('Downloaded weight-byte total does not match verified manifest')
        measured = dict(role=role, repo=model['repo'], revision=model['revision'], logical_bytes=logical,
                        safetensors_bytes=weight_bytes, allocated_bytes=sum(f.stat().st_blocks * 512 for f in path.rglob('*') if f.is_file()))
        temp = record.with_suffix('.tmp')
        temp.write_text(json.dumps(measured, indent=2));temp.replace(record)
        print('DOWNLOADED', json.dumps(measured), flush=True)


if __name__ == '__main__':
    main()
