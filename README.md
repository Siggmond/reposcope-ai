# RepoScope AI

[![PyPI](https://img.shields.io/pypi/v/reposcope-ai)](https://pypi.org/project/reposcope-ai/)
[![Python](https://img.shields.io/pypi/pyversions/reposcope-ai)](https://pypi.org/project/reposcope-ai/)
[![License](https://img.shields.io/github/license/Siggmond/reposcope-ai)](LICENSE)
[![RepoScope workflow](https://img.shields.io/github/actions/workflow/status/Siggmond/reposcope-ai/reposcope.yml?label=workflow)](https://github.com/Siggmond/reposcope-ai/actions/workflows/reposcope.yml)
[![GitHub stars](https://img.shields.io/github/stars/Siggmond/reposcope-ai?style=social)](https://github.com/Siggmond/reposcope-ai)
![CLI](https://img.shields.io/badge/interface-CLI-blue)
![GitHub Action](https://img.shields.io/badge/GitHub-Action-2088FF)

**RepoScope AI** is a deterministic **CLI + GitHub Action** for turning an unfamiliar repository into practical architecture, risk, onboarding, and summary documentation. It helps maintainers, contributors, freelancers, consultants, and onboarding engineers build useful context quickly from a local repo or GitHub URL.

RepoScope is not a linter, not a security scanner, and not a magic AI code reviewer. By default it uses deterministic repository analysis and writes versionable Markdown and JSON artifacts. Optional AI mode can explain findings that already exist in the structured analysis, but it does not discover new issues.

---

## Quick Reviewer Path

If you have five minutes, this is the fastest way to evaluate the project.

**Problem it solves:** unfamiliar repositories often lack clear architecture notes, onboarding paths, risk summaries, and "where should I start?" guidance. RepoScope generates those first-pass documents from the repository itself.

**Install the CLI:**

```bash
pip install reposcope-ai
```

**Run it on a local repository:**

```bash
reposcope analyze .
```

**Run it on a GitHub repository URL:**

```bash
reposcope analyze https://github.com/user/repo
```

**Find the generated reports:**

```text
.reposcope/
|-- ARCHITECTURE.md
|-- RISKS.md
|-- ONBOARDING.md
|-- SUMMARY.md
`-- SUMMARY.json
```

**Use the GitHub Action:** the composite action sets up Python, installs RepoScope from PyPI by default, runs `reposcope analyze .`, and uploads `.reposcope/` as a workflow artifact named `reposcope`.

```yaml
- uses: actions/checkout@v4
- uses: Siggmond/reposcope-ai@v0.10.0
```

**Understand AI mode:** AI is disabled by default. With `--ai` and `REPOSCOPE_OPENAI_API_KEY`, RepoScope asks AI only to explain deterministic findings already produced by the analyzer. If the key is missing or the provider fails, deterministic reports are still written.

**Review tests/checks:** tests live in `tests/` and use `pytest`. For local development, install with `pip install -e ".[dev]"` and run `pytest`.

---

## What RepoScope Helps You Decide

RepoScope is built for practical repository orientation, not for abstract scoring. It helps reviewers and maintainers answer questions such as:

- Where should I start reading?
- Which files look risky to touch first?
- What changed in a PR, and did it touch known risk areas?
- Are there obvious structural smells worth human review?
- Are ownership or inactivity hints visible from Git history?

The answers are deterministic by default, explainable, and written for humans.

---

## What This Project Proves

RepoScope AI demonstrates practical developer-tooling work:

- CLI product design with a small, memorable command surface: `reposcope analyze <target>`.
- Repository loading for both local paths and GitHub URLs.
- Deterministic report generation that can run without networked AI services.
- Markdown and JSON artifacts designed for humans, CI artifacts, and downstream automation.
- GitHub Action integration through a composite `action.yml`.
- Architecture, risk, onboarding, ownership, and PR-impact documentation generation.
- Optional AI explanations that explain existing findings only.
- Fallback behavior when AI is unavailable or disabled.
- Honest handling of heuristic limits instead of claiming perfect repository understanding.

PR comment support is partially represented by `reposcope/src/report/pr_comment.py`, which renders a concise comment from `SUMMARY.json`. The current composite action uploads artifacts but does not yet post that comment automatically.

---

## Installation

```bash
pip install reposcope-ai
```

Development install:

```bash
pip install -e .
```

Install test dependencies:

```bash
pip install -e ".[dev]"
```

---

## CLI Usage

Analyze the current repository:

```bash
reposcope analyze .
```

Analyze a GitHub repository:

```bash
reposcope analyze https://github.com/user/repo
```

Write reports somewhere else:

```bash
reposcope analyze . --output reports/reposcope
```

Enable optional heuristic analyzers:

```bash
reposcope analyze . --aggressive
```

Compute deterministic PR impact against a Git base ref:

```bash
reposcope analyze . --diff main
```

---

## Generated Reports

RepoScope writes reports to `.reposcope/` unless `--output` is provided:

- `ARCHITECTURE.md` - main folders, entry points, and best-effort data-flow notes.
- `RISKS.md` - deterministic findings such as large files, god files, missing tests, circular imports, and other structural smells.
- `ONBOARDING.md` - first-hour checklist, where-to-start guidance, safe-ish files, risky files, run hints, and ownership hints when Git history is available.
- `SUMMARY.md` - concise human-readable scan summary.
- `SUMMARY.json` - structured scan output for automation, PR comments, or future integrations.

The reports are meant to be readable in pull requests, workflow artifacts, internal onboarding docs, or a repository's own documentation folder.

---

## GitHub Action

RepoScope ships with a composite GitHub Action. A minimal workflow looks like this:

```yaml
name: RepoScope

on:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Siggmond/reposcope-ai@v0.10.0
```

The action currently:

- Sets up Python.
- Installs `reposcope-ai` from PyPI by default.
- Runs `reposcope analyze .`.
- Uploads `.reposcope/` as an artifact named `reposcope`.

Useful inputs:

| Input | Purpose | Default |
| --- | --- | --- |
| `python-version` | Python version used by the action | `3.11` |
| `install-source` | Install from PyPI (`pypi`) or this action repository (`repo`) | `pypi` |
| `reposcope-version` | PyPI version to install, or `latest` | `latest` |
| `enable-ai` | Run `reposcope analyze . --ai` | `false` |

To enable AI explanations in the action, pass the flag and provide the API key as an environment variable:

```yaml
- uses: Siggmond/reposcope-ai@v0.10.0
  with:
    enable-ai: "true"
  env:
    REPOSCOPE_OPENAI_API_KEY: ${{ secrets.REPOSCOPE_OPENAI_API_KEY }}
```

Note: `action.yml` contains `post-comment` and `github-token` inputs, but the current composite action does not post PR comments. Treat them as reserved until a posting step is wired in.

---

## AI Mode Boundaries

AI mode is intentionally narrow:

- AI is disabled by default.
- AI only receives structured findings already produced by deterministic analysis.
- AI output is labeled as `AI-assisted explanation` when it appears in reports.
- AI does not discover new findings, assign hidden scores, or replace deterministic output.
- If the API key is missing, the provider fails, or the AI response cannot be parsed, RepoScope still writes deterministic reports.
- There is no hidden black-box scoring path.

Use AI mode when a short explanation would help a human understand an existing finding. Do not use it as evidence that RepoScope found additional issues.

```bash
set REPOSCOPE_OPENAI_API_KEY=YOUR_KEY
reposcope analyze . --ai
```

On macOS/Linux:

```bash
export REPOSCOPE_OPENAI_API_KEY=YOUR_KEY
reposcope analyze . --ai
```

---

## Current Scope / Honest Limitations

RepoScope is useful as a fast orientation layer, but it is deliberately not a substitute for engineering review:

- Analysis is heuristic and repository-shape based.
- Build and run instructions may be inferred and incomplete.
- Circular import detection is best-effort and currently focused on Python imports.
- Risk detection highlights structural signals; it is not a security scanner or correctness proof.
- Optional aggressive analysis can surface noisier heuristic findings and labels them as heuristic.
- AI mode is optional and does not discover new findings.
- Results should support human review, onboarding, and triage, not replace them.

---

## Development Checks

```bash
pip install -e ".[dev]"
pytest
```

The current test suite covers smoke scanning, large-file and god-file detection, conservative circular import checks, onboarding ranking, ownership hints, PR impact, and AI fallback behavior.

---

## Release Note

RepoScope v0.10.0 introduced PR impact analysis and onboarding intelligence.

---

## License

MIT License
