from pathlib import Path

from reposcope.src.scanner.repo_scanner import scan_repo


def test_scan_repo_smoke(tmp_path: Path):
    (tmp_path / "a.py").write_text("print('x')\n", encoding="utf-8")
    repo = scan_repo(tmp_path)
    assert repo.root == tmp_path.resolve()
    assert len(repo.files) == 1
