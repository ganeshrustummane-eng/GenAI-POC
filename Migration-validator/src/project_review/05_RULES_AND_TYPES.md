# 05 — Validation Rules and Type Handling

## What Are Validation Rules?

A validation rule defines how to normalise a column's value in both PostgreSQL and Snowflake so they can be compared as text strings. Without normalisation, the same data can look different:

| Value | PostgreSQL raw | Snowflake raw | After normalisation |
|-------|---------------|---------------|---------------------|
| true (boolean) | `t` | `1` | `'TRUE'` = `'TRUE'` ✓ |
| NULL | `NULL` | `NULL` | `'<<NULL>>'` = `'<<NULL>>'` ✓ |
| 3.14159 (numeric) | `3.14159000000` | `3.14159` | `'3.1415900000'` = `'3.1415900000'` ✓ |
| `2024-01-15 10:30:00` (timestamp) | `2024-01-15 10:30:00` | `2024-01-15 10:30:00.000` | ISO 8601 both sides ✓ |

---

## The NULL Sentinel

**Every rule** wraps its expression in:
```sql
-- PostgreSQL
COALESCE(CAST(<expression> AS TEXT), '<<NULL>>')

-- Snowflake
COALESCE(CAST(<expression> AS VARCHAR), '<<NULL>>')
```

This converts SQL NULL to the string `<<NULL>>`. Because text comparison is used (`WHERE pg_value = sf_value`), NULL = NULL works correctly. Without this, `NULL != NULL` always in SQL.

---

## All 11 Type Rules

### Rule 1: boolean

**Trigger:** PG `boolean` ↔ SF `BOOLEAN`, `NUMBER(1,0)`, `TINYINT`

**Problem:** PG stores booleans as `t`/`f`. Snowflake stores as `TRUE`/`FALSE` or `1`/`0`.

```sql
-- PostgreSQL
COALESCE(
  CASE WHEN col THEN 'TRUE' ELSE 'FALSE' END,
  '<<NULL>>'
)

-- Snowflake
COALESCE(
  CASE WHEN col = TRUE THEN 'TRUE' ELSE 'FALSE' END,
  '<<NULL>>'
)
```

---

### Rule 2: numeric

**Trigger:** PG `numeric`, `decimal`, `float`, `double precision`, `real` ↔ SF `NUMBER`, `FLOAT`, `DECIMAL`

**Problem:** Floating point precision differences between databases.

```sql
-- PostgreSQL
COALESCE(CAST(ROUND(col::numeric, 10) AS TEXT), '<<NULL>>')

-- Snowflake
COALESCE(CAST(ROUND(col, 10) AS VARCHAR), '<<NULL>>')
```

Rounds to 10 decimal places to eliminate floating-point noise while preserving enough precision.

---

### Rule 3: timestamp_ntz (Timestamp Without Time Zone)

**Trigger:** PG `timestamp without time zone`, `timestamp` ↔ SF `TIMESTAMP_NTZ`

**Problem:** Different default format strings.

```sql
-- PostgreSQL
COALESCE(TO_CHAR(col, 'YYYY-MM-DD"T"HH24:MI:SS.US'), '<<NULL>>')

-- Snowflake
COALESCE(TO_VARCHAR(col, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '<<NULL>>')
```

Both produce ISO 8601 format: `2024-01-15T10:30:00.000000`

---

### Rule 4: timestamp_tz (Timestamp With Time Zone)

**Trigger:** PG `timestamp with time zone`, `timestamptz` ↔ SF `TIMESTAMP_TZ`, `TIMESTAMP_LTZ`

**Problem:** Time zone storage differs. PG stores UTC internally; SF stores original tz offset.

```sql
-- PostgreSQL
COALESCE(TO_CHAR(col AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US+00:00'), '<<NULL>>')

-- Snowflake
COALESCE(TO_VARCHAR(CONVERT_TIMEZONE('UTC', col), 'YYYY-MM-DD"T"HH24:MI:SS.FF6+00:00'), '<<NULL>>')
```

Both convert to UTC first, then format identically.

---

### Rule 5: date

**Trigger:** PG `date` ↔ SF `DATE`

**Problem:** Different date display formats by locale/session.

```sql
-- PostgreSQL
COALESCE(TO_CHAR(col, 'YYYY-MM-DD'), '<<NULL>>')

-- Snowflake
COALESCE(TO_VARCHAR(col, 'YYYY-MM-DD'), '<<NULL>>')
```

---

### Rule 6: text (Catch-All)

**Trigger:** Any `character varying`, `varchar`, `char`, `text`, `nvarchar` ↔ SF `TEXT`, `VARCHAR`, `STRING`

**Problem:** Trailing spaces, case differences.

```sql
-- PostgreSQL
COALESCE(UPPER(TRIM(col::TEXT)), '<<NULL>>')

-- Snowflake
COALESCE(UPPER(TRIM(col::VARCHAR)), '<<NULL>>')
```

TRIM removes leading/trailing whitespace. UPPER makes comparison case-insensitive.

**Note:** This is the catch-all rule — registered last in the registry, so any type that doesn't match a more specific rule gets this one.

---

### Rule 7: uuid

**Trigger:** PG `uuid` ↔ SF `VARCHAR(36)`

**Problem:** PG returns UUIDs lowercase with hyphens; SF may return uppercase or without hyphens.

```sql
-- PostgreSQL
COALESCE(UPPER(col::TEXT), '<<NULL>>')

-- Snowflake
COALESCE(UPPER(col::VARCHAR), '<<NULL>>')
```

---

### Rule 8: integer

**Trigger:** PG `smallint`, `integer`, `int`, `bigint`, `serial`, `bigserial` ↔ SF `NUMBER`, `INTEGER`

**Problem:** SF NUMBER may have trailing `.0`; PG integers are plain numbers.

```sql
-- PostgreSQL
COALESCE(CAST(col AS TEXT), '<<NULL>>')

-- Snowflake
COALESCE(CAST(col AS VARCHAR), '<<NULL>>')
```

Note from code: a comment in `integer_rule.py` says `"# We dont hav cast to text or string (Conditional)"` — suggests conditional casting was considered but not implemented.

---

### Rule 9: json

**Trigger:** PG `json`, `jsonb` ↔ SF `VARIANT`, `OBJECT`, `ARRAY`

**Problem:** JSON key ordering may differ; SF VARIANT has its own serialization.

```sql
-- PostgreSQL
COALESCE(col::jsonb::TEXT, '<<NULL>>')

-- Snowflake
COALESCE(col::VARCHAR, '<<NULL>>')
```

**Limitation:** JSON key ordering is not guaranteed to be identical. This rule detects structural presence but not semantic equivalence. Columns using this rule are typically noted as "compared as text — ordering may differ."

---

### Rule 10: bytea

**Trigger:** PG `bytea` ↔ SF `BINARY`, `VARBINARY`

**Problem:** Binary data cannot be directly compared as text.

```sql
-- PostgreSQL
COALESCE(encode(col, 'hex'), '<<NULL>>')

-- Snowflake
COALESCE(HEX_ENCODE(col), '<<NULL>>')
```

Both encode to hex string for text comparison.

---

### Rule 11: hstore

**Trigger:** PG `hstore` (USER-DEFINED type) ↔ SF `VARCHAR`

**Problem:** `hstore` is a PostgreSQL-specific key-value type. Snowflake has no native equivalent.

```sql
-- PostgreSQL
COALESCE(col::TEXT, '<<NULL>>')

-- Snowflake
COALESCE(col::VARCHAR, '<<NULL>>')
```

**Bug fixed 2026-08-07:** Original code had `TRIM(col::TEXT)` which failed because `btrim(hstore)` does not exist in PostgreSQL. Fixed by removing the TRIM wrapper — only casting to TEXT.

---

## Rule Selection Priority

1. **Configured** — user explicitly set the rule in config
2. **Registry lookup** — `rules_catalog.json` trigger pairs matched by (source_type, target_type)
3. **AI selected** — for ambiguous columns, AI picks from the known rule IDs
4. **Text fallback** — if nothing else matches, TextRule applies TRIM + UPPER

---

## rules_catalog.json Structure

The machine-readable source for all rules:

```json
{
  "version": "3.0",
  "rules": [
    {
      "id": "boolean",
      "display_name": "Boolean Conversion",
      "description": "Normalise PostgreSQL boolean to TRUE/FALSE string",
      "trigger_type_pairs": [
        {"source_type": "boolean", "target_type": "BOOLEAN"},
        {"source_type": "boolean", "target_type": "NUMBER(1,0)"}
      ],
      "pg_sql_template": "COALESCE(CASE WHEN {col} THEN 'TRUE' ELSE 'FALSE' END, '<<NULL>>')",
      "sf_sql_template": "COALESCE(CASE WHEN {col} = TRUE THEN 'TRUE' ELSE 'FALSE' END, '<<NULL>>')",
      "auto_detect": true
    },
    ...
  ],
  "chaining_order": ["boolean", "numeric", "timestamp_tz", ...],
  "rule_application_order": ["boolean", "numeric", ...]
}
```

`{col}` is replaced with the actual column name at query generation time.

---

## Learned Rules (rule_book_learned.json)

Users can add custom rules via `validate_cli.py add-rule` command. Currently one entry:

```json
{
  "version": "1.0",
  "last_updated": "2026-08-10",
  "learned_rules": [
    {
      "id": "ex_strip",
      "display_name": "example_Strip",
      "description": "Example: check for negative amounts",
      "pg_sql_template": "{col}",
      "sf_sql_template": "{col}",
      "source_type": "*",
      "target_type": "*",
      "is_learned": true,
      "learned_at": "2026-08-10",
      "example": ""
    }
  ]
}
```

This is a test/placeholder entry. The `{col}` identity templates mean it applies no actual transformation. A real learned rule would have SQL expressions.

---

## Fivetran Filter (Not a Rule, But Auto-Applied)

When `_FIVETRAN_ACTIVE` column is detected in the Snowflake schema:

```sql
-- All Snowflake queries get this WHERE clause added automatically
WHERE _FIVETRAN_ACTIVE = TRUE
```

This filters out soft-deleted rows that Fivetran marks as inactive rather than deleting. Without this filter, row counts between PG and SF would differ by the number of deleted rows.
