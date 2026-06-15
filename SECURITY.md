# Security Policy

This project is designed for local personal knowledge bases. Treat everything
under `raw/` and generated wiki pages as private unless you intentionally publish
that content.

## Reporting

Please open a GitHub issue for security-sensitive bugs that do not expose private
data. If a report includes private source material, redact the data first and
describe the reproduction steps with synthetic examples.

## Data Handling

- Codex session import applies basic redaction for common secrets, emails, and
  local user paths, but it is not a substitute for review.
- The default `.gitignore` excludes private source material and generated
  knowledge pages.
- Always review `git status --ignored` before publishing a vault with real data.
