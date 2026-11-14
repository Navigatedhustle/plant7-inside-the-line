import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PORT = int(os.environ.get('P7_PORT', '8097'))
if not 1024 <= APP_PORT <= 65535:
    raise ValueError('P7_PORT must be between 1024 and 65535')
MANIFEST = json.loads((ROOT / 'config/models.json').read_text())
MODELS = {model['role']: model for model in MANIFEST['models']}
DB = ROOT / 'data/mes.duckdb'
TABLES = ('units', 'station_events', 'torque_results', 'defects', 'first_pass_yield', 'downtime')
HERO = 'First pass yield on Line 3 dropped about 4 points on Tuesday second shift. Why, and what should we contain right now?'
PRESETS = [HERO, 'Compare torque and angle trends by tool on Line 3 since Monday.',
           'Which shipped Line 3 units used T40-B between Monday recalibration and its verified return to service?',
           'Compare Line 3 first pass yield across all three shifts.',
           'What changed at Line 3 Station 40 since Monday?']


def installation_mode():
    path = ROOT / 'runtime/install.json'
    return json.loads(path.read_text())['mode'] if path.exists() else 'live'


def source_paths():
    paths = []
    for folder in ('work_instructions', 'fmea', 'supplier', 'plant_records'):
        paths.extend(sorted((ROOT / 'docs' / folder).glob('*.md')))
    paths.extend([ROOT / 'data/maintenance_log.csv', ROOT / 'data/shift_notes.md'])
    return paths
