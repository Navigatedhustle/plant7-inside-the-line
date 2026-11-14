#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
.venv/bin/python scripts/log_command.py '.venv/bin/python scripts/manage.py stop'
