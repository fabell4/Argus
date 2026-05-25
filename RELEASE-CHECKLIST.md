# Quick Release Checklist

Use this checklist for every release.

## Pre-Release

- [ ] All code changes committed and tested locally
- [ ] Run `ruff format src tests` — no changes needed
- [ ] Run `ruff check src tests` — all checks pass
- [ ] Run `mypy src` — no errors
- [ ] Run `pytest --cov=src -v` — all tests pass, coverage ≥85%
- [ ] Verify Dockerfile uses public registries (Docker Hub, not private registry)
- [ ] Security documentation reviewed and current (SECURITY.md)

## Version Update

- [ ] Update `CHANGELOG.md` with new version and changes
- [ ] Update `frontend/package.json` version field
- [ ] Commit: `git commit -m "chore: release vX.Y.Z"`

## Validation

- [ ] Trigger "Pre-Release Check" workflow on GitHub Actions
- [ ] Enter version number (e.g., `0.1.0-beta`)
- [ ] Wait for ✅ All checks passed

## Release

- [ ] Create tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z: ..."`
- [ ] Push: `git push origin main`
- [ ] Push tag: `git push origin vX.Y.Z`

## Monitor

- [ ] CI workflow completes successfully
- [ ] SonarQube Quality Gate: PASSED
- [ ] Docker images pushed to registries

## Verify

- [ ] GitHub release created
- [ ] Docker images available: `ghcr.io/.../argus:X.Y.Z` and `:latest`

---

**⚠️ STOP if any step fails. Do not proceed to next step until issue is resolved.**
