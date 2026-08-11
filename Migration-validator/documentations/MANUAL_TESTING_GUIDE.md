# Migration Validator — Manual Testing Guide

> **Who this is for:** QA engineers, data engineers, and developers who need to manually test and verify every level of the Migration Validator system.  
> **Goal:** Step-by-step instructions to test at every layer — from the database connection to the final YAML output — with explicit commands, expected outputs, and what to do when something fails.

---

## Table of Contents

1. [Pre-Test Checklist](#1-pre-test-checklist)
2. [Level 1: Environment Setup Test](#2-level-1-environment-setup-test)
3. [Level 2: Database Connection Test](#3-level-2-database-connection-test)
4. [Level 3: Schema Extraction Test](#4-level-3-schema-extraction-test)
5. [Level 4: Column Matching Test](#5-level-4-column-matching-test)
6. [Level 5: AI Integration Test](#6-level-5-ai-integration-test)
7. [Level 6: Rule Book Test](#7-level-6-rule-book-test)
8. [Level 7: SQL Query Generation Test](#8-level-7-sql-query-generation-test)
9. [Level 8: YAML Output Validation Test](#9-level-8-yaml-output-validation-test)
10. [Level 9: SQL Execution Test (Run Queries Manually)](#10-level-9-sql-execution-test-run-queries-manually)
11. [Level 10: End-to-End Full Pipeline Test](#11-level-10-end-to-end-full-pipeline-test)
12. [Level 11: Report Generation Test](#12-level-11-report-generation-test)
13. [Validation Decision Matrix](#13-validation-decision-matrix)
14. [Interpreting Results — Pass / Fail / Partial](#14-interpreting-results--pass--fail--partial)
15. [Test Data Setup (Local PostgreSQL)](#15-test-data-setup-local-postgresql)

---

## 1. Pre-Test Checklist

Before running any test, confirm the following:

```
[ ] Python 3.9 or newer installed
[ ] .env file created with correct credentials
[ ] EPAM VPN connected (for Snowflake and DIAL API)
[ ] Docker Desktop running (for local PostgreSQL)
[ ] virtual environment activated OR packages installed globally
```

### Activate the virtual environment

```powershell
# From project root
cd C:\EPAM-Personal\Migration-validator
.\.venv\Scripts\Activate.ps1

# Verify python is from venv
python --version
# Expected: Python 3.x.x
```

### Install packages (first time only)

```powershell
pip install psycopg2-binary snowflake-connector-python python-dotenv rapidfuzz pyyaml
```

---

## 2. Level 1: Environment Setup Test

**Goal:** Verify the project directory is correct and all key files exist.

### Test 1.1 — Project structure check

```powershell
cd C:\EPAM-Personal\Migration-validator

# Check key files exist
Test-Path ".env"                                     # Must be True
Test-Path "src\validate_cli.py"                      # Must be True
Test-Path "src\validation_pipeline.py"               # Must be True
Test-Path "src\rule_book.py"                         # Must be True
Test-Path "src\rules_catalog.json"                   # Must be True
Test-Path "src\generated_queries\sql_query_generator.py"  # Must be True
Test-Path "src\generated_queries\yaml_config_writer.py"   # Must be True
```

**Expected:** All return `True`  
**If False:** The repository is incomplete. Re-clone or check the working directory.

---

### Test 1.2 — .env file has required keys

```powershell
# Read .env and check required keys
$env_content = Get-Content .env -Raw

@("SOURCE_HOST", "SOURCE_DATABASE", "SOURCE_USERNAME", "SOURCE_PASSWORD",
  "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
  "SNOWFLAKE_USERNAME", "SNOWFLAKE_PASSWORD") | ForEach-Object {
    if ($env_content -match $_) {
        Write-Host "  OK: $_" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $_" -ForegroundColor Red
    }
}
```

**Expected:** All keys show `OK`  
**If missing:** Edit `.env` and add the missing key with its value.

---

### Test 1.3 — Python imports work

```powershell
cd src
python -c "
import yaml
import psycopg2
import snowflake.connector
from dotenv import load_dotenv
print('All imports OK')
"
```

**Expected output:**
```
All imports OK
```

**If import fails:** Run `pip install <package-name>` for the missing module.

---

## 3. Level 2: Database Connection Test

**Goal:** Verify connectivity to PostgreSQL and Snowflake.

### Test 2.1 — PostgreSQL connection

```powershell
cd C:\EPAM-Personal\Migration-validator\src
python check_connections.py
```

**Expected output contains:**
```
  ✓ PostgreSQL connected
  ✓ Tables found: X
```

**If fails:**
```
  ✗ PostgreSQL connection failed: ...
```

**Diagnosis steps:**
```powershell
# Option A: Test with psql directly
psql -h localhost -p 5432 -U postgres -d your_db -c "SELECT 1;"

# Option B: Test with Python directly
python -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv('../.env')
conn = psycopg2.connect(
    host=os.getenv('SOURCE_HOST','localhost'),
    port=int(os.getenv('SOURCE_PORT','5432')),
    database=os.getenv('SOURCE_DATABASE'),
    user=os.getenv('SOURCE_USERNAME'),
    password=os.getenv('SOURCE_PASSWORD')
)
print('Connected! Server version:', conn.server_version)
conn.close()
"
```

---

### Test 2.2 — Snowflake connection

```powershell
python -c "
import snowflake.connector, os
from dotenv import load_dotenv
load_dotenv('../.env')
conn = snowflake.connector.connect(
    account=os.getenv('SNOWFLAKE_ACCOUNT'),
    database=os.getenv('SNOWFLAKE_DATABASE'),
    schema=os.getenv('SNOWFLAKE_SCHEMA'),
    user=os.getenv('SNOWFLAKE_USERNAME'),
    password=os.getenv('SNOWFLAKE_PASSWORD')
)
cur = conn.cursor()
cur.execute('SELECT CURRENT_VERSION()')
print('Snowflake connected! Version:', cur.fetchone()[0])
cur.close()
conn.close()
"
```

**Expected output:**
```
Snowflake connected! Version: 8.x.x
```

**Common errors:**

| Error | Fix |
|---|---|
| `250001 (08001): Failed to connect` | Check VPN is on; check SNOWFLAKE_ACCOUNT format (no `.snowflakecomputing.com`) |
| `251005: User does not exist` | Verify SNOWFLAKE_USERNAME |
| `390100: Incorrect username or password` | Verify SNOWFLAKE_PASSWORD |
| `390189: The requested warehouse is not found` | Set SNOWFLAKE_WAREHOUSE in .env |

---

### Test 2.3 — Local Docker PostgreSQL (if using Docker)

```powershell
# Start local test database
cd C:\EPAM-Personal\Migration-validator
docker-compose up -d

# Wait 10 seconds for health check, then verify
docker ps
# Expected: migration_validator_source_db  Up (healthy)

# Connect directly
psql -h localhost -p 5432 -U admin -d source_db -c "SELECT COUNT(*) FROM source_data.users;"
# Expected: count = 10 (sample data seeded)
```

---

## 4. Level 3: Schema Extraction Test

**Goal:** Verify that the schema extractor correctly reads column metadata from both databases.

### Test 3.1 — PostgreSQL schema extraction

```powershell
cd C:\EPAM-Personal\Migration-validator\src

python -c "
from dotenv import load_dotenv; load_dotenv('../.env')
from sql_extractor import PostgresExtractor

extractor = PostgresExtractor()

# Replace 'your_schema' and 'your_table' with actual values
columns = extractor.extract_columns('public', 'events')

print(f'Found {len(columns)} columns:')
for col in columns:
    print(f'  {col.column_name:<30} {col.data_type}')
"
```

**Expected output (varies by table):**
```
Found 12 columns:
  event_id                       integer
  event_name                     character varying
  is_active                      boolean
  created_at                     timestamp without time zone
  ...
```

**What to verify:**
- Column count matches what you see in the actual table (`\d tablename` in psql)
- Data types are PostgreSQL native types (lowercase)
- No columns are missing

---

### Test 3.2 — Snowflake schema extraction

```powershell
python -c "
from dotenv import load_dotenv; load_dotenv('../.env')
from sql_extractor import SnowflakeExtractor

extractor = SnowflakeExtractor()

# Replace with actual values
columns = extractor.extract_columns('YOUR_SCHEMA', 'EVENTS')

print(f'Found {len(columns)} columns:')
for col in columns:
    print(f'  {col.column_name:<30} {col.data_type}')
"
```

**Expected output:**
```
Found 12 columns:
  EVENT_ID                       NUMBER
  EVENT_NAME                     TEXT
  IS_ACTIVE                      BOOLEAN
  CREATED_AT                     TIMESTAMP_NTZ
  _FIVETRAN_ACTIVE               BOOLEAN
  ...
```

**What to verify:**
- Column names are UPPERCASE (standard Snowflake behavior)
- `_FIVETRAN_ACTIVE` is detected if present
- Data types are Snowflake types (UPPERCASE)

---

### Test 3.3 — List available tables

```powershell
python validate_cli.py list-tables
```

**Expected output:**
```
  PostgreSQL — your_db.public
    • events
    • users
    • orders
    ...

  Snowflake — YOUR_DB.YOUR_SCHEMA
    • EVENTS
    • USERS
    • ORDERS
    ...
```

**If a table you expect is missing:** Check user permissions — the extractor queries `information_schema.tables` and only returns tables the user has SELECT access to.

---

## 5. Level 4: Column Matching Test

**Goal:** Verify that source columns are correctly matched to target columns, and verify confidence scores.

### Test 4.1 — Exact matching

This is tested implicitly when you run the generate command. To inspect matching behavior:

```powershell
python -c "
from dotenv import load_dotenv; load_dotenv('../.env')
from sql_extractor import PostgresExtractor, SnowflakeExtractor
from matching.candidate_matcher import CandidateMatcher

pg = PostgresExtractor()
sf = SnowflakeExtractor()

src_cols = pg.extract_columns('public', 'events')
tgt_cols = sf.extract_columns('YOUR_SCHEMA', 'EVENTS')

matcher = CandidateMatcher()
decisions = matcher.match(src_cols, tgt_cols)

for d in decisions:
    status = 'EXACT' if d.method == 'exact' else 'FUZZY' if d.method == 'fuzzy' else 'SKIP'
    score = f'score={d.final_score:.2f}' if d.final_score else ''
    tgt = d.target_col.column_name if d.target_col else 'UNMATCHED'
    print(f'  {d.source_col.column_name:<30} → {tgt:<30} [{status}] {score}')
"
```

**Expected output:**
```
  event_id                       → EVENT_ID                       [EXACT] score=1.00
  event_name                     → EVENT_NAME                     [EXACT] score=1.00
  is_active                      → IS_ACTIVE                      [EXACT] score=1.00
  reg_date                       → REGISTRATION_DATE              [FUZZY] score=0.82
  ...
```

**What to verify:**
- Most columns match as EXACT (score=1.00)
- Renamed columns are caught as FUZZY with reasonable scores
- Unexpected columns show UNMATCHED (these need investigation)

---

### Test 4.2 — Check for unmatched columns

```powershell
python -c "
from dotenv import load_dotenv; load_dotenv('../.env')
from sql_extractor import PostgresExtractor, SnowflakeExtractor
from matching.candidate_matcher import CandidateMatcher

pg = PostgresExtractor()
sf = SnowflakeExtractor()

src_cols = pg.extract_columns('public', 'events')
tgt_cols = sf.extract_columns('YOUR_SCHEMA', 'EVENTS')

matcher = CandidateMatcher()
decisions = matcher.match(src_cols, tgt_cols)

unmatched = [d for d in decisions if d.skip_validation and not d.source_col.column_name.startswith('_')]
if unmatched:
    print('UNMATCHED SOURCE COLUMNS (not in Snowflake):')
    for d in unmatched:
        print(f'  ✗ {d.source_col.column_name}  ({d.source_col.data_type})')
else:
    print('All source columns matched.')
"
```

**Expected:** Either `All source columns matched.` or a list of legitimately dropped columns.

**If a column is unexpectedly unmatched:**
1. Check if the column exists in Snowflake by a different name
2. Add a learned rule to teach the matcher: `python validate_cli.py add-rule`
3. Or use `--explicit-mappings` flag (if using `run_with_plan`)

---

## 6. Level 5: AI Integration Test

**Goal:** Verify that the DIAL API is reachable and the configured model responds.

### Test 5.1 — Check which models are available

```powershell
cd C:\EPAM-Personal\Migration-validator\src
python validate_cli.py list-models
```

**Expected output (with DIAL key set):**
```
  DIAL API Key  : ✓ ACTIVE
  Current model : gpt-4o-mini

  Probing API to find working models...
  ✓ 2 working model(s) on your key

  #    Provider     Model ID                              Display Name      Description
  ──────────────────────────────────────────────────────────────────────────────
  1    OpenAI       gpt-4o-mini                           GPT-4o Mini       ...   ← active
  2    OpenAI       gpt-4o                                GPT-4o            ...
```

**If DIAL_API_KEY is not set:**
```
  DIAL API Key  : ✗ NOT CONFIGURED
```

**Action:** Add `DIAL_API_KEY=your_key` to `.env`, then reconnect VPN.

---

### Test 5.2 — Quick AI connectivity test

```powershell
python -c "
from dotenv import load_dotenv; load_dotenv('../.env')
import os
import urllib.request, json

api_key = os.getenv('DIAL_API_KEY', '')
api_base = os.getenv('DIAL_API_BASE', 'https://ai-proxy.lab.epam.com')
api_version = os.getenv('DIAL_API_VERSION', '2025-04-01-preview')
model = os.getenv('DIAL_MODEL', 'gpt-4o-mini')

if not api_key:
    print('DIAL_API_KEY not set — skipping AI test')
else:
    url = f'{api_base}/openai/deployments/{model}/chat/completions?api-version={api_version}'
    payload = json.dumps({
        'messages': [{'role': 'user', 'content': 'Say OK'}],
        'max_tokens': 5
    }).encode('utf-8')
    req = urllib.request.Request(url, data=payload,
        headers={'api-key': api_key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            print('AI test PASSED. Response:', resp['choices'][0]['message']['content'])
    except Exception as e:
        print('AI test FAILED:', e)
"
```

**Expected output:**
```
AI test PASSED. Response: OK
```

---

## 7. Level 6: Rule Book Test

**Goal:** Verify the rule book loads correctly and contains expected rules.

### Test 6.1 — View all rules

```powershell
cd C:\EPAM-Personal\Migration-validator\src
python validate_cli.py rules
```

**Expected output (excerpt):**
```
  Base rules   : 12
  Learned rules: 0
  Total        : 12

  ── BASE RULES (Built-in, apply automatically) ──────────────
  boolean_conversion  (Boolean to 1/0 String)
    Description : Converts PostgreSQL boolean to '1'/'0' string...
    Triggers on : boolean → BOOLEAN
    PG SQL      : CASE WHEN {col} THEN '1' ELSE '0' END
    SF SQL      : CASE WHEN {col} THEN '1' ELSE '0' END
  ...
```

**What to verify:**
- At least 10 base rules are listed
- Each rule shows `PG SQL` and `SF SQL` templates
- No Python error during load

---

### Test 6.2 — Test rule lookup

```powershell
python -c "
from rule_book import rule_book

# Test type lookups
test_cases = [
    ('boolean', 'BOOLEAN'),
    ('integer', 'NUMBER'),
    ('character varying', 'TEXT'),
    ('date', 'DATE'),
    ('timestamp without time zone', 'TIMESTAMP_NTZ'),
    ('timestamp with time zone', 'TIMESTAMP_TZ'),
    ('numeric', 'FLOAT'),
    ('uuid', 'TEXT'),
]

print('Rule lookup tests:')
for pg_type, sf_type in test_cases:
    rule = rule_book.get_rule_for_type(pg_type, sf_type)
    pg_expr = rule.apply_postgresql('test_col', alias='test_col_normalized')
    print(f'  {pg_type:<35} → {sf_type:<15} | {rule.__class__.__name__}')
    print(f'    PG: {pg_expr[:80]}')
"
```

**Expected:** Each type pair returns a rule with a valid SQL expression. No `None` or `AttributeError`.

---

### Test 6.3 — Add and verify a learned rule

```powershell
python validate_cli.py add-rule
```

When prompted:
```
Rule ID: test_rule_delete_me
Display name: Test Rule
Description: A test rule for manual testing
When to apply: VARCHAR to VARCHAR
PostgreSQL SQL: TRIM(UPPER({col}))
Snowflake SQL: TRIM(UPPER({col}))
Example: (skip)
Save? Y
```

**Expected:**
```
  ✓ Rule 'test_rule_delete_me' saved to rule_book_learned.json ✓
  ✓ It will be included in ALL future AI prompts automatically.
```

Verify it was saved:

```powershell
python -c "
from rule_book import rule_book
learned = rule_book.learned_rules()
print(f'Learned rules: {len(learned)}')
for r in learned:
    print(f'  {r.id}: {r.description}')
"
```

**Cleanup** (remove the test rule from `src/rule_book_learned.json`):

```powershell
# Open the file and delete the test_rule_delete_me entry manually
notepad src\rule_book_learned.json
```

---

## 8. Level 7: SQL Query Generation Test

**Goal:** Verify that all 8 queries are generated correctly and contain valid SQL.

### Test 7.1 — Generate queries (no database needed)

If you want to test query structure without needing a database connection, use the Python API directly:

```powershell
cd C:\EPAM-Personal\Migration-validator\src
python -c "
from models import DatabaseType, ColumnMapping, TransformationRuleType
from generated_queries.sql_query_generator import SQLQueryGenerator
from ai_transformation.static_rule_mapper import ColumnRuleMapping
from rules import get_rule_for_type

# Define some test column mappings
test_mappings = [
    ColumnRuleMapping(
        source_column='user_id',
        target_column='USER_ID',
        source_type='integer',
        target_type='NUMBER',
        rule=get_rule_for_type('integer', 'NUMBER'),
        is_primary_key=True,
        skip_validation=False,
        matched_by='exact',
    ),
    ColumnRuleMapping(
        source_column='username',
        target_column='USERNAME',
        source_type='character varying',
        target_type='TEXT',
        rule=get_rule_for_type('character varying', 'TEXT'),
        is_primary_key=False,
        skip_validation=False,
        matched_by='exact',
    ),
    ColumnRuleMapping(
        source_column='is_active',
        target_column='IS_ACTIVE',
        source_type='boolean',
        target_type='BOOLEAN',
        rule=get_rule_for_type('boolean', 'BOOLEAN'),
        is_primary_key=False,
        skip_validation=False,
        matched_by='exact',
    ),
]

gen = SQLQueryGenerator()
qs = gen.generate(
    pg_schema='public',
    pg_table='users',
    sf_database='MY_DB',
    sf_schema='MY_SCHEMA',
    sf_table='USERS',
    mappings=test_mappings,
    has_fivetran_active=True,
    generated_by='static',
    model_used='N/A',
)

print('=== QUERY ① - Row Count PostgreSQL ===')
print(qs.row_count_source)
print()
print('=== QUERY ② - Row Count Snowflake ===')
print(qs.row_count_target)
print()
print('=== QUERY ③ - Main Validation PostgreSQL ===')
print(qs.main_validation_source)
print()
print('=== QUERY ④ - Main Validation Snowflake ===')
print(qs.main_validation_target)
print()
print('=== QUERY ⑤ - NULL % PostgreSQL ===')
print(qs.null_pct_source)
print()
print('=== QUERY ⑦ - Distinct Count PostgreSQL ===')
print(qs.distinct_count_source)
"
```

**Expected output for Query ①:**
```sql
-- ① ROW COUNT: PostgreSQL (public.users)
SELECT COUNT(*) AS source_row_count
FROM public.users;
```

**Expected output for Query ②:**
```sql
-- ② ROW COUNT: Snowflake (MY_DB.MY_SCHEMA.USERS)
SELECT COUNT(*) AS target_row_count
FROM MY_DB.MY_SCHEMA.USERS
WHERE _FIVETRAN_ACTIVE = TRUE;
```

**Expected output for Query ③:**
```sql
-- ③ SOURCE: PostgreSQL (public.users)
SELECT
    COALESCE(CAST(CAST(user_id AS TEXT) AS TEXT), '<<NULL>>') AS user_id_normalized,
    COALESCE(CAST(TRIM(username) AS TEXT), '<<NULL>>') AS username_normalized,
    COALESCE(CAST(CASE WHEN is_active THEN '1' ELSE '0' END AS TEXT), '<<NULL>>') AS is_active_normalized
FROM public.users;
```

**What to verify per query:**
- ① `COUNT(*)` with alias `source_row_count`
- ② `COUNT(*)` with alias `target_row_count` + Fivetran filter (if applicable)
- ③ All columns with `_normalized` alias, COALESCE wrapper, correct PG expressions
- ④ All columns with same alias names as ③ but SF expressions, Fivetran filter
- ⑤ `total_rows` + `_null_pct` per column using `SUM(CASE WHEN ... IS NULL ...)`
- ⑦ `total_rows` + `_distinct_count` per column using `COUNT(DISTINCT ...)`

---

### Test 7.2 — Run full generation with live databases

```powershell
cd C:\EPAM-Personal\Migration-validator\src
python validate_cli.py generate --pg-table events --sf-table EVENTS
```

**During the run you will be prompted:**
1. Review rule book → press `c` to continue
2. Change model? → press Enter to keep current
3. Proceed? → press `Y`
4. Execute queries now? → press `n` (for generation-only test)

**Expected terminal output:**
```
  ✓  GENERATION COMPLETE
  ──────────────────────────────────────────────────────────────
  Table          : events
  Generated by   : AI
  AI Model       : gpt-4o-mini
  Active columns : 12
  Fivetran filter: YES — WHERE _FIVETRAN_ACTIVE = TRUE

  Output files:
    💾 SQL :  C:\...\validation_sql\events_validation.sql
    📋 YAML:  C:\...\validation_sql\events_validation.yaml
```

**Then verify the output files exist:**

```powershell
Test-Path "C:\EPAM-Personal\Migration-validator\validation_sql\events_validation.sql"
Test-Path "C:\EPAM-Personal\Migration-validator\validation_sql\events_validation.yaml"
# Both must be True
```

---

### Test 7.3 — Verify SQL file contains all 8 queries

```powershell
$sql = Get-Content "C:\EPAM-Personal\Migration-validator\validation_sql\events_validation.sql" -Raw

@("① ROW COUNT", "② ROW COUNT",
  "③ MAIN VALIDATION", "④ MAIN VALIDATION",
  "⑤ NULL % PER COLUMN", "⑥ NULL % PER COLUMN",
  "⑦ DISTINCT VALUE COUNT", "⑧ DISTINCT VALUE COUNT") | ForEach-Object {
    if ($sql -match [regex]::Escape($_)) {
        Write-Host "  FOUND: $_" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $_" -ForegroundColor Red
    }
}
```

**Expected:** All 8 labels found.

---

## 9. Level 8: YAML Output Validation Test

**Goal:** Verify the YAML file is syntactically valid and structurally correct.

### Test 8.1 — YAML syntax validation

```powershell
cd C:\EPAM-Personal\Migration-validator

python -c "
import yaml, sys

yaml_file = 'validation_sql/events_validation.yaml'
try:
    with open(yaml_file) as f:
        data = yaml.safe_load(f)
    print('YAML syntax: VALID')
except yaml.YAMLError as e:
    print('YAML syntax: INVALID')
    print(str(e))
    sys.exit(1)
"
```

**Expected:**
```
YAML syntax: VALID
```

---

### Test 8.2 — YAML structure validation

```powershell
python -c "
import yaml, sys

yaml_file = 'validation_sql/events_validation.yaml'

with open(yaml_file) as f:
    data = yaml.safe_load(f)

errors = []

# Check top-level
if 'tables' not in data:
    errors.append('Missing top-level \"tables\" key')
    print('YAML structure: INVALID -', '\n'.join(errors))
    sys.exit(1)

required_blocks = ['row_count_validation', 'data_validation', 'null_pct_validation', 'distinct_count_validation']
required_keys_per_block = ['source_table_name', 'sourcequery', 'target_table_name', 'targetquery']

for table_name, table_body in data['tables'].items():
    print(f'Table: {table_name}')
    
    if 'validations' not in table_body:
        errors.append(f'  Missing \"validations\" in {table_name}')
        continue
    
    validations = table_body['validations']
    
    for block in required_blocks:
        if block not in validations:
            errors.append(f'  Missing validation block: {block}')
            continue
        
        block_data = validations[block]
        for key in required_keys_per_block:
            if key not in block_data:
                errors.append(f'  Missing key \"{key}\" in {block}')
            elif not str(block_data[key]).strip():
                errors.append(f'  Empty value for \"{key}\" in {block}')
            else:
                print(f'  OK: {block}.{key}')

if errors:
    print('\nFAILED:')
    for e in errors: print(' ', e)
else:
    print('\nYAML structure: ALL CHECKS PASSED')
"
```

**Expected:**
```
Table: events
  OK: row_count_validation.source_table_name
  OK: row_count_validation.sourcequery
  ...
YAML structure: ALL CHECKS PASSED
```

---

### Test 8.3 — Check that queries inside YAML are valid SQL (basic)

```powershell
python -c "
import yaml, re

yaml_file = 'validation_sql/events_validation.yaml'
with open(yaml_file) as f:
    data = yaml.safe_load(f)

issues = []
for table_name, table_body in data['tables'].items():
    for block_name, block in table_body['validations'].items():
        for query_key in ['sourcequery', 'targetquery']:
            sql = block.get(query_key, '')
            if not sql:
                issues.append(f'{block_name}.{query_key} is empty')
                continue
            if 'SELECT' not in sql.upper():
                issues.append(f'{block_name}.{query_key} missing SELECT')
            if 'FROM' not in sql.upper():
                issues.append(f'{block_name}.{query_key} missing FROM')

if issues:
    print('SQL sanity check FAILED:')
    for i in issues: print(' ', i)
else:
    print('SQL sanity check: PASSED (SELECT + FROM found in all queries)')
"
```

---

### Test 8.4 — YAML indentation check (10-space SQL content)

```powershell
python -c "
with open('validation_sql/events_validation.yaml') as f:
    lines = f.readlines()

in_query_block = False
bad_lines = []
for i, line in enumerate(lines, 1):
    stripped = line.rstrip('\n')
    if 'sourcequery: |' in stripped or 'targetquery: |' in stripped:
        in_query_block = True
        continue
    if in_query_block:
        if stripped.strip() == '' or stripped.startswith('#'):
            in_query_block = False
            continue
        if stripped and not stripped.startswith(' ' * 10):
            bad_lines.append((i, repr(stripped[:50])))

if bad_lines:
    print('Indentation issues (SQL content must be at >=10 spaces):')
    for lineno, content in bad_lines:
        print(f'  Line {lineno}: {content}')
else:
    print('Indentation check: PASSED')
"
```

---

## 10. Level 9: SQL Execution Test (Run Queries Manually)

**Goal:** Execute the generated SQL queries against the real databases and verify results.

### Test 9.1 — Execute Query ① (PostgreSQL row count)

**In psql or DBeaver, connect to PostgreSQL and run:**

```sql
-- From events_validation.sql, Query ①
SELECT COUNT(*) AS source_row_count
FROM public.events;
```

**Expected:** A number > 0 (whatever rows exist in source)  
**Record this number:** `source_row_count = ___________`

---

### Test 9.2 — Execute Query ② (Snowflake row count)

**In Snowflake UI or SnowSQL:**

```sql
-- From events_validation.sql, Query ②
SELECT COUNT(*) AS target_row_count
FROM MY_DB.MY_SCHEMA.EVENTS
WHERE _FIVETRAN_ACTIVE = TRUE;
```

**Expected:** Should match source_row_count from Query ①  
**Record this number:** `target_row_count = ___________`

**Comparison:**
```
source_row_count == target_row_count  → PASS
abs(source - target) / source * 100 < 1% → ACCEPTABLE (within 1% tolerance)
difference > 1% → FAIL — investigate before continuing
```

---

### Test 9.3 — Execute Query ③ (PostgreSQL normalised data, small table)

**Run this only on tables with < 100,000 rows initially.**

```sql
-- From events_validation.sql, Query ③
-- Run in PostgreSQL and export to CSV
COPY (
    SELECT
        COALESCE(CAST(CAST(event_id AS TEXT) AS TEXT), '<<NULL>>') AS event_id_normalized,
        COALESCE(CAST(TRIM(event_name) AS TEXT), '<<NULL>>') AS event_name_normalized,
        ...
    FROM public.events
) TO 'C:/temp/events_source.csv' WITH CSV HEADER;
```

Or in psql:
```
\copy (SELECT ... FROM public.events) TO 'C:/temp/events_source.csv' CSV HEADER
```

---

### Test 9.4 — Execute Query ④ (Snowflake normalised data)

**In Snowflake UI:**
- Run Query ④ from the SQL file
- Click "Download results" → CSV
- Save as `events_target.csv`

---

### Test 9.5 — Compare ③ vs ④

```powershell
# Sort both CSVs by first column and compare
$source = Import-Csv "C:\temp\events_source.csv" | Sort-Object event_id_normalized
$target = Import-Csv "C:\temp\events_target.csv" | Sort-Object event_id_normalized

if ($source.Count -ne $target.Count) {
    Write-Host "ROW COUNT MISMATCH: source=$($source.Count) target=$($target.Count)" -ForegroundColor Red
} else {
    $mismatches = 0
    for ($i = 0; $i -lt $source.Count; $i++) {
        $srcRow = $source[$i]
        $tgtRow = $target[$i]
        # Compare all normalized columns
        foreach ($col in $srcRow.PSObject.Properties.Name) {
            if ($srcRow.$col -ne $tgtRow.$col) {
                $mismatches++
                Write-Host "MISMATCH row $i, col $col: '$($srcRow.$col)' != '$($tgtRow.$col)'" -ForegroundColor Yellow
                if ($mismatches -ge 10) { break }
            }
        }
        if ($mismatches -ge 10) { break }
    }
    if ($mismatches -eq 0) {
        Write-Host "DATA VALIDATION: PASSED - all rows match" -ForegroundColor Green
    } else {
        Write-Host "DATA VALIDATION: FAILED - $mismatches mismatches found" -ForegroundColor Red
    }
}
```

---

### Test 9.6 — Execute Queries ⑤ and ⑥ (NULL %)

```sql
-- Query ⑤ on PostgreSQL
-- Run and note values for each column
```

```sql
-- Query ⑥ on Snowflake
-- Compare _null_pct values with ⑤
```

**Expected:** All `_null_pct` values match between ⑤ and ⑥.

**Tolerance:** For large tables, a difference of < 0.01% is acceptable due to timing (data may have changed between runs).

---

### Test 9.7 — Execute via CLI (automated execution option)

After generating queries, the CLI offers to execute them immediately:

```powershell
python validate_cli.py generate --pg-table events --sf-table EVENTS
# After generation prompts complete:
# Execute queries now? → y (execute ALL queries)
```

**Expected terminal output:**
```
  ✓ Returned 1 row(s) in 45ms
  ┌─────────────────────────┐
  │ source_row_count        │
  ├─────────────────────────┤
  │ 10542                   │
  └─────────────────────────┘
  ...
  ROW COUNT COMPARISON
  ─────────────────────────────
  PostgreSQL rows : 10,542
  Snowflake  rows : 10,542
  ✓ Row counts MATCH ✓  (10,542 rows)
```

---

## 11. Level 10: End-to-End Full Pipeline Test

**Goal:** Run the complete pipeline from connection to output and verify everything works together.

### Test 10.1 — Full pipeline run with verification

```powershell
cd C:\EPAM-Personal\Migration-validator\src

# Run full pipeline
python validate_cli.py generate `
    --pg-database your_db `
    --pg-schema public `
    --pg-table events `
    --sf-database YOUR_DB `
    --sf-schema YOUR_SCHEMA `
    --sf-table EVENTS `
    --model gpt-4o-mini

# Then check all output exists
$sqlFile = "..\validation_sql\events_validation.sql"
$yamlFile = "..\validation_sql\events_validation.yaml"

if (Test-Path $sqlFile) {
    $lineCount = (Get-Content $sqlFile | Measure-Object -Line).Lines
    Write-Host "SQL file: $lineCount lines" -ForegroundColor Green
} else {
    Write-Host "SQL file MISSING" -ForegroundColor Red
}

if (Test-Path $yamlFile) {
    python -c "import yaml; yaml.safe_load(open('$yamlFile'.replace('\','/'))); print('YAML valid')"
} else {
    Write-Host "YAML file MISSING" -ForegroundColor Red
}
```

---

### Test 10.2 — Static fallback mode (no AI key)

Test that the pipeline works without AI:

```powershell
# Temporarily unset the AI key
$savedKey = $env:DIAL_API_KEY
$env:DIAL_API_KEY = ""

python validate_cli.py generate --pg-table events --sf-table EVENTS

# Restore
$env:DIAL_API_KEY = $savedKey
```

**Expected terminal output:**
```
  AI Mode     : ⚠ Not active — static fallback
```

The pipeline should still complete and generate valid output using static type-based rule assignment.

---

### Test 10.3 — Test with a renamed column

If you have a table where source column `reg_date` maps to Snowflake column `REGISTRATION_DATE`:

```powershell
python validate_cli.py generate --pg-table users --sf-table USERS
```

**Expected in the output:**
```
  Active columns : 15
```

The AI (or fuzzy matcher) should detect the `reg_date` → `REGISTRATION_DATE` mapping and apply the `date_standardization` rule.

**Verify in the SQL file:**
```powershell
Select-String "reg_date" "validation_sql\users_validation.sql"
# Should find it in Query ③ as: COALESCE(CAST(TO_CHAR(reg_date, 'YYYY-MM-DD') AS TEXT), '<<NULL>>') AS reg_date_normalized
```

---

## 12. Level 11: Report Generation Test

**Goal:** Verify that JSON, HTML, and Text reports are generated correctly by the `DataValidator` engine.

### Test 11.1 — Generate reports using the validator API

```powershell
cd C:\EPAM-Personal\Migration-validator\src

python -c "
from dotenv import load_dotenv; load_dotenv('../.env')
from models import *
from validator import DataValidator
from report_generator import ReportWriter, ReportGenerator
import os

# Build a minimal config (uses your actual databases)
source_db = DatabaseConfig(
    database_type=DatabaseType.POSTGRESQL,
    host=os.getenv('SOURCE_HOST','localhost'),
    port=int(os.getenv('SOURCE_PORT','5432')),
    database=os.getenv('SOURCE_DATABASE',''),
    username=os.getenv('SOURCE_USERNAME',''),
    password=os.getenv('SOURCE_PASSWORD',''),
    schema=os.getenv('SOURCE_SCHEMA','public')
)

# Minimal column mapping test
col_maps = [
    ColumnMapping(
        source_column='event_id',
        target_column='EVENT_ID',
        source_data_type='integer',
        target_data_type='NUMBER',
        primary_key=True
    )
]

table_map = TableMapping(
    source_table='events',
    target_table='EVENTS',
    column_mappings=col_maps
)

print('Report Generator test...')
from models import ValidationReport, TableValidationResult
from datetime import datetime
import uuid

# Build a dummy report for format testing (no DB connection needed)
report = ValidationReport(
    validation_id=str(uuid.uuid4()),
    timestamp=datetime.now(),
    source_database='postgresql://localhost/test',
    target_database='snowflake://account/db',
    total_tables=1,
    passed_tables=1,
    failed_tables=0,
    error_tables=0,
    total_source_rows=100,
    total_target_rows=100,
    total_matched_rows=100,
    overall_status='PASS'
)

# Generate text report
text_report = ReportGenerator.generate_text_report(report)
print(text_report[:500])
print('Report generation: PASSED')
"
```

---

## 13. Validation Decision Matrix

Use this table to decide which tests to run based on your situation:

| Situation | Tests to Run | Time |
|---|---|---|
| First time setup | 1.1, 1.2, 1.3, 2.1, 2.2, 3.3 | 15 min |
| Before a migration hand-off | All levels 1–9 | 2 hours |
| Daily regression check | 2.1, 2.2, 7.2, 9.1, 9.2 | 30 min |
| YAML file is broken | 8.1, 8.2, 8.3, 8.4 | 10 min |
| AI not working | 5.1, 5.2 | 5 min |
| Rule book changes | 6.1, 6.2 | 10 min |
| New table being validated | 3.1, 3.2, 4.1, 7.2, 8.1–8.4, 9.1–9.7 | 45 min |
| Column matching is wrong | 4.1, 4.2, 6.3 (add rule) | 20 min |

---

## 14. Interpreting Results — Pass / Fail / Partial

### Row Count Results (① vs ②)

| Result | Meaning | Action |
|---|---|---|
| ① == ② | Row counts match | Proceed to data validation ③④ |
| abs(①-②)/① < 1% | Within tolerance | Investigate and document, usually acceptable |
| ①② differ by > 1% | Rows missing or duplicated | Block sign-off; investigate ETL |
| ② > ① | Duplicate rows in Snowflake | Check Fivetran filter is applied; check dedup logic |
| ② < ① | Rows missing in Snowflake | Check ETL job completed; check filters in ETL |

### Data Validation Results (③ vs ④)

| Result | Meaning | Action |
|---|---|---|
| ③ CSV == ④ CSV | All values match after normalization | PASS — migration is complete |
| Small % mismatch | Transformation rule not covering a case | Add learned rule; regenerate; re-run |
| Large % mismatch | Wrong transformation rule applied | Check rule assignment; fix type mapping |
| `<<NULL>>` vs actual value | NULL handling differs between sides | Check NULL_STANDARDIZATION rule |
| Timestamp mismatch | Timezone conversion issue | Check TIMESTAMP_TZ rule for UTC conversion |

### NULL % Results (⑤ vs ⑥)

| Result | Meaning | Action |
|---|---|---|
| All null_pct match | NULL distribution identical | PASS |
| Source null_pct > Target null_pct | NULLs converted to 0 or empty string in target | Investigate ETL default values |
| Target null_pct > Source null_pct | Values lost during migration (became NULL) | Investigate ETL failures |

### Overall Status

| Status | Meaning |
|---|---|
| `PASS` | All tables pass; row counts and data match 100% |
| `PARTIAL` | Row counts differ by > 0 but data matches (extra/missing rows) |
| `FAIL` | Data values differ after normalization |
| `ERROR` | Connection failure, query error, or runtime exception |

---

## 15. Test Data Setup (Local PostgreSQL)

If you don't have access to the real databases, use the local Docker PostgreSQL with sample data:

### Start the test database

```powershell
cd C:\EPAM-Personal\Migration-validator
docker-compose up -d

# Wait for health check
Start-Sleep 15
docker ps
# Should show: (healthy) status
```

### Verify sample data

```powershell
psql -h localhost -p 5432 -U admin -d source_db -c "
SELECT table_name, pg_total_relation_size(quote_ident(table_name)) as size_bytes
FROM information_schema.tables
WHERE table_schema = 'source_data'
ORDER BY table_name;
"
```

### Update .env for local database

```bash
SOURCE_HOST=localhost
SOURCE_PORT=5432
SOURCE_DATABASE=source_db
SOURCE_SCHEMA=source_data
SOURCE_USERNAME=admin
SOURCE_PASSWORD=admin123
```

### Run a full local test

```powershell
cd src
python validate_cli.py generate --pg-table users --sf-table USERS
# (Snowflake will fail if not configured — that's OK for local testing)
# Use static fallback mode: skip AI key check
```

### Verify the sample data content

```powershell
psql -h localhost -p 5432 -U admin -d source_db -c "SELECT * FROM source_data.users LIMIT 5;"
```

---

## Quick Reference — Commands Summary

```powershell
# ── Setup ──────────────────────────────────────────────────
cd C:\EPAM-Personal\Migration-validator
.\.venv\Scripts\Activate.ps1

# ── Connection tests ────────────────────────────────────────
cd src
python check_connections.py

# ── List tables ─────────────────────────────────────────────
python validate_cli.py list-tables

# ── List AI models ──────────────────────────────────────────
python validate_cli.py list-models

# ── View rule book ──────────────────────────────────────────
python validate_cli.py rules

# ── Generate queries (full pipeline) ────────────────────────
python validate_cli.py generate --pg-table events --sf-table EVENTS

# ── Generate with specific model ────────────────────────────
python validate_cli.py generate --pg-table events --sf-table EVENTS --model gpt-4o-mini

# ── Validate YAML file ──────────────────────────────────────
python -c "import yaml; yaml.safe_load(open('../validation_sql/events_validation.yaml')); print('OK')"

# ── Run verify script ────────────────────────────────────────
python verify_yaml_generation.py

# ── View generated SQL ──────────────────────────────────────
Get-Content "..\validation_sql\events_validation.sql"

# ── Add a custom rule ────────────────────────────────────────
python validate_cli.py add-rule

# ── Interactive menu ────────────────────────────────────────
python validate_cli.py
```

---

*Last updated: 2026-08-10*  
*Maintained by: AI Engineering Team — EPAM*
