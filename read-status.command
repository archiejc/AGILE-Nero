#!/bin/zsh
set -eu
cd "${0:A:h}"
.venv/bin/nero read-state --config configs/local/robot.toml --seconds 5 --output outputs/deployment/robot-state.json
