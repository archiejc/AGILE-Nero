"""Compatibility alias for agile_nero.robot.diagnostics.cli."""

import sys

from agile_nero.robot.diagnostics import cli as _module

if __name__ == "__main__":
    sys.exit(_module.main())

sys.modules[__name__] = _module
