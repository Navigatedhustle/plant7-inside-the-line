"""Use direct Docker access when available, with the existing group fallback."""
from functools import lru_cache
import shlex
import subprocess


@lru_cache(maxsize=1)
def direct_access():
    try:
        return subprocess.run(['docker', 'info', '--format', '{{.ServerVersion}}'], capture_output=True, timeout=15).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def docker_command(args):
    command = ['docker', *args]
    return command if direct_access() else ['sg', 'docker', '-c', shlex.join(command)]
