# 06 — Pipeline Execution Flow

## Entry Point

User runs:
```
python validate_cli.py
```

An interactive menu appears. Selecting "Generate validation SQL" launches the main flow.

---

## Interactive Prompts (validate_cli.py)

The CLI asks the user for:

```
PostgreSQL database name:    [user types]
PostgreSQL schema:           [user types, default: public]
PostgreSQL table:            [user types]

Snowflake database:          [user types]
Snowflake schema:            [user types]
Snowflake table:             [user types]

Primary key columns:         [user types, comma-separated]

Select AI model:
  1. gpt-4o       [WORKING]
  2. gpt-4        [WORKING]
  (only working models shown — from 24h model probe cache)
```

Then the pipeline runs automatically.

---

## The 7-Step Plan-Driven Pipeline (run_with_plan)

### Step 1 — Schema Extraction

**Files:** `sql_extractor/postgres_extractor.py`, `sql_extractor/snowflake_extractor.py`

What happens:
- Connects to PostgreSQL via `SOURCE_*` env vars
- Runs `SELECT column_name, data_type, udt_name, is_nullable, ordinal_position, ...
  FROM information_schema.columns WHERE table_schema = %s AND table_name = %s`
- Detects USER-DEFINED types (hstore, citext) by checking `udt_name`
- Same for Snowflake, but column names returned in UPPERCASE
- Checks if `_FIVETRAN_ACTIVE` exists in Snowflake schema → sets `has_fivetran_active` flag

**Output:** Two lists of `ColumnMetadata` objects (PG columns + SF columns)

---

### Step 2 — Exact Matching

**File:** `matching/exact_matcher.py`

What happens (3 priority levels):
1. **Priority 0 (Configured):** If user provided explicit column mappings in config, use those directly
2. **Priority 1 (Case-insensitive exact):** `user_id` matches `USER_ID` — same letters, different case
3. **Priority 2 (Normalized exact):** `user_id` vs `userid` — strip underscores + lowercase

Columns matched here are immediately `resolved` — no fuzzy scoring or AI needed.

**Output:** `ExactMatchResult` per column (matched or unmatched)

---

### Step 3 — Fuzzy Matching + Confidence Scoring

**Files:** `matching/fuzzy_matcher.py`, `matching/confidence.py`

What happens for each unmatched column:

**Fuzzy scoring (RapidFuzz):**
```
source: "created_by_user"
candidates: ["CREATED_BY", "CREATED_BY_USER_ID", "LAST_MODIFIED_BY"]
token_ratio scores: [0.87, 0.91, 0.62]
```

**Confidence scoring (weighted):**
```
name_similarity_weight:    0.40   (from fuzzy score)
type_compatibility_weight: 0.35   (from 40+ known PG→SF type pairs)
position_proximity_weight: 0.10   (ordinal position distance)
learned_example_weight:    0.15   (boost if past human correction matches)

final_confidence = sum of (score × weight)
```

Type compatibility examples in the 40+ pair list:
- `("integer", "NUMBER")` → compatible
- `("boolean", "BOOLEAN")` → compatible
- `("boolean", "NUMBER(1,0)")` → compatible
- `("text", "VARCHAR")` → compatible
- `("timestamp without time zone", "TIMESTAMP_NTZ")` → compatible

**Output:** Top-N `FuzzyCandidate` objects per unmatched source column, each with confidence score and breakdown

---

### Step 4 — Classification

**File:** `matching/candidate_matcher.py`

```
confidence ≥ 0.95  → resolved        (accept best fuzzy match, no AI needed)
0.75 ≤ confidence < 0.95 → ai_needed (send to AI for disambiguation)
confidence < 0.75  → unmatched       (flag for human review)
```

Constants:
```python
FUZZY_HIGH_CONFIDENCE = 0.95
FUZZY_AI_REVIEW = 0.75
```

**Output:** `MatchDecision` per column: `resolved` | `ai_needed` | `unmatched`

---

### Step 5 — AI Resolution (One Call Per Ambiguous Column)

**Files:** `ai/rule_planner.py`, `ai/prompt_builder.py`, `ai/response_parser.py`, `learning/retrieval.py`

What happens for each `ai_needed` column:

1. Load relevant learned examples from `rule_book_learned.json` (scored by name/type similarity)
2. Build system prompt (rule reference table + JSON contract)
3. Build user prompt (one column + top candidates + learned examples)
4. Call DIAL AzureOpenAI API (temperature=0, JSON mode)
5. Parse + validate response (must choose from provided candidates, rule must be known)
6. On any error → fallback: accept best fuzzy candidate without AI

If no `DIAL_API_KEY` is set → all `ai_needed` columns fall back to best fuzzy match.

**Output:** `PlannerResult` with decisions dict + number of AI calls made

---

### Step 6 — Plan Validation

**File:** `validation/plan_validator.py`

8 checks run on the assembled plan:

| Check | Type | What It Does |
|-------|------|--------------|
| 1 | Error | Table identity fields are non-empty (schema, table names) |
| 2 | Error | At least one active (non-skipped) mapping exists |
| 3 | Error | No duplicate source column names in mappings |
| 4 | Warning | No duplicate target column names (warns but doesn't block) |
| 5 | Error | All column names are non-empty strings |
| 6 | Warning | All transformation rule IDs are in the known set |
| 7 | Warning | All confidence values are in [0.0, 1.0] |
| 8 | Error | Plan status is not already INVALID |

If any Error check fails → `PlanValidationError` is raised → pipeline stops.

**Output:** `ValidationResult(is_valid, issues, warnings)`

---

### Step 7 — SQL + YAML Generation

**Files:** `generated_queries/sql_query_generator.py`, `generated_queries/yaml_config_writer.py`, `generated_queries/query_output_manager.py`

The `CanonicalValidationPlan` is passed to:

**SQL Generator → 8 queries:**
1. `SELECT COUNT(*) FROM pg_schema.pg_table` (PG row count)
2. `SELECT COUNT(*) FROM sf_database.sf_schema.sf_table WHERE ...` (SF row count, with Fivetran filter if needed)
3. PG main validation SELECT (normalised column expressions)
4. SF main validation SELECT (normalised column expressions)
5. PG NULL % per column
6. SF NULL % per column
7. PG DISTINCT count per column
8. SF DISTINCT count per column

**YAML Writer → 4 blocks:**
```yaml
row_count_check:
  source_sql: |
    SELECT COUNT(*) FROM ...
  target_sql: |
    SELECT COUNT(*) FROM ...

data_completeness:
  source_sql: |
    SELECT col1, col2, ... FROM ...
  target_sql: |
    SELECT COL1, COL2, ... FROM ...

null_percentage:
  source_sql: |
    SELECT
      ROUND(100.0 * SUM(CASE WHEN col1 IS NULL ...) / COUNT(*), 2) AS col1_null_pct,
      ...
  target_sql: |
    ...

distinct_count:
  source_sql: |
    SELECT
      COUNT(DISTINCT col1) AS col1_distinct,
      ...
  target_sql: |
    ...
```

**Files saved to:**
```
src/validation_sql/<table>_validation.sql
src/validation_sql/<table>_validation.yaml
```

---

## Optional: Live Execution (query_executor.py)

After generation, `validate_cli.py` asks:

```
Execute these queries now? [y/N]
```

If yes, `QueryExecutor.execute_all()` runs:

| Order | Query | What It Checks |
|-------|-------|----------------|
| 1 | PG row count | Source row count |
| 2 | SF row count | Target row count |
| 3 | PG null % | Column-level null distribution (source) |
| 4 | SF null % | Column-level null distribution (target) |
| 5 | SF duplicate PK | Duplicates in target (expect 0) |
| 6 | Missing rows | PKs in PG not in SF |
| 7 | PG main validation | First 20 rows shown in table format |
| 8 | SF main validation | First 20 rows shown in table format |

Verdict thresholds:
```
Row count diff > 5%   → FAIL
Row count diff 1–5%   → WARN
Row count diff < 1%   → PASS

NULL % diff > 5%      → FAIL
NULL % diff ≤ 5%      → PASS

Duplicate PKs > 0     → FAIL
Missing rows > 0      → FAIL
```

Final summary box printed with overall PASS/WARN/FAIL/ERROR status.

---

## Legacy Flow (run — 3 Steps)

Used when `validation_pipeline.run()` is called directly (not `run_with_plan()`):

```
Step 1: sql_extractor/ → schema extraction (same as v2)
Step 2: ai_transformation/orchestrator → sends ALL columns to AI at once
Step 3: generated_queries/ → SQL + YAML generation
```

No fuzzy matching, no confidence scoring, no plan object, no 8-check validation.
