# 02 — Architecture

## Two Generations Side by Side

The codebase has two generations of code. The **legacy stack** was the first implementation; the **v2 stack** is the current active development path. Both exist in the repo simultaneously.

---

## Legacy Stack (preserved, not the main path)

```
validate_cli.py
  └─ validation_pipeline.run()   ← legacy mode
       ├─ schema_extractor.py    ← PG + SF schema extraction
       ├─ ai_transformation/     ← sends ENTIRE schema to AI in one call
       │    ├─ ai_rule_mapper.py
       │    └─ static_rule_mapper.py
       └─ generated_queries/     ← produces SQL + YAML
```

Problems with the legacy approach:
- Sends all columns to AI at once → high token cost
- No structured plan object → hard to validate or inspect
- No fuzzy/confidence scoring → AI decides everything

---

## v2 Stack (current active path)

```
validate_cli.py
  └─ validation_pipeline.run_with_plan()   ← 7-step plan-driven flow
       │
       ├─ Step 1: sql_extractor/           ← extract real schemas from both DBs
       │    ├─ postgres_extractor.py
       │    └─ snowflake_extractor.py
       │
       ├─ Step 2: matching/exact_matcher   ← case-insensitive + normalized name matching
       │
       ├─ Step 3: matching/fuzzy_matcher   ← RapidFuzz token_ratio scoring
       │         + matching/confidence     ← weighted score (name 40% + type 35% + position 10% + learned 15%)
       │
       ├─ Step 4: matching/candidate_matcher
       │         → resolved   if confidence ≥ 0.95
       │         → ai_needed  if confidence 0.75–0.95
       │         → unmatched  if confidence < 0.75
       │
       ├─ Step 5: ai/rule_planner          ← ONE AI call per ambiguous column only
       │    ├─ ai/prompt_builder.py        ← builds system + user prompt
       │    ├─ ai/response_parser.py       ← validates AI output, rejects hallucinated names
       │    └─ learning/retrieval.py       ← injects past corrections as examples
       │
       ├─ Step 6: validation/plan_validator ← 8 integrity checks on the plan
       │
       └─ Step 7: generated_queries/       ← SQL + YAML output from the plan
            ├─ sql_query_generator.py      ← 8 SQL queries
            └─ yaml_config_writer.py       ← 4 YAML blocks
```

---

## Standalone Tools (bridge between generations)

```
query_builder.py   ← connects to both DBs, extracts schema, builds all 8 SQL queries
                      without executing them. Uses legacy rule engine + new AI approach.

query_executor.py  ← takes the SQL file, executes it against live DBs,
                      prints coloured PASS/WARN/FAIL verdicts in terminal.
```

---

## Central Data Object: CanonicalValidationPlan

The `CanonicalValidationPlan` (in `core/validation_plan.py`) is the single source of truth that flows through all 7 steps. It contains:

- Table identifiers (PG schema/table, SF database/schema/table)
- List of `ColumnMappingEntry` objects — one per column pair
- Each `ColumnMappingEntry` holds:
  - source and target column names + types
  - how the match was made (`match_method`: CONFIGURED / EXACT / NORMALIZED_EXACT / FUZZY / FUZZY_AI / AI)
  - fuzzy score + confidence breakdown
  - which transformation rule to apply
  - whether AI resolved it + which learned example was used
  - whether to skip validation for this column
- `has_fivetran_active` flag
- Warnings, ambiguities, unmatched columns lists
- AI call count + model used

This object is validated (Step 6), then passed directly to the SQL and YAML generators (Step 7).

---

## Dynamic Suite (optional, schema-driven)

In addition to the standard 8 queries, there is an optional `dynamic_suite/` component that generates **business-logic-aware queries** based on what types of columns the table has:

```
dynamic_suite/suite_generator.py
  ├─ profiling/schema_profiler.py      ← classifies columns into 9 ColumnGroup types
  │                                       (NUMERIC_FINANCIAL, NUMERIC_QUANTITY, TEMPORAL,
  │                                        IDENTIFIER, STATUS_FLAG, TEXT_ENUM, etc.)
  ├─ profiling/validation_rule_engine.py ← decides which extra checks are needed
  │                                       (MIN/MAX, SUM, DUPLICATE_CHECK, VALUE_DIST)
  ├─ profiling/ai_recommendation.py    ← optional AI suggestions for business rules
  └─ dynamic_suite/query_optimizer.py  ← collapses all aggregates into ONE table scan
```

Key optimisation: instead of 5 separate full-table scans (one each for NULL%, DISTINCT, MIN/MAX, SUM, VALUE_DIST), the optimizer folds them all into a single SELECT statement per side.

---

## Key Design Decisions

### 1. NULL Sentinel `<<NULL>>`
All SQL expressions wrap columns in `COALESCE(CAST(col AS TEXT), '<<NULL>>')`.
This means SQL NULL becomes the string `<<NULL>>` — so when comparing PG and SF rows side by side, NULL = NULL works correctly in a text-based comparison. Without this, NULL != NULL always, making validation impossible.

### 2. Token-Efficient AI
The old approach sent the entire schema (all column pairs) to AI in one prompt. The new approach sends **only the ambiguous columns** (confidence 0.75–0.95). High-confidence matches are resolved without AI. Low-confidence matches are flagged as unmatched. Only the "middle" cases go to AI — typically 10–30% of columns.

### 3. No Database Execution in Main Flow
`validate_cli.py` → `validation_pipeline.run_with_plan()` generates SQL/YAML files and stops. It never executes the queries. Execution is optional via `query_executor.py`. This makes the main flow safe for engineers who have read-only DB access or who want to review SQL before running it.

### 4. Fivetran Auto-Filter
When `_FIVETRAN_ACTIVE` column is detected in the Snowflake schema, ALL target-side queries automatically get `WHERE _FIVETRAN_ACTIVE = TRUE` added. This filters out Fivetran-managed soft-deleted rows that would otherwise cause false row count mismatches.

### 5. Learning System
Human corrections from previous runs are stored in `rule_book_learned.json`. When the tool encounters a similar column in a future run, it:
- Boosts the fuzzy confidence score by 0.15 if a learned example matches
- Injects the correction as an example in the AI prompt

### 6. Model Probe with 24h Cache
The tool probes all 26 candidate DIAL models at startup (parallel, 6 threads) to find which ones actually respond. Results are cached for 24 hours. Only working models appear in the selection menu. As of 2026-08-10, only `gpt-4o` and `gpt-4` were responding.
