# Migration Validator — Handover Guide

> **Audience:** New team member taking over this project.
> **Purpose:** Everything you need to run, configure, extend, and explain this tool.

---

## Table of Contents

1. [What This Tool Does](#1-what-this-tool-does)
2. [Project Structure](#2-project-structure)
3. [Setup — First Time](#3-setup--first-time)
4. [Running the Tool](#4-running-the-tool)
5. [How Column Matching Works](#5-how-column-matching-works)
6. [How Rules Work](#6-how-rules-work)
7. [How to Add a New Rule](#7-how-to-add-a-new-rule)
8. [AI Integration](#8-ai-integration)
9. [Output — What Gets Generated](#9-output--what-gets-generated)
10. [Batch Mode (Multiple Tables)](#10-batch-mode-multiple-tables)
11. [The YAML Config Files Explained](#11-the-yaml-config-files-explained)
12. [Fuzzy Match & Failure Thresholds](#12-fuzzy-match--failure-thresholds)
13. [Static Column Exclusion List](#13-static-column-exclusion-list)
14. [Common Workflows](#14-common-workflows)
15. [Environment Variables Reference](#15-environment-variables-reference)
16. [Key Design Decisions](#16-key-design-decisions)

---

## 1. What This Tool Does

**Migration Validator** compares data between a source database and Snowflake after a migration to confirm the data landed correctly.

Given a source table (PostgreSQL / MSSQL / Athena) and a Snowflake target table, it:

1. Extracts column schemas from both databases
2. Matches source columns to target columns (exact → fuzzy → AI)
3. Assigns a transformation rule to each column pair (e.g., cast boolean → `'1'/'0'`, normalize timestamps → UTC string)
4. Generates validation SQL queries that produce **comparable, normalized output** from both sides
5. Writes those queries into **YAML files** ready for an automated validation runner

The core idea: wrap every column in `COALESCE(CAST(expr AS TEXT), '<<NULL>>')` on both sides, then compare. SQL `NULL != NULL` breaks equality — the `<<NULL>>` sentinel makes nulls comparable across systems.

---

## 2. Project Structure

```
Migration-validator/
├── .env                          ← YOUR credentials (never commit)
├── .env.example                  ← template — copy this to .env
├── config/
│   └── bronze/
│       ├── count_validation/
│       │   └── bronze_count_validation.yaml   ← row counts, ALL tables in one file
│       └── data_validation/
│           ├── events_validation.yaml          ← column-level checks for "events"
│           ├── events_dynamic_suite.yaml       ← schema-aware checks (MIN/MAX, DUPE etc.)
│           ├── acctsoftware_validation.yaml
│           └── ...one pair per table...
└── src/
    ├── validate_cli.py           ← MAIN ENTRY POINT — run this
    ├── validation_pipeline.py    ← orchestrates the full flow
    ├── rules/
    │   ├── __init__.py           ← RuleRegistry + get_rule_for_type()
    │   ├── postgres_base_rules.py ← ALL rule classes live here
    │   ├── snowflake_rules.py    ← re-exports postgres_base_rules
    │   ├── mssql_rules.py
    │   └── athena_rules.py
    ├── matching/
    │   ├── exact_matcher.py      ← tier 1: exact + normalized name
    │   ├── fuzzy_matcher.py      ← tier 2: RapidFuzz scored candidates
    │   ├── candidate_matcher.py  ← orchestrates all tiers
    │   └── normalizer.py
    ├── ai/
    │   ├── prompt_builder.py     ← builds AI prompt per ambiguous column
    │   ├── rule_planner.py       ← calls DIAL API, one call per column
    │   └── response_parser.py
    ├── generated_queries/
    │   ├── sql_query_generator.py  ← builds SQL strings (in memory)
    │   ├── query_output_manager.py ← entry point for generation
    │   └── yaml_config_writer.py  ← writes YAML files to config/bronze/
    ├── batch/
    │   ├── config_parser.py      ← reads your tables.yaml batch file
    │   ├── batch_runner.py       ← runs N tables, parallel optional
    │   └── manifest_writer.py    ← writes runs/_manifest.json
    ├── sql_extractor/
    │   └── extractors.py         ← PostgresExtractor, SnowflakeExtractor, etc.
    ├── dynamic_suite/
    │   └── suite_generator.py    ← generates MIN/MAX/SUM/DUPE/VALUE_DIST checks
    ├── core/
    │   └── validation_plan.py    ← CanonicalValidationPlan dataclass
    └── learning/
        └── retrieval.py          ← LearnedRuleRetriever (feeds AI hints)
```

---

## 3. Setup — First Time

### Step 1 — Install dependencies

```bash
cd C:\EPAM-Personal\Migration-validator
pip install -r requirements.txt
```

Key packages: `openai`, `snowflake-connector-python`, `psycopg2`, `pyodbc`, `rapidfuzz`, `python-dotenv`, `pyyaml`

### Step 2 — Create your `.env`

```bash
copy .env.example .env
# Then edit .env with your actual credentials
```

Minimum required fields for a PostgreSQL → Snowflake run:

```env
# AI (optional — tool works without it, uses static rules)
DIAL_API_KEY=your_key_here
DIAL_MODEL=gpt-4o

# Snowflake target
SNOWFLAKE_ACCOUNT=ZJAUJWQ-EP12783
SNOWFLAKE_DATABASE=DEV_EDGE_BRONZE
SNOWFLAKE_SCHEMA=STOREDGE_FMS_PUBLIC
SNOWFLAKE_USERNAME=you@company.com
SNOWFLAKE_PASSWORD=your_password

# Source DB (slot 1)
SRC_1_TYPE=postgresql
SRC_1_HOST=localhost
SRC_1_PORT=5432
SRC_1_DATABASE=fms
SRC_1_SCHEMA=public
SRC_1_USERNAME=postgres
SRC_1_PASSWORD=secret
```

You can define up to 10 source connections as `SRC_1_*`, `SRC_2_*`, ... `SRC_10_*`. Each slot can be a different database type.

### Step 3 — Verify setup

```bash
cd src
python validate_cli.py setup      # interactive wizard checks .env
python validate_cli.py list-models  # confirms AI connectivity
python validate_cli.py list-tables  # confirms DB connectivity
```

---

## 4. Running the Tool

All commands run from the `src/` directory:

```bash
cd C:\EPAM-Personal\Migration-validator\src
```

### Interactive mode (beginner-friendly)

```bash
python validate_cli.py
```

Shows a numbered menu. Walk through it — pick source, pick target, pick table, generate.

### Single table (command line)

```bash
python validate_cli.py generate \
    --pg-table events \
    --sf-table EVENTS
```

The tool picks your source from `.env`. If you have multiple source slots, it prompts you to choose.

### Single table — skip all prompts

```bash
python validate_cli.py generate \
    --source 1 \
    --pg-table events \
    --sf-table EVENTS \
    --pg-schema public \
    --sf-schema STOREDGE_FMS_PUBLIC \
    --sf-database DEV_EDGE_BRONZE
```

`--source 1` picks `SRC_1_*` without prompting. If all Snowflake credentials are in `.env`, they are used without asking.

### Multiple tables in one command

```bash
python validate_cli.py generate \
    --source 1 \
    --tables events,customers,orders
```

Runs generate for each table in sequence using the same connection.

### Exclude extra columns

```bash
python validate_cli.py generate \
    --source 1 \
    --pg-table events \
    --sf-table EVENTS \
    --exclude legacy_col,internal_id
```

The static exclusion list (Fivetran/ETL audit columns) is always applied automatically. `--exclude` adds on top of it.

### View available AI models

```bash
python validate_cli.py list-models
```

### Manage connection profiles

```bash
python validate_cli.py profiles           # list saved profiles
python validate_cli.py profiles delete fms-dev
```

Profiles are stored at `~/.migration-validator/profiles.json` (outside the repo).

---

## 5. How Column Matching Works

Matching runs in three tiers. Each tier only processes columns that the previous tier couldn't resolve.

```
Source columns ──► TIER 1: Exact Match ──► resolved (confidence = 1.0)
                        │
                   unmatched
                        │
                        ▼
                   TIER 2: Fuzzy Match (RapidFuzz token_ratio)
                        │
                  score ≥ 0.95 ──► auto-accept (no AI)
                  score 0.80–0.95 ──► send to AI for review
                  score < 0.80 ──► FAIL (column skipped)
                        │
                   ai_needed
                        │
                        ▼
                   TIER 3: AI (RulePlanner via DIAL API)
                        │
                   resolved or still ambiguous ──► skip with warning
```

### Tier 1 — Exact Matching

Tried in this order:
1. **Explicit mapping override** — user supplied `{src_col: tgt_col}` in batch YAML
2. **Exact original name** — case-insensitive: `"amount"` matches `"AMOUNT"`
3. **Normalized name** — strips underscores/punctuation, lowercases: `"created_at"` matches `"CREATEDAT"`

### Tier 2 — Fuzzy Matching

- Uses `rapidfuzz.fuzz.token_ratio` (falls back to Python's `difflib` if not installed)
- Compares normalized column names
- Returns top 5 scored candidates per source column
- Thresholds (change via env vars):
  - `FUZZY_HIGH_CONFIDENCE=0.95` → auto-accept
  - `FUZZY_AI_REVIEW=0.80` → send to AI
  - Below `0.80` → column marked FAIL, skipped from validation

### Tier 3 — AI (RulePlanner)

- Only columns between 0.80 and 0.95 are sent to AI
- One API call per ambiguous column (not the full schema — efficient)
- AI receives: source column name/type, top 5 fuzzy candidates with scores
- AI returns: chosen target column, transformation rule, confidence, reason
- Falls back to best fuzzy candidate if AI is unavailable or returns an invalid answer

### What happens to unmatched/skipped columns

They appear in the generated plan JSON as `skip_validation: true`. They are excluded from the YAML files. The output summary reports how many were skipped and why.

---

## 6. How Rules Work

A **rule** is a Python class that knows how to express a column in normalized, comparable SQL on both the source and Snowflake sides.

### The abstract base class (`postgres_base_rules.py`)

Every rule extends `BaseValidationRule` and implements:

| Method | Purpose |
|---|---|
| `rule_name` | Unique snake_case ID (e.g. `"boolean"`, `"timestamp_ntz"`) |
| `trigger_pairs` | List of `(source_type_prefix, target_type_prefix)` tuples that trigger this rule. `"*"` is a wildcard. |
| `_pg_expression(col)` | The PostgreSQL SQL for the column (raw expression, no COALESCE) |
| `_sf_expression(col)` | The Snowflake SQL for the column (raw expression, no COALESCE) |

The base class `apply_postgresql()` and `apply_snowflake()` automatically wrap the expression:

```python
COALESCE(CAST(<your expression> AS TEXT), '<<NULL>>')   -- PostgreSQL
COALESCE(CAST(<your expression> AS STRING), '<<NULL>>')  -- Snowflake
```

You never write the null wrapping yourself.

### Built-in rules (registered in `src/rules/__init__.py`)

| Rule name | Trigger types (source → target) | What it does |
|---|---|---|
| `boolean` | `BOOLEAN → BOOLEAN` | `CASE WHEN col = true THEN '1' WHEN col = false THEN '0' ELSE NULL END` |
| `integer` | `INTEGER/BIGINT/SMALLINT → NUMBER` | `CAST(col AS TEXT/STRING)` |
| `numeric` | `NUMERIC/FLOAT/DECIMAL → NUMBER/FLOAT` | `ROUND(CAST(col AS NUMERIC), 2)` |
| `timestamp_tz` | `TIMESTAMPTZ → TIMESTAMP_TZ` | Converts to UTC string `'YYYY-MM-DD HH24:MI:SS'` |
| `timestamp_ntz` | `TIMESTAMP → TIMESTAMP_NTZ` | Formats as string `'YYYY-MM-DD HH24:MI:SS'` |
| `date` | `DATE → DATE` | Formats as `'YYYY-MM-DD'` |
| `uuid` | `UUID → VARCHAR` | `UPPER(TRIM(CAST(col AS TEXT)))` |
| `json` | `JSON/JSONB → VARIANT` | Normalizes JSON to string form |
| `bytea` | `BYTEA → BINARY` | Hex-encodes both sides |
| `hstore` | `HSTORE → TEXT` | `TRIM(CAST(col AS TEXT))` |
| `text` | `* → *` (wildcard, last) | `TRIM(col)` — catch-all |

### Rule lookup order matters

Registered in `src/rules/__init__.py` — **the first matching rule wins**. `TextRule` (wildcard `*`) is always registered last so it only catches what nothing else matched.

### Rule → SQL flow

```
CanonicalValidationPlan.active_mappings
    │ each entry has source_type + target_type
    ▼
_plan_to_rule_mappings()  ← in sql_query_generator.py
    │ calls get_rule_for_type(source_type, target_type)
    ▼
RuleRegistry.lookup()     ← iterates registered rules, first trigger_pairs match wins
    │ returns BaseValidationRule instance
    ▼
ColumnRuleMapping(source_col, target_col, rule=...)
    │
    ▼
SQLQueryGenerator.generate()
    │ calls rule.apply_postgresql(col) and rule.apply_snowflake(col) per column
    ▼
Full SELECT query strings  ──► YAMLConfigWriter ──► config/bronze/*.yaml
```

---

## 7. How to Add a New Rule

Suppose you want a rule that strips all non-digit characters from phone number columns.

### Step 1 — Write the rule class

Open `src/rules/postgres_base_rules.py` and add at the bottom (before `TextRule`):

```python
class PhoneStripRule(BaseValidationRule):
    """Strips non-digit characters from phone numbers for comparison."""

    @property
    def rule_name(self) -> str:
        return "phone_strip"

    @property
    def description(self) -> str:
        return "Phone: strip non-digit chars. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        # Trigger when source is VARCHAR/CHAR and target is VARCHAR/TEXT
        return [
            ("CHARACTER VARYING", "VARCHAR"),
            ("VARCHAR", "VARCHAR"),
            ("CHARACTER", "VARCHAR"),
        ]

    def _pg_expression(self, col: str) -> str:
        # PostgreSQL: REGEXP_REPLACE with 'g' flag (global)
        return f"REGEXP_REPLACE({col}, '[^0-9]', '', 'g')"

    def _sf_expression(self, col: str) -> str:
        # Snowflake: REGEXP_REPLACE without 'g' flag
        return f"REGEXP_REPLACE({col}, '[^0-9]', '')"
```

### Step 2 — Register the rule

Open `src/rules/__init__.py`. Add your import and registration BEFORE `TextRule`:

```python
from rules.postgres_base_rules import (
    ...existing imports...,
    PhoneStripRule,       # ← add this
)

...

_registry.register(UUIDRule())
_registry.register(JSONRule())
_registry.register(PhoneStripRule())   # ← add before TextRule
_registry.register(TextRule())         # MUST stay last
```

### Step 3 — What gets generated

For a column `phone_number` (type `CHARACTER VARYING`) matched to `PHONE_NUMBER` (type `VARCHAR`), the tool now generates:

**PostgreSQL side:**
```sql
COALESCE(CAST(REGEXP_REPLACE(phone_number, '[^0-9]', '', 'g') AS TEXT), '<<NULL>>') AS phone_number_normalized
```

**Snowflake side:**
```sql
COALESCE(CAST(REGEXP_REPLACE(PHONE_NUMBER, '[^0-9]', '') AS STRING), '<<NULL>>') AS phone_number_normalized
```

### Important: trigger_pairs specificity

Because `TextRule` has `trigger_pairs = [("*", "*")]` and is registered last, your rule only applies if its trigger_pairs are more specific AND it is registered before `TextRule`. If your column's types don't match your trigger_pairs, it falls through to `TextRule`.

If you want a rule to apply to a **specific column name** (not type-based), you should apply an explicit mapping in batch YAML or override at the plan level — the rule system is type-based, not name-based.

### Alternative: Add a hint rule (no code, AI-only)

For cases where you just want the AI to be aware of a pattern (e.g., "phone number columns should be stripped of dashes"):

```bash
python validate_cli.py add-rule
```

This saves to `src/rule_book_learned.json` and injects the description into every AI prompt as a hint. It does **not** change what SQL is generated — it only guides the AI's column matching/rule assignment decisions. For actual SQL changes, you need a Python rule class.

---

## 8. AI Integration

### What AI is used for

The AI is only invoked for **ambiguous column matches** — columns where fuzzy matching scored between 0.80 and 0.95. It is NOT used for obvious exact matches or for generating SQL (SQL comes from the rule classes).

### DIAL API (EPAM's AI proxy)

The tool calls EPAM's DIAL proxy which speaks the OpenAI API protocol:

```
Endpoint : https://ai-proxy.lab.epam.com
Auth     : Api-Key header (your DIAL_API_KEY from .env)
Protocol : Azure OpenAI client (openai Python package)
```

Supported models (set `DIAL_MODEL` in `.env`):

| Model ID | Best for |
|---|---|
| `gpt-4o` | Best quality, more expensive |
| `gpt-4o-mini` | Faster, cheaper, good for most cases |
| `claude-sonnet-5` | Good alternative |

### How a single AI call works

For each ambiguous column:

1. **PromptBuilder** (`src/ai/prompt_builder.py`) creates a focused prompt:
   - System: "You are a data migration expert. Choose from these candidates only. Return JSON only."
   - User: source column name, normalized name, data type, nullable, plus top 5 fuzzy candidates with their scores, plus any relevant learned examples

2. **RulePlanner** (`src/ai/rule_planner.py`) calls the DIAL API with `temperature=0, response_format=json_object`

3. AI returns:
   ```json
   {
     "status": "resolved",
     "source_column": "created_at",
     "target_column": "CREATED_AT",
     "source_type": "timestamp without time zone",
     "target_type": "TIMESTAMP_NTZ",
     "transformation_rule": "timestamp_ntz",
     "confidence": 0.97,
     "reason": "Name exact match normalized, compatible timestamp types."
   }
   ```

4. **ResponseParser** validates the chosen `target_column` is actually in the candidate list (prevents hallucination). Falls back to best fuzzy candidate if not.

### What happens without a DIAL API key

The tool falls back to `StaticRuleMapper` which does pure type-pair lookup — no network calls. All columns with exact or high-confidence fuzzy matches work perfectly. Columns with scores 0.80–0.95 are auto-accepted using the best fuzzy match without AI validation.

Set `DIAL_API_KEY=` (empty) in `.env` to explicitly disable AI.

### Learned rules

Custom rule knowledge injected into AI prompts (not SQL generation):

```bash
python validate_cli.py add-rule    # interactive wizard
python validate_cli.py rules       # view all learned rules
```

Stored in `src/rule_book_learned.json`. These are text descriptions the AI reads as context. They help AI make better decisions when column names are unusual or domain-specific.

---

## 9. Output — What Gets Generated

After running `generate`, three files are produced:

### File 1 — Data validation YAML

```
config/bronze/data_validation/<table>_validation.yaml
```

Contains three validation blocks for the table:
- `data_validation` — normalized full-scan SELECT comparing all columns
- `null_pct_validation` — NULL percentage per column
- `distinct_count_validation` — distinct value count per column

### File 2 — Count validation YAML (shared)

```
config/bronze/count_validation/bronze_count_validation.yaml
```

One shared file. Each new table's count check is **appended** (not overwritten). Contains simple `SELECT COUNT(*)` for source and target.

### File 3 — Dynamic suite YAML

```
config/bronze/data_validation/<table>_dynamic_suite.yaml
```

Schema-aware checks generated by the dynamic suite engine:
- `MIN_MAX` — range checks for numeric/date columns
- `SUM` — aggregate sum for numeric columns
- `DUPLICATE_CHECK` — duplicate row detection (if PK detected)
- `VALUE_DIST` — top value distribution for categorical columns
- `AI_RULE` — AI-recommended checks (if DIAL key present)

### Batch run artifacts

```
src/runs/batch_run_<timestamp>/
    _manifest.json           ← summary of all tables: status, duration, paths
    _execution_log.txt       ← human-readable log
    <table>/
        <table>_plan.json    ← full column mapping plan for that table
```

---

## 10. Batch Mode (Multiple Tables)

For migrating many tables at once, use a batch YAML file.

### Create `tables.yaml`

```yaml
source:
  type: postgresql        # postgresql | mssql | athena
  host: localhost         # omit to use SRC_1_HOST from .env
  port: 5432
  database: fms
  schema: public
  username: postgres
  password: secret

target:
  type: snowflake
  account: ZJAUJWQ-EP12783
  database: DEV_EDGE_BRONZE
  schema: STOREDGE_FMS_PUBLIC
  username: you@company.com
  password: secret

tables:
  - source_table: events
    target_table: EVENTS
    primary_keys: [event_id]

  - source_table: customers
    target_table: CUSTOMERS
    primary_keys: [customer_id]
    explicit_mappings:          # force specific column name mappings
      customer_id: CUST_ID
      email_address: EMAIL

  - source_table: order_lines
    target_table: ORDER_LINES
    primary_keys: [order_id, line_number]    # composite PK
    source_schema: orders_schema             # per-table schema override
    target_schema: ORDERS_SCHEMA

execution:
  parallel: true         # run tables concurrently
  max_workers: 4         # max concurrent threads
  fail_fast: false       # continue even if one table fails
```

### Run batch

```bash
python validate_cli.py batch --config tables.yaml

# Preview without executing:
python validate_cli.py batch --config tables.yaml --dry-run
```

### Batch output

- One `*_validation.yaml` per table → `config/bronze/data_validation/`
- One `*_dynamic_suite.yaml` per table → `config/bronze/data_validation/`
- Count entries appended → `config/bronze/count_validation/bronze_count_validation.yaml`
- Manifest → `src/runs/batch_run_<timestamp>/_manifest.json`

---

## 11. The YAML Config Files Explained

### Count validation YAML structure

```yaml
# config/bronze/count_validation/bronze_count_validation.yaml

tables:
  events:                          # table key
    validations:
      count_validation:
        source_table_name: events
        source: postgresql
        sourcequery: |
          SELECT COUNT(*) AS source_row_count
          FROM public.events;

        target_table_name: EVENTS
        target: snowflake
        targetquery: |
          SELECT COUNT(*) AS target_row_count
          FROM DEV_EDGE_BRONZE.STOREDGE_FMS_PUBLIC.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE;
```

### Data validation YAML structure

```yaml
# config/bronze/data_validation/events_validation.yaml
# Generated: 2026-08-13, By: AI (model: gpt-4o), Columns: 39

tables:
  events:
    validations:

      # Block 1: Compare every column, normalized, between source and target
      data_validation:
        source_table_name: events
        source: postgresql
        sourcecolumn: id           # primary key column (for join/reference)
        sourcequery: |
          SELECT
            COALESCE(CAST(CAST(id AS TEXT) AS TEXT), '<<NULL>>') AS id_normalized,
            COALESCE(CAST(TRIM(type) AS TEXT), '<<NULL>>') AS type_normalized,
            COALESCE(CAST(
              CASE WHEN needs_followup = true THEN '1'
                   WHEN needs_followup = false THEN '0'
                   ELSE NULL END
              AS TEXT), '<<NULL>>') AS needs_followup_normalized,
            COALESCE(CAST(
              TO_CHAR(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
              AS TEXT), '<<NULL>>') AS created_at_normalized,
            ...
          FROM public.events;

        target_table_name: EVENTS
        target: snowflake
        targetcolumn: ID
        targetquery: |
          SELECT
            COALESCE(CAST(CAST(ID AS STRING) AS STRING), '<<NULL>>') AS id_normalized,
            COALESCE(CAST(TRIM(TYPE) AS STRING), '<<NULL>>') AS type_normalized,
            COALESCE(CAST(
              CASE WHEN NEEDS_FOLLOWUP = TRUE THEN '1'
                   WHEN NEEDS_FOLLOWUP = FALSE THEN '0'
                   ELSE NULL END
              AS STRING), '<<NULL>>') AS needs_followup_normalized,
            COALESCE(CAST(
              TO_VARCHAR(CONVERT_TIMEZONE('UTC', CREATED_AT), 'YYYY-MM-DD HH24:MI:SS')
              AS STRING), '<<NULL>>') AS created_at_normalized,
            ...
          FROM DEV_EDGE_BRONZE.STOREDGE_FMS_PUBLIC.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE;

      # Block 2: NULL % per column
      null_pct_validation:
        source_table_name: events
        source: postgresql
        sourcequery: |
          SELECT
            COUNT(*) AS total_rows,
            ROUND(100.0 * SUM(CASE WHEN id IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS id_null_pct,
            ROUND(100.0 * SUM(CASE WHEN type IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS type_null_pct,
            ...
          FROM public.events;
        target_table_name: EVENTS
        target: snowflake
        targetquery: |
          SELECT COUNT(*) AS total_rows,
            ROUND(100.0 * SUM(CASE WHEN ID IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS id_null_pct,
            ...
          FROM DEV_EDGE_BRONZE.STOREDGE_FMS_PUBLIC.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE;

      # Block 3: Distinct value counts
      distinct_count_validation:
        source_table_name: events
        source: postgresql
        sourcequery: |
          SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT id) AS id_distinct_count,
            COUNT(DISTINCT type) AS type_distinct_count,
            ...
          FROM public.events;
        target_table_name: EVENTS
        target: snowflake
        targetquery: |
          SELECT COUNT(*) AS total_rows,
            COUNT(DISTINCT ID) AS id_distinct_count, ...
          FROM DEV_EDGE_BRONZE.STOREDGE_FMS_PUBLIC.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE;
```

**Important:** You do not edit these YAML files manually. Re-run `generate` to regenerate them. The files are the output, not the input.

---

## 12. Fuzzy Match & Failure Thresholds

| Score range | Outcome |
|---|---|
| `≥ 0.95` | Auto-accept, no AI review |
| `0.80 – 0.95` | Send to AI for validation |
| `< 0.80` | **FAIL** — column skipped, excluded from YAML |

Override via `.env`:

```env
FUZZY_HIGH_CONFIDENCE=0.95   # change auto-accept threshold
FUZZY_AI_REVIEW=0.80         # change AI-review lower bound
```

When a column fails (score < 0.80), it appears in the console output as skipped and is listed in the plan JSON's `unmatched_source_columns`. It is NOT included in any generated YAML.

If you see a column that should match but was skipped, use an **explicit mapping** in batch YAML:

```yaml
tables:
  - source_table: my_table
    target_table: MY_TABLE
    explicit_mappings:
      weirdly_named_col: TOTALLY_DIFFERENT_NAME    # forces match
```

---

## 13. Static Column Exclusion List

These columns are always excluded from validation regardless of what you specify. They are ETL/CDC audit columns that should never be compared between source and target:

```
_fivetran_synced    _fivetran_deleted   _fivetran_id        _fivetran_index
_fivetran_start     _fivetran_end       _fivetran_active
etl_insert_dt       etl_update_dt       etl_batch_id
dw_insert_dt        dw_update_dt        dw_batch_id
load_dt             load_ts             created_at_dw       updated_at_dw
record_source       hash_diff           dv_load_dt          dv_record_source
```

To add more columns to this list permanently, edit `STATIC_EXCLUDE_COLUMNS` in `src/validate_cli.py`.

To exclude additional columns for a single run:

```bash
python validate_cli.py generate --pg-table events --sf-table EVENTS \
    --exclude my_internal_col,another_col
```

---

## 14. Common Workflows

### Workflow A: Generate YAML for one table

```bash
cd src
python validate_cli.py generate --source 1 --pg-table events --sf-table EVENTS
```

Output in:
- `config/bronze/data_validation/events_validation.yaml`
- `config/bronze/data_validation/events_dynamic_suite.yaml`
- `config/bronze/count_validation/bronze_count_validation.yaml` (appended)

---

### Workflow B: Run all tables in batch

1. Create `tables.yaml` (see Section 10)
2. `python validate_cli.py batch --config tables.yaml --dry-run` — preview
3. `python validate_cli.py batch --config tables.yaml` — execute

---

### Workflow C: A column didn't match — force it

The column `cust_email` on source didn't match `EMAIL_ADDRESS` on target (score below threshold).

Add to batch YAML:

```yaml
tables:
  - source_table: customers
    target_table: CUSTOMERS
    explicit_mappings:
      cust_email: EMAIL_ADDRESS    # forced match
```

Re-run. The explicit mapping bypasses fuzzy matching entirely.

---

### Workflow D: Add a new data type rule

1. Write rule class in `src/rules/postgres_base_rules.py` (see Section 7)
2. Register it in `src/rules/__init__.py` before `TextRule`
3. Re-run generate — the new rule auto-applies to matching type pairs

---

### Workflow E: A table has no primary key detected

The tool will warn `"No PK detected — duplicate/missing row checks skipped."` and continue. The validation still runs on all columns but without the duplicate/missing-row checks in the dynamic suite.

To supply PK manually in batch mode:

```yaml
tables:
  - source_table: my_table
    target_table: MY_TABLE
    primary_keys: [id]           # declare it explicitly
```

---

### Workflow F: MSSQL source

```env
SRC_2_TYPE=mssqlserver
SRC_2_HOST=EPINHYDW1D68
SRC_2_PORT=1433
SRC_2_DATABASE=DevT5000
SRC_2_SCHEMA=dbo
SRC_2_USERNAME=AzureAD\GaneshRustumMane
SRC_2_PASSWORD=
```

Then: `python validate_cli.py generate --source 2 --pg-table AcctSoftware --sf-table ACCTSOFTWARE`

(The `--pg-table` flag accepts any source table name regardless of the actual DB type.)

---

### Workflow G: Athena source

```env
SRC_3_TYPE=athena
SRC_3_HOST=us-east-1           # repurposed as AWS region
SRC_3_DATABASE=my_glue_db
ATHENA_S3_OUTPUT=s3://my-bucket/athena-results/
```

AWS credentials via environment (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) or IAM role.

---

## 15. Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `DIAL_API_KEY` | Optional | EPAM DIAL API key. Without it, AI features are disabled. |
| `DIAL_MODEL` | Optional | AI model: `gpt-4o`, `gpt-4o-mini`, `claude-sonnet-5` |
| `DIAL_API_BASE` | Optional | Default: `https://ai-proxy.lab.epam.com` |
| `DIAL_API_VERSION` | Optional | Default: `2025-04-01-preview` |
| `SNOWFLAKE_ACCOUNT` | Yes | Format: `ORG-ACCOUNT` (no `.snowflakecomputing.com`) |
| `SNOWFLAKE_DATABASE` | Yes | Target database name |
| `SNOWFLAKE_SCHEMA` | Yes | Target schema name |
| `SNOWFLAKE_USERNAME` | Yes | Snowflake login email |
| `SNOWFLAKE_PASSWORD` | Yes | Snowflake password |
| `SRC_N_TYPE` | Yes | `postgresql`, `mssqlserver`, or `athena` |
| `SRC_N_HOST` | Yes | Source host (or AWS region for Athena) |
| `SRC_N_PORT` | Yes | Source port |
| `SRC_N_DATABASE` | Yes | Source database |
| `SRC_N_SCHEMA` | Yes | Source schema |
| `SRC_N_USERNAME` | Yes | Source DB username |
| `SRC_N_PASSWORD` | Sometimes | Source DB password (blank for Windows Auth) |
| `FUZZY_HIGH_CONFIDENCE` | No | Auto-accept threshold. Default: `0.95` |
| `FUZZY_AI_REVIEW` | No | AI-review lower bound. Default: `0.80` |
| `ATHENA_S3_OUTPUT` | Athena only | S3 URI for Athena query results |

---

## 16. Key Design Decisions

### Why `'<<NULL>>'` instead of empty string?

SQL `NULL != NULL` — you cannot compare NULLs with `=`. Using `''` would wrongly equate NULL with empty string. `'<<NULL>>'` is a sentinel string that is distinct from any real value and makes NULLs comparable across systems.

### Why is `_FIVETRAN_ACTIVE = TRUE` added to Snowflake queries?

Fivetran keeps a full history of every row. The `_FIVETRAN_ACTIVE = TRUE` filter selects only the current/latest version of each record. Without it, you'd be comparing the source's current rows against Fivetran's entire history, which always mismatches.

### Why does the tool write YAML instead of running queries directly?

The YAML files are consumed by a separate validation runner (external to this tool). The tool's job is to generate the correct queries — execution is separate. This keeps concerns separated and lets the runner handle scheduling, alerting, and result storage independently.

### Why one rule class per data type instead of one big SQL builder?

Each rule encapsulates exactly what it means to "normalize" a specific type. Adding a new type pair doesn't touch any existing logic. The registry + trigger_pairs system means rules are discoverable and testable independently.

### What is the `dynamic_suite` for vs the `data_validation`?

- **`data_validation`** — row-by-row column comparison. Catches value-level differences.
- **`dynamic_suite`** — aggregate-level checks. Catches range violations, duplicates, distribution shifts, and structural issues that row-by-row comparison might miss (or be too slow to catch on large tables).

Both are needed for a complete validation. Run `data_validation` first; if it passes, run `dynamic_suite` for deeper checks.
