# Migration Validator — Complete Tool Overview

> Everything you need to know: what it does, how to set it up, how it works internally, and how your data stays secure.

---

## Table of Contents

1. [What This Tool Does](#1-what-this-tool-does)
2. [Who It Is For](#2-who-it-is-for)
3. [Environment Setup](#3-environment-setup)
4. [Project Structure](#4-project-structure)
5. [Architecture — How It Works End to End](#5-architecture--how-it-works-end-to-end)
6. [Step-by-Step Data Flow](#6-step-by-step-data-flow)
7. [CLI Reference](#7-cli-reference)
8. [AI Mode vs Static Mode](#8-ai-mode-vs-static-mode)
9. [Available AI Models](#9-available-ai-models)
10. [Normalization Rules Catalog](#10-normalization-rules-catalog)
11. [Generated Output — 8 Validation Queries](#11-generated-output--8-validation-queries)
12. [YAML Output](#12-yaml-output)
13. [Custom Rule Book](#13-custom-rule-book)
14. [Running Queries — Manual vs Terminal Execution](#14-running-queries--manual-vs-terminal-execution)
15. [Validation Reports](#15-validation-reports)
16. [Data Security](#16-data-security)
17. [Common Issues and Troubleshooting](#17-common-issues-and-troubleshooting)
18. [Extending the Tool](#18-extending-the-tool)

---

## 1. What This Tool Does

**Migration Validator** is a Python CLI tool that automatically generates ready-to-run SQL and YAML files for validating data integrity after migrating tables from **PostgreSQL to Snowflake** (typically via Fivetran or any ETL pipeline).

### The core problem it solves

After a migration, you need to prove that data was transferred completely and correctly. Doing this by hand for dozens of tables with different column types is error-prone and slow. Source and target tables are never identical — column types differ, values are represented differently, columns can be renamed, and NULLs may be handled inconsistently.

This tool handles all of that automatically:

- It connects to both databases and reads their schemas live.
- It assigns the correct normalization rule to every column pair (using AI or deterministic matching).
- It generates 8 SQL validation queries per table that normalize values on both sides before comparing them, so the comparison is always apples-to-apples.
- It also produces a YAML config file ready for use with automated test runners.

**The tool does NOT execute queries against your actual data automatically.** It generates the queries, and you (or a downstream automation) run them. This keeps the tool safe and auditable.

---

## 2. Who It Is For

- **Data engineers and migration testers** who need to validate PostgreSQL → Snowflake migrations.
- **QA teams** who want ready-to-run SQL proofs of data completeness for sign-off.
- **Teams using Fivetran** — the tool auto-detects the `_FIVETRAN_ACTIVE` column and adds the correct filter so only active (non-deleted) records are compared.
- **Teams without Fivetran** — static and AI modes work equally well without Fivetran.

---

## 3. Environment Setup

### 3.1 Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.9+ | Tested on 3.10, 3.11, 3.14 |
| PostgreSQL access | Any | Read-only access to `information_schema` is enough for schema extraction |
| Snowflake access | Any | Read-only access to `INFORMATION_SCHEMA` is enough |
| EPAM VPN | Required for AI mode | DIAL API endpoint is on `ai-proxy.lab.epam.com` |
| Docker (optional) | 20+ | Only needed for local test PostgreSQL instance |

### 3.2 Install Python Dependencies

```powershell
cd C:\EPAM-Personal\Migration-validator
pip install -r requirements.txt
```

The requirements include:

| Package | Purpose |
|---|---|
| `psycopg2-binary` | PostgreSQL driver |
| `snowflake-connector-python` | Snowflake driver |
| `openai>=1.0` | DIAL/EPAM AI API client (OpenAI-compatible) |
| `python-dotenv` | Loads `.env` file |

### 3.3 Configure Environment Variables

Copy the example file and fill in your values:

```powershell
copy .env.example .env
```

Edit `.env`:

```ini
# ── PostgreSQL Source ──────────────────────────────────────────────────
SOURCE_HOST=your-pg-host
SOURCE_PORT=5432
SOURCE_DATABASE=your_database
SOURCE_SCHEMA=public
SOURCE_USERNAME=your_user
SOURCE_PASSWORD=your_password

# ── Snowflake Target ───────────────────────────────────────────────────
SNOWFLAKE_ACCOUNT=your_account.region.cloud
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema
SNOWFLAKE_USERNAME=your_user
SNOWFLAKE_PASSWORD=your_password

# ── AI / EPAM DIAL (optional — requires VPN) ───────────────────────────
DIAL_API_KEY=your_key_here
DIAL_API_BASE=https://ai-proxy.lab.epam.com
DIAL_MODEL=gpt-4o
```

Without `DIAL_API_KEY`, the tool runs in **static mode** — fully offline, no VPN required, completely deterministic. See [Section 8](#8-ai-mode-vs-static-mode) for details.

### 3.4 Verify Connections (Run This First)

```powershell
cd src
python check_connections.py
```

This runs 6 sequential health checks:

1. Python package availability
2. Environment variable presence (passwords are masked in output)
3. PostgreSQL connection — lists tables and row counts in your schema
4. Snowflake connection — lists tables and row counts
5. DIAL API reachability (optional — only warns if not configured)
6. Internal module import check

All 6 must pass before you run the main pipeline.

### 3.5 Local Test PostgreSQL (Docker, Optional)

If you don't have a PostgreSQL instance to test with, spin one up locally:

```powershell
docker-compose up -d
```

This starts a PostgreSQL 15 container named `migration_validator_source_db` with:
- Database: `source_db`
- User: `admin` / Password: `admin123`
- Port: `5432`
- Pre-loaded test schema from `tests/postgres/init/`

---

## 4. Project Structure

```
Migration-validator/
│
├── .env                          ← Your credentials (not committed)
├── .env.example                  ← Template to copy
├── docker-compose.yml            ← Local test PostgreSQL
├── requirements.txt
│
├── src/                          ← All source code
│   ├── validate_cli.py           ← CLI entry point (run this)
│   ├── validation_pipeline.py    ← Full pipeline orchestrator
│   ├── check_connections.py      ← Pre-flight health checker
│   ├── ai_query_agent.py         ← Older AI agent layer (dynamic validation path)
│   ├── rule_book.py              ← Rule book singleton (base + learned rules)
│   ├── rules_catalog.json        ← Rule definitions injected into AI prompts
│   ├── rule_book_learned.json    ← Your custom rules (auto-created on first add)
│   │
│   ├── rules/                    ← Per-type normalization rule classes
│   │   ├── base_rule.py          ← Abstract base + RuleRegistry
│   │   ├── boolean_rule.py
│   │   ├── numeric_rule.py
│   │   ├── timestamp_ntz_rule.py
│   │   ├── timestamp_tz_rule.py
│   │   ├── date_rule.py
│   │   ├── text_rule.py          ← Wildcard catch-all
│   │   ├── uuid_rule.py
│   │   ├── integer_rule.py
│   │   ├── json_rule.py
│   │   ├── bytea_rule.py
│   │   ├── hstore_rule.py
│   │   └── null_rule.py
│   │
│   ├── sql_extractor/            ← Live schema extraction
│   │   ├── base_extractor.py     ← ColumnMetadata dataclass + abstract base
│   │   ├── postgres_extractor.py ← Queries PG information_schema.columns
│   │   └── snowflake_extractor.py← Queries SF INFORMATION_SCHEMA.COLUMNS
│   │
│   ├── ai_transformation/        ← Rule assignment (AI or static)
│   │   ├── ai_rule_mapper.py     ← Calls DIAL API, parses JSON response
│   │   ├── static_rule_mapper.py ← Offline type-pair matching
│   │   └── orchestrator.py       ← Tries AI first, falls back to static
│   │
│   └── generated_queries/        ← SQL + YAML builders
│       ├── sql_query_generator.py← Builds 8 SQL blocks per table
│       ├── yaml_config_writer.py ← Writes YAML config from mappings
│       └── query_output_manager.py← Saves .sql and .yaml to disk
│
├── validation_sql/               ← Generated output (auto-created, not committed)
│   ├── events_validation.sql
│   └── events_validation.yaml
│
├── docs/
│   └── TOOL_OVERVIEW.md          ← This file
│
└── tests/postgres/               ← Local test data
    ├── init/01-init-schema.sql
    ├── init/02-insert-sample-data.sql
    ├── QUICKSTART.md
    └── setup.ps1
```

---

## 5. Architecture — How It Works End to End

```
┌─────────────────────────────────────────────────────────────────────┐
│              validate_cli.py  (CLI entry point)                     │
│                                                                     │
│  Commands:                                                          │
│    generate     Full pipeline — schema → rules → SQL + YAML        │
│    rules        Show all rules (base + learned)                     │
│    add-rule     Add a custom learned rule                           │
│    list-models  Show available AI models                            │
│    list-tables  List tables in both databases                       │
│    (none)       Interactive menu                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    validation_pipeline.py                           │
│          Orchestrates Steps 1–3 in sequence                         │
└────────┬────────────────────┬───────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
     STEP 1               STEP 2               STEP 3
  sql_extractor/      ai_transformation/    generated_queries/
  ──────────────      ──────────────────    ──────────────────
  Connect to PG       RuleMapperOrchestrator  SQLQueryGenerator
  Connect to SF         ├─ AIRuleMapper        builds 8 SQL blocks
  Pull column           │   calls DIAL API     per table
  metadata from         │   (any LLM)
  information_schema    └─ StaticRuleMapper  YAMLConfigWriter
                            (offline fallback)  writes YAML alongside

                                                     │
                                                     ▼
                                              STEP 4 OUTPUT
                                           validation_sql/
                                           ├── table_validation.sql
                                           └── table_validation.yaml
```

---

## 6. Step-by-Step Data Flow

### Step 1 — Schema Extraction

`postgres_extractor.py` queries `information_schema.columns` on PostgreSQL. `snowflake_extractor.py` queries `INFORMATION_SCHEMA.COLUMNS` on Snowflake. Both collect every column's name, data type, nullability, ordinal position, precision, and scale as `ColumnMetadata` objects.

The Snowflake extractor additionally checks whether a `_FIVETRAN_ACTIVE` column exists. If it does, every generated Snowflake query will include `WHERE _FIVETRAN_ACTIVE = TRUE` to ensure only the latest active (non-deleted soft-delete) records are compared.

**Only schema metadata is read at this stage — no actual table data is touched.**

### Step 2 — Column Matching and Rule Assignment

`RuleMapperOrchestrator` receives the two lists of `ColumnMetadata` objects and attempts the AI path first, falling back to static if unavailable.

**AI path** (`ai_rule_mapper.py`):
- Strips Fivetran metadata columns (prefix `_FIVETRAN_`) from the column list sent to the model.
- Builds a structured JSON prompt containing column names, types, nullability, and the full rules catalog.
- Sends this to the DIAL API (`/chat/completions` endpoint) using `temperature=0` for deterministic output.
- The model returns a JSON object: one rule assignment per column pair plus a reasoning explanation.
- Falls back to static if the API call fails or the JSON cannot be parsed.

**Static path** (`static_rule_mapper.py`):
- Matches `(pg_type, sf_type)` pairs deterministically against the rules catalog.
- Fully offline — no API key or VPN needed.
- Skips `_FIVETRAN_*` metadata columns automatically.

Either path returns a `List[ColumnRuleMapping]`, where each item holds: `pg_column`, `sf_column`, `rule_id`, `pg_expression`, `sf_expression`.

### Step 3 — SQL and YAML Generation

`SQLQueryGenerator` takes the column rule mappings and builds 8 SQL blocks per table (see [Section 11](#11-generated-output--8-validation-queries)).

`YAMLConfigWriter` wraps each SQL block into a YAML structure with `source_table_name`, `sourcequery`, `target_table_name`, and `targetquery` fields — ready for a downstream test runner.

### Step 4 — Output Files

`QueryOutputManager` writes two files to `validation_sql/`:

- `<table>_validation.sql` — all 8 SQL queries, labelled and formatted with usage instructions.
- `<table>_validation.yaml` — structured YAML pairing source/target queries for each validation type.

---

## 7. CLI Reference

### Interactive Menu (no command)

```powershell
cd src
python validate_cli.py
```

Presents a numbered menu. Good for first-time use.

### Generate — Full Pipeline

```powershell
# Minimal — prompts for anything not provided
python validate_cli.py generate --pg-table events --sf-table EVENTS

# Fully specified
python validate_cli.py generate \
    --pg-database fms \
    --pg-schema public \
    --pg-table events \
    --sf-database dev_edge_bronze \
    --sf-schema storedge_fms_public \
    --sf-table EVENTS \
    --model gpt-4o-mini
```

**Arguments:**

| Argument | Description | Default |
|---|---|---|
| `--pg-database` | PostgreSQL database name | `SOURCE_DATABASE` from `.env` |
| `--pg-schema` | PostgreSQL schema | `SOURCE_SCHEMA` from `.env` or `public` |
| `--pg-table` | PostgreSQL table name | Required |
| `--sf-database` | Snowflake database name | `SNOWFLAKE_DATABASE` from `.env` |
| `--sf-schema` | Snowflake schema | `SNOWFLAKE_SCHEMA` from `.env` |
| `--sf-table` | Snowflake table name | Required |
| `--model` | AI model to use | `DIAL_MODEL` from `.env` or `gpt-4o` |

### Other Commands

```powershell
# Show all rules (base built-in + your learned rules)
python validate_cli.py rules

# Add a new custom rule interactively
python validate_cli.py add-rule

# List all available AI models (grouped by provider)
python validate_cli.py list-models

# List tables available in both databases
python validate_cli.py list-tables
```

### After Generation — Execute Immediately

After SQL and YAML files are generated, the CLI offers to execute the queries live in the terminal:

```
Execute queries now in the terminal?
  [y]  Execute ALL queries and show results
  [s]  Execute row count queries only
  [n]  Skip — I'll run them manually
```

Selecting `[y]` connects to both databases, runs all 8 queries, displays results as ASCII tables, and prints a row-count comparison verdict.

---

## 8. AI Mode vs Static Mode

| Feature | AI Mode | Static Mode |
|---|---|---|
| Requires `DIAL_API_KEY` | Yes | No |
| Requires EPAM VPN | Yes | No |
| Handles renamed columns | Yes (semantic matching) | No (name must match) |
| Provides reasoning explanation | Yes | No |
| Deterministic output | No (model may vary) | Yes (always identical) |
| Speed | ~2–5 seconds per table | <100 ms per table |
| Fallback behavior | Falls back to static on error | N/A |

**AI mode activates automatically when `DIAL_API_KEY` is set in `.env`.** If the key is missing, the API is unreachable, or the model returns unparseable JSON, the pipeline falls back to static mode with a warning — generation always succeeds.

Both modes produce identical SQL output for tables with no renamed columns and standard type mappings. AI mode adds value for tables with column renames, ambiguous types, or complex business context that benefits from model reasoning.

---

## 9. Available AI Models

The tool connects to EPAM DIAL — a unified API gateway that provides access to models from multiple providers through a single OpenAI-compatible endpoint.

**EPAM VPN is required to reach `ai-proxy.lab.epam.com`.**

| Provider | Model ID | Notes |
|---|---|---|
| OpenAI | `gpt-5` | Frontier — highest quality |
| OpenAI | `gpt-5.6-terra-2026-07-09` | Latest GPT-5 dated snapshot |
| OpenAI | `gpt-4o` | Default — best balance of accuracy and speed |
| OpenAI | `gpt-4o-mini` | Fast, lower cost — good for simple tables |
| OpenAI | `gpt-4-turbo` | 128k context — large schema tables |
| OpenAI | `o3` / `o3-mini` / `o4-mini` | Reasoning models |
| Anthropic | `anthropic.claude-sonnet-5` | Top Anthropic model |
| Anthropic | `anthropic.claude-opus-4` | Most powerful Claude |
| Anthropic | `anthropic.claude-haiku-4-5` | Fastest Claude |
| Google | `gemini-2.5-pro` | Very large context window |
| Google | `gemini-2.0-flash` | Fast multimodal |
| Meta | `meta-llama-3-1-405b-instruct` | Largest open-weight model |
| Mistral | `mistral-large-2` | European flagship LLM |

Select a model per run: `--model gpt-4o-mini`
Set a session default: `DIAL_MODEL=gpt-4o` in `.env`
Browse interactively: `python validate_cli.py list-models`

---

## 10. Normalization Rules Catalog

Every column value on both sides is wrapped as:

```sql
COALESCE(CAST(<rule_expression> AS TEXT/STRING), '<<NULL>>')
```

The `<<NULL>>` sentinel converts SQL NULLs to a text placeholder so NULLs are comparable across databases as regular string values.

| Rule ID | Triggers On | PostgreSQL Expression | Snowflake Expression |
|---|---|---|---|
| `boolean` | `boolean` | `CASE WHEN col THEN '1' ELSE '0' END` | `CASE WHEN col THEN '1' ELSE '0' END` |
| `numeric` | `numeric`, `decimal`, `float`, `double` | `ROUND(CAST(col AS NUMERIC), 2)` | `ROUND(col::FLOAT, 2)` |
| `timestamp_ntz` | `timestamp without time zone` | `TO_CHAR(col, 'YYYY-MM-DD HH24:MI:SS')` | `TO_VARCHAR(col, 'YYYY-MM-DD HH24:MI:SS')` |
| `timestamp_tz` | `timestamp with time zone` | `TO_CHAR(col AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')` | `TO_VARCHAR(CONVERT_TIMEZONE('UTC', col), 'YYYY-MM-DD HH24:MI:SS')` |
| `date` | `date` | `TO_CHAR(col, 'YYYY-MM-DD')` | `TO_VARCHAR(col, 'YYYY-MM-DD')` |
| `text` | `text`, `varchar`, `char` | `TRIM(col)` | `TRIM(col)` |
| `uuid` | `uuid` | `UPPER(TRIM(CAST(col AS TEXT)))` | `UPPER(TRIM(col::STRING))` |
| `integer` | `integer`, `bigint`, `smallint`, `serial` | `CAST(col AS TEXT)` | `col::STRING` |
| `json` | `json`, `jsonb` | `col::jsonb::text` | `TO_JSON(PARSE_JSON(col))` |
| `bytea` | `bytea` | `encode(col, 'hex')` | `LOWER(HEX_ENCODE(col))` |
| `hstore` | `hstore` (USER-DEFINED) | `TRIM(CAST(col AS TEXT))` | `TRIM(col::STRING)` |
| `text` (fallback) | Everything else | `TRIM(col)` | `TRIM(col)` |

Rules are matched in specificity order. The `text` rule is registered last as a wildcard catch-all — any column type not matched by a more specific rule falls through to it.

### Rule Application Order (innermost to outermost)

```
1. Type-specific inner expression  (integer → cast, uuid → upper, json → normalize)
2. Boolean conversion              (CASE WHEN → '1'/'0')
3. Timestamp timezone conversion   (UTC normalization)
4. Timestamp / Date format         (YYYY-MM-DD HH24:MI:SS)
5. Numeric rounding                (ROUND to 2dp)
6. Text trimming                   (TRIM)
7. NULL placeholder                ← ALWAYS LAST: COALESCE(…, '<<NULL>>')
```

---

## 11. Generated Output — 8 Validation Queries

For every table pair, the tool generates **8 SQL queries** written to a single `.sql` file:

| Query | Label | Purpose | Run On |
|---|---|---|---|
| ① | `ROW COUNT — PostgreSQL` | `SELECT COUNT(*) AS source_row_count` | PostgreSQL |
| ② | `ROW COUNT — Snowflake` | `SELECT COUNT(*) AS target_row_count` (+ Fivetran filter if applicable) | Snowflake |
| ③ | `MAIN VALIDATION — PostgreSQL` | Normalized full-scan SELECT — every column wrapped in its rule expression | PostgreSQL |
| ④ | `MAIN VALIDATION — Snowflake` | Same, Snowflake dialect, same column aliases as ③ for direct comparison | Snowflake |
| ⑤ | `NULL % — PostgreSQL` | Per-column NULL percentage | PostgreSQL |
| ⑥ | `NULL % — Snowflake` | Per-column NULL percentage | Snowflake |
| ⑦ | `DISTINCT COUNT — PostgreSQL` | Distinct value count per column | PostgreSQL |
| ⑧ | `DISTINCT COUNT — Snowflake` | Distinct value count per column | Snowflake |

### How to use the output

```
① vs ②  — Row counts must match (or be within tolerance)
③ vs ④  — Export both to CSV; diff them row-by-row — must be identical
⑤ vs ⑥  — NULL percentages per column must match
⑦ vs ⑧  — Distinct counts per column must match (large differences indicate data drift)
```

### Example generated SQL header

```sql
-- ======================================================================
-- MIGRATION VALIDATOR — Generated Validation Queries
-- Table        : events
-- Source       : postgresql://public.events
-- Target       : snowflake://dev_edge_bronze.storedge_fms_public.EVENTS
-- Generated    : 2026-08-07T14:22:01.384521
-- Generated by : AI
-- AI Model     : gpt-4o
-- ======================================================================
-- HOW TO USE:
--   ① Run on PostgreSQL  → compare count with ②
--   ② Run on Snowflake   → compare count with ①
--   ③ Run on PostgreSQL  → export to CSV
--   ④ Run on Snowflake   → export to CSV
--   Compare ③ vs ④ row-by-row — must be IDENTICAL
--   ⑤ Run on PostgreSQL  → compare NULL % with ⑥
--   ⑥ Run on Snowflake   → compare NULL % with ⑤
--   ⑦ Run on PostgreSQL  → compare distinct counts with ⑧
--   ⑧ Run on Snowflake   → compare distinct counts with ⑦
-- ======================================================================
```

---

## 12. YAML Output

Alongside every `.sql` file, a `.yaml` file is written with the same queries structured for automated test runners:

```yaml
validations:
  - validation_type: row_count
    source_table_name: public.events
    sourcequery: |
      SELECT COUNT(*) AS source_row_count
      FROM public.events;
    target_table_name: dev_edge_bronze.storedge_fms_public.EVENTS
    targetquery: |
      SELECT COUNT(*) AS target_row_count
      FROM dev_edge_bronze.storedge_fms_public.EVENTS
      WHERE _FIVETRAN_ACTIVE = TRUE;

  - validation_type: main_validation
    source_table_name: public.events
    sourcequery: |
      SELECT
          COALESCE(CAST(CAST(event_id AS TEXT) AS TEXT), '<<NULL>>') AS event_id_normalized,
          ...
    target_table_name: dev_edge_bronze.storedge_fms_public.EVENTS
    targetquery: |
      SELECT
          COALESCE(CAST(event_id::STRING AS STRING), '<<NULL>>') AS event_id_normalized,
          ...
```

---

## 13. Custom Rule Book

The rule book has two layers:

**Base rules** — built into the tool. These cover all standard PostgreSQL to Snowflake type mappings and are never modified.

**Learned rules** — your project-specific rules. Stored in `src/rule_book_learned.json`. Automatically injected into every future AI prompt.

### Add a custom rule

```powershell
python validate_cli.py add-rule
```

The interactive wizard collects:
- Rule ID (snake_case)
- Display name
- Description (plain English)
- When to apply (trigger description)
- Source (PostgreSQL) type that triggers this
- Target (Snowflake) type that triggers this
- PostgreSQL SQL template — use `{col}` as the column placeholder
- Snowflake SQL template — use `{col}` as the column placeholder
- Optional example or scenario

Example custom rule — phone number normalization:

```
Rule ID     : phone_strip
Description : Strip all non-digit characters from phone number fields
When        : VARCHAR phone columns migrated from PG to Snowflake
PG SQL      : REGEXP_REPLACE({col}, '[^0-9]', '', 'g')
SF SQL      : REGEXP_REPLACE({col}, '[^0-9]', '')
Example     : '+1 (555) 123-4567' becomes '15551234567'
```

### View the rule book

```powershell
python validate_cli.py rules
```

Displays all base rules and learned rules with their SQL templates and trigger types, plus the rule application order.

---

## 14. Running Queries — Manual vs Terminal Execution

### Option A — Manual Execution

Open the generated `.sql` file in any SQL client (DBeaver, DataGrip, psql, SnowSQL) and run each numbered query block against its respective database. Export queries ③ and ④ to CSV and diff them.

### Option B — Terminal Execution (built-in)

After generation, the CLI prompts you to run the queries immediately. It connects to both databases using the credentials from `.env`, executes each query, and prints results as ASCII tables in the terminal.

Row count comparison verdict is printed automatically:

```
  ════════════════════════════════════════════════════════════════
  ROW COUNT COMPARISON
  ────────────────────────────────────────────────────────────────
    PostgreSQL rows : 1,247,832
    Snowflake  rows : 1,247,832
  ✓ Row counts MATCH ✓  (1,247,832 rows)
  ════════════════════════════════════════════════════════════════
```

For mismatches within 1%, a warning is shown instead of an error (configurable tolerance).

---

## 15. Validation Reports

The tool includes a report generator (`src/report_generator.py`) that produces three output formats after a full automated validation run:

### JSON Report

Machine-readable format with complete per-table and per-column results:

```json
{
  "validation_id": "abc123def456",
  "timestamp": "2026-08-07T14:30:00",
  "overall_status": "PASS",
  "summary": {
    "total_tables": 3,
    "passed_tables": 3,
    "total_source_rows": 1247832,
    "total_target_rows": 1247832,
    "overall_data_completeness_percentage": 100.0
  },
  "table_results": [...]
}
```

### HTML Report

Visual dashboard with overall status, data completeness percentage, per-table progress bars, and detailed comparison results. Saved to `validation_reports/report_TIMESTAMP.html`.

### Text Report

Human-readable summary suitable for emails or ticket comments:

```
================================================================================
MIGRATION VALIDATION REPORT
================================================================================

Overall Status: PASS
Data Completeness: 100.00%
Success Rate: 100.00%

Source Rows: 1,247,832   Target Rows: 1,247,832   Matched: 1,247,832

Table: events       PASS   (1,247,832 rows)
Table: users        PASS   (   52,441 rows)
Table: locations    PASS   (    3,198 rows)
```

---

## 16. Data Security

### What stays local

- All database credentials are stored only in your local `.env` file.
- `.env` is never committed to version control (it is listed in `.gitignore`).
- The `check_connections.py` health checker masks passwords in terminal output: the first 4 characters are shown followed by `****`.
- No actual table data is ever read from your databases. The extractors only query `information_schema.columns` / `INFORMATION_SCHEMA.COLUMNS` — schema metadata only.
- Generated `.sql` and `.yaml` files are written to `validation_sql/` which is local only.

### What is sent to the DIAL API (AI mode only)

When AI mode is active, the following is sent to the EPAM DIAL endpoint over HTTPS:

- **Column metadata only:** column names, data types, nullability flags, and ordinal positions. No actual data values.
- **Table name and schema name:** used as context for the AI to understand the domain.
- **The rules catalog:** the full `rules_catalog.json` content, which is static reference data.
- **Your learned rules** (if any): the SQL templates you defined, not any data.

**No passwords, no connection strings, no actual row data, and no credentials are ever sent to the AI API.**

### DIAL API security

- The DIAL endpoint is hosted on EPAM infrastructure (`ai-proxy.lab.epam.com`).
- Access requires EPAM VPN — the endpoint is not publicly reachable.
- All API calls use HTTPS with the `Api-Key` header.
- The API key is read from the environment variable `DIAL_API_KEY`, never hardcoded.
- `temperature=0` is set on all AI calls to prevent randomness and make outputs reproducible.

### Credential handling summary

| Credential | Stored Where | Sent Where |
|---|---|---|
| PostgreSQL password | `.env` (local only) | PostgreSQL server only |
| Snowflake password | `.env` (local only) | Snowflake service only |
| DIAL API key | `.env` (local only) | EPAM DIAL endpoint (HTTPS, VPN-gated) |

### Running without the AI (zero external calls)

If you do not set `DIAL_API_KEY`, the tool operates entirely offline. No outbound connections are made to any external service. Only your local PostgreSQL and Snowflake databases are contacted.

---

## 17. Common Issues and Troubleshooting

### PostgreSQL connection fails

```
✗ PostgreSQL connection FAILED: could not connect to server
```

Checks:
1. Is PostgreSQL running? `pg_isready -h <host> -p 5432`
2. Is the database name correct? `psql -U <user> -l`
3. Is a firewall or VPN blocking port 5432?
4. Is `SOURCE_PASSWORD` correct in `.env`?

### Snowflake connection fails

```
✗ Snowflake connection FAILED: Failed to connect
```

Checks:
1. Account format must be `ORG_NAME-ACCOUNT_NAME` (e.g. `ZJAUJWQ-EP12783`)
2. Verify credentials work at `https://app.snowflake.com`
3. Check `SNOWFLAKE_DATABASE` and `SNOWFLAKE_SCHEMA` exist
4. MFA — if MFA is required, use key-pair authentication instead of password
5. Are you on EPAM VPN?

### AI mode not activating

```
⚠ DIAL_API_KEY is not set — static fallback will be used
```

Solution: Connect to EPAM VPN, then set `DIAL_API_KEY` in your `.env` file. Run `python check_connections.py` to verify the DIAL connection.

### No tables found in schema

```
⚠ Schema 'public' exists but has NO tables
```

Check `SOURCE_SCHEMA` in `.env`. The schema must exist and contain BASE TABLE objects (not views only).

### Column count mismatch between PG and Snowflake

The static mapper will only include columns that exist on both sides. The AI mapper will note unmatched columns in its explanation and set `skip_validation=true` for them. Skipped column names are printed in the generation summary.

### `openai` package not installed

```
✗ openai NOT FOUND → run: pip install openai>=1.0.0
```

Run `pip install openai>=1.0.0`. The `openai` package is required for AI mode. Static mode works without it.

---

## 18. Extending the Tool

### Add a new normalization rule

1. Create `src/rules/mytype_rule.py` inheriting from `BaseValidationRule`.
2. Implement `_pg_expression(col)` and `_sf_expression(col)`.
3. Register it in `src/rules/base_rule.py` `RuleRegistry` before `TextRule` (which is the wildcard catch-all — rules after it are never reached).
4. Add an entry to `src/rules_catalog.json` so the AI receives its description in future prompts.

### Add a project-specific rule without touching code

Use the CLI wizard — no code changes required:

```powershell
python validate_cli.py add-rule
```

See [Section 13](#13-custom-rule-book) for details.

### Support a new target database (e.g. BigQuery)

1. Add `sql_extractor/bigquery_extractor.py` inheriting from `BaseExtractor`.
2. Add BigQuery-dialect expressions to every rule class (`_bq_expression` method).
3. Add a dialect flag to `SQLQueryGenerator` and `YAMLConfigWriter`.

### Swap the AI provider

Edit `ai_transformation/ai_rule_mapper.py`. The DIAL API is OpenAI-compatible — change `api_base` and `model`. Any provider with an OpenAI-compatible `/chat/completions` endpoint (Azure OpenAI, OpenAI direct, local Ollama, etc.) works without further changes.

### Change the output location

Edit `src/generated_queries/query_output_manager.py` and update the `OUTPUT_DIR` constant. Currently defaults to `validation_sql/` in the project root.
