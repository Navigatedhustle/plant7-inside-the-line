#!/usr/bin/env python3
"""Build an allowlisted, checksummed handoff. Excludes credentials, sessions and model weights."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
NAME = 'plant7-inside-the-line'


def package_files(root=ROOT):
    paths = set()
    for name in ['README.md', 'QUICKSTART.md', 'requirements.lock', 'package.json', 'package-lock.json', 'tsconfig.json']:
        paths.add(root / name)
    for folder in ['plant7', 'frontend', 'config', 'tests', 'bootstrap']:
        paths.update(p for p in (root / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    paths.discard(root / 'config/gpu_args.json')
    # Operator scripts that restore other projects or change sharing never enter the handoff.
    scripts = ['install.sh', 'install.py', 'doctor.py', 'docker_access.py', 'gpu_config.py', 'launch.py', 'manage.py', 'prepare_inside.py', 'build_scenarios.py',
               'start_all.sh', 'stop_all.sh', 'open_desktop.sh', 'healthcheck.sh', 'healthcheck.py', 'restart_app.py',
               'download_models.py', 'log_command.py', 'build_ui.sh', 'validate_guided_ui.py', 'package_demo.py', 'build_install_guide.py']
    paths.update(root / 'scripts' / name for name in scripts)
    for folder in ['work_instructions', 'fmea', 'supplier', 'plant_records']:
        paths.update(p for p in (root / 'docs' / folder).rglob('*') if p.is_file())
    paths.update((root / 'docs').glob('*.md'))
    paths.update((root / 'docs').glob('*.pdf'))
    paths.update((root / 'docs').glob('*LICENSE_INVENTORY.json'))
    paths.add(root / 'docs/captures/replay-run.json')
    paths.update(p for p in (root / 'docs/captures/guided').glob('*') if p.is_file())
    # Include only the synthetic source records needed to reproduce the inspected story.
    paths.update(root / 'data' / name for name in ['mes.duckdb', 'maintenance_log.csv', 'shift_notes.md', 'generation_manifest.json'])
    paths.update(p for p in (root / 'static').rglob('*') if p.is_file())
    for path in paths:
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise RuntimeError('Missing or unsafe release source: ' + str(path.relative_to(root)))
    return sorted(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / (NAME + '.tar.gz')
    if archive.exists():
        parser.error('Release already exists. Choose a new output folder to preserve previous handoffs.')
    with tempfile.TemporaryDirectory(prefix='plant7-release-') as temp:
        stage = Path(temp) / NAME
        stage.mkdir()
        checksums = {}
        for src in package_files():
            relative = src.relative_to(ROOT)
            dest = stage / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            checksums[str(relative)] = hashlib.sha256(dest.read_bytes()).hexdigest()
        (stage / 'bundle-manifest.json').write_text(json.dumps({'format': 1, 'name': NAME, 'sha256': checksums,
            'weights_included': False, 'scope': 'Synthetic telemetry/document demonstration. Vision unavailable. Review requirements remain in docs/KNOWN_LIMITATIONS.md.'}, indent=2))
        with tarfile.open(archive, 'w:gz') as tar:
            tar.add(stage, arcname=NAME)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / (archive.name + '.sha256')).write_text(digest + '  ' + archive.name + '\n')
    print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': digest, 'files': len(checksums)}, indent=2))


if __name__ == '__main__':
    main()
