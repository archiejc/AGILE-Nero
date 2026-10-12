#!/bin/zsh
set -eu
cd "${0:A:h}"
if ! command -v uv >/dev/null 2>&1; then
  print 'Install uv first: brew install uv'
  exit 1
fi
uv sync --locked --extra workflow --extra ml
.venv/bin/nero doctor --output outputs/deployment/environment.json
