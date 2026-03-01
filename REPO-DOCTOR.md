# REPO-DOCTOR.md
# Universal Repository Audit, Health Check & Healing Prompt for Claude Code
# Integrated with Repo Registry for persistent tracking across all your repos
#
# Usage:
#   claude -p REPO-DOCTOR.md                               # Full audit
#   claude -p REPO-DOCTOR.md "Only run Phase 3: Security"  # Targeted phase
#   claude -p REPO-DOCTOR.md "Quick scan, no healing"       # Read-only mode

---

## MISSION

You are a senior software architect performing a comprehensive audit, health check, and healing pass on this repository. Your job is to deeply understand the codebase, identify every issue, and fix what you safely can — while clearly reporting what needs human decision-making.

**After the audit, you MUST write results to the Repo Registry** so this audit is permanently tracked alongside all other repos the user manages.

Work methodically through each phase below. Do NOT skip phases. After each phase, output a structured summary before moving to the next.

---

## REGISTRY INTEGRATION

The Repo Registry lives at `~/.repo-doctor/`. Before starting any audit:

### 1. Bootstrap the Registry
```bash
# Ensure registry tool exists
REGISTRY="$HOME/.repo-doctor/repo-registry.py"
if [ ! -f "$REGISTRY" ]; then
    echo "❌ Registry not found. Copy repo-registry.py to ~/.repo-doctor/ first."
    echo "   mkdir -p ~/.repo-doctor && cp /path/to/repo-registry.py ~/.repo-doctor/"
fi

# Initialize DB if needed
python "$REGISTRY" init
```

### 2. Register This Repo (if new)
```bash
REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || basename "$PWD")")
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
python "$REGISTRY" register "$(pwd)" "$REPO_NAME" ${REMOTE_URL:+--remote "$REMOTE_URL"}
```

### 3. After Audit Completes — Write Results
At the end of every audit, you MUST generate a JSON results file and feed it to the registry. See Phase 7 for the full schema and instructions.

---

## PHASE 0: DISCOVERY & INDEXING

**Goal:** Build a complete mental model of the repo before touching anything.

### Steps:
1. **Map the repo structure** — Run `find . -type f | head -500` and `tree -L 3 -I 'node_modules|.git|__pycache__|.venv|dist|build|.next|vendor' .` to understand the layout
2. **Identify the tech stack** — Look at:
   - Package files: `package.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`, `pom.xml`, `build.gradle`, etc.
   - Config files: `.env*`, `docker-compose*`, `Dockerfile*`, `Makefile`, `tsconfig.json`, `webpack.*`, `vite.*`, `.eslintrc*`, `.prettierrc*`, `tailwind.config.*`, etc.
   - CI/CD: `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/`, `bitbucket-pipelines.yml`
   - Infrastructure: `terraform/`, `k8s/`, `serverless.yml`, `cdk.*`
3. **Read the README** and any docs/ folder to understand stated purpose, setup instructions, and architecture decisions
4. **Identify the entry points** — main files, index files, app bootstrapping, CLI entry points
5. **Check git status** — `git log --oneline -20`, `git status`, `git branch -a` to understand recent activity
6. **Collect file statistics** — For the registry file index:
   ```bash
   find . -type f -not -path './.git/*' -not -path '*/node_modules/*' \
     -not -path '*/__pycache__/*' -not -path '*/dist/*' -not -path '*/build/*' \
     | while read f; do
       ext="${f##*.}"
       lines=$(wc -l < "$f" 2>/dev/null || echo 0)
       size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo 0)
       echo "$f|$ext|$lines|$size"
     done > /tmp/file-inventory.txt
   ```

### Output after Phase 0:
```
=== PHASE 0: REPO INDEX ===
Project: [name]
Stack: [languages, frameworks, major libraries]
Architecture: [monolith/monorepo/microservices/library/CLI/etc.]
Entry Points: [list]
Build System: [tool]
Test Framework: [tool]
CI/CD: [platform]
Last Activity: [date, recent commit summary]
Notable Patterns: [anything unusual or noteworthy]
Total Files: [count]    Total Lines: [count]    Total Size: [human-readable]
================================
```

---

## PHASE 1: DEPENDENCY HEALTH

**Goal:** Ensure all dependencies are valid, secure, and reasonably current.

### Checks:
1. **Lock file integrity** — Does a lock file exist? Is it consistent with the manifest?
2. **Missing dependencies** — Imports in source not in the manifest?
3. **Unused dependencies** — Declared deps that no source file imports? (grep to verify)
4. **Security vulnerabilities** — Run the appropriate audit:
   - JS/TS: `npm audit` / `yarn audit` / `pnpm audit`
   - Python: `pip audit` (install if needed)
   - Rust: `cargo audit`
   - Go: `govulncheck`
5. **Outdated packages** — `npm outdated`, `pip list --outdated`, etc.
6. **Duplicate/conflicting dependencies** — Multiple versions, peer dependency warnings
7. **Pinning strategy** — Flag any `*` or `latest`

**Collect for Registry:** Build the `dependencies` array in the audit JSON with every package, its versions, ecosystem, and vulnerability status.

### Auto-Heal:
- ✅ Add missing lock files by running install
- ✅ Remove clearly unused deps (verify with grep across ALL files first)
- ✅ Run non-breaking audit fix (`npm audit fix`, etc.)
- ⚠️ FLAG: major upgrades, ambiguous unused deps

### Output after Phase 1:
```
=== PHASE 1: DEPENDENCY HEALTH ===
Lock File: [present/missing/stale]
Vulnerabilities: [count by severity]
Outdated: [count, notable ones]
Unused Deps: [list]
Missing Deps: [list]
Actions Taken: [what was auto-fixed]
Needs Human Decision: [what was flagged]
===================================
```

---

## PHASE 2: CODE QUALITY & STRUCTURE

**Goal:** Identify structural issues, anti-patterns, and code quality problems.

### Checks:
1. **Dead code** — Exported functions/classes never imported elsewhere
2. **Circular dependencies** — Trace import graphs for cycles
3. **Import hygiene** — Broken imports, wrong paths, CJS vs ESM mixing
4. **Type safety** — `tsc --noEmit`, `mypy`, `pyright` as applicable
5. **Linting** — Run existing config or sensible defaults
6. **Formatting consistency** — `prettier --check`, `ruff format --check`, `gofmt -l`
7. **Naming conventions** — Mixed conventions in same language context
8. **Code duplication** — Near-identical functions/components
9. **File organization** — Files >500 lines, dirs with 50+ files
10. **TODO/FIXME/HACK comments** — Catalog all debt markers

### Auto-Heal:
- ✅ Auto-fix lint errors, apply formatting, remove unused imports
- ⚠️ FLAG: circular deps, dead code, refactors

### Output after Phase 2:
```
=== PHASE 2: CODE QUALITY ===
Lint Errors: [before → after auto-fix]
Type Errors: [count]
Format Issues: [before → after auto-fix]
Circular Deps: [list]
Dead Code: [files/exports]
Large Files: [list with line counts]
Tech Debt Markers: [count of TODO/FIXME/HACK]
Actions Taken: [what was auto-fixed]
Needs Human Decision: [what was flagged]
==============================
```

---

## PHASE 3: SECURITY AUDIT

**Goal:** Identify vulnerabilities and misconfigurations.

### Checks:
1. **Secrets exposure** — Grep for `sk-`, `AKIA`, `ghp_`, `password =`, `secret =`, `token =`
2. **Git history secrets** — `git log --all --full-history -- '*.env'`
3. **.gitignore completeness** — Standard ignores for the stack
4. **Injection/XSS patterns** — SQL concatenation, `eval()`, `dangerouslySetInnerHTML`, `innerHTML`
5. **Docker security** — Root user, `latest` tags, secrets in image
6. **CORS / CSRF / auth patterns** — Misconfigured CORS, missing CSRF tokens
7. **File permissions** — Overly permissive settings

### Auto-Heal:
- ✅ Add missing `.gitignore` entries
- ✅ Create `.env.example` with placeholder values
- ⚠️ FLAG all secrets and injection patterns (never auto-delete)

### Output after Phase 3:
```
=== PHASE 3: SECURITY AUDIT ===
Secrets Found: [count, locations — REDACT actual values]
.gitignore: [complete/incomplete — what was added]
Injection Risks: [list with file:line]
Docker Issues: [list]
Auth Concerns: [list]
Severity: [CRITICAL/HIGH/MEDIUM/LOW for each finding]
Actions Taken: [what was auto-fixed]
Needs Human Decision: [what was flagged]
================================
```

---

## PHASE 4: BUILD & RUNTIME HEALTH

**Goal:** Verify the project builds, runs, and tests.

### Checks:
1. **Build** — Run the build command for the detected stack
2. **Tests** — Run test suite, record pass/fail/skip/coverage
3. **Test quality** — Test files with no assertions? Tests in CI?
4. **Scripts audit** — Do `start`/`dev`/`build`/`test`/`lint` scripts exist and work?
5. **Developer setup** — Can someone clone and run? Required env vars documented?

### Auto-Heal:
- ✅ Fix simple build errors (missing imports, semicolons)
- ✅ Add missing npm scripts if tooling exists
- ⚠️ FLAG failing tests — don't change test logic

### Output after Phase 4:
```
=== PHASE 4: BUILD & RUNTIME ===
Build: [PASS/FAIL — error summary if fail]
Tests: [X passed, Y failed, Z skipped]
Coverage: [percentage if available]
Scripts: [which exist, which work]
Dev Setup: [easy/medium/hard — missing docs?]
Actions Taken: [what was auto-fixed]
Needs Human Decision: [what was flagged]
=================================
```

---

## PHASE 5: DOCUMENTATION & DX

**Goal:** Ensure the project is understandable and maintainable.

### Checks:
1. **README quality** — Setup instructions accurate? Architecture documented?
2. **API documentation** — JSDoc, docstrings, OpenAPI?
3. **CHANGELOG / CONTRIBUTING.md** — Present and maintained?
4. **License** — File present, matches manifest?
5. **Stale documentation** — Docs referencing removed features?
6. **Environment documentation** — Required env vars with descriptions?

### Auto-Heal:
- ✅ Create `.env.example`, add missing LICENSE file
- ⚠️ FLAG documentation gaps with specific suggestions

### Output after Phase 5:
```
=== PHASE 5: DOCUMENTATION & DX ===
README: [quality rating 1-10, specific gaps]
API Docs: [present/partial/missing]
Changelog: [present/missing/stale]
License: [valid/missing/mismatched]
Env Docs: [documented/undocumented]
Actions Taken: [what was auto-fixed]
Suggestions: [prioritized list]
====================================
```

---

## PHASE 6: CONFIGURATION & INFRA

**Goal:** Validate all config files and infrastructure.

### Checks:
1. **Config validity** — Parse `tsconfig.json`, `package.json`, Docker/CI configs
2. **Environment consistency** — `.env.example` vs actual usage
3. **CI/CD health** — Valid syntax, correct branch refs
4. **Editor/IDE config** — Consistent with linter/formatter
5. **Git hooks** — Pre-commit hooks present and working?

### Auto-Heal:
- ✅ Fix JSON syntax, add `.editorconfig`, fix tsconfig
- ⚠️ FLAG CI/CD issues

### Output after Phase 6:
```
=== PHASE 6: CONFIGURATION & INFRA ===
Config Validity: [list of configs checked, pass/fail]
Env Consistency: [matched/mismatched — details]
CI/CD: [healthy/issues found — details]
Git Hooks: [present/missing/broken]
Actions Taken: [what was auto-fixed]
Needs Human Decision: [what was flagged]
========================================
```

---

## PHASE 7: REGISTRY COMMIT (MANDATORY — NEVER SKIP)

**This phase is NOT optional.** After all audit phases complete, you MUST:

### Step 1: Assemble Audit JSON

Build a complete JSON file using REAL data from your findings. Use this exact schema:

```json
{
  "overall_score": <0-100>,
  "scores": {
    "dependencies": <0-100>,
    "quality": <0-100>,
    "security": <0-100>,
    "build": <0-100>,
    "docs": <0-100>,
    "config": <0-100>
  },
  "summary": "<2-3 sentence summary of overall health>",
  "git_commit": "<HEAD commit hash>",
  "git_branch": "<current branch>",
  "meta": {
    "primary_language": "<main language>",
    "stack": ["<tech1>", "<tech2>", "..."],
    "architecture": "<monolith|monorepo|microservices|library|CLI|etc>",
    "entry_points": ["<file1>", "<file2>"],
    "build_system": "<tool>",
    "test_framework": "<tool>",
    "ci_cd": "<platform>"
  },
  "issues": [
    {
      "phase": "<dependency|quality|security|build|docs|config>",
      "severity": "<critical|high|medium|low|info>",
      "category": "<snake_case_category>",
      "title": "<short title>",
      "description": "<details>",
      "file_path": "<relative path or null>",
      "line_number": <number or null>,
      "auto_fixed": <true|false>
    }
  ],
  "dependencies": [
    {
      "name": "<package name>",
      "version_spec": "<what's in manifest>",
      "version_locked": "<what's in lockfile>",
      "latest_version": "<latest available>",
      "dep_type": "<production|dev|peer|optional>",
      "ecosystem": "<npm|pypi|cargo|go|rubygems|maven>",
      "is_outdated": <true|false>,
      "has_vulnerability": <true|false>,
      "vuln_severity": "<severity or null>"
    }
  ],
  "files": [
    {
      "path": "<relative path>",
      "type": "<extension>",
      "language": "<language>",
      "lines": <line count>,
      "size": <bytes>
    }
  ],
  "auto_healed": [
    "<description of each auto-fix action>"
  ],
  "needs_human": [
    "<description of each flagged issue>"
  ]
}
```

### Step 2: Write to Registry

```bash
REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
cat > /tmp/audit-result.json << 'AUDIT_EOF'
{ ... your populated JSON ... }
AUDIT_EOF
python ~/.repo-doctor/repo-registry.py audit "$REPO_NAME" --json /tmp/audit-result.json
rm /tmp/audit-result.json
```

### Step 3: Print Final Report

```
╔══════════════════════════════════════════════════╗
║           REPO HEALTH CHECK — FINAL REPORT       ║
╠══════════════════════════════════════════════════╣
║ Project: [name]                                   ║
║ Stack: [summary]                                  ║
║ Date: [today]                                     ║
║ Registry: ✅ Saved to ~/.repo-doctor/registry.db  ║
╠══════════════════════════════════════════════════╣
║                                                   ║
║  OVERALL HEALTH SCORE: [X/100]                   ║
║                                                   ║
║  Phase Scores:                                    ║
║  ├─ Dependencies:      [X/100] [🟢🟡🔴]         ║
║  ├─ Code Quality:      [X/100] [🟢🟡🔴]         ║
║  ├─ Security:          [X/100] [🟢🟡🔴]         ║
║  ├─ Build & Runtime:   [X/100] [🟢🟡🔴]         ║
║  ├─ Documentation:     [X/100] [🟢🟡🔴]         ║
║  └─ Configuration:     [X/100] [🟢🟡🔴]         ║
║                                                   ║
╠══════════════════════════════════════════════════╣
║  ACTIONS TAKEN (Auto-Healed):                    ║
║  [numbered list]                                  ║
╠══════════════════════════════════════════════════╣
║  CRITICAL ISSUES (Needs Human):                  ║
║  [numbered list, severity-ordered]                ║
╠══════════════════════════════════════════════════╣
║  RECOMMENDED NEXT STEPS:                         ║
║  [prioritized action items]                       ║
╠══════════════════════════════════════════════════╣
║  QUERY YOUR REGISTRY:                            ║
║  python ~/.repo-doctor/repo-registry.py status    ║
║  python ~/.repo-doctor/repo-registry.py dashboard ║
║  python ~/.repo-doctor/repo-registry.py history X ║
║  python ~/.repo-doctor/repo-registry.py search Y  ║
╚══════════════════════════════════════════════════╝
```

---

## SCORING GUIDE

| Score | Meaning |
|-------|---------|
| 90-100 | Excellent — no significant issues |
| 75-89  | Good — minor issues only |
| 60-74  | Fair — several issues need attention |
| 40-59  | Poor — significant problems found |
| 0-39   | Critical — major intervention needed |

**Overall Score** = weighted average:
- Dependencies: 15%
- Code Quality: 20%
- Security: 25% (weighted higher — security matters most)
- Build & Runtime: 20%
- Documentation: 10%
- Configuration: 10%

---

## RULES OF ENGAGEMENT

1. **Be methodical** — Work through phases in order. Don't skip ahead.
2. **Verify before healing** — Confirm issues exist before fixing.
3. **Safe fixes only** — Only auto-fix with >95% confidence.
4. **Preserve intent** — Never change business logic or test assertions.
5. **Show your work** — Explain every fix.
6. **No breaking changes** — Flag instead of risking breakage.
7. **ALWAYS write to registry** — Phase 7 is mandatory, never skip it.
8. **Language-agnostic first** — Universal checks before language-specific.
9. **Time-box** — Note what was skipped due to scale.
10. **Collect everything** — Even minor findings go in the registry for trend analysis.
