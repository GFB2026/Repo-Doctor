# PROJECT-DOCTOR.md
# Universal Project Audit, Health Check & Healing System
# Works on codebases, legal files, school work, business documents — anything.

## EXECUTE IMMEDIATELY

You are reading this file as your instructions. DO NOT wait for further input. DO NOT ask any questions. DO NOT confirm before starting. BEGIN the full audit NOW by running Phase 0: Detection on the current working directory. Work through every phase autonomously until the final report is printed and results are written to the registry. The user expects you to run the entire process end-to-end without stopping.

START NOW. Run Phase 0.

---

## MISSION

You are a senior analyst performing a comprehensive audit, health check, and organization pass on this project. Your FIRST job is to figure out WHAT you're looking at — it could be a software codebase, a legal case folder, school coursework, a business document collection, a creative project, or a mix of everything.

Adapt your entire approach based on what you find. Then audit it, fix what you safely can, and write results to the Project Registry.

---

## PHASE 0: DETECTION — WHAT AM I LOOKING AT?

**This is the most important phase. Get this right and everything else follows.**

### Step 1: Scan Everything
```bash
# Map the full structure
find . -type f -not -path './.git/*' | head -300
tree -L 3 -I 'node_modules|.git|__pycache__|.venv|dist|build|.next|vendor' . 2>/dev/null || find . -maxdepth 3 -not -path './.git/*' | head -200

# Count file types
find . -type f -not -path './.git/*' | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20

# Check for code indicators
ls package.json requirements.txt pyproject.toml Cargo.toml go.mod Gemfile Makefile Dockerfile docker-compose* 2>/dev/null

# Check for document indicators
find . -type f \( -name "*.docx" -o -name "*.pdf" -o -name "*.doc" -o -name "*.xlsx" -o -name "*.xls" -o -name "*.pptx" -o -name "*.txt" -o -name "*.rtf" -o -name "*.odt" -o -name "*.csv" \) | head -50
```

### Step 2: Classify the Project

Based on what you find, assign ONE primary type and optionally secondary types:

| Type | Indicators |
|------|-----------|
| **CODEBASE** | package.json, .py/.js/.ts/.go/.rs files, Dockerfile, .git with code commits, src/ directories |
| **LEGAL** | Contracts, pleadings, discovery, case files, attorney correspondence, exhibits, .pdf/.docx legal documents, folders named by case/matter |
| **SCHOOL** | Syllabi, assignments, essays, problem sets, course-numbered folders, research papers, citations |
| **BUSINESS** | Proposals, invoices, SOWs, marketing materials, financial spreadsheets, client folders, org charts |
| **CREATIVE** | Manuscripts, screenplays, design files, image assets, portfolio pieces, drafts/revisions |
| **RESEARCH** | Datasets, notebooks (.ipynb), papers, literature reviews, methodology docs, raw data |
| **PERSONAL** | Tax docs, insurance, medical records, personal finance, mixed life admin files |
| **MIXED** | Combination of the above — identify the primary and secondary types |

### Output after Phase 0:
```
=== PHASE 0: PROJECT DETECTION ===
Project Name: [name]
Primary Type: [CODEBASE / LEGAL / SCHOOL / BUSINESS / CREATIVE / RESEARCH / PERSONAL / MIXED]
Secondary Types: [if any]
Confidence: [HIGH / MEDIUM / LOW]
Total Files: [count]
File Types: [breakdown]
Key Observations: [what tipped the classification]
==================================
```

**Now proceed to the phase set that matches the detected type.**

---

# ============================================================
# TRACK A: CODEBASE PROJECTS
# ============================================================

If the project is a CODEBASE, run these 6 phases:

## A1: DEPENDENCY HEALTH
- Lock file integrity and consistency
- Missing/unused dependencies (verify with grep)
- Security vulnerabilities (npm audit, pip audit, etc.)
- Outdated packages, pinning strategy
- **Auto-heal:** Run safe audit fixes, remove verified unused deps
- **Flag:** Major upgrades, ambiguous deps

## A2: CODE QUALITY & STRUCTURE
- Dead code, circular dependencies, import hygiene
- Type safety (tsc, mypy, pyright)
- Linting and formatting (run existing config or sensible defaults)
- Code duplication, file organization (flag >500 line files)
- TODO/FIXME/HACK catalog
- **Auto-heal:** Auto-fix lint, apply formatting, remove unused imports
- **Flag:** Circular deps, dead code, refactors needed

## A3: SECURITY AUDIT
- Secrets scan (API keys, tokens, passwords in source)
- Git history for committed secrets
- .gitignore completeness
- Injection/XSS patterns (eval, SQL concat, innerHTML)
- Docker security (root user, latest tags, secrets in image)
- **Auto-heal:** Fix .gitignore, create .env.example
- **Flag:** All secrets and injection patterns

## A4: BUILD & RUNTIME
- Run build command, test suite
- Test quality (empty test files, coverage)
- Scripts audit (do start/dev/build/test/lint exist and work)
- Developer setup assessment
- **Auto-heal:** Fix simple build errors, add missing scripts
- **Flag:** Failing tests

## A5: DOCUMENTATION & DX
- README quality and accuracy
- API docs, CHANGELOG, CONTRIBUTING, LICENSE
- Environment documentation
- Stale docs referencing removed features
- **Auto-heal:** Create .env.example, add missing LICENSE
- **Flag:** Documentation gaps

## A6: CONFIGURATION & INFRA
- Config file validity (tsconfig, package.json, Docker, CI/CD)
- Environment consistency
- Editor/IDE config, git hooks
- **Auto-heal:** Fix JSON syntax, add .editorconfig
- **Flag:** CI/CD issues

---

# ============================================================
# TRACK B: LEGAL PROJECTS
# ============================================================

If the project is LEGAL (case files, contracts, discovery, etc.), run these phases:

## B1: DOCUMENT INVENTORY & ORGANIZATION
- **Catalog every document** — filename, type, date, page count, parties involved
- **Filing structure assessment:**
  - Are documents organized by category (pleadings, discovery, correspondence, exhibits)?
  - Are filenames consistent and descriptive?
  - Are there date-stamped versions vs unnamed drafts?
  - Is there a clear folder hierarchy?
- **Missing document detection:**
  - Referenced documents that don't exist in the folder
  - Gaps in chronological sequence (e.g., complaint exists but no answer)
  - Standard documents missing for the case type
- **Duplicate detection** — Same document with different names or in multiple folders
- **Auto-heal:** Suggest a folder structure, flag duplicates, create a document index
- **Flag:** Missing referenced docs, unnamed/undated files

## B2: CONTENT ANALYSIS
- **Document types found:** Contracts, pleadings, motions, correspondence, exhibits, discovery responses, affidavits, orders, etc.
- **Key dates extraction** — Filing dates, deadlines, statute of limitations, hearing dates
- **Parties identification** — Who are the parties, counsel, judges, witnesses mentioned?
- **Claim/issue mapping** — What legal claims or issues are being pursued?
- **Cross-reference check** — Do exhibits match what's referenced in briefs? Do discovery responses match requests?
- **Flag:** Inconsistencies between documents, missing exhibits, unreferenced evidence

## B3: TIMELINE & STATUS
- **Build a chronological timeline** of all events based on document dates
- **Identify current status** — What stage is the matter in?
- **Upcoming deadlines** — Any mentioned deadlines, statutes, or response dates
- **Action items** — What appears to need attention based on the documents?
- **Flag:** Passed deadlines, gaps in timeline, stale matters

## B4: COMPLETENESS & RISK
- **Standard checklist by case type:**
  - Litigation: Complaint, answer, discovery, motions, orders, trial prep
  - Contract: All parties signed, all exhibits attached, amendments tracked
  - Corporate: Formation docs, resolutions, compliance filings
  - Real estate: Title, survey, inspection, closing docs
- **Privilege/confidentiality check** — Are privileged documents marked? Are there documents that should be restricted?
- **Version control** — Are there multiple drafts? Is the final version clearly identified?
- **Flag:** Missing standard documents, unsigned agreements, unresolved redlines

## B5: DOCUMENTATION QUALITY
- **Naming conventions** — Are files named consistently? (e.g., YYYY-MM-DD_Type_Description)
- **Metadata** — Are PDFs searchable (OCR)? Are Word docs using track changes properly?
- **Organization** — Could someone new pick this up and understand the matter?
- **Index/summary** — Is there a master index, case summary, or matter overview?
- **Auto-heal:** Generate a master document index, suggest renamed files, create a timeline summary
- **Flag:** Non-searchable PDFs, inconsistent naming, missing case summary

---

# ============================================================
# TRACK C: SCHOOL / ACADEMIC PROJECTS
# ============================================================

If the project is SCHOOL or ACADEMIC work, run these phases:

## C1: INVENTORY & ORGANIZATION
- **Catalog all materials** — syllabi, assignments, papers, notes, problem sets, presentations
- **Course/subject mapping** — Which courses are represented?
- **Assignment tracking** — Completed vs incomplete, graded vs ungraded
- **File organization** — By course? By date? By type? Or chaos?
- **Auto-heal:** Suggest folder structure (by course > by assignment type), create index
- **Flag:** Missing assignments, disorganized structure

## C2: CONTENT QUALITY
- **Writing quality** — For essays/papers: structure, citations, formatting
- **Citation check** — Are sources cited? Consistent citation format (APA, MLA, Chicago)?
- **Completeness** — Do assignments appear complete? Are there empty/stub files?
- **Formatting** — Consistent formatting, proper headers, page numbers
- **Flag:** Missing citations, incomplete work, formatting inconsistencies

## C3: ACADEMIC INTEGRITY
- **Citation completeness** — Every claim backed by a source?
- **Bibliography/references** — Present and properly formatted?
- **Source quality** — Are sources academic/credible or random web pages?
- **Flag:** Missing citations for specific claims, weak source quality

## C4: PROGRESS & GAPS
- **What's complete vs in-progress vs not started?**
- **Grade tracking** — If grades are present, summarize performance
- **Knowledge gaps** — Based on coursework, what areas might need more attention?
- **Study materials** — Are there study guides, flashcards, practice problems?
- **Suggest:** Study schedule, areas to focus on, missing materials to create

---

# ============================================================
# TRACK D: BUSINESS PROJECTS
# ============================================================

If the project is BUSINESS documents, run these phases:

## D1: DOCUMENT INVENTORY
- **Catalog everything** — Proposals, contracts, invoices, SOWs, marketing, financial docs
- **Client/project mapping** — Which clients or projects are represented?
- **Document status** — Draft vs final, signed vs unsigned, current vs expired
- **Auto-heal:** Create a document index, suggest folder structure
- **Flag:** Unsigned contracts, expired documents still in active folders

## D2: FINANCIAL HEALTH
- **Invoice tracking** — Outstanding vs paid, aging analysis
- **Contract values** — Total contract values, recurring revenue
- **Expense documentation** — Are expenses categorized and documented?
- **Tax readiness** — Are documents organized for tax purposes?
- **Flag:** Old unpaid invoices, missing expense receipts, tax-relevant gaps

## D3: OPERATIONAL COMPLETENESS
- **Standard business docs:** Do these exist?
  - Operating agreement / bylaws
  - Business licenses / registrations
  - Insurance policies (current?)
  - Client contracts (signed, current?)
  - Employee/contractor agreements
  - Privacy policy / terms of service (if applicable)
- **Compliance** — Are required filings up to date?
- **Flag:** Missing standard documents, expired licenses/insurance

## D4: COMMUNICATION & PROPOSALS
- **Proposal quality** — Are proposals professional, complete, clearly priced?
- **Template consistency** — Are documents using consistent branding/formatting?
- **Follow-up tracking** — Are there sent proposals with no response documented?
- **Flag:** Inconsistent branding, stale proposals, missing follow-ups

---

# ============================================================
# TRACK E: CREATIVE / RESEARCH / PERSONAL
# ============================================================

For CREATIVE, RESEARCH, or PERSONAL projects, adapt the general framework:

## E1: INVENTORY & ORGANIZATION
- Catalog all files by type, date, and status (draft/final/archived)
- Assess folder structure and naming conventions
- Identify duplicates and orphaned files
- **Auto-heal:** Create index, suggest structure, flag duplicates

## E2: COMPLETENESS & QUALITY
- What appears finished vs in-progress vs abandoned?
- Are there multiple versions/drafts with a clear progression?
- Is the current/final version clearly identifiable?
- **Flag:** Abandoned work, version confusion, missing pieces

## E3: ACCESSIBILITY & MAINTENANCE
- Can someone else understand this collection?
- Are files in open/accessible formats?
- Is there any documentation or README explaining the project?
- Are backups or exports needed?
- **Auto-heal:** Create a README/index for the project
- **Flag:** Proprietary formats, no documentation, no backup strategy

---

# ============================================================
# UNIVERSAL PHASES (RUN FOR ALL PROJECT TYPES)
# ============================================================

## UNIVERSAL 1: FILE HEALTH
Run for ALL project types after the type-specific phases:

- **Corruption check** — Can all files be opened/read?
- **Empty files** — Flag zero-byte files
- **Very large files** — Flag anything unusually large
- **Old/stale files** — Files not modified in 1+ years in an active project
- **Naming hygiene** — Spaces, special characters, inconsistent casing, overly long names
- **Duplicate detection** — Files with same size/name in different locations
- **Auto-heal:** List all issues found, suggest renames for badly named files

## UNIVERSAL 2: STRUCTURE ASSESSMENT
Run for ALL project types:

- **Depth** — Is the folder structure too deep (>5 levels) or too flat?
- **Overcrowding** — Folders with 50+ files that should be subdivided?
- **Empty folders** — Directories with nothing in them
- **README/INDEX** — Is there any top-level documentation explaining the project?
- **Auto-heal:** Create or update a top-level README/INDEX document

---

# ============================================================
# REGISTRY INTEGRATION (MANDATORY — ALL PROJECT TYPES)
# ============================================================

## FINAL PHASE: REGISTRY COMMIT

The Project Registry lives at `~/.repo-doctor/`. After ALL audit phases:

### 1. Bootstrap (if needed)
```bash
REGISTRY="$HOME/.repo-doctor/repo-registry.py"
if [ ! -f "$REGISTRY" ]; then
    echo "[ERROR] Registry not found at $REGISTRY"
    echo "Copy repo-registry.py to ~/.repo-doctor/ first."
else
    python "$REGISTRY" init 2>/dev/null
fi
```

### 2. Register + Write Results
```bash
PROJECT_NAME=$(basename "$(pwd)")
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")

# Register if new
if [ -n "$REMOTE_URL" ]; then
    python "$REGISTRY" register "$(pwd)" "$PROJECT_NAME" --remote "$REMOTE_URL"
else
    python "$REGISTRY" register "$(pwd)" "$PROJECT_NAME"
fi

# Write audit JSON
cat > /tmp/audit-result.json << 'AUDIT_EOF'
{ ... populated from real findings ... }
AUDIT_EOF
python "$REGISTRY" audit "$PROJECT_NAME" --json /tmp/audit-result.json
rm /tmp/audit-result.json
```

### Audit JSON Schema
Adapt to project type — not all fields apply to every type:

```json
{
  "overall_score": 75,
  "scores": {
    "organization": 80,
    "completeness": 70,
    "quality": 65,
    "security": 85,
    "documentation": 60,
    "health": 90
  },
  "summary": "Well-organized legal case folder with strong document inventory...",
  "git_commit": "<hash or null>",
  "git_branch": "<branch or null>",
  "meta": {
    "project_type": "LEGAL",
    "secondary_types": [],
    "primary_language": "<language or null>",
    "stack": ["<technologies or document types>"],
    "architecture": "<structure description>",
    "entry_points": ["<main files or key documents>"],
    "build_system": "<or null>",
    "test_framework": "<or null>",
    "ci_cd": "<or null>"
  },
  "issues": [
    {
      "phase": "<phase name>",
      "severity": "high",
      "category": "missing_document",
      "title": "No signed contract for Acme Corp engagement",
      "description": "SOW exists but no executed agreement found",
      "file_path": "clients/acme/",
      "line_number": null,
      "auto_fixed": false
    }
  ],
  "dependencies": [],
  "files": [
    {
      "path": "contracts/acme-sow-v2.docx",
      "type": "docx",
      "language": null,
      "lines": null,
      "size": 45200
    }
  ],
  "auto_healed": [
    "Created master document index",
    "Suggested folder reorganization"
  ],
  "needs_human": [
    "Missing signed contract for Acme Corp",
    "3 expired insurance certificates"
  ]
}
```

### Score Categories by Project Type

**CODEBASE** scores map to: dependencies, quality, security, build, docs, config

**LEGAL / BUSINESS / SCHOOL / CREATIVE / RESEARCH / PERSONAL** scores map to:
| Score | Meaning |
|-------|---------|
| organization | Folder structure, naming, filing system |
| completeness | Are expected documents present? Gaps? |
| quality | Content quality, formatting, professionalism |
| security | Sensitive data exposure, privilege, confidentiality |
| documentation | README, indexes, summaries, metadata |
| health | File integrity, duplicates, staleness, accessibility |

---

## FINAL REPORT

```
+======================================================+
:           PROJECT HEALTH CHECK -- FINAL REPORT        :
+======================================================+
: Project: [name]                                       :
: Type: [CODEBASE / LEGAL / SCHOOL / BUSINESS / etc.]  :
: Date: [today]                                         :
: Registry: Saved to ~/.repo-doctor/registry.db         :
+======================================================+
:                                                       :
:  OVERALL HEALTH SCORE: [X/100]                        :
:                                                       :
:  Phase Scores:                                        :
:  [phase 1]:      [X/100] [OK/!!/XX]                  :
:  [phase 2]:      [X/100] [OK/!!/XX]                  :
:  [phase 3]:      [X/100] [OK/!!/XX]                  :
:  [phase 4]:      [X/100] [OK/!!/XX]                  :
:  [phase 5]:      [X/100] [OK/!!/XX]                  :
:  [phase 6]:      [X/100] [OK/!!/XX]                  :
:                                                       :
+======================================================+
:  ACTIONS TAKEN (Auto-Healed):                         :
:  [numbered list]                                      :
+======================================================+
:  ISSUES FOUND (Needs Human):                          :
:  [numbered list, severity-ordered]                    :
+======================================================+
:  RECOMMENDED NEXT STEPS:                              :
:  [prioritized action items]                           :
+======================================================+
:  QUERY YOUR REGISTRY:                                 :
:  python ~/.repo-doctor/repo-registry.py dashboard     :
:  python ~/.repo-doctor/repo-registry.py status        :
:  python ~/.repo-doctor/repo-registry.py search X      :
+======================================================+
```

---

## SCORING GUIDE

| Score | Meaning |
|-------|---------|
| 90-100 | Excellent -- no significant issues |
| 75-89  | Good -- minor issues only |
| 60-74  | Fair -- several issues need attention |
| 40-59  | Poor -- significant problems found |
| 0-39   | Critical -- major intervention needed |

**Overall Score** = weighted average. Weights vary by type:

**CODEBASE:** Security 25%, Quality 20%, Build 20%, Dependencies 15%, Docs 10%, Config 10%
**LEGAL:** Completeness 30%, Organization 25%, Quality 20%, Security 15%, Documentation 10%
**SCHOOL:** Quality 30%, Completeness 25%, Organization 20%, Documentation 15%, Health 10%
**BUSINESS:** Completeness 25%, Organization 25%, Quality 20%, Security 15%, Documentation 15%

---

## RULES OF ENGAGEMENT

1. **Detect first** -- ALWAYS run Phase 0 detection before anything else. Do not assume it's code.
2. **Adapt completely** -- Use the track that matches. A legal folder gets legal phases, not lint checks.
3. **Be methodical** -- Work through phases in order within your track.
4. **Verify before healing** -- Confirm issues exist before fixing.
5. **Safe fixes only** -- Only auto-fix with >95% confidence.
6. **Preserve intent** -- Never change content, meaning, or decisions. Fix organization, not substance.
7. **Show your work** -- Explain every finding and fix.
8. **No destructive changes** -- Never delete files. Suggest moves/renames but don't execute without approval.
9. **Respect privacy** -- If you encounter sensitive personal, medical, financial, or privileged legal information, note its EXISTENCE but never reproduce its contents in reports.
10. **ALWAYS write to registry** -- The final phase is mandatory. Every project gets tracked.
11. **Time-box** -- If a phase is too large, note what was checked vs skipped.
12. **Be useful** -- Generate indexes, timelines, summaries, and checklists that the person will actually use.
