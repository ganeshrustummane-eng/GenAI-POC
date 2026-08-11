# 📘 Migration Validator — Complete Project Documentation

> **What this tool does in one sentence:**
> You tell it a database name, schema, and table — it connects to both PostgreSQL
> and Snowflake, asks GPT-4o to figure out the right transformation rules,
> and gives you **8 ready-to-run SQL queries** to validate your migration data.
> You run those queries yourself. Nothing executes automatically.

---

## 📋 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture — How Everything Connects](#2-architecture--how-everything-connects)
3. [File Map — Every File Explained](#3-file-map--every-file-explained)
4. [The Evolving Rule Book](#4-the-evolving-rule-book)
5. [CLI Tool — Complete Command Reference](#5-cli-tool--complete-command-reference)
6. [What Queries Get Generated](#6-what-queries-get-generated)
7. [Data Flow — Step by Step](#7-data-flow--step-by-step)
8. [Configuration Reference (.env)](#8-configuration-reference-env)
9. [PostgreSQL → Snowflake Type Mapping](#9-postgresql--snowflake-type-mapping)
10. [How AI Works in This Tool](#10-how-ai-works-in-this-tool)
11. [What Was Done (History)](#11-what-was-done-history)
12. [What To Do Next](#12-what-to-do-next)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Project Overview

### The Problem
You migrated data from **PostgreSQL → Snowflake**. Now you need to verify:
- Did all rows make it across? (**Row completeness**)
- Are NULL values the same in both? (**NULL consistency**)
- Are there duplicate primary keys in Snowflake? (**Duplicate detection**)
- Are any rows missing from Snowflake by primary key? (**Missing rows**)
- Do column values match after accounting for type differences? (**Value integrity**)

### The Old Way (Static — Deprecated)
You had to hard-code every column, every data type, and every rule in Python.
Every new table meant editing Python code. That was `main_example.py`.

### The New Way (Dynamic — Current)
You type:
```
database name → fms
schema       → public
table        → events
```
The tool does everything else — connects, discovers columns, asks AI, generates SQL.

### The AI Layer
Between schema extraction and SQL generation sits **GPT-4o via EPAM DIAL**.
The AI reads your column types, reads the full rule book, and decides which
transformation rules to apply per column. It then returns a structured JSON
plan that the tool uses to build the final SQL queries.

---

## 2. Architecture — How Everything Connects

```
┌─────────────────────────────────────────────────────────────────────┐
│                        YOU (the user)                               │
│                                                                     │
│   python validate_cli.py generate                                   │
│   > database: fms                                                   │
│   > schema:   public                                                │
│   > table:    events                                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     validate_cli.py  (CLI)                          │
│   Interactive menu + argument parser                                │
│   Collects: db, schema, table, pk hints                             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     query_builder.py  (Orchestrator)                │
│                                                                     │
│   Step 1 ──► schema_extractor.py                                    │
│              ├── PostgresSchemaExtractor → connects to PG           │
│              │   queries information_schema.columns                 │
│              │   returns List[ColumnInfo]                           │
│              └── SnowflakeSchemaExtractor → connects to Snowflake   │
│                  queries INFORMATION_SCHEMA.COLUMNS                 │
│                  returns List[ColumnInfo]                           │
│                                                                     │
│   Step 2 ──► rule_book.py                                           │
│              ├── loads rules_catalog.json  (base rules)             │
│              └── loads rule_book_learned.json  (your rules)         │
│              builds a formatted prompt block                        │
│                                                                     │
│   Step 3 ──► AI (GPT-4o via DIAL)                                   │
│              receives: column pairs + full rule book                │
│              returns:  JSON { column_mappings, explanation }        │
│              fallback: static type-pair matching if no DIAL key     │
│                                                                     │
│   Step 4 ──► SQL generation                                         │
│              transformation_rules.py applies rules per column       │
│              builds 8 SQL queries (see Section 6)                   │
│                                                                     │
│   Step 5 ──► Output                                                 │
│              prints queries to terminal                             │
│              saves to validation_sql/<table>_validation.sql         │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    YOU run the queries manually                      │
│                                                                     │
│   pgAdmin / psql        →  run queries ①③⑤⑧                        │
│   Snowflake Web UI      →  run queries ②④⑥⑦                        │
│   Compare ③ vs ④        →  validate data completeness               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. File Map — Every File Explained

```
Migration-validator/
│
├── .env                          ← YOUR credentials (never commit this)
├── .env.example                  ← Template — copy to .env and fill in
├── requirements.txt              ← pip install -r requirements.txt
│
├── src/
│   │
│   │  ── ENTRY POINTS ──────────────────────────────────────────────
│   ├── validate_cli.py           ← ★ MAIN TOOL — run this every day
│   │                                Interactive CLI with 4 commands
│   │
│   ├── check_connections.py      ← Health checker — run this first
│   │                                Verifies packages, env vars, DBs, AI
│   │
│   ├── main_dynamic.py           ← Alternative entry point (code-based)
│   │                                Edit SINGLE_TABLE_CONFIG and run
│   │
│   │  ── CORE ENGINE ─────────────────────────────────────────────
│   ├── query_builder.py          ← Orchestrates the 3-step pipeline
│   │                                schema → AI → SQL generation
│   │
│   ├── schema_extractor.py       ← Live schema extraction
│   │                                PostgresSchemaExtractor
│   │                                SnowflakeSchemaExtractor
│   │                                SchemaComparator (side-by-side diff)
│   │
│   ├── rule_book.py              ← Evolving rule book manager
│   │                                Loads base + learned rules
│   │                                Builds AI prompt injection block
│   │                                Saves new rules to disk
│   │
│   ├── transformation_rules.py   ← Applies rules to column expressions
│   │                                Takes rule list → returns SQL fragment
│   │
│   ├── sql_generators.py         ← SQL template engine
│   │                                Builds SELECT/COUNT queries per DB type
│   │
│   │  ── AI AGENT ──────────────────────────────────────────────
│   ├── ai_query_agent.py         ← DIAL/GPT-4o integration
│   │                                Builds prompts, calls API, parses JSON
│   │                                Used by dynamic_validator.py
│   │
│   │  ── RULE STORAGE ─────────────────────────────────────────
│   ├── rules_catalog.json        ← BASE rules (built-in, 14 rules)
│   │                                Do NOT edit manually
│   │
│   ├── rule_book_learned.json    ← YOUR learned rules (auto-created)
│   │                                Grows as you add rules via CLI
│   │                                Safe to commit to Git
│   │
│   │  ── SUPPORT MODULES ───────────────────────────────────────
│   ├── models.py                 ← All dataclasses and enums
│   │                                DatabaseConfig, ColumnMapping, etc.
│   │
│   ├── schema_discovery.py       ← ColumnInfo dataclass + row parsers
│   │
│   ├── database_connectors.py    ← Low-level DB connection classes
│   │                                PostgreSQLConnector, SnowflakeConnector
│   │                                ConnectorFactory.from_env()
│   │
│   ├── dynamic_validator.py      ← Full auto-execution validator
│   │                                Runs SQL and computes metrics
│   │                                Use when you want auto results
│   │
│   ├── report_generator.py       ← Writes JSON/HTML/TXT reports
│   │
│   └── main_example.py           ← OLD static entry point (deprecated)
│                                    Kept for reference only
│
├── validation_sql/               ← ★ GENERATED SQL SAVED HERE
│   ├── events_validation.sql
│   └── general_ledger_line_items_validation.sql
│
├── validation_reports/           ← Auto-execution reports (if used)
│   ├── dynamic_report_*.json
│   ├── dynamic_report_*.html
│   └── dynamic_report_*.txt
│
└── docs/
    ├── MIGRATION_VALIDATOR_DOCS.md   ← This file
    ├── EXECUTION_GUIDE.md
    └── AI_AGENT_GUIDE.md
```

---

## 4. The Evolving Rule Book

This is one of the most important concepts in the tool. The rule book is how
the AI knows what SQL transformations to apply to each column.

### How It Works

```
rules_catalog.json          rule_book_learned.json
(14 built-in rules)    +    (your rules — starts empty)
        │                           │
        └───────────┬───────────────┘
                    ▼
              rule_book.py
           (RuleBook manager)
                    │
                    ▼
         build_prompt_block()
       (formatted text block)
                    │
                    ▼
          Injected into AI prompt
          every single time you run
          "generate" command
```

### Built-In Base Rules (rules_catalog.json)

| Rule ID | What It Does | When Applied |
|---------|-------------|--------------|
| `BOOLEAN_CONVERSION` | `true/false` → `'TRUE'/'FALSE'` string | BOOLEAN columns |
| `NULL_STANDARDIZATION` | `NULL` → `'<NULL>'` sentinel | ALL nullable columns (always last) |
| `WHITESPACE_TRIM` | `TRIM(col)` removes leading/trailing spaces | VARCHAR/TEXT columns |
| `CASE_INSENSITIVE` | `LOWER(col)` for case-insensitive compare | VARCHAR/TEXT columns |
| `DATE_STANDARDIZATION` | `TO_CHAR(col, 'YYYY-MM-DD')` | DATE columns |
| `NUMERIC_PRECISION` | `ROUND(col, scale)` | NUMERIC/DECIMAL columns |
| `EMPTY_STRING_NULL` | Empty string `''` treated as NULL | VARCHAR columns |
| `INTEGER_CAST` | `CAST(col AS BIGINT/NUMBER)` | INT/SERIAL → NUMBER |
| `TIMESTAMP_TO_DATE` | Strips time part from timestamps | TIMESTAMP columns |
| `UUID_TO_VARCHAR` | `CAST(uuid AS VARCHAR)` | UUID columns |
| `JSON_SKIP` | Skip JSONB — mark ignore_validation=true | JSONB/JSON columns |
| `ARRAY_SKIP` | Skip ARRAY types | ARRAY columns |
| `BYTEA_SKIP` | Skip binary data | BYTEA columns |
| `TEXT_TO_NUMBER` | `CAST(text AS NUMERIC)` | TEXT→NUMBER conversions |

### Rule Chaining Order
Rules must be applied in this exact order (innermost first, outermost last):
```
integer_cast
→ uuid_to_varchar
  → boolean_conversion
    → timestamp_to_date
      → date_standardization
        → numeric_precision
          → text_to_number
            → empty_string_null
              → whitespace_trim
                → case_insensitive
                  → null_standardization   ← ALWAYS LAST/OUTERMOST
```

### Adding a New Learned Rule

Run the CLI and choose `add-rule`:
```powershell
python validate_cli.py add-rule
```

You will be asked:
```
Rule ID (snake_case)              : phone_number_strip
Display name                      : Phone Number Normalisation
What does this rule do?           : Strips all non-numeric characters from phone numbers
When to apply?                    : When source column is a VARCHAR phone number
Source type that triggers it      : VARCHAR
Target type that triggers it      : VARCHAR
PostgreSQL SQL template ({col})   : REGEXP_REPLACE({col}, '[^0-9]', '', 'g')
Snowflake SQL template  ({col})   : REGEXP_REPLACE({col}, '[^0-9]', '')
Optional example                  : phone_number column in customers table
```

After saving, `rule_book_learned.json` is updated. The next time you run
`generate`, this rule is **automatically included in the AI prompt**.
You never need to describe it again.

### The Learned Rules File (rule_book_learned.json)

```json
{
  "_comment": "Auto-generated by rule_book.py",
  "version": "1.0",
  "last_updated": "2025-07-14T10:30:00",
  "learned_rules": [
    {
      "id": "phone_number_strip",
      "display_name": "Phone Number Normalisation",
      "description": "Strips all non-numeric characters from phone numbers",
      "when_to_apply": "When source column is a VARCHAR phone number",
      "pg_sql_template": "REGEXP_REPLACE({col}, '[^0-9]', '', 'g')",
      "sf_sql_template": "REGEXP_REPLACE({col}, '[^0-9]', '')",
      "source_type": "VARCHAR",
      "target_type": "VARCHAR",
      "is_learned": true,
      "learned_at": "2025-07-14T10:30:00"
    }
  ]
}
```

> ✅ **This file is safe to commit to Git** — it's your team's shared rule memory.

---

## 5. CLI Tool — Complete Command Reference

The CLI is the **primary interface** for the tool. Always use this.

### Start the CLI

```powershell
cd C:\EPAM-Personal\Migration-validator
.venv\Scripts\activate
cd src
python validate_cli.py
```

This opens the **interactive menu**:
```
╔══════════════════════════════════════════════════════════════════╗
║        Migration Validator  —  AI Query Generator               ║
║        PostgreSQL  →  Snowflake  Data Completeness              ║
╚══════════════════════════════════════════════════════════════════╝

  AI Mode   : ✓ ACTIVE (GPT-4o via DIAL)
  Rule Book : 14 base + 0 learned rules

  What would you like to do?

    [1]  Generate validation SQL queries    ← Main workflow
    [2]  Show rule book
    [3]  Add a new rule to rule book
    [4]  List tables in both databases
    [q]  Quit
```

---

### Command: `generate` — Main Workflow

**Interactive mode** (prompts you for input):
```powershell
python validate_cli.py generate
```

**Direct arguments** (no prompts, fastest):
```powershell
python validate_cli.py generate \
    --db fms \
    --schema public \
    --table events \
    --sf-schema storedge_fms_public \
    --sf-table EVENTS \
    --pk event_id
```

**All arguments:**

| Argument | Description | Example |
|----------|-------------|---------|
| `--db` | PostgreSQL database name | `fms` |
| `--schema` | PostgreSQL schema name | `public` |
| `--table` | PostgreSQL table name | `events` |
| `--sf-schema` | Snowflake schema name | `storedge_fms_public` |
| `--sf-table` | Snowflake table name | `EVENTS` |
| `--pk` | Primary key column(s), comma-separated | `event_id` or `id,tenant_id` |

> If `--pk` is omitted, the tool auto-detects PKs by looking for columns
> named `id` or ending in `_id` with an integer type.

**What happens when you run generate:**
```
  [1/3] Connecting to databases and extracting schemas...
    ✓ Extracted 8 columns from PostgreSQL: fms.public.events
    ✓ Extracted 8 columns from Snowflake: dev_edge_bronze.storedge_fms_public.EVENTS

    Schema Comparison: public.events → storedge_fms_public.EVENTS
    Source columns : 8
    Target columns : 8
    Matched        : 8
    Type changes   : 3
      [TYPE CHANGED] event_id: INTEGER → NUMBER(38,0)
      [TYPE CHANGED] created_at: TIMESTAMP → TIMESTAMP_NTZ(9)
      [OK] event_name: VARCHAR(255) → VARCHAR(255)

  [2/3] Asking AI to assign transformation rules...
    ✓ AI assigned rules for 8 columns

  [3/3] Generating validation SQL queries...
    💾 SQL saved to: C:\...\validation_sql\events_validation.sql

  ══════════════════════════════════════════════════════════════════════
    📋 VALIDATION QUERIES  |  events
    Generated by : AI
  ══════════════════════════════════════════════════════════════════════
  ... (8 queries printed here)
```

---

### Command: `rules` — View Rule Book

```powershell
python validate_cli.py rules
```

Shows:
- All 14 base rules with their SQL templates
- All your learned rules with when they were added
- Total rule count

---

### Command: `add-rule` — Add a New Rule

```powershell
python validate_cli.py add-rule
```

Use this when:
- You discover the AI is applying the wrong transformation for a specific column type
- Your data has a custom encoding or format (phone numbers, product codes, etc.)
- You want to enforce a specific business rule for a column pattern

The rule is saved to `rule_book_learned.json` and injected into every future AI prompt automatically.

---

### Command: `list-tables` — Show Available Tables

```powershell
python validate_cli.py list-tables
```

Shows all tables in both:
- PostgreSQL (from `SOURCE_DATABASE.SOURCE_SCHEMA`)
- Snowflake (from `SNOWFLAKE_DATABASE.SNOWFLAKE_SCHEMA`)

Use this to confirm table names before running `generate`.

---

## 6. What Queries Get Generated

Every time you run `generate`, you get **8 SQL queries**. Here is what each one does and where to run it:

---

### Query ① — Row Count on PostgreSQL
```sql
-- Run on: PostgreSQL
SELECT COUNT(*) AS source_row_count FROM public.events;
```
**Purpose:** Get the total number of rows in the source table.

---

### Query ② — Row Count on Snowflake
```sql
-- Run on: Snowflake
SELECT COUNT(*) AS target_row_count
FROM dev_edge_bronze.storedge_fms_public.EVENTS;
```
**Purpose:** Get the total number of rows in the target table.

**How to use ① + ②:** Compare the two counts. They should be identical.
If they differ → rows were lost or duplicated during migration.

---

### Query ③ — Main Validation Query on PostgreSQL (normalised)
```sql
-- Run on: PostgreSQL
SELECT
    COALESCE(CAST(CAST(event_id AS BIGINT) AS TEXT), '<NULL>') AS event_id_normalized,
    COALESCE(CAST(LOWER(TRIM(event_name)) AS TEXT), '<NULL>') AS event_name_normalized,
    COALESCE(CAST(CASE WHEN is_active = true THEN 'TRUE'
                       WHEN is_active = false THEN 'FALSE'
                       ELSE 'NULL' END AS TEXT), '<NULL>') AS is_active_normalized,
    COALESCE(TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS'), '<NULL>') AS created_at_normalized
FROM public.events
ORDER BY event_id_normalized;
```
**Purpose:** Fetch all source data with type normalization applied so it can be compared to the Snowflake version.

---

### Query ④ — Main Validation Query on Snowflake (normalised)
```sql
-- Run on: Snowflake
SELECT
    COALESCE(CAST(CAST(EVENT_ID AS NUMBER) AS VARCHAR), '<NULL>') AS event_id_normalized,
    COALESCE(LOWER(TRIM(EVENT_NAME)), '<NULL>') AS event_name_normalized,
    COALESCE(CASE WHEN IS_ACTIVE = TRUE THEN 'TRUE'
                  WHEN IS_ACTIVE = FALSE THEN 'FALSE'
                  ELSE 'NULL' END, '<NULL>') AS is_active_normalized,
    COALESCE(TO_VARCHAR(CREATED_AT, 'YYYY-MM-DD HH24:MI:SS'), '<NULL>') AS created_at_normalized
FROM dev_edge_bronze.storedge_fms_public.EVENTS
ORDER BY event_id_normalized;
```
**Purpose:** Same data from Snowflake with the same normalization applied.

**How to use ③ + ④:** The two result sets should be **row-by-row identical**.
Export both to CSV and diff them, or compare in a SQL tool that supports set comparison.

---

### Query ⑤ — NULL % Check on PostgreSQL
```sql
-- Run on: PostgreSQL
SELECT
    COUNT(*) AS total_rows,
    ROUND(100.0 * SUM(CASE WHEN event_name IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2)
        AS event_name_null_pct,
    ROUND(100.0 * SUM(CASE WHEN created_at IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2)
        AS created_at_null_pct
FROM public.events;
```
**Purpose:** Shows what % of each column is NULL in the source.

---

### Query ⑥ — NULL % Check on Snowflake
Same structure as ⑤ but for the Snowflake target.

**How to use ⑤ + ⑥:** The NULL percentages per column should match.
A difference > 5% means NULLs were introduced or lost during migration.

---

### Query ⑦ — Duplicate PK Check on Snowflake
```sql
-- Run on: Snowflake
-- Expected result: 0 rows (no duplicates)
SELECT EVENT_ID, COUNT(*) AS cnt
FROM dev_edge_bronze.storedge_fms_public.EVENTS
GROUP BY EVENT_ID
HAVING COUNT(*) > 1
ORDER BY cnt DESC;
```
**Purpose:** Find any primary key values that appear more than once in Snowflake.
Expected result: **zero rows**. If rows appear here, data was duplicated during migration.

---

### Query ⑧ — Missing Rows Check
```sql
-- Step 1: Run on PostgreSQL — get all source PKs
SELECT event_id, CAST(event_id AS TEXT) AS pk_key
FROM public.events
ORDER BY event_id;

-- Step 2: Run on Snowflake — get all target PKs
SELECT EVENT_ID, CAST(EVENT_ID AS VARCHAR) AS pk_key
FROM dev_edge_bronze.storedge_fms_public.EVENTS
ORDER BY EVENT_ID;

-- Step 3: Compare the pk_key columns
-- Any pk_key in Step 1 missing from Step 2 = ROW MISSING IN TARGET
```
**Purpose:** Find which specific rows (by PK) are in the source but not in the target.

---

## 7. Data Flow — Step by Step

```
User Input
  │
  │  database="fms", schema="public", table="events"
  ▼
validate_cli.py
  │
  │  Passes params to QueryBuilder.build()
  ▼
query_builder.py — Step 1: Schema Extraction
  │
  ├──► PostgresSchemaExtractor.extract_columns("public", "events")
  │      SELECT column_name, data_type, is_nullable, ...
  │      FROM information_schema.columns
  │      WHERE table_schema='public' AND table_name='events'
  │      Returns: List[ColumnInfo]
  │
  └──► SnowflakeSchemaExtractor.extract_columns("storedge_fms_public", "EVENTS")
         SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, ...
         FROM dev_edge_bronze.INFORMATION_SCHEMA.COLUMNS
         WHERE TABLE_SCHEMA='STOREDGE_FMS_PUBLIC' AND TABLE_NAME='EVENTS'
         Returns: List[ColumnInfo]
  │
  ▼
query_builder.py — Step 2: AI Rule Assignment
  │
  ├──► rule_book.build_prompt_block()
  │      Combines base rules (rules_catalog.json)
  │      + learned rules (rule_book_learned.json)
  │      Returns: formatted text block
  │
  ├──► Build system prompt:
  │      "You are a Senior Data Migration QA Engineer.
  │       Here are the rules: [full rule book]
  │       Return JSON: { column_mappings: [...], explanation: '...' }"
  │
  ├──► Build user prompt:
  │      "Map these columns:
  │       source: event_id INTEGER → target: EVENT_ID NUMBER
  │       source: event_name VARCHAR → target: EVENT_NAME VARCHAR
  │       ..."
  │
  ├──► GPT-4o (via DIAL API) returns:
  │      {
  │        "column_mappings": [
  │          {
  │            "source_column": "event_id",
  │            "target_column": "EVENT_ID",
  │            "apply_rules": ["INTEGER_CAST", "NULL_STANDARDIZATION"],
  │            "primary_key": true
  │          },
  │          {
  │            "source_column": "event_name",
  │            "target_column": "EVENT_NAME",
  │            "apply_rules": ["WHITESPACE_TRIM", "CASE_INSENSITIVE", "NULL_STANDARDIZATION"]
  │          }
  │        ],
  │        "explanation": "event_id is INTEGER→NUMBER requiring integer_cast..."
  │      }
  │
  └──► (Fallback) If no DIAL_API_KEY:
         Static matching from rules_catalog.json trigger_type_pairs
  │
  ▼
query_builder.py — Step 3: SQL Generation
  │
  ├──► For each column mapping:
  │      transformation_rules.py.apply_rules(column, [RULE1, RULE2], DB_TYPE)
  │      Returns: "COALESCE(CAST(LOWER(TRIM(event_name)) AS TEXT), '<NULL>')"
  │
  ├──► Assemble 8 SQL queries
  │      (row count, main validation, null %, duplicate PK, missing rows)
  │
  └──► Save to validation_sql/events_validation.sql
  │
  ▼
Terminal Output
  Print all 8 queries with section headers
  (you copy them and run in your SQL client)
```

---

## 8. Configuration Reference (.env)

The `.env` file in the project root controls everything.

```env
# ─────────────────────────────────────────────────────────────────
# AI / DIAL — Required for AI mode. Without this, static rules used.
# Must be on EPAM VPN to reach https://ai-proxy.lab.epam.com
# ─────────────────────────────────────────────────────────────────
DIAL_API_KEY=dial-xxxxxxxxxxxxxxxxxxxxxx
DIAL_API_BASE=https://ai-proxy.lab.epam.com
DIAL_API_VERSION=2025-04-01-preview
DIAL_MODEL=gpt-4o

# ─────────────────────────────────────────────────────────────────
# PostgreSQL Source
# Used by: schema_extractor.py, database_connectors.py
# ─────────────────────────────────────────────────────────────────
SOURCE_HOST=localhost
SOURCE_PORT=5432
SOURCE_DATABASE=fms          ← database you connect to (can override per-call)
SOURCE_SCHEMA=public         ← default schema (can override per-call)
SOURCE_USERNAME=postgres
SOURCE_PASSWORD=your_password

# ─────────────────────────────────────────────────────────────────
# Snowflake Target
# Account format: ORGANIZATION_NAME-ACCOUNT_NAME
# Find in Snowflake: Admin > Account Details
# ─────────────────────────────────────────────────────────────────
SNOWFLAKE_ACCOUNT=ZJAUJWQ-EP12783
SNOWFLAKE_DATABASE=dev_edge_bronze
SNOWFLAKE_SCHEMA=storedge_fms_public
SNOWFLAKE_USERNAME=MANEGANESH99
SNOWFLAKE_PASSWORD=your_password
```

### Which file uses which variable?

| Variable | Used by |
|----------|---------|
| `DIAL_*` | `query_builder.py`, `ai_query_agent.py` |
| `SOURCE_*` | `schema_extractor.py`, `database_connectors.py`, `check_connections.py` |
| `SNOWFLAKE_*` | `schema_extractor.py`, `database_connectors.py`, `check_connections.py` |

---

## 9. PostgreSQL → Snowflake Type Mapping

This is the reference the AI uses to decide which rules to apply:

| PostgreSQL Type | Snowflake Type | Rules Applied |
|----------------|----------------|---------------|
| `SERIAL` / `BIGSERIAL` | `NUMBER(38,0)` | `INTEGER_CAST`, `NULL_STANDARDIZATION` |
| `INTEGER` / `INT` / `INT4` | `NUMBER(38,0)` | `INTEGER_CAST`, `NULL_STANDARDIZATION` |
| `BIGINT` / `INT8` | `NUMBER(38,0)` | `INTEGER_CAST`, `NULL_STANDARDIZATION` |
| `VARCHAR(n)` / `TEXT` | `VARCHAR` | `WHITESPACE_TRIM`, `CASE_INSENSITIVE`, `EMPTY_STRING_NULL`, `NULL_STANDARDIZATION` |
| `BOOLEAN` / `BOOL` | `BOOLEAN` | `BOOLEAN_CONVERSION`, `NULL_STANDARDIZATION` |
| `NUMERIC(p,s)` / `DECIMAL` | `NUMBER(p,s)` | `NUMERIC_PRECISION`, `NULL_STANDARDIZATION` |
| `DATE` | `DATE` | `DATE_STANDARDIZATION`, `NULL_STANDARDIZATION` |
| `TIMESTAMP` | `TIMESTAMP_NTZ` | `DATE_STANDARDIZATION`, `NULL_STANDARDIZATION` |
| `TIMESTAMPTZ` | `TIMESTAMP_TZ` | `DATE_STANDARDIZATION`, `NULL_STANDARDIZATION` |
| `UUID` | `VARCHAR` | `UUID_TO_VARCHAR`, `WHITESPACE_TRIM`, `NULL_STANDARDIZATION` |
| `JSONB` / `JSON` | `VARIANT` | `ignore_validation = true` — manual review |
| `ARRAY` | `ARRAY` / `VARIANT` | `ignore_validation = true` — manual review |
| `BYTEA` | `BINARY` | `ignore_validation = true` — binary data |

---

## 10. How AI Works in This Tool

### What the AI Receives

The AI (GPT-4o via EPAM DIAL) receives two messages:

**System Prompt** contains:
```
You are a Senior Data Migration QA Engineer.
[Full rule book — 14 base + N learned rules, with SQL templates]
Return ONLY a JSON object in this exact shape: {...}
Rules: NULL_STANDARDIZATION must be last, ignore JSONB/ARRAY/BYTEA, etc.
```

**User Prompt** contains:
```
Generate a validation query plan for this migration:
Source: PostgreSQL → public.events
Target: Snowflake  → dev_edge_bronze.storedge_fms_public.EVENTS
Primary key hints: [event_id]

Column pairs (8 total):
[
  { "source": { "column_name": "event_id", "data_type": "integer", ... },
    "target": { "column_name": "EVENT_ID", "data_type": "NUMBER", ... } },
  ...
]
Return the JSON validation plan.
```

### What the AI Returns

```json
{
  "column_mappings": [
    {
      "source_column": "event_id",
      "target_column": "EVENT_ID",
      "source_data_type": "integer",
      "target_data_type": "NUMBER",
      "primary_key": true,
      "ignore_validation": false,
      "apply_rules": ["INTEGER_CAST", "NULL_STANDARDIZATION"]
    },
    {
      "source_column": "event_name",
      "target_column": "EVENT_NAME",
      "source_data_type": "character varying",
      "target_data_type": "VARCHAR",
      "primary_key": false,
      "ignore_validation": false,
      "apply_rules": ["WHITESPACE_TRIM", "CASE_INSENSITIVE", "NULL_STANDARDIZATION"]
    }
  ],
  "explanation": "event_id is INTEGER in PG mapped to NUMBER in Snowflake — integer_cast required. All VARCHAR columns get whitespace_trim and case_insensitive for consistent comparison..."
}
```

### Static Fallback (No DIAL Key)

If `DIAL_API_KEY` is not set in `.env`, the tool falls back to **static rule matching**:
- Reads `rules_catalog.json` trigger_type_pairs
- Matches source/target type pairs mechanically
- Less accurate than AI — won't catch edge cases
- Still produces valid queries

---

## 11. What Was Done (History)

### Phase 1 — Static Model (Old, Deprecated)
- `main_example.py` — every column, type, and rule was **hard-coded in Python**
- To validate a new table you had to write Python code
- Rules were scattered across individual files

### Phase 2 — Dynamic Refactor (Done)

#### New Files Created:
| File | What It Added |
|------|--------------|
| `schema_extractor.py` | Live extraction from real DB connections |
| `dynamic_validator.py` | Full auto-pipeline (schema → AI → SQL → execute → report) |
| `main_dynamic.py` | New entry point with config-only editing |
| `check_connections.py` | 6-step health checker |

#### Problems Fixed:
- `sql_generators.py` was importing `TableMapping` which was removed — fixed
- `main_dynamic.py` config updated to point to real tables (`events`, `general_ledger_line_items`)
- `database_connectors.py` — added `ConnectorFactory.from_env()` method
- `.env.example` — restructured with clear sections and comments
- `ai_query_agent.py` — enriched system prompt with completeness goals and type mapping table

### Phase 3 — Query Generator + Evolving Rule Book (Done — Current Phase)

#### New Files Created:
| File | What It Added |
|------|--------------|
| `rule_book.py` | Rule book manager — loads base + learned rules, builds AI prompt block |
| `query_builder.py` | 3-step pipeline: schema → AI → SQL output only (no execution) |
| `validate_cli.py` | Interactive CLI with 4 commands |
| `rule_book_learned.json` | Auto-created when first rule is added |

#### Key Design Decisions:
1. **Output-only mode** — queries are printed/saved, never executed automatically
2. **Rule book is persistent** — learned rules survive restarts via JSON file
3. **AI prompt injection** — entire rule book is injected into every AI call
4. **Fallback always works** — no DIAL key = static rules, still produces valid SQL

---

## 12. What To Do Next

### Immediate Next Steps (Short Term)

#### 1. Test the CLI with Your Real Tables
```powershell
cd src
python validate_cli.py generate \
    --db fms --schema public --table events \
    --sf-schema storedge_fms_public --sf-table EVENTS
```
Take the generated SQL and run each query manually in:
- pgAdmin (queries ①③⑤⑧)
- Snowflake Web UI (queries ②④⑥⑦)

#### 2. Run for the Second Table
```powershell
python validate_cli.py generate \
    --db fms --schema public --table general_ledger_line_items \
    --sf-schema storedge_fms_public --sf-table GENERAL_LEDGER_LINE_ITEMS
```

#### 3. Review and Grow the Rule Book
After running queries, if you see a transformation the AI got wrong:
```powershell
python validate_cli.py add-rule
```
Describe the correct rule once. It's remembered forever.

---

### Medium Term Improvements

#### 4. Add a Results Comparison Script
Currently you run queries ③ and ④ manually and compare them visually.
Next improvement: a script that:
- Accepts the output of both queries as CSV files
- Computes a diff automatically
- Reports which rows differ and why

#### 5. Scheduled Validation
Run the CLI automatically on a schedule (e.g. after each ETL load):
```powershell
# Windows Task Scheduler / PowerShell script
python validate_cli.py generate `
    --db fms --schema public --table events `
    --sf-schema storedge_fms_public --sf-table EVENTS
```

#### 6. Multi-Table Config File
Instead of passing table names every time, support a YAML/JSON config:
```yaml
# validate_config.yaml
source_database: fms
tables:
  - source_schema: public
    source_table: events
    target_schema: storedge_fms_public
    target_table: EVENTS
    primary_key: [event_id]
  - source_schema: public
    source_table: general_ledger_line_items
    target_schema: storedge_fms_public
    target_table: GENERAL_LEDGER_LINE_ITEMS
    primary_key: [id]
```

#### 7. HTML/PDF Report for Manually Run Queries
Currently the manual query results stay in your SQL client.
Next step: a `report_from_csv.py` script that takes the CSV exports and
generates a formatted HTML report with pass/fail status.

---

### Long Term Improvements (Best Performance)

#### 8. Automated Comparison Execution
The `dynamic_validator.py` already exists and does automatic execution.
To use it properly, integrate it with a proper test runner:
```python
# pytest integration
def test_events_completeness():
    from dynamic_validator import DynamicValidator
    v = DynamicValidator()
    report = v.run(
        source_database="fms",
        source_schema="public",
        source_table="events",
        target_schema="storedge_fms_public",
        target_table="EVENTS",
    )
    assert report.overall_status == "PASS"
    assert report.overall_completeness_pct >= 99.0
```

#### 9. Rule Book Feedback Loop
After running queries, if the AI got a rule wrong, automatically update the rule book:
- If AI picked `CASE_INSENSITIVE` for a column that should be case-sensitive → add a learned rule to override

#### 10. Column-Level Mismatch Drill-Down
When Query ③ vs ④ shows differences, you want to know:
- Which specific rows differ?
- Which column caused the mismatch?

Add a drill-down query generator:
```sql
-- Find rows where event_name doesn't match after normalization
SELECT src.event_id, src.event_name_normalized, tgt.event_name_normalized
FROM [source_query] src
LEFT JOIN [target_query] tgt ON src.event_id_normalized = tgt.event_id_normalized
WHERE src.event_name_normalized != tgt.event_name_normalized;
```

#### 11. Support More Source Databases
Currently only PostgreSQL source is supported.
The `DatabaseType` enum already has `MSSQL`. Extend:
- `MSSQLSchemaExtractor` in `schema_extractor.py`
- Type mapping for SQL Server → Snowflake in AI prompt

#### 12. Web UI (Future)
Build a simple Flask/FastAPI web interface:
```
/              → Home — shows list of validated tables with status
/generate      → Form to enter db/schema/table and run generation
/rules         → View and add rules
/reports       → Browse historical SQL files
```

---

## 13. Troubleshooting

### ✗ `cannot import name 'TableMapping' from 'models'`

**Cause:** An old file still imports `TableMapping` which was removed in the dynamic refactor.
**Fix:** Already fixed in `sql_generators.py`. If it appears elsewhere:
```python
# Remove this:
from models import DatabaseType, TableMapping, ColumnMapping, ...
# Replace with:
from models import DatabaseType, ColumnMapping, ...
```

---

### ✗ `No columns found for public.events`

**Cause:** Wrong schema or table name spelling.
**Fix:**
```powershell
python validate_cli.py list-tables
# Confirm exact table names in both databases
```

---

### ✗ `DIAL API error: 401 Unauthorized`

**Cause:** DIAL_API_KEY wrong or expired, or not on EPAM VPN.
**Fix:**
1. Connect to EPAM VPN
2. Check `DIAL_API_KEY` in `.env` is valid
3. Tool still works without AI — static fallback produces valid SQL

---

### ✗ `PostgreSQL connection FAILED: password authentication failed`

**Fix:**
```powershell
# Verify password works:
psql -U postgres -d fms -c "SELECT 1"
# Update SOURCE_PASSWORD in .env
```

---

### ✗ `Snowflake connection FAILED: Failed to connect`

**Common causes:**
1. Account format wrong → must be `ZJAUJWQ-EP12783` (ORG-ACCOUNT with dash)
2. Database or schema doesn't exist → check in Snowflake web UI
3. Network blocking Snowflake → check firewall/VPN settings

---

### ⚠ AI assigned wrong rules

**What to do:**
1. Run `python validate_cli.py rules` to see what rules are available
2. Run `python validate_cli.py add-rule` to add the correct rule for that column type
3. Re-run `generate` — the new rule will be in the AI prompt and used correctly

---

### ⚠ Queries ③ and ④ produce different row counts when they should match

This usually means the ORDER BY is sorting differently.
**Fix:** Ensure both queries use the same ORDER BY column and the PK column
is correctly identified. Pass `--pk your_pk_column` to the generate command.
