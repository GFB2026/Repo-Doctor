# 🩺 Repo Doctor

A universal repository audit system with persistent registry tracking for Claude Code.

## Quick Start

```bash
# 1. Install the registry (one-time)
bash setup.sh

# 2. Add the alias (optional, for convenience)
echo 'alias repo-doctor="python ~/.repo-doctor/repo-registry.py"' >> ~/.zshrc
source ~/.zshrc

# 3. Drop REPO-DOCTOR.md into any repo and audit it
cp REPO-DOCTOR.md /path/to/your/repo/
cd /path/to/your/repo
claude -p REPO-DOCTOR.md
```

## What You Get

### The Audit (REPO-DOCTOR.md)
Drop into any repo. Claude Code runs 7 phases:

| Phase | What It Does |
|-------|-------------|
| 0 - Discovery | Maps structure, stack, entry points, git status |
| 1 - Dependencies | Lock files, vulnerabilities, unused/missing deps |
| 2 - Code Quality | Lint, types, dead code, circular deps, formatting |
| 3 - Security | Secrets, injection patterns, .gitignore, Docker |
| 4 - Build & Runtime | Build verification, test suite, scripts, dev setup |
| 5 - Documentation | README, API docs, changelog, license, env docs |
| 6 - Configuration | Config validation, CI/CD, env consistency |
| 7 - Registry | **Writes all results to your persistent database** |

### The Registry (repo-registry.py)
A SQLite-backed CLI that accumulates data across every audit:

```bash
repo-doctor status                    # All repos at a glance
repo-doctor status my-project         # Deep dive on one repo
repo-doctor dashboard                 # Portfolio-wide summary
repo-doctor search "React"            # Find repos by stack/name/tag
repo-doctor history my-project        # Score history over time
repo-doctor tags my-project client v2 # Tag repos for organization
repo-doctor note my-project "Needs refactor before Q3"
repo-doctor relate frontend backend depends_on
repo-doctor export --format json      # Full data export
```

### What's Tracked

- **Per repo:** Name, path, remote URL, tech stack, architecture, tags, notes
- **Per audit:** 6 phase scores + overall, git state, every issue found, every fix applied
- **Per issue:** Phase, severity, category, file path, line number, auto-fixed status
- **Per dependency:** Name, versions (spec/locked/latest), ecosystem, vulnerability status
- **File inventory:** Path, language, line count, size

### Database Location

```
~/.repo-doctor/
├── registry.db        # SQLite database (all your data)
└── repo-registry.py   # CLI tool
```

## Example Output

```
┌──────────────────┬────────────────────────┬───────┬──────┬──────┬──────┬───────┬──────┬──────┬────────────┐
│Name              │Stack                   │Score  │Dep   │Qual  │Sec   │Build  │Docs  │Cfg   │Last Audit  │
├──────────────────┼────────────────────────┼───────┼──────┼──────┼──────┼───────┼──────┼──────┼────────────┤
│ili-orchestrator  │Python, Brevo…          │🟢 91   │🟢 95  │🟢 88  │🟢 92  │🟢 95   │🟢 80  │🟢 90  │2026-02-28  │
│pc-utility-pro    │Electron, React…        │🟡 78   │🟢 85  │🟡 72  │🟡 65  │🟢 90   │🟡 60  │🟢 88  │2026-02-28  │
│template-engine   │Next.js, Tailwind…      │🟡 65   │🟡 70  │🟡 60  │🟡 55  │🟢 80   │🔴 40  │🟡 75  │2026-02-27  │
└──────────────────┴────────────────────────┴───────┴──────┴──────┴──────┴───────┴──────┴──────┴────────────┘
```
