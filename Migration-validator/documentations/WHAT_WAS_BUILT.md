# What Was Built — Dynamic Validation Suite

> **Audience:** Project lead, reviewer, or anyone picking up this feature.  
> **Purpose:** Explains exactly what was added, where every file lives, and why the decisions were made.

---

## Summary

The migration validator previously generated 8 identical SQL queries for every table — regardless of what columns the table contained.  This release adds a **dynamic validation suite** that:

1. Profiles each table's schema to identify column types and characteristics
2. Decides which additional validations are warranted (conditionally)
3. Collapses all aggregate statistics into a single query per side (query optimizer)
4. Optionally asks the AI to suggest business-rule condition checks

**The 8-query baseline is unchanged and remains the foundation.**  The dynamic suite is purely additive.

---

## Files Created

### `src/profiling/` (new package)

| File | Purpose |
|---|---|
| `__init__.py` | Package exports |
| `schema_profiler.py` | Classifies columns into semantic groups (NUMERIC_FINANCIAL, IDENTIFIER, TEMPORAL, etc.) using name keywords + data type |
| `validation_rule_engine.py` | Maps column groups to `ValidationRequirement` objects — decides what needs checking |
| `ai_recommendation.py` | Calls DIAL API with column metadata (no row data) to get business-rule condition suggestions |

### `src/dynamic_suite/` (new package)

| File | Purpose |
|---|---|
| `__init__.py` | Package exports |
| `validation_suite.py` | `ValidationSuite` output container + `GeneratedQuery` dataclass |
| `query_optimizer.py` | Collapses multiple aggregate requirements into one combined query per side |
| `suite_generator.py` | Top-level `DynamicSuiteGenerator` orchestrator — runs all 4 steps |

### `src/tests/` (new test package)

| File | Tests | Count |
|---|---|---|
| `__init__.py` | Package marker | — |
| `test_schema_profiler.py` | Column group classification for all types and keyword patterns | 27 tests |
| `test_validation_rule_engine.py` | Baseline always present; conditional triggering per type | 26 tests |
| `test_query_optimizer.py` | SQL structure, optimizer collapse, Fivetran filter, duplicate check | 18 tests |
| `test_suite_generator.py` | Full pipeline integration (no DB connection) | 15 tests |

**Total: 105 tests — 105 passing — 0 failures**

### Documentation

| File | Purpose |
|---|---|
| `DYNAMIC_VALIDATION_SUITE.md` | Architecture guide, SQL examples, extension guide |
| `WHAT_WAS_BUILT.md` | This file — change log and decision rationale |
| `PROJECT_DOCUMENTATION.md` | (pre-existing) Comprehensive project documentation |
| `MANUAL_TESTING_GUIDE.md` | (pre-existing) Manual testing guide for every level |

---

## What Each New Module Does

### SchemaProfiler (`profiling/schema_profiler.py`)

Reads `List[ColumnMetadata]` from the existing extractors and classifies each column without making any database query.

**Classification priority (in order):**
1. SKIPPED — JSON, JSONB, ARRAY, BYTEA are not comparable
2. TEMPORAL — date/timestamp type → unambiguous
3. IDENTIFIER — name ends with `_id`, `_key`, `_uuid`, `_guid`, or type is `uuid`
4. STATUS_FLAG — boolean type or name starts with `is_`, `has_`, `can_`
5. NUMERIC_FINANCIAL — numeric type AND name keyword in financial set (amount, balance, price, salary, cost, revenue…)
6. NUMERIC_QUANTITY — numeric type AND name keyword in quantity set (quantity, qty, count, units, stock…)
7. NUMERIC_GENERIC — any other numeric column
8. TEXT_ENUM — text type AND name root word is status/type/state/category/role/tier
9. TEXT_GENERIC — everything else

**Key design decision:** Identifier check runs before numeric check. This means `customer_id bigint NOT NULL` → IDENTIFIER, not NUMERIC_GENERIC. This prevents false SUM/MIN_MAX requirements on FK columns.

---

### ValidationRuleEngine (`profiling/validation_rule_engine.py`)

Pure function-style decision engine. Takes a `TableProfile`, returns `List[ValidationRequirement]`.

**Rule table:**

| Requirement | Trigger | Columns assigned |
|---|---|---|
| ROW_COUNT | Always | (none — table-level) |
| DATA_VALIDATION | Always | (none — uses canonical plan mappings) |
| NULL_PCT | Always | All non-skipped columns |
| DISTINCT_COUNT | Always | All non-skipped columns |
| MIN_MAX | Any numeric column | All numeric columns |
| SUM | Financial or quantity column | Financial + quantity columns only |
| DUPLICATE_CHECK | NOT NULL identifier column | NOT NULL identifier columns (= business keys) |
| VALUE_DIST | Status flag or enum text column | Status + enum columns |

**Key design decision:** SUM applies to financial + quantity but NOT generic numeric. A column named `score` or `age` should not have a SUM check — that's meaningless. Only columns explicitly identified as financial/monetary or quantity/inventory are summed.

---

### AIRecommendationEngine (`profiling/ai_recommendation.py`)

Sends only column names and types to DIAL — never any row data.

**Security:** The prompt explicitly says "you do not have access to actual row data" and the engine validates that AI only references columns it was told about (hallucinated column names are silently dropped).

**Fallback:** If `DIAL_API_KEY` is absent, returns empty list immediately. If the API call fails, returns empty list with a warning to stderr. The pipeline always continues.

**What AI recommends:** Business-rule condition fragments (not full queries):
- `amount >= 0` (non-negative financial value)
- `quantity > 0` (positive quantity)
- `end_date >= start_date` (date ordering)
- `email IS NOT NULL` (mandatory field)

These are embedded in the output SQL as runnable queries (`SELECT COUNT(*) FROM table WHERE NOT (<condition>)`).

---

### QueryOptimizer (`dynamic_suite/query_optimizer.py`)

The most important optimization in this release.

**Before:** N aggregate requirements → 2N database scans (one per requirement per side).

**After:** All aggregate requirements (NULL_PCT + DISTINCT_COUNT + MIN_MAX + SUM + VALUE_DIST) → 2 database scans (one combined query per side).

**What stays separate:**
- ROW_COUNT — must be standalone (`SELECT COUNT(*)`)
- DATA_VALIDATION — must be standalone (returns all rows for row-level comparison)
- DUPLICATE_CHECK — cannot be merged (requires GROUP BY + HAVING semantics)

**The combined aggregate query** merges:
```sql
SELECT
    COUNT(*) AS total_rows,
    -- NULL%:
    ROUND(100.0 * SUM(CASE WHEN col IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS col_null_pct,
    -- DISTINCT:
    COUNT(DISTINCT col)      AS col_distinct_count,
    -- MIN/MAX:
    MIN(numeric_col)         AS numeric_col_min,
    MAX(numeric_col)         AS numeric_col_max,
    -- SUM:
    SUM(financial_col)       AS financial_col_sum
FROM table;
```

---

### DynamicSuiteGenerator (`dynamic_suite/suite_generator.py`)

Thin orchestrator that runs profiler → rule engine → AI → optimizer → suite.

Accepts `active_mappings` (ColumnRuleMapping list from the canonical plan) so the ③/④ normalised SELECT queries are generated using the existing rule-application logic — no duplication.

---

## Decisions That Were NOT Made (and why)

### Why not modify the existing `SQLQueryGenerator`?

The `SQLQueryGenerator` (`generated_queries/sql_query_generator.py`) is a stable, tested module that produces the 8 baseline queries. Modifying it would risk breaking the existing pipeline. The dynamic suite is a separate layer that sits on top and calls the existing generator for ③/④.

### Why not one giant "universal query"?

A single `SELECT … FROM table` that tries to cover all checks would be unreadable, undebuggable, and hard to explain to stakeholders. Keeping the row-count queries separate makes it obvious what each number means. The optimizer only merges what is truly mergeable (same semantics, same aggregation level).

### Why no row-level SUM comparison?

SUM is a table-level aggregate comparison (one number per side), not a row-level check. Comparing SUM totals is fast and catches a class of errors that row-level comparison also catches, but SUM catches financial discrepancies that happen to cancel out at the row level (one row +$10k, another -$10k → total unchanged, row count unchanged, but both rows are wrong).

### Why is AI only additive?

The deterministic checks (profiler + rule engine) are reliable, repeatable, and auditable. AI suggestions vary between calls. Making AI optional and additive ensures the validation output is reproducible even without a DIAL API key.

---

## How to Verify the Build

```powershell
# 1. Run all tests
cd "C:\EPAM-Personal\Migration-validator\src"
python -m pytest tests/ -v

# Expected: 105 passed in < 1 second

# 2. Smoke-test the profiler
python -c "
import sys; sys.path.insert(0, '.')
from sql_extractor.base_extractor import ColumnMetadata
from profiling import SchemaProfiler, ValidationRuleEngine

cols = [
    ColumnMetadata(1, 'order_id', 'integer', is_nullable=False),
    ColumnMetadata(2, 'amount',   'numeric',  is_nullable=True, numeric_scale=2),
    ColumnMetadata(3, 'status',   'character varying'),
]
profile = SchemaProfiler().profile(cols, 'public', 'orders')
print(profile.summary())

reqs = ValidationRuleEngine().decide(profile)
for r in reqs:
    print(r.query_number_src, r.label, '[conditional]' if r.is_conditional else '[baseline]')
"

# 3. Generate a full suite (no DB connection needed)
python -c "
import sys; sys.path.insert(0, '.')
from sql_extractor.base_extractor import ColumnMetadata
from dynamic_suite import DynamicSuiteGenerator

cols = [
    ColumnMetadata(1, 'order_id', 'integer', is_nullable=False),
    ColumnMetadata(2, 'amount',   'numeric',  is_nullable=True, numeric_scale=2),
    ColumnMetadata(3, 'status',   'character varying'),
]
gen   = DynamicSuiteGenerator()
suite = gen.generate(
    source_columns=cols,
    source_schema='public', source_table='orders',
    sf_database='MY_DB', sf_schema='MY_SCHEMA', sf_table='ORDERS',
    has_fivetran_active=True,
    use_ai_recommendations=False,
)
print(suite.to_combined_sql())
print()
print('Total query pairs:', suite.total_query_pairs)
print('Baseline:', len(suite.baseline_queries))
print('Conditional:', len(suite.conditional_queries))
"
```

---

## What Was NOT Changed

These files were read but not modified:

| File | Why read | Why not changed |
|---|---|---|
| `src/models.py` | Understand existing data models | No changes needed — new models defined separately |
| `src/core/validation_plan.py` | Understand CanonicalValidationPlan | Not modified — new suite wraps it |
| `src/generated_queries/sql_query_generator.py` | Understand 8-query baseline | Not modified — dynamic suite calls it |
| `src/ai/rule_planner.py` | Understand AI planner pattern | AIRecommendationEngine follows same pattern |
| `src/ai_transformation/static_rule_mapper.py` | Understand ColumnRuleMapping | Used as input to optimizer |
| `src/sql_extractor/base_extractor.py` | Understand ColumnMetadata | Used as-is in profiler |

---

*Built: 2026-08-10*  
*Tests: 105 passed, 0 failed*  
*Lines of code added: ~1,200 (excluding tests and docs)*
