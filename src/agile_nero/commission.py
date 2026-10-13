"""Compatibility alias for explicit motor/feedback setup; import does not connect."""

import sys

from agile_nero.robot.diagnostics import commission as _module

sys.modules[__name__] = _module
