from __future__ import annotations

from pathlib import Path


_DEFAULT_IGNORED_DIRS = {
    ".git",
    ".reposcope",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}

_DEFAULT_IGNORED_FILES = {
    ".ds_store",
}


def should_ignore_path(root: Path, path: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True

    parts = {p.lower() for p in rel.parts}
    for d in _DEFAULT_IGNORED_DIRS:
        if d.lower() in parts:
            return True

    if path.name.lower() in _DEFAULT_IGNORED_FILES:
        return True

    return False
