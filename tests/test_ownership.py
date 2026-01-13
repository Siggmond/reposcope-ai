from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from reposcope.src.analyzers.architecture import analyze_architecture
from reposcope.src.analyzers.onboarding import analyze_onboarding
from reposcope.src.analyzers.risks import analyze_risks
from reposcope.src.scanner.repo_scanner import scan_repo
from reposcope.src.utils.git_tools import git_available


@pytest.mark.skipif(not git_available(), reason="git not available")
def test_ownership_hints_single_author_and_inactivity(tmp_path: Path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def run(args: list[str], *, env: dict | None = None) -> None:
        subprocess.run(args, check=True, capture_output=True, text=True, cwd=repo_dir, env=env)

    run(["git", "init"])

    f1 = repo_dir / "a.py"
    f2 = repo_dir / "b.py"
    f1.write_text("print('a')\n", encoding="utf-8")
    f2.write_text("print('b')\n", encoding="utf-8")

    env1 = {
        "GIT_AUTHOR_NAME": "Alice",
        "GIT_AUTHOR_EMAIL": "alice@example.com",
        "GIT_COMMITTER_NAME": "Alice",
        "GIT_COMMITTER_EMAIL": "alice@example.com",
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+0000",
        "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+0000",
        **dict(os.environ),
    }

    run(["git", "add", "."], env=env1)
    run(["git", "commit", "-m", "add files"], env=env1)

    repo = scan_repo(repo_dir)
    risks = analyze_risks(repo)
    arch = analyze_architecture(repo)
    onboarding = analyze_onboarding(repo, risks=risks, architecture=arch)

    ownership = onboarding.get("ownership")
    assert ownership

    single = ownership.get("single_author_files") or []
    assert any(it.get("file") == "a.py" for it in single)
    assert any(it.get("file") == "b.py" for it in single)

    inactive = ownership.get("inactive_files") or []
    assert any(it.get("file") in {"a.py", "b.py"} for it in inactive)
