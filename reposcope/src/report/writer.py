from __future__ import annotations

import datetime
import importlib.metadata
import json
from dataclasses import dataclass
from pathlib import Path

from reposcope import __version__
from reposcope.src.ai.factory import get_ai_provider
from reposcope.src.analyzers.architecture import analyze_architecture
from reposcope.src.analyzers.onboarding import analyze_onboarding
from reposcope.src.analyzers.risks import analyze_risks
from reposcope.src.scanner.types import Repo
from reposcope.src.utils.git_tools import git_diff_names


@dataclass(frozen=True)
class ReportBundle:
    architecture_md: str
    risks_md: str
    onboarding_md: str
    summary: dict


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_reports(
    repo: Repo,
    output_dir: Path,
    use_ai: bool,
    *,
    aggressive: bool = False,
    diff_base: str | None = None,
) -> ReportBundle:
    output_dir.mkdir(parents=True, exist_ok=True)

    architecture = analyze_architecture(repo)
    risks = analyze_risks(repo, aggressive=aggressive)
    onboarding = analyze_onboarding(repo, risks=risks, architecture=architecture)

    pr_impact = None
    if diff_base:
        changed = git_diff_names(repo_root=repo.root, base=diff_base)
        pr_impact = _build_pr_impact(
            repo=repo,
            risks=risks,
            architecture=architecture,
            changed_files=changed,
            base=diff_base,
        )

    ai = get_ai_provider(use_ai=use_ai)
    ai_architecture = None
    ai_risks = {}

    if ai.enabled():
        try:
            ai_architecture = ai.explain_architecture(architecture=architecture)
        except Exception:
            ai_architecture = None

        try:
            ai_risks = _build_ai_risk_explanations(ai=ai, risks=risks)
        except Exception:
            ai_risks = {}

    architecture_md = _render_architecture(repo, architecture, ai_explanation=ai_architecture)
    risks_md = _render_risks(repo, risks, ai_explanations=ai_risks)
    onboarding_md = _render_onboarding(repo, onboarding)

    scan_date_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    repo_name = repo.root.name
    try:
        reposcope_version = importlib.metadata.version("reposcope-ai")
    except importlib.metadata.PackageNotFoundError:
        reposcope_version = __version__

    summary_md = _render_summary_md(
        repo_name=repo_name,
        scan_date_utc=scan_date_utc,
        reposcope_version=reposcope_version,
        risks=risks,
        pr_impact=pr_impact,
    )

    summary = {
        "repo_name": repo_name,
        "scan_date_utc": scan_date_utc,
        "reposcope_version": reposcope_version,
        "repo_root": str(repo.root),
        "file_count": len(repo.files),
        "architecture": architecture,
        "risks": {
            **risks,
            "large_files": [x["file"] for x in risks.get("large_files", [])],
            "god_files": [x["file"] for x in risks.get("god_files", [])],
        },
        "onboarding": onboarding,
        "pr_impact": pr_impact,
    }

    _write_text(output_dir / "ARCHITECTURE.md", architecture_md)
    _write_text(output_dir / "RISKS.md", risks_md)
    _write_text(output_dir / "ONBOARDING.md", onboarding_md)
    _write_text(output_dir / "SUMMARY.md", summary_md)
    (output_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return ReportBundle(
        architecture_md=architecture_md,
        risks_md=risks_md,
        onboarding_md=onboarding_md,
        summary=summary,
    )


def _render_architecture(repo: Repo, architecture: dict, ai_explanation: str | None) -> str:
    lines: list[str] = []
    lines.append("# Architecture")
    lines.append("")
    lines.append(f"Repo root: `{repo.root}`")
    lines.append("")

    lines.append("## Main folders")
    lines.append("")
    for f in architecture.get("main_folders", []):
        lines.append(f"- **{f['name']}**: {f['file_count']} files")
    lines.append("")

    lines.append("## Entry points (best-effort)")
    lines.append("")
    for ep in architecture.get("entry_points", []):
        lines.append(f"- `{ep}`")
    lines.append("")

    lines.append("## High-level data flow (best-effort)")
    lines.append("")
    lines.append("- **[input]** CLI / entrypoint")
    lines.append("- **[core]** primary modules under main folders")
    lines.append("- **[output]** files, APIs, DB, or stdout depending on the project")
    lines.append("")

    if ai_explanation:
        lines.append("## AI-assisted explanation")
        lines.append("")
        lines.append(ai_explanation)
        lines.append("")

    return "\n".join(lines)


def _render_risks(repo: Repo, risks: dict, ai_explanations: dict[str, dict]) -> str:
    lines: list[str] = []
    lines.append("# Risks & Smells")
    lines.append("")
    lines.append(f"Repo root: `{repo.root}`")
    lines.append("")

    lines.append("## Analyzer findings")
    lines.append("")
    if not risks.get("findings"):
        lines.append("- **[none detected]**")
    else:
        for finding in risks.get("findings") or []:
            label = finding.get("label") or ""
            title = finding.get("title") or "(untitled)"
            lines.append(f"- **{label}** {title}")
            if finding.get("message"):
                lines.append(f"  - {finding['message']}")
            items = finding.get("items")
            if isinstance(items, list) and items:
                for it in items[:20]:
                    if isinstance(it, str):
                        lines.append(f"  - `{it}`")
                    else:
                        lines.append(f"  - `{it}`")
            if finding.get("limits"):
                lines.append(f"  - **limits** {finding['limits']}")
    lines.append("")

    lines.append("## Large files")
    lines.append("")
    if not risks.get("large_files"):
        lines.append("- **[none detected]**")
    else:
        for item in risks["large_files"]:
            lines.append(f"- **[deterministic]** `{item['file']}` ({item['lines']} lines)")
            ai_item = ai_explanations.get(item["file"])
            if ai_item:
                lines.append(f"  - **[AI-assisted explanation]** {ai_item['rationale']}")

    lines.append("")

    lines.append("## God files (very high line count)")
    lines.append("")
    if not risks.get("god_files"):
        lines.append("- **[none detected]**")
    else:
        for item in risks["god_files"]:
            lines.append(f"- **[deterministic]** `{item['file']}` ({item['lines']} lines)")
            ai_item = ai_explanations.get(item["file"])
            if ai_item:
                lines.append(f"  - **[AI-assisted explanation]** {ai_item['rationale']}")

    lines.append("")

    lines.append("## Circular imports (best-effort, Python only)")
    lines.append("")
    if not risks.get("circular_imports"):
        lines.append("- **[none detected]**")
    else:
        for cycle in risks["circular_imports"]:
            lines.append(f"- **[deterministic]** `{ ' -> '.join(cycle) }`")

    if risks.get("heuristic_circular_imports"):
        lines.append("")
        lines.append("## Circular imports (heuristic)")
        lines.append("")
        for cycle in risks.get("heuristic_circular_imports") or []:
            lines.append(f"- **[heuristic]** `{ ' -> '.join(cycle) }`")

    lines.append("")

    lines.append("## Tests")
    lines.append("")
    if risks.get("missing_tests"):
        lines.append("- **[deterministic]** No obvious tests directory/config detected (`tests/`, `pytest.ini`).")
        ai_item = ai_explanations.get("tests")
        if ai_item:
            lines.append(f"  - **[AI-assisted explanation]** {ai_item['rationale']}")
    else:
        lines.append("- **[ok]** Tests directory/config detected.")
    lines.append("")

    return "\n".join(lines)


def _render_onboarding(repo: Repo, onboarding: dict) -> str:
    lines: list[str] = []
    lines.append("# Onboarding")
    lines.append("")
    lines.append(f"Repo root: `{repo.root}`")
    lines.append("")

    lines.append("## First-hour checklist")
    lines.append("")
    if not onboarding.get("first_hour_checklist"):
        lines.append("- **[unknown]**")
    else:
        for item in onboarding.get("first_hour_checklist") or []:
            lines.append(f"- {item}")
    lines.append("")

    lines.append("## Where to start (deterministic)")
    lines.append("")
    wts = onboarding.get("where_to_start") or {}
    good = wts.get("good_first_files") or []
    avoid = wts.get("avoid_first_files") or []

    lines.append("### Good first files")
    lines.append("")
    if not good:
        lines.append("- **[none detected]**")
    else:
        for it in good:
            fp = it.get("file")
            role = it.get("role")
            signals = it.get("signals") or []
            if fp:
                if signals:
                    lines.append(f"- `{fp}` ({role}) — {', '.join(signals)}")
                else:
                    lines.append(f"- `{fp}` ({role})")
    lines.append("")

    lines.append("### Risky files to avoid first")
    lines.append("")
    if not avoid:
        lines.append("- **[none detected]**")
    else:
        for it in avoid:
            fp = it.get("file")
            reasons = it.get("reasons") or []
            if fp:
                if reasons:
                    lines.append(f"- `{fp}` — {', '.join(reasons)}")
                else:
                    lines.append(f"- `{fp}`")
    lines.append("")

    ownership = onboarding.get("ownership")
    if ownership:
        lines.append("## Ownership & bus-factor hints (deterministic)")
        lines.append("")
        limits = ownership.get("limits")
        if limits:
            lines.append(f"- **limits** {limits}")

        single = ownership.get("single_author_files") or []
        inactive = ownership.get("inactive_files") or []
        threshold = ownership.get("inactivity_days_threshold")

        lines.append("")
        lines.append("### Single-author files")
        lines.append("")
        if not single:
            lines.append("- **[none detected]**")
        else:
            for it in single[:20]:
                fp = it.get("file")
                author = it.get("author")
                if fp and author:
                    lines.append(f"- `{fp}` — {author}")
                elif fp:
                    lines.append(f"- `{fp}`")

        lines.append("")
        lines.append(f"### Long-inactive files (≥ {threshold} days)")
        lines.append("")
        if not inactive:
            lines.append("- **[none detected]**")
        else:
            for it in inactive[:20]:
                fp = it.get("file")
                days = it.get("days_since_change")
                if fp and days is not None:
                    lines.append(f"- `{fp}` — {days} days since last change")
                elif fp:
                    lines.append(f"- `{fp}`")

        lines.append("")

    lines.append("## Start here")
    lines.append("")
    if not onboarding.get("start_here"):
        lines.append("- **[no obvious docs found]**")
    else:
        for p in onboarding["start_here"]:
            lines.append(f"- `{p}`")
    lines.append("")

    lines.append("## How to run (best guess)")
    lines.append("")
    if not onboarding.get("how_to_run"):
        lines.append("- **[unknown]** RepoScope couldn't infer run instructions.")
    else:
        for cmd in onboarding["how_to_run"]:
            lines.append(f"- `{cmd}`")
    lines.append("")

    lines.append("## Safe-ish files to modify")
    lines.append("")
    if not onboarding.get("safe_to_modify"):
        lines.append("- **[unknown]**")
    else:
        for p in onboarding["safe_to_modify"]:
            lines.append(f"- `{p}`")
    lines.append("")

    lines.append("## Risky files to touch first")
    lines.append("")
    if not onboarding.get("risky_to_modify"):
        lines.append("- **[none detected]**")
    else:
        for p in onboarding["risky_to_modify"]:
            lines.append(f"- `{p}`")
    lines.append("")

    lines.append("## Entry points")
    lines.append("")
    if not onboarding.get("entry_points"):
        lines.append("- **[unknown]**")
    else:
        for ep in onboarding["entry_points"]:
            lines.append(f"- `{ep}`")
    lines.append("")

    return "\n".join(lines)


def _render_summary_md(
    *,
    repo_name: str,
    scan_date_utc: str,
    reposcope_version: str,
    risks: dict,
    pr_impact: dict | None,
) -> str:
    lines: list[str] = []
    lines.append("# RepoScope Summary")
    lines.append("")
    lines.append(f"Repo: `{repo_name}`")
    lines.append("")
    lines.append(f"Scan date (UTC): `{scan_date_utc}`")
    lines.append("")
    lines.append(f"RepoScope version: `{reposcope_version}`")
    lines.append("")
    lines.append("Generated by RepoScope (deterministic analysis + optional AI explanations).")
    lines.append("")

    if pr_impact:
        lines.append("## PR impact (deterministic)")
        lines.append("")
        base = pr_impact.get("base")
        changed = pr_impact.get("changed_files") or []
        lines.append(f"Base: `{base}`")
        lines.append("")
        if not changed:
            lines.append("- **[none detected]**")
        else:
            touched = pr_impact.get("touched") or {}
            for key in ["entrypoints", "god_files", "large_files", "dead_code"]:
                items = touched.get(key) or []
                if items:
                    lines.append(f"- **[{key}]** {len(items)} file(s)")
                    for fp in items[:10]:
                        lines.append(f"  - `{fp}`")
        lines.append("")

    lines.append("## Top findings")
    lines.append("")
    findings = _top_findings_for_summary_md(risks)
    if not findings:
        lines.append("- **[none detected]**")
    else:
        for f in findings:
            lines.append(f"- {f}")
    lines.append("")

    return "\n".join(lines)


def _top_findings_for_summary_md(risks: dict) -> list[str]:
    out: list[str] = []

    for item in (risks.get("god_files") or [])[:3]:
        file_path = item.get("file")
        lines = item.get("lines")
        if file_path is not None and lines is not None:
            out.append(f"**[god file]** `{file_path}` ({lines} lines)")

    for item in (risks.get("large_files") or [])[:3]:
        file_path = item.get("file")
        lines = item.get("lines")
        if file_path is not None and lines is not None:
            out.append(f"**[large file]** `{file_path}` ({lines} lines)")

    if risks.get("missing_tests"):
        out.append("**[missing tests]** No obvious tests directory/config detected")

    for cycle in (risks.get("circular_imports") or [])[:2]:
        if isinstance(cycle, list) and cycle:
            out.append(f"**[circular imports]** `{ ' -> '.join(cycle) }`")

    return out[:6]


def _build_pr_impact(
    *,
    repo: Repo,
    risks: dict,
    architecture: dict,
    changed_files: list[str] | None,
    base: str,
) -> dict:
    changed = sorted(set(changed_files or []))
    large = {x.get("file") for x in (risks.get("large_files") or []) if x.get("file")}
    god = {x.get("file") for x in (risks.get("god_files") or []) if x.get("file")}
    entrypoints = set(architecture.get("entry_points") or [])
    dead = set()
    for fnd in risks.get("findings") or []:
        if fnd.get("analyzer") == "dead_code_unimported_modules":
            items = fnd.get("items") or []
            if isinstance(items, list):
                dead = set([x for x in items if isinstance(x, str)])

    touched = {
        "large_files": sorted([f for f in changed if f in large]),
        "god_files": sorted([f for f in changed if f in god]),
        "entrypoints": sorted([f for f in changed if f in entrypoints]),
        "dead_code": sorted([f for f in changed if f in dead]),
    }

    return {
        "base": base,
        "changed_files": changed,
        "touched": touched,
        "limits": "Uses `git diff --name-only <base>` and intersects with deterministic RepoScope signals. Does not infer runtime behavior.",
    }


def _build_ai_risk_explanations(*, ai, risks: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}

    for item in risks.get("large_files", [])[:10]:
        path = item.get("file")
        if not path:
            continue
        reason = f"File has {item.get('lines')} lines (threshold: 500 lines)."
        insight = ai.explain_risk(file_path=path, reason=reason, excerpt=None)
        if insight:
            out[path] = {"title": insight.title, "rationale": insight.rationale}

    for item in risks.get("god_files", [])[:10]:
        path = item.get("file")
        if not path:
            continue
        reason = f"File has {item.get('lines')} lines (threshold: 800 lines)."
        insight = ai.explain_risk(file_path=path, reason=reason, excerpt=None)
        if insight:
            out[path] = {"title": insight.title, "rationale": insight.rationale}

    if risks.get("missing_tests"):
        path = "tests"
        reason = "No obvious tests directory/config detected (tests/, pytest.ini)."
        insight = ai.explain_risk(file_path=path, reason=reason, excerpt=None)
        if insight:
            out[path] = {"title": insight.title, "rationale": insight.rationale}

    return out
