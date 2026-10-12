"""Legacy unittest discovery entry; tests live in tests/offline by module."""

from pathlib import Path


def load_tests(loader, tests, pattern):
    root = Path(__file__).resolve().parents[1]
    return loader.discover(
        str(root / "tests/offline"), pattern="test_*.py", top_level_dir=str(root)
    )
