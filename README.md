# RepoScope AI

**RepoScope AI** is a fast, deterministic **CLI + GitHub Action** that audits a Git repository and generates
**clear, actionable documentation** — so you can understand any codebase in minutes, not hours.

It is designed for **developers, contributors, freelancers, and maintainers** who need to answer one question quickly:

> *“What am I looking at, and where should I start?”*

---

## 🚨 The Problem

Opening an unfamiliar repository usually means wasting time figuring out:
- Where is the entry point?
- How is the project structured?
- Which files are risky or too large?
- Where can I safely make changes?
- What should a new contributor know first?

Most repositories **do not document these answers**.

---

## ✅ The Solution

RepoScope analyzes a repository (local path or GitHub URL) and generates a small set of **opinionated, human‑readable reports**:

- **ARCHITECTURE.md** — high‑level project structure and layout
- **RISKS.md** — large files, missing tests, structural smells
- **ONBOARDING.md** — guidance for new contributors
- **SUMMARY.md / SUMMARY.json** — concise, shareable snapshot

All outputs are:
- Deterministic by default
- Versionable (plain Markdown / JSON)
- Designed to be read by humans, not dashboards

---

## 👥 Who This Is For

- **Contributors** — get context before opening a PR  
- **Freelancers / consultants** — audit a repo quickly and surface risk areas  
- **New team members** — know where to start and what to avoid  
- **Maintainers** — document repo shape and obvious smells automatically  

If you’ve ever said *“I need 30 minutes just to understand this repo”*, this tool is for you.

---

## 📦 Installation

```bash
pip install reposcope-ai
```

Development install (editable):
```bash
pip install -e .
```

Install dev dependencies (tests):
```bash
pip install -e ".[dev]"
```

---

## ⚡ 30‑Second Repo Audit

Analyze a GitHub repository:
```bash
reposcope analyze https://github.com/user/repo
```

Analyze a local repository:
```bash
reposcope analyze .
```

Generated output:
```text
.reposcope/
├── ARCHITECTURE.md
├── RISKS.md
├── ONBOARDING.md
├── SUMMARY.md
└── SUMMARY.json
```

---

## 🧠 Optional AI Explanations (Opt‑In)

RepoScope supports an **AI explanations mode** that adds explanations **only** to existing findings.

```bash
set REPOSCOPE_OPENAI_API_KEY=YOUR_KEY
reposcope analyze . --ai
```

### AI design rules (important):
- AI **never discovers new issues**
- AI receives **structured findings only**
- All AI text is clearly labeled as **AI‑assisted explanation**
- If AI fails, RepoScope silently falls back to non‑AI output

AI is **disabled by default**.

---

## 🤖 GitHub Action (PR Integration)

RepoScope ships with a first‑class GitHub Action.

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

The workflow:
- Runs RepoScope on the repo
- Uploads `.reposcope/` as artifacts
- Optionally comments top risks on the PR (opt‑in)

---

## 🏷️ One‑Shot Badge

```md
[![RepoScope](https://img.shields.io/badge/RepoScope-Analyzed-blue)](https://github.com/OWNER/REPO/actions)
```

---

## 📄 Example Output

Excerpt from `RISKS.md`:

```text
## God files (very high line count)
- src/core/big_file.py (1203 lines)
```

---

## ⚠️ Limitations (Honest)

- Analysis is heuristic, not static analysis
- Circular import detection is best‑effort
- Build/run instructions are inferred and may be incomplete
- Very large repos may take longer depending on file count

---

## 🔐 Trust & Safety

- Deterministic output by default
- AI is optional and clearly labeled
- No hallucinated findings
- No black‑box scoring

---

## 📜 License

MIT License

---

If you maintain repositories, review pull requests, or onboard developers,
RepoScope AI is built to save you time.
