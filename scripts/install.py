#!/usr/bin/env python3
"""Relocatable, unprivileged installation. No machine or network configuration changes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.docker_access import docker_command


def verify_bundle(root=ROOT):
    manifest = root / 'bundle-manifest.json'
    if not manifest.exists():
        return  # Developer checkout; packaged releases always carry the file.
    for relative, expected in json.loads(manifest.read_text())['sha256'].items():
        path = root / relative
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise RuntimeError('Missing or unsafe bundle file: ' + relative)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Bundle checksum mismatch: ' + relative + '. Extract a fresh copy before installing.')


def command(args, **kwargs):
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True, **kwargs)


def desktop_entry(root):
    # Desktop Exec quoting is not shell quoting. Escape according to the desktop file grammar.
    def quote(value):
        return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'
    return '\n'.join(['[Desktop Entry]', 'Version=1.0', 'Type=Application',
        'Name=Plant 7: Inside the Line', 'Comment=Launch the guided local investigation',
        'Exec=' + quote(root / 'scripts/open_desktop.sh'), 'Path=' + str(root),
        'Icon=applications-engineering', 'Terminal=true', 'Categories=Education;Engineering;', ''])


def copy_models(source, root=ROOT):
    """Accept only complete pinned checkpoints. Copy them; never mount another project's directory."""
    manifest = json.loads((root / 'config/models.json').read_text())
    for model in manifest['models']:
        role = model['role']
        if role == 'vision':
            continue
        src = source / 'models' / role
        record = source / 'logs' / ('download-' + role + '.json')
        if not record.is_file() or not src.is_dir():
            raise RuntimeError('Model source is missing verified ' + role + '. Use a complete Plant 7 source or --download-models.')
        measured = json.loads(record.read_text())
        if any(measured.get(k) != model[k] for k in ('repo', 'revision')):
            raise RuntimeError('Model source revision mismatch: ' + role)
        if sum(f.stat().st_size for f in src.glob('*.safetensors')) != model['weight_bytes']:
            raise RuntimeError('Model source weight size mismatch: ' + role)
        target = root / 'models' / role
        if target.resolve() == src.resolve():
            continue
        if target.exists() and (root / 'logs' / ('download-' + role + '.json')).exists():
            current = json.loads((root / 'logs' / ('download-' + role + '.json')).read_text())
            if all(current.get(k) == model[k] for k in ('repo', 'revision')) and sum(f.stat().st_size for f in target.glob('*.safetensors')) == model['weight_bytes']:
                continue
        if target.exists():
            raise RuntimeError('Refusing to replace existing weights: ' + str(target))
        if shutil.disk_usage(root).free < model['weight_bytes'] + 20 * 1024**3:
            raise RuntimeError('Insufficient disk space to copy ' + role + ' with 20 GiB reserve.')
        print('Copying pinned checkpoint:', role, flush=True)
        # copytree does not overwrite an existing target; use a staging directory for interrupted copies.
        staging = root / 'models' / (role + '.installing')
        if staging.exists():
            raise RuntimeError('An interrupted copy remains at ' + str(staging) + '. Inspect it before retrying.')
        staging.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, staging, ignore=shutil.ignore_patterns('.cache', '.git'))
        staging.rename(target)
        (root / 'logs' / ('download-' + role + '.json')).write_text(json.dumps(measured, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['replay', 'live'], default='replay')
    parser.add_argument('--model-source', type=Path, help='Existing Plant 7 folder containing models/ and logs/download-*.json')
    parser.add_argument('--download-models', action='store_true', help='Download the four pinned accessible models (~157 GB) and serving image')
    parser.add_argument('--wheelhouse', type=Path, help='Offline Python wheel folder; no package-index requests')
    parser.add_argument('--no-shortcut', action='store_true')
    args = parser.parse_args()
    if platform.system() != 'Linux' or sys.version_info[:2] != (3, 12):
        parser.error('Supported install target: Linux with Python 3.12. Live inference also requires a compatible Fury GPU stack.')
    if args.mode == 'replay' and (args.model_source or args.download_models):
        parser.error('Use --mode live when supplying model weights.')
    if args.model_source and args.download_models:
        parser.error('Choose --model-source or --download-models.')
        verify_bundle()
    for name in ('logs', 'runtime', 'models', '.cache'):
        (ROOT / name).mkdir(exist_ok=True)
    # Fail before dependency installation for unsupported live hardware or occupied model ports.
    if args.mode == 'live':
        command([sys.executable, 'scripts/doctor.py', '--pre-install'])
    python = ROOT / '.venv/bin/python'
    marker = ROOT / '.venv/plant7-environment.json'
    if marker.exists() and json.loads(marker.read_text())['root'] != str(ROOT):
        import time
        (ROOT / '.venv').rename(ROOT / ('.venv-before-move-' + str(time.time_ns())))
    if not python.exists():
        print('Creating local Python environment…', flush=True)
        venv.EnvBuilder(with_pip=False).create(ROOT / '.venv')
    marker.write_text(json.dumps({'root': str(ROOT)}))
    bootstrap = next((ROOT / 'bootstrap').glob('pip-*.whl'))
    pip_code = "import sys;sys.path.insert(0,sys.argv.pop(1));from pip._internal.cli.main import main;raise SystemExit(main())"
    pip_args = ['install', '--disable-pip-version-check', '--cache-dir', str(ROOT / '.cache/pip'), '-r', 'requirements.lock']
    if args.wheelhouse:
        pip_args += ['--no-index', '--find-links', str(args.wheelhouse.resolve())]
    command([python, '-c', pip_code, bootstrap, *pip_args])
    command([python, 'scripts/prepare_inside.py'])
    if args.model_source:
        copy_models(args.model_source.resolve())
    if args.download_models:
        command([python, 'scripts/download_models.py', 'brain', 'worker', 'embed', 'rerank'])
        manifest = json.loads((ROOT / 'config/models.json').read_text())
        command(docker_command(['pull', manifest['image']]))
    if args.mode == 'live':
        command([python, 'scripts/doctor.py', '--live'])
    # Write installation state only after every required step succeeds. Preserve credentials/sessions.
    from datetime import datetime, timezone
    state = {'mode': args.mode, 'installed_at': datetime.now(timezone.utc).isoformat(), 'root': str(ROOT)}
    temp = ROOT / 'runtime/install.tmp'
    temp.write_text(json.dumps(state, indent=2))
    temp.replace(ROOT / 'runtime/install.json')
    entry = ROOT / 'Plant 7.desktop'
    entry.write_text(desktop_entry(ROOT));entry.chmod(0o755)
    if not args.no_shortcut:
        apps = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'applications'
        apps.mkdir(parents=True, exist_ok=True)
        (apps / 'plant7-inside-the-line.desktop').write_text(desktop_entry(ROOT))
    print('\nInstalled ' + args.mode + ' mode. Launch: ./scripts/open_desktop.sh')
    print('Recorded mode runs without models or Docker. Live mode uses the four pinned local roles; vision remains unavailable.')


if __name__ == '__main__':
    try:
        import fcntl
        with (ROOT / '.plant7-install.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Installation is already running in this folder. Wait for that installer to finish.')
            main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print('\nInstall incomplete:', error, file=sys.stderr)
        raise SystemExit(1)
