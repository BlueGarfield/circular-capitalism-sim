# Security Policy

## Supported versions

Only the latest release on the default branch receives security fixes.

## Reporting a vulnerability

Please **do not** open a public issue for security-sensitive reports.
Instead, use GitHub's **private vulnerability reporting** on this repository
(Security tab → "Report a vulnerability"). Include reproduction steps and
affected versions. You will receive an acknowledgment within 7 days.

## Scope notes

- This project is a research simulator; it processes no user credentials and
  ships no network services beyond a local Streamlit dashboard.
- Never include secrets, tokens, or private data in issues, PRs, scenario
  files, or committed outputs. `.gitignore` excludes `.env` and local
  environments by default.
