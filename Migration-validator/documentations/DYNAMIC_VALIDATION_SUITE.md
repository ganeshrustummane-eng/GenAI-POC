# Dynamic Validation Suite — Architecture & Developer Guide

> **What this is:** A schema-driven, self-adapting validation system built on top of the existing 8-query baseline. It profiles each table, decides which additional checks are warranted, and collapses all aggregate statistics into a single optimised query per side.

---

## Table of Contents

1. [Problem with Static Validation](#1-problem-with-static-validation)
2. [Architecture Overview](#2-architecture-overview)
3. [Pipeline Step-by-Step](#3-pipeline-step-by-step)
4. [Column Groups (Semantic Classification)](#4-column-groups-semantic-classification)
5. [Validation Types — Baseline vs Conditional](#5-validation-types--baseline-vs-conditional)
6. [The Query Optimizer — Why It Matters](#6-the-query-optimizer--why-it-matters)
7. [AI Recommendation Layer](#7-ai-recommendation-layer)
8. [Generated SQL — Full Example](#8-generated-sql--full-example)
9. [Module Reference](#9-module-reference)
10. [How to Run](#10-how-to-run)
11. [How to Extend](#11-how-to-extend)
12. [Test Coverage](#12-test-coverage)
13. [Decision Matrix — What Triggers What](#13-decision-matrix--what-triggers-what)

---

## 1. Problem with Static Validation

The original 8-query baseline is excellent but identical for every table:

| Query | What it checks |
|---|---|
| ① ② | Row count |
| ③ ④ | Full normalised data diff |
| ⑤ ⑥ | NULL % per column |
| ⑦ ⑧ | Distinct count per column |

These 8 queries do NOT detect:

- **Value truncation in financial data** — SUM(amount) differs by $10,000 while row counts are equal
- **Duplicate rows created by ETL** — GROUP BY customer_id HAVING COUNT(*) > 1
- **Extreme value corruption** — MIN(salary) = -999999 (sign flip during migration)
- **Domain violations** — quantity < 0, end_date < start_date, invalid status values

The dynamic suite adds these checks automatically based on what columns are in the table — without requiring manual configuration.

---

## 2. Architecture Overview

```
Table
  ↓
Schema Extraction (existing — PostgresExtractor / SnowflakeExtractor)
  ↓
SchemaProfiler                     ← profiling/schema_profiler.py
  Classifies each column into semantic groups:
  NUMERIC_FINANCIAL, NUMERIC_QUANTITY, IDENTIFIER,
  TEMPORAL, STATUS_FLAG, TEXT_ENUM, SKIPPED, …
  ↓
ValidationRuleEngine               ← profiling/validation_rule_engine.py
  Maps column groups → ValidationRequirement list
  Baseline: always ROW_COUNT + DATA_VALIDATION + NULL_PCT + DISTINCT_COUNT
  Conditional: MIN_MAX, SUM, DUPLICATE_CHECK, VALUE_DIST (when relevant columns exist)
  ↓
AIRecommendationEngine (optional)  ← profiling/ai_recommendation.py
  Sends column names + types to DIAL
  Returns business-rule condition fragments (no row data)
  Gracefully skipped when DIAL_API_KEY is absent
  ↓
QueryOptimizer                     ← dynamic_suite/query_optimizer.py
  Collapses all aggregate requirements (NULL_PCT + DISTINCT + MIN_MAX + SUM + VALUE_DIST)
  into ONE combined aggregate query per side
  ↓
ValidationSuite                    ← dynamic_suite/validation_suite.py
  Output container: all SQL, all requirements, all AI recommendations
  .to_combined_sql()    → write to .sql file
  .to_summary_dict()    → embed in JSON report
```

---

## 3. Pipeline Step-by-Step

### Step 1 — Schema Profiling

```python
from profiling import SchemaProfiler

profiler = SchemaProfiler()
profile  = profiler.profile(source_columns, schema="public", table="orders")
print(profile.summary())
```

Output:
```
Table: public.orders
  Total columns    : 8
  Financial        : 1 — amount
  Quantity         : 1 — quantity
  Temporal         : 1 — created_at
  Identifiers      : 2 — order_id, customer_id
  Status/Flag      : 1 — is_active
  Text Enum        : 1 — status
  Skipped          : 1 — metadata (jsonb)
  Business keys    : order_id, customer_id
```

### Step 2 — Validation Decision

```python
from profiling import ValidationRuleEngine

engine       = ValidationRuleEngine()
requirements = engine.decide(profile)

for req in requirements:
    tag = "[conditional]" if req.is_conditional else "[baseline]"
    print(f"{req.query_number_src}/{req.query_number_tgt}  {req.label}  {tag}")
```

Output:
```
① / ②   Row Count                              [baseline]
③ / ④   Full Data Validation (normalised)      [baseline]
⑤ / ⑥   NULL % Per Column                     [baseline]
⑦ / ⑧   Distinct Value Count Per Column       [baseline]
⑨ / ⑩   MIN / MAX Per Numeric Column          [conditional]
⑪ / ⑫   SUM Reconciliation (Financial/Qty)    [conditional]
⑬ / ⑭   Duplicate Check (Business Key)        [conditional]
⑮ / ⑯   Value Distribution (Status/Enum)      [conditional]
```

### Step 3 — Query Optimisation

Instead of 8 separate aggregate queries (one per requirement pair), the optimizer collapses them:

```
BEFORE optimisation                AFTER optimisation
─────────────────────────────────  ─────────────────────────────────
Source NULL % query                ONE combined aggregate source query
Source DISTINCT query              (contains all aggregate functions)
Source MIN/MAX query         →
Source SUM query
─────────────────────────────────
Target NULL % query                ONE combined aggregate target query
Target DISTINCT query
Target MIN/MAX query         →
Target SUM query
```

**Result:** 8 aggregate requirements → 1 source query + 1 target query (2 scans instead of 8).

### Step 4 — Suite Assembly

```python
from dynamic_suite import DynamicSuiteGenerator

gen   = DynamicSuiteGenerator()
suite = gen.generate(
    source_columns=pg_columns,
    source_schema="public",
    source_table="orders",
    sf_database="MY_DB",
    sf_schema="MY_SCHEMA",
    sf_table="ORDERS",
    has_fivetran_active=True,
    active_mappings=rule_mappings,       # from canonical plan
    use_ai_recommendations=True,
)

with open("orders_validation_suite.sql", "w") as f:
    f.write(suite.to_combined_sql())
```

---

## 4. Column Groups (Semantic Classification)

The `SchemaProfiler` classifies every column into one primary group:

| Group | Classification Logic | Example Columns |
|---|---|---|
| `NUMERIC_FINANCIAL` | Numeric type AND name contains: amount, balance, price, salary, cost, revenue, fee, tax, discount… | `amount`, `total_price`, `monthly_salary` |
| `NUMERIC_QUANTITY` | Numeric type AND name contains: quantity, qty, count, units, stock, volume, capacity… | `quantity`, `units_sold`, `item_count` |
| `NUMERIC_GENERIC` | Any other numeric column | `score`, `age`, `rating` |
| `TEMPORAL` | date, timestamp, timestamptz, timestamp_ntz, timestamp_tz types | `created_at`, `updated_date`, `event_time` |
| `IDENTIFIER` | name ends with _id, _key, _uuid, _guid OR uuid type | `customer_id`, `order_id`, `external_uuid` |
| `STATUS_FLAG` | boolean type OR name starts with is_, has_, can_, was_ | `is_active`, `has_children`, `active` |
| `TEXT_ENUM` | VARCHAR/TEXT whose name suggests an enum value | `status`, `account_type`, `order_state` |
| `TEXT_GENERIC` | All other text columns | `description`, `notes`, `address` |
| `SKIPPED` | JSON, JSONB, ARRAY, BYTEA, HSTORE — not comparable | `metadata`, `tags`, `binary_data` |

**Priority order when multiple groups match:**
1. SKIPPED (always first — non-comparable types)
2. TEMPORAL (type-driven — unambiguous)
3. IDENTIFIER (name wins over type — `customer_id bigint` is an identifier, not numeric)
4. STATUS_FLAG (boolean type or flag prefix)
5. NUMERIC groups (financial > quantity > generic, keyword-based)
6. TEXT groups (enum name check > generic)

---

## 5. Validation Types — Baseline vs Conditional

### Baseline validations (always generated)

| Type | Trigger | What it catches |
|---|---|---|
| `ROW_COUNT` | Always | Missing or duplicated rows |
| `DATA_VALIDATION` | Always | Value-level differences in any column |
| `NULL_PCT` | Always | NULL introduced or eliminated by ETL |
| `DISTINCT_COUNT` | Always | Cardinality collapse (deduplication errors) |

### Conditional validations (triggered by column profile)

| Type | Trigger condition | What it catches |
|---|---|---|
| `MIN_MAX` | Any numeric column exists | Range truncation, extreme-value loss, sign flips |
| `SUM` | NUMERIC_FINANCIAL or NUMERIC_QUANTITY column exists | Financial reconciliation — invisible to row count |
| `DUPLICATE_CHECK` | IDENTIFIER column that is NOT NULL | ETL fan-out, dedup failures, insert-insert race |
| `VALUE_DIST` | STATUS_FLAG or TEXT_ENUM column exists | Boolean-to-int mapping errors, enum value truncation |

### Why SUM is so important

```
PostgreSQL COUNT(*) = 100,000   ← row counts match
Snowflake  COUNT(*) = 100,000   ← ✓ passes row count check
Distinct count also matches      ← ✓ passes distinct check
NULL % also matches              ← ✓ passes NULL check

PostgreSQL SUM(amount) = 15,430,250.50
Snowflake  SUM(amount) = 15,420,250.50   ← ✗ FAILS SUM check — $10,000 missing

Only SUM catches this.
```

---

## 6. The Query Optimizer — Why It Matters

Without optimization, N aggregate requirements → 2N database scans.

A table with `amount, quantity, status, is_active, order_id` would trigger:
- NULL % query
- DISTINCT query
- MIN/MAX query (amount + quantity)
- SUM query (amount + quantity)
- VALUE_DIST query (status + is_active)

= **10 queries** (5 × 2 sides) = 10 full table scans

With optimization:
```sql
-- ONE combined aggregate query per side
SELECT
    COUNT(*)                          AS total_rows,
    -- NULL % (NULL_PCT requirement)
    ROUND(100.0 * SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4)
                                      AS amount_null_pct,
    ROUND(100.0 * SUM(CASE WHEN quantity IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4)
                                      AS quantity_null_pct,
    -- DISTINCT (DISTINCT_COUNT requirement)
    COUNT(DISTINCT amount)            AS amount_distinct_count,
    COUNT(DISTINCT quantity)          AS quantity_distinct_count,
    -- MIN / MAX (MIN_MAX requirement)
    MIN(amount)                       AS amount_min,
    MAX(amount)                       AS amount_max,
    MIN(quantity)                     AS quantity_min,
    MAX(quantity)                     AS quantity_max,
    -- SUM (SUM requirement)
    SUM(amount)                       AS amount_sum,
    SUM(quantity)                     AS quantity_sum
FROM public.orders;
```

= **2 queries** (1 source + 1 target) = 2 full table scans

**10 scans → 2 scans.** The DUPLICATE_CHECK stays separate (GROUP BY + HAVING semantics cannot be merged into an aggregate SELECT).

---

## 7. AI Recommendation Layer

The `AIRecommendationEngine` sends only column metadata (names and types — no row data) to DIAL and receives back business-rule condition fragments.

### What AI receives (prompt excerpt)

```
Table: public.orders

Columns:
  - order_id   (integer, NOT NULL, group=identifier)
  - amount     (numeric, NULLABLE, group=numeric_financial)
  - quantity   (integer, NULLABLE, group=numeric_quantity)
  - status     (character varying, NULLABLE, group=text_enum)
  - created_at (timestamp without time zone, NULLABLE, group=temporal)
```

### What AI returns

```json
{
  "recommendations": [
    {
      "check_name": "non_negative_amount",
      "description": "Amount must be non-negative",
      "columns": ["amount"],
      "pg_expr": "amount >= 0",
      "sf_expr": "AMOUNT >= 0",
      "severity": "error",
      "rationale": "Financial columns should never be negative unless explicitly modelling debt"
    },
    {
      "check_name": "positive_quantity",
      "description": "Quantity must be positive",
      "columns": ["quantity"],
      "pg_expr": "quantity > 0",
      "sf_expr": "QUANTITY > 0",
      "severity": "warning",
      "rationale": "Negative quantities typically indicate data entry errors"
    }
  ]
}
```

### How AI recommendations are embedded in the SQL output

```sql
-- ================================================================
-- AI-RECOMMENDED BUSINESS RULE CHECKS
-- These are condition fragments. Run as:
--   SELECT COUNT(*) FROM <table> WHERE NOT (<condition>);
-- Any count > 0 = data quality issue.
-- ================================================================

-- AI Recommendation: Amount must be non-negative
-- Severity : error
-- Columns  : amount
-- Condition: amount >= 0
-- Run on PostgreSQL:
SELECT COUNT(*) AS violating_rows
FROM public.orders
WHERE NOT (amount >= 0);

-- Run on Snowflake:
SELECT COUNT(*) AS violating_rows
FROM MY_DB.MY_SCHEMA.ORDERS
WHERE _FIVETRAN_ACTIVE = TRUE AND NOT (AMOUNT >= 0);
```

### Graceful degradation

If `DIAL_API_KEY` is absent or the API call fails:
- AI recommendations are skipped silently
- All baseline and conditional validations still run
- A warning is printed to stderr but the pipeline completes normally

---

## 8. Generated SQL — Full Example

For a table `orders(order_id integer NOT NULL, amount numeric, quantity integer, status varchar, created_at timestamp)`:

```sql
-- ========================================================================
-- DYNAMIC MIGRATION VALIDATOR — Generated Validation Suite
-- Source       : public.orders
-- Target       : MY_DB.MY_SCHEMA.ORDERS
-- Generated    : 2026-08-10T14:30:00
-- Total checks : 4 query pair(s)
-- Fivetran     : YES — WHERE _FIVETRAN_ACTIVE = TRUE
-- ========================================================================

-- ────────────────────────────────────────────────────────────────────────
-- SOURCE ① / ② — Row Count
-- ────────────────────────────────────────────────────────────────────────
-- ① ROW COUNT: PostgreSQL (public.orders)
SELECT COUNT(*) AS source_row_count
FROM public.orders;

-- ② ROW COUNT: Snowflake (MY_DB.MY_SCHEMA.ORDERS)
SELECT COUNT(*) AS target_row_count
FROM MY_DB.MY_SCHEMA.ORDERS WHERE _FIVETRAN_ACTIVE = TRUE;

-- ────────────────────────────────────────────────────────────────────────
-- SOURCE ③ / ④ — Full Data Validation (normalised)
-- ────────────────────────────────────────────────────────────────────────
-- ③ SOURCE: PostgreSQL (public.orders)
SELECT
    COALESCE(CAST(CAST(order_id AS TEXT) AS TEXT), '<<NULL>>') AS order_id_normalized,
    COALESCE(ROUND(CAST(amount AS NUMERIC), 2)::TEXT, '<<NULL>>') AS amount_normalized,
    ...
FROM public.orders;

-- ────────────────────────────────────────────────────────────────────────
-- SOURCE ⑤–⑫ combined — Combined Aggregate Query (NULL% + DISTINCT + MIN/MAX + SUM)
-- ────────────────────────────────────────────────────────────────────────
-- ⑤–⑫ COMBINED AGGREGATE: PostgreSQL (public.orders)
-- One scan replaces 4 separate aggregate query types.
SELECT
    COUNT(*) AS total_rows,
    ROUND(100.0 * SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS amount_null_pct,
    ROUND(100.0 * SUM(CASE WHEN quantity IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS quantity_null_pct,
    COUNT(DISTINCT amount) AS amount_distinct_count,
    COUNT(DISTINCT quantity) AS quantity_distinct_count,
    MIN(amount) AS amount_min,
    MAX(amount) AS amount_max,
    MIN(quantity) AS quantity_min,
    MAX(quantity) AS quantity_max,
    SUM(amount) AS amount_sum,
    SUM(quantity) AS quantity_sum
FROM public.orders;

-- ────────────────────────────────────────────────────────────────────────
-- SOURCE ⑬ / ⑭ — Duplicate Check (Business Key)
-- ────────────────────────────────────────────────────────────────────────
-- ⑬ DUPLICATE CHECK: PostgreSQL (public.orders)
-- Expect: 0 rows returned.
SELECT
    order_id,
    COUNT(*) AS duplicate_count
FROM public.orders
GROUP BY order_id
HAVING COUNT(*) > 1;
```

---

## 9. Module Reference

### `profiling/schema_profiler.py`

| Class / Function | Description |
|---|---|
| `SchemaProfiler` | Main classifier |
| `SchemaProfiler.profile(columns, schema, table)` | Returns `TableProfile` |
| `TableProfile` | Aggregate of all `ColumnProfile` + helper properties |
| `ColumnProfile` | One column's classification (group, business_key, has_precision) |
| `ColumnGroup` | Enum of all semantic groups |

### `profiling/validation_rule_engine.py`

| Class / Function | Description |
|---|---|
| `ValidationRuleEngine` | Decision engine |
| `ValidationRuleEngine.decide(profile)` | Returns `List[ValidationRequirement]` |
| `ValidationRequirement` | One validation type + its columns + reason |
| `ValidationType` | Enum: ROW_COUNT, DATA_VALIDATION, NULL_PCT, DISTINCT_COUNT, MIN_MAX, SUM, DUPLICATE_CHECK, VALUE_DIST |

### `profiling/ai_recommendation.py`

| Class / Function | Description |
|---|---|
| `AIRecommendationEngine` | Calls DIAL for business-rule suggestions |
| `AIRecommendationEngine.recommend(profile)` | Returns `List[AIRecommendation]` |
| `AIRecommendation` | One suggestion: check_name, pg_expr, sf_expr, severity |

### `dynamic_suite/query_optimizer.py`

| Class / Function | Description |
|---|---|
| `QueryOptimizer` | Collapses requirements into minimal queries |
| `QueryOptimizer.optimize(requirements, profile, …)` | Returns `List[GeneratedQuery]` |

### `dynamic_suite/validation_suite.py`

| Class / Function | Description |
|---|---|
| `ValidationSuite` | Output container |
| `ValidationSuite.to_combined_sql()` | Full .sql file content |
| `ValidationSuite.to_summary_dict()` | JSON-serialisable summary |
| `GeneratedQuery` | One query pair (source SQL + target SQL) |

### `dynamic_suite/suite_generator.py`

| Class / Function | Description |
|---|---|
| `DynamicSuiteGenerator` | Top-level orchestrator |
| `DynamicSuiteGenerator.generate(…)` | Runs all 4 steps, returns `ValidationSuite` |

---

## 10. How to Run

### Standalone (from Python)

```python
import os
from dotenv import load_dotenv
load_dotenv()

from sql_extractor import PostgresExtractor, SnowflakeExtractor
from dynamic_suite import DynamicSuiteGenerator

# Extract schemas
pg = PostgresExtractor()
sf = SnowflakeExtractor()

pg_cols = pg.extract_columns("public", "orders")

gen   = DynamicSuiteGenerator()
suite = gen.generate(
    source_columns=pg_cols,
    source_schema="public",
    source_table="orders",
    sf_database=os.getenv("SNOWFLAKE_DATABASE"),
    sf_schema=os.getenv("SNOWFLAKE_SCHEMA"),
    sf_table="ORDERS",
    has_fivetran_active=True,
    use_ai_recommendations=True,
)

with open("validation_sql/orders_dynamic_suite.sql", "w", encoding="utf-8") as f:
    f.write(suite.to_combined_sql())

import json
print(json.dumps(suite.to_summary_dict(), indent=2))
```

### Via CLI (if wired into validate_cli.py)

The `DynamicSuiteGenerator` can be called from `validate_cli.py` after the canonical plan is built:

```python
from dynamic_suite import DynamicSuiteGenerator

gen   = DynamicSuiteGenerator()
suite = gen.generate(
    source_columns=source_meta.columns,
    source_schema=plan.source_schema,
    source_table=plan.source_table,
    sf_database=plan.target_database,
    sf_schema=plan.target_schema,
    sf_table=plan.target_table,
    has_fivetran_active=plan.has_fivetran_active,
    active_mappings=rule_mappings,
    use_ai_recommendations=True,
    generated_by=plan.generated_by,
    model_used=plan.model_used,
)
```

---

## 11. How to Extend

### Add a new column group

1. Add a new value to `ColumnGroup` enum in `schema_profiler.py`
2. Add classification logic in `SchemaProfiler._classify()`
3. Add a property in `TableProfile` to expose the new group
4. Add a new `ValidationType` in `validation_rule_engine.py`
5. Add the decision logic in `ValidationRuleEngine.decide()`
6. Add SQL generation in `QueryOptimizer.optimize()` or `_combined_aggregate_sql()`
7. Write tests in `tests/test_schema_profiler.py` and `tests/test_validation_rule_engine.py`

### Add a new conditional validation

Example: adding a `REFERENTIAL_INTEGRITY` check for foreign-key columns:

```python
# In validation_rule_engine.py — ValidationRuleEngine.decide()
fk_cols = [p for p in profile.identifier_columns if p.column_name.endswith("_id") and p.column_name != "id"]
if fk_cols:
    requirements.append(ValidationRequirement(
        validation_type=ValidationType.REFERENTIAL_INTEGRITY,
        columns=fk_cols,
        label="Foreign Key Non-NULL Check",
        query_number_src="⑰",
        query_number_tgt="⑱",
        reason=f"Table has {len(fk_cols)} FK column(s) — verify they are NOT NULL in both sides.",
        is_conditional=True,
    ))
```

### Change the AI model for recommendations

Set in `.env`:
```bash
DIAL_MODEL=gpt-4o          # use more powerful model for AI suggestions
```

Or pass directly:
```python
gen = DynamicSuiteGenerator(model="gpt-4o")
```

---

## 12. Test Coverage

All new code is covered by unit tests in `src/tests/`:

| Test file | What it tests |
|---|---|
| `test_schema_profiler.py` | Column group classification for all types and name patterns |
| `test_validation_rule_engine.py` | Which validations are triggered and which are not |
| `test_query_optimizer.py` | SQL structure, optimizer collapse, Fivetran filter |
| `test_suite_generator.py` | Full pipeline integration (no DB connection needed) |

**Run all tests:**
```powershell
cd src
python -m pytest tests/ -v
```

**Expected result:** 105 tests, all passing, in < 1 second (no database required).

---

## 13. Decision Matrix — What Triggers What

| Table characteristics | Triggered validations |
|---|---|
| Any table | ROW_COUNT, DATA_VALIDATION, NULL_PCT, DISTINCT_COUNT |
| Has any numeric column | + MIN_MAX |
| Has financial or quantity column | + SUM |
| Has NOT NULL identifier column | + DUPLICATE_CHECK |
| Has boolean or enum-like text column | + VALUE_DIST |
| DIAL_API_KEY set | + AI recommendations |

### Quick examples

**Simple dimension table (id, name, code, created_at):**
- ROW_COUNT, DATA_VALIDATION, NULL_PCT, DISTINCT_COUNT
- No SUM (no financial), no DUPLICATE (id is nullable or generic), no VALUE_DIST

**Orders table (order_id NOT NULL, amount numeric, quantity int, status varchar, is_active bool):**
- ROW_COUNT, DATA_VALIDATION, NULL_PCT, DISTINCT_COUNT  ← baseline
- MIN_MAX (amount, quantity)                            ← has numeric
- SUM (amount, quantity)                               ← financial + quantity
- DUPLICATE_CHECK (order_id)                           ← NOT NULL identifier
- VALUE_DIST (status, is_active)                       ← enum + boolean

**Log table (id, event_name text, metadata jsonb, created_at timestamp):**
- ROW_COUNT, DATA_VALIDATION, NULL_PCT, DISTINCT_COUNT  ← baseline
- metadata is SKIPPED (jsonb → cannot be compared)
- No SUM, no DUPLICATE (id might be nullable), no VALUE_DIST (event_name → TEXT_GENERIC not TEXT_ENUM)

---

*Last updated: 2026-08-10*
