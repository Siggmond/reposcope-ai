# RepoScope GitHub Action

The **RepoScope GitHub Action** runs RepoScope as part of a GitHub workflow and uploads
the generated `.reposcope/` reports as workflow artifacts.

PR commenting is **explicitly opt-in**.

---

## What this action does

- Runs RepoScope against the checked-out repository
- Generates architecture, risk, onboarding, and summary reports
- Uploads `.reposcope/` as workflow artifacts
- Optionally posts a **concise, trust-safe PR comment** with top risks

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
  pull-requests: write

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Siggmond/reposcope-ai@v0.1.0
        with:
          post-comment: "true"
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

---

## Inputs

| Input | Description | Default |
|------|------------|---------|
| `python-version` | Python version used by the action | `3.11` |
| `install-source` | Install RepoScope from PyPI (`pypi`) or this repo (`repo`) | `pypi` |
| `reposcope-version` | RepoScope version to install | `latest` |
| `enable-ai` | Enable AI explanations mode | `false` |
| `post-comment` | Post PR comment with top risks | `false` |
| `github-token` | Required if `post-comment` is `true` | — |

---

## Notes

- `.reposcope/` is uploaded as an artifact named **reposcope**
- PR comments are intentionally short and link to full artifacts
- AI explanations are explain-only and never introduce new findings
