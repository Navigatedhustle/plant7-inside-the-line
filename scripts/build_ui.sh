#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if command -v node >/dev/null; then
  npm run build
else
  export PATH="$PWD/.tools/node-v22.14.0-linux-arm64/bin:$PATH"
  npm run build
fi
