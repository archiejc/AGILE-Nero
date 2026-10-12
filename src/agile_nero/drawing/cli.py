"""Compatibility exports only; add new code to the domain module."""

from agile_nero.api.cli import MAX_INPUT_BYTES, main, unique_object

__all__ = ["MAX_INPUT_BYTES", "main", "unique_object"]

if __name__ == "__main__":
    import sys

    sys.exit(main())
