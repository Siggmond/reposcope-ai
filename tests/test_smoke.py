from pathlib import Path

from reposcope.src.analyzers import risks as risks_mod
from reposcope.src.analyzers.architecture import analyze_architecture
from reposcope.src.analyzers.onboarding import analyze_onboarding
from reposcope.src.scanner.repo_scanner import scan_repo


def test_scan_repo_smoke(tmp_path: Path):
    (tmp_path / "a.py").write_text("print('x')\n", encoding="utf-8")
    repo = scan_repo(tmp_path)
    assert repo.root == tmp_path.resolve()
    assert len(repo.files) == 1


def test_large_file_detection_triggers_on_loc_threshold(tmp_path: Path):
    # Build a file with >500 lines of non-comment code.
    content = ("x = 1" + "\n") * 501
    (tmp_path / "big.py").write_text(content, encoding="utf-8")

    repo = scan_repo(tmp_path)
    risks = risks_mod.analyze_risks(repo)

    large = risks.get("large_files") or []
    assert any(
        item.get("file") == "big.py" and (item.get("lines") or 0) > 500 and item.get("kind") == "large file"
        for item in large
    ), large


def test_large_file_detection_none_detected_on_small_repo(tmp_path: Path):
    (tmp_path / "small.py").write_text("# comment\n\nprint('x')\n", encoding="utf-8")

    repo = scan_repo(tmp_path)
    risks = risks_mod.analyze_risks(repo)

    assert (risks.get("large_files") or []) == []


def test_circular_import_detection_resolvable_only_python(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("\n", encoding="utf-8")
    (tmp_path / "pkg" / "a.py").write_text("from pkg import b\n", encoding="utf-8")
    (tmp_path / "pkg" / "b.py").write_text("from pkg import a\n", encoding="utf-8")

    repo = scan_repo(tmp_path)
    risks = risks_mod.analyze_risks(repo)

    cycles = risks.get("circular_imports") or []
    assert cycles, risks
    assert any("pkg.a" in cycle and "pkg.b" in cycle for cycle in cycles), cycles


def test_god_module_thresholds_by_defs(tmp_path: Path):
    defs = "\n".join([f"def f{i}():\n    return {i}\n" for i in range(31)])
    (tmp_path / "bigmod.py").write_text(defs + "\n", encoding="utf-8")

    repo = scan_repo(tmp_path)
    risks = risks_mod.analyze_risks(repo)

    findings = risks.get("findings") or []
    hit = [f for f in findings if f.get("analyzer") == "god_module_python_defs"]
    assert hit, findings
    assert any((it.get("file") == "bigmod.py" and it.get("functions", 0) >= 31) for it in (hit[0].get("items") or []))


def test_entry_point_ambiguity_none_detected(tmp_path: Path):
    (tmp_path / "lib.py").write_text("print('x')\n", encoding="utf-8")

    repo = scan_repo(tmp_path)
    risks = risks_mod.analyze_risks(repo)

    findings = risks.get("findings") or []
    assert any(f.get("analyzer") == "entry_point_none" for f in findings), findings


def test_entry_point_ambiguity_multiple_detected(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('x')\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("print('y')\n", encoding="utf-8")

    repo = scan_repo(tmp_path)
    risks = risks_mod.analyze_risks(repo)

    findings = risks.get("findings") or []
    assert any(f.get("analyzer") == "entry_point_multiple" for f in findings), findings


def test_config_sprawl_and_env_key_docs(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "tox.ini").write_text("[tox]\n", encoding="utf-8")
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (tmp_path / ".env").write_text("API_KEY=abc\n# documented\nPORT=8000\n", encoding="utf-8")

    repo = scan_repo(tmp_path)
    risks = risks_mod.analyze_risks(repo)

    findings = risks.get("findings") or []
    assert any(f.get("analyzer") == "config_sprawl_missing_docs" for f in findings), findings
    env_findings = [f for f in findings if f.get("analyzer") == "config_env_keys_without_comments"]
    assert env_findings, findings
    env_items = env_findings[0].get("items") or []
    assert any(item.get("file") == ".env" and "API_KEY" in (item.get("keys") or []) for item in env_items), env_items


def test_dead_code_conservative_unimported_module(tmp_path: Path):
    (tmp_path / "main.py").write_text("from used import x\nprint(x)\n", encoding="utf-8")
    (tmp_path / "used.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "dead.py").write_text("y = 2\n", encoding="utf-8")

    repo = scan_repo(tmp_path)
    risks = risks_mod.analyze_risks(repo)

    findings = risks.get("findings") or []
    dead = [f for f in findings if f.get("analyzer") == "dead_code_unimported_modules"]
    assert dead, findings
    assert "dead" in "\n".join(dead[0].get("items") or []), dead


def test_aggressive_gates_heuristics(tmp_path: Path):
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "__init__.py").write_text("\n", encoding="utf-8")
    (tmp_path / "p" / "a.py").write_text("import os\nos.system('rm -rf /')\n" + "\n".join([f"x{i}={i+2}" for i in range(20)]) + "\n", encoding="utf-8")

    repo = scan_repo(tmp_path)
    base = risks_mod.analyze_risks(repo)
    assert (base.get("heuristic_circular_imports") or []) == []
    assert not any((f.get("label") == "[heuristic]") for f in (base.get("findings") or [])), base.get("findings")

    aggr = risks_mod.analyze_risks(repo, aggressive=True)
    assert any((f.get("label") == "[heuristic]") for f in (aggr.get("findings") or [])), aggr.get("findings")


def test_onboarding_where_to_start_ranking_and_avoid(tmp_path: Path):
    (tmp_path / "README.md").write_text("# x\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("hello\n", encoding="utf-8")

    (tmp_path / "main.py").write_text("from core import api\nprint(api())\n", encoding="utf-8")
    (tmp_path / "core.py").write_text("def api():\n    return 1\n", encoding="utf-8")

    big = ("x = 1\n" * 900)
    (tmp_path / "big.py").write_text(big, encoding="utf-8")

    repo = scan_repo(tmp_path)
    risks = risks_mod.analyze_risks(repo)
    arch = analyze_architecture(repo)
    onboarding = analyze_onboarding(repo, risks=risks, architecture=arch)

    wts = onboarding.get("where_to_start") or {}
    good = wts.get("good_first_files") or []
    avoid = wts.get("avoid_first_files") or []

    assert good
    assert avoid
    assert any(it.get("file") == "docs/guide.md" for it in good)
    assert any(it.get("file") == "main.py" for it in avoid)
    assert any(it.get("file") == "big.py" for it in avoid)
