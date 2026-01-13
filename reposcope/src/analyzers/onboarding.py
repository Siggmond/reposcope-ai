from __future__ import annotations

import ast
import datetime
from collections import defaultdict
from pathlib import Path

from reposcope.src.scanner.types import Repo
from reposcope.src.utils.git_tools import (
    days_since_unix_ts,
    git_file_authors,
    git_file_last_commit_unix_ts,
)


def _exists(repo: Repo, rel: str) -> bool:
    p = repo.root / rel
    return p.exists()


def _python_module_name_for_relpath(rel_path: str) -> str | None:
    if not rel_path.endswith(".py"):
        return None
    if rel_path.startswith("."):
        return None

    no_ext = rel_path[:-3]
    parts = [p for p in no_ext.split("/") if p]
    if not parts:
        return None
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    return ".".join(parts)


def _build_python_module_index(repo: Repo) -> dict[str, str]:
    out: dict[str, str] = {}
    for f in repo.iter_files():
        if f.extension != "py":
            continue
        mod = _python_module_name_for_relpath(f.rel_path)
        if mod:
            out[mod] = f.rel_path
    return out


def _resolve_import_to_module(*, module_index: dict[str, str], importer: str, imported: str) -> str | None:
    if not imported:
        return None

    parts = imported.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in module_index:
            return candidate

    if imported.startswith("."):
        base = importer.split(".")
        while imported.startswith("."):
            imported = imported[1:]
            if base:
                base = base[:-1]
        if not base:
            return None
        tail = imported.lstrip(".")
        candidate = ".".join([*base, *([p for p in tail.split(".") if p])])
        if candidate in module_index:
            return candidate

    return None


def _python_import_edges(*, module_index: dict[str, str], importer_module: str, text: str) -> set[str]:
    out: set[str] = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = _resolve_import_to_module(
                    module_index=module_index,
                    importer=importer_module,
                    imported=alias.name,
                )
                if target:
                    out.add(target)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            imported = node.module
            if node.level and node.level > 0:
                imported = "." * node.level + imported
            base_target = _resolve_import_to_module(
                module_index=module_index,
                importer=importer_module,
                imported=imported,
            )
            for alias in node.names:
                if alias.name == "*":
                    continue
                if base_target:
                    candidate = f"{base_target}.{alias.name}"
                    if candidate in module_index:
                        out.add(candidate)
                        continue
                if base_target:
                    out.add(base_target)

    return out


def _config_file_like(rel_path: str) -> bool:
    low = rel_path.lower()
    base = low.split("/")[-1]
    if base in {
        "pyproject.toml",
        "setup.cfg",
        "tox.ini",
        "pytest.ini",
        "package.json",
        "tsconfig.json",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".env",
    }:
        return True
    if base.startswith("requirements") and base.endswith(".txt"):
        return True
    if base.endswith(".env"):
        return True
    return False


def _file_role(*, rel_path: str, entry_points: set[str]) -> str:
    low = rel_path.lower()
    if low.startswith("docs/") or low.endswith(".md"):
        return "docs"
    if rel_path in entry_points:
        return "entrypoint"
    if _config_file_like(rel_path):
        return "config"
    return "core"


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

    entry_points = set(architecture.get("entry_points") or [])
    module_index = _build_python_module_index(repo)
    module_text_by_module: dict[str, str] = {}
    for f in repo.iter_files():
        if f.extension != "py":
            continue
        mod = _python_module_name_for_relpath(f.rel_path)
        if not mod:
            continue
        try:
            module_text_by_module[mod] = f.path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

    incoming: dict[str, int] = defaultdict(int)
    for mod, text in module_text_by_module.items():
        if mod not in incoming:
            incoming[mod] += 0
        for dep in _python_import_edges(module_index=module_index, importer_module=mod, text=text):
            incoming[dep] += 1

    god_files = {x.get("file") for x in (risks.get("god_files") or []) if x.get("file")}
    large_files = {x.get("file") for x in (risks.get("large_files") or []) if x.get("file")}
    dead_code_files: set[str] = set()
    for fnd in risks.get("findings") or []:
        if fnd.get("analyzer") == "dead_code_unimported_modules":
            items = fnd.get("items") or []
            if isinstance(items, list):
                dead_code_files = set([x for x in items if isinstance(x, str)])

    candidates: list[dict] = []
    for f in repo.iter_files():
        role = _file_role(rel_path=f.rel_path, entry_points=entry_points)
        fan_in = 0
        if f.extension == "py":
            mod = _python_module_name_for_relpath(f.rel_path)
            if mod:
                fan_in = int(incoming.get(mod, 0))
        loc = f.lines or 0
        candidates.append(
            {
                "file": f.rel_path,
                "role": role,
                "fan_in": fan_in,
                "lines": loc,
                "size_bytes": f.size_bytes,
                "is_large": f.rel_path in large_files,
                "is_god": f.rel_path in god_files,
                "is_entrypoint": f.rel_path in entry_points,
                "is_dead": f.rel_path in dead_code_files,
            }
        )

    good_first: list[dict] = []
    avoid_first: list[dict] = []

    for c in candidates:
        r: list[str] = []
        if c["role"] == "docs":
            r.append("docs")
        if c["role"] == "config":
            r.append("config")
        if c["fan_in"] > 0:
            r.append(f"fan-in={c['fan_in']}")
        if c["lines"]:
            r.append(f"loc={c['lines']}")

        if c["is_god"] or c["is_large"] or c["is_entrypoint"]:
            rr: list[str] = []
            if c["is_entrypoint"]:
                rr.append("entrypoint")
            if c["is_god"]:
                rr.append("god file")
            if c["is_large"]:
                rr.append("large file")
            if c["is_dead"]:
                rr.append("possibly unused")
            avoid_first.append({"file": c["file"], "role": c["role"], "reasons": rr})
            continue

        score = 0
        if c["role"] in {"docs", "config"}:
            score += 5
        if 0 < c["lines"] <= 200:
            score += 4
        elif 200 < c["lines"] <= 500:
            score += 2
        elif c["lines"] > 500:
            score -= 3
        score += min(c["fan_in"], 10)

        good_first.append({"file": c["file"], "role": c["role"], "score": score, "signals": r})

    good_first.sort(key=lambda x: (x.get("score", 0), x.get("file", "")), reverse=True)
    avoid_first.sort(key=lambda x: (len(x.get("reasons") or []), x.get("file", "")), reverse=True)

    checklist = []
    checklist.append("Read `README.md` and any `docs/` overview")
    checklist.append("Find the entry point(s) and run the project or tests")
    checklist.append("Identify one small, high-signal file to read end-to-end")
    checklist.append("Pick a first change in docs/config/tests before core code")

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    inactivity_days_threshold = 180
    max_files_checked = 200

    single_author_files: list[dict] = []
    inactive_files: list[dict] = []
    ownership_available = True

    for f in list(repo.iter_files())[:max_files_checked]:
        low = f.rel_path.lower()
        if low.startswith(".git/"):
            continue
        if low.startswith(".reposcope/"):
            continue

        authors = git_file_authors(repo_root=repo.root, rel_path=f.rel_path)
        if authors is None:
            ownership_available = False
            break

        if authors and len(authors) == 1:
            single_author_files.append({"file": f.rel_path, "author": authors[0]})

        last_ts = git_file_last_commit_unix_ts(repo_root=repo.root, rel_path=f.rel_path)
        if last_ts is None:
            continue
        days = days_since_unix_ts(now_utc=now_utc, unix_ts=last_ts)
        if days >= inactivity_days_threshold:
            inactive_files.append({"file": f.rel_path, "days_since_change": days})

    single_author_files.sort(key=lambda x: x.get("file") or "")
    inactive_files.sort(key=lambda x: (x.get("days_since_change") or 0, x.get("file") or ""), reverse=True)

    out = {
        "start_here": start_here,
        "safe_to_modify": safe_to_modify,
        "risky_to_modify": risky_to_modify,
        "how_to_run": run_instructions,
        "entry_points": architecture.get("entry_points", []),
        "where_to_start": {
            "good_first_files": good_first[:15],
            "avoid_first_files": avoid_first[:15],
        },
        "first_hour_checklist": checklist,
    }

    if ownership_available:
        out["ownership"] = {
            "single_author_files": single_author_files[:25],
            "inactive_files": inactive_files[:25],
            "limits": "Uses `git log` per file. If git is unavailable or history cannot be read, this section is omitted.",
            "inactivity_days_threshold": inactivity_days_threshold,
        }

    return out
