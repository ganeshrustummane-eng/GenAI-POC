-- =============================================================================
-- PostgreSQL Source Data — Migration Validator Test Dataset
-- =============================================================================
-- Table: public.migration_test
-- Purpose: Covers every validation rule type so every test case can be
--          verified manually after dumping this into PG and Snowflake.
--
-- Rules covered:
--   text          → VARCHAR / TEXT / CHARACTER VARYING
--   boolean       → BOOLEAN
--   integer       → SMALLINT / INTEGER / BIGINT / SERIAL
--   numeric       → NUMERIC / DECIMAL / FLOAT / DOUBLE PRECISION
--   date          → DATE
--   timestamp_ntz → TIMESTAMP WITHOUT TIME ZONE
--   timestamp_tz  → TIMESTAMP WITH TIME ZONE
--   uuid          → UUID
--   json          → JSON / JSONB
--   bytea         → BYTEA
--   hstore        → HSTORE  (requires hstore extension)
--   null_handling → NULL values in every column type
--
-- Row inventory (row_id: what it tests):
--   1  → Perfect match — all values identical on both sides
--   2  → Text whitespace — PG has leading/trailing spaces (should match SF after TRIM)
--   3  → Text case      — PG lowercase, SF uppercase (should match after LOWER/UPPER N/A — text rule does NOT case-fold, just trims; intentional mismatch row to CONFIRM validator catches it)
--   4  → Boolean TRUE
--   5  → Boolean FALSE
--   6  → Boolean NULL
--   7  → Integer values (SMALLINT / INT / BIGINT)
--   8  → Numeric precision — PG stores more decimal places than SF (rounds to 2dp)
--   9  → Numeric NULL
--   10 → Date standard
--   11 → Timestamp NTZ — PG has microseconds, SF truncated (should match at second level)
--   12 → Timestamp TZ  — PG +05:30, SF UTC (should match after UTC normalization)
--   13 → UUID lowercase PG vs uppercase SF
--   14 → JSON / JSONB — different key order (should match after canonical parse)
--   15 → BYTEA binary data
--   16 → HSTORE key-value data
--   17 → All NULLs row (every nullable column is NULL → all become '<<NULL>>')
--   18 → Empty string (text columns) — stays '' not converted to NULL
--   19 → INTENTIONAL MISMATCH — amount differs PG 100.00 vs SF 200.00 (validator should FAIL this)
--   20 → INTENTIONAL MISMATCH — boolean PG TRUE vs SF FALSE (validator should FAIL this)
-- =============================================================================

-- Enable hstore extension (run once per database)
CREATE EXTENSION IF NOT EXISTS hstore;

-- Drop and recreate clean
DROP TABLE IF EXISTS public.migration_test;

CREATE TABLE public.migration_test (
    row_id                  SERIAL          PRIMARY KEY,

    -- Text family
    col_varchar             VARCHAR(255),
    col_text                TEXT,
    col_char                CHAR(10),

    -- Boolean
    col_boolean             BOOLEAN,

    -- Integer family
    col_smallint            SMALLINT,
    col_integer             INTEGER,
    col_bigint              BIGINT,

    -- Numeric family
    col_numeric             NUMERIC(18, 6),
    col_decimal             DECIMAL(18, 4),
    col_float               DOUBLE PRECISION,

    -- Date / Time family
    col_date                DATE,
    col_timestamp_ntz       TIMESTAMP WITHOUT TIME ZONE,
    col_timestamp_tz        TIMESTAMP WITH TIME ZONE,

    -- UUID
    col_uuid                UUID,

    -- JSON
    col_json                JSON,
    col_jsonb               JSONB,

    -- Binary
    col_bytea               BYTEA,

    -- HStore
    col_hstore              HSTORE,

    -- Test label
    test_label              TEXT
);

-- =============================================================================
-- Row 1: Perfect match — values are identical on both systems
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar, col_text, col_char,
    col_boolean,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid,
    col_json, col_jsonb,
    col_bytea,
    col_hstore,
    test_label
) VALUES (
    'hello world',
    'this is a text column',
    'CHAR      ',          -- CHAR(10) padded
    TRUE,
    100,
    1000000,
    9999999999999,
    1234.567800,
    9876.5432,
    3.14159265,
    '2024-01-15',
    '2024-01-15 10:30:00',
    '2024-01-15 10:30:00+00',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    '{"name":"Alice","age":30}',
    '{"name":"Alice","age":30}',
    E'\\xDEADBEEF',
    '"key1"=>"value1","key2"=>"value2"',
    'TC-01: Perfect match'
);

-- =============================================================================
-- Row 2: Text whitespace — PG has spaces, SF will have trimmed version
--        TextRule applies TRIM on both sides → should MATCH
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar, col_text, col_char,
    col_boolean, col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    '  spaces around  ',
    '   leading and trailing   ',
    'PAD       ',
    FALSE,
    1, 1, 1,
    1.00, 1.00, 1.0,
    '2024-02-01',
    '2024-02-01 00:00:00',
    '2024-02-01 00:00:00+00',
    'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    '{"x":1}', '{"x":1}',
    E'\\x01',
    '"k"=>"v"',
    'TC-02: Whitespace trim (PG has spaces, SF clean) → MATCH after TRIM'
);

-- =============================================================================
-- Row 3: Text case difference — PG lowercase, SF stores same (text rule does NOT
--        case-fold — this is an INTENTIONAL MISMATCH to verify the validator
--        correctly FAILS when values differ after TRIM)
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar, col_text, col_char,
    col_boolean, col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'lowercase value',
    'another lowercase',
    'lower     ',
    TRUE,
    2, 2, 2,
    2.00, 2.00, 2.0,
    '2024-02-02',
    '2024-02-02 00:00:00',
    '2024-02-02 00:00:00+00',
    'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33',
    '{"y":2}', '{"y":2}',
    E'\\x02',
    '"k"=>"v2"',
    'TC-03: Text case mismatch (PG lower, SF UPPER in Snowflake setup) → FAIL expected'
);

-- =============================================================================
-- Row 4: Boolean TRUE
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar, col_boolean,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'bool_true', TRUE,
    3, 3, 3,
    3.00, 3.00, 3.0,
    '2024-03-01',
    '2024-03-01 06:00:00',
    '2024-03-01 06:00:00+00',
    'd3eebc99-9c0b-4ef8-bb6d-6bb9bd380a44',
    '{"b":true}', '{"b":true}',
    E'\\x03',
    '"bk"=>"bv"',
    'TC-04: Boolean TRUE → both become ''1'' → MATCH'
);

-- =============================================================================
-- Row 5: Boolean FALSE
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar, col_boolean,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'bool_false', FALSE,
    4, 4, 4,
    4.00, 4.00, 4.0,
    '2024-03-02',
    '2024-03-02 06:00:00',
    '2024-03-02 06:00:00+00',
    'e4eebc99-9c0b-4ef8-bb6d-6bb9bd380a55',
    '{"b":false}', '{"b":false}',
    E'\\x04',
    '"fk"=>"fv"',
    'TC-05: Boolean FALSE → both become ''0'' → MATCH'
);

-- =============================================================================
-- Row 6: Boolean NULL
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar, col_boolean,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'bool_null', NULL,
    5, 5, 5,
    5.00, 5.00, 5.0,
    '2024-03-03',
    '2024-03-03 06:00:00',
    '2024-03-03 06:00:00+00',
    'f5eebc99-9c0b-4ef8-bb6d-6bb9bd380a66',
    '{"c":null}', '{"c":null}',
    E'\\x05',
    '"nk"=>"nv"',
    'TC-06: Boolean NULL → both become ''<<NULL>>'' → MATCH'
);

-- =============================================================================
-- Row 7: Integer family — all sizes
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'integers',
    32767,              -- max SMALLINT
    2147483647,         -- max INTEGER
    9223372036854775807, -- max BIGINT
    100.00, 100.00, 100.0,
    '2024-04-01',
    '2024-04-01 12:00:00',
    '2024-04-01 12:00:00+00',
    'a6eebc99-9c0b-4ef8-bb6d-6bb9bd380a77',
    '{"n":7}', '{"n":7}',
    E'\\x07',
    '"ik"=>"iv"',
    'TC-07: Max integer values cast to text → MATCH'
);

-- =============================================================================
-- Row 8: Numeric precision — PG stores 6dp, SF stores 2dp
--        NumericRule rounds both to 2dp → should MATCH
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'numeric_precision',
    8, 8, 8,
    9999.999999,   -- 6dp in PG → rounds to 10000.00
    1234.5678,     -- 4dp in PG → rounds to 1234.57
    3.14159265,    -- many dp  → rounds to 3.14
    '2024-04-08',
    '2024-04-08 00:00:00',
    '2024-04-08 00:00:00+00',
    'a7eebc99-9c0b-4ef8-bb6d-6bb9bd380a88',
    '{"p":8}', '{"p":8}',
    E'\\x08',
    '"pk"=>"pv"',
    'TC-08: Numeric precision noise → MATCH after ROUND(x, 2)'
);

-- =============================================================================
-- Row 9: Numeric NULL
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'numeric_null',
    9, 9, 9,
    NULL, NULL, NULL,
    '2024-04-09',
    '2024-04-09 00:00:00',
    '2024-04-09 00:00:00+00',
    'a8eebc99-9c0b-4ef8-bb6d-6bb9bd380a99',
    '{"q":9}', '{"q":9}',
    E'\\x09',
    '"qk"=>"qv"',
    'TC-09: Numeric NULL → both become ''<<NULL>>'' → MATCH'
);

-- =============================================================================
-- Row 10: Date — standard date value
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'date_test',
    10, 10, 10,
    10.00, 10.00, 10.0,
    '2000-12-31',
    '2000-12-31 23:59:59',
    '2000-12-31 23:59:59+00',
    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380aaa',
    '{"d":10}', '{"d":10}',
    E'\\x0a',
    '"dk"=>"dv"',
    'TC-10: Date 2000-12-31 → formatted as YYYY-MM-DD → MATCH'
);

-- =============================================================================
-- Row 11: Timestamp NTZ with microseconds in PG, truncated in SF
--         TimestampNTZRule strips to second → should MATCH
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'ts_ntz_microseconds',
    11, 11, 11,
    11.00, 11.00, 11.0,
    '2024-06-15',
    '2024-06-15 08:45:30.123456',   -- PG has microseconds
    '2024-06-15 08:45:30+00',
    'c1eebc99-9c0b-4ef8-bb6d-6bb9bd380abb',
    '{"ts":11}', '{"ts":11}',
    E'\\x0b',
    '"tk"=>"tv"',
    'TC-11: Timestamp NTZ microseconds → stripped to second → MATCH'
);

-- =============================================================================
-- Row 12: Timestamp TZ — PG in +05:30, SF will store in UTC
--         Both normalized to UTC string → MATCH
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'ts_tz_offset',
    12, 12, 12,
    12.00, 12.00, 12.0,
    '2024-07-04',
    '2024-07-04 00:00:00',
    '2024-07-04 14:30:00+05:30',    -- IST → UTC = 09:00:00
    'd2eebc99-9c0b-4ef8-bb6d-6bb9bd380acc',
    '{"tz":12}', '{"tz":12}',
    E'\\x0c',
    '"zk"=>"zv"',
    'TC-12: Timestamp TZ +05:30 → UTC normalized → MATCH'
);

-- =============================================================================
-- Row 13: UUID — PG lowercase, SF uppercase
--         UUIDRule: UPPER(TRIM(CAST(... AS TEXT))) on both → MATCH
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'uuid_case',
    13, 13, 13,
    13.00, 13.00, 13.0,
    '2024-08-01',
    '2024-08-01 00:00:00',
    '2024-08-01 00:00:00+00',
    'e3eebc99-9c0b-4ef8-bb6d-6bb9bd380add',  -- PG stores lowercase
    '{"u":13}', '{"u":13}',
    E'\\x0d',
    '"uk"=>"uv"',
    'TC-13: UUID lowercase PG → UPPER on both sides → MATCH'
);

-- =============================================================================
-- Row 14: JSON / JSONB — different key ordering
--         JSONRule canonicalizes via jsonb::text → MATCH
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'json_key_order',
    14, 14, 14,
    14.00, 14.00, 14.0,
    '2024-08-14',
    '2024-08-14 00:00:00',
    '2024-08-14 00:00:00+00',
    'f4eebc99-9c0b-4ef8-bb6d-6bb9bd380aee',
    '{"b":2,"a":1}',          -- key order: b then a
    '{"z":26,"a":1,"m":13}',  -- different order
    E'\\x0e',
    '"jk"=>"jv"',
    'TC-14: JSON different key order → canonical parse → MATCH'
);

-- =============================================================================
-- Row 15: BYTEA binary data
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'bytea_test',
    15, 15, 15,
    15.00, 15.00, 15.0,
    '2024-09-01',
    '2024-09-01 00:00:00',
    '2024-09-01 00:00:00+00',
    'a5eebc99-9c0b-4ef8-bb6d-6bb9bd380aff',
    '{"by":15}', '{"by":15}',
    E'\\x48656c6c6f',    -- "Hello" in hex
    '"byk"=>"byv"',
    'TC-15: BYTEA → encode hex → both lower hex → MATCH'
);

-- =============================================================================
-- Row 16: HSTORE key-value
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'hstore_test',
    16, 16, 16,
    16.00, 16.00, 16.0,
    '2024-09-16',
    '2024-09-16 00:00:00',
    '2024-09-16 00:00:00+00',
    'b6eebc99-9c0b-4ef8-bb6d-6bb9bd380b00',
    '{"h":16}', '{"h":16}',
    E'\\x10',
    '"gate_code"=>"1234","move_date"=>"2024-09-16"',
    'TC-16: HSTORE → CAST to TEXT then TRIM (format differs from SF JSON text)'
);

-- =============================================================================
-- Row 17: All NULLs — every nullable column is NULL
--         All become '<<NULL>>' on both sides → MATCH
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar, col_text, col_char,
    col_boolean,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    NULL, NULL, NULL,
    NULL,
    NULL, NULL, NULL,
    NULL, NULL, NULL,
    NULL, NULL, NULL,
    NULL, NULL, NULL, NULL, NULL,
    'TC-17: All NULL → all become ''<<NULL>>'' → MATCH'
);

-- =============================================================================
-- Row 18: Empty string — text columns have ''
--         TextRule: TRIM('') = '' (stays empty, NOT converted to NULL)
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar, col_text, col_char,
    col_boolean,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    '', '', '          ',  -- CHAR(10) all spaces → TRIM = ''
    FALSE,
    18, 18, 18,
    18.00, 18.00, 18.0,
    '2024-10-18',
    '2024-10-18 00:00:00',
    '2024-10-18 00:00:00+00',
    'c7eebc99-9c0b-4ef8-bb6d-6bb9bd380b11',
    '{"e":18}', '{"e":18}',
    E'\\x12',
    '"ek"=>"ev"',
    'TC-18: Empty string stays '''' (not NULL) → MATCH'
);

-- =============================================================================
-- Row 19: INTENTIONAL MISMATCH — numeric amount differs
--         PG: col_numeric = 100.00  |  SF: col_numeric = 200.00
--         Validator should report FAIL for this row
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'mismatch_numeric',
    19, 19, 19,
    100.00,   -- PG value — SF will have 200.00 (see snowflake_setup.sql)
    100.00, 100.0,
    '2024-11-01',
    '2024-11-01 00:00:00',
    '2024-11-01 00:00:00+00',
    'd8eebc99-9c0b-4ef8-bb6d-6bb9bd380b22',
    '{"m":19}', '{"m":19}',
    E'\\x13',
    '"mk"=>"mv"',
    'TC-19: INTENTIONAL MISMATCH numeric → validator should FAIL'
);

-- =============================================================================
-- Row 20: INTENTIONAL MISMATCH — boolean differs
--         PG: TRUE  |  SF: FALSE
--         Validator should report FAIL for this row
-- =============================================================================
INSERT INTO public.migration_test (
    col_varchar, col_boolean,
    col_smallint, col_integer, col_bigint,
    col_numeric, col_decimal, col_float,
    col_date, col_timestamp_ntz, col_timestamp_tz,
    col_uuid, col_json, col_jsonb, col_bytea, col_hstore,
    test_label
) VALUES (
    'mismatch_boolean', TRUE,  -- PG: TRUE → SF will have FALSE
    20, 20, 20,
    20.00, 20.00, 20.0,
    '2024-11-20',
    '2024-11-20 00:00:00',
    '2024-11-20 00:00:00+00',
    'e9eebc99-9c0b-4ef8-bb6d-6bb9bd380b33',
    '{"bm":20}', '{"bm":20}',
    E'\\x14',
    '"bmk"=>"bmv"',
    'TC-20: INTENTIONAL MISMATCH boolean → validator should FAIL'
);

-- =============================================================================
-- Verification query — run after insert to confirm row count
-- =============================================================================
SELECT COUNT(*) AS total_rows FROM public.migration_test;
SELECT row_id, test_label FROM public.migration_test ORDER BY row_id;
