# Changelog

## 0.10.0

### Major feature upgrade — repo understanding & decision support

- Deterministic structural analyzers:
  - Large files (LOC-based)
  - God modules (AST-based)
  - Dead code (conservative, resolvable-only)
  - Circular imports (Python, resolvable-only)
- Onboarding intelligence:
  - “Where to start” recommendations
  - First-hour checklist
  - Safe vs risky files
- PR impact analysis:
  - `--diff <base>` highlights risk when reviewing changes
- Ownership & bus-factor hints (git-based, deterministic)
- Aggressive mode (`--aggressive`) for opt-in heuristic checks:
  - Magic numbers
  - Risky shell commands
- Improved summaries:
  - Clear labeling: deterministic vs heuristic
  - Shareable `SUMMARY.md`

This release significantly expands RepoScope’s usefulness for
contributors, reviewers, freelancers, and maintainers.




## 0.1.0

### Initial public release

- CLI: `reposcope analyze <path|url>` generates `.reposcope/` reports
- Reports:
  - ARCHITECTURE.md
  - RISKS.md
  - ONBOARDING.md
  - SUMMARY.md / SUMMARY.json
- Optional AI explanations mode (`--ai`) for explaining existing findings
- GitHub Action:
  - Uploads `.reposcope/` as workflow artifacts
  - Optional concise PR comment
