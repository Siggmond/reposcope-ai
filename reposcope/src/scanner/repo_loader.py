from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from reposcope.src.scanner.repo_scanner import scan_repo
from reposcope.src.utils.paths import is_github_url, normalize_local_path


@dataclass(frozen=True)
class LoadedRepo:
    root: Path
    is_temp: bool


def _clone_github_repo(url: str) -> LoadedRepo:
    tmp_dir = Path(tempfile.mkdtemp(prefix="reposcope_"))

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(tmp_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError("git is required to analyze GitHub URLs") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to clone repo. git said: {e.stderr.strip() or e.stdout.strip()}"
        ) from e

    return LoadedRepo(root=tmp_dir, is_temp=True)


def load_repo(target: str):
    loaded = None
    if is_github_url(target):
        loaded = _clone_github_repo(target)
        root = loaded.root
    else:
        root = normalize_local_path(target)

    repo = scan_repo(root)
    return repo
