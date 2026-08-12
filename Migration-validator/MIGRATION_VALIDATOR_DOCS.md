# Migration Validator — Complete Project Documentation

> **Purpose:** Automate data completeness validation when migrating tables from PostgreSQL or MS SQL Server to Snowflake. The tool extracts live schema metadata, generates normalised SQL validation queries, writes them to YAML config files, and can execute those queries live to show pass/fail results.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Directory Structure](#2-directory-structure)
3. [Configuration — .env File](#3-configuration--env-file)
4. [Source Files — What Each File Does](#4-source-files--what-each-file-does)
5. [Interactive Menu Reference](#5-interactive-menu-reference)
6. [Connection Profiles](#6-connection-profiles)
7. [Validation YAML Format](#7-validation-yaml-format)
8. [SQL Output Format](#8-sql-output-format)
9. [Normalization Rules](#9-normalization-rules)
10. [Rule Book System](#10-rule-book-system)
11. [AI Integration (DIAL API)](#11-ai-integration-dial-api)
12. [Pipeline Flow — End to End](#12-pipeline-flow--end-to-end)
13. [Adding a New Source Database](#13-adding-a-new-source-database)
14. [Batch Mode](#14-batch-mode)
15. [Tests](#15-tests)
16. [Dummy Data & Test Setup](#16-dummy-data--test-setup)
17. [Known Behaviours & Constraints](#17-known-behaviours--constraints)

---

## 1. Quick Start

```powershell
# 1. Activate virtual environment
cd C:\EPAM-Personal\Migration-validator
.venv\Scripts\Activate.ps1

# 2. Copy and fill in credentials
copy .env.example .env
# Edit .env with your database credentials

# 3. Run the interactive tool
cd src
python validate_cli.py

# 4. Choose an option from the menu:
#   [1] Single Table  — generate YAML + SQL for one table
#   [2] Run Tables    — generate YAML + SQL for multiple tables
#   [9] Execute YAML  — run saved YAML against live databases
```

---

## 2. Directory Structure

```
Migration-validator/
│
├── .env                          ← Your credentials (git-ignored, NEVER commit)
├── .env.example                  ← Template showing all supported env vars
├── requirements.txt              ← Python dependencies
├── docker-compose.yml            ← Spins up local PostgreSQL for testing
│
├── config/                       ← YAML validation configs (OUTPUT — committed)
│   └── bronze/
│       ├── count_validation/
│       │   └── bronze_count_validation.yaml   ← ONE shared file, all tables
│       └── data_validation/
│           ├── events_validation.yaml          ← one per table
│           ├── migration_test_validation.yaml
│           ├── acctsoftware_validation.yaml
│           └── addresses_validation.yaml
│
├── validation_sql/               ← Generated .sql files (OUTPUT)
│   ├── events_validation.sql
│   ├── acctsoftware_validation.sql
│   └── ...
│
├── dummy-data/                   ← SQL scripts to create test tables
│   ├── postgres_setup.sql
│   └── snowflake_setup.sql
│
├── MSServer-data/                ← MSSQL sample DDL and CSV data
│
├── tests/                        ← Integration & unit tests (root level)
│   ├── test_end_to_end.py
│   ├── test_sql_generation.py
│   ├── test_yaml_generation.py
│   └── ...
│
└── src/                          ← All application source code
    ├── validate_cli.py           ← MAIN ENTRY POINT — interactive CLI
    ├── validation_pipeline.py    ← Python API entry point
    ├── setup_wizard.py           ← Interactive connection setup wizard
    ├── rule_book.py              ← Column transformation rule registry
    ├── rule_book_learned.json    ← Persisted user-added rules
    ├── rules_catalog.json        ← Static rule catalog (used by AI)
    │
    ├── sql_extractor/            ← Database connectors + schema discovery
    │   ├── extractors.py         ← PostgresExtractor, MSSQLExtractor, SnowflakeExtractor, AthenaExtractor
    │   └── __init__.py
    │
    ├── ai_transformation/        ← Column → rule mapping
    │   ├── orchestrator.py       ← Decides AI vs static mapping
    │   ├── ai_rule_mapper.py     ← Calls DIAL API with schema context
    │   ├── static_rule_mapper.py ← Pattern-matching fallback
    │   └── __init__.py
    │
    ├── generated_queries/        ← SQL and YAML file writers
    │   ├── query_output_manager.py  ← Orchestrates SQL gen + file writing
    │   ├── sql_query_generator.py   ← Builds all 6–8 validation SQL queries
    │   ├── yaml_config_writer.py    ← Writes config/bronze/ YAML files
    │   └── __init__.py
    │
    ├── core/
    │   └── validation_plan.py    ← CanonicalValidationPlan data class
    │
    ├── matching/                 ← Column name matching (source ↔ Snowflake)
    │   ├── exact_matcher.py      ← Case-insensitive exact match
    │   ├── fuzzy_matcher.py      ← RapidFuzz similarity matching
    │   ├── candidate_matcher.py  ← Combines exact + fuzzy candidates
    │   ├── confidence.py         ← Multi-factor confidence scoring
    │   ├── normalizer.py         ← Name normalisation (strip spaces, case)
    │   └── __init__.py
    │
    ├── ai/                       ← AI helper modules
    │   ├── rule_planner.py       ← Decides which columns need AI resolution
    │   ├── prompt_builder.py     ← Builds structured AI prompts
    │   ├── response_parser.py    ← Parses AI JSON response to rule mappings
    │   └── __init__.py
    │
    ├── rules/                    ← Per-database SQL normalisation rules
    │   ├── postgres_base_rules.py   ← 11 built-in PostgreSQL rules
    │   ├── mssql_rules.py           ← MSSQL-specific overrides
    │   ├── snowflake_rules.py       ← Snowflake-side expressions
    │   ├── athena_rules.py          ← AWS Athena rules
    │   └── __init__.py
    │
    ├── profiling/                ← Schema profiling (dynamic suite)
    │   ├── schema_profiler.py    ← Analyses column types for extra checks
    │   ├── validation_rule_engine.py ← Decides which checks to run per column
    │   └── ai_recommendation.py  ← AI-suggested business-rule checks
    │
    ├── dynamic_suite/            ← Extended validation (beyond basic 6 queries)
    │   ├── suite_generator.py    ← Generates MIN/MAX/SUM/duplicate checks
    │   ├── query_optimizer.py    ← Combines multiple checks per SQL round-trip
    │   ├── validation_suite.py   ← ValidationSuite data class
    │   └── __init__.py
    │
    ├── batch/                    ← Batch processing from a YAML config list
    │   ├── batch_runner.py       ← Processes N tables in parallel
    │   ├── config_parser.py      ← Parses batch YAML config
    │   ├── manifest_writer.py    ← Writes _manifest.json result file
    │   └── __init__.py
    │
    ├── validation/
    │   └── plan_validator.py     ← Validates a CanonicalValidationPlan for errors
    │
    ├── learning/                 ← Rule feedback loop
    │   ├── feedback.py           ← Saves user corrections to rule_book_learned.json
    │   └── retrieval.py          ← Retrieves learned rules for a column
    │
    ├── model_probe.py            ← Probes DIAL API to find available models
    │
    └── tests/                    ← Unit tests (src-level)
        ├── test_validation_rule_engine.py
        ├── test_schema_profiler.py
        ├── test_suite_generator.py
        └── test_query_optimizer.py
```

---

## 3. Configuration — .env File

The `.env` file lives at the project root (`Migration-validator/.env`). It is **git-ignored** — never commit it. Use `.env.example` as a template.

### Source connections

Up to 10 source databases are supported using the `SRC_N_*` pattern:

```dotenv
# Source 1 — PostgreSQL
SRC_1_TYPE=postgresql
SRC_1_HOST=localhost
SRC_1_PORT=5432
SRC_1_DATABASE=fms
SRC_1_SCHEMA=public
SRC_1_USERNAME=postgres
SRC_1_PASSWORD=secret

# Source 2 — MS SQL Server
SRC_2_TYPE=mssqlserver
SRC_2_HOST=EPINHYDW1D68
SRC_2_PORT=1433
SRC_2_DATABASE=DevT5000
SRC_2_SCHEMA=dbo
SRC_2_USERNAME=sa
SRC_2_PASSWORD=secret
# For Windows auth: SRC_2_MSSQL_AUTH=windows

# Legacy single-source vars (backwards compat — map to SRC_1)
SOURCE_TYPE=postgresql
SOURCE_HOST=localhost
SOURCE_PORT=5432
SOURCE_DATABASE=fms
SOURCE_SCHEMA=public
SOURCE_USERNAME=postgres
SOURCE_PASSWORD=secret
```

### Snowflake target

```dotenv
SNOWFLAKE_ACCOUNT=ZJAUJWQ-EP12783
SNOWFLAKE_DATABASE=DEV_EDGE_BRONZE
SNOWFLAKE_SCHEMA=STOREDGE_FMS_PUBLIC
SNOWFLAKE_USERNAME=user@company.com
SNOWFLAKE_PASSWORD=secret
SNOWFLAKE_WAREHOUSE=COMPUTE_WH      # optional
SNOWFLAKE_ROLE=SYSADMIN             # optional
```

### AI / DIAL API

```dotenv
DIAL_API_KEY=your-api-key-here
DIAL_ENDPOINT=https://your-dial-endpoint/openai/deployments
DIAL_MODEL=gpt-4o                   # model to use for rule assignment
```

---

## 4. Source Files — What Each File Does

### `src/validate_cli.py` — Main Entry Point

**What it does:** The entire interactive CLI. Run with `python validate_cli.py`.

Key functions:

| Function | Purpose |
|---|---|
| `cmd_interactive()` | Renders the main menu and routes choices |
| `cmd_generate(args)` | Menu [1]: single-table generation workflow |
| `cmd_multi_db(args)` | Menu [2]: multi-table workflow |
| `cmd_list_tables(args)` | Menu [3]: lists all source + Snowflake tables |
| `cmd_execute_yaml(args)` | Menu [9]: runs YAML queries live, shows pass/fail |
| `cmd_connections(args)` | Menu [c]: pings all configured connections |
| `cmd_profiles(args)` | Menu [8]: lists/deletes saved connection profiles |
| `cmd_rules(args)` | Menu [5]: displays the rule book |
| `cmd_add_rule(args)` | Menu [6]: adds a custom normalisation rule |
| `_pick_snowflake_target()` | Interactive: picks Snowflake account + database + schema; writes to `os.environ` |
| `_pick_source_connection()` | Picks a source DB from configured `SRC_N_*` slots |
| `ConnectionProfileManager` | Saves/loads profiles from `~/.migration-validator/profiles.json` |
| `_C` class | ANSI colour constants (GREEN, CYAN, BLUE, YELLOW, RED, DIM, RESET, BOLD) |

**Important env propagation:** `_pick_snowflake_target()` always writes the selected values into `os.environ["SNOWFLAKE_ACCOUNT"]`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA`, `SNOWFLAKE_USERNAME`, `SNOWFLAKE_PASSWORD` so all downstream extractors pick them up without needing to edit `.env`.

---

### `src/validation_pipeline.py` — Python API

**What it does:** Wires all modules together into a callable pipeline. Used for scripting and testing.

```python
from validation_pipeline import ValidationPipeline

pipeline = ValidationPipeline(model="gpt-4o")
result = pipeline.run(
    pg_schema="public",
    pg_table="events",
    sf_database="dev_edge_bronze",
    sf_schema="storedge_fms_public",
    sf_table="EVENTS",
)
```

`run()` performs: extract → match columns → AI/static rule mapping → generate SQL → write YAML.

---

### `src/setup_wizard.py` — Connection Setup Wizard

**What it does:** Guides a first-time user through entering and saving all database credentials to `.env`. Also provides live database/schema discovery.

Key functions:

| Function | Purpose |
|---|---|
| `run_wizard()` | Top-level wizard flow |
| `_collect_one_source()` | Prompts for one source DB; shows live DB/schema picker |
| `_collect_snowflake_target()` | Prompts for Snowflake credentials; shows live DB/schema picker |
| `_discover_postgres_databases()` | Lists PG databases excluding system ones |
| `_discover_postgres_schemas()` | Lists PG schemas with table counts |
| `_discover_mssql_databases()` | Lists MSSQL databases (skips master/model/msdb/tempdb) |
| `_discover_mssql_schemas()` | Lists MSSQL schemas excluding 12 system schemas |
| `_discover_snowflake_databases()` | Runs `SHOW DATABASES` against Snowflake |
| `_discover_snowflake_schemas()` | Runs `SHOW SCHEMAS` + table counts per schema |
| `_pick_from_live_list()` | Numbered picker with manual entry fallback |
| `print_connection_registry()` | Returns all `SRC_N_*` entries as a structured list |

---

### `src/sql_extractor/extractors.py` — Database Connectors

**What it does:** All four extractors in one file. Each extractor can:
- `extract_columns(schema, table)` → list of `ColumnMetadata`
- `list_tables(schema)` → list of table names
- `list_schemas()` → list of schema names
- `detect_primary_key(schema, table)` → `PrimaryKeyInfo`

| Class | Database | Python driver |
|---|---|---|
| `PostgresExtractor` | PostgreSQL | `psycopg2` |
| `MSSQLExtractor` | MS SQL Server | `pyodbc` |
| `SnowflakeExtractor` | Snowflake | `snowflake-connector-python` |
| `AthenaExtractor` | AWS Athena | `pyathena` |

`ExtractorFactory.create(db_type, **kwargs)` instantiates the right class from a string like `"postgresql"`, `"mssql"`, `"snowflake"`.

`ExtractorFactory.create_from_env()` builds an extractor from `SOURCE_*` env vars.

**Credential reading:** Each extractor reads credentials from `os.environ` at instantiation time. This means if you update `os.environ["SNOWFLAKE_DATABASE"]` before calling `SnowflakeExtractor()`, the new value is used.

---

### `src/rule_book.py` — Column Transformation Rule Registry

**What it does:** Holds all rules mapping PostgreSQL data types → SQL normalisation expressions. The rule book has two layers:

- **Base rules** (11 built-in): defined in `src/rules/postgres_base_rules.py`
- **Learned rules** (user-added): persisted in `src/rule_book_learned.json`

A rule contains:
- `data_types`: list of types this rule matches (e.g. `["boolean", "bool"]`)
- `source_expr`: PostgreSQL expression template (e.g. `CASE WHEN {col} THEN '1' ELSE '0' END`)
- `target_expr`: Snowflake expression template
- `description`: human-readable explanation

---

### `src/rules/` — Per-Database Normalisation Expressions

| File | Purpose |
|---|---|
| `postgres_base_rules.py` | 11 base rules: boolean, numeric, timestamp, uuid, text, etc. |
| `mssql_rules.py` | MSSQL-specific type names and expressions (maps to same rule shapes) |
| `snowflake_rules.py` | Snowflake-side expressions where they differ from Postgres |
| `athena_rules.py` | Athena-specific normalisation |

---

### `src/ai_transformation/` — Column Rule Mapping

#### `orchestrator.py`
Decides for each column whether to use AI or static mapping. Static mapping is always tried first. AI is called only for columns where static matching confidence is below the threshold.

#### `static_rule_mapper.py`
Pattern-matching mapper. Uses `ColumnRuleMapping` dataclass. Matches by exact type name, then by normalised type family. Returns `skip_validation=True` for unsupported types (bytea, xml, json, array).

#### `ai_rule_mapper.py`
Calls the DIAL API with a structured prompt (column name, source type, Snowflake type, sample data context). Parses the JSON response to a `ColumnRuleMapping`. Falls back to static on any error.

---

### `src/generated_queries/` — SQL and YAML Writers

#### `query_output_manager.py`
Orchestrates all file output for one table. Produces:
- `validation_sql/<table>_validation.sql` — all SQL queries
- `config/bronze/data_validation/<table>_validation.yaml` — data/null/distinct YAML
- `config/bronze/count_validation/bronze_count_validation.yaml` — count YAML (appended)

**Entry point:** `QueryOutputManager().generate(...)` or `generate_from_plan(plan)`.

#### `sql_query_generator.py`
Builds all 6–8 SQL queries from column mappings:

| Query | Description |
|---|---|
| ① Source row count | `SELECT COUNT(*) FROM <source_table>` |
| ② Target row count | `SELECT COUNT(*) FROM <sf_table> WHERE _FIVETRAN_ACTIVE = TRUE` |
| ③ Source data validation | Full normalised `SELECT` of all columns |
| ④ Target data validation | Full normalised `SELECT` of all Snowflake columns |
| ⑤ Source NULL % | `SELECT col, SUM(CASE WHEN col IS NULL ...)` per column |
| ⑥ Target NULL % | Same for Snowflake |
| ⑦ Source distinct count | `SELECT col, COUNT(DISTINCT col)` |
| ⑧ Target distinct count | Same for Snowflake |

#### `yaml_config_writer.py`
Writes YAML files. Default output paths (when `output_dir` is not passed):
- `_BRONZE_CONFIG_DIR = config/bronze/` (relative to project root)
- Data YAML → `config/bronze/data_validation/<table>_validation.yaml`
- Count YAML → `config/bronze/count_validation/bronze_count_validation.yaml`

The count YAML **appends** each table as a new block. On first write it creates the file header; subsequent writes append without duplicating the `tables:` key.

---

### `src/core/validation_plan.py` — Data Class

**What it does:** Holds all resolved decisions for one table pair:
- Source schema, table, database
- Snowflake database, schema, table
- Column mappings (exact matches, fuzzy matches, AI-resolved, skipped)
- `has_fivetran_active` flag
- `generated_by` and `model_used` metadata

`CanonicalValidationPlan` is the "single source of truth" passed between the matching, AI, and generation stages.

---

### `src/matching/` — Column Name Matching

| File | Purpose |
|---|---|
| `exact_matcher.py` | Case-insensitive exact match; also handles normalised names (strips underscores) |
| `fuzzy_matcher.py` | RapidFuzz token-sort ratio; returns top N candidates above threshold |
| `candidate_matcher.py` | Combines exact + fuzzy into a ranked candidate list per column |
| `confidence.py` | Multi-factor score: name similarity + type compatibility + ordinal position |
| `normalizer.py` | Strips special characters and lowercases for comparison |

---

### `src/ai/` — AI Pipeline Helpers

| File | Purpose |
|---|---|
| `rule_planner.py` | Inspects confidence scores; decides which columns go to AI |
| `prompt_builder.py` | Builds the structured JSON prompt sent to the AI model |
| `response_parser.py` | Parses the AI's JSON response into `ColumnRuleMapping` objects |

---

### `src/profiling/` — Schema Profiling (Dynamic Suite)

| File | Purpose |
|---|---|
| `schema_profiler.py` | Profiles columns: detects financial, enum, date, boolean, id types |
| `validation_rule_engine.py` | Decides which validation types each column needs (e.g. SUM for financial) |
| `ai_recommendation.py` | Asks AI for business-rule checks beyond the standard 6 queries |

---

### `src/dynamic_suite/` — Extended Validation Suite

Produces additional checks beyond the standard 6:
- MIN/MAX for date/numeric columns
- SUM for financial columns
- Duplicate detection for business-key columns
- Value distribution for enum/status columns

| File | Purpose |
|---|---|
| `suite_generator.py` | Entry point: builds `ValidationSuite` from schema profile |
| `query_optimizer.py` | Combines multiple column checks into fewer SQL round-trips |
| `validation_suite.py` | `ValidationSuite` data class holding all generated query pairs |

Output: `validation_sql/<table>_dynamic_suite.yaml` and `.sql`.

---

### `src/batch/` — Batch Processing

Run validation for many tables from a YAML config file:

```yaml
# tables.yaml
tables:
  - source_table: events
    sf_table: EVENTS
    pg_schema: public
    sf_schema: STOREDGE_FMS_PUBLIC
  - source_table: migration_test
    sf_table: MIGRATION_TEST
    ...
```

```powershell
python validate_cli.py batch --config tables.yaml --workers 4
```

| File | Purpose |
|---|---|
| `batch_runner.py` | Processes tables in parallel using ThreadPoolExecutor |
| `config_parser.py` | Loads and validates the batch YAML config |
| `manifest_writer.py` | Writes `_manifest.json` with per-table results |

---

### `src/model_probe.py` — AI Model Discovery

**What it does:** Probes the DIAL API to find which models respond successfully. Results are cached for 24 hours in `.dial_model_cache.json`. Used by menu option [4] and [7].

---

### `src/learning/` — Rule Feedback Loop

When a user corrects a rule assignment, the correction is saved to `src/rule_book_learned.json`.

| File | Purpose |
|---|---|
| `feedback.py` | `save_feedback(column_name, rule_name, source_expr, target_expr)` |
| `retrieval.py` | `get_rule_for_column(column_name)` — checks learned rules before base rules |

---

### `src/validation/plan_validator.py`

Validates a `CanonicalValidationPlan` before SQL generation. Checks for:
- Missing Snowflake matches
- Type mismatches above threshold
- Empty active mappings

---

## 5. Interactive Menu Reference

Start with: `python src/validate_cli.py`

```
[c]  Connections    — ping all configured databases
[1]  Single Table   — full workflow for one table
[2]  Run Tables     — pick source, type table names, process all
[3]  List tables    — show all tables in source + Snowflake
[4]  Select AI model
[5]  View rule book — see all 11 base + learned rules
[6]  Add custom rule
[7]  List available AI models
[8]  Connection profiles
[9]  Execute YAML   — run saved YAML queries, see pass/fail
[q]  Quit
```

### Menu [1] Single Table — Detailed Flow

1. Pick source connection (from SRC_N_* slots)
2. Pick schema (list from live DB)
3. Pick table (list from live DB)
4. Select Snowflake target: account → database → schema (live discovery)
5. Select Snowflake table (auto-matched by name, confidence %)
6. Specify columns to exclude (optional)
7. Select AI model
8. Pipeline runs: extract → match → map rules → generate SQL → write YAML

### Menu [2] Run Tables — Detailed Flow

1. Pick source connection
2. Pick schema
3. Type comma-separated table names (or Enter to list and pick)
4. Select Snowflake target (live discovery writes to env)
5. Snowflake tables auto-matched (100% = exact, lower % = fuzzy)
6. Specify exclusions (optional)
7. Each table processed in sequence

### Menu [9] Execute YAML — Detailed Flow

1. Lists all YAML files under `config/bronze/` (count + data)
2. Pick a file
3. Pick which table block (or run all)
4. Pick credentials: current `.env` or a saved profile
5. Pick validation block (count_validation, data_validation, etc.)
6. Runs source query (PostgreSQL/MSSQL) + target query (Snowflake)
7. Shows source result, target result, and PASS/FAIL per check
8. Summary: total passed / failed / errors

---

## 6. Connection Profiles

Profiles let you save a named (source + Snowflake) credential pair and reuse it without re-entering credentials.

**Storage:** `~/.migration-validator/profiles.json` — outside the repository, never committed.

**Profile schema:**
```json
{
  "MY_PROFILE": {
    "source": {
      "db_type": "mssql",
      "host": "EPINHYDW1D68",
      "port": 1433,
      "database": "DevT5000",
      "schema": "dbo",
      "username": "sa",
      "password": "..."
    },
    "snowflake": {
      "account": "ZJAUJWQ-EP12783",
      "database": "DEV_SITELINK_BRONZE",
      "schema": "AWSDEV_DEVT5000_DBO",
      "username": "user@company.com",
      "password": "...",
      "warehouse": "",
      "role": ""
    },
    "created_at": "2026-08-12T14:00:00"
  }
}
```

**Using profiles:**
- Profiles are offered during menu [9] Execute YAML (step 3)
- Also available via `--connection-profile NAME` CLI flag on `generate` and `multi` commands
- View profiles: menu [8] or `python validate_cli.py profiles list`
- Delete profile: menu [8] → delete, or `python validate_cli.py profiles delete NAME`

**Why profiles exist:** Different Snowflake databases can be on different accounts with different credentials. DEV_SITELINK_BRONZE and DEV_EDGE_BRONZE may need separate accounts. A profile saves the entire credential set so you switch between databases with one selection instead of editing `.env`.

---

## 7. Validation YAML Format

### Count Validation — `config/bronze/count_validation/bronze_count_validation.yaml`

One shared file. All tables are blocks under `tables:`. Each run with a new table **appends** to this file.

```yaml
tables:
  events:
    validations:
      count_validation:
        source_table_name: events
        source: postgres
        sourcequery: |
          SELECT COUNT(*) AS source_row_count
          FROM public.events;
        target_table_name: events
        target: snowflake
        targetquery: |
          SELECT COUNT(*) AS target_row_count
          FROM dev_edge_bronze.storedge_fms_public.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE;

  acctsoftware:
    validations:
      count_validation:
        ...
```

### Data Validation — `config/bronze/data_validation/<table>_validation.yaml`

One file per table. Three validation blocks:

```yaml
tables:
  events:
    validations:

      data_validation:          # Full normalised SELECT (all columns)
        source_table_name: events
        source: postgresql
        sourcecolumn: id        # first active column
        sourcequery: |
          SELECT
            CAST(id AS TEXT),
            TRIM(name),
            ...
          FROM public.events;
        target_table_name: EVENTS
        target: snowflake
        targetcolumn: ID
        targetquery: |
          SELECT
            CAST(ID AS TEXT),
            TRIM(NAME),
            ...
          FROM dev_edge_bronze.storedge_fms_public.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE;

      null_pct_validation:      # NULL % per column
        ...

      distinct_count_validation: # Distinct values per column
        ...
```

---

## 8. SQL Output Format

All generated `.sql` files land in `validation_sql/`. Each contains all 6–8 queries for one table, separated by headers:

```sql
-- ═══════════════════════════════════
-- Migration Validator — events
-- Generated: 2026-08-12T14:00:00
-- ═══════════════════════════════════

-- ① SOURCE row count
SELECT COUNT(*) AS source_row_count FROM public.events;

-- ② TARGET row count
SELECT COUNT(*) AS target_row_count
FROM dev_edge_bronze.storedge_fms_public.EVENTS
WHERE _FIVETRAN_ACTIVE = TRUE;

-- ③ SOURCE data validation
SELECT
  CAST(id AS TEXT) AS id,
  ...
FROM public.events;

-- ④ TARGET data validation
SELECT
  CAST(ID AS TEXT) AS ID,
  ...
FROM dev_edge_bronze.storedge_fms_public.EVENTS
WHERE _FIVETRAN_ACTIVE = TRUE;

-- ⑤ SOURCE NULL % per column
SELECT ...

-- ⑥ TARGET NULL % per column
...
```

---

## 9. Normalization Rules

All column values are normalised to text representations before comparison so type differences between PostgreSQL and Snowflake don't cause false failures.

| Type | PostgreSQL expression | Snowflake expression |
|---|---|---|
| boolean | `CASE WHEN {col} THEN '1' ELSE '0' END` | `CASE WHEN {col} THEN '1' ELSE '0' END` |
| integer / bigint | `CAST({col} AS TEXT)` | `CAST({col} AS TEXT)` |
| numeric / decimal | `CAST(ROUND(CAST({col} AS NUMERIC), 2) AS TEXT)` | `CAST(ROUND(CAST({col} AS FLOAT), 2) AS TEXT)` |
| text / varchar / char | `TRIM({col})` | `TRIM({col})` |
| timestamp | `TO_CHAR({col}, 'YYYY-MM-DD HH24:MI:SS')` | `TO_VARCHAR({col}, 'YYYY-MM-DD HH24:MI:SS')` |
| timestamp with time zone | `TO_CHAR({col} AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')` | `TO_VARCHAR(CONVERT_TIMEZONE('UTC', {col}), 'YYYY-MM-DD HH24:MI:SS')` |
| date | `TO_CHAR({col}, 'YYYY-MM-DD')` | `TO_VARCHAR({col}, 'YYYY-MM-DD')` |
| uuid | `UPPER(TRIM(CAST({col} AS TEXT)))` | `UPPER(TRIM(CAST({col} AS TEXT)))` |
| json / jsonb | `({col})::text` | `TO_JSON({col})::text` |
| NULL sentinel | `COALESCE(<expr>, '<<NULL>>')` | `COALESCE(<expr>, '<<NULL>>')` |
| Fivetran filter | _(not applicable)_ | `WHERE _FIVETRAN_ACTIVE = TRUE` |

---

## 10. Rule Book System

The rule book is the registry of all type-to-expression mappings.

**View rules:** Menu [5] in the interactive tool.

**Add a custom rule:** Menu [6]. Prompts for:
- Column name pattern (e.g. `amount`, `price`)
- PostgreSQL expression template
- Snowflake expression template
- Description

Custom rules are saved to `src/rule_book_learned.json` and persist across sessions.

**Rule priority:** Learned rules override base rules when a column name matches.

---

## 11. AI Integration (DIAL API)

DIAL is EPAM's LLM gateway. It routes requests to OpenAI, Anthropic, Google, and other providers through one consistent API.

**Configuration:**
```dotenv
DIAL_API_KEY=your-key
DIAL_ENDPOINT=https://your-dial-host/openai/deployments
DIAL_MODEL=gpt-4o
```

**How it's used:**
1. Static rule mapper runs first for all columns
2. Columns with low confidence (ambiguous type, unusual name) are sent to AI
3. AI receives: column name, source type, Snowflake type, table context
4. AI returns: recommended rule name + expressions
5. If AI fails: falls back to static mapping

**Model selection:** Menu [4] shows all working models (probed and cached in `.dial_model_cache.json`). Selecting a model sets `os.environ["DIAL_MODEL"]` for the session. To persist: update `DIAL_MODEL` in `.env`.

**Available models** (as of Aug 2026): gpt-4o, gpt-4o-2024-11-20, anthropic.claude-sonnet-5, gemini-2.5-pro.

---

## 12. Pipeline Flow — End to End

```
User picks source table + Snowflake target
         │
         ▼
[1] Extract source schema
    PostgresExtractor / MSSQLExtractor
    → List[ColumnMetadata] (name, type, nullable, pk)
         │
         ▼
[2] Extract Snowflake schema
    SnowflakeExtractor
    → List[ColumnMetadata]
    → has_fivetran_active (bool)
         │
         ▼
[3] Column matching
    ExactMatcher  → immediate match if name = name (case-insensitive)
    FuzzyMatcher  → RapidFuzz similarity for near-matches
    CandidateMatcher → merges, ranks by confidence score
         │
         ▼
[4] Rule assignment
    For each matched column pair:
      StaticRuleMapper  → looks up type in rule book
      If confidence < threshold:
        AI RulePlanner → sends to DIAL API
        AI response parsed → ColumnRuleMapping
         │
         ▼
[5] CanonicalValidationPlan built
    Holds all decisions: matches, rules, fivetran flag, metadata
         │
         ▼
[6] PlanValidator checks for errors
         │
         ▼
[7] SQLQueryGenerator builds all SQL
    → ValidationQuerySet (6–8 SQL strings)
         │
         ▼
[8] File output
    QueryOutputManager:
      ├── validation_sql/<table>_validation.sql
      ├── config/bronze/data_validation/<table>_validation.yaml
      └── config/bronze/count_validation/bronze_count_validation.yaml (append)
```

---

## 13. Adding a New Source Database

1. **Add a new extractor class** in `src/sql_extractor/extractors.py` — implement `extract_columns()`, `list_tables()`, `list_schemas()`, `detect_primary_key()`.
2. **Register it** in `_REGISTRY` at the bottom of `extractors.py`.
3. **Add normalisation rules** in a new file under `src/rules/`, following the pattern in `postgres_base_rules.py`.
4. **Add a live discovery function** in `src/setup_wizard.py` following `_discover_postgres_databases()`.
5. **Add env var support** — add the new type to `_normalize_db_type()` in `validate_cli.py`.

---

## 14. Batch Mode

Process many tables at once from a config file:

```powershell
python src/validate_cli.py batch --config tables.yaml
python src/validate_cli.py batch --config tables.yaml --dry-run
python src/validate_cli.py batch --config tables.yaml --workers 8 --verbose
```

`tables.yaml` example:
```yaml
tables:
  - source_table: events
    sf_table: EVENTS
    pg_schema: public
    sf_schema: STOREDGE_FMS_PUBLIC
    sf_database: DEV_EDGE_BRONZE
  - source_table: migration_test
    sf_table: MIGRATION_TEST
    pg_schema: public
    sf_schema: STOREDGE_FMS_PUBLIC
    sf_database: DEV_EDGE_BRONZE
    exclude_columns: [internal_id, debug_flag]
```

Results are written to `_manifest.json` in the working directory.

---

## 15. Tests

Tests are in two locations:
- `tests/` (root level) — integration tests requiring live connections
- `src/tests/` — unit tests that can run without any connections

```powershell
# Run unit tests (no DB required)
cd src
python -m pytest tests/ -v

# Run root-level tests (requires connections configured in .env)
cd ..
python -m pytest tests/ -v -k "not snowflake"  # skip Snowflake tests
```

Key test files:

| File | What it tests |
|---|---|
| `tests/test_sql_generation.py` | SQL query builder output |
| `tests/test_yaml_generation.py` | YAML writer output format |
| `tests/test_exact_matcher.py` | Exact column name matching |
| `tests/test_fuzzy_matching.py` | Fuzzy matching with RapidFuzz |
| `tests/test_normalization.py` | Type normalisation expressions |
| `tests/test_end_to_end.py` | Full pipeline with mock data |
| `src/tests/test_validation_rule_engine.py` | Rule engine logic |
| `src/tests/test_schema_profiler.py` | Schema profiler detection |

---

## 16. Dummy Data & Test Setup

### PostgreSQL

```powershell
# Start local PostgreSQL with Docker
docker-compose up -d

# Load test tables
psql -h localhost -U postgres -d fms -f dummy-data/postgres_setup.sql
```

Creates tables: `migration_test`, `events`, `general_ledger_line_items`, `abc`.

### Snowflake

Run `dummy-data/snowflake_setup.sql` in a Snowflake worksheet. Creates matching tables in your Snowflake database/schema.

### MSSQL test data

`MSServer-data/Addresses_mssqlserver.csv` — sample CSV data for the Addresses table.
`MSServer-data/addressess_mssqlserver_ddl.sql` — DDL to recreate the Addresses table.

---

## 17. Known Behaviours & Constraints

**Snowflake database switching:** The interactive target picker (`_pick_snowflake_target()`) asks for account + credentials and updates `os.environ` immediately. If your two Snowflake databases are on different accounts (e.g., DEV_EDGE_BRONZE on one account, DEV_SITELINK_BRONZE on another), the correct approach is to use connection profiles — each profile stores a full credential set for a specific account + database combination.

**Count YAML is appended, not replaced:** Running the pipeline twice for the same table will add a duplicate block to `bronze_count_validation.yaml`. Delete and regenerate if you need a clean file.

**_FIVETRAN_ACTIVE detection:** The tool automatically adds `WHERE _FIVETRAN_ACTIVE = TRUE` on the Snowflake side if the table has a column named `_FIVETRAN_ACTIVE`. This is detected during schema extraction.

**Unsupported types:** Columns of type `bytea`, `xml`, `array`, `json`, `jsonb`, `user-defined` are skipped by default (listed in the "skipped columns" summary). Add a custom rule via menu [6] to handle them.

**Windows encoding:** The tool writes all files as UTF-8. Box-drawing characters (╔, ║, etc.) in the banner require a UTF-8 capable terminal. In PowerShell, run `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` if you see garbled output.

**`.env` is never auto-updated:** The tool reads `.env` at startup via `python-dotenv`. Interactive selections update `os.environ` for the current session only. To make changes permanent, edit `.env` manually.

**Profile passwords are stored in plaintext** in `~/.migration-validator/profiles.json`. This is local-only storage outside the repo. Do not use profiles on shared machines.
