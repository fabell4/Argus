# Argus TODO

## ✅ All Issues Resolved

### Type Checking (mypy)

- [x] Installed types-requests stub package
- [x] Fixed all no-any-return errors using proper type annotations
- [x] Added Protocol-based typing for optional dependencies (influxdb-client)
- [x] Removed all unused type: ignore comments

**Mypy status:** ✅ Clean - 0 errors in 36 source files

### Linting Issues

- [x] Added `encoding="utf-8"` to all `open()` calls
- [x] Removed unused `timezone` import from runtime_config.py
- [x] Refactored shared_state.py to use dataclass instead of global statements
- [x] Changed `logging.error()` to `logging.exception()` for exception logging
- [x] Fixed unused/shadowed function parameters (prefixed with `_` or added noqa)
- [x] Removed redundant `response_model` parameters from FastAPI routes

**Pytest status:** ✅ 31/31 tests pass

### Frontend

- [x] ESLint: Clean (no issues)
- [x] TypeScript: Clean (tsc --noEmit passes)
- [x] Build: Clean (vite build passes)

**Current status:** 🎉 Zero problems detected across all files

**Current problem count:** 14 VS Code diagnostics (PowerGauge.tsx cache issues only)
