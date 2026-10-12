"""Compatibility entry point; prefer python -m agile_nero.api."""

import sys

from agile_nero.api.cli import main

sys.exit(main())
