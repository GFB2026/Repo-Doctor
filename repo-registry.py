#!/usr/bin/env python3
"""
repo-registry.py - Central registry for all audited projects.

Usage:
    python repo-registry.py init                          # Initialize the database
    python repo-registry.py register <path> <name>        # Register a new project
    python repo-registry.py audit <name> --json <file>    # Log an audit result
    python repo-registry.py status [name]                 # Show project status
    python repo-registry.py dashboard                     # Portfolio dashboard
    python repo-registry.py actions                       # All open issues, all projects
    python repo-registry.py diff <name>                   # Compare last 2 audits
    python repo-registry.py stale [days]                  # Find neglected projects
    python repo-registry.py overlap                       # Shared tech across projects
    python repo-registry.py brief <name>                  # One-page project brief
    python repo-registry.py portfolio [--sort score]      # Business intelligence view
    python repo-registry.py value <name> --revenue X      # Tag business context
    python repo-registry.py search <query>                # Search by stack/name/tag
    python repo-registry.py history <name>                # Audit history
    python repo-registry.py tags <name> <tag1> <tag2>     # Add tags
    python repo-registry.py note <name> "note text"       # Add a note
    python repo-registry.py relate <src> <tgt> <rel>      # Link two projects
    python repo-registry.py export [--format json|csv]    # Export full registry
    python repo-registry.py brief-export <name>           # Export brief to markdown
    python repo-registry.py remove <name>                 # Deactivate a project
"""

import sqlite3
import json
import os
import sys
import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

# ─── Configuration ────────────────────────────────────────────────────────────

DB_DIR = Path.home() / ".repo-doctor"
DB_PATH = DB_DIR / "registry.db"

# ─── Database Schema ─────────────────────────────────────────────────────────

SCHEMA = """
-- Core repository table
CREATE TABLE IF NOT EXISTS repos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT UNIQUE NOT NULL,
    path            TEXT,
    remote_url      TEXT,
    description     TEXT,
    primary_language TEXT,
    stack           TEXT,           -- JSON array of technologies
    architecture    TEXT,           -- monolith, monorepo, microservices, library, CLI, etc.
    entry_points    TEXT,           -- JSON array
    build_system    TEXT,
    test_framework  TEXT,
    ci_cd           TEXT,
    tags            TEXT,           -- JSON array of user tags
    first_seen      TEXT NOT NULL,
    last_audited    TEXT,
    is_active       INTEGER DEFAULT 1
);

-- Audit results over time
CREATE TABLE IF NOT EXISTS audits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id         INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    audit_date      TEXT NOT NULL,
    overall_score   INTEGER,        -- 0-100
    dep_score       INTEGER,        -- Phase 1: Dependencies
    quality_score   INTEGER,        -- Phase 2: Code Quality
    security_score  INTEGER,        -- Phase 3: Security
    build_score     INTEGER,        -- Phase 4: Build & Runtime
    docs_score      INTEGER,        -- Phase 5: Documentation
    config_score    INTEGER,        -- Phase 6: Configuration
    summary         TEXT,           -- Free-text summary
    raw_report      TEXT,           -- Full JSON report data
    auto_healed     TEXT,           -- JSON array of actions taken
    needs_human     TEXT,           -- JSON array of flagged issues
    git_commit      TEXT,           -- HEAD commit hash at audit time
    git_branch      TEXT            -- Active branch at audit time
);

-- Individual issues found during audits
CREATE TABLE IF NOT EXISTS issues (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id        INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    repo_id         INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    phase           TEXT NOT NULL,   -- dependency, quality, security, build, docs, config
    severity        TEXT NOT NULL,   -- critical, high, medium, low, info
    category        TEXT,            -- e.g., "unused_dependency", "hardcoded_secret", "no_tests"
    title           TEXT NOT NULL,
    description     TEXT,
    file_path       TEXT,
    line_number     INTEGER,
    auto_fixed      INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'open'  -- open, fixed, wontfix, deferred
);

-- Files inventory per repo (snapshot at audit time)
CREATE TABLE IF NOT EXISTS file_index (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id         INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    audit_id        INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    file_path       TEXT NOT NULL,
    file_type       TEXT,            -- extension
    language        TEXT,
    line_count      INTEGER,
    size_bytes      INTEGER,
    last_modified   TEXT
);

-- Dependencies inventory per repo
CREATE TABLE IF NOT EXISTS dependencies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id         INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    audit_id        INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    version_spec    TEXT,            -- What's in the manifest
    version_locked  TEXT,            -- What's in the lock file
    latest_version  TEXT,
    dep_type        TEXT,            -- production, dev, peer, optional
    ecosystem       TEXT,            -- npm, pypi, cargo, go, rubygems, maven
    is_outdated     INTEGER DEFAULT 0,
    has_vulnerability INTEGER DEFAULT 0,
    vuln_severity   TEXT
);

-- User notes / context about repos
CREATE TABLE IF NOT EXISTS notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id         INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    created_at      TEXT NOT NULL,
    note            TEXT NOT NULL
);

-- Cross-repo relationships
CREATE TABLE IF NOT EXISTS repo_relationships (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_repo_id  INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    target_repo_id  INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    relationship    TEXT NOT NULL,   -- depends_on, fork_of, related_to, deploys_to
    notes           TEXT
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_audits_repo ON audits(repo_id);
CREATE INDEX IF NOT EXISTS idx_audits_date ON audits(audit_date);
CREATE INDEX IF NOT EXISTS idx_issues_repo ON issues(repo_id);
CREATE INDEX IF NOT EXISTS idx_issues_severity ON issues(severity);
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_deps_repo ON dependencies(repo_id);
CREATE INDEX IF NOT EXISTS idx_files_repo ON file_index(repo_id);
CREATE INDEX IF NOT EXISTS idx_notes_repo ON notes(repo_id);

-- Views for common queries
CREATE VIEW IF NOT EXISTS v_repo_latest_audit AS
SELECT r.*, a.audit_date as last_audit_date, a.overall_score,
       a.dep_score, a.quality_score, a.security_score,
       a.build_score, a.docs_score, a.config_score
FROM repos r
LEFT JOIN audits a ON a.repo_id = r.id
    AND a.audit_date = (SELECT MAX(audit_date) FROM audits WHERE repo_id = r.id);

CREATE VIEW IF NOT EXISTS v_open_issues AS
SELECT i.*, r.name as repo_name
FROM issues i
JOIN repos r ON r.id = i.repo_id
WHERE i.status = 'open'
ORDER BY
    CASE i.severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
        ELSE 5
    END;
"""

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_db():
    """Get a database connection, creating the DB if needed."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


from contextlib import contextmanager

@contextmanager
def db_session(schema=None):
    """Context manager for DB connections: connect, init schema, commit/rollback, close."""
    conn = get_db()
    if schema:
        conn.executescript(schema)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def json_dumps(obj):
    return json.dumps(obj, indent=2) if obj else None


def json_loads(s):
    if s is None:
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return s


def score_color(score):
    """Return text indicator for a score."""
    if score is None:
        return " "
    if score >= 80:
        return "OK"
    if score >= 60:
        return "!!"
    if score >= 40:
        return "**"
    return "XX"


# Score dimension mapping: (display_label, db_column)
SCORE_DIMS = [
    ("Dep",   "dep_score"),
    ("Qual",  "quality_score"),
    ("Sec",   "security_score"),
    ("Build", "build_score"),
    ("Docs",  "docs_score"),
    ("Cfg",   "config_score"),
]


def fmt_score(score):
    """Format a single score with its color indicator."""
    return f"{score_color(score)} {score or '-'}"


def fmt_stack(stack_json, max_items=3):
    """Format a JSON stack array for display."""
    stack = json_loads(stack_json)
    if not stack:
        return "-"
    result = ", ".join(stack[:max_items])
    if len(stack) > max_items:
        result += "..."
    return result


def require_repo(conn, name, fields="id"):
    """Look up a repo by name, printing an error if not found. Returns row or None."""
    row = conn.execute(f"SELECT {fields} FROM repos WHERE name = ?", (name,)).fetchone()
    if not row:
        print(f"[ERROR] Repo '{name}' not found.")
    return row


def print_table(headers, rows, col_widths=None):
    """Print a formatted ASCII table."""
    if not col_widths:
        col_widths = []
        for i, h in enumerate(headers):
            max_w = len(str(h))
            for r in rows:
                max_w = max(max_w, len(str(r[i])) if i < len(r) else 0)
            col_widths.append(min(max_w + 2, 50))

    header_line = "|".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
    sep_line = "+".join("-" * w for w in col_widths)

    print(f"+{'+'.join('-' * w for w in col_widths)}+")
    print(f"|{header_line}|")
    print(f"+{sep_line}+")
    for row in rows:
        cells = []
        for i, w in enumerate(col_widths):
            val = str(row[i]) if i < len(row) else ""
            cells.append(val[:w].ljust(w))
        print(f"|{'|'.join(cells)}|")
    print(f"+{'+'.join('-' * w for w in col_widths)}+")


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_init():
    """Initialize the database."""
    with db_session(SCHEMA):
        pass
    print(f"[OK] Registry initialized at {DB_PATH}")


def cmd_register(path, name, remote_url=None, description=None):
    """Register a new repository."""
    with db_session(SCHEMA) as conn:
        try:
            conn.execute(
                """INSERT INTO repos (name, path, remote_url, description, first_seen)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, str(Path(path).resolve()), remote_url, description, now_iso())
            )
            conn.commit()
            print(f"[OK] Registered repo: {name} -> {path}")
        except sqlite3.IntegrityError:
            conn.execute(
                "UPDATE repos SET path = ?, remote_url = COALESCE(?, remote_url) WHERE name = ?",
                (str(Path(path).resolve()), remote_url, name)
            )
            print(f"[UPDATE] Updated existing repo: {name} -> {path}")


def _score(scores, *keys):
    """Return the first non-None score from a list of field name aliases."""
    for k in keys:
        v = scores.get(k)
        if v is not None:
            return v
    return None


def cmd_audit(name, json_file=None, json_data=None):
    """Log an audit result for a repo."""
    with db_session(SCHEMA) as conn:
        repo = require_repo(conn, name)
        if not repo:
            return

        repo_id = repo["id"]

        # Load audit data — from file, raw string/dict, or stdin
        if json_file:
            with open(json_file) as f:
                data = json.load(f)
        elif json_data:
            data = json.loads(json_data) if isinstance(json_data, str) else json_data
        elif not sys.stdin.isatty():
            raw = sys.stdin.read().strip()
            if not raw:
                print("[ERROR] No JSON data on stdin")
                return
            # Extract JSON from Claude output — find first { ... last }
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1:
                print("[ERROR] No JSON object found in stdin")
                return
            data = json.loads(raw[start:end + 1])
        else:
            print("[ERROR] Provide --json <file> or pipe JSON via stdin")
            return

        # Score field aliasing — accept both codebase and non-codebase field names
        # Codebase:    dependencies, quality, security, build, docs, config
        # Non-code:    completeness, quality, security, health, documentation, organization
        scores = data.get("scores", {})

        # Insert audit record
        audit_id = conn.execute(
            """INSERT INTO audits
               (repo_id, audit_date, overall_score, dep_score, quality_score,
                security_score, build_score, docs_score, config_score,
                summary, raw_report, auto_healed, needs_human, git_commit, git_branch)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                repo_id, now_iso(),
                data.get("overall_score"),
                _score(scores, "dependencies", "completeness", "dep"),
                _score(scores, "quality"),
                _score(scores, "security"),
                _score(scores, "build", "health"),
                _score(scores, "docs", "documentation"),
                _score(scores, "config", "organization"),
                data.get("summary"),
                json_dumps(data),
                json_dumps(data.get("auto_healed", [])),
                json_dumps(data.get("needs_human", [])),
                data.get("git_commit"),
                data.get("git_branch"),
            )
        ).lastrowid

        # Update repo metadata
        meta = data.get("meta", {})
        conn.execute(
            """UPDATE repos SET
                primary_language = COALESCE(?, primary_language),
                stack = COALESCE(?, stack),
                architecture = COALESCE(?, architecture),
                entry_points = COALESCE(?, entry_points),
                build_system = COALESCE(?, build_system),
                test_framework = COALESCE(?, test_framework),
                ci_cd = COALESCE(?, ci_cd),
                last_audited = ?
               WHERE id = ?""",
            (
                meta.get("primary_language"),
                json_dumps(meta.get("stack")),
                meta.get("architecture"),
                json_dumps(meta.get("entry_points")),
                meta.get("build_system"),
                meta.get("test_framework"),
                meta.get("ci_cd"),
                now_iso(),
                repo_id,
            )
        )

        # Batch insert issues
        issues_data = [
            (audit_id, repo_id, issue.get("phase", "unknown"),
             issue.get("severity", "info"), issue.get("category"),
             issue.get("title", "Untitled issue"), issue.get("description"),
             issue.get("file_path"), issue.get("line_number"),
             1 if issue.get("auto_fixed") else 0)
            for issue in data.get("issues", [])
        ]
        if issues_data:
            conn.executemany(
                """INSERT INTO issues
                   (audit_id, repo_id, phase, severity, category, title,
                    description, file_path, line_number, auto_fixed)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                issues_data
            )

        # Batch insert dependencies
        deps_data = [
            (repo_id, audit_id, dep.get("name"), dep.get("version_spec"),
             dep.get("version_locked"), dep.get("latest_version"),
             dep.get("dep_type", "production"), dep.get("ecosystem"),
             1 if dep.get("is_outdated") else 0,
             1 if dep.get("has_vulnerability") else 0, dep.get("vuln_severity"))
            for dep in data.get("dependencies", [])
        ]
        if deps_data:
            conn.executemany(
                """INSERT INTO dependencies
                   (repo_id, audit_id, name, version_spec, version_locked,
                    latest_version, dep_type, ecosystem, is_outdated, has_vulnerability, vuln_severity)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                deps_data
            )

        # Batch insert file index
        files_data = [
            (repo_id, audit_id, f.get("path"), f.get("type"),
             f.get("language"), f.get("lines"), f.get("size"))
            for f in data.get("files", [])
        ]
        if files_data:
            conn.executemany(
                """INSERT INTO file_index
                   (repo_id, audit_id, file_path, file_type, language, line_count, size_bytes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                files_data
            )

    score = data.get("overall_score", "?")
    print(f"[OK] Audit logged for {name} - Score: {score}/100 (audit #{audit_id})")


def cmd_status(name=None):
    """Show status of one or all repos."""
    with db_session(SCHEMA) as conn:
        if name:
            rows = conn.execute(
                "SELECT * FROM v_repo_latest_audit WHERE name = ?", (name,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM v_repo_latest_audit WHERE is_active = 1 ORDER BY name"
            ).fetchall()

        if not rows:
            print("No repos found." if not name else f"Repo '{name}' not found.")
            return

        headers = ["Name", "Stack", "Score"] + [d[0] for d in SCORE_DIMS] + ["Last Audit"]
        table_rows = []
        for r in rows:
            table_rows.append([
                r["name"],
                fmt_stack(r["stack"]),
                fmt_score(r["overall_score"]),
                *[fmt_score(r[col]) for _, col in SCORE_DIMS],
                (r["last_audit_date"] or "never")[:10],
            ])

        print_table(headers, table_rows)

        if name and rows:
            repo_id = rows[0]["id"]
            issue_counts = conn.execute(
                """SELECT severity, COUNT(*) as cnt FROM issues
                   WHERE repo_id = ? AND status = 'open'
                   GROUP BY severity ORDER BY
                   CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                   WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5 END""",
                (repo_id,)
            ).fetchall()
            if issue_counts:
                print(f"\n  Open Issues:")
                for ic in issue_counts:
                    print(f"    {ic['severity'].upper():>10}: {ic['cnt']}")


def cmd_search(query):
    """Search repos by name, stack, tags, or description."""
    with db_session(SCHEMA) as conn:
        q = f"%{query}%"
        rows = conn.execute(
            """SELECT * FROM v_repo_latest_audit
               WHERE name LIKE ? OR stack LIKE ? OR tags LIKE ?
                     OR description LIKE ? OR primary_language LIKE ?
                     OR architecture LIKE ?""",
            (q, q, q, q, q, q)
        ).fetchall()

        if not rows:
            print(f"No repos matching '{query}'")
            return

        headers = ["Name", "Language", "Stack", "Score", "Architecture"]
        table_rows = []
        for r in rows:
            table_rows.append([
                r["name"],
                r["primary_language"] or "-",
                fmt_stack(r["stack"], max_items=4),
                fmt_score(r["overall_score"]),
                r["architecture"] or "-",
            ])
        print_table(headers, table_rows)


def cmd_history(name):
    """Show audit history for a repo."""
    with db_session(SCHEMA) as conn:
        repo = require_repo(conn, name)
        if not repo:
            return

        audits = conn.execute(
            """SELECT id, audit_date, overall_score, dep_score, quality_score,
                      security_score, build_score, docs_score, config_score,
                      git_branch, git_commit
               FROM audits WHERE repo_id = ? ORDER BY audit_date DESC""",
            (repo["id"],)
        ).fetchall()

        if not audits:
            print(f"No audits recorded for '{name}'")
            return

        print(f"\n  Audit History: {name}")
        print(f"  {'=' * 70}")

        headers = ["#", "Date", "Score"] + [d[0] for d in SCORE_DIMS] + ["Branch"]
        table_rows = []
        for a in audits:
            table_rows.append([
                a["id"],
                a["audit_date"][:10],
                fmt_score(a["overall_score"]),
                *[a[col] or "-" for _, col in SCORE_DIMS],
                a["git_branch"] or "-",
            ])

        print_table(headers, table_rows)


def cmd_export(fmt="json"):
    """Export the full registry."""
    with db_session(SCHEMA) as conn:
        repos = conn.execute("SELECT * FROM v_repo_latest_audit").fetchall()
        all_issues = conn.execute("SELECT * FROM v_open_issues").fetchall()

        if fmt == "json":
            output = {
                "exported_at": now_iso(),
                "repos": [dict(r) for r in repos],
                "open_issues": [dict(i) for i in all_issues],
            }
            print(json.dumps(output, indent=2, default=str))

        elif fmt == "csv":
            buf = io.StringIO()
            writer = csv.writer(buf)
            if repos:
                writer.writerow(repos[0].keys())
                for r in repos:
                    writer.writerow(list(r))
            print(buf.getvalue())


def cmd_dashboard():
    """Print a summary dashboard."""
    with db_session(SCHEMA) as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM repos WHERE is_active = 1").fetchone()["c"]
        audited = conn.execute("SELECT COUNT(*) as c FROM repos WHERE last_audited IS NOT NULL AND is_active = 1").fetchone()["c"]
        avg_score = conn.execute("SELECT AVG(overall_score) as avg FROM v_repo_latest_audit WHERE overall_score IS NOT NULL").fetchone()["avg"]

        issue_summary = conn.execute(
            """SELECT severity, COUNT(*) as cnt FROM issues
               WHERE status = 'open'
               GROUP BY severity"""
        ).fetchall()

        stack_summary = conn.execute(
            """SELECT primary_language, COUNT(*) as cnt FROM repos
               WHERE is_active = 1 AND primary_language IS NOT NULL
               GROUP BY primary_language ORDER BY cnt DESC LIMIT 10"""
        ).fetchall()

        recent_audits = conn.execute(
            """SELECT r.name, a.audit_date, a.overall_score
               FROM audits a JOIN repos r ON r.id = a.repo_id
               ORDER BY a.audit_date DESC LIMIT 5"""
        ).fetchall()

        print(dedent(f"""
        +==================================================+
        :          REPO REGISTRY -- DASHBOARD               :
        +==================================================+
        :  Total Repos:     {total:<30}:
        :  Audited:         {audited:<30}:
        :  Avg Health:      {f'{avg_score:.0f}/100' if avg_score else 'N/A':<30}:
        +==================================================+
        :  OPEN ISSUES                                      :"""))

        for iss in issue_summary:
            sev = iss["severity"].upper()
            cnt = iss["cnt"]
            print(f"    :  {sev:>12}: {cnt:<33}:")

        print("    +==================================================+")
        print("    :  LANGUAGES                                        :")
        for s in stack_summary:
            print(f"    :  {s['primary_language']:>12}: {s['cnt']:<33}:")

        print("    +==================================================+")
        print("    :  RECENT AUDITS                                    :")
        for ra in recent_audits:
            score_str = fmt_score(ra['overall_score'])
            print(f"    :  {ra['name'][:20]:<20} {ra['audit_date'][:10]}  {score_str:<12}:")

        print("    +==================================================+")


def cmd_tags(name, tags):
    """Add tags to a repo."""
    with db_session(SCHEMA) as conn:
        repo = require_repo(conn, name, "id, tags")
        if not repo:
            return
        existing = json_loads(repo["tags"]) or []
        merged = list(set(existing + tags))
        conn.execute("UPDATE repos SET tags = ? WHERE id = ?", (json_dumps(merged), repo["id"]))
        print(f"[OK] Tags for {name}: {', '.join(merged)}")


def cmd_note(name, note_text):
    """Add a note to a repo."""
    with db_session(SCHEMA) as conn:
        repo = require_repo(conn, name)
        if not repo:
            return
        conn.execute(
            "INSERT INTO notes (repo_id, created_at, note) VALUES (?, ?, ?)",
            (repo["id"], now_iso(), note_text)
        )
        print(f"[OK] Note added to {name}")


def cmd_relate(source, target, relationship, notes=None):
    """Create a relationship between two repos."""
    with db_session(SCHEMA) as conn:
        src = conn.execute("SELECT id FROM repos WHERE name = ?", (source,)).fetchone()
        tgt = conn.execute("SELECT id FROM repos WHERE name = ?", (target,)).fetchone()
        if not src or not tgt:
            print(f"[ERROR] Both repos must exist. Missing: {source if not src else target}")
            return
        conn.execute(
            """INSERT INTO repo_relationships (source_repo_id, target_repo_id, relationship, notes)
               VALUES (?, ?, ?, ?)""",
            (src["id"], tgt["id"], relationship, notes)
        )
        print(f"[OK] {source} -[{relationship}]-> {target}")


def cmd_remove(name):
    """Remove a repo (soft delete)."""
    with db_session(SCHEMA) as conn:
        conn.execute("UPDATE repos SET is_active = 0 WHERE name = ?", (name,))
        print(f"[OK] Repo '{name}' deactivated (data preserved)")


def cmd_actions():
    """Cross-project action items — every open issue, prioritized."""
    with db_session(SCHEMA) as conn:
        issues = conn.execute(
            """SELECT i.severity, i.title, i.phase, i.file_path, i.category,
                      r.name as repo_name, a.audit_date
               FROM issues i
               JOIN repos r ON r.id = i.repo_id
               JOIN audits a ON a.id = i.audit_id
               WHERE i.status = 'open' AND i.auto_fixed = 0
               ORDER BY
                   CASE i.severity
                       WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                       WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5
                   END,
                   a.audit_date DESC"""
        ).fetchall()

        if not issues:
            print("  No open action items across any project.")
            return

        print(f"\n  OPEN ACTION ITEMS ACROSS ALL PROJECTS ({len(issues)} total)")
        print(f"  {'=' * 70}")

        current_sev = None
        for idx, iss in enumerate(issues, 1):
            sev = iss["severity"].upper()
            if sev != current_sev:
                current_sev = sev
                marker = {"CRITICAL": "XXX", "HIGH": "!!!", "MEDIUM": "!!", "LOW": "!"}.get(sev, " ")
                print(f"\n  [{marker}] {sev}")
                print(f"  {'-' * 40}")

            loc = f" ({iss['file_path']})" if iss["file_path"] else ""
            print(f"  {idx:>3}. [{iss['repo_name']}] {iss['title']}{loc}")


def cmd_diff(name):
    """Compare last two audits — show what improved and what regressed."""
    with db_session(SCHEMA) as conn:
        repo = require_repo(conn, name)
        if not repo:
            return

        audits = conn.execute(
            """SELECT * FROM audits WHERE repo_id = ?
               ORDER BY audit_date DESC LIMIT 2""",
            (repo["id"],)
        ).fetchall()

        if len(audits) < 2:
            print(f"  Need at least 2 audits for '{name}' to show a diff. Only {len(audits)} found.")
            return

        current, previous = audits[0], audits[1]

        print(f"\n  AUDIT DIFF: {name}")
        print(f"  {previous['audit_date'][:10]}  ->  {current['audit_date'][:10]}")
        print(f"  {'=' * 50}")

        diff_fields = [("Overall", "overall_score")] + [(label, col) for label, col in
                       [("Dependencies", "dep_score"), ("Quality", "quality_score"),
                        ("Security", "security_score"), ("Build", "build_score"),
                        ("Docs", "docs_score"), ("Config", "config_score")]]

        for label, field in diff_fields:
            old_val = previous[field]
            new_val = current[field]
            if old_val is not None and new_val is not None:
                delta = new_val - old_val
                arrow = f"+{delta} ^" if delta > 0 else (f"{delta} v" if delta < 0 else "  =")
                print(f"  {label:<15} {old_val:>3} -> {new_val:>3}  {arrow}")
            else:
                print(f"  {label:<15} {'?':>3} -> {'?':>3}")

        # Issue counts — single query for both audits
        counts = conn.execute(
            """SELECT audit_id,
                      SUM(CASE WHEN auto_fixed = 0 THEN 1 ELSE 0 END) as unfixed,
                      SUM(CASE WHEN auto_fixed = 1 THEN 1 ELSE 0 END) as fixed
               FROM issues WHERE audit_id IN (?, ?) GROUP BY audit_id""",
            (previous["id"], current["id"])
        ).fetchall()
        count_map = {r["audit_id"]: (r["unfixed"], r["fixed"]) for r in counts}
        old_unfixed, old_fixed = count_map.get(previous["id"], (0, 0))
        new_unfixed, new_fixed = count_map.get(current["id"], (0, 0))

        print(f"\n  Issues (unfixed):  {old_unfixed} -> {new_unfixed}")
        print(f"  Auto-healed:       {old_fixed} -> {new_fixed}")


def cmd_stale(days=30):
    """Find projects that haven't been audited recently or ever."""
    with db_session(SCHEMA) as conn:
        never = conn.execute(
            "SELECT name, path, first_seen FROM repos WHERE last_audited IS NULL AND is_active = 1"
        ).fetchall()

        old = conn.execute(
            """SELECT r.name, r.path, r.last_audited, a.overall_score
                FROM repos r
                LEFT JOIN audits a ON a.repo_id = r.id
                    AND a.audit_date = (SELECT MAX(audit_date) FROM audits WHERE repo_id = r.id)
                WHERE r.is_active = 1 AND r.last_audited IS NOT NULL
                    AND julianday('now') - julianday(r.last_audited) > ?
                ORDER BY r.last_audited ASC""",
            (days,)
        ).fetchall()

        low = conn.execute(
            """SELECT r.name, a.overall_score, a.audit_date
               FROM repos r
               JOIN audits a ON a.repo_id = r.id
                   AND a.audit_date = (SELECT MAX(audit_date) FROM audits WHERE repo_id = r.id)
               WHERE r.is_active = 1 AND a.overall_score < 60
               ORDER BY a.overall_score ASC"""
        ).fetchall()

        print(f"\n  PROJECT ATTENTION NEEDED")
        print(f"  {'=' * 50}")

        if never:
            print(f"\n  NEVER AUDITED ({len(never)}):")
            for r in never:
                print(f"    - {r['name']:<25} registered {r['first_seen'][:10]}")

        if old:
            print(f"\n  STALE (>{days} days since last audit) ({len(old)}):")
            for r in old:
                score = fmt_score(r['overall_score']) if r['overall_score'] else "n/a"
                print(f"    - {r['name']:<25} last audited {r['last_audited'][:10]}  score: {score}")

        if low:
            print(f"\n  LOW HEALTH (score < 60) ({len(low)}):")
            for r in low:
                print(f"    - {r['name']:<25} score: {r['overall_score']}  ({r['audit_date'][:10]})")

        if not never and not old and not low:
            print("\n  Everything looks good. No projects need immediate attention.")


def cmd_overlap():
    """Find shared technologies and dependencies across projects."""
    with db_session(SCHEMA) as conn:
        repos = conn.execute(
            "SELECT name, stack FROM repos WHERE is_active = 1 AND stack IS NOT NULL"
        ).fetchall()

        tech_map = {}
        for r in repos:
            stack = json_loads(r["stack"]) or []
            for tech in stack:
                tech_lower = tech.lower().strip()
                tech_map.setdefault(tech_lower, {"display": tech, "repos": []})
                tech_map[tech_lower]["repos"].append(r["name"])

        dep_map = {}
        deps = conn.execute(
            """SELECT d.name as dep_name, d.ecosystem, r.name as repo_name
               FROM dependencies d
               JOIN repos r ON r.id = d.repo_id
               JOIN audits a ON a.id = d.audit_id
                   AND a.audit_date = (SELECT MAX(audit_date) FROM audits WHERE repo_id = d.repo_id)
               WHERE r.is_active = 1"""
        ).fetchall()

        for d in deps:
            key = f"{d['dep_name']} ({d['ecosystem']})" if d["ecosystem"] else d["dep_name"]
            dep_map.setdefault(key, [])
            dep_map[key].append(d["repo_name"])

        print(f"\n  CROSS-PROJECT OVERLAP ANALYSIS")
        print(f"  {'=' * 50}")

        shared_tech = {k: v for k, v in tech_map.items() if len(v["repos"]) > 1}
        if shared_tech:
            print(f"\n  SHARED TECHNOLOGIES ({len(shared_tech)}):")
            for key in sorted(shared_tech, key=lambda k: len(tech_map[k]["repos"]), reverse=True):
                info = tech_map[key]
                print(f"    {info['display']:<25} -> {', '.join(info['repos'])}")

        unique_tech = {k: v for k, v in tech_map.items() if len(v["repos"]) == 1}
        if unique_tech:
            print(f"\n  UNIQUE TECHNOLOGIES ({len(unique_tech)}):")
            for key in sorted(unique_tech):
                info = tech_map[key]
                print(f"    {info['display']:<25} -> {info['repos'][0]}")

        shared_deps = {k: v for k, v in dep_map.items() if len(v) > 1}
        if shared_deps:
            print(f"\n  SHARED DEPENDENCIES ({len(shared_deps)}):")
            for dep in sorted(shared_deps, key=lambda k: len(dep_map[k]), reverse=True):
                print(f"    {dep:<30} -> {', '.join(dep_map[dep])}")


def cmd_brief(name):
    """Generate a one-page project brief from registry data."""
    with db_session(SCHEMA) as conn:
        repo = conn.execute(
            "SELECT * FROM v_repo_latest_audit WHERE name = ?", (name,)
        ).fetchone()

        if not repo:
            print(f"[ERROR] Project '{name}' not found.")
            return

        audit = conn.execute(
            """SELECT * FROM audits WHERE repo_id = ?
               ORDER BY audit_date DESC LIMIT 1""",
            (repo["id"],)
        ).fetchone()

        issues = conn.execute(
            """SELECT severity, COUNT(*) as cnt FROM issues
               WHERE repo_id = ? AND status = 'open' AND auto_fixed = 0
               GROUP BY severity
               ORDER BY CASE severity
                   WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                   WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5 END""",
            (repo["id"],)
        ).fetchall()

        critical = conn.execute(
            """SELECT title, file_path FROM issues
               WHERE repo_id = ? AND status = 'open' AND severity IN ('critical', 'high')
               AND auto_fixed = 0 LIMIT 5""",
            (repo["id"],)
        ).fetchall()

        notes = conn.execute(
            "SELECT note, created_at FROM notes WHERE repo_id = ? ORDER BY created_at DESC LIMIT 3",
            (repo["id"],)
        ).fetchall()

        rels = conn.execute(
            """SELECT r2.name, rr.relationship, rr.notes
               FROM repo_relationships rr
               JOIN repos r2 ON r2.id = rr.target_repo_id
               WHERE rr.source_repo_id = ?
               UNION
               SELECT r2.name, rr.relationship, rr.notes
               FROM repo_relationships rr
               JOIN repos r2 ON r2.id = rr.source_repo_id
               WHERE rr.target_repo_id = ?""",
            (repo["id"], repo["id"])
        ).fetchall()

        audit_count = conn.execute(
            "SELECT COUNT(*) as c FROM audits WHERE repo_id = ?", (repo["id"],)
        ).fetchone()["c"]

        healed = json_loads(audit["auto_healed"]) if audit and audit["auto_healed"] else []
        needs_human = json_loads(audit["needs_human"]) if audit and audit["needs_human"] else []
        tags = json_loads(repo["tags"]) or []

        print(f"""
  +{'=' * 58}+
  : PROJECT BRIEF: {name:<40} :
  +{'=' * 58}+

  Type:          {repo['architecture'] or 'Unknown'}
  Language:      {repo['primary_language'] or 'Unknown'}
  Stack:         {fmt_stack(repo['stack'], max_items=5)}
  Path:          {repo['path'] or 'Unknown'}
  Remote:        {repo['remote_url'] or 'None'}
  Tags:          {', '.join(tags) if tags else 'None'}
  First Seen:    {repo['first_seen'][:10] if repo['first_seen'] else 'Unknown'}
  Last Audited:  {repo['last_audited'][:10] if repo['last_audited'] else 'Never'}
  Total Audits:  {audit_count}""")

        if audit:
            os_ = repo["overall_score"]
            print(f"\n  HEALTH: {os_}/100 {score_color(os_)}")
            for label, col in [("Dependencies", "dep_score"), ("Quality", "quality_score"),
                               ("Security", "security_score"), ("Build", "build_score"),
                               ("Docs", "docs_score"), ("Config", "config_score")]:
                print(f"    {label + ':':<15} {repo[col] or '?'}")

        if issues:
            print(f"\n  OPEN ISSUES:")
            for iss in issues:
                print(f"    {iss['severity'].upper()}: {iss['cnt']}")

        if critical:
            print(f"\n  TOP PRIORITIES:")
            for c in critical:
                loc = f" ({c['file_path']})" if c["file_path"] else ""
                print(f"    - {c['title']}{loc}")

        if healed:
            print(f"\n  LAST AUTO-HEALED ({len(healed)}):")
            for h in healed[:5]:
                print(f"    - {h}")

        if needs_human:
            print(f"\n  NEEDS ATTENTION ({len(needs_human)}):")
            for n in needs_human[:5]:
                print(f"    - {n}")

        if rels:
            print(f"\n  RELATED PROJECTS:")
            for rel in rels:
                print(f"    {rel['relationship']} -> {rel['name']}" +
                      (f" ({rel['notes']})" if rel["notes"] else ""))

        if notes:
            print(f"\n  RECENT NOTES:")
            for n in notes:
                print(f"    [{n['created_at'][:10]}] {n['note']}")

        if audit and audit["summary"]:
            print(f"\n  SUMMARY: {audit['summary']}")

        print(f"\n  +{'=' * 58}+")


def cmd_portfolio(sort_by="score"):
    """Business intelligence view — projects ranked by value/health."""
    with db_session(SCHEMA) as conn:
        if sort_by == "health":
            order = "a.overall_score ASC"
        elif sort_by == "recent":
            order = "r.last_audited DESC"
        else:
            order = "a.overall_score DESC"

        # Single query with LEFT JOINs to pre-aggregated subqueries (fixes N+1)
        rows = conn.execute(
            f"""SELECT r.name, r.primary_language, r.architecture, r.tags,
                       a.overall_score, a.security_score, a.audit_date,
                       COALESCE(ic.open_issues, 0) as open_issues,
                       COALESCE(ic.critical_issues, 0) as critical_issues,
                       COALESCE(ac.audit_count, 0) as audit_count
                FROM repos r
                LEFT JOIN audits a ON a.repo_id = r.id
                    AND a.audit_date = (SELECT MAX(audit_date) FROM audits WHERE repo_id = r.id)
                LEFT JOIN (
                    SELECT repo_id,
                           SUM(CASE WHEN status='open' AND auto_fixed=0 THEN 1 ELSE 0 END) as open_issues,
                           SUM(CASE WHEN severity IN ('critical','high') AND status='open' THEN 1 ELSE 0 END) as critical_issues
                    FROM issues GROUP BY repo_id
                ) ic ON ic.repo_id = r.id
                LEFT JOIN (
                    SELECT repo_id, COUNT(*) as audit_count FROM audits GROUP BY repo_id
                ) ac ON ac.repo_id = r.id
                WHERE r.is_active = 1
                ORDER BY {order}"""
        ).fetchall()

        if not rows:
            print("  No projects in registry.")
            return

        total = len(rows)
        audited = sum(1 for r in rows if r["overall_score"] is not None)
        avg = sum(r["overall_score"] for r in rows if r["overall_score"]) / max(audited, 1)
        total_issues = sum(r["open_issues"] for r in rows)
        total_critical = sum(r["critical_issues"] for r in rows)
        total_audits = sum(r["audit_count"] for r in rows)

        print(f"""
  +{'=' * 58}+
  : PORTFOLIO OVERVIEW                                     :
  +{'=' * 58}+
  : Projects: {total:<5}  Audited: {audited:<5}  Total Audits: {total_audits:<5}  :
  : Avg Health: {avg:.0f}/100    Open Issues: {total_issues:<4} Critical: {total_critical:<4}:
  +{'=' * 58}+
""")

        headers = ["Project", "Type", "Score", "Sec", "Issues", "Crit", "Audits", "Last Audit"]
        table_rows = []
        for r in rows:
            tags = json_loads(r["tags"])
            tag_str = f" [{','.join(tags[:2])}]" if tags else ""
            table_rows.append([
                (r["name"] + tag_str)[:30],
                (r["architecture"] or r["primary_language"] or "?")[:12],
                fmt_score(r["overall_score"]),
                fmt_score(r["security_score"]),
                str(r["open_issues"]),
                str(r["critical_issues"]) if r["critical_issues"] else "-",
                str(r["audit_count"]),
                (r["audit_date"] or "never")[:10],
            ])

        print_table(headers, table_rows)

        at_risk = [r for r in rows if r["overall_score"] and r["overall_score"] < 60]
        if at_risk:
            print(f"\n  AT RISK ({len(at_risk)}):")
            for r in at_risk:
                print(f"    {score_color(r['overall_score'])} {r['name']}: {r['overall_score']}/100 - {r['critical_issues']} critical issues")


def cmd_value(name, revenue=None, client=None, priority=None):
    """Tag a project with business context — revenue, client, priority."""
    with db_session(SCHEMA) as conn:
        repo = require_repo(conn, name, "id, tags")
        if not repo:
            return

        existing_tags = json_loads(repo["tags"]) or []

        # Single-pass: filter out old prefixed tags and append new ones
        updates = {}
        if revenue:
            updates["rev:"] = f"rev:{revenue}"
        if client:
            updates["client:"] = f"client:{client}"
        if priority:
            updates["pri:"] = f"pri:{priority}"

        if updates:
            prefixes = tuple(updates.keys())
            existing_tags = [t for t in existing_tags if not t.startswith(prefixes)]
            existing_tags.extend(updates.values())

        conn.execute("UPDATE repos SET tags = ? WHERE id = ?",
                     (json_dumps(existing_tags), repo["id"]))
        print(f"[OK] Updated {name}: {', '.join(existing_tags)}")


def cmd_brief_export(name):
    """Export project brief to a markdown file."""
    f = io.StringIO()
    from contextlib import redirect_stdout
    with redirect_stdout(f):
        cmd_brief(name)
    brief_text = f.getvalue()
    out_path = Path.home() / ".repo-doctor" / f"{name}-brief.md"
    out_path.write_text(f"```\n{brief_text}\n```\n")
    print(f"[OK] Brief exported to {out_path}")


def cmd_me():
    """Personal development report — analyzes YOU across all projects."""
    # Dimension mapping for single-pass averaging
    DIM_MAP = [
        ("Dependencies",  "dep_score"),
        ("Code Quality",  "quality_score"),
        ("Security",      "security_score"),
        ("Build",         "build_score"),
        ("Documentation", "docs_score"),
        ("Configuration", "config_score"),
    ]

    def compute_dim_averages(audits_list):
        """Single-pass dimension averaging across audits."""
        sums = {col: 0 for _, col in DIM_MAP}
        counts = {col: 0 for _, col in DIM_MAP}
        for a in audits_list:
            for _, col in DIM_MAP:
                val = a[col]
                if val is not None:
                    sums[col] += val
                    counts[col] += 1
        return {label: sums[col] / counts[col] if counts[col] else None
                for label, col in DIM_MAP}

    with db_session(SCHEMA) as conn:
        repos = conn.execute("SELECT * FROM repos WHERE is_active = 1").fetchall()
        if not repos:
            print("  No projects in registry yet. Audit some projects first.")
            return

        audits = conn.execute(
            """SELECT a.*, r.name as repo_name FROM audits a
               JOIN repos r ON r.id = a.repo_id
               ORDER BY a.audit_date ASC"""
        ).fetchall()

        # Get issue counts via SQL aggregation instead of fetching all rows
        open_issue_rows = conn.execute(
            """SELECT i.severity, i.category, i.phase FROM issues i
               JOIN repos r ON r.id = i.repo_id
               WHERE i.status = 'open' AND i.auto_fixed = 0 AND r.is_active = 1"""
        ).fetchall()

        latest_audits = conn.execute(
            """SELECT a.*, r.name as repo_name FROM audits a
               JOIN repos r ON r.id = a.repo_id
               WHERE a.audit_date = (SELECT MAX(audit_date) FROM audits WHERE repo_id = a.repo_id)"""
        ).fetchall()

        total_repos = len(repos)
        audited_repos = sum(1 for r in repos if r["last_audited"])
        total_audits = len(audits)
        never_audited = [r for r in repos if not r["last_audited"]]

        scores = [a["overall_score"] for a in latest_audits if a["overall_score"] is not None]
        avg_score = sum(scores) / len(scores) if scores else 0

        dim_avgs = compute_dim_averages(latest_audits)

        ranked_dims = sorted(
            [(k, v) for k, v in dim_avgs.items() if v is not None],
            key=lambda x: x[1], reverse=True
        )
        strengths = [(k, v) for k, v in ranked_dims if v >= 75]
        weaknesses = [(k, v) for k, v in ranked_dims if v < 65]

        # Single-pass issue pattern counting
        sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        category_counts = {}
        phase_counts = {}
        category_sets = {}  # for blind spot detection
        for i in open_issue_rows:
            sev_counts[i["severity"]] = sev_counts.get(i["severity"], 0) + 1
            cat = i["category"] or "uncategorized"
            category_counts[cat] = category_counts.get(cat, 0) + 1
            ph = i["phase"]
            phase_counts[ph] = phase_counts.get(ph, 0) + 1
            if i["category"]:
                cat_lower = i["category"].lower()
                category_sets.setdefault(cat_lower, 0)
                category_sets[cat_lower] += 1

        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        top_phases = sorted(phase_counts.items(), key=lambda x: x[1], reverse=True)
        total_open = len(open_issue_rows)

        # Tech breadth
        all_languages = set()
        all_tech = set()
        arch_types = set()
        for r in repos:
            if r["primary_language"]:
                all_languages.add(r["primary_language"])
            stack = json_loads(r["stack"]) or []
            for t in stack:
                all_tech.add(t)
            if r["architecture"]:
                arch_types.add(r["architecture"])

        # Evolution tracking
        score_timeline = [(a["audit_date"][:10], a["overall_score"], a["repo_name"])
                          for a in audits if a["overall_score"] is not None]

        improvements = []
        repo_audit_map = {}
        for a in audits:
            if a["overall_score"] is not None:
                repo_audit_map.setdefault(a["repo_name"], []).append(a["overall_score"])
        for rname, scores_list in repo_audit_map.items():
            if len(scores_list) >= 2:
                delta = scores_list[-1] - scores_list[0]
                improvements.append((rname, scores_list[0], scores_list[-1], delta))

        # Data-driven blind spot detection
        sec_avg = dim_avgs.get("Security") or 0
        docs_avg = dim_avgs.get("Documentation") or 0
        build_avg = dim_avgs.get("Build") or 0

        # Count category issues for blind spot checks
        secret_count = sum(v for k, v in category_sets.items() if "secret" in k)
        missing_doc_count = sum(v for k, v in category_sets.items() if "missing_doc" in k)
        test_count = sum(v for k, v in category_sets.items() if "test" in k)

        BLIND_SPOT_RULES = [
            (sec_avg < 60,
             "SECURITY: You consistently score low on security across projects. "
             "This suggests security isn't part of your default workflow. "
             "Consider adding pre-commit secret scanning and making .gitignore "
             "review a first step on every project."),
            (docs_avg < 60,
             "DOCUMENTATION: Your projects consistently lack documentation. "
             "This creates bus-factor risk and slows onboarding. "
             "Try writing the README before writing code — it forces you "
             "to clarify your own thinking."),
            (build_avg < 60,
             "BUILD DISCIPLINE: Projects frequently have build/test issues. "
             "Consider adopting a template with CI/CD pre-configured so every "
             "new project starts with a working pipeline."),
            (secret_count >= 2,
             "SECRETS MANAGEMENT: Multiple projects have exposed secrets. "
             "This is a pattern, not an accident. Set up a secrets manager "
             "(1Password CLI, doppler, or even just a consistent .env.example workflow) "
             "and break the habit."),
            (missing_doc_count >= 3,
             "MISSING STANDARD FILES: Multiple projects lack LICENSE, CHANGELOG, "
             "or CONTRIBUTING files. Create a project starter template with these "
             "pre-populated so you never ship without them."),
            (len(never_audited) >= 2,
             f"UNTRACKED WORK: You have {len(never_audited)} registered projects "
             "that have never been audited. Unaudited projects accumulate hidden debt. "
             "Run the batch crawler to get baselines on everything."),
            (test_count >= 2,
             "TEST COVERAGE: Multiple projects flagged for insufficient testing. "
             "Consider writing tests before features (TDD) or at minimum adding "
             "tests as a PR checklist item."),
            (scores and len(scores) >= 3 and (max(scores) - min(scores)) > 30,
             f"INCONSISTENCY: Your project scores range from {min(scores) if scores else 0} to "
             f"{max(scores) if scores else 0} (a {(max(scores) - min(scores)) if scores and len(scores) >= 3 else 0}-point spread). "
             "This suggests you invest heavily in some projects while neglecting others. "
             "Consider applying the same baseline standards to everything."),
        ]
        blind_spots = [msg for condition, msg in BLIND_SPOT_RULES if condition]

        # Recommendations
        recommendations = []

        crit_count = sev_counts.get("critical", 0) + sev_counts.get("high", 0)
        if crit_count > 0:
            recommendations.append(
                f"FIX {crit_count} CRITICAL/HIGH ISSUES NOW. These are active risks. "
                "Run 'actions' to see the full list, address them before building new features.")

        if weaknesses:
            worst = weaknesses[-1]
            recommendations.append(
                f"LEVEL UP '{worst[0].upper()}' (avg {worst[1]:.0f}/100). This is your weakest area. "
                f"Focus your next project improvement sprint here for maximum score gains.")

        if total_audits < total_repos * 2:
            recommendations.append(
                "RE-AUDIT MORE. Most projects only have 1 audit. Run second passes after fixing "
                "issues to track improvement and build your score history.")

        if never_audited:
            names = ", ".join(r["name"] for r in never_audited[:5])
            recommendations.append(
                f"AUDIT UNTRACKED PROJECTS: {names}. Get baselines on everything so nothing hides.")

        if len(all_languages) >= 4:
            recommendations.append(
                f"LANGUAGE BREADTH ({len(all_languages)} languages). You're spread across many "
                "technologies. Consider whether depth in fewer stacks would serve you better, "
                "or if the breadth is strategic for your consulting work.")
        elif len(all_languages) == 1:
            recommendations.append(
                f"SINGLE LANGUAGE ({list(all_languages)[0]}). All your projects use one language. "
                "This is fine for depth, but consider whether learning a complementary stack "
                "would open new opportunities.")

        tagged_with_value = [r for r in repos
                             if r["tags"] and ("rev:" in (r["tags"] or "") or "client:" in (r["tags"] or ""))]
        if len(tagged_with_value) < len(repos) // 2:
            recommendations.append(
                "TAG BUSINESS CONTEXT. Less than half your projects have revenue/client/priority tags. "
                "Use 'value' command to annotate them — it helps you prioritize where to invest time.")

        if docs_avg < 70:
            recommendations.append(
                "BUILD A DOCS HABIT. Your documentation scores are below average. "
                "Challenge: write a README for every project before the first commit. "
                "If you can't explain it in a README, you don't fully understand it yet.")

        ci_repos = [r for r in repos if r["ci_cd"] and r["ci_cd"].lower() != "none"]
        if len(ci_repos) < audited_repos // 2:
            recommendations.append(
                "ADD CI/CD TO MORE PROJECTS. Less than half have automated pipelines. "
                "Even a basic GitHub Actions workflow for lint + test catches issues before they compound.")

        # Growth trajectory
        trajectory = "NOT ENOUGH DATA"
        if improvements:
            up = sum(1 for i in improvements if i[3] > 0)
            down = sum(1 for i in improvements if i[3] < 0)
            trajectory = "IMPROVING" if up > down else ("DECLINING" if down > up else "STABLE")

        # Print the report
        print(f"""
  +{'=' * 62}+
  :                    PERSONAL DEVELOPMENT REPORT                  :
  +{'=' * 62}+

  PROFILE
  {'=' * 40}
  Projects Managed:    {total_repos}
  Projects Audited:    {audited_repos}
  Total Audits Run:    {total_audits}
  Languages:           {', '.join(sorted(all_languages)) if all_languages else 'Unknown'}
  Technologies:        {len(all_tech)}
  Architectures:       {', '.join(sorted(arch_types)) if arch_types else 'Unknown'}
  Avg Project Health:  {avg_score:.0f}/100
  Growth Trajectory:   {trajectory}""")

        print(f"""
  SKILLS RADAR
  {'=' * 40}""")
        for dim_name, dim_val in ranked_dims:
            bar_len = int((dim_val / 100) * 30) if dim_val else 0
            bar = "#" * bar_len + "." * (30 - bar_len)
            print(f"  {dim_name:<15} [{bar}] {dim_val:.0f} {score_color(dim_val)}")

        if strengths:
            print(f"""
  STRENGTHS
  {'=' * 40}""")
            for s_name, s_val in strengths:
                print(f"  {score_color(s_val)} {s_name}: {s_val:.0f}/100")
            print("  -> These are your reliable areas. Maintain them.")

        if weaknesses:
            print(f"""
  GROWTH AREAS
  {'=' * 40}""")
            for w_name, w_val in weaknesses:
                print(f"  {score_color(w_val)} {w_name}: {w_val:.0f}/100")
            print("  -> Focus here for the biggest improvement gains.")

        if top_categories:
            print(f"""
  RECURRING ISSUE PATTERNS
  {'=' * 40}
  These keep showing up across your projects:""")
            for cat, cnt in top_categories:
                print(f"    {cat.replace('_', ' '):.<35} {cnt}x")

        if top_phases:
            print(f"""
  ISSUES BY PHASE
  {'=' * 40}""")
            for ph, cnt in top_phases:
                pct = (cnt / max(total_open, 1)) * 100
                print(f"    {ph:<20} {cnt:>3} ({pct:.0f}%)")

        if blind_spots:
            print(f"""
  BLIND SPOTS
  {'=' * 40}
  Things you might not realize about your patterns:
""")
            for idx, bs in enumerate(blind_spots, 1):
                print(f"  {idx}. {bs}")
                print()

        if improvements:
            print(f"""
  EVOLUTION TRACKING
  {'=' * 40}
  Projects with multiple audits:""")
            for rname, first, last, delta in improvements:
                arrow = f"+{delta} IMPROVED" if delta > 0 else (f"{delta} REGRESSED" if delta < 0 else "= STABLE")
                print(f"    {rname:<25} {first} -> {last}  ({arrow})")

        if score_timeline and len(score_timeline) >= 3:
            print(f"""
  RECENT AUDIT TIMELINE
  {'=' * 40}""")
            for date, score, rname in score_timeline[-10:]:
                print(f"    {date}  {score_color(score)} {score:>3}  {rname}")

        if recommendations:
            print(f"""
  +{'=' * 62}+
  :                     RECOMMENDATIONS                             :
  +{'=' * 62}+
""")
            for idx, rec in enumerate(recommendations, 1):
                print(f"  {idx}. {rec}")
                print()

        print(f"""
  +{'=' * 62}+
  :  Next: Fix your top action items, re-audit, and run 'me' again :
  :  to track your growth over time.                                :
  +{'=' * 62}+
""")


def cmd_me_export():
    """Export personal report to markdown file."""
    f = io.StringIO()
    from contextlib import redirect_stdout
    with redirect_stdout(f):
        cmd_me()
    report = f.getvalue()
    out_path = Path.home() / ".repo-doctor" / f"personal-report-{datetime.now().strftime('%Y-%m-%d')}.md"
    out_path.write_text(f"```\n{report}\n```\n")
    print(f"[OK] Personal report exported to {out_path}")


# ─── CLI Router ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "init":
        cmd_init()

    elif cmd == "register":
        if len(sys.argv) < 4:
            print("Usage: repo-registry.py register <path> <name> [--remote <url>] [--desc <text>]")
            return
        path, name = sys.argv[2], sys.argv[3]
        remote = sys.argv[sys.argv.index("--remote") + 1] if "--remote" in sys.argv else None
        desc = sys.argv[sys.argv.index("--desc") + 1] if "--desc" in sys.argv else None
        cmd_register(path, name, remote, desc)

    elif cmd == "audit":
        if len(sys.argv) < 3:
            print("Usage: repo-registry.py audit <name> --json <file>")
            print("       echo '{...}' | repo-registry.py audit <name>")
            return
        name = sys.argv[2]
        json_file = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
        cmd_audit(name, json_file=json_file)

    elif cmd == "status":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_status(name)

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: repo-registry.py search <query>")
            return
        cmd_search(sys.argv[2])

    elif cmd == "history":
        if len(sys.argv) < 3:
            print("Usage: repo-registry.py history <name>")
            return
        cmd_history(sys.argv[2])

    elif cmd == "export":
        fmt = "json"
        if "--format" in sys.argv:
            fmt = sys.argv[sys.argv.index("--format") + 1]
        cmd_export(fmt)

    elif cmd == "dashboard":
        cmd_dashboard()

    elif cmd == "tags":
        if len(sys.argv) < 4:
            print("Usage: repo-registry.py tags <name> <tag1> [tag2] ...")
            return
        cmd_tags(sys.argv[2], sys.argv[3:])

    elif cmd == "note":
        if len(sys.argv) < 4:
            print("Usage: repo-registry.py note <name> \"note text\"")
            return
        cmd_note(sys.argv[2], " ".join(sys.argv[3:]))

    elif cmd == "relate":
        if len(sys.argv) < 5:
            print("Usage: repo-registry.py relate <source> <target> <relationship> [notes]")
            return
        notes = " ".join(sys.argv[5:]) if len(sys.argv) > 5 else None
        cmd_relate(sys.argv[2], sys.argv[3], sys.argv[4], notes)

    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("Usage: repo-registry.py remove <name>")
            return
        cmd_remove(sys.argv[2])

    elif cmd == "actions":
        cmd_actions()

    elif cmd == "diff":
        if len(sys.argv) < 3:
            print("Usage: repo-registry.py diff <n>")
            return
        cmd_diff(sys.argv[2])

    elif cmd == "stale":
        days = 30
        if len(sys.argv) > 2:
            try:
                days = int(sys.argv[2])
            except ValueError:
                pass
        cmd_stale(days)

    elif cmd == "overlap":
        cmd_overlap()

    elif cmd == "brief":
        if len(sys.argv) < 3:
            print("Usage: repo-registry.py brief <n>")
            return
        cmd_brief(sys.argv[2])

    elif cmd == "brief-export":
        if len(sys.argv) < 3:
            print("Usage: repo-registry.py brief-export <n>")
            return
        cmd_brief_export(sys.argv[2])

    elif cmd == "portfolio":
        sort_by = "score"
        if "--sort" in sys.argv:
            sort_by = sys.argv[sys.argv.index("--sort") + 1]
        cmd_portfolio(sort_by)

    elif cmd == "value":
        if len(sys.argv) < 3:
            print("Usage: repo-registry.py value <n> [--revenue $X] [--client name] [--priority 1-5]")
            return
        name = sys.argv[2]
        rev = sys.argv[sys.argv.index("--revenue") + 1] if "--revenue" in sys.argv else None
        client = sys.argv[sys.argv.index("--client") + 1] if "--client" in sys.argv else None
        pri = sys.argv[sys.argv.index("--priority") + 1] if "--priority" in sys.argv else None
        cmd_value(name, revenue=rev, client=client, priority=pri)

    elif cmd == "me":
        cmd_me()

    elif cmd == "me-export":
        cmd_me_export()

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
