# Changelog

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
