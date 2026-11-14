#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv/bin/python ]]; then
  echo 'Install Plant 7 first: ./scripts/install.sh'
  exit 1
fi
mkdir -p logs
.venv/bin/python scripts/launch.py --open "$@" 2>&1 | tee -a logs/launch.log
