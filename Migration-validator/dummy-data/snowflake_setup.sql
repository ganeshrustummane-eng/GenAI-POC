-- =============================================================================
-- Snowflake Target Data — Migration Validator Test Dataset
-- =============================================================================
-- Table: <YOUR_DATABASE>.<YOUR_SCHEMA>.MIGRATION_TEST
--
-- Replace <YOUR_DATABASE> and <YOUR_SCHEMA> with your actual values.
-- Recommended: use the same database/schema as your .env SNOWFLAKE_DATABASE
-- and SNOWFLAKE_SCHEMA variables.
--
-- This table mirrors public.migration_test in PostgreSQL with Snowflake types.
-- Includes _FIVETRAN_ACTIVE column (the Fivetran soft-delete marker).
--
-- Key differences from PostgreSQL:
--   • TIMESTAMP WITHOUT TIME ZONE → TIMESTAMP_NTZ(9)
--   • TIMESTAMP WITH TIME ZONE   → TIMESTAMP_TZ(9)
--   • UUID (native)              → VARCHAR(36)
--   • JSON / JSONB               → VARIANT
--   • BYTEA                      → BINARY
--   • HSTORE                     → VARCHAR (JSON-like string)
--   • SERIAL (auto-increment)    → NUMBER with AUTOINCREMENT
--   • _FIVETRAN_ACTIVE BOOLEAN   → Fivetran active-record marker
--
-- Row-by-row design mirrors postgres_setup.sql.
-- Rows 19 and 20 have intentional data mismatches to verify FAIL detection.
-- =============================================================================



-- Drop and recreate
DROP TABLE IF EXISTS MIGRATION_TEST;

CREATE TABLE MIGRATION_TEST (
    ROW_ID                  NUMBER          AUTOINCREMENT PRIMARY KEY,

    -- Text family
    COL_VARCHAR             VARCHAR(255),
    COL_TEXT                TEXT,
    COL_CHAR                CHAR(10),

    -- Boolean
    COL_BOOLEAN             BOOLEAN,

    -- Integer family
    COL_SMALLINT            NUMBER(5),
    COL_INTEGER             NUMBER(10),
    COL_BIGINT              NUMBER(19),

    -- Numeric family
    COL_NUMERIC             NUMBER(18, 6),
    COL_DECIMAL             NUMBER(18, 4),
    COL_FLOAT               FLOAT,

    -- Date / Time family
    COL_DATE                DATE,
    COL_TIMESTAMP_NTZ       TIMESTAMP_NTZ(9),
    COL_TIMESTAMP_TZ        TIMESTAMP_TZ(9),

    -- UUID (stored as VARCHAR in Snowflake)
    COL_UUID                VARCHAR(36),

    -- JSON (stored as VARIANT in Snowflake)
    COL_JSON                VARIANT,
    COL_JSONB               VARIANT,

    -- Binary
    COL_BYTEA               BINARY,

    -- HStore (Fivetran converts to JSON-like VARCHAR)
    COL_HSTORE              VARCHAR,

    -- Test label
    TEST_LABEL              VARCHAR,

    -- Fivetran active marker (set TRUE for all rows — no soft-deletes in test)
    _FIVETRAN_ACTIVE        BOOLEAN DEFAULT TRUE
);

-- =============================================================================
-- Row 1: Perfect match
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR, COL_TEXT, COL_CHAR,
    COL_BOOLEAN,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB,
    COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) SELECT
    'hello world',
    'this is a text column',
    'CHAR      ',
    TRUE,
    100, 1000000, 9999999999999,
    1234.567800, 9876.5432, 3.14159265,
    '2024-01-15',
    '2024-01-15 10:30:00'::TIMESTAMP_NTZ,
    '2024-01-15 10:30:00 +0000'::TIMESTAMP_TZ,
    'A0EEBC99-9C0B-4EF8-BB6D-6BB9BD380A11',
    PARSE_JSON('{"name":"Alice","age":30}'),
    PARSE_JSON('{"name":"Alice","age":30}'),
    TO_BINARY('DEADBEEF', 'HEX'),
    '{"key1":"value1","key2":"value2"}',
    'TC-01: Perfect match',
    TRUE;

-- =============================================================================
-- Row 2: Whitespace trim — SF has no extra spaces (PG had spaces)
--        After TRIM on both sides → MATCH
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR, COL_TEXT, COL_CHAR,
    COL_BOOLEAN, COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'spaces around',          -- no spaces (PG had '  spaces around  ')
    'leading and trailing',   -- no spaces (PG had '   leading and trailing   ')
    'PAD       ',
    FALSE,
    1, 1, 1,
    1.00, 1.00, 1.0,
    '2024-02-01',
    '2024-02-01 00:00:00'::TIMESTAMP_NTZ,
    '2024-02-01 00:00:00 +0000'::TIMESTAMP_TZ,
    'B1EEBC99-9C0B-4EF8-BB6D-6BB9BD380A22',
    PARSE_JSON('{"x":1}'), PARSE_JSON('{"x":1}'),
    TO_BINARY('01', 'HEX'),
    '{"k":"v"}',
    'TC-02: Whitespace trim → MATCH',
    TRUE
);

-- =============================================================================
-- Row 3: INTENTIONAL MISMATCH — text case
--        PG: 'lowercase value'  |  SF: 'LOWERCASE VALUE'
--        TextRule does NOT case-fold → validator should FAIL
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR, COL_TEXT, COL_CHAR,
    COL_BOOLEAN, COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'LOWERCASE VALUE',        -- UPPERCASE on SF side (PG is lowercase) → MISMATCH
    'ANOTHER LOWERCASE',      -- UPPERCASE on SF side → MISMATCH
    'LOWER     ',
    TRUE,
    2, 2, 2,
    2.00, 2.00, 2.0,
    '2024-02-02',
    '2024-02-02 00:00:00'::TIMESTAMP_NTZ,
    '2024-02-02 00:00:00 +0000'::TIMESTAMP_TZ,
    'C2EEBC99-9C0B-4EF8-BB6D-6BB9BD380A33',
    PARSE_JSON('{"y":2}'), PARSE_JSON('{"y":2}'),
    TO_BINARY('02', 'HEX'),
    '{"k":"v2"}',
    'TC-03: Text case mismatch → FAIL expected',
    TRUE
);

-- =============================================================================
-- Row 4: Boolean TRUE
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR, COL_BOOLEAN,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'bool_true', TRUE,
    3, 3, 3,
    3.00, 3.00, 3.0,
    '2024-03-01',
    '2024-03-01 06:00:00'::TIMESTAMP_NTZ,
    '2024-03-01 06:00:00 +0000'::TIMESTAMP_TZ,
    'D3EEBC99-9C0B-4EF8-BB6D-6BB9BD380A44',
    PARSE_JSON('{"b":true}'), PARSE_JSON('{"b":true}'),
    TO_BINARY('03', 'HEX'),
    '{"bk":"bv"}',
    'TC-04: Boolean TRUE → ''1'' → MATCH',
    TRUE
);

-- =============================================================================
-- Row 5: Boolean FALSE
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR, COL_BOOLEAN,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'bool_false', FALSE,
    4, 4, 4,
    4.00, 4.00, 4.0,
    '2024-03-02',
    '2024-03-02 06:00:00'::TIMESTAMP_NTZ,
    '2024-03-02 06:00:00 +0000'::TIMESTAMP_TZ,
    'E4EEBC99-9C0B-4EF8-BB6D-6BB9BD380A55',
    PARSE_JSON('{"b":false}'), PARSE_JSON('{"b":false}'),
    TO_BINARY('04', 'HEX'),
    '{"fk":"fv"}',
    'TC-05: Boolean FALSE → ''0'' → MATCH',
    TRUE
);

-- =============================================================================
-- Row 6: Boolean NULL
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR, COL_BOOLEAN,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'bool_null', NULL,
    5, 5, 5,
    5.00, 5.00, 5.0,
    '2024-03-03',
    '2024-03-03 06:00:00'::TIMESTAMP_NTZ,
    '2024-03-03 06:00:00 +0000'::TIMESTAMP_TZ,
    'F5EEBC99-9C0B-4EF8-BB6D-6BB9BD380A66',
    PARSE_JSON('{"c":null}'), PARSE_JSON('{"c":null}'),
    TO_BINARY('05', 'HEX'),
    '{"nk":"nv"}',
    'TC-06: Boolean NULL → ''<<NULL>>'' → MATCH',
    TRUE
);

-- =============================================================================
-- Row 7: Integer family — max values
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'integers',
    32767, 2147483647, 9223372036854775807,
    100.00, 100.00, 100.0,
    '2024-04-01',
    '2024-04-01 12:00:00'::TIMESTAMP_NTZ,
    '2024-04-01 12:00:00 +0000'::TIMESTAMP_TZ,
    'A6EEBC99-9C0B-4EF8-BB6D-6BB9BD380A77',
    PARSE_JSON('{"n":7}'), PARSE_JSON('{"n":7}'),
    TO_BINARY('07', 'HEX'),
    '{"ik":"iv"}',
    'TC-07: Max integer values → MATCH',
    TRUE
);

-- =============================================================================
-- Row 8: Numeric precision — SF stores 2dp (PG had more)
--        After ROUND(x, 2) on both sides → MATCH
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'numeric_precision',
    8, 8, 8,
    10000.00,   -- Fivetran rounded 9999.999999 → 10000.00
    1234.57,    -- Fivetran rounded 1234.5678  → 1234.57
    3.14,       -- Fivetran rounded 3.14159265 → 3.14
    '2024-04-08',
    '2024-04-08 00:00:00'::TIMESTAMP_NTZ,
    '2024-04-08 00:00:00 +0000'::TIMESTAMP_TZ,
    'A7EEBC99-9C0B-4EF8-BB6D-6BB9BD380A88',
    PARSE_JSON('{"p":8}'), PARSE_JSON('{"p":8}'),
    TO_BINARY('08', 'HEX'),
    '{"pk":"pv"}',
    'TC-08: Numeric precision → ROUND(2) → MATCH',
    TRUE
);

-- =============================================================================
-- Row 9: Numeric NULL
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'numeric_null',
    9, 9, 9,
    NULL, NULL, NULL,
    '2024-04-09',
    '2024-04-09 00:00:00'::TIMESTAMP_NTZ,
    '2024-04-09 00:00:00 +0000'::TIMESTAMP_TZ,
    'A8EEBC99-9C0B-4EF8-BB6D-6BB9BD380A99',
    PARSE_JSON('{"q":9}'), PARSE_JSON('{"q":9}'),
    TO_BINARY('09', 'HEX'),
    '{"qk":"qv"}',
    'TC-09: Numeric NULL → ''<<NULL>>'' → MATCH',
    TRUE
);

-- =============================================================================
-- Row 10: Date
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'date_test',
    10, 10, 10,
    10.00, 10.00, 10.0,
    '2000-12-31',
    '2000-12-31 23:59:59'::TIMESTAMP_NTZ,
    '2000-12-31 23:59:59 +0000'::TIMESTAMP_TZ,
    'B0EEBC99-9C0B-4EF8-BB6D-6BB9BD380AAA',
    PARSE_JSON('{"d":10}'), PARSE_JSON('{"d":10}'),
    TO_BINARY('0a', 'HEX'),
    '{"dk":"dv"}',
    'TC-10: Date YYYY-MM-DD → MATCH',
    TRUE
);

-- =============================================================================
-- Row 11: Timestamp NTZ — SF has no microseconds (PG had .123456)
--         After TO_VARCHAR/TO_CHAR stripping to second → MATCH
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'ts_ntz_microseconds',
    11, 11, 11,
    11.00, 11.00, 11.0,
    '2024-06-15',
    '2024-06-15 08:45:30.000'::TIMESTAMP_NTZ,  -- Fivetran truncated microseconds
    '2024-06-15 08:45:30 +0000'::TIMESTAMP_TZ,
    'C1EEBC99-9C0B-4EF8-BB6D-6BB9BD380ABB',
    PARSE_JSON('{"ts":11}'), PARSE_JSON('{"ts":11}'),
    TO_BINARY('0b', 'HEX'),
    '{"tk":"tv"}',
    'TC-11: Timestamp NTZ microseconds stripped → MATCH',
    TRUE
);

-- =============================================================================
-- Row 12: Timestamp TZ — SF stores in UTC (PG was +05:30 = 14:30 IST = 09:00 UTC)
--         Both sides normalize to UTC string → MATCH
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'ts_tz_offset',
    12, 12, 12,
    12.00, 12.00, 12.0,
    '2024-07-04',
    '2024-07-04 00:00:00'::TIMESTAMP_NTZ,
    '2024-07-04 09:00:00 +0000'::TIMESTAMP_TZ,  -- Fivetran stored as UTC (14:30 IST → 09:00 UTC)
    'D2EEBC99-9C0B-4EF8-BB6D-6BB9BD380ACC',
    PARSE_JSON('{"tz":12}'), PARSE_JSON('{"tz":12}'),
    TO_BINARY('0c', 'HEX'),
    '{"zk":"zv"}',
    'TC-12: Timestamp TZ +05:30 → UTC 09:00 → MATCH',
    TRUE
);

-- =============================================================================
-- Row 13: UUID — SF stores UPPERCASE (PG stores lowercase)
--         UUIDRule: UPPER(TRIM(CAST(... AS TEXT/STRING))) on both → MATCH
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'uuid_case',
    13, 13, 13,
    13.00, 13.00, 13.0,
    '2024-08-01',
    '2024-08-01 00:00:00'::TIMESTAMP_NTZ,
    '2024-08-01 00:00:00 +0000'::TIMESTAMP_TZ,
    'E3EEBC99-9C0B-4EF8-BB6D-6BB9BD380ADD',  -- UPPERCASE in SF (PG had lowercase)
    PARSE_JSON('{"u":13}'), PARSE_JSON('{"u":13}'),
    TO_BINARY('0d', 'HEX'),
    '{"uk":"uv"}',
    'TC-13: UUID case norm → UPPER both → MATCH',
    TRUE
);

-- =============================================================================
-- Row 14: JSON different key order — Snowflake VARIANT canonicalizes on read
--         Both side: TO_JSON(PARSE_JSON(...)) / ::jsonb::text → MATCH
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'json_key_order',
    14, 14, 14,
    14.00, 14.00, 14.0,
    '2024-08-14',
    '2024-08-14 00:00:00'::TIMESTAMP_NTZ,
    '2024-08-14 00:00:00 +0000'::TIMESTAMP_TZ,
    'F4EEBC99-9C0B-4EF8-BB6D-6BB9BD380AEE',
    PARSE_JSON('{"a":1,"b":2}'),          -- SF key order: a then b (PG had b then a — jsonb sorts)
    PARSE_JSON('{"a":1,"m":13,"z":26}'),  -- SF sorted (PG had z,a,m)
    TO_BINARY('0e', 'HEX'),
    '{"jk":"jv"}',
    'TC-14: JSON key order canonical → MATCH',
    TRUE
);

-- =============================================================================
-- Row 15: BYTEA / BINARY
--         PG: encode(col, 'hex') → '48656c6c6f'
--         SF: LOWER(HEX_ENCODE(col)) → '48656c6c6f'
--         → MATCH
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'bytea_test',
    15, 15, 15,
    15.00, 15.00, 15.0,
    '2024-09-01',
    '2024-09-01 00:00:00'::TIMESTAMP_NTZ,
    '2024-09-01 00:00:00 +0000'::TIMESTAMP_TZ,
    'A5EEBC99-9C0B-4EF8-BB6D-6BB9BD380AFF',
    PARSE_JSON('{"by":15}'), PARSE_JSON('{"by":15}'),
    TO_BINARY('48656c6c6f', 'HEX'),   -- "Hello" in binary
    '{"byk":"byv"}',
    'TC-15: BYTEA → hex → MATCH',
    TRUE
);

-- =============================================================================
-- Row 16: HSTORE → Fivetran converts to JSON-like VARCHAR on SF
--         Note: PG format ("k"=>"v") ≠ SF format ({"k":"v"})
--         HStoreRule trims both but does NOT reformat — expect FAIL in practice
--         This row is documented as an "informational" case
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'hstore_test',
    16, 16, 16,
    16.00, 16.00, 16.0,
    '2024-09-16',
    '2024-09-16 00:00:00'::TIMESTAMP_NTZ,
    '2024-09-16 00:00:00 +0000'::TIMESTAMP_TZ,
    'B6EEBC99-9C0B-4EF8-BB6D-6BB9BD380B00',
    PARSE_JSON('{"h":16}'), PARSE_JSON('{"h":16}'),
    TO_BINARY('10', 'HEX'),
    -- Fivetran JSON format (differs from PG hstore "key"=>"value" format)
    '{"gate_code":"1234","move_date":"2024-09-16"}',
    'TC-16: HSTORE format differs PG vs SF → known mismatch (hstore rule limitation)',
    TRUE
);

-- =============================================================================
-- Row 17: All NULLs
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR, COL_TEXT, COL_CHAR,
    COL_BOOLEAN,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    NULL, NULL, NULL,
    NULL,
    NULL, NULL, NULL,
    NULL, NULL, NULL,
    NULL, NULL, NULL,
    NULL, NULL, NULL, NULL, NULL,
    'TC-17: All NULL → ''<<NULL>>'' → MATCH',
    TRUE
);

-- =============================================================================
-- Row 18: Empty string
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR, COL_TEXT, COL_CHAR,
    COL_BOOLEAN,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    '', '', '          ',
    FALSE,
    18, 18, 18,
    18.00, 18.00, 18.0,
    '2024-10-18',
    '2024-10-18 00:00:00'::TIMESTAMP_NTZ,
    '2024-10-18 00:00:00 +0000'::TIMESTAMP_TZ,
    'C7EEBC99-9C0B-4EF8-BB6D-6BB9BD380B11',
    PARSE_JSON('{"e":18}'), PARSE_JSON('{"e":18}'),
    TO_BINARY('12', 'HEX'),
    '{"ek":"ev"}',
    'TC-18: Empty string stays empty → MATCH',
    TRUE
);

-- =============================================================================
-- Row 19: INTENTIONAL MISMATCH — col_numeric 200.00 (PG has 100.00)
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'mismatch_numeric',
    19, 19, 19,
    200.00,   -- MISMATCH: PG has 100.00, SF has 200.00
    100.00, 100.0,
    '2024-11-01',
    '2024-11-01 00:00:00'::TIMESTAMP_NTZ,
    '2024-11-01 00:00:00 +0000'::TIMESTAMP_TZ,
    'D8EEBC99-9C0B-4EF8-BB6D-6BB9BD380B22',
    PARSE_JSON('{"m":19}'), PARSE_JSON('{"m":19}'),
    TO_BINARY('13', 'HEX'),
    '{"mk":"mv"}',
    'TC-19: INTENTIONAL MISMATCH numeric → FAIL expected',
    TRUE
);

-- =============================================================================
-- Row 20: INTENTIONAL MISMATCH — boolean FALSE (PG has TRUE)
-- =============================================================================
INSERT INTO MIGRATION_TEST (
    COL_VARCHAR, COL_BOOLEAN,
    COL_SMALLINT, COL_INTEGER, COL_BIGINT,
    COL_NUMERIC, COL_DECIMAL, COL_FLOAT,
    COL_DATE, COL_TIMESTAMP_NTZ, COL_TIMESTAMP_TZ,
    COL_UUID, COL_JSON, COL_JSONB, COL_BYTEA, COL_HSTORE,
    TEST_LABEL, _FIVETRAN_ACTIVE
) VALUES (
    'mismatch_boolean', FALSE,  -- MISMATCH: PG has TRUE, SF has FALSE
    20, 20, 20,
    20.00, 20.00, 20.0,
    '2024-11-20',
    '2024-11-20 00:00:00'::TIMESTAMP_NTZ,
    '2024-11-20 00:00:00 +0000'::TIMESTAMP_TZ,
    'E9EEBC99-9C0B-4EF8-BB6D-6BB9BD380B33',
    PARSE_JSON('{"bm":20}'), PARSE_JSON('{"bm":20}'),
    TO_BINARY('14', 'HEX'),
    '{"bmk":"bmv"}',
    'TC-20: INTENTIONAL MISMATCH boolean → FAIL expected',
    TRUE
);

-- =============================================================================
-- Verification
-- =============================================================================
SELECT COUNT(*) AS total_rows FROM MIGRATION_TEST WHERE _FIVETRAN_ACTIVE = TRUE;
SELECT ROW_ID, TEST_LABEL FROM MIGRATION_TEST WHERE _FIVETRAN_ACTIVE = TRUE ORDER BY ROW_ID;
