from __future__ import annotations

from pathlib import Path

from reposcope.src.scanner.types import FileInfo, Repo
from reposcope.src.utils.ignore import should_ignore_path


def _count_lines(path: Path) -> int | None:
    try:
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return None


def scan_repo(root: Path) -> Repo:
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Repository root not found: {root}")

    files: list[FileInfo] = []

    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if should_ignore_path(root, p):
            continue

        rel = str(p.relative_to(root)).replace("\\", "/")
        ext = p.suffix.lower().lstrip(".")
        try:
            size = p.stat().st_size
        except OSError:
            continue

        lines = None
        if ext in {"py", "ts", "tsx", "js", "jsx", "java", "go", "rs", "kt", "swift", "cs"}:
            lines = _count_lines(p)

        files.append(
            FileInfo(
                path=p,
                rel_path=rel,
                size_bytes=size,
                extension=ext,
                lines=lines,
            )
        )

    files.sort(key=lambda f: f.rel_path)
    return Repo(root=root, files=tuple(files))
