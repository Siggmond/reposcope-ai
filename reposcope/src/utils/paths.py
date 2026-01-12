from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


def is_github_url(target: str) -> bool:
    try:
        u = urlparse(target)
    except ValueError:
        return False

    if u.scheme not in {"http", "https"}:
        return False
    if not u.netloc:
        return False

    host = u.netloc.lower()
    if host not in {"github.com", "www.github.com"}:
        return False

    parts = [p for p in u.path.split("/") if p]
    return len(parts) >= 2


def normalize_local_path(p: str) -> Path:
    return Path(p).expanduser().resolve()
