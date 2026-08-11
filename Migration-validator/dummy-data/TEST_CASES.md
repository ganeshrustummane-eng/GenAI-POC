# Migration Validator — Test Cases Manual Verification Guide

## Overview

**Table:** `public.migration_test` (PostgreSQL) → `MIGRATION_TEST` (Snowflake)  
**Total rows:** 20  
**Match expected:** 15 rows PASS | 5 rows FAIL (intentional mismatches)

This document is your step-by-step checklist. For each test case:
- Load data using `postgres_setup.sql` and `snowflake_setup.sql`
- Run the validator against the table pair
- Execute the generated SQL on both databases
- Compare results manually using the expected outcomes below

---

## Setup Steps

```
1. Run postgres_setup.sql  → connects to your local/remote PostgreSQL
2. Run snowflake_setup.sql → connects to your Snowflake (replace <YOUR_DATABASE> and <YOUR_SCHEMA>)
3. Run the validator:
   python src/validation_pipeline.py \
       --pg-schema public \
       --pg-table migration_test \
       --sf-schema <YOUR_SCHEMA> \
       --sf-table MIGRATION_TEST \
       --sf-database <YOUR_DATABASE>
4. Open the generated .sql file in validation_sql/
5. Run the PG block in PostgreSQL, run the SF block in Snowflake
6. Compare row-by-row using the expected outcomes below
```

---

## Rule Reference

| Rule Name      | PG Type(s)                              | SF Type(s)              | Transformation Applied                        |
|----------------|-----------------------------------------|-------------------------|-----------------------------------------------|
| `text`         | VARCHAR, TEXT, CHAR, CHARACTER VARYING  | VARCHAR, TEXT, STRING   | TRIM(col) on both sides                       |
| `boolean`      | BOOLEAN, BOOL                           | BOOLEAN, BOOL           | TRUE→'1', FALSE→'0', NULL→'<<NULL>>'          |
| `integer`      | SMALLINT, INTEGER, BIGINT, SERIAL       | NUMBER, INTEGER         | CAST to TEXT                                  |
| `numeric`      | NUMERIC, DECIMAL, FLOAT, DOUBLE PREC   | NUMBER, FLOAT, DECIMAL  | ROUND(x, 2) then CAST to TEXT                 |
| `date`         | DATE                                    | DATE                    | TO_CHAR/TO_VARCHAR(col, 'YYYY-MM-DD')         |
| `timestamp_ntz`| TIMESTAMP WITHOUT TIME ZONE             | TIMESTAMP_NTZ           | TO_CHAR/TO_VARCHAR(col, 'YYYY-MM-DD HH24:MI:SS') — strips microseconds |
| `timestamp_tz` | TIMESTAMP WITH TIME ZONE                | TIMESTAMP_TZ            | Convert to UTC, then format 'YYYY-MM-DD HH24:MI:SS' |
| `uuid`         | UUID                                    | VARCHAR, STRING         | UPPER(TRIM(CAST(col AS TEXT)))                |
| `json`         | JSON, JSONB                             | VARIANT                 | PG: col::jsonb::text  /  SF: TO_JSON(PARSE_JSON(col)) |
| `bytea`        | BYTEA                                   | BINARY, VARBINARY       | PG: encode(col,'hex')  /  SF: LOWER(HEX_ENCODE(col)) |
| `hstore`       | HSTORE                                  | VARCHAR, TEXT           | PG: TRIM(CAST(col AS TEXT))  /  SF: TRIM(col) |
| `null_placeholder` | (all)                              | (all)                   | COALESCE(expr, '<<NULL>>') — wraps every rule |

---

## Test Cases

---

### TC-01: Perfect Match
**Row ID:** 1  
**Rule tested:** All rules (baseline)  
**What it tests:** Every column has identical values on both sides.  

| Column | PG Value | SF Value | Rule | Expected |
|--------|----------|----------|------|----------|
| col_varchar | 'hello world' | 'hello world' | text | MATCH |
| col_boolean | TRUE | TRUE | boolean | MATCH ('1' = '1') |
| col_integer | 1000000 | 1000000 | integer | MATCH |
| col_numeric | 1234.567800 | 1234.567800 | numeric | MATCH (both round to '1234.57') |
| col_date | 2024-01-15 | 2024-01-15 | date | MATCH |
| col_timestamp_ntz | 2024-01-15 10:30:00 | 2024-01-15 10:30:00 | timestamp_ntz | MATCH |
| col_timestamp_tz | 2024-01-15 10:30:00+00 | 2024-01-15 10:30:00+00 | timestamp_tz | MATCH |
| col_uuid | a0eebc99-... | A0EEBC99-... | uuid | MATCH (both → uppercase) |
| col_bytea | \xDEADBEEF | 0xDEADBEEF | bytea | MATCH (both → 'deadbeef') |

**Expected validator result:** PASS

---

### TC-02: Text Whitespace Trim
**Row ID:** 2  
**Rule tested:** `text`  
**What it tests:** PG has leading/trailing spaces. SF has clean values. TRIM on both sides eliminates the difference.  

| Column | PG Value | SF Value | After TRIM | Expected |
|--------|----------|----------|------------|----------|
| col_varchar | `'  spaces around  '` | `'spaces around'` | `'spaces around'` = `'spaces around'` | MATCH |
| col_text | `'   leading and trailing   '` | `'leading and trailing'` | `'leading and trailing'` = `'leading and trailing'` | MATCH |

**Manual SQL to verify (run on PG):**
```sql
SELECT TRIM(col_varchar) AS trimmed FROM public.migration_test WHERE row_id = 2;
-- Expected: 'spaces around'
```

**Expected validator result:** PASS

---

### TC-03: Text Case Mismatch (Intentional FAIL)
**Row ID:** 3  
**Rule tested:** `text`  
**What it tests:** TextRule does NOT case-fold — it only TRIMs. PG has lowercase, SF has uppercase. This should be caught as a mismatch.  

| Column | PG Value | SF Value | After TRIM | Expected |
|--------|----------|----------|------------|----------|
| col_varchar | `'lowercase value'` | `'LOWERCASE VALUE'` | `'lowercase value'` ≠ `'LOWERCASE VALUE'` | **FAIL** |
| col_text | `'another lowercase'` | `'ANOTHER LOWERCASE'` | mismatch | **FAIL** |

**Note:** If your migration uses case-insensitive comparison, you would need to apply LOWER()/UPPER() explicitly. The current TextRule does not do this — which is the intended design as per spec.

**Expected validator result:** FAIL (col_varchar and col_text mismatch)

---

### TC-04: Boolean TRUE
**Row ID:** 4  
**Rule tested:** `boolean`  
**What it tests:** TRUE on both sides normalizes to the string `'1'`.  

| Column | PG Value | SF Value | After Rule | Expected |
|--------|----------|----------|------------|----------|
| col_boolean | TRUE | TRUE | `'1'` = `'1'` | MATCH |

**Manual SQL to verify (run on PG):**
```sql
SELECT COALESCE(CAST(CASE WHEN col_boolean = true THEN '1' WHEN col_boolean = false THEN '0' ELSE NULL END AS TEXT), '<<NULL>>') 
FROM public.migration_test WHERE row_id = 4;
-- Expected: '1'
```

**Manual SQL to verify (run on SF):**
```sql
SELECT COALESCE(CAST(CASE WHEN COL_BOOLEAN = TRUE THEN '1' WHEN COL_BOOLEAN = FALSE THEN '0' ELSE NULL END AS STRING), '<<NULL>>')
FROM MIGRATION_TEST WHERE ROW_ID = 4 AND _FIVETRAN_ACTIVE = TRUE;
-- Expected: '1'
```

**Expected validator result:** PASS

---

### TC-05: Boolean FALSE
**Row ID:** 5  
**Rule tested:** `boolean`  
**What it tests:** FALSE on both sides normalizes to the string `'0'`.  

| Column | PG Value | SF Value | After Rule | Expected |
|--------|----------|----------|------------|----------|
| col_boolean | FALSE | FALSE | `'0'` = `'0'` | MATCH |

**Expected validator result:** PASS

---

### TC-06: Boolean NULL
**Row ID:** 6  
**Rule tested:** `boolean` + null_placeholder  
**What it tests:** NULL boolean on both sides → `'<<NULL>>'`.  

| Column | PG Value | SF Value | After Rule | Expected |
|--------|----------|----------|------------|----------|
| col_boolean | NULL | NULL | `'<<NULL>>'` = `'<<NULL>>'` | MATCH |

**Expected validator result:** PASS

---

### TC-07: Integer Max Values
**Row ID:** 7  
**Rule tested:** `integer`  
**What it tests:** Maximum values for SMALLINT (32767), INTEGER (2147483647), BIGINT (9223372036854775807) — all cast to text correctly.  

| Column | PG Value | After Rule | Expected |
|--------|----------|------------|----------|
| col_smallint | 32767 | `'32767'` | MATCH |
| col_integer | 2147483647 | `'2147483647'` | MATCH |
| col_bigint | 9223372036854775807 | `'9223372036854775807'` | MATCH |

**Expected validator result:** PASS

---

### TC-08: Numeric Precision Rounding
**Row ID:** 8  
**Rule tested:** `numeric`  
**What it tests:** PG stores more decimal places than SF. NumericRule rounds both to 2dp — eliminating ETL precision noise.  

| Column | PG Value | SF Value | After ROUND(x,2) | Expected |
|--------|----------|----------|-------------------|----------|
| col_numeric | 9999.999999 | 10000.00 | `'10000.00'` = `'10000.00'` | MATCH |
| col_decimal | 1234.5678 | 1234.57 | `'1234.57'` = `'1234.57'` | MATCH |
| col_float | 3.14159265 | 3.14 | `'3.14'` = `'3.14'` | MATCH |

**Manual SQL to verify (run on PG):**
```sql
SELECT 
    ROUND(CAST(col_numeric AS NUMERIC), 2) AS num,
    ROUND(CAST(col_decimal AS NUMERIC), 2) AS dec,
    ROUND(CAST(col_float   AS NUMERIC), 2) AS flt
FROM public.migration_test WHERE row_id = 8;
-- Expected: 10000.00 | 1234.57 | 3.14
```

**Expected validator result:** PASS

---

### TC-09: Numeric NULL
**Row ID:** 9  
**Rule tested:** `numeric` + null_placeholder  
**What it tests:** NULL numeric on both sides → `'<<NULL>>'`.  

| Column | PG Value | SF Value | After Rule | Expected |
|--------|----------|----------|------------|----------|
| col_numeric | NULL | NULL | `'<<NULL>>'` = `'<<NULL>>'` | MATCH |
| col_decimal | NULL | NULL | `'<<NULL>>'` = `'<<NULL>>'` | MATCH |
| col_float | NULL | NULL | `'<<NULL>>'` = `'<<NULL>>'` | MATCH |

**Expected validator result:** PASS

---

### TC-10: Date Formatting
**Row ID:** 10  
**Rule tested:** `date`  
**What it tests:** DATE on both sides formatted to 'YYYY-MM-DD' text for comparison.  

| Column | PG Value | SF Value | After Rule | Expected |
|--------|----------|----------|------------|----------|
| col_date | 2000-12-31 | 2000-12-31 | `'2000-12-31'` = `'2000-12-31'` | MATCH |

**Manual SQL (PG):**
```sql
SELECT TO_CHAR(col_date, 'YYYY-MM-DD') FROM public.migration_test WHERE row_id = 10;
-- Expected: '2000-12-31'
```

**Manual SQL (SF):**
```sql
SELECT TO_VARCHAR(COL_DATE, 'YYYY-MM-DD') FROM MIGRATION_TEST WHERE ROW_ID = 10 AND _FIVETRAN_ACTIVE = TRUE;
-- Expected: '2000-12-31'
```

**Expected validator result:** PASS

---

### TC-11: Timestamp NTZ — Microsecond Stripping
**Row ID:** 11  
**Rule tested:** `timestamp_ntz`  
**What it tests:** PG stores `2024-06-15 08:45:30.123456` (with microseconds). SF (Fivetran) truncated to `2024-06-15 08:45:30.000`. Both formatted to second-level precision → MATCH.  

| Column | PG Value | SF Value | After Rule | Expected |
|--------|----------|----------|------------|----------|
| col_timestamp_ntz | 2024-06-15 08:45:30.123456 | 2024-06-15 08:45:30.000 | `'2024-06-15 08:45:30'` = `'2024-06-15 08:45:30'` | MATCH |

**Manual SQL (PG):**
```sql
SELECT TO_CHAR(col_timestamp_ntz, 'YYYY-MM-DD HH24:MI:SS') FROM public.migration_test WHERE row_id = 11;
-- Expected: '2024-06-15 08:45:30'
```

**Manual SQL (SF):**
```sql
SELECT TO_VARCHAR(COL_TIMESTAMP_NTZ, 'YYYY-MM-DD HH24:MI:SS') FROM MIGRATION_TEST WHERE ROW_ID = 11 AND _FIVETRAN_ACTIVE = TRUE;
-- Expected: '2024-06-15 08:45:30'
```

**Expected validator result:** PASS

---

### TC-12: Timestamp TZ — Timezone UTC Normalization
**Row ID:** 12  
**Rule tested:** `timestamp_tz`  
**What it tests:** PG stored `2024-07-04 14:30:00+05:30` (IST). Fivetran migrated it as `2024-07-04 09:00:00+00` (UTC). Both sides normalize to UTC string → MATCH.  

| Column | PG Value | SF Value | After UTC normalize | Expected |
|--------|----------|----------|---------------------|----------|
| col_timestamp_tz | 2024-07-04 14:30:00+05:30 | 2024-07-04 09:00:00+00 | `'2024-07-04 09:00:00'` = `'2024-07-04 09:00:00'` | MATCH |

**Manual SQL (PG):**
```sql
SELECT TO_CHAR(col_timestamp_tz AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') 
FROM public.migration_test WHERE row_id = 12;
-- Expected: '2024-07-04 09:00:00'
```

**Manual SQL (SF):**
```sql
SELECT TO_VARCHAR(CONVERT_TIMEZONE('UTC', COL_TIMESTAMP_TZ), 'YYYY-MM-DD HH24:MI:SS')
FROM MIGRATION_TEST WHERE ROW_ID = 12 AND _FIVETRAN_ACTIVE = TRUE;
-- Expected: '2024-07-04 09:00:00'
```

**Expected validator result:** PASS

---

### TC-13: UUID Case Normalization
**Row ID:** 13  
**Rule tested:** `uuid`  
**What it tests:** PG stores UUID in lowercase. SF (Fivetran) stores it in uppercase. UUIDRule applies UPPER(TRIM(...)) on both sides → MATCH.  

| Column | PG Value | SF Value | After UPPER(TRIM) | Expected |
|--------|----------|----------|-------------------|----------|
| col_uuid | e3eebc99-9c0b-4ef8-bb6d-6bb9bd380add | E3EEBC99-9C0B-4EF8-BB6D-6BB9BD380ADD | `'E3EEBC99-...'` = `'E3EEBC99-...'` | MATCH |

**Manual SQL (PG):**
```sql
SELECT UPPER(TRIM(CAST(col_uuid AS TEXT))) FROM public.migration_test WHERE row_id = 13;
-- Expected: 'E3EEBC99-9C0B-4EF8-BB6D-6BB9BD380ADD'
```

**Expected validator result:** PASS

---

### TC-14: JSON Canonical Key Order
**Row ID:** 14  
**Rule tested:** `json`  
**What it tests:** PG stores JSON `{"b":2,"a":1}` (b first). PostgreSQL's `::jsonb` automatically sorts keys alphabetically → `{"a":1,"b":2}`. Snowflake's `TO_JSON(PARSE_JSON(...))` also sorts keys. Both sides produce the same canonical JSON string → MATCH.  

| Column | PG Value | SF Value | After canonical | Expected |
|--------|----------|----------|-----------------|----------|
| col_json | {"b":2,"a":1} | {"a":1,"b":2} | `'{"a":1,"b":2}'` = `'{"a":1,"b":2}'` | MATCH |
| col_jsonb | {"z":26,"a":1,"m":13} | {"a":1,"m":13,"z":26} | sorted → MATCH | MATCH |

**Manual SQL (PG):**
```sql
SELECT col_json::jsonb::text, col_jsonb::jsonb::text 
FROM public.migration_test WHERE row_id = 14;
-- Expected: '{"a":1,"b":2}' | '{"a":1,"m":13,"z":26}'
```

**Manual SQL (SF):**
```sql
SELECT TO_JSON(PARSE_JSON(CAST(COL_JSON AS STRING))),
       TO_JSON(PARSE_JSON(CAST(COL_JSONB AS STRING)))
FROM MIGRATION_TEST WHERE ROW_ID = 14 AND _FIVETRAN_ACTIVE = TRUE;
-- Expected: '{"a":1,"b":2}' | '{"a":1,"m":13,"z":26}'
```

**Expected validator result:** PASS

---

### TC-15: BYTEA / BINARY Hex Encoding
**Row ID:** 15  
**Rule tested:** `bytea`  
**What it tests:** PG BYTEA `\x48656c6c6f` ("Hello" bytes). ByteaRule on PG: `encode(col,'hex')` → `'48656c6c6f'`. On SF: `LOWER(HEX_ENCODE(col))` → `'48656c6c6f'`. MATCH.  

| Column | PG Value | SF Value | After hex encode | Expected |
|--------|----------|----------|------------------|----------|
| col_bytea | \x48656c6c6f | 0x48656c6c6f | `'48656c6c6f'` = `'48656c6c6f'` | MATCH |

**Manual SQL (PG):**
```sql
SELECT encode(col_bytea, 'hex') FROM public.migration_test WHERE row_id = 15;
-- Expected: '48656c6c6f'
```

**Manual SQL (SF):**
```sql
SELECT LOWER(HEX_ENCODE(COL_BYTEA)) FROM MIGRATION_TEST WHERE ROW_ID = 15 AND _FIVETRAN_ACTIVE = TRUE;
-- Expected: '48656c6c6f'
```

**Expected validator result:** PASS

---

### TC-16: HSTORE Format Difference (Known Limitation)
**Row ID:** 16  
**Rule tested:** `hstore`  
**What it tests:** PostgreSQL hstore format `"key"=>"value"` vs Snowflake JSON format `{"key":"value"}` (Fivetran conversion). HStoreRule only trims — it does NOT reformat. The raw text strings differ.  

| Column | PG Value (trimmed) | SF Value (trimmed) | Expected |
|--------|--------------------|--------------------|----------|
| col_hstore | `"gate_code"=>"1234","move_date"=>"2024-09-16"` | `{"gate_code":"1234","move_date":"2024-09-16"}` | **FAIL** (format differs) |

**This is a known limitation of the hstore rule.** The rule ensures SQL runs without errors (avoids `btrim(hstore)` type error) but cannot reconcile the format difference. Document this as a known mismatch and handle via:
- Custom comparison logic, OR
- `ignore_validation: true` for hstore columns in your YAML config

**Expected validator result:** FAIL (format mismatch — expected, documented)

---

### TC-17: All Columns NULL
**Row ID:** 17  
**Rule tested:** All rules + null_placeholder  
**What it tests:** Every nullable column is NULL on both sides. All normalize to `'<<NULL>>'`.  

| All columns | PG | SF | After COALESCE | Expected |
|-------------|----|----|----------------|----------|
| (all) | NULL | NULL | `'<<NULL>>'` = `'<<NULL>>'` | MATCH |

**Expected validator result:** PASS

---

### TC-18: Empty String vs NULL
**Row ID:** 18  
**Rule tested:** `text`  
**What it tests:** Empty string `''` is preserved as `''` — NOT converted to NULL. TRIM('') = ''. This confirms empty string ≠ NULL in the validation.  

| Column | PG Value | After TRIM | Expected |
|--------|----------|------------|----------|
| col_varchar | `''` | `''` | MATCH (both empty string) |
| col_char | `'          '` (10 spaces) | `''` | MATCH (TRIM collapses spaces) |

**Important:** `''` (empty string) ≠ `'<<NULL>>'`. If a column is NULL on one side and `''` on the other, it WILL be reported as a mismatch.

**Expected validator result:** PASS

---

### TC-19: Intentional Numeric Mismatch
**Row ID:** 19  
**Rule tested:** `numeric`  
**What it tests:** col_numeric is 100.00 on PG but 200.00 on SF. After ROUND(x,2): `'100.00'` ≠ `'200.00'`.  

| Column | PG Value | SF Value | After ROUND(2) | Expected |
|--------|----------|----------|----------------|----------|
| col_numeric | 100.00 | 200.00 | `'100.00'` ≠ `'200.00'` | **FAIL** |

**Expected validator result:** FAIL — this row must show up as a mismatch in the report.

---

### TC-20: Intentional Boolean Mismatch
**Row ID:** 20  
**Rule tested:** `boolean`  
**What it tests:** col_boolean is TRUE on PG but FALSE on SF. After rule: `'1'` ≠ `'0'`.  

| Column | PG Value | SF Value | After Rule | Expected |
|--------|----------|----------|------------|----------|
| col_boolean | TRUE | FALSE | `'1'` ≠ `'0'` | **FAIL** |

**Expected validator result:** FAIL — this row must show up as a mismatch in the report.

---

## Fivetran _FIVETRAN_ACTIVE Filter Test

All rows in Snowflake have `_FIVETRAN_ACTIVE = TRUE`. The validator detects this column and adds `WHERE _FIVETRAN_ACTIVE = TRUE` to all Snowflake queries automatically.

**To test the filter:**
1. Manually insert a duplicate row in Snowflake with `_FIVETRAN_ACTIVE = FALSE` for any row_id.
2. Re-run the validator.
3. Confirm the inactive row is ignored and the count still matches.

```sql
-- In Snowflake — add an inactive duplicate for row 1
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR, COL_BOOLEAN, _FIVETRAN_ACTIVE
) VALUES ('inactive duplicate', TRUE, FALSE);

-- The validator query will use WHERE _FIVETRAN_ACTIVE = TRUE
-- so this row must be invisible to validation queries
```

---

## Summary Table

| Row | Test Case | Rule(s) | Expected |
|-----|-----------|---------|----------|
| 1 | Perfect match — all types | All | PASS |
| 2 | Text whitespace TRIM | text | PASS |
| 3 | Text case mismatch | text | **FAIL** |
| 4 | Boolean TRUE | boolean | PASS |
| 5 | Boolean FALSE | boolean | PASS |
| 6 | Boolean NULL | boolean + null | PASS |
| 7 | Integer max values | integer | PASS |
| 8 | Numeric precision ROUND(2) | numeric | PASS |
| 9 | Numeric NULL | numeric + null | PASS |
| 10 | Date YYYY-MM-DD | date | PASS |
| 11 | Timestamp NTZ microseconds stripped | timestamp_ntz | PASS |
| 12 | Timestamp TZ UTC normalization | timestamp_tz | PASS |
| 13 | UUID case normalization | uuid | PASS |
| 14 | JSON canonical key order | json | PASS |
| 15 | BYTEA hex encoding | bytea | PASS |
| 16 | HSTORE format difference | hstore | **FAIL** (known limitation) |
| 17 | All NULLs → `<<NULL>>` | null_placeholder | PASS |
| 18 | Empty string stays empty | text | PASS |
| 19 | Numeric value mismatch (100 vs 200) | numeric | **FAIL** |
| 20 | Boolean mismatch (TRUE vs FALSE) | boolean | **FAIL** |

**PASS expected: 16 rows | FAIL expected: 4 rows**

---

## Row Count Check

Run this on both sides before column comparison:

**PostgreSQL:**
```sql
SELECT COUNT(*) FROM public.migration_test;
-- Expected: 20
```

**Snowflake:**
```sql
SELECT COUNT(*) FROM MIGRATION_TEST WHERE _FIVETRAN_ACTIVE = TRUE;
-- Expected: 20
```

If counts differ, the migration itself is incomplete — investigate before column-level validation.

---

## Column Mapping Expected by Validator

The validator should auto-map these column pairs (exact match, case-insensitive):

| PostgreSQL Column | Snowflake Column | Rule Applied |
|-------------------|------------------|--------------|
| row_id | ROW_ID | integer |
| col_varchar | COL_VARCHAR | text |
| col_text | COL_TEXT | text |
| col_char | COL_CHAR | text |
| col_boolean | COL_BOOLEAN | boolean |
| col_smallint | COL_SMALLINT | integer |
| col_integer | COL_INTEGER | integer |
| col_bigint | COL_BIGINT | integer |
| col_numeric | COL_NUMERIC | numeric |
| col_decimal | COL_DECIMAL | numeric |
| col_float | COL_FLOAT | numeric |
| col_date | COL_DATE | date |
| col_timestamp_ntz | COL_TIMESTAMP_NTZ | timestamp_ntz |
| col_timestamp_tz | COL_TIMESTAMP_TZ | timestamp_tz |
| col_uuid | COL_UUID | uuid |
| col_json | COL_JSON | json |
| col_jsonb | COL_JSONB | json |
| col_bytea | COL_BYTEA | bytea |
| col_hstore | COL_HSTORE | hstore |
| test_label | TEST_LABEL | text |
| _(none)_ | _FIVETRAN_ACTIVE | _(Fivetran marker — filtered, not compared)_ |
