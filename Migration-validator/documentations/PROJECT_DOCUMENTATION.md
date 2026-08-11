# Migration Validator — Complete Project Documentation

> **Audience:** Developers, QA engineers, data engineers, and anyone onboarding to this project.  
> **Purpose:** Single source of truth explaining what the tool does, how every component works, how 8 queries are designed, how validation is performed, and how the YAML output is structured and validated.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Architecture Overview](#3-architecture-overview)
4. [Directory Structure](#4-directory-structure)
5. [How the 8 Queries Work — Efficiency Analysis](#5-how-the-8-queries-work--efficiency-analysis)
6. [Validation Logic — How It Works](#6-validation-logic--how-it-works)
7. [YAML Output — Structure, Validation, and Correctness](#7-yaml-output--structure-validation-and-correctness)
8. [Transformation Rules — Complete Reference](#8-transformation-rules--complete-reference)
9. [Pipeline Internals](#9-pipeline-internals)
10. [Database Connectors and Schema Extraction](#10-database-connectors-and-schema-extraction)
11. [AI Integration (EPAM DIAL)](#11-ai-integration-epam-dial)
12. [Rule Book — Base and Learned Rules](#12-rule-book--base-and-learned-rules)
13. [CLI Reference](#13-cli-reference)
14. [Configuration (.env)](#14-configuration-env)
15. [Output Files](#15-output-files)
16. [Reports — JSON, HTML, Text](#16-reports--json-html-text)
17. [Fivetran Active Filter](#17-fivetran-active-filter)
18. [Common Issues and Solutions](#18-common-issues-and-solutions)
19. [Design Decisions and Future Work](#19-design-decisions-and-future-work)

---

## 1. Project Overview

The **Migration Validator** is a PoC (Proof of Concept) tool that automates **data completeness validation** when migrating tables from PostgreSQL (or SQL Server) to Snowflake.

### What It Does

```
PostgreSQL / SQL Server
        │
        │  (live schema extraction)
        ▼
Migration Validator
  ├── Extracts column metadata from both sides
  ├── AI matches source ↔ target columns (handles renames)
  ├── Assigns transformation rules per column type
  ├── Generates 8 SQL validation queries
  ├── Generates YAML config file
  └── Optionally executes queries and shows results
        │
        ▼
Snowflake
```

### What It Does NOT Do

- It does not move data — it only validates that data moved correctly.
- It does not fix mismatches — it reports them.
- It does not handle multi-source consolidation (Phase 1 PoC scope).
- Primary-key–based row matching is deferred to a future milestone.

---

## 2. Problem Statement

During database migration, source and target tables often have:

| Issue | Example |
|---|---|
| Different column names | `user_id` → `USER_ID` |
| Different data types | `BIT(0/1)` → `BOOLEAN(TRUE/FALSE)` |
| Different date formats | `01/10/2024` → `2024-01-10` |
| Trailing/leading whitespace | `' John '` vs `'John'` |
| Case differences | `'ACTIVE'` vs `'active'` |
| NULL vs empty string | `NULL` vs `''` |
| Numeric precision noise | `100` vs `100.00` |
| Timezone offsets | `2024-01-10T10:00:00+05:30` vs `2024-01-10T04:30:00Z` |

A direct column comparison produces **false failures**. The validator applies **normalization rules** before comparison so that semantically equal values are treated as equal.

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     validate_cli.py (CLI entry point)           │
│                 Interactive menu + command parser               │
└────────────────────────────┬────────────────────────────────────┘
                             │ calls
┌────────────────────────────▼────────────────────────────────────┐
│                   validation_pipeline.py                        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  Step 1: Extract schemas                                │   │
│   │          sql_extractor/postgres_extractor.py            │   │
│   │          sql_extractor/snowflake_extractor.py           │   │
│   ├─────────────────────────────────────────────────────────┤   │
│   │  Step 2–4: Deterministic Column Matching                │   │
│   │          matching/exact_matcher.py                      │   │
│   │          matching/fuzzy_matcher.py (RapidFuzz)          │   │
│   │          matching/confidence.py                         │   │
│   ├─────────────────────────────────────────────────────────┤   │
│   │  Step 5: AI for Ambiguous Columns Only                  │   │
│   │          ai/rule_planner.py                             │   │
│   │          ai_transformation/ai_rule_mapper.py            │   │
│   ├─────────────────────────────────────────────────────────┤   │
│   │  Step 6: Plan Validation                                │   │
│   │          validation/plan_validator.py                   │   │
│   │          core/validation_plan.py (CanonicalPlan)        │   │
│   ├─────────────────────────────────────────────────────────┤   │
│   │  Step 7: SQL + YAML Generation                          │   │
│   │          generated_queries/sql_query_generator.py       │   │
│   │          generated_queries/yaml_config_writer.py        │   │
│   │          generated_queries/query_output_manager.py      │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                             │ writes
           ┌─────────────────┴──────────────────┐
           │  validation_sql/                    │
           │    <table>_validation.sql   (8 SQL) │
           │    <table>_validation.yaml  (YAML)  │
           └─────────────────────────────────────┘
```

### Key Design Principles

- **No hardcoded schemas** — everything is resolved at runtime from live database connections.
- **PK-Free (Phase 1)** — queries operate on full table scans; no ORDER BY primary key.
- **AI only where needed** — exact and fuzzy matching resolve most columns; AI only handles genuinely ambiguous cases (saves tokens and cost).
- **Deterministic output** — given the same schema, same rules produce the same SQL every time.
- **Fivetran-aware** — automatically detects `_FIVETRAN_ACTIVE` on Snowflake and adds `WHERE _FIVETRAN_ACTIVE = TRUE` to filter only latest records.

---

## 4. Directory Structure

```
Migration-validator/
├── .env                            ← Database credentials (never commit!)
├── docker-compose.yml              ← PostgreSQL local test database
├── Problem-statement.md            ← Original PoC requirements
├── IMPLEMENTATION_GUIDE.md         ← Setup walkthrough
│
├── src/                            ← All Python source code
│   ├── validate_cli.py             ← CLI entry point (use this)
│   ├── validation_pipeline.py      ← End-to-end orchestrator
│   ├── models.py                   ← Data models (DatabaseConfig, ColumnMapping, etc.)
│   ├── validator.py                ← Core validation engine (run_validation)
│   ├── report_generator.py         ← JSON / HTML / Text report builder
│   ├── rule_book.py                ← Rule manager (base + learned rules)
│   │
│   ├── sql_extractor/              ← Schema extraction from live databases
│   │   ├── postgres_extractor.py   ← Reads pg_catalog / information_schema
│   │   └── snowflake_extractor.py  ← Reads INFORMATION_SCHEMA.COLUMNS
│   │
│   ├── rules/                      ← Strongly-typed SQL transformation rule classes
│   │   ├── base_rule.py            ← BaseValidationRule abstract class
│   │   ├── boolean_rule.py         ← CASE WHEN → '1'/'0'
│   │   ├── numeric_rule.py         ← ROUND(CAST(… AS NUMERIC), 2)
│   │   ├── date_rule.py            ← TO_CHAR / TO_VARCHAR 'YYYY-MM-DD'
│   │   ├── timestamp_ntz_rule.py   ← Timestamp without timezone
│   │   ├── timestamp_tz_rule.py    ← Timestamp with timezone → UTC
│   │   ├── text_rule.py            ← TRIM(…)
│   │   ├── integer_rule.py         ← CAST(… AS TEXT/STRING)
│   │   ├── uuid_rule.py            ← UPPER(TRIM(CAST(… AS TEXT)))
│   │   ├── json_rule.py            ← ::jsonb::text / TO_JSON(PARSE_JSON)
│   │   ├── bytea_rule.py           ← encode(…,'hex') / HEX_ENCODE
│   │   ├── null_rule.py            ← COALESCE(…, '<<NULL>>')
│   │   └── hstore_rule.py          ← hstore type handling
│   │
│   ├── matching/                   ← Column-pairing algorithms
│   │   ├── exact_matcher.py        ← Case-insensitive name match
│   │   ├── fuzzy_matcher.py        ← RapidFuzz similarity score
│   │   ├── confidence.py           ← Multi-factor confidence score
│   │   └── candidate_matcher.py    ← Orchestrates exact+fuzzy+confidence
│   │
│   ├── ai/                         ← AI rule planning (ambiguous only)
│   │   ├── rule_planner.py         ← Sends ambiguous cols to AI
│   │   ├── prompt_builder.py       ← Builds AI prompt
│   │   └── response_parser.py      ← Parses AI JSON response
│   │
│   ├── ai_transformation/          ← AI + static rule mapping
│   │   ├── ai_rule_mapper.py       ← Full AI mapping (legacy path)
│   │   ├── static_rule_mapper.py   ← Static type-based mapping
│   │   └── orchestrator.py         ← Chooses AI or static
│   │
│   ├── core/
│   │   └── validation_plan.py      ← CanonicalValidationPlan data model
│   │
│   ├── validation/
│   │   └── plan_validator.py       ← Structural integrity check on plan
│   │
│   ├── generated_queries/          ← SQL + YAML output generation
│   │   ├── sql_query_generator.py  ← Builds all 8 SQL queries
│   │   ├── yaml_config_writer.py   ← Builds YAML from query set
│   │   └── query_output_manager.py ← Orchestrates file writing
│   │
│   ├── learning/                   ← Rule learning from feedback
│   │   ├── feedback.py             ← Save new examples to disk
│   │   └── retrieval.py            ← Retrieve learned examples for AI
│   │
│   ├── rules_catalog.json          ← Rule metadata for AI prompts
│   ├── rule_book_learned.json      ← User-defined learned rules (auto-created)
│   └── transformation_rules.py     ← Legacy rule engine (backward compat)
│
├── validation_sql/                 ← Generated SQL and YAML output files
│   ├── events_validation.sql
│   ├── events_validation.yaml
│   └── ...
│
└── tests/
    └── postgres/
        ├── init/                   ← SQL scripts to seed local test DB
        ├── test_connection.py
        └── QUICKSTART.md
```

---

## 5. How the 8 Queries Work — Efficiency Analysis

### The 8 Generated Queries

For every table pair (PostgreSQL → Snowflake), the system generates exactly **8 SQL queries**. Here is what each one does, why it exists, and how to interpret its output.

---

### Query ① — Row Count: PostgreSQL (Source)

```sql
-- ① ROW COUNT: PostgreSQL (public.events)
SELECT COUNT(*) AS source_row_count
FROM public.events;
```

**Purpose:** Get the total number of rows in the source table.  
**Run on:** PostgreSQL  
**Compare with:** Query ②  
**Pass condition:** `source_row_count == target_row_count`

---

### Query ② — Row Count: Snowflake (Target)

```sql
-- ② ROW COUNT: Snowflake (dev_db.schema.EVENTS)
SELECT COUNT(*) AS target_row_count
FROM dev_db.schema.EVENTS
WHERE _FIVETRAN_ACTIVE = TRUE;   -- only if Fivetran column detected
```

**Purpose:** Get the total number of rows in the target table.  
**Run on:** Snowflake  
**Compare with:** Query ①  
**Pass condition:** `target_row_count == source_row_count`

**Why Fivetran filter?** Fivetran uses change-data-capture, keeping historical versions of each row. Without `WHERE _FIVETRAN_ACTIVE = TRUE`, the row count would always be higher than the source. The filter ensures only the latest active records are counted.

---

### Query ③ — Main Validation SELECT: PostgreSQL (Source, normalised)

```sql
-- ③ SOURCE: PostgreSQL (public.events)
SELECT
    COALESCE(CAST(CAST(event_id AS TEXT) AS TEXT), '<<NULL>>') AS event_id_normalized,
    COALESCE(CAST(TRIM(event_name) AS TEXT), '<<NULL>>') AS event_name_normalized,
    COALESCE(CAST(CASE WHEN is_active THEN '1' ELSE '0' END AS TEXT), '<<NULL>>') AS is_active_normalized,
    COALESCE(CAST(TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS TEXT), '<<NULL>>') AS created_at_normalized
FROM public.events;
```

**Purpose:** Pull ALL rows from the source table with every column normalized to a comparable text form.  
**Run on:** PostgreSQL  
**Export to:** CSV  
**Compare with:** Query ④ CSV row-by-row  
**Pass condition:** Both CSV files are identical (every row, every column)

---

### Query ④ — Main Validation SELECT: Snowflake (Target, normalised)

```sql
-- ④ TARGET: Snowflake (dev_db.schema.EVENTS)
SELECT
    COALESCE(CAST(CAST(EVENT_ID AS STRING) AS STRING), '<<NULL>>') AS event_id_normalized,
    COALESCE(CAST(TRIM(EVENT_NAME) AS STRING), '<<NULL>>') AS event_name_normalized,
    COALESCE(CAST(CASE WHEN IS_ACTIVE THEN '1' ELSE '0' END AS STRING), '<<NULL>>') AS is_active_normalized,
    COALESCE(CAST(TO_VARCHAR(CREATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS STRING), '<<NULL>>') AS created_at_normalized
FROM dev_db.schema.EVENTS
WHERE _FIVETRAN_ACTIVE = TRUE;
```

**Purpose:** Pull ALL rows from the target table with the same normalizations applied.  
**Run on:** Snowflake  
**Export to:** CSV  
**Compare with:** Query ③ CSV row-by-row  
**Pass condition:** Identical to ③ output after sorting both CSVs by the same column

**Critical design:** Both ③ and ④ use the **same alias names** (e.g. `event_id_normalized` — source column name) on both sides. This makes CSV comparison straightforward — column names match even when the actual column names differ between databases.

---

### Query ⑤ — NULL % Per Column: PostgreSQL

```sql
-- ⑤ NULL % CHECK: PostgreSQL (public.events)
SELECT
    COUNT(*) AS total_rows,
    ROUND(100.0 * SUM(CASE WHEN event_id IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS event_id_null_pct,
    ROUND(100.0 * SUM(CASE WHEN event_name IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS event_name_null_pct,
    ROUND(100.0 * SUM(CASE WHEN is_active IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS is_active_null_pct,
    ROUND(100.0 * SUM(CASE WHEN created_at IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS created_at_null_pct
FROM public.events;
```

**Purpose:** Calculate what percentage of each column is NULL on the source side.  
**Run on:** PostgreSQL  
**Compare with:** Query ⑥  
**Pass condition:** `event_id_null_pct` in ⑤ == `event_id_null_pct` in ⑥ (within tolerance)

**Why this matters:** A migration might accidentally convert NULLs to 0 or empty string, or lose NULLs from required fields. NULL % comparison catches this class of defect without a full row-by-row scan.

---

### Query ⑥ — NULL % Per Column: Snowflake

```sql
-- ⑥ NULL % CHECK: Snowflake (dev_db.schema.EVENTS)
SELECT
    COUNT(*) AS total_rows,
    ROUND(100.0 * SUM(CASE WHEN EVENT_ID IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS event_id_null_pct,
    ROUND(100.0 * SUM(CASE WHEN EVENT_NAME IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS event_name_null_pct,
    ...
FROM dev_db.schema.EVENTS
WHERE _FIVETRAN_ACTIVE = TRUE;
```

**Purpose:** Same as ⑤ but on the Snowflake side.  
**Compare with:** Query ⑤  
**Pass condition:** All `_null_pct` columns match ⑤

---

### Query ⑦ — Distinct Value Count Per Column: PostgreSQL

```sql
-- ⑦ DISTINCT VALUE COUNT: PostgreSQL (public.events)
-- Compare distinct counts with ⑧ — large differences indicate data drift.
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT event_id) AS event_id_distinct_count,
    COUNT(DISTINCT event_name) AS event_name_distinct_count,
    COUNT(DISTINCT is_active) AS is_active_distinct_count,
    COUNT(DISTINCT created_at) AS created_at_distinct_count
FROM public.events;
```

**Purpose:** Count how many unique values exist per column on the source side.  
**Run on:** PostgreSQL  
**Compare with:** Query ⑧  
**Pass condition:** Distinct counts match (or are close) between ⑦ and ⑧

**Why this matters:** If a column has 500 distinct values in PostgreSQL but only 300 in Snowflake, data was truncated or collapsed. Distinct counts surface data drift that row counts cannot.

---

### Query ⑧ — Distinct Value Count Per Column: Snowflake

Same as ⑦ but on Snowflake side. Used to detect cardinality loss during migration.

---

### Is 8 Queries Efficient?

**Yes — and here is why each pair is necessary:**

| Pair | What it catches | Can it be dropped? |
|---|---|---|
| ① + ② Row count | Missing or duplicate rows | No — first sanity check |
| ③ + ④ Data validation | Wrong values, bad transformations | No — only full correctness proof |
| ⑤ + ⑥ NULL % | Null handling errors | Only if you don't care about nulls |
| ⑦ + ⑧ Distinct count | Cardinality loss, value collapse | Only if ③/④ are run every time |

**Practical tradeoff:**
- For a quick check: Run only ① + ② (30 seconds, 2 queries).
- For a full validation: Run all 8 (varies by table size).
- For a daily job: Run ① + ② + ⑤ + ⑥ (aggregates are fast even on large tables).
- For migration sign-off: Run all 8 and export ③ + ④ to CSV for comparison.

The 8-query design is deliberate. Aggregates (①②⑤⑥⑦⑧) are cheap — they scan the table once. Full-data queries (③④) are expensive on large tables but are the only way to catch row-level data corruption.

---

## 6. Validation Logic — How It Works

### Step 1: Schema Extraction

The pipeline connects to both databases and reads column metadata:

**PostgreSQL extraction** reads from `information_schema.columns` and `pg_catalog`:
- Column name
- Data type (e.g. `integer`, `character varying`, `boolean`, `timestamp with time zone`)
- Nullable
- Position (ordinal)

**Snowflake extraction** reads from `INFORMATION_SCHEMA.COLUMNS`:
- Column name (usually UPPER_CASE)
- Data type (e.g. `NUMBER`, `TEXT`, `BOOLEAN`, `TIMESTAMP_NTZ`)
- Detects `_FIVETRAN_ACTIVE` column

### Step 2: Column Matching

Column matching happens in three layers:

**Layer A — Exact Match (case-insensitive)**
- `user_id` matches `USER_ID`
- `created_at` matches `CREATED_AT`
- Fast, deterministic, ~90% of columns resolved here

**Layer B — Fuzzy Match (RapidFuzz)**
- Uses token sort ratio and partial ratio
- `first_name` matches `firstname` (score ~95)
- `reg_date` matches `REGISTRATION_DATE` (score ~70)
- Threshold: score ≥ 80 is accepted; below is sent to AI

**Layer C — AI Resolution (DIAL API)**
- Only columns that fuzzy matching cannot resolve confidently
- AI receives: source column name, source type, target candidates, all rule descriptions
- AI returns: best match + transformation rule + reason
- Token-efficient: only ambiguous columns are sent

**Confidence Scoring** (multi-factor):
```
final_score = (
    name_similarity  * 0.40   +
    type_compatibility * 0.30 +
    position_proximity * 0.20 +
    learned_example    * 0.10
)
```

### Step 3: Rule Assignment

For each matched column pair, the system assigns a **transformation rule** based on the PostgreSQL data type mapped to the Snowflake data type:

| PG Type | SF Type | Rule | SQL Applied |
|---|---|---|---|
| `boolean` | `BOOLEAN` | `boolean_conversion` | `CASE WHEN col THEN '1' ELSE '0' END` |
| `integer`, `bigint` | `NUMBER` | `integer_cast` | `CAST(col AS TEXT)` |
| `character varying` | `TEXT`, `VARCHAR` | `text` | `TRIM(col)` |
| `date` | `DATE` | `date_standardization` | `TO_CHAR(col, 'YYYY-MM-DD')` |
| `timestamp without time zone` | `TIMESTAMP_NTZ` | `timestamp_ntz` | `TO_CHAR(col, 'YYYY-MM-DD HH24:MI:SS')` |
| `timestamp with time zone` | `TIMESTAMP_TZ` | `timestamp_tz` | `TO_CHAR(col AT TIME ZONE 'UTC', ...)` |
| `numeric`, `decimal` | `NUMBER`, `FLOAT` | `numeric_precision` | `ROUND(CAST(col AS NUMERIC), 2)` |
| `uuid` | `TEXT`, `VARCHAR` | `uuid_to_varchar` | `UPPER(TRIM(CAST(col AS TEXT)))` |
| `jsonb`, `json` | `VARIANT` | `json_skip` | Skipped — not comparable |
| `bytea` | `BINARY` | `bytea_skip` | Skipped — not comparable |
| `ARRAY` | any | `array_skip` | Skipped — not comparable |

**NULL Wrapper (ALL columns):**  
After every type-specific transformation, a NULL sentinel is applied:
```sql
COALESCE(CAST(<transformed_expr> AS TEXT), '<<NULL>>')
```
This converts SQL NULL into the literal string `<<NULL>>` so that NULL == NULL comparison works in CSV diff tools.

### Step 4: Plan Validation

Before generating SQL, the plan is validated:
- Every source column that should be validated has a target column
- No duplicate target columns
- Rule assignments are valid for the type pairs
- Fivetran filter is only applied when the column exists

### Step 5: SQL Generation

The `SQLQueryGenerator` builds all 8 queries deterministically from the validated plan.

### Step 6: Comparison (Manual in Phase 1)

The tester:
1. Runs ① and ② → compares row counts
2. Runs ③ → exports to CSV
3. Runs ④ → exports to CSV
4. Sorts both CSVs by same column → diffs them
5. Runs ⑤ and ⑥ → compares NULL % columns
6. Runs ⑦ and ⑧ → compares distinct counts

**PASS criteria:**
- Row counts ①② match (or within 1% tolerance)
- ③ and ④ CSV exports are identical after sorting
- All NULL % columns ⑤⑥ match
- All distinct counts ⑦⑧ match

---

## 7. YAML Output — Structure, Validation, and Correctness

### Why YAML?

The YAML file is the machine-readable output consumed by **automated validation runners** (e.g. a CI/CD pipeline, a custom Python test runner, or a third-party data quality tool). The SQL file is for manual review; the YAML file is for automation.

### YAML File Structure

A generated YAML file (`events_validation.yaml`) looks like this:

```yaml
# ============================================================
# Migration Validator — YAML Validation Config
# Table      : events
# Generated  : 2026-08-10T14:32:00
# By         : AI (model: gpt-4o-mini)
# Columns    : 12 comparable columns
#
# Validation blocks:
#   row_count_validation    — COUNT(*) on both sides
#   data_validation         — normalised full-scan SELECT (all columns)
#   null_pct_validation     — NULL % per column
#   distinct_count_validation — distinct value counts per column
# ============================================================

tables:
  events:
    validations:

      # ── ① / ② Row count check ────────────────────────────────────
      row_count_validation:
        source_table_name: events
        source: postgresql
        sourcequery: |
          SELECT COUNT(*) AS source_row_count
          FROM public.events;
        target_table_name: EVENTS
        target: snowflake
        targetquery: |
          SELECT COUNT(*) AS target_row_count
          FROM dev_db.schema.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE;

      # ── ③ / ④ Normalised data validation (all columns) ───────────
      data_validation:
        source_table_name: events
        source: postgresql
        sourcecolumn: event_id
        sourcequery: |
          SELECT
              COALESCE(CAST(CAST(event_id AS TEXT) AS TEXT), '<<NULL>>') AS event_id_normalized,
              COALESCE(CAST(TRIM(event_name) AS TEXT), '<<NULL>>') AS event_name_normalized
          FROM public.events;
        target_table_name: EVENTS
        target: snowflake
        targetcolumn: EVENT_ID
        targetquery: |
          SELECT
              COALESCE(CAST(CAST(EVENT_ID AS STRING) AS STRING), '<<NULL>>') AS event_id_normalized,
              COALESCE(CAST(TRIM(EVENT_NAME) AS STRING), '<<NULL>>') AS event_name_normalized
          FROM dev_db.schema.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE;

      # ── ⑤ / ⑥ NULL % per column ──────────────────────────────────
      null_pct_validation:
        source_table_name: events
        source: postgresql
        sourcequery: |
          SELECT
              COUNT(*) AS total_rows,
              ROUND(100.0 * SUM(CASE WHEN event_id IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS event_id_null_pct
          FROM public.events;
        target_table_name: EVENTS
        target: snowflake
        targetquery: |
          SELECT
              COUNT(*) AS total_rows,
              ROUND(100.0 * SUM(CASE WHEN EVENT_ID IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS event_id_null_pct
          FROM dev_db.schema.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE;

      # ── ⑦ / ⑧ Distinct value counts per column ───────────────────
      distinct_count_validation:
        source_table_name: events
        source: postgresql
        sourcequery: |
          SELECT
              COUNT(*) AS total_rows,
              COUNT(DISTINCT event_id) AS event_id_distinct_count
          FROM public.events;
        target_table_name: EVENTS
        target: snowflake
        targetquery: |
          SELECT
              COUNT(*) AS total_rows,
              COUNT(DISTINCT EVENT_ID) AS event_id_distinct_count
          FROM dev_db.schema.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE;
```

---

### YAML Indentation Rules (Critical)

YAML literal block scalars (the `|` character) require strict indentation. A wrong indent breaks the parser.

```
tables:                            ← 0 spaces (root key)
  events:                          ← 2 spaces
    validations:                   ← 4 spaces
      row_count_validation:        ← 6 spaces
        source_table_name: events  ← 8 spaces
        sourcequery: |             ← 8 spaces
          SELECT COUNT(*) ...      ← 10 spaces (content of literal block)
          FROM public.events;      ← 10 spaces
```

**Rule:** Content inside a `|` block must be indented MORE than the key that introduces it.  
The key `sourcequery:` is at 8 spaces, so SQL content is at **10 spaces**.

---

### How to Validate a YAML File is Correctly Written

**Method 1 — Python parse check (fastest):**

```python
import yaml

with open("validation_sql/events_validation.yaml", "r") as f:
    data = yaml.safe_load(f)

# Check top-level structure
assert "tables" in data, "Missing 'tables' key"
for table_name, table_body in data["tables"].items():
    assert "validations" in table_body, f"Missing 'validations' in {table_name}"
    validations = table_body["validations"]
    
    for block_name, block in validations.items():
        assert "sourcequery" in block, f"Missing sourcequery in {block_name}"
        assert "targetquery" in block, f"Missing targetquery in {block_name}"
        # Queries must be non-empty strings
        assert block["sourcequery"].strip(), f"Empty sourcequery in {block_name}"
        assert block["targetquery"].strip(), f"Empty targetquery in {block_name}"
        print(f"  OK: {table_name}.{block_name}")

print("YAML validation PASSED")
```

**Method 2 — CLI check:**

```powershell
cd C:\EPAM-Personal\Migration-validator
python -c "import yaml; yaml.safe_load(open('validation_sql/events_validation.yaml'))"
# No output = valid YAML. Exception = syntax error.
```

**Method 3 — Run the built-in verify script:**

```powershell
cd src
python verify_yaml_generation.py
```

**Method 4 — Online YAML validator:**

Copy the YAML file content and paste into https://www.yamllint.com/ — it flags indentation and syntax errors.

---

### Common YAML Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `yaml.scanner.ScannerError: mapping values are not allowed here` | Tab character instead of spaces | Replace all tabs with spaces (8 or 10 as required) |
| `yaml.scanner.ScannerError: while parsing a block mapping` | Wrong indentation level | Align `sourcequery:` to 8 spaces |
| Query content starts at wrong indent | `\|` block content < 10 spaces | Ensure SQL lines are at 10 spaces |
| `sourcequery` is None in Python | Empty block after `\|` | Check there is at least one non-empty SQL line after `\|` |
| Missing `tables` key | Manual edit error | Do not edit YAML by hand; regenerate |

**Golden rule: Never manually edit generated YAML files.** If the SQL is wrong, fix the rule and regenerate.

---

## 8. Transformation Rules — Complete Reference

All 12 normalization principles:

### Rule 1: Boolean Conversion

| Database | Input | Output |
|---|---|---|
| PostgreSQL | `TRUE` | `'1'` |
| PostgreSQL | `FALSE` | `'0'` |
| Snowflake | `TRUE` | `'1'` |
| Snowflake | `FALSE` | `'0'` |

```sql
-- PostgreSQL
COALESCE(CAST(CASE WHEN is_active THEN '1' ELSE '0' END AS TEXT), '<<NULL>>')

-- Snowflake
COALESCE(CAST(CASE WHEN IS_ACTIVE THEN '1' ELSE '0' END AS STRING), '<<NULL>>')
```

**Triggers on:** PG `boolean` / `bool` → SF `BOOLEAN`

---

### Rule 2: Integer Cast

Converts numeric integer types to text to eliminate type-width differences (`INT` vs `BIGINT` vs `SMALLINT`).

```sql
-- PostgreSQL
COALESCE(CAST(CAST(user_id AS TEXT) AS TEXT), '<<NULL>>')

-- Snowflake
COALESCE(CAST(CAST(USER_ID AS STRING) AS STRING), '<<NULL>>')
```

**Triggers on:** PG `integer`, `bigint`, `smallint`, `serial` → SF `NUMBER`, `INTEGER`

---

### Rule 3: Text / VARCHAR — Whitespace Trim

Removes leading and trailing spaces before comparison.

```sql
-- PostgreSQL
COALESCE(CAST(TRIM(customer_name) AS TEXT), '<<NULL>>')

-- Snowflake
COALESCE(CAST(TRIM(CUSTOMER_NAME) AS STRING), '<<NULL>>')
```

**Result:** `' John '` == `'John'` → PASS  
**Triggers on:** PG `character varying`, `text`, `char`, `varchar` → SF `TEXT`, `VARCHAR`, `STRING`

---

### Rule 4: Date Standardization

Converts dates to ISO format `YYYY-MM-DD` regardless of display format.

```sql
-- PostgreSQL
COALESCE(CAST(TO_CHAR(event_date, 'YYYY-MM-DD') AS TEXT), '<<NULL>>')

-- Snowflake
COALESCE(CAST(TO_VARCHAR(EVENT_DATE, 'YYYY-MM-DD') AS STRING), '<<NULL>>')
```

**Result:** `'01/10/2024'` == `'2024-01-10'` → PASS  
**Triggers on:** PG `date` → SF `DATE`

---

### Rule 5: Timestamp (without timezone)

Strips microseconds and normalizes to `YYYY-MM-DD HH24:MI:SS`.

```sql
-- PostgreSQL
COALESCE(CAST(TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS TEXT), '<<NULL>>')

-- Snowflake
COALESCE(CAST(TO_VARCHAR(CREATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS STRING), '<<NULL>>')
```

**Triggers on:** PG `timestamp without time zone`, `timestamp` → SF `TIMESTAMP_NTZ`

---

### Rule 6: Timestamp (with timezone) → UTC

Converts to UTC before formatting, eliminating timezone offset differences.

```sql
-- PostgreSQL
COALESCE(CAST(TO_CHAR(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS TEXT), '<<NULL>>')

-- Snowflake
COALESCE(CAST(TO_VARCHAR(CONVERT_TIMEZONE('UTC', CREATED_AT), 'YYYY-MM-DD HH24:MI:SS') AS STRING), '<<NULL>>')
```

**Triggers on:** PG `timestamp with time zone`, `timestamptz` → SF `TIMESTAMP_TZ`, `TIMESTAMP_LTZ`

---

### Rule 7: Numeric Precision

Rounds to 2 decimal places and casts to text to eliminate floating-point precision noise.

```sql
-- PostgreSQL
COALESCE(CAST(ROUND(CAST(balance AS NUMERIC), 2) AS TEXT), '<<NULL>>')

-- Snowflake
COALESCE(CAST(ROUND(CAST(BALANCE AS FLOAT), 2) AS STRING), '<<NULL>>')
```

**Result:** `100` == `100.00` == `100.000` → PASS  
**Triggers on:** PG `numeric`, `decimal`, `real`, `double precision`, `float` → SF `NUMBER`, `FLOAT`, `DECIMAL`

---

### Rule 8: UUID Normalization

Converts UUIDs to UPPER CASE text to eliminate case differences.

```sql
-- PostgreSQL
COALESCE(CAST(UPPER(TRIM(CAST(user_uuid AS TEXT))) AS TEXT), '<<NULL>>')

-- Snowflake
COALESCE(CAST(UPPER(TRIM(USER_UUID)) AS STRING), '<<NULL>>')
```

**Result:** `'a1b2c3d4-...'` == `'A1B2C3D4-...'` → PASS  
**Triggers on:** PG `uuid` → SF `TEXT`, `VARCHAR`

---

### Rule 9: JSON / JSONB — Skip

JSON objects cannot be reliably compared as text because key order differs between serializers. These columns are **skipped** (not validated in Phase 1).

```sql
-- Both sides: column excluded from SELECT
-- Marked skip_validation = True in the plan
```

**Triggers on:** PG `json`, `jsonb` → SF `VARIANT`, `OBJECT`  
**Future:** Canonical JSON serialization for comparison (Phase 2)

---

### Rule 10: Bytea / Binary — Skip

Binary data is skipped by default (Phase 1 scope).

**Triggers on:** PG `bytea` → SF `BINARY`

---

### Rule 11: NULL Sentinel — Applied to ALL Columns

This is the outermost wrapper applied to every column regardless of type.

```sql
COALESCE(CAST(<inner_expr> AS TEXT), '<<NULL>>')
```

**Why `<<NULL>>`?** SQL `NULL != NULL` is always false. By replacing NULL with the sentinel string `'<<NULL>>'`, the comparison `'<<NULL>>' = '<<NULL>>'` is `TRUE`, making NULL-to-NULL equality work in CSV diff tools.

**The sentinel `<<NULL>>` will never appear in real data** because no column value contains `<<` and `>>` together.

---

### Rule 12: Fivetran Active Filter

Applied **only on the Snowflake side**, only when `_FIVETRAN_ACTIVE` column is detected.

```sql
WHERE _FIVETRAN_ACTIVE = TRUE
```

This filter is added to ②④⑥⑧ (all Snowflake queries) but NOT to ①③⑤⑦ (PostgreSQL queries).

---

## 9. Pipeline Internals

### Legacy Pipeline (`run`)

Used by the default CLI path:

```
validate_cli.py generate
    → ValidationPipeline.run()
        1. PostgresExtractor.extract_columns()
        2. SnowflakeExtractor.extract_columns()
        3. RuleMapperOrchestrator.map_columns()
           └── AIRuleMapper (if DIAL_API_KEY) OR StaticRuleMapper
        4. QueryOutputManager.generate()
           ├── SQLQueryGenerator.generate()    → .sql file
           └── YAMLConfigWriter.write()         → .yaml file
```

### Plan-Driven Pipeline (`run_with_plan`)

More advanced 7-step pipeline:

```
validate_cli.py generate (with plan flag)
    → ValidationPipeline.run_with_plan()
        1. Extract schemas (PostgresExtractor + SnowflakeExtractor)
        2. Exact matching (ExactMatcher)
        3. Fuzzy matching (FuzzyMatcher with RapidFuzz)
        4. Confidence scoring (multi-factor ConfidenceScorer)
        5. AI resolution of ambiguous only (RulePlanner)
        6. Plan validation (PlanValidator)
        7. SQL + YAML generation (generate_from_plan)
```

The `CanonicalValidationPlan` object is the **single source of truth** — all downstream generation reads from it. Nothing else has mutable state after plan construction.

---

## 10. Database Connectors and Schema Extraction

### PostgreSQL Extractor

Connects via `psycopg2` and queries `information_schema.columns`. Returns a list of `ColumnInfo` objects with:
- `column_name` (original case)
- `data_type` (PostgreSQL type string, lowercase)
- `ordinal_position`
- `is_nullable`

**Configuration:**
```
SOURCE_HOST=localhost
SOURCE_PORT=5432
SOURCE_DATABASE=your_db
SOURCE_SCHEMA=public
SOURCE_USERNAME=postgres
SOURCE_PASSWORD=your_password
```

### Snowflake Extractor

Connects via `snowflake-connector-python` and queries `INFORMATION_SCHEMA.COLUMNS`. Also checks for `_FIVETRAN_ACTIVE` column existence.

**Configuration:**
```
SNOWFLAKE_ACCOUNT=xy12345.us-east-1
SNOWFLAKE_DATABASE=YOUR_DB
SNOWFLAKE_SCHEMA=YOUR_SCHEMA
SNOWFLAKE_USERNAME=YOUR_USER
SNOWFLAKE_PASSWORD=YOUR_PASSWORD
```

### ConnectorFactory (Legacy)

`database_connectors.py` provides `ConnectorFactory` that creates typed connectors for MSSQL, PostgreSQL, and Snowflake used by the `DataValidator` engine.

---

## 11. AI Integration (EPAM DIAL)

### What DIAL Is

EPAM DIAL (Digital AI Layer) is an API gateway that provides access to multiple AI models under one endpoint:

```
https://ai-proxy.lab.epam.com
```

Models include:
- `gpt-4o` — best accuracy, higher cost
- `gpt-4o-mini` — fast, cost-effective, recommended for most use cases
- `gpt-4-turbo`
- `claude-3-5-sonnet`
- `gemini-pro`

### When AI Is Used

AI is **not** used for every column. The system sends columns to AI only when:

1. Exact match fails (column names do not match case-insensitively)
2. Fuzzy match score is below the confidence threshold (typically 80)
3. No learned example exists for this source/target column pair

This keeps AI usage minimal and cost-controlled.

### What AI Does

The AI receives:
- Source column name + type
- Top fuzzy match candidates from the Snowflake schema
- The complete rule catalog (all transformation rules)
- Any learned examples from `rule_book_learned.json`

The AI returns:
- Best target column match
- Recommended transformation rule ID
- Reason for the decision (human-readable)

### Configuration

```bash
# .env
DIAL_API_KEY=your_epam_dial_key
DIAL_API_BASE=https://ai-proxy.lab.epam.com
DIAL_API_VERSION=2025-04-01-preview
DIAL_MODEL=gpt-4o-mini
```

### Model Caching

Model availability is cached for 24 hours in `.dial_model_cache.json` next to `.env`. To force a fresh check:

```powershell
Remove-Item .dial_model_cache.json
```

### Static Fallback

If `DIAL_API_KEY` is not set, the pipeline falls back to **static rule mapping** — pure type-based rule assignment with no AI column matching. Column names must match exactly (case-insensitive) for the static path.

---

## 12. Rule Book — Base and Learned Rules

### Base Rules

Defined in `src/rules/*.py` and described in `src/rules_catalog.json`. These are **immutable** — they cannot be changed at runtime.

Base rules cover all standard PostgreSQL → Snowflake type conversions.

### Learned Rules

Stored in `src/rule_book_learned.json`. These are **your team's custom rules**, added for special cases not covered by base rules:

Examples:
- Phone number normalization: strip `+`, `-`, spaces
- Currency stripping: remove `$`, `,` before numeric comparison
- Custom date format: `DD/MM/YYYY` stored as text

### Adding a Learned Rule

```powershell
cd src
python validate_cli.py add-rule
```

The wizard prompts for:
- Rule ID (snake_case)
- Display name
- Description (plain English)
- When to apply (what types trigger this)
- PostgreSQL SQL template (use `{col}` as placeholder)
- Snowflake SQL template
- Optional example

The rule is saved to `rule_book_learned.json` and injected into every future AI prompt.

### Viewing All Rules

```powershell
python validate_cli.py rules
```

---

## 13. CLI Reference

### Interactive Mode (No Arguments)

```powershell
cd src
python validate_cli.py
```

Shows menu:
```
[1]  Generate SQL + YAML validation files   ← Full workflow
[2]  Select AI model
[3]  View rule book
[4]  Add a custom rule to rule book
[5]  List tables in both databases
[q]  Quit
```

### Command: generate

Full workflow — extract schemas, map columns, assign rules, generate SQL + YAML.

```powershell
# Minimal (interactive prompts for missing values)
python validate_cli.py generate --pg-table events --sf-table EVENTS

# Full (no prompts)
python validate_cli.py generate \
    --pg-database mydb \
    --pg-schema public \
    --pg-table events \
    --sf-database dev_db \
    --sf-schema MY_SCHEMA \
    --sf-table EVENTS \
    --model gpt-4o-mini
```

**Arguments:**

| Argument | Description | Default |
|---|---|---|
| `--pg-database` | PostgreSQL database name | `SOURCE_DATABASE` env |
| `--pg-schema` | PostgreSQL schema | `SOURCE_SCHEMA` env or `public` |
| `--pg-table` | PostgreSQL table (required) | — |
| `--sf-database` | Snowflake database | `SNOWFLAKE_DATABASE` env |
| `--sf-schema` | Snowflake schema | `SNOWFLAKE_SCHEMA` env |
| `--sf-table` | Snowflake table (required) | — |
| `--model` | AI model name | `DIAL_MODEL` env or `gpt-4o` |

### Command: rules

Display full rule book.

```powershell
python validate_cli.py rules
```

### Command: add-rule

Add a custom learned rule.

```powershell
python validate_cli.py add-rule
```

### Command: list-models

Show AI models available on your API key.

```powershell
python validate_cli.py list-models
```

### Command: list-tables

List all tables in both databases.

```powershell
python validate_cli.py list-tables
```

---

## 14. Configuration (.env)

Create a `.env` file in the project root (`C:\EPAM-Personal\Migration-validator\.env`):

```bash
# ── PostgreSQL Source ──────────────────────────────────────
SOURCE_HOST=localhost
SOURCE_PORT=5432
SOURCE_DATABASE=your_database
SOURCE_SCHEMA=public
SOURCE_USERNAME=postgres
SOURCE_PASSWORD=your_password

# ── Snowflake Target ───────────────────────────────────────
SNOWFLAKE_ACCOUNT=xy12345.us-east-1        # Account identifier (not full URL)
SNOWFLAKE_DATABASE=YOUR_DATABASE
SNOWFLAKE_SCHEMA=YOUR_SCHEMA
SNOWFLAKE_USERNAME=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH            # Optional: warehouse name

# ── EPAM DIAL AI (Optional) ────────────────────────────────
DIAL_API_KEY=your_epam_dial_api_key
DIAL_API_BASE=https://ai-proxy.lab.epam.com
DIAL_API_VERSION=2025-04-01-preview
DIAL_MODEL=gpt-4o-mini                    # Recommended model
```

**Security:** Never commit `.env` to Git. Add it to `.gitignore`.

---

## 15. Output Files

Generated files are written to `validation_sql/` (one level above `src/`):

```
validation_sql/
├── events_validation.sql    ← All 8 queries with comments
├── events_validation.yaml   ← YAML config for automation
├── users_validation.sql
├── users_validation.yaml
└── ...
```

File naming convention: `<pg_table_name_lowercase>_validation.sql / .yaml`

**The SQL file** is for:
- Manual review of generated queries
- Running queries in a SQL client (DBeaver, DataGrip, etc.)
- Sharing with the QA team

**The YAML file** is for:
- Automated validation runners
- CI/CD pipeline integration
- Feeding into data quality tools

---

## 16. Reports — JSON, HTML, Text

When using the `DataValidator.run_validation()` API (automated mode), three report formats are generated:

### JSON Report

Machine-readable, contains:
- `validation_id`, `timestamp`, `overall_status`
- Per-table: source rows, target rows, matched rows, completeness %, status
- Per-column: matched count, applied rules, status

### HTML Report

Visual dashboard with:
- Summary cards (status, completeness %, passed tables, matched rows)
- Per-table table with progress bars
- Color-coded status badges (PASS=green, FAIL=red, PARTIAL=yellow)

```powershell
# Open HTML report
Start-Process validation_reports/report_20260810_143200.html
```

### Text Report

Plain text summary:
```
================================================================================
MIGRATION VALIDATION REPORT
================================================================================
Validation ID: abc123
Overall Status: PASS
Data Completeness: 100.00%
Success Rate: 100.00%
...
```

---

## 17. Fivetran Active Filter

When Fivetran loads data to Snowflake using change-data-capture, it adds columns:
- `_FIVETRAN_ACTIVE` — TRUE for the current/latest version of each row
- `_FIVETRAN_SYNCED` — last sync timestamp
- `_FIVETRAN_DELETED` — TRUE for deleted rows

**Without filtering**, a table with 1000 source rows may have 2500 rows in Snowflake (including historical versions). Row counts will never match.

**With `WHERE _FIVETRAN_ACTIVE = TRUE`**, only the latest active record per logical row is included, matching the source row count.

The system **auto-detects** this column:
```python
# In SnowflakeExtractor
has_fivetran_active = any(col.column_name == '_FIVETRAN_ACTIVE' for col in columns)
```

When detected, the filter is added to **all Snowflake queries** (②④⑥⑧) automatically.

---

## 18. Common Issues and Solutions

### Connection Failures

```
✗ PostgreSQL connection failed: could not connect to server
```
**Check:**
- VPN is connected (for remote databases)
- `SOURCE_HOST`, `SOURCE_PORT` are correct in `.env`
- Firewall/network allows connection
- Run: `python src/check_connections.py`

### Table Not Found

```
relation "public.events" does not exist
```
**Check:**
- Schema name is correct (`public` vs actual schema)
- Table name case (PostgreSQL is case-sensitive for quoted names)
- User has `SELECT` permission on the table
- Run: `python validate_cli.py list-tables`

### AI Not Working

```
⚠ Not active — static fallback
```
**Check:**
- `DIAL_API_KEY` is set in `.env`
- VPN is connected (EPAM DIAL is internal)
- API key is valid: visit https://ai-proxy.lab.epam.com
- Run: `python validate_cli.py list-models`

### Wrong Column Matched

If the AI matches the wrong source column to the wrong target column:
1. Check `rule_book_learned.json` for conflicting learned examples
2. Run `python validate_cli.py add-rule` to add a corrective example
3. Regenerate queries

### YAML Parsing Error

```
yaml.scanner.ScannerError
```
**Fix:**
- Do not manually edit YAML files
- Delete the broken file and regenerate: `python validate_cli.py generate ...`
- Check `src/verify_yaml_generation.py` for diagnostics

---

## 19. Design Decisions and Future Work

### Current Scope (Phase 1 PoC)

- Single source database per run (PostgreSQL OR SQL Server → Snowflake)
- Static transformation rules (no dynamic business rules)
- Manual execution of SQL queries (no automated comparison engine yet)
- No primary-key–based row matching (full table scans only)
- JSON, ARRAY, BYTEA columns are skipped (not comparable in Phase 1)

### Phase 2 Planned Enhancements

- Automated CSV comparison (run ③ and ④ and diff inline)
- Primary-key–based row matching (find which specific rows differ)
- Multi-source consolidation (SQL Server + PostgreSQL → Snowflake)
- Dynamic business rules from configuration
- Source-to-Target Mapping (STM) file integration
- Aggregate validations (MIN, MAX, AVG, SUM per column)
- Duplicate detection
- Data profiling dashboard
- Scheduled validation jobs

### Why No PK Matching in Phase 1?

Row-by-row PK matching requires:
1. Both source and target to have the same primary key
2. Consistent PK data types (UUID vs INTEGER vs composite)
3. Ordering guarantees

In practice, migrated tables often have:
- PKs auto-generated differently in Snowflake
- No PK on Snowflake side (dimensional model)
- Composite PKs that change during migration

The Phase 1 approach (full table scan + normalization) provides **data completeness validation** without requiring PK consistency.

---

*Last updated: 2026-08-10*  
*Maintained by: AI Engineering Team — EPAM*
