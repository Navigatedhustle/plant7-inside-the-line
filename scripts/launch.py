#!/usr/bin/env python3
"""Serialize startup and verify the chosen slice before opening a browser."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--mode', choices=['live', 'replay'])
    args = parser.parse_args()
    for folder in ('runtime', 'logs'):
        (ROOT / folder).mkdir(exist_ok=True)
    installed = ROOT / 'runtime/install.json'
    mode = args.mode or (json.loads(installed.read_text())['mode'] if installed.exists() else 'live')
    # Only one startup controller per checkout. Other launches wait and then reuse healthy services.
    with (ROOT / 'runtime/launch.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Plant 7 is already starting. Waiting for the same launch…', flush=True)
            deadline = time.monotonic() + 1800
            while time.monotonic() < deadline:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    time.sleep(1)
            else:
                raise RuntimeError('Another startup is still active. Inspect logs/launch.log.')
        from scripts.doctor import checks
        issues = [c for c in checks(live=mode == 'live') if not c['ready']]
        if issues:
            raise RuntimeError('\n'.join(c['check'] + ': ' + c['action'] for c in issues))
        subprocess.run([sys.executable, 'scripts/prepare_inside.py'], cwd=ROOT, check=True)
        from scripts.manage import start_app, start_models
        from plant7.settings import APP_PORT
        print('Starting ' + mode + ' mode…', flush=True)
        if mode == 'live' and not start_models(['brain', 'worker', 'embed', 'rerank']):
            raise RuntimeError('A required local model did not start. See logs/failure-*.log; recorded mode is available with --mode replay.')
        start_app()
        import httpx
        with httpx.Client(trust_env=False, timeout=10) as client:
            health = client.get(f'http://127.0.0.1:{APP_PORT}/api/health').json()
        if not health['presentation_ready'] or not health['captured_local_replay']:
            raise RuntimeError('Presentation artifacts are incomplete. Rerun installation.')
        if mode == 'live' and not health['telemetry_investigation_ready']:
            raise RuntimeError('Local inference is not ready. Run ./scripts/healthcheck.sh.')
        url = f'http://127.0.0.1:{APP_PORT}/' + ('?walkthrough=recorded' if mode == 'replay' else '')
        print('Ready: ' + url, flush=True)
        print('Vision is unavailable; the working slice covers telemetry and documents.', flush=True)
        if args.open:
            if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
                subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                print('No desktop session detected. Open the URL in a browser on this machine.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Plant 7 needs attention: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
