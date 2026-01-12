from __future__ import annotations

from pathlib import Path

from reposcope.src.scanner.types import Repo


def _exists(repo: Repo, rel: str) -> bool:
    p = repo.root / rel
    return p.exists()


def analyze_onboarding(repo: Repo, risks: dict, architecture: dict) -> dict:
    start_here = []

    for candidate in [
        "README.md",
        "CONTRIBUTING.md",
        "docs/README.md",
        "pyproject.toml",
        "package.json",
        "Makefile",
    ]:
        if _exists(repo, candidate):
            start_here.append(candidate)

    safe_to_modify = []
    risky_to_modify = []

    for f in repo.iter_files():
        low = f.rel_path.lower()
        if low.startswith("docs/") or low.endswith(".md"):
            safe_to_modify.append(f.rel_path)
        if any(g["file"] == f.rel_path for g in risks.get("god_files", [])):
            risky_to_modify.append(f.rel_path)

    safe_to_modify = safe_to_modify[:25]
    risky_to_modify = sorted(set(risky_to_modify))[:25]

    run_instructions = []
    if _exists(repo, "pyproject.toml"):
        run_instructions.append("python -m pip install -e .")
    if _exists(repo, "package.json"):
        run_instructions.append("npm install")
        run_instructions.append("npm test")
        run_instructions.append("npm run build")

    return {
        "start_here": start_here,
        "safe_to_modify": safe_to_modify,
        "risky_to_modify": risky_to_modify,
        "how_to_run": run_instructions,
        "entry_points": architecture.get("entry_points", []),
    }
