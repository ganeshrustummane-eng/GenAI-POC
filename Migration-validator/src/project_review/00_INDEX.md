# Migration Validator v2.0 — Project Review Index

> Complete project documentation for lead review presentation.
> All files are based on actual source code analysis as of 2026-08-11.

---

## Documents in This Folder

| # | File | What It Covers |
|---|------|----------------|
| 01 | [01_PROJECT_OVERVIEW.md](01_PROJECT_OVERVIEW.md) | What the tool does, why it exists, high-level summary |
| 02 | [02_ARCHITECTURE.md](02_ARCHITECTURE.md) | Two-generation architecture, data flow diagram, key design decisions |
| 03 | [03_FILE_REFERENCE.md](03_FILE_REFERENCE.md) | Every file — folder, purpose, what it does in plain language |
| 04 | [04_PROMPTS_AND_AI.md](04_PROMPTS_AND_AI.md) | Every AI prompt we send, what we ask for, system vs user prompts |
| 05 | [05_RULES_AND_TYPES.md](05_RULES_AND_TYPES.md) | All 11 type rules, what they do, SQL they produce |
| 06 | [06_PIPELINE_FLOW.md](06_PIPELINE_FLOW.md) | Step-by-step execution path for both pipeline modes |
| 07 | [07_SQL_AND_YAML_OUTPUT.md](07_SQL_AND_YAML_OUTPUT.md) | Exactly what SQL and YAML is generated, format, structure |
| 08 | [08_TESTS.md](08_TESTS.md) | All 107 tests, what each class tests, current status |
| 09 | [09_ENV_VARS_AND_CONFIG.md](09_ENV_VARS_AND_CONFIG.md) | All environment variables, config files, security notes |
| 10 | [10_KNOWN_ISSUES_AND_HISTORY.md](10_KNOWN_ISSUES_AND_HISTORY.md) | Bugs fixed, open issues, session-by-session development history |

---

## Quick Reference

**Entry point:** `validate_cli.py` (interactive CLI)
**Core pipeline:** `validation_pipeline.py` → `run_with_plan()`
**AI prompt location:** `ai/prompt_builder.py`
**Rule definitions:** `rules_catalog.json` + `rules/` package
**Output files:** `validation_sql/<table>_validation.sql` + `.yaml`
**Tests:** `tests/` — 107 tests, all passing
