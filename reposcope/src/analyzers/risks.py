from __future__ import annotations

import re
from collections import defaultdict

from reposcope.src.scanner.types import Repo


_IMPORT_RE = re.compile(r"^\s*(from\s+([\w\.]+)\s+import|import\s+([\w\.]+))")


def _python_imports(text: str) -> set[str]:
    imports: set[str] = set()
    for line in text.splitlines()[:5000]:
        m = _IMPORT_RE.match(line)
        if not m:
            continue
        mod = m.group(2) or m.group(3)
        if mod:
            imports.add(mod.split(".")[0])
    return imports


def analyze_risks(repo: Repo) -> dict:
    large_files = []
    god_files = []

    py_modules: dict[str, str] = {}
    for f in repo.iter_files():
        if f.lines is not None and f.lines >= 800:
            god_files.append({"file": f.rel_path, "lines": f.lines})
        if f.size_bytes >= 300_000:
            large_files.append({"file": f.rel_path, "size_bytes": f.size_bytes})

        if f.extension == "py":
            try:
                py_modules[f.rel_path] = f.path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass

    # best-effort circular imports: only considers top-level module names within repo
    local_py_toplevel = {p.split("/")[0] for p in py_modules.keys()}
    graph: dict[str, set[str]] = defaultdict(set)

    for rel, text in py_modules.items():
        src_top = rel.split("/")[0]
        for imp in _python_imports(text):
            if imp in local_py_toplevel:
                graph[src_top].add(imp)

    cycles = []

    def dfs(start: str, node: str, path: list[str], visiting: set[str]):
        visiting.add(node)
        path.append(node)
        for nxt in graph.get(node, set()):
            if nxt == start and len(path) > 1:
                cycles.append(path[:] + [start])
            if nxt in visiting:
                continue
            dfs(start, nxt, path, visiting)
        path.pop()
        visiting.remove(node)

    for n in sorted(graph.keys()):
        dfs(n, n, [], set())

    # missing tests heuristic
    has_tests_dir = any(f.rel_path.lower().startswith("tests/") for f in repo.iter_files())
    has_pytest = any(f.rel_path.lower().endswith("pytest.ini") for f in repo.iter_files())
    missing_tests = not (has_tests_dir or has_pytest)

    return {
        "large_files": sorted(large_files, key=lambda x: x["size_bytes"], reverse=True)[:20],
        "god_files": sorted(god_files, key=lambda x: x["lines"], reverse=True)[:20],
        "circular_imports": cycles[:10],
        "missing_tests": missing_tests,
    }
