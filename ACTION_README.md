# RepoScope GitHub Action

The **RepoScope GitHub Action** runs RepoScope in a GitHub workflow and uploads the generated `.reposcope/` reports as workflow artifacts.

This action is deterministic by default. AI explanations are opt-in and only explain findings already produced by RepoScope.

---

## What This Action Does

- Sets up Python.
- Installs `reposcope-ai` from PyPI by default.
- Runs `reposcope analyze .` against the checked-out repository.
- Uploads `.reposcope/` as an artifact named `reposcope`.

The repository also contains a PR comment renderer in `reposcope/src/report/pr_comment.py`, but the current composite action does not post PR comments automatically.

---

## Usage

Create `.github/workflows/reposcope.yml`:

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

---

## AI Explanations

AI mode is disabled by default. To enable it, pass `enable-ai: "true"` and provide `REPOSCOPE_OPENAI_API_KEY`.

```yaml
- uses: Siggmond/reposcope-ai@v0.10.0
  with:
    enable-ai: "true"
  env:
    REPOSCOPE_OPENAI_API_KEY: ${{ secrets.REPOSCOPE_OPENAI_API_KEY }}
```

If the key is missing or AI fails, RepoScope still writes deterministic reports.

---

## Inputs

| Input | Description | Default |
| --- | --- | --- |
| `python-version` | Python version used by the action | `3.11` |
| `install-source` | Install RepoScope from PyPI (`pypi`) or from this action repository (`repo`) | `pypi` |
| `reposcope-version` | RepoScope version to install from PyPI | `latest` |
| `enable-ai` | Enable AI explanations mode | `false` |
| `post-comment` | Reserved in the current action; no PR comment is posted yet | `false` |
| `github-token` | Reserved with `post-comment`; not used by the current action | none |

---

## Notes

- `.reposcope/` is uploaded as an artifact named `reposcope`.
- Generated reports include `ARCHITECTURE.md`, `RISKS.md`, `ONBOARDING.md`, `SUMMARY.md`, and `SUMMARY.json`.
- AI explanations are explain-only and never introduce new findings.
- RepoScope v0.10.0 introduced PR impact analysis and onboarding intelligence.
