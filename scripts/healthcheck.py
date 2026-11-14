#!/usr/bin/env python3
"""Check the installed working slice; full multimodal readiness remains separate."""
import argparse
import json
import sys
import os
import httpx
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--full', action='store_true', help='Require the separately gated full multimodal stack')
parser.add_argument('--json', action='store_true')
args = parser.parse_args()
try:
    with httpx.Client(trust_env=False, timeout=10) as api:
        response = api.get('http://127.0.0.1:' + os.environ.get('P7_PORT', '8097') + '/api/health')
        response.raise_for_status()
        data = response.json()
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print('Application: READY')
        print('Installed mode:', data['installation_mode'])
        print('Working demo slice:', 'READY' if data['working_slice_ready'] else 'NEEDS ATTENTION')
        for model in data['models']:
            print(model['role'] + ': ' + ('READY' if model['healthy'] else 'UNAVAILABLE'))
        print('Full vision acceptance:', 'READY' if data['ready'] and data['golden_run'] else 'NOT ACCEPTED; outside the working slice')
    sys.exit(0 if (data['ready'] and data['golden_run'] if args.full else data['working_slice_ready']) else 1)
except Exception as error:
    print('Health check failed:', error)
    sys.exit(1)
