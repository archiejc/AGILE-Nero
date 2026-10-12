#!/bin/zsh
set -eu
cd "${0:A:h}"
.venv/bin/nero doctor --output outputs/deployment/environment.json
