# 07 — SQL and YAML Output

## Where Files Are Saved

All generated files go to:
```
src/validation_sql/<table>_validation.sql
src/validation_sql/<table>_validation.yaml
```

---

## Example: events Table

Assume we are validating `public.events` (PostgreSQL) → `storedge_fms_public.EVENTS` (Snowflake).

The table has columns: `id` (integer), `user_id` (integer), `event_name` (varchar), `amount` (numeric), `created_at` (timestamp), `is_active` (boolean), `metadata` (jsonb).

---

## SQL File: events_validation.sql

```sql
-- ============================================================
-- Migration Validation: public.events → storedge_fms_public.EVENTS
-- Generated: 2026-08-11T14:32:00
-- Model: gpt-4o
-- Columns mapped: 7  |  AI calls: 1  |  Fivetran active: true
-- ============================================================

-- [1] Row Count — PostgreSQL (Source)
SELECT COUNT(*) AS row_count
FROM public.events;

-- [2] Row Count — Snowflake (Target)
SELECT COUNT(*) AS row_count
FROM storedge_fms_public.EVENTS
WHERE _FIVETRAN_ACTIVE = TRUE;

-- [3] Main Validation SELECT — PostgreSQL
SELECT
  COALESCE(CAST(id AS TEXT), '<<NULL>>') AS id,
  COALESCE(CAST(user_id AS TEXT), '<<NULL>>') AS user_id,
  COALESCE(UPPER(TRIM(event_name::TEXT)), '<<NULL>>') AS event_name,
  COALESCE(CAST(ROUND(amount::numeric, 10) AS TEXT), '<<NULL>>') AS amount,
  COALESCE(TO_CHAR(created_at, 'YYYY-MM-DD"T"HH24:MI:SS.US'), '<<NULL>>') AS created_at,
  COALESCE(CASE WHEN is_active THEN 'TRUE' ELSE 'FALSE' END, '<<NULL>>') AS is_active,
  COALESCE(metadata::jsonb::TEXT, '<<NULL>>') AS metadata
FROM public.events
ORDER BY id;

-- [4] Main Validation SELECT — Snowflake
SELECT
  COALESCE(CAST(ID AS VARCHAR), '<<NULL>>') AS ID,
  COALESCE(CAST(USER_ID AS VARCHAR), '<<NULL>>') AS USER_ID,
  COALESCE(UPPER(TRIM(EVENT_NAME::VARCHAR)), '<<NULL>>') AS EVENT_NAME,
  COALESCE(CAST(ROUND(AMOUNT, 10) AS VARCHAR), '<<NULL>>') AS AMOUNT,
  COALESCE(TO_VARCHAR(CREATED_AT, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '<<NULL>>') AS CREATED_AT,
  COALESCE(CASE WHEN IS_ACTIVE = TRUE THEN 'TRUE' ELSE 'FALSE' END, '<<NULL>>') AS IS_ACTIVE,
  COALESCE(METADATA::VARCHAR, '<<NULL>>') AS METADATA
FROM storedge_fms_public.EVENTS
WHERE _FIVETRAN_ACTIVE = TRUE
ORDER BY ID;

-- [5] NULL % per Column — PostgreSQL
SELECT
  ROUND(100.0 * SUM(CASE WHEN id IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS id_null_pct,
  ROUND(100.0 * SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS user_id_null_pct,
  ROUND(100.0 * SUM(CASE WHEN event_name IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS event_name_null_pct,
  ROUND(100.0 * SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS amount_null_pct,
  ROUND(100.0 * SUM(CASE WHEN created_at IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS created_at_null_pct,
  ROUND(100.0 * SUM(CASE WHEN is_active IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS is_active_null_pct,
  ROUND(100.0 * SUM(CASE WHEN metadata IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS metadata_null_pct,
  COUNT(*) AS total_rows
FROM public.events;

-- [6] NULL % per Column — Snowflake
SELECT
  ROUND(100.0 * SUM(CASE WHEN ID IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS ID_null_pct,
  ROUND(100.0 * SUM(CASE WHEN USER_ID IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS USER_ID_null_pct,
  ROUND(100.0 * SUM(CASE WHEN EVENT_NAME IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS EVENT_NAME_null_pct,
  ROUND(100.0 * SUM(CASE WHEN AMOUNT IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS AMOUNT_null_pct,
  ROUND(100.0 * SUM(CASE WHEN CREATED_AT IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS CREATED_AT_null_pct,
  ROUND(100.0 * SUM(CASE WHEN IS_ACTIVE IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS IS_ACTIVE_null_pct,
  ROUND(100.0 * SUM(CASE WHEN METADATA IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS METADATA_null_pct,
  COUNT(*) AS total_rows
FROM storedge_fms_public.EVENTS
WHERE _FIVETRAN_ACTIVE = TRUE;

-- [7] Distinct Count — PostgreSQL
SELECT
  COUNT(DISTINCT id) AS id_distinct,
  COUNT(DISTINCT user_id) AS user_id_distinct,
  COUNT(DISTINCT event_name) AS event_name_distinct,
  COUNT(DISTINCT amount) AS amount_distinct,
  COUNT(DISTINCT created_at) AS created_at_distinct,
  COUNT(DISTINCT is_active) AS is_active_distinct,
  COUNT(DISTINCT metadata::jsonb) AS metadata_distinct
FROM public.events;

-- [8] Distinct Count — Snowflake
SELECT
  COUNT(DISTINCT ID) AS ID_distinct,
  COUNT(DISTINCT USER_ID) AS USER_ID_distinct,
  COUNT(DISTINCT EVENT_NAME) AS EVENT_NAME_distinct,
  COUNT(DISTINCT AMOUNT) AS AMOUNT_distinct,
  COUNT(DISTINCT CREATED_AT) AS CREATED_AT_distinct,
  COUNT(DISTINCT IS_ACTIVE) AS IS_ACTIVE_distinct,
  COUNT(DISTINCT METADATA) AS METADATA_distinct
FROM storedge_fms_public.EVENTS
WHERE _FIVETRAN_ACTIVE = TRUE;
```

---

## YAML File: events_validation.yaml

```yaml
# Migration Validation Configuration
# Source: public.events (PostgreSQL)
# Target: storedge_fms_public.EVENTS (Snowflake)
# Generated: 2026-08-11T14:32:00

table_pair:
  source:
    database: source_db
    schema: public
    table: events
  target:
    database: storedge_fms_public
    schema: public
    table: EVENTS
  fivetran_active_filter: true

validations:

  row_count_check:
    description: Compare total row counts between source and target
    source_sql: |
          SELECT COUNT(*) AS row_count
          FROM public.events
    target_sql: |
          SELECT COUNT(*) AS row_count
          FROM storedge_fms_public.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE
    expected: source_count == target_count

  data_completeness:
    description: Compare normalised column values row by row
    source_sql: |
          SELECT
            COALESCE(CAST(id AS TEXT), '<<NULL>>') AS id,
            COALESCE(CAST(user_id AS TEXT), '<<NULL>>') AS user_id,
            COALESCE(UPPER(TRIM(event_name::TEXT)), '<<NULL>>') AS event_name,
            COALESCE(CAST(ROUND(amount::numeric, 10) AS TEXT), '<<NULL>>') AS amount,
            COALESCE(TO_CHAR(created_at, 'YYYY-MM-DD"T"HH24:MI:SS.US'), '<<NULL>>') AS created_at,
            COALESCE(CASE WHEN is_active THEN 'TRUE' ELSE 'FALSE' END, '<<NULL>>') AS is_active,
            COALESCE(metadata::jsonb::TEXT, '<<NULL>>') AS metadata
          FROM public.events
          ORDER BY id
    target_sql: |
          SELECT
            COALESCE(CAST(ID AS VARCHAR), '<<NULL>>') AS ID,
            COALESCE(CAST(USER_ID AS VARCHAR), '<<NULL>>') AS USER_ID,
            COALESCE(UPPER(TRIM(EVENT_NAME::VARCHAR)), '<<NULL>>') AS EVENT_NAME,
            COALESCE(CAST(ROUND(AMOUNT, 10) AS VARCHAR), '<<NULL>>') AS AMOUNT,
            COALESCE(TO_VARCHAR(CREATED_AT, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '<<NULL>>') AS CREATED_AT,
            COALESCE(CASE WHEN IS_ACTIVE = TRUE THEN 'TRUE' ELSE 'FALSE' END, '<<NULL>>')
              AS IS_ACTIVE,
            COALESCE(METADATA::VARCHAR, '<<NULL>>') AS METADATA
          FROM storedge_fms_public.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE
          ORDER BY ID
    expected: all rows match after normalisation

  null_percentage:
    description: Compare NULL percentage per column
    source_sql: |
          SELECT
            ROUND(100.0 * SUM(CASE WHEN id IS NULL THEN 1 ELSE 0 END)
              / NULLIF(COUNT(*), 0), 4) AS id_null_pct,
            ROUND(100.0 * SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END)
              / NULLIF(COUNT(*), 0), 4) AS amount_null_pct,
            COUNT(*) AS total_rows
          FROM public.events
    target_sql: |
          SELECT
            ROUND(100.0 * SUM(CASE WHEN ID IS NULL THEN 1 ELSE 0 END)
              / NULLIF(COUNT(*), 0), 4) AS ID_null_pct,
            ROUND(100.0 * SUM(CASE WHEN AMOUNT IS NULL THEN 1 ELSE 0 END)
              / NULLIF(COUNT(*), 0), 4) AS AMOUNT_null_pct,
            COUNT(*) AS total_rows
          FROM storedge_fms_public.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE
    expected: null_pct diff per column <= 5%

  distinct_count:
    description: Compare distinct value counts per column
    source_sql: |
          SELECT
            COUNT(DISTINCT id) AS id_distinct,
            COUNT(DISTINCT event_name) AS event_name_distinct,
            COUNT(DISTINCT amount) AS amount_distinct
          FROM public.events
    target_sql: |
          SELECT
            COUNT(DISTINCT ID) AS ID_distinct,
            COUNT(DISTINCT EVENT_NAME) AS EVENT_NAME_distinct,
            COUNT(DISTINCT AMOUNT) AS AMOUNT_distinct
          FROM storedge_fms_public.EVENTS
          WHERE _FIVETRAN_ACTIVE = TRUE
    expected: distinct counts match within acceptable tolerance
```

---

## Dynamic Suite Output (Optional)

When `dynamic_suite/suite_generator.py` is used, a more comprehensive SQL file is produced that includes ALL aggregate checks in one combined SELECT:

```sql
-- SOURCE Combined Aggregates (one table scan)
SELECT
  COUNT(*) AS total_rows,

  -- NULL percentages
  ROUND(100.0 * SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4)
    AS amount_null_pct,
  ROUND(100.0 * SUM(CASE WHEN event_name IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4)
    AS event_name_null_pct,

  -- Distinct counts
  COUNT(DISTINCT amount) AS amount_distinct,
  COUNT(DISTINCT event_name) AS event_name_distinct,

  -- Min/Max (numeric columns)
  MIN(amount) AS amount_min,
  MAX(amount) AS amount_max,

  -- Sum (financial columns)
  SUM(amount) AS amount_sum

FROM public.events;
```

Instead of 5 separate queries (one scan each), this is ONE query that collects all metrics simultaneously. For a 100M row table, this saves 4 full table scans.

---

## How Column Mapping Appears in SQL

For a column mapped as `created_by` (PG) → `CREATED_BY_USER` (SF) with rule `text`:

```sql
-- PostgreSQL
COALESCE(UPPER(TRIM(created_by::TEXT)), '<<NULL>>') AS created_by

-- Snowflake
COALESCE(UPPER(TRIM(CREATED_BY_USER::VARCHAR)), '<<NULL>>') AS created_by
```

The alias uses the source column name in both, so the output columns can be compared directly.

---

## Verdict Display (Terminal Output)

When `query_executor.py` runs the queries, results are displayed like:

```
┌─────────────────────────────────────────────────────────────┐
│  ROW COUNT COMPARISON                                        │
│  PostgreSQL:  1,000,000                                      │
│  Snowflake:   1,000,000                                      │
│  Difference:  0 rows (0.00%)                                 │
│                                                              │
│  ✅ PASS                                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  NULL PERCENTAGE COMPARISON                                  │
│  Column             PG NULL%    SF NULL%    Diff    Status  │
│  amount             12.50%      12.50%      0.00%   PASS    │
│  event_name         0.00%       0.00%       0.00%   PASS    │
│  metadata           45.20%      47.80%      2.60%   WARN    │
└─────────────────────────────────────────────────────────────┘
```
