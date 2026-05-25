---
layout: default
title: "Code Review Policy"
---

# Code Review Policy

**Projects:** Argus / Hermes (shared policy)
**Format:** Human-readable reference. The machine-readable version for AI agents is
`.github/instructions/code-review-policy.instructions.md`.

> **Shared template notice** — Sections 1–11 of this document are identical across Argus and
> Hermes. Only Section 12 (Project-Specific Configuration) differs per repo. When updating
> shared sections, apply the same change to the other project.

---

## Purpose

This policy defines the nine review categories that must be completed before any release tag
is cut. It establishes:

- **What to check** in each category
- **Why each category exists** and what failures it prevents
- **How to run** each check (commands and tooling)
- **Exit criteria** — the conditions that must all be true before a release tag is created
- **Finding classification** — how to record and track issues found during review

The policy is designed to be consumed by both humans (as a pre-release checklist) and AI
agents (via the companion `.instructions.md` file).

---

## Review Sequencing and Dependencies

Reviews must be performed in order. Each category depends on the previous ones being clean
because findings in early categories can invalidate conclusions drawn in later ones (e.g.
a dependency CVE may make an application-level security control moot).

``` text
1. Supply Chain Security        ← must be clean before anything else
2. Application Security Audit   ← requires supply chain clean
3. Defensive Coding Review      ← requires app security approved
4. Best Practices Review        ← requires defensive coding reviewed
5. Modernization Review         ← can run in parallel with Best Practices
6. Error Handling Review        ← requires Best Practices and Modernization
7. Test Coverage Review         ← requires all code changes from above complete
8. Documentation Accuracy Review← requires test counts to be final
9. Performance Review           ← requires all functional changes complete
```

---

## Severity Levels

| Level | Meaning | Release Impact |
| ------- | --------- | ---------------- |
| 🔴 HIGH | Critical defect, security vulnerability, or data integrity risk | Blocks release unconditionally |
| 🟡 MEDIUM | Quality issue affecting reliability or maintainability | Should be resolved; may defer to next minor with tracked TODO |
| 🟢 LOW | Polish item with minimal user impact | Defer to post-release backlog |

---

## Category 1: Supply Chain Security

### Why This Category Comes First

This category was added after discovering that three known CVEs in `starlette` (CVE-2025-54121,
CVE-2025-62727, PYSEC-2026-161) were shipped in a release because the security audit item was
scoped to application-level controls only. Dependency CVEs are published continuously after
packages are pinned — no manual review can catch them. Automated scanning must be the first
gate, not an optional CI artifact.

### What to Check

- No package in `requirements.txt` has a known CVE at any severity
- No npm package in `frontend/package.json` has a high or critical vulnerability
- Dependency update automation (Dependabot / Renovate) is active for pip, npm, and Actions

### How to Run

```bash
# Python dependencies
pip-audit -r requirements.txt

# Frontend dependencies (run from frontend/ directory)
cd frontend && npm audit --omit=dev
```

Both commands must exit 0 with no findings. If findings exist:

1. Identify the fix version from the `pip-audit` output (Fix Versions column)
2. Check if the direct dependency that pulls in the vulnerable package needs to be upgraded
   alongside it (version conflicts are common — use `pip install "pkg==X" "dep==Y" --dry-run`
   to verify compatibility)
3. Upgrade in `requirements.txt`, re-run the full test suite, then re-run `pip-audit`

### Pass Criteria

All scan commands exit 0. Any CVE at HIGH or CRITICAL severity blocks release unconditionally,
regardless of findings in any other category.

---

## Category 2: Application Security Audit

### Why This Category Exists

The application handles API key authentication, operator-supplied URLs (alert providers), and
user-submitted configuration. Failures here expose production deployments to authentication
bypass, SSRF, SQL injection, or information disclosure.

### What to Check

**Authentication:** `secrets.compare_digest()` used for all key comparisons; correct HTTP
status codes (401 vs 403); all write endpoints protected; minimum 32-character key enforced
at startup.

**Rate limiting:** Middleware present on all routes; limit headers returned; configurable via
environment variable.

**Input validation:** Pydantic models on all request bodies; no string concatenation into SQL
queries.

**SSRF:** Operator-supplied URLs (Webhook, Gotify, ntfy, Apprise) validated to `https://`
scheme before storage; validation at write time, not at call time.

**Headers and CORS:** `X-Content-Type-Options`, `X-Frame-Options` present; CORS origin not
wildcard in production; no partial secrets in logs.

### How to Run

No single command covers this category. Review the relevant source files directly:

- `src/api/auth.py` — authentication and key comparison
- `src/api/middleware.py` (or equivalent) — rate limiting, headers
- `src/api/routes/*.py` — input validation, protected endpoints
- `src/services/alert_providers.py` — URL validation

Run the API security test suite to verify controls work:

```bash
pytest tests/test_api*.py -v
```

---

## Category 3: Defensive Coding Review

### Why This Category Exists

Well-typed code can still fail at runtime if it doesn't account for edge cases: env vars set
to negative numbers, config files partially written during a crash, database connections left
open under error paths. This category ensures the code fails safely and predictably.

### What to Check

- Env var helpers validate value range (not just type)
- Persistent state (runtime config) uses atomic write: temp file → `os.replace()`
- All SQLite connections use `with conn:` and specify `timeout=`
- All file I/O uses `with` blocks
- Thread-shared state protected by locks
- All HTTP calls have explicit timeouts
- Background threads catch and log exceptions at the thread boundary

### How to Run

Code inspection is the primary tool. Grep for common failure patterns:

```bash
# Find non-context-manager SQLite usage
ruff check src --select E

# Find potential missing timeouts in HTTP calls
grep -rn "requests\." src/ | grep -v timeout

# Verify no file opens without context manager
grep -rn "open(" src/ | grep -v "with open"
```

---

## Category 4: Best Practices Review

### Why This Category Exists

Repeated magic strings, duplicated logic, and inconsistent type annotations accumulate into
a maintenance burden that compounds over time. This category addresses structural quality
before patterns become entrenched.

### What to Check

- All repeated string values extracted to `StrEnum` or constants
- No logic copied across more than one module
- Complete, consistent type annotations using Python 3.10+ union syntax
- Imports organised: stdlib → third-party → local
- No silent exception swallows

### How to Run

```bash
ruff check src
mypy src
```

---

## Category 5: Modernization Review

### Why This Category Exists

Python deprecated several common patterns in 3.10–3.12. Using them makes the codebase harder
to migrate and generates deprecation warnings in newer interpreters. This category prevents
technical debt from accumulating.

### What to Check

- `datetime.utcnow()` → `datetime.now(timezone.utc)`
- `os.path.*` → `pathlib.Path`
- `Optional[X]` / `Union[X, Y]` → `X | None` / `X | Y`
- `Dict`, `List`, `Tuple` from `typing` → lowercase builtins
- String enums use `StrEnum`
- No `typing.io` / `typing.re` (removed in 3.12)

### How to Run

```bash
# Ruff can catch some of these
ruff check src --select UP

# Mypy catches type annotation inconsistencies
mypy src
```

---

## Category 6: Error Handling Review

### Why This Category Exists

Silent failures are the hardest category of bug to diagnose in production. A scheduler
thread that swallows an exception and stops running looks identical to one that ran successfully
until someone notices stale data. This category ensures every failure mode is observable.

### What to Check

- Every `except` block logs or re-raises — no `pass`
- HTTP error responses return structured JSON, not Python tracebacks
- All network calls have `timeout`
- Startup failures are fatal with a clear message
- Background exceptions are logged with `exc_info=True`
- Error catalog updated for new messages

### How to Run

```bash
# Ruff catches bare except and broad except
ruff check src --select E722,BLE001

# Manual review of exception handling in scheduler/main.py
grep -n "except" src/main.py
```

---

## Category 7: Test Coverage Review

### Why This Category Exists

Coverage gates prevent regression paths from going undetected. `ResourceWarning` failures
indicate unclosed database connections that will cause problems under load. Frontend coverage
ensures UI logic is exercised, not just rendered.

### What to Check

- Python backend ≥90% coverage
- Frontend ≥70% statement coverage
- Zero `ResourceWarning` in test run
- New modules have tests
- No skipped tests without justification
- Integration paths covered end-to-end

### How to Run

```bash
# Python — coverage gate
pytest --cov=src --cov-report=term-missing --cov-fail-under=90

# Python — resource leak check
pytest -W error::ResourceWarning

# Frontend — coverage
cd frontend && npx vitest run --coverage
```

---

## Category 8: Documentation Accuracy Review

### Why This Category Exists

Stale documentation erodes trust and creates friction for new contributors. Test count
mismatches, wrong environment variable names, and outdated API tables are the most common
class of documentation rot in these projects.

### What to Check

- README setup commands work on a clean checkout
- Test count and coverage percentage match CI
- `.env.example` covers all variables in `config.py`
- API table matches FastAPI route definitions
- `CHANGELOG.md` updated
- `CONTRIBUTING.md` tested on Windows and Linux

### How to Run

```bash
# Verify test count matches README
pytest --collect-only -q | tail -1

# Verify coverage matches README
pytest --cov=src --cov-report=term-missing | grep "TOTAL"

# Diff env vars: check config.py vs .env.example
grep -oP '(?<=os\.getenv\()["\x27]\K[^"'\'']+' src/config.py | sort > /tmp/config_vars.txt
grep -oP '^\w+' .env.example | sort > /tmp/example_vars.txt
diff /tmp/config_vars.txt /tmp/example_vars.txt
```

---

## Category 9: Performance Review

### Why This Category Exists

Performance problems that are invisible in development become production incidents after
data volume grows. Missing database indexes, blocking I/O on the async request path, and
per-request config file reads are cheap to fix early and expensive to fix after data
accumulates.

### What to Check

- Timestamp indexes on all date-range query tables
- No blocking I/O on FastAPI's async request path
- Runtime config cached (mtime check)
- Alert providers use connection pooling
- Prometheus labels are bounded
- SQLite not reopened per request in hot paths

### How to Run

```bash
# Verify indexes exist in SQLite schema
sqlite3 data/argus.db ".schema power_snapshots"
sqlite3 data/argus.db ".schema power_events"

# Check for blocking calls on async routes
grep -n "time.sleep\|open(\|conn = " src/api/routes/*.py
```

---

## Exit Criteria

A release tag **must not** be created until every item in this table is verified:

| Gate | Command / Evidence |
| ------ | -------------------- |
| Supply chain — pip | `pip-audit -r requirements.txt` exits 0 |
| Supply chain — npm | `npm audit --omit=dev` exits 0 (no high/critical) |
| Tests pass | `pytest` exits 0 |
| Python coverage ≥90% | `pytest --cov=src --cov-fail-under=90` exits 0 |
| Frontend coverage ≥70% | `vitest run --coverage` from `frontend/` ≥70% statements |
| No ResourceWarnings | `pytest -W error::ResourceWarning` exits 0 |
| Ruff lint clean | `ruff check src` exits 0 |
| Ruff format clean | `ruff format --check src` exits 0 |
| Mypy | `mypy src` exits 0; all suppressions documented |
| No open HIGH findings | All 🔴 HIGH items across all 9 categories resolved |
| Docs current | README test count and API table match current codebase |

---

## Recording Findings

Use this format for every finding raised during a review:

``` text
ID:             SC-1  (category abbreviation + sequential number)
File:           src/requirements.txt
Severity:       HIGH
Summary:        starlette 0.46.2 has three known CVEs
Detail:         CVE-2025-54121 (fixed 0.47.2), CVE-2025-62727 (fixed 0.49.1),
                PYSEC-2026-161 (fixed 1.0.1). fastapi 0.115.12 pins starlette<0.47.0,
                requiring a coordinated upgrade of both packages.
Recommendation: Upgrade fastapi to 0.133.0, starlette to 1.0.1
Resolution:     commit abc1234 — "fix: upgrade fastapi 0.133.0 / starlette 1.0.1 (SC-1)"
```

Category abbreviations: `SC`, `SEC`, `DEF`, `BP`, `MOD`, `ERR`, `COV`, `DOC`, `PERF`

HIGH findings must reference a resolving commit before the release tag is created.
MEDIUM/LOW findings must have a TODO.md entry with a target milestone.

---

## Project-Specific Configuration — Argus

**Runtime:** Python 3.12+, Node.js 22+
**Architecture:** Two-process — scheduler (`python -m src.main`) + API (`uvicorn src.api.main:app`)
**Frontend:** React 18 / TypeScript / Vite / Vitest
**Dependency automation:** Dependabot (pip, npm, GitHub Actions)

### Additional Supply Chain Steps

Run `npm audit --omit=dev` from the `frontend/` subdirectory. Both processes share
`requirements.txt`; the audit covers scheduler and API together.

### Additional Security Checks

- NUT socket connections must specify a connect timeout; credentials must not appear in logs
- SNMP community strings must not appear in log output at any level
- All alert provider URLs validated for `https://` scheme before writing to `runtime_config.json`

### Additional Defensive Coding Checks

- `data/runtime_config.json` writes must use atomic write at all call sites
- NUT and SNMP pollers must catch `socket.timeout` / `OSError` and retry exactly
once before marking a device offline

### Coverage Thresholds

| Layer | Command | Gate |
| ------- | --------- | ------ |
| Python | `pytest --cov=src --cov-fail-under=90` | ≥90% |
| Frontend | `vitest run --coverage` from `frontend/` | ≥70% statements |
