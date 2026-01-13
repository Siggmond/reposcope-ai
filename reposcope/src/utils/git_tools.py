from __future__ import annotations

import datetime
import subprocess
from pathlib import Path


def git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True, text=True)
        return True
    except Exception:
        return False


def git_diff_names(*, repo_root: Path, base: str) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--name-only", base],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    files = []
    for line in (result.stdout or "").splitlines():
        rel = line.strip().replace("\\", "/")
        if rel:
            files.append(rel)
    return sorted(set(files))


def git_file_authors(*, repo_root: Path, rel_path: str, max_commits: int = 200) -> list[str] | None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "log",
                f"-n{max_commits}",
                "--format=%an",
                "--",
                rel_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    authors = []
    for line in (result.stdout or "").splitlines():
        name = line.strip()
        if name:
            authors.append(name)
    return sorted(set(authors))


def git_file_last_commit_unix_ts(*, repo_root: Path, rel_path: str) -> int | None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "log",
                "-n1",
                "--format=%ct",
                "--",
                rel_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    raw = (result.stdout or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def days_since_unix_ts(*, now_utc: datetime.datetime, unix_ts: int) -> int:
    dt = datetime.datetime.fromtimestamp(unix_ts, tz=datetime.timezone.utc)
    delta = now_utc - dt
    return max(0, int(delta.total_seconds() // 86400))
