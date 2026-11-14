"""Handoff boundaries, independent sessions and honest per-run token accounting."""
import asyncio
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from plant7.app import app
from plant7 import inside_line as inside
from plant7.clients import RUN_USAGE, record_usage
from scripts.install import verify_bundle, desktop_entry, copy_models


def test_browser_capability_controls_only_its_own_synthetic_session(monkeypatch, tmp_path):
    monkeypatch.setattr(inside, 'RUNTIME', tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=app, client=('192.168.5.77', 1234))
        async with httpx.AsyncClient(transport=transport, base_url='http://plant7') as c:
            a = (await c.post('/api/stage/demo-session')).json()
            b = (await c.post('/api/stage/demo-session')).json()
            auth = {'X-Presenter-Key': a['session_key']}
            assert (await c.patch('/api/stage/sessions/' + a['session_id'], headers=auth, json={'chapter': 2})).status_code == 200
            assert (await c.patch('/api/stage/sessions/' + b['session_id'], headers=auth, json={'chapter': 4})).status_code == 403
            assert (await c.post('/api/demo-counter/start', headers=auth)).status_code == 403
            assert (await c.post('/api/stage/sessions', headers=auth)).status_code == 403
            view = await c.get('/api/stage/sessions/' + a['session_id'])
            assert '_control_hash' not in view.text and a['session_key'] not in view.text
            assert view.headers['cache-control'] == 'no-store'
            assert not (tmp_path / 'current.json').exists()
            replay = await c.post('/api/stage/sessions/' + a['session_id'] + '/jobs', headers=auth, json={'replay': True})
            assert replay.status_code == 200
            rid = replay.json()['run_id']
            result = (await c.get('/api/stage/jobs/' + rid)).json()
            assert result['token_economics']['basis'] == 'recorded'
            assert (await c.delete('/api/stage/jobs/' + rid, headers={'X-Presenter-Key': b['session_key']})).status_code == 403
            await c.post('/api/stage/sessions/' + a['session_id'] + '/reset', headers=auth)
            assert (await c.get('/api/stage/sessions/' + a['session_id'])).json()['stage']['run_id'] is None
            inside.JOBS.pop(rid)
    asyncio.run(scenario())


def test_replay_cannot_mislabel_a_different_dataset(monkeypatch, tmp_path):
    monkeypatch.setattr(inside, 'RUNTIME', tmp_path)
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://plant7') as c:
            s = (await c.post('/api/stage/demo-session')).json()
            r = await c.post('/api/stage/sessions/' + s['session_id'] + '/jobs', headers={'X-Presenter-Key': s['session_key']}, json={'replay': True, 'scenario': 'no_anomaly'})
            assert r.status_code == 409
    asyncio.run(scenario())


def test_token_usage_is_isolated_across_overlapping_tasks():
    async def task(tokens):
        sink = []
        context = RUN_USAGE.set(sink)
        try:
            await asyncio.sleep(0)
            record_usage({'role': 'brain', 'prompt_tokens': tokens, 'completion_tokens': 7})
            return inside.token_economics({'usage_measurements': sink, 'mode': 'live_local'})
        finally:
            RUN_USAGE.reset(context)
    async def scenario():
        a, b = await asyncio.gather(task(100), task(200))
        assert a['prompt_tokens'] == 100 and b['prompt_tokens'] == 200
        assert a['completion_tokens'] == b['completion_tokens'] == 7
    asyncio.run(scenario())


def test_incomplete_usage_cannot_be_costed_as_a_complete_run():
    usage = inside.token_economics({'mode': 'live_local', 'usage_measurements': [
        {'role': 'brain', 'prompt_tokens': 30, 'completion_tokens': 4},
        {'role': 'worker', 'prompt_tokens': None, 'completion_tokens': None},
        {'role': 'embed', 'prompt_tokens': 900, 'completion_tokens': 0}]})
    assert usage['prompt_tokens'] == 30 and usage['usage_complete'] is False
    empty = inside.token_economics({})
    assert empty['prompt_tokens'] is None and empty['completion_tokens'] is None


def test_bundle_tampering_fails_before_installation(tmp_path):
    (tmp_path / 'file.txt').write_text('original')
    (tmp_path / 'bundle-manifest.json').write_text(json.dumps({'sha256': {'file.txt': hashlib.sha256(b'original').hexdigest()}}))
    verify_bundle(tmp_path)
    (tmp_path / 'file.txt').write_text('changed')
    with pytest.raises(RuntimeError, match='checksum mismatch'):
        verify_bundle(tmp_path)


def test_desktop_launcher_quotes_spaces_and_desktop_metacharacters():
    entry = desktop_entry(Path('/tmp/Plant 7 $demo%'))
    assert 'Exec="/tmp/Plant 7 \\$demo%%/scripts/open_desktop.sh"' in entry
    assert '/home/gb300' not in entry


def test_retried_submission_reuses_the_saved_run(monkeypatch, tmp_path):
    monkeypatch.setattr(inside, 'RUNTIME', tmp_path)
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://plant7') as c:
            s = (await c.post('/api/stage/demo-session')).json()
            auth = {'X-Presenter-Key': s['session_key']}
            body = {'replay': True, 'request_id': 'd' * 32}
            url = '/api/stage/sessions/' + s['session_id'] + '/jobs'
            a = await c.post(url, headers=auth, json=body)
            b = await c.post(url, headers=auth, json=body)
            assert a.status_code == b.status_code == 200
            assert a.json()['run_id'] == b.json()['run_id']
            different = await c.post(url, headers=auth, json={**body, 'question': 'Different investigation question'})
            assert different.status_code == 409
            inside.JOBS.pop(a.json()['run_id'])
    asyncio.run(scenario())


def test_recorded_mode_cannot_call_live_stage_or_legacy_models(monkeypatch, tmp_path):
    monkeypatch.setattr(inside, 'RUNTIME', tmp_path)
    monkeypatch.setattr(inside, 'installation_mode', lambda: 'replay')
    from plant7 import app as backend
    monkeypatch.setattr(backend, 'installation_mode', lambda: 'replay')
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://plant7') as c:
            s = (await c.post('/api/stage/demo-session')).json()
            stage = await c.post('/api/stage/sessions/' + s['session_id'] + '/jobs', headers={'X-Presenter-Key': s['session_key']}, json={})
            legacy = await c.post('/api/investigate', json={'question': 'Inspect the source evidence'})
            assert stage.status_code == legacy.status_code == 503
    asyncio.run(scenario())


def test_recorded_recovery_is_available_even_when_live_queue_is_full(monkeypatch, tmp_path):
    monkeypatch.setattr(inside, 'RUNTIME', tmp_path)
    monkeypatch.setattr(inside, 'JOBS', {str(i): {'status': 'queued'} for i in range(24)})
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://plant7') as c:
            s = (await c.post('/api/stage/demo-session')).json()
            r = await c.post('/api/stage/sessions/' + s['session_id'] + '/jobs', headers={'X-Presenter-Key': s['session_key']}, json={'replay': True})
            assert r.status_code == 200 and r.json()['mode'] == 'captured_replay'
    asyncio.run(scenario())


def test_offline_python_wheels_can_accompany_upstream_live_asset_downloads(monkeypatch, tmp_path):
    # Python-index access and upstream model/image access are independent installation choices.
    import sys
    from scripts import install
    monkeypatch.setattr(install, 'ROOT', tmp_path)
    monkeypatch.setattr(install, 'verify_bundle', lambda: None)
    commands = []
    monkeypatch.setattr(install, 'command', lambda args, **kw: commands.append([str(x) for x in args]))
    monkeypatch.setattr(install, 'docker_command', lambda args: ['docker', *args])
    (tmp_path / '.venv/bin').mkdir(parents=True)
    (tmp_path / '.venv/bin/python').touch()
    (tmp_path / 'bootstrap').mkdir()
    (tmp_path / 'bootstrap/pip-test.whl').touch()
    (tmp_path / 'config').mkdir()
    (tmp_path / 'config/models.json').write_text(json.dumps({'image': 'example@sha256:pinned'}))
    monkeypatch.setattr(sys, 'argv', ['install.py', '--mode', 'live', '--download-models', '--wheelhouse', str(tmp_path / 'wheels'), '--no-shortcut'])
    install.main()
    assert any('--no-index' in c for c in commands)
    assert any('scripts/download_models.py' in c for c in commands)
    assert ['docker', 'pull', 'example@sha256:pinned'] in commands
    assert json.loads((tmp_path / 'runtime/install.json').read_text())['mode'] == 'live'


def test_checkpoint_retry_reuses_only_the_matching_complete_revision(tmp_path):
    from scripts.download_models import checkpoint_ready
    model = {'repo': 'example/checkpoint', 'revision': 'pinned', 'weight_bytes': 4}
    path = tmp_path / 'weights';path.mkdir()
    (path / 'config.json').write_text('{}')
    (path / 'model.safetensors').write_bytes(b'1234')
    record = tmp_path / 'download.json';record.write_text(json.dumps(model))
    assert checkpoint_ready(model, path, record)
    record.write_text(json.dumps({**model, 'revision': 'different'}))
    assert not checkpoint_ready(model, path, record)
    record.write_text(json.dumps(model))
    (path / 'model.safetensors').write_bytes(b'123')
    assert not checkpoint_ready(model, path, record)
