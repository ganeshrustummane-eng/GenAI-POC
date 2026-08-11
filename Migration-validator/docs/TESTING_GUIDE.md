# Testing Guide — How to Verify Everything Is Working

This guide walks you through every layer of testing, from zero-dependency offline checks to full live-database runs. Follow in order.

> **📘 Testing DiAL API?** See the dedicated guide: [DIAL_API_TESTING_GUIDE.md](DIAL_API_TESTING_GUIDE.md) or run `python test_dial_api.py`

---

## Layer 0 — Environment Sanity (2 minutes, no DB needed)

Before anything else, confirm Python and packages are installed.

```powershell
# From project root
cd C:\EPAM-Personal\Migration-validator

# Activate virtual environment
.venv\Scripts\activate

# Confirm Python version (needs 3.9+)
python --version

# Confirm all packages installed
pip list | findstr "openai snowflake psycopg2 click"
```

Expected: you see all four packages listed with version numbers.

If any are missing:
```powershell
pip install -r requirements.txt
```

---

## Layer 1 — Offline Pipeline Test (5 minutes, no DB needed)

This test runs the full SQL + YAML generation pipeline using mock column data. No database connections required.

```powershell
cd src
python verify_yaml_generation.py
```

**What to look for:**

```
[OK] Static rule mapper produced N column mappings
[OK] SQL query generator built all 6 query blocks
[OK] YAML written to validation_sql/test_table_validation.yaml
[OK] SQL written to validation_sql/test_table_validation.sql
```

**Manual inspection — open the generated YAML:**
1. Open `validation_sql/test_table_validation.yaml`
2. Check that `row_count_validation` block has both `sourcequery` and `targetquery`
3. Check that `data_validation.sourcequery` contains `COALESCE(…, '<<NULL>>')` around each column
4. Check that `data_validation.targetquery` uses Snowflake syntax (`::`  casting, `TO_CHAR` with Snowflake dialect)
5. If a boolean column exists, confirm it renders as `CASE WHEN col = true THEN '1' WHEN col = false THEN '0'`
6. If a timestamp column exists, confirm it renders as `TO_CHAR(col, 'YYYY-MM-DD HH24:MI:SS')`

---

## Layer 2 — Connection Health Check (5 minutes, requires DB credentials in `.env`)

```powershell
cd src
python check_connections.py
```

**What to look for — each check prints PASS or FAIL:**

```
[PASS] Python packages: all required packages found
[PASS] PostgreSQL: connected to <database> as <user>
[PASS] Snowflake: connected to <account>/<database>/<schema>
[PASS] DIAL API key: present (AI mode will be available)
```

**If PostgreSQL fails:**
- Confirm `SOURCE_HOST`, `SOURCE_PORT`, `SOURCE_DATABASE`, `SOURCE_USERNAME`, `SOURCE_PASSWORD` in `.env`
- Confirm the PG server is reachable (ping the host, check firewall)
- Try: `psql -h <host> -U <user> -d <database>` from terminal

**If Snowflake fails:**
- Confirm `SNOWFLAKE_ACCOUNT` format — must be `accountname.region.cloud` (e.g. `xy12345.us-east-1.aws`)
- Confirm the user has `USAGE` on the warehouse and `SELECT` on the schema
- Try the standalone test: `python test_snowflake_connector.py`

**If DIAL API FAIL (not blocking for static mode):**
- EPAM VPN must be connected
- `DIAL_API_KEY` must be set in `.env`
- The tool still works without it (static rule mapper is used)
- **For detailed DiAL testing:** See [DIAL_API_TESTING_GUIDE.md](DIAL_API_TESTING_GUIDE.md) or run `python test_dial_api.py`

---

## Layer 3 — Static Mode Generation (10 minutes, requires DB connections)

Generate validation files without AI. This confirms the full pipeline works with real schema data.

```powershell
cd src
python validate_cli.py generate --pg-table events --sf-table EVENTS --mode static
```

Replace `events` / `EVENTS` with a real table that exists in both your PG and Snowflake schemas.

**What to verify:**

1. No error output during generation
2. Files created:
   - `validation_sql/events_validation.sql`
   - `validation_sql/events_validation.yaml`
3. Open the YAML and count columns — should match what you see in `information_schema.columns` for that table
4. Check that `_FIVETRAN_ACTIVE` filter appears in Snowflake queries (if that column exists in your SF table)
5. Check that `_FIVETRAN_*` system columns are NOT included in the data validation SELECT list

**If column count is wrong:**

Run the schema inspection command:
```powershell
python validate_cli.py list-tables
```
This lists all tables visible to both extractors. Cross-check with your actual schema.

---

## Layer 4 — AI Mode Generation (10 minutes, requires EPAM VPN + DIAL key)

```powershell
cd src
python validate_cli.py generate --pg-table events --sf-table EVENTS --model gpt-4o
```

**What to verify vs static mode:**

1. The console shows: `Using AI rule mapper (model: gpt-4o)`
2. The generated YAML exists and is valid (same structure as static mode)
3. AI mode should handle renamed columns — if your PG table has `user_id` and SF table has `USER_ID`, both should appear in the mapping
4. For ambiguous types (e.g. a `text` column that actually stores JSON), AI mode may assign `json` rule instead of `text` — check the YAML comments for assigned rules

**List available models:**
```powershell
python validate_cli.py list-models
```

**Try a different model:**
```powershell
python validate_cli.py generate --pg-table events --sf-table EVENTS --model anthropic.claude-haiku-4-5
```

---

## Layer 5 — Run Generated SQL Against Real Databases

This is the actual validation step. The tool generates the SQL; you run it.

### Step 5a — Run source queries against PostgreSQL

Open your PostgreSQL client (psql, DBeaver, DataGrip, etc.) and run the queries from the generated `.sql` file or from the YAML `sourcequery` fields.

**Row count check:**
```sql
-- From row_count_validation.sourcequery
SELECT COUNT(*) AS source_row_count
FROM public.events;
```
Note the number. Call it `pg_count`.

**Data validation scan:**
Run the full `data_validation.sourcequery` SELECT. This returns one row per record, each column normalized to text. Note the row count — should match `pg_count`.

### Step 5b — Run target queries against Snowflake

In Snowflake (Snowsight, DBeaver, etc.) run the matching `targetquery` blocks.

**Row count check:**
```sql
-- From row_count_validation.targetquery
SELECT COUNT(*) AS target_row_count
FROM dev_edge_bronze.storedge_fms_public.EVENTS
WHERE _FIVETRAN_ACTIVE = TRUE;
```
Note the number. Call it `sf_count`.

### Step 5c — Compare

| Check | Pass condition |
|---|---|
| Row counts | `pg_count == sf_count` |
| Data scan row counts | Both return same number of rows |
| NULL % per column | Each column's NULL % within acceptable tolerance (e.g., < 1% difference) |
| Distinct counts | Each column's distinct count matches |

**For exact data diff**, export both data scan results to CSV and run a diff tool, or load both into a DataFrame:

```python
import pandas as pd

pg_df = pd.read_csv("pg_events.csv")
sf_df = pd.read_csv("sf_events.csv")

# Sort both by the same column before comparing
pg_df = pg_df.sort_values("id_normalized").reset_index(drop=True)
sf_df = sf_df.sort_values("id_normalized").reset_index(drop=True)

diff = pg_df.compare(sf_df)
print(f"Differing rows: {len(diff)}")
```

---

## Layer 6 — Edge Case Checks

After the happy path works, test these specific cases:

### NULL handling
Confirm a column that has NULLs in PG shows `<<NULL>>` — not empty string, not `None`, not `null`.

In PG:
```sql
SELECT COALESCE(CAST(nullable_column AS TEXT), '<<NULL>>') FROM events LIMIT 5;
```
You should see the literal string `<<NULL>>` for null rows.

### Boolean columns
Confirm `true` → `'1'` and `false` → `'0'` on both sides. If PG stores `TRUE` and SF stores `true`, both should normalize to `'1'`.

### Timestamp with timezone
If your table has `timestamp with time zone` columns, confirm both sides show the same UTC-formatted string. A row with `2024-01-15 10:30:00+05:30` (PG) should produce `2024-01-15 05:00:00` on both sides.

### Fivetran filter
If `_FIVETRAN_ACTIVE` exists in Snowflake, confirm the generated SF query has `WHERE _FIVETRAN_ACTIVE = TRUE`. Confirm PG query does NOT have this filter. The counts may differ legitimately — SF filters out soft-deleted records.

### Tables with no overlapping columns
If a table exists in PG but the SF table has completely different column names, the static mapper will return zero mappings. The YAML will have only row count blocks. This is expected. AI mode would handle renamed columns by semantic matching.

---

## Layer 7 — Rule Book Verification

Test that custom rules work:

```powershell
cd src
python validate_cli.py add-rule
```

Follow the prompts to add a rule. Then regenerate a table:
```powershell
python validate_cli.py generate --pg-table events --sf-table EVENTS
```

Verify the custom rule appears in the generated SQL for the columns you specified.

View all rules (built-in + learned):
```powershell
python validate_cli.py rules
```

---

## Quick Test Checklist

Copy this as your sign-off checklist before declaring the tool working:

```
[ ] Layer 0: Python + packages OK
[ ] Layer 1: verify_yaml_generation.py produces valid YAML offline
[ ] Layer 2: check_connections.py shows PASS for PG and Snowflake
[ ] Layer 3: Static mode generates .sql and .yaml for a real table
[ ] Layer 4: AI mode generates output (if EPAM VPN + DIAL key available)
[ ] Layer 5a: Row count queries run against PG without error
[ ] Layer 5b: Row count queries run against Snowflake without error
[ ] Layer 5c: Counts match (or you understand why they differ)
[ ] Layer 6: NULL sentinel '<<NULL>>' appears correctly
[ ] Layer 6: Boolean columns produce '1'/'0' not 'true'/'false'
[ ] Layer 7: Custom rule persists and appears in regenerated output
```

---

## Common Errors and Fixes

| Error | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: psycopg2` | Package not installed | `pip install psycopg2-binary` |
| `SSL SYSCALL error: EOF detected` | PG connection requires SSL | Add `sslmode=require` to PG env vars |
| `250001: Failed to connect to DB` | Wrong Snowflake account format | Use `xy12345.us-east-1.aws` format |
| `YAML: No columns mapped` | Column names don't match PG ↔ SF | Check schema names, use AI mode for renamed columns |
| `KeyError: 'DIAL_MODEL'` | `.env` file missing that variable | Add `DIAL_MODEL=gpt-4o` to `.env` |
| `openai.AuthenticationError` | DIAL API key wrong or VPN off | Connect EPAM VPN, check key |
| Generated query has wrong table path | Snowflake schema path hardcoded | Check `SNOWFLAKE_DATABASE` and `SNOWFLAKE_SCHEMA` in `.env` |
