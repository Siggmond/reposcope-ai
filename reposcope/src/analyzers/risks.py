from __future__ import annotations

import ast
import io
import re
import tokenize
from collections import defaultdict

from reposcope.src.scanner.types import Repo


_IMPORT_RE = re.compile(r"^\s*(from\s+([\w\.]+)\s+import|import\s+([\w\.]+))")


_SOURCE_EXTENSIONS = {"py", "ts", "tsx", "js", "jsx", "java", "go", "rs", "kt", "swift", "cs"}


_ENTRYPOINT_CANDIDATE_RELS = {
    "manage.py",
    "setup.py",
    "pyproject.toml",
    "package.json",
}


_ENTRYPOINT_CANDIDATE_SUFFIXES = (
    "main.py",
    "app.py",
    "index.js",
    "index.ts",
)


_CONFIG_FILE_NAMES = {
    "pyproject.toml",
    "setup.cfg",
    "tox.ini",
    "pytest.ini",
    "package.json",
    "tsconfig.json",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".env",
}


_CONFIG_DOCS = {
    "configuration.md",
    "config.md",
    "docs/configuration.md",
    "docs/config.md",
}


def _count_loc(*, text: str, extension: str) -> int:
    loc = 0
    in_block_comment = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        if in_block_comment:
            end = line.find("*/")
            if end == -1:
                continue
            in_block_comment = False
            line = line[end + 2 :].strip()
            if not line:
                continue

        if extension == "py":
            if line.startswith("#"):
                continue
            loc += 1
            continue

        if line.startswith("//"):
            continue

        start = line.find("/*")
        if start != -1:
            before = line[:start].strip()
            after = line[start + 2 :]
            end = after.find("*/")
            if end != -1:
                after_tail = after[end + 2 :].strip()
                if before or after_tail:
                    loc += 1
                continue
            if before:
                loc += 1
            in_block_comment = True
            continue

        loc += 1

    return loc


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


def _detect_cycles_resolvable_only(graph: dict[str, set[str]]) -> list[list[str]]:
    cycles: set[tuple[str, ...]] = set()

    def norm_cycle(path: list[str]) -> tuple[str, ...]:
        if not path:
            return tuple()
        if path[0] == path[-1]:
            path = path[:-1]
        n = len(path)
        if n == 0:
            return tuple()
        rotations = [tuple(path[i:] + path[:i]) for i in range(n)]
        best = min(rotations)
        return best

    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str, stack: list[str], stack_set: set[str]) -> None:
        visited.add(node)
        visiting.add(node)
        stack.append(node)
        stack_set.add(node)

        for nxt in sorted(graph.get(node, set())):
            if nxt in stack_set:
                idx = stack.index(nxt)
                cyc = stack[idx:] + [nxt]
                cycles.add(norm_cycle(cyc))
                continue
            if nxt not in visited:
                dfs(nxt, stack, stack_set)

        stack.pop()
        stack_set.remove(node)
        visiting.remove(node)

    for n in sorted(graph.keys()):
        if n not in visited:
            dfs(n, [], set())

    out = []
    for cyc in sorted(cycles):
        out.append(list(cyc) + [cyc[0]])
    return out


def _count_python_defs(text: str) -> tuple[int, int]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return (0, 0)

    functions = 0
    classes = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions += 1
        elif isinstance(node, ast.ClassDef):
            classes += 1
    return (functions, classes)


def _entry_point_candidates(repo: Repo) -> list[str]:
    out: set[str] = set()
    for f in repo.iter_files():
        low = f.rel_path.lower()
        if low.endswith(_ENTRYPOINT_CANDIDATE_SUFFIXES):
            out.add(f.rel_path)
        if low in _ENTRYPOINT_CANDIDATE_RELS:
            out.add(f.rel_path)
    return sorted(out)


def _config_files(repo: Repo) -> list[str]:
    out: list[str] = []
    for f in repo.iter_files():
        low = f.rel_path.lower()
        base = low.split("/")[-1]
        if base in _CONFIG_FILE_NAMES:
            out.append(f.rel_path)
        if base.startswith("requirements") and base.endswith(".txt"):
            out.append(f.rel_path)
    return sorted(set(out))


def _has_config_docs(repo: Repo) -> bool:
    rels = {f.rel_path.lower() for f in repo.iter_files()}
    return any(doc in rels for doc in _CONFIG_DOCS)


def _env_keys_without_comments(text: str) -> list[str]:
    keys: list[str] = []
    prev_nonempty = ""
    for raw in text.splitlines()[:5000]:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            prev_nonempty = line
            continue
        if "=" not in line or line.startswith("export "):
            prev_nonempty = line
            continue
        k = line.split("=", 1)[0].strip()
        if not k or " " in k:
            prev_nonempty = line
            continue
        if not prev_nonempty.startswith("#"):
            keys.append(k)
        prev_nonempty = line
    return keys


def _magic_numbers_python(text: str) -> list[str]:
    out: list[str] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
    except tokenize.TokenError:
        return out
    for tok_type, tok_str, _, _, _ in tokens:
        if tok_type != tokenize.NUMBER:
            continue
        if tok_str in {"0", "1", "-1"}:
            continue
        out.append(tok_str)
        if len(out) >= 25:
            break
    return out


def _risky_shell_patterns(text: str) -> list[str]:
    patterns = [
        r"\bos\.system\s*\(",
        r"\bsubprocess\.(run|call|Popen)\s*\(",
        r"\bshell\s*=\s*True\b",
        r"\brm\s+-rf\b",
        r"\bcurl\b.*\|\s*sh\b",
    ]
    hits: list[str] = []
    for pat in patterns:
        if re.search(pat, text):
            hits.append(pat)
    return hits


def analyze_risks(repo: Repo, *, aggressive: bool = False) -> dict:
    large_files = []
    god_files = []

    findings: list[dict] = []

    large_file_loc_threshold = 500
    god_file_loc_threshold = 800

    py_modules: dict[str, str] = {}
    for f in repo.iter_files():
        loc = None
        if f.extension in _SOURCE_EXTENSIONS:
            try:
                text = f.path.read_text(encoding="utf-8", errors="ignore")
                loc = _count_loc(text=text, extension=f.extension)
                if loc > large_file_loc_threshold:
                    large_files.append({"kind": "large file", "file": f.rel_path, "lines": loc})
                if loc >= god_file_loc_threshold:
                    god_files.append({"file": f.rel_path, "lines": loc})
            except OSError:
                loc = None

        if f.extension == "py":
            try:
                py_modules[f.rel_path] = f.path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass

    module_index = _build_python_module_index(repo)
    module_text_by_module: dict[str, str] = {}
    for rel, text in py_modules.items():
        mod = _python_module_name_for_relpath(rel)
        if mod:
            module_text_by_module[mod] = text

    import_graph: dict[str, set[str]] = defaultdict(set)
    for mod, text in module_text_by_module.items():
        for dep in _python_import_edges(module_index=module_index, importer_module=mod, text=text):
            import_graph[mod].add(dep)

    resolvable_cycles = _detect_cycles_resolvable_only(import_graph)

    if resolvable_cycles:
        findings.append(
            {
                "label": "[deterministic]",
                "analyzer": "circular_imports_python_resolvable",
                "title": "Circular imports (Python, resolvable-only)",
                "items": resolvable_cycles[:10],
                "limits": "Static AST parsing only. Flags cycles only when all involved modules resolve to files within this repo. Ignores dynamic imports.",
            }
        )

    god_function_threshold = 30
    god_class_threshold = 10
    god_by_defs: list[dict] = []
    for mod, text in module_text_by_module.items():
        funcs, classes = _count_python_defs(text)
        if funcs > god_function_threshold or classes > god_class_threshold:
            rel = module_index.get(mod)
            if rel:
                god_by_defs.append(
                    {
                        "file": rel,
                        "functions": funcs,
                        "classes": classes,
                        "function_threshold": god_function_threshold,
                        "class_threshold": god_class_threshold,
                    }
                )
    if god_by_defs:
        god_by_defs.sort(key=lambda x: (x["functions"], x["classes"]), reverse=True)
        findings.append(
            {
                "label": "[deterministic]",
                "analyzer": "god_module_python_defs",
                "title": "God module indicators (Python defs/classes)",
                "items": god_by_defs[:20],
                "limits": "Counts only top-level `def`/`class` via AST. Does not measure complexity or runtime behavior.",
            }
        )

    eps = _entry_point_candidates(repo)
    if len(eps) == 0:
        findings.append(
            {
                "label": "[deterministic]",
                "analyzer": "entry_point_none",
                "title": "Entry point ambiguity",
                "items": [],
                "message": "No obvious entry point detected (based on filename patterns).",
                "limits": "Looks only for common filenames (e.g. main.py/app.py/index.ts) and a few root build files. Does not inspect code to infer runtime entrypoints.",
            }
        )
    elif len(eps) > 1:
        findings.append(
            {
                "label": "[deterministic]",
                "analyzer": "entry_point_multiple",
                "title": "Entry point ambiguity",
                "items": eps[:20],
                "message": "Multiple possible entry points detected (based on filename patterns).",
                "limits": "Looks only for common filenames (e.g. main.py/app.py/index.ts) and a few root build files. Does not inspect code to infer runtime entrypoints.",
            }
        )

    config_files = _config_files(repo)
    if len(config_files) >= 4 and not _has_config_docs(repo):
        findings.append(
            {
                "label": "[deterministic]",
                "analyzer": "config_sprawl_missing_docs",
                "title": "Config sprawl",
                "items": config_files[:30],
                "message": "Multiple config files found, but no obvious configuration documentation file detected.",
                "limits": "Config files are detected by filename only. Docs are detected only by presence of CONFIG/Configuration markdown files.",
            }
        )

    for f in repo.iter_files():
        if f.rel_path.lower().endswith("/.env") or f.rel_path.lower() == ".env":
            try:
                env_text = f.path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            keys = _env_keys_without_comments(env_text)
            if keys:
                findings.append(
                    {
                        "label": "[deterministic]",
                        "analyzer": "config_env_keys_without_comments",
                        "title": "Config keys without comments (.env)",
                        "items": [{"file": f.rel_path, "keys": keys[:50]}],
                        "limits": "Only checks `.env` files. A key is treated as documented only when immediately preceded by a comment line.",
                    }
                )

    incoming: dict[str, int] = defaultdict(int)
    for src, deps in import_graph.items():
        for dep in deps:
            incoming[dep] += 1
        if src not in incoming:
            incoming[src] += 0

    entrypoint_modules: set[str] = set()
    for ep in eps:
        if ep.endswith(".py"):
            mod = _python_module_name_for_relpath(ep)
            if mod:
                entrypoint_modules.add(mod)

    dead_modules: list[str] = []
    for mod in sorted(module_text_by_module.keys()):
        rel = module_index.get(mod)
        if not rel:
            continue
        low = rel.lower()
        if low.startswith("tests/"):
            continue
        if low.endswith("/__init__.py"):
            continue
        if mod in entrypoint_modules:
            continue
        if incoming.get(mod, 0) == 0:
            dead_modules.append(rel)

    if dead_modules:
        findings.append(
            {
                "label": "[deterministic]",
                "analyzer": "dead_code_unimported_modules",
                "title": "Dead code (very conservative)",
                "items": dead_modules[:50],
                "message": "Python files that are never imported by any other Python file (based on resolvable static imports).",
                "limits": "Ignores dynamic imports, CLI entrypoints outside known patterns, and non-Python entry mechanisms.",
            }
        )

    heuristic_cycles: list[list[str]] = []
    if aggressive:
        local_py_toplevel = {p.split("/")[0] for p in py_modules.keys()}
        graph_top: dict[str, set[str]] = defaultdict(set)
        for rel, text in py_modules.items():
            src_top = rel.split("/")[0]
            for imp in _python_imports(text):
                if imp in local_py_toplevel:
                    graph_top[src_top].add(imp)

        heuristic_cycles = _detect_cycles_resolvable_only(graph_top)
        if heuristic_cycles:
            findings.append(
                {
                    "label": "[heuristic]",
                    "analyzer": "circular_imports_python_toplevel",
                    "title": "Circular imports (Python, top-level packages)",
                    "items": heuristic_cycles[:10],
                    "limits": "Uses only top-level folder names as module identifiers. This may over/under-report in multi-package repos.",
                }
            )

        magic_files: list[dict] = []
        for mod, text in module_text_by_module.items():
            rel = module_index.get(mod)
            if not rel:
                continue
            nums = _magic_numbers_python(text)
            if len(nums) >= 10:
                magic_files.append({"file": rel, "examples": nums[:10], "count": len(nums)})
        if magic_files:
            magic_files.sort(key=lambda x: x["count"], reverse=True)
            findings.append(
                {
                    "label": "[heuristic]",
                    "analyzer": "magic_numbers_python",
                    "title": "Magic numbers (Python)",
                    "items": magic_files[:20],
                    "limits": "Counts numeric literals via tokenization and excludes only 0/1/-1. Does not understand domain constants or configuration patterns.",
                }
            )

        shell_hits: list[dict] = []
        for f in repo.iter_files():
            if f.extension not in {"py", "sh", "ps1", "js", "ts"}:
                continue
            try:
                text = f.path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            pats = _risky_shell_patterns(text)
            if pats:
                shell_hits.append({"file": f.rel_path, "patterns": pats})
        if shell_hits:
            findings.append(
                {
                    "label": "[heuristic]",
                    "analyzer": "risky_shell_commands",
                    "title": "Risky shell command patterns",
                    "items": shell_hits[:30],
                    "limits": "Pattern-based matching only. Does not infer actual runtime execution or input sanitization.",
                }
            )

    has_tests_dir = any(f.rel_path.lower().startswith("tests/") for f in repo.iter_files())
    has_pytest = any(f.rel_path.lower().endswith("pytest.ini") for f in repo.iter_files())
    missing_tests = not (has_tests_dir or has_pytest)

    return {
        "large_files": sorted(large_files, key=lambda x: x["lines"], reverse=True)[:20],
        "god_files": sorted(god_files, key=lambda x: x["lines"], reverse=True)[:20],
        "circular_imports": resolvable_cycles[:10],
        "heuristic_circular_imports": heuristic_cycles[:10],
        "missing_tests": missing_tests,
        "findings": findings,
    }
