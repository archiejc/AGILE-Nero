"""Compatibility alias for agile_nero.robot.diagnostics.state."""

import sys

from agile_nero.robot.diagnostics import state as _module

sys.modules[__name__] = _module
