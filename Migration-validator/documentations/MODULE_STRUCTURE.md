# 📐 Migration Validator — Module Structure & Architecture

> **Version:** 2.0 (Modular)  
> **Pipeline:** PostgreSQL → Snowflake Data Completeness Validation  
> **No automatic execution** — all generated SQL is reviewed and run manually.

---

## 🗂️ Complete Project Layout

```
Migration-validator/
│
├── .env                          ← Your credentials (git-ignored)
├── .env.example                  ← Template — copy to .env
├── requirements.txt              ← Python dependencies
│
├── 📁 src/                       ← ALL source code
│   │
│   ├── 📦 rules/                 ══ MODULE 1: TRANSFORMATION RULES ══
│   │   ├── __init__.py           ← RuleRegistry + get_rule_for_type()
│   │   ├── base_rule.py          ← Abstract BaseValidationRule interface
│   │   ├── boolean_rule.py       ← BOOLEAN → '1'/'0'
│   │   ├── numeric_rule.py       ← NUMERIC → ROUND(2dp) → text
│   │   ├── timestamp_ntz_rule.py ← TIMESTAMP → 'YYYY-MM-DD HH24:MI:SS'
│   │   ├── timestamp_tz_rule.py  ← TIMESTAMPTZ → UTC → format
│   │   ├── date_rule.py          ← DATE → 'YYYY-MM-DD'
│   │   ├── text_rule.py          ← VARCHAR/TEXT → TRIM  [default fallback]
│   │   ├── uuid_rule.py          ← UUID → UPPER(TRIM())
│   │   ├── integer_rule.py       ← INT/BIGINT → CAST to text
│   │   ├── json_rule.py          ← JSON/JSONB → canonical text
│   │   ├── bytea_rule.py         ← BYTEA → lowercase hex text
│   │   └── null_rule.py          ← NULL → '<<NULL>>' standalone rule
│   │
│   ├── 📦 sql_extractor/         ══ MODULE 2: LIVE SCHEMA EXTRACTION ══
│   │   ├── __init__.py           ← Exports PostgresExtractor, SnowflakeExtractor
│   │   ├── base_extractor.py     ← ColumnMetadata, TableMetadata, BaseExtractor
│   │   ├── postgres_extractor.py ← Reads information_schema.columns from PG
│   │   └── snowflake_extractor.py← Reads INFORMATION_SCHEMA.COLUMNS from SF
│   │                                Detects _FIVETRAN_ACTIVE column
│   │
│   ├── 📦 ai_transformation/     ══ MODULE 3: COLUMN MAPPING + RULE ASSIGNMENT ══
│   │   ├── __init__.py           ← Exports + AVAILABLE_MODELS list
│   │   ├── static_rule_mapper.py ← Deterministic (pg_type, sf_type) matching
│   │   ├── ai_rule_mapper.py     ← DIAL/GPT-4o AI mapper + model selection
│   │   └── orchestrator.py       ← AI-first, static-fallback orchestrator
│   │                                set_model() for runtime model switching
│   │
│   ├── 📦 generated_queries/     ══ MODULE 4: SQL + YAML OUTPUT ══
│   │   ├── __init__.py           ← Exports SQLQueryGenerator, YAMLConfigWriter
│   │   ├── sql_query_generator.py← Builds 6 SQL validation queries (no PK)
│   │   ├── yaml_config_writer.py ← Writes YAML in project standard format
│   │   └── query_output_manager.py← Orchestrates both → saves .sql + .yaml
│   │
│   ├── rule_book.py              ══ MODULE 5: EVOLVING RULE CATALOG ══
│   │                                Loads base rules from rules_catalog.json
│   │                                Loads learned rules from rule_book_learned.json
│   │                                Builds AI prompt injection block
│   │                                Saves new learned rules to disk
│   │
│   ├── validation_pipeline.py    ══ MODULE 6: END-TO-END PIPELINE ══
│   │                                Wires modules 2→3→4 together
│   │                                Exposes model= parameter for selection
│   │                                CLI: python validation_pipeline.py --pg-table X
│   │
│   ├── validate_cli.py           ══ MODULE 7: INTERACTIVE CLI ══
│   │                                Main user-facing entry point
│   │                                Commands: generate | rules | add-rule |
│   │                                          list-models | list-tables
│   │                                Interactive menu when no command given
│   │
│   ├── rules_catalog.json        ← Rule definitions v3.0 (JSON)
│   │                                Machine-readable + AI prompt source
│   ├── rule_book_learned.json    ← Auto-created when first custom rule saved
│   │
│   └── (legacy — backward compat)
│       ├── models.py, transformation_rules.py, sql_generators.py
│       ├── database_connectors.py, validator.py, report_generator.py
│       └── dynamic_validator.py, ai_query_agent.py, schema_extractor.py
│
├── 📁 validation_sql/            ← GENERATED OUTPUT (one pair per table)
│   ├── events_validation.sql
│   ├── events_validation.yaml
│   ├── general_ledger_line_items_validation.sql
│   ├── general_ledger_line_items_validation.yaml
│   └── <table>_validation.{sql,yaml}
│
└── 📁 tests/                     ← Test fixtures and test data
```

---

## 🔁 Data Flow Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                     USER: validate_cli.py                          │
│                     python validate_cli.py generate                │
│                     --pg-table events --sf-table EVENTS            │
│                     --model gpt-4o-mini                            │
└───────────────────────────┬────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────────┐
│                MODULE 6: ValidationPipeline                        │
│                validation_pipeline.py                              │
│                                                                    │
│   Step 1 ──► sql_extractor     → pg_columns, sf_columns           │
│   Step 2 ──► ai_transformation → List[ColumnRuleMapping]          │
│   Step 3 ──► generated_queries → .sql + .yaml files               │
└────────────────────────────────────────────────────────────────────┘
       │                    │                         │
       ▼                    ▼                         ▼
┌─────────────┐   ┌─────────────────┐    ┌───────────────────────┐
│ MODULE 2    │   │ MODULE 3        │    │ MODULE 4              │
│ sql_extractor│   │ ai_transformation│    │ generated_queries     │
│             │   │                 │    │                       │
│ PostgreSQL  │   │ AIRuleMapper    │    │ SQLQueryGenerator     │
│   ↓         │   │  (model picker) │    │   → 6 SQL queries     │
│ ColumnMeta  │   │ StaticMapper    │    │                       │
│             │   │  (fallback)     │    │ YAMLConfigWriter      │
│ Snowflake   │   │                 │    │   → YAML config       │
│   ↓         │   │ ColumnRule      │    │                       │
│ ColumnMeta  │   │ Mapping[]       │    │ QueryOutputManager    │
│ + Fivetran? │   │                 │    │   → saves both files  │
└─────────────┘   └─────────────────┘    └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ MODULE 1: rules/      │
              │                       │
              │ BooleanRule           │
              │ NumericRule           │
              │ TimestampNTZRule      │
              │ TimestampTZRule       │
              │ DateRule              │
              │ TextRule (fallback)   │
              │ UUIDRule              │
              │ IntegerRule           │
              │ JSONRule              │
              │ ByteaRule             │
              │ NullPlaceholderRule   │
              └───────────────────────┘
```

---

## 📋 Generated YAML Format (Project Standard)

```yaml
tables:
  <source_table_name>:
    validations:
      data_validation:
        source_table_name: <source_table_name>
        source: postgresql
        sourcecolumn: <first_column>      # no PK dependency — first mapped column
        sourcequery: |
          SELECT
              COALESCE(CAST(CASE WHEN is_active = true THEN '1' … END AS TEXT), '<<NULL>>') AS is_active_normalized,
              COALESCE(CAST(ROUND(CAST(amount AS NUMERIC), 2) AS TEXT), '<<NULL>>') AS amount_normalized,
              COALESCE(CAST(TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS TEXT), '<<NULL>>') AS created_at_normalized,
              …
          FROM public.<source_table>;
        target_table_name: <TARGET_TABLE_NAME>
        target: snowflake
        targetcolumn: <FIRST_COLUMN>
        targetquery: |
          SELECT
              COALESCE(CAST(CASE WHEN IS_ACTIVE = TRUE THEN '1' … END AS STRING), '<<NULL>>') AS is_active_normalized,
              COALESCE(CAST(ROUND(CAST(AMOUNT AS NUMBER(38,2)), 2) AS STRING), '<<NULL>>') AS amount_normalized,
              COALESCE(CAST(TO_VARCHAR(CREATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS STRING), '<<NULL>>') AS created_at_normalized,
              …
          FROM <sf_db>.<sf_schema>.<TARGET_TABLE>
          WHERE _FIVETRAN_ACTIVE = TRUE;   ← only when _FIVETRAN_ACTIVE detected
```

---

## 🛡️ All Normalization Rules

| Rule ID        | PG Type(s)              | SF Type(s)       | PG SQL                                  | SF SQL                                  | Why                                      |
|----------------|-------------------------|------------------|-----------------------------------------|-----------------------------------------|------------------------------------------|
| `boolean`      | BOOLEAN, BOOL           | BOOLEAN          | `CASE WHEN col=true THEN '1' … END`    | `CASE WHEN col=TRUE THEN '1' … END`    | Case differences (true vs TRUE)           |
| `numeric`      | NUMERIC, DECIMAL, FLOAT | NUMBER, FLOAT    | `ROUND(CAST(col AS NUMERIC), 2)`       | `ROUND(CAST(col AS NUMBER(38,2)), 2)`  | Precision noise from ETL                 |
| `timestamp_ntz`| TIMESTAMP               | TIMESTAMP_NTZ    | `TO_CHAR(col,'YYYY-MM-DD HH24:MI:SS')` | `TO_VARCHAR(col,'YYYY-MM-DD HH24:MI:SS')` | Microsecond noise                     |
| `timestamp_tz` | TIMESTAMPTZ             | TIMESTAMP_TZ     | `TO_CHAR(col AT TIME ZONE 'UTC',…)`    | `TO_VARCHAR(CONVERT_TIMEZONE('UTC',col),…)` | Timezone offset differences         |
| `date`         | DATE                    | DATE             | `TO_CHAR(col,'YYYY-MM-DD')`            | `TO_VARCHAR(col,'YYYY-MM-DD')`         | Uniform date text                        |
| `text`         | VARCHAR, CHAR, TEXT     | VARCHAR, STRING  | `TRIM(col)`                            | `TRIM(col)`                            | Whitespace from ETL padding              |
| `uuid`         | UUID                    | TEXT, VARCHAR    | `UPPER(TRIM(CAST(col AS TEXT)))`       | `UPPER(TRIM(CAST(col AS STRING)))`     | Case differences (lower vs upper UUID)   |
| `integer`      | INTEGER, BIGINT, SERIAL | NUMBER, INTEGER  | `CAST(col AS TEXT)`                    | `CAST(col AS STRING)`                  | Type width differences                   |
| `json`         | JSON, JSONB             | VARIANT          | `col::jsonb::text`                     | `TO_JSON(PARSE_JSON(CAST(col AS STRING)))` | Key order / whitespace differences   |
| `bytea`        | BYTEA                   | BINARY           | `encode(col,'hex')`                    | `LOWER(HEX_ENCODE(col))`              | Binary → comparable text                 |
| `null`         | **ALL**                 | **ALL**          | `COALESCE(CAST(… AS TEXT),'<<NULL>>')` | `COALESCE(CAST(… AS STRING),'<<NULL>>')` | SQL NULL ≠ NULL                       |
| Fivetran filter| —                       | When detected    | —                                      | `WHERE _FIVETRAN_ACTIVE = TRUE`        | Compare only latest record, not history  |

---

## 🤖 AI Model Selection

```bash
# Per-run flag
python src/validate_cli.py generate --pg-table events --sf-table EVENTS \
    --model gpt-4o-mini

# Interactive selection
python src/validate_cli.py        # → [2] Select AI model

# Persistent default in .env
DIAL_MODEL=gpt-4o-mini

# Python API
from validation_pipeline import ValidationPipeline
pipeline = ValidationPipeline(model="claude-3-5-sonnet")
pipeline.set_model("gpt-4o")     # switch at runtime
```

**Available models** (via EPAM DIAL — requires VPN + `DIAL_API_KEY`):

| Model               | Best for                              |
|---------------------|---------------------------------------|
| `gpt-4o`            | Best accuracy (default)               |
| `gpt-4o-mini`       | Speed + cost efficiency               |
| `gpt-4-turbo`       | Large schemas (high context window)   |
| `claude-3-5-sonnet` | Alternative reasoning via DIAL bridge |
| `gemini-pro`        | Alternative via DIAL bridge           |

---

## 📚 Rule Book — Custom Rules

```bash
# Add a custom rule interactively
python src/validate_cli.py add-rule

# View all rules (base + learned)
python src/validate_cli.py rules
```

Custom rules are saved to `src/rule_book_learned.json` and automatically injected
into every AI prompt so the AI knows about them.

**Example learned rule:**
```json
{
  "id": "phone_strip",
  "display_name": "Phone Number Strip",
  "description": "Remove all non-numeric characters from phone numbers",
  "when_to_apply": "VARCHAR phone number columns (source_type=VARCHAR, target_type=VARCHAR)",
  "pg_sql_template": "REGEXP_REPLACE({col}, '[^0-9]', '', 'g')",
  "sf_sql_template": "REGEXP_REPLACE({col}, '[^0-9]', '')",
  "source_type": "VARCHAR",
  "target_type": "VARCHAR"
}
```

---

## ⚡ CLI Reference

```bash
# Interactive menu (recommended for first-time users)
python src/validate_cli.py

# Full generation with all options
python src/validate_cli.py generate \
    --pg-schema public \
    --pg-table events \
    --sf-schema STOREDGE_FMS_PUBLIC \
    --sf-table EVENTS \
    --sf-database DEV_EDGE_BRONZE \
    --model gpt-4o-mini

# View the rule book
python src/validate_cli.py rules

# Add a custom rule
python src/validate_cli.py add-rule

# List available AI models
python src/validate_cli.py list-models

# List tables in both databases
python src/validate_cli.py list-tables

# Direct pipeline (no interactive prompts)
python src/validation_pipeline.py \
    --pg-table events --sf-table EVENTS --model gpt-4o

# List models via pipeline
python src/validation_pipeline.py --list-models
```

---

## 🔮 Future Milestones (Deferred)

| Feature                          | Status      | Notes                                          |
|----------------------------------|-------------|------------------------------------------------|
| Primary key ordering & detection | ⏳ Deferred  | ORDER BY pk, auto-detect from DB constraints   |
| Duplicate PK check (Snowflake)   | ⏳ Deferred  | GROUP BY pk HAVING COUNT(*) > 1                |
| Missing rows check (two-step)    | ⏳ Deferred  | Compare pk_key across both systems             |
| Multi-table batch generation     | ⏳ Planned   | Process all tables in a schema at once         |
| HTML comparison report           | ⏳ Planned   | Visual diff of source vs target CSV results    |

---

*Migration Validator v2.0 — Built for PostgreSQL → Snowflake validation*
