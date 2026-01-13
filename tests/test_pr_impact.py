from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from reposcope.src.report.writer import write_reports
from reposcope.src.utils.git_tools import git_available
from reposcope.src.scanner.repo_scanner import scan_repo


@pytest.mark.skipif(not git_available(), reason="git not available")
def test_pr_impact_detects_touched_large_file(tmp_path: Path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def run(args: list[str]) -> None:
        subprocess.run(args, check=True, capture_output=True, text=True, cwd=repo_dir)

    run(["git", "init"])
    run(["git", "config", "user.email", "test@example.com"])
    run(["git", "config", "user.name", "Test User"])

    (repo_dir / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (repo_dir / "big.py").write_text(("x = 1\n" * 900), encoding="utf-8")

    run(["git", "add", "."])
    run(["git", "commit", "-m", "base"])

    (repo_dir / "big.py").write_text(("x = 1\n" * 901), encoding="utf-8")
    (repo_dir / "main.py").write_text("print('changed')\n", encoding="utf-8")

    repo = scan_repo(repo_dir)
    out_dir = repo_dir / ".reposcope"

    write_reports(repo=repo, output_dir=out_dir, use_ai=False, diff_base="HEAD")

    summary = json.loads((out_dir / "SUMMARY.json").read_text(encoding="utf-8"))
    pr = summary.get("pr_impact")
    assert pr
    assert pr.get("base") == "HEAD"

    touched = (pr.get("touched") or {})
    assert "big.py" in (touched.get("large_files") or [])
    assert "main.py" in (touched.get("entrypoints") or [])
