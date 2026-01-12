# RepoScope GitHub Action

This action runs RepoScope in a workflow and uploads `.reposcope/` as workflow artifacts.

PR commenting is **opt-in**.

## Usage
Create `.github/workflows/reposcope.yml`:

```yml
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
      - uses: reposcope-ai/analyze-repo@v1
        with:
          post-comment: "true"
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs
- `install-source`: `pypi` (default) or `repo`
- `reposcope-version`: `latest` (default) or a pinned version like `0.1.0`
- `enable-ai`: `true|false` (default `false`)
- `post-comment`: `true|false` (default `false`)
- `github-token`: required if `post-comment` is `true`

## Notes
- The workflow uploads `.reposcope/` as an artifact named `reposcope`.
- The PR comment (when enabled) is intentionally short: top risks + workflow run link + trust note.
