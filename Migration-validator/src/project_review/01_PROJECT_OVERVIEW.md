# 01 — Project Overview

## What Is This Tool?

**Migration Validator v2.0** is a Python tool that automates data validation between a PostgreSQL source database and a Snowflake target database. It is built for data migration projects where you need to verify that data moved correctly — same row counts, same values, same nulls — without writing validation SQL by hand.

---

## The Problem It Solves

When migrating data from PostgreSQL to Snowflake:
- Column names may differ (e.g., `user_id` in PG → `USERID` in Snowflake)
- Data types differ (e.g., `boolean` in PG → `NUMBER(1,0)` in Snowflake)
- NULL handling differs between databases
- Snowflake may have Fivetran-managed tables with soft-deletes (`_FIVETRAN_ACTIVE` column)
- Writing 8+ SQL validation queries per table manually for 50+ tables is impractical

This tool automates the full workflow: **schema discovery → column matching → rule selection → SQL generation → optional execution**.

---

## What It Produces

For each source/target table pair, it generates:

1. **A `.sql` file** with 8 validation queries and Possible Dynamic Queries :
   - Row count (PG vs SF)
   - Main data comparison SELECT (normalised for type differences)
   - NULL % per column (PG vs SF)
   - DISTINCT count per column
   - Duplicate primary key check (SF)
   - Missing rows check (rows in PG not in SF)

2. **A `.yaml` file** with 4 structured validation blocks:
   - `row_count_check`
   - `data_completeness`
   - `null_percentage`
   - `distinct_count`

3. **Optional live execution** of those queries with coloured PASS/WARN/FAIL verdicts in the terminal.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| CLI framework | Click |
| PostgreSQL driver | psycopg2 |
| Snowflake driver | snowflake-connector-python |
| AI provider | EPAM DIAL (AzureOpenAI-compatible API) |
| Fuzzy matching | RapidFuzz + difflib fallback |
| Tests | pytest (107 tests) |
| Config | .env file + environment variables |

---

## Who Runs It

A data engineer or QA engineer on a migration project. They run the CLI interactively:

```
python validate_cli.py
```

The tool asks them for:
- Source PostgreSQL: database, schema, table name
- Target Snowflake: database, schema, table name
- Primary key columns
- Which AI model to use (only working models are shown)

Then it generates all SQL/YAML automatically.

---

## Version Status

- **Current version:** 2.0.0 (`__init__.py`)
- **Legacy stack:** preserved but not the main path
- **New stack (v2):** plan-driven, token-efficient AI, active development
- **Tests:** 107 tests, all passing as of last cache (`lastfailed = {}`)
- **Known security issue:** `main_example.py` has hard-coded credentials (see `10_KNOWN_ISSUES_AND_HISTORY.md`)
