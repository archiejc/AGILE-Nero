"""Compatibility alias for agile_nero.robot.diagnostics.transport."""

import sys

from agile_nero.robot.diagnostics import transport as _module

sys.modules[__name__] = _module
