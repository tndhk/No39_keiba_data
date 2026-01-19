# Dead Code Analysis Report

Generated: 2026-01-19

## Summary

| Category | Count | Status |
|----------|-------|--------|
| Unused Imports | 4 | CLEANED |
| Unused Models | 2 | CAUTION - future use |
| Unused Functions | 0 | - |
| Unused Files | 0 | - |

---

## CLEANED: Unused Imports in Test Files

The following unused imports were removed from test files:

### tests/test_cli.py (CLEANED)

| Line | Import | Status |
|------|--------|--------|
| 3 | `import calendar` | REMOVED |
| 5 | `from pathlib import Path` | REMOVED |
| 6 | `call` from `unittest.mock` | REMOVED |
| 11 | `scrape` from `keiba.cli` | REMOVED |

All tests passed after cleanup (184 passed).

---

## CAUTION: Potentially Unused Models

These models are defined and exported but not used in the main CLI logic. They appear to be prepared for future features.

### keiba/models/owner.py - Owner Model

- Defined in: `keiba/models/owner.py`
- Exported in: `keiba/models/__init__.py`
- Used in: Test files only (`tests/test_models.py`, `tests/test_integration.py`)
- Status: CAUTION - Keep for future use (horse.owner_id references this model)

### keiba/models/breeder.py - Breeder Model

- Defined in: `keiba/models/breeder.py`
- Exported in: `keiba/models/__init__.py`
- Used in: Test files only (`tests/test_models.py`, `tests/test_integration.py`)
- Status: CAUTION - Keep for future use (horse.breeder_id references this model)

---

## DANGER: Critical Files

No critical files identified for deletion.

---

## Recommendations

### Immediate Actions (SAFE)

1. Remove unused imports in `tests/test_cli.py`:
   - `import calendar`
   - `from pathlib import Path`
   - `call` from mock imports
   - `scrape` from keiba.cli imports

### Deferred Actions (CAUTION)

1. Keep `Owner` and `Breeder` models:
   - They have corresponding foreign keys in the `Horse` model
   - Tests verify their functionality
   - They are likely intended for future scraper enhancements

### No Action Required (DANGER)

- No dangerous dead code detected

---

## Test Coverage

Current test coverage: 87% (702 statements, 92 missing)

All 184 tests passing.
