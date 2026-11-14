"""Small command journal used by project lifecycle and media tools."""
import datetime
import json
import subprocess
from .settings import ROOT


def log(message):
    with (ROOT / 'logs/build.log').open('a') as output:
        output.write(str(datetime.datetime.now(datetime.timezone.utc)) + ' ' + message + '\n')


def run(args, **kwargs):
    merge_output = kwargs.pop('merge_output', False)
    log('COMMAND argv=' + json.dumps(list(map(str, args))))
    result = subprocess.run(args, capture_output=True, text=True, **kwargs)
    log(result.stdout + result.stderr + '\nEXIT ' + str(result.returncode))
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:] or result.stdout[-3000:])
    return result.stdout + result.stderr if merge_output else result.stdout
