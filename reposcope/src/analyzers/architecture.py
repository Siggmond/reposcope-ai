from __future__ import annotations

from collections import Counter, defaultdict

from reposcope.src.scanner.types import Repo


def analyze_architecture(repo: Repo) -> dict:
    top_level = Counter()
    by_folder = defaultdict(list)

    for f in repo.iter_files():
        parts = f.rel_path.split("/")
        top = parts[0] if parts else "(root)"
        top_level[top] += 1

        folder = "/".join(parts[:-1]) if len(parts) > 1 else "(root)"
        by_folder[folder].append(f)

    main_folders = [
        {"name": name, "file_count": cnt}
        for name, cnt in top_level.most_common(25)
    ]

    entry_point_candidates = []
    for f in repo.iter_files():
        low = f.rel_path.lower()
        if low.endswith("main.py") or low.endswith("app.py") or low.endswith("index.js") or low.endswith("index.ts"):
            entry_point_candidates.append(f.rel_path)
        if low in {"manage.py", "setup.py", "pyproject.toml", "package.json"}:
            entry_point_candidates.append(f.rel_path)

    entry_point_candidates = sorted(set(entry_point_candidates))

    return {
        "main_folders": main_folders,
        "entry_points": entry_point_candidates[:20],
    }
