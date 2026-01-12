from pathlib import Path

from reposcope.src.report.writer import write_reports
from reposcope.src.scanner.repo_scanner import scan_repo


def test_ai_flag_without_key_falls_back(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("REPOSCOPE_OPENAI_API_KEY", raising=False)

    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('x')\n", encoding="utf-8")

    repo = scan_repo(tmp_path)
    out_dir = tmp_path / ".reposcope"

    bundle = write_reports(repo=repo, output_dir=out_dir, use_ai=True)

    assert (out_dir / "ARCHITECTURE.md").exists()
    assert (out_dir / "RISKS.md").exists()
    assert (out_dir / "ONBOARDING.md").exists()
    assert (out_dir / "SUMMARY.md").exists()
    assert (out_dir / "SUMMARY.json").exists()

    assert "AI-assisted" not in bundle.risks_md
    assert "AI-assisted" not in bundle.architecture_md
