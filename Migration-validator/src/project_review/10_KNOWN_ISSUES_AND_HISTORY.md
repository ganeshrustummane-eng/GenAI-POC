# 10 — Known Issues and Development History

## Active Security Issue

### Hard-Coded Credentials in main_example.py

**File:** `src/main_example.py`
**Severity:** HIGH — credentials visible in source code

The `create_example_config()` function contains:
```python
password="Ganeshmane@999"          # PostgreSQL password
account="ZJAUJWQ-EP12783"          # Snowflake account identifier
username="MANEGANESH99"             # Snowflake username
```

**Action needed:** This file should not be committed to any shared repository. Either:
1. Replace with `.env`-based loading
2. Add `main_example.py` to `.gitignore`
3. Delete the file (functionality is superseded by `main_dynamic.py`)

---

## Hard-Coded Table References in main_dynamic.py

**File:** `src/main_dynamic.py`
**Severity:** LOW — not a security issue, but not portable

```python
SINGLE_TABLE_CONFIG = {
    "pg_database": "fms",
    "pg_schema": "public",
    "pg_table": "events",
    "sf_account": "ZJAUJWQ-EP12783",     # hard-coded
    "sf_database": "storedge_fms_public",
    "sf_table": "EVENTS"
}
```

This file is the developer's personal config for their specific environment. It should be replaced by `validate_cli.py` (which prompts interactively) or converted to read from `.env`.

---

## Open Design Note in integer_rule.py

**File:** `src/rules/integer_rule.py`
**Last line:** `# We dont hav cast to text or string (Conditional)`

This is an in-progress design note left in the source code. It appears to suggest a conditional casting path was considered (where integer-to-NUMBER mapping might not need explicit CAST) but was not implemented. Not a bug — integers compare correctly — but the comment is confusing.

---

## Placeholder Learned Rule in rule_book_learned.json

**File:** `src/rule_book_learned.json`

The only entry (`ex_strip`) was added as a test to verify the `add-rule` CLI command works. It has identity templates `{col}` (no actual transformation) and a description about negative amounts but no negative-amount SQL logic.

**Action needed:** Either:
1. Delete this entry (it does nothing)
2. Implement it properly with actual SQL templates if negative-amount checking is desired

---

## DIAL Model Availability (as of 2026-08-10)

Of the 26 candidate models probed, only 2 were responding:

| Model | Status |
|-------|--------|
| `gpt-4o` | ✅ Working |
| `gpt-4` | ✅ Working |
| `gpt-4o-mini` | ❌ "Unknown deployment" |
| `gpt-4-turbo` | ❌ "Unknown deployment" |
| `gpt-3.5-turbo` | ❌ "Unknown deployment" |
| `anthropic.claude-3-5-sonnet` | ❌ Error |
| `anthropic.claude-3-haiku` | ❌ Error |
| `gemini-1.5-pro` | ❌ Error |
| `gemini-1.5-flash` | ❌ Error |

This means the model selection menu currently shows only 2 options. The model probe cache should be invalidated if new models are provisioned in DIAL.

---

## Bugs Fixed During Development

### Bug 1: hstore TRIM Error (Fixed 2026-08-07)

**Session:** codemie-analytics-b57514fd (12 turns, $2.05)

**Error:**
```
ERROR: function pg_catalog.btrim(hstore) does not exist
LINE: COALESCE(UPPER(TRIM(metadata::TEXT)), '<<NULL>>')
```

**Root cause:** `hstore` is a user-defined PostgreSQL type. The `btrim()` function (used by TRIM) does not accept hstore as input — it only accepts text.

**Fix:** `src/rules/hstore_rule.py` — removed the TRIM wrapper. Now uses only `CAST(col AS TEXT)`:

```python
# Before (broken)
def _pg_expression(self, col: str) -> str:
    return f"UPPER(TRIM({col}::TEXT))"

# After (fixed)
def _pg_expression(self, col: str) -> str:
    return f"{col}::TEXT"
```

---

### Bug 2: Snowflake Row Count Showing 0 (Fixed 2026-08-07)

**Session:** codemie-analytics-5d05a853 (6 turns, $0.63)

**Error:**
```
ROW COUNT MISMATCH
PostgreSQL: 1,000
Snowflake:  0
```

**Root cause:** When the Fivetran filter was applied, the query was using the wrong database/schema combination. The WHERE clause was referencing `_FIVETRAN_ACTIVE` but the table qualified name was incorrect, causing Snowflake to silently return 0 rows instead of an error.

**Fix:** `src/query_executor.py` — corrected the table qualified name in the Snowflake row count query when Fivetran filter is active.

---

## Development Session History

Reconstructed from `docs/codemie/analytics/` JSON files.

### Session 1 — 2026-08-06 (14 turns, $3.51)

**Title:** "Explore the project and understand execution flow."

**What happened:**
- Initial project exploration — reading all files to understand the existing structure
- 27 files read, 403 lines written
- Mapping out the legacy stack vs new stack
- Understanding how `validation_pipeline.py` calls the various submodules

**Outcome:** Baseline understanding established. No functional changes.

---

### Session 2 — 2026-08-07 (39 turns, $5.95)

**Title:** "Act as Data Engineer... optimized AI model use... add option to execute SQL... also add more models."

**What happened:**
- Largest session by cost and turns
- Added model selection UI to `validate_cli.py` — shows a numbered menu of available models
- Added SQL execution option at end of generate flow (the "Execute these queries now? [y/N]" prompt)
- Added more models to `AVAILABLE_MODELS` list in `ai_rule_mapper.py`
- Improved YAML output structure
- 6 files edited, 428 lines added / 52 removed

**Outcome:** Major feature session — interactive model selection + live SQL execution now available.

---

### Session 3 — 2026-08-07 (17 turns, $2.22)

**Title:** "Why in YAML file there is only one SQL script? Possibly can be multiple."

**What happened:**
- Discovered that `yaml_config_writer.py` was only writing one SQL script per YAML file
- Changed to write all 4 validation blocks (row_count_check, data_completeness, null_percentage, distinct_count)
- 1 file edited, 117 lines added / 43 removed

**Outcome:** YAML now contains 4 SQL blocks per file, matching what the README described.

---

### Session 4 — 2026-08-07 (12 turns, $2.05)

**Title:** Shows the actual error: `function pg_catalog.btrim(hstore) does not exist`

**What happened:**
- Engineer ran the tool against a real table containing hstore columns
- Encountered the btrim(hstore) PostgreSQL error
- Diagnosed root cause: TRIM cannot be applied to hstore type
- Fixed `hstore_rule.py` to remove TRIM wrapper
- 1 file edited, 11 lines added / 2 removed

**Outcome:** hstore columns now validated correctly.

---

### Session 5 — 2026-08-07 (6 turns, $0.63)

**Title:** Shows the actual error: `ROW COUNT MISMATCH — PostgreSQL: 1000, Snowflake: 0`

**What happened:**
- Cheapest session — quick targeted bug fix
- Snowflake row count was 0 when Fivetran filter was active
- Fixed the table qualified name in Snowflake row count query
- 1 file edited, 7 lines added / 2 removed

**Outcome:** Row count now correctly returns the Fivetran-active row count.

---

### Session 6 — 2026-08-10 (22 turns, $1.56)

**Title:** Shows the model probe test output — "2 of 9 models working: gpt-4o and gpt-4"

**What happened:**
- Created `model_probe.py` from scratch
- 26-model parallel probing with 24h disk cache
- Integrated probe into `validate_cli.py` model selection menu
- Only working models shown in menu
- 2 files changed, 200 lines added / 13 removed

**Outcome:** Model selection now shows only models that actually respond. Users no longer see errors from unavailable models.

---

## Total Development Cost (from analytics)

| Session | Date | Turns | Cost |
|---------|------|-------|------|
| Initial exploration | 2026-08-06 | 14 | $3.51 |
| Model selection + SQL execution | 2026-08-07 | 39 | $5.95 |
| YAML multi-block fix | 2026-08-07 | 17 | $2.22 |
| hstore bug fix | 2026-08-07 | 12 | $2.05 |
| Row count 0 bug fix | 2026-08-07 | 6 | $0.63 |
| Model probe feature | 2026-08-10 | 22 | $1.56 |
| **Total** | | **110 turns** | **$15.92** |
