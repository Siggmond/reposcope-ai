from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class FileInfo:
    path: Path
    rel_path: str
    size_bytes: int
    extension: str
    lines: int | None


@dataclass(frozen=True)
class Repo:
    root: Path
    files: tuple[FileInfo, ...]

    def iter_files(self) -> Iterable[FileInfo]:
        return self.files
