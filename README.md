# RepoScope AI

RepoScope is a CLI tool that analyzes a repository (local path or GitHub URL) and writes **actionable** repo intelligence into files.

## What problem this solves
When you open an unfamiliar repository, you usually waste time answering basics:
- Where is the entry point?
- What’s the project shape?
- Where are the risky areas?
- Where should I start making changes?

RepoScope generates a small set of opinionated reports so you can get productive quickly.

## Why GitHub users need it
- **[contributors]** Get context fast before sending a PR.
- **[freelancers]** Audit a repo quickly and surface likely risk areas.
- **[new team members]** Find the safe places to start and the risky parts to avoid.
- **[maintainers]** Document repo shape and obvious smells for newcomers.

## Installation
```bash
python -m pip install reposcope-ai
```

Development install (editable):
```bash
python -m pip install -e .
```

Install dev dependencies (tests):
```bash
python -m pip install -e ".[dev]"
```

## 30-second Repo Audit
```bash
reposcope analyze https://github.com/user/repo
```

Output folder:
```text
.reposcope/
├── ARCHITECTURE.md
├── RISKS.md
├── ONBOARDING.md
├── SUMMARY.json
└── SUMMARY.md
```

## Usage
Analyze a local repo:
```bash
reposcope analyze .
```

Analyze a GitHub repo:
```bash
reposcope analyze https://github.com/user/project
```

AI explanations mode (optional):
```bash
set REPOSCOPE_OPENAI_API_KEY=YOUR_KEY
reposcope analyze . --ai
```

## Output
RepoScope writes its results into:
```
.reposcope/
├── ARCHITECTURE.md
├── RISKS.md
├── ONBOARDING.md
├── SUMMARY.json
└── SUMMARY.md
```

## One-shot badge
```md
[![RepoScope](https://img.shields.io/badge/RepoScope-Analyzed-blue)](https://github.com/OWNER/REPO/actions)
```

## GitHub Action (workflow integration)
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

The workflow uploads `.reposcope/` as artifacts. PR commenting only happens when the workflow enables it.

## Sample output
After running `reposcope analyze .`, open `.reposcope/RISKS.md`.

Example snippet:
```text
# Risks & Smells

## God files (very high line count)
- `src/something/big_file.py` (1203 lines)
```

## Notes
- Reports are best-effort heuristics.
- AI is optional and disabled by default.
- AI mode only adds **AI-assisted explanation** to existing findings. It does not add new findings.
- If AI fails for any reason, RepoScope falls back to non-AI output.

## Limitations (honest)
- Circular import detection is best-effort (currently focused on Python-style imports).
- Build/run instructions are inferred from common files and may be incomplete.
- Very large repos may take longer depending on file count.
