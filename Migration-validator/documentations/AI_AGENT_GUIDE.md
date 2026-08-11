# AI Query Agent — Execution Guide

This guide covers everything needed to use the AI-powered SQL validation query generator end-to-end.

---

## Prerequisites

| Requirement | Details |
|---|---|
| EPAM VPN | Must be connected — DIAL API only works on VPN |
| Python venv | `.venv` in the project root |
| `.env` file | Created from `.env.example` with your `DIAL_API_KEY` set |
| Source DB | PostgreSQL or MSSQL running and accessible |
| Target DB | Snowflake account with migrated tables |

---

## One-Time Setup

### 1. Create `.env`

```powershell
cd C:\EPAM-Personal\Migration-validator
copy .env.example .env
```

Open `.env` and fill in:

```
DIAL_API_KEY=<your key from https://ai-proxy.lab.epam.com>
DIAL_API_BASE=https://ai-proxy.lab.epam.com
DIAL_API_VERSION=2025-04-01-preview
DIAL_MODEL=gpt-4o
```

Your key name in the EPAM DIAL portal: **EPM-GPT-Ganesh_Rustummane_PERSONAL**

### 2. Verify DIAL connection

```powershell
.\.venv\Scripts\python.exe -c "
import os; from dotenv import load_dotenv; load_dotenv('.env')
from openai import AzureOpenAI
key = os.getenv('DIAL_API_KEY')
client = AzureOpenAI(api_key=key, api_version='2025-04-01-preview', azure_endpoint='https://ai-proxy.lab.epam.com')
r = client.chat.completions.create(model='gpt-4o', messages=[{'role':'user','content':'say DIAL_OK'}], extra_headers={'Api-Key': key}, max_tokens=5)
print(r.choices[0].message.content)
"
```

Expected output: `DIAL_OK`

---

## The Two-Step Workflow

```
STEP 1 — discover     Print the introspection SQL to run in your DB client
STEP 2 — generate     AI reads your schema → writes validation SQL for you
```

The AI **never connects to your databases**. You paste the schema output as input, and you paste the generated SQL into your DB client to run. No data leaves your environment through the AI.

---

## Step 1 — Get Schema Introspection SQL

Run `discover` to get the exact query you need to execute in your SQL client.

### PostgreSQL source

```powershell
.\.venv\Scripts\python.exe src\ai_cli.py discover `
  --source-type postgresql `
  --schema source_data `
  --table users
```

### SQL Server source

```powershell
.\.venv\Scripts\python.exe src\ai_cli.py discover `
  --source-type mssql `
  --schema dbo `
  --table Customers
```

### Snowflake target

```powershell
.\.venv\Scripts\python.exe src\ai_cli.py discover `
  --source-type snowflake `
  --schema TARGET_SCHEMA `
  --table USERS `
  --database SNOWFLAKE_DB
```

### List all tables in a schema (no --table flag)

```powershell
.\.venv\Scripts\python.exe src\ai_cli.py discover `
  --source-type postgresql `
  --schema source_data
```

The command prints the SQL. Copy it, run it in your SQL client (pgAdmin, DBeaver, SSMS, Snowflake Worksheet), and export the result as a JSON file.

**Export tips by client:**

| Client | How to export JSON |
|---|---|
| DBeaver | Right-click results → Export → JSON |
| pgAdmin | Query Tool → Download as JSON |
| SSMS | Results to text → copy → paste into `.json` file |
| Snowflake Worksheet | Download button → JSON |

Save as e.g. `source_users_schema.json` and `target_users_schema.json`.

---

## Step 2 — Generate Validation SQL

There are two input modes: **schema files** (recommended) and **inline columns** (quick testing).

### Mode A — Schema files (from Step 1 export)

```powershell
.\.venv\Scripts\python.exe src\ai_cli.py generate `
  --source-type postgresql `
  --source-schema source_data `
  --source-table users `
  --target-type snowflake `
  --target-schema TARGET_SCHEMA `
  --target-table USERS `
  --target-database SNOWFLAKE_DB `
  --source-schema-file source_users_schema.json `
  --target-schema-file target_users_schema.json `
  --pk user_id
```

### Mode B — Inline columns (quick, no JSON file needed)

Format: `column_name:SOURCE_TYPE:TARGET_TYPE` separated by commas.

```powershell
.\.venv\Scripts\python.exe src\ai_cli.py generate `
  --source-type postgresql `
  --source-schema source_data `
  --source-table users `
  --target-type snowflake `
  --target-schema TARGET_SCHEMA `
  --target-table USERS `
  --target-database SNOWFLAKE_DB `
  --columns "user_id:SERIAL:NUMBER,username:VARCHAR(100):VARCHAR,email:VARCHAR(255):VARCHAR,is_active:BOOLEAN:BOOLEAN,balance:NUMERIC(12,2):NUMBER,created_at:TIMESTAMP:TIMESTAMP_NTZ" `
  --pk user_id
```

> **Tip:** Types with parentheses like `NUMERIC(12,2)` are handled correctly — no need to escape commas inside them.

---

## Output Formats

Control what gets printed with `--output`.

### Console (default) — human-readable summary

```powershell
... generate [options]
```

Shows column mappings, rules assigned per column, AI reasoning, and both SQL queries.

### SQL only — ready to paste directly into your DB client

```powershell
... generate [options] --output sql
```

Output:
```sql
-- SOURCE (PostgreSQL): source_data.users
SELECT
    COALESCE(CAST(user_id AS BIGINT), '<NULL>') AS user_id_normalized,
    COALESCE(LOWER(TRIM(NULLIF(username, ''))), '<NULL>') AS username_normalized,
    ...
FROM source_data.users
ORDER BY user_id

-- TARGET (Snowflake): TARGET_SCHEMA.USERS
SELECT
    COALESCE(CAST(USER_ID AS NUMBER), '<NULL>') AS USER_ID_normalized,
    ...
FROM SNOWFLAKE_DB.TARGET_SCHEMA.USERS
ORDER BY USER_ID
```

### JSON — machine-readable, includes rule assignments

```powershell
... generate [options] --output json
```

Useful for piping into other tools or saving the full plan.

### Save to file instead of stdout

```powershell
... generate [options] --output sql --output-file users_validation.sql
```

---

## Full Real-World Example

Validating a `customers` table migrated from MSSQL to Snowflake.

```powershell
# Step 1a — get source introspection SQL
.\.venv\Scripts\python.exe src\ai_cli.py discover `
  --source-type mssql `
  --schema dbo `
  --table Customers

# Step 1b — get target introspection SQL
.\.venv\Scripts\python.exe src\ai_cli.py discover `
  --source-type snowflake `
  --schema TARGET_SCHEMA `
  --table CUSTOMERS `
  --database SNOWFLAKE_DB
```

Run both queries in your SQL clients, export results to:
- `customers_source_schema.json`
- `customers_target_schema.json`

```powershell
# Step 2 — generate validation SQL
.\.venv\Scripts\python.exe src\ai_cli.py generate `
  --source-type mssql `
  --source-schema dbo `
  --source-table Customers `
  --target-type snowflake `
  --target-schema TARGET_SCHEMA `
  --target-table CUSTOMERS `
  --target-database SNOWFLAKE_DB `
  --source-schema-file customers_source_schema.json `
  --target-schema-file customers_target_schema.json `
  --pk customer_id `
  --output sql `
  --output-file customers_validation.sql
```

Open `customers_validation.sql`. It contains two blocks:
1. **SOURCE SQL** — run in MSSQL
2. **TARGET SQL** — run in Snowflake

Run each in the respective DB client, export both results to CSV/Excel, then compare row by row.

---

## What the AI Does (and Does Not Do)

| The AI does | The AI does not |
|---|---|
| Reads column types from your schema input | Connect to your databases |
| Selects the right transformation rules from `rules_catalog.json` | Read or extract any actual table data |
| Generates dialect-specific SQL per DB (MSSQL / PostgreSQL / Snowflake) | Store or log your schema metadata |
| Explains its rule choices | Modify any existing data |

### How rules are selected

The AI reads `src/rules_catalog.json` and matches each source→target type pair to the applicable rules, then chains them in canonical order. Example:

| Source type | Target type | Rules applied |
|---|---|---|
| `BOOLEAN` | `BOOLEAN` | `BOOLEAN_CONVERSION` → `NULL_STANDARDIZATION` |
| `VARCHAR(100)` | `VARCHAR` | `EMPTY_STRING_NULL` → `WHITESPACE_TRIM` → `CASE_INSENSITIVE` → `NULL_STANDARDIZATION` |
| `NUMERIC(12,2)` | `NUMBER` | `NUMERIC_PRECISION` → `NULL_STANDARDIZATION` |
| `TIMESTAMP` | `TIMESTAMP_NTZ` | `DATE_STANDARDIZATION` → `NULL_STANDARDIZATION` |
| `BIT` | `BOOLEAN` | `BOOLEAN_CONVERSION` → `NULL_STANDARDIZATION` |
| `SERIAL` | `NUMBER` | `INTEGER_CAST` → `NULL_STANDARDIZATION` |

The chaining produces a single nested expression, e.g.:
```sql
COALESCE(LOWER(TRIM(NULLIF(username, ''))), '<NULL>') AS username_normalized
```

---

## No VPN / Offline Mode

When `DIAL_API_KEY` is not set or DIAL is unreachable, the agent automatically falls back to **static rule matching** — it applies the same rules using the type-pair logic in `rules_catalog.json` without calling any API. The output SQL is identical in quality; you just lose the AI's free-text explanation of edge cases.

```
[INFO] DIAL_API_KEY not set — using static rule matching.
```

No code change needed to switch modes — just set or unset the env var.

---

## Adding New Rules

All rules live in `src/rules_catalog.json`. To add a custom rule (e.g. phone number normalization):

1. **Add entry to `rules_catalog.json`:**
```json
{
  "id": "phone_normalize",
  "enum_value": "PHONE_NORMALIZE",
  "display_name": "Phone Normalization",
  "description": "Strips non-digit characters from phone numbers for uniform comparison.",
  "auto_detect": false,
  "trigger_type_pairs": [
    {"source": "VARCHAR", "target": "VARCHAR"}
  ],
  "sql_templates": {
    "MSSQL":      "REPLACE(REPLACE(REPLACE({col}, '-', ''), '(', ''), ')', '') AS {col}_normalized",
    "PostgreSQL": "REGEXP_REPLACE({col}, '[^0-9]', '', 'g') AS {col}_normalized",
    "Snowflake":  "REGEXP_REPLACE({col}, '[^0-9]', '') AS {col}_normalized"
  },
  "notes": "Set auto_detect: false — only apply when explicitly requested."
}
```

2. **Add to `TransformationRuleType` enum in `src/models.py`:**
```python
PHONE_NORMALIZE = "phone_normalize"
```

3. **Add rule class in `src/transformation_rules.py`:**
```python
class PhoneNormalizeRule(TransformationRule):
    def __init__(self):
        super().__init__(TransformationRuleType.PHONE_NORMALIZE)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        if db_type == DatabaseType.MSSQL:
            return f"REPLACE(REPLACE(REPLACE({expr}, '-', ''), '(', ''), ')', '')"
        elif db_type == DatabaseType.POSTGRESQL:
            return f"REGEXP_REPLACE({expr}, '[^0-9]', '', 'g')"
        else:  # Snowflake
            return f"REGEXP_REPLACE({expr}, '[^0-9]', '')"
```

4. **Register it in `TransformationRulesEngine.__init__()` in the same file.**

The AI will immediately pick it up in the next run because the system prompt is built from `rules_catalog.json` at runtime.

---

## Troubleshooting

### `DIAL API error: 401`
- Check your `DIAL_API_KEY` in `.env` — no extra spaces or quotes
- Confirm you are on EPAM VPN

### `DIAL API error: 404` or `DeploymentNotFound`
- Check `DIAL_MODEL` in `.env` — must be an exact deployment name
- Run this to list what your key can access:
```powershell
.\.venv\Scripts\python.exe -c "
import os, requests
from dotenv import load_dotenv; load_dotenv('.env')
key = os.getenv('DIAL_API_KEY')
r = requests.get('https://ai-proxy.lab.epam.com/openai/models', headers={'Api-Key': key})
for m in r.json()['data']: print(m['id'])
"
```

### `DIAL API error: 429`
- Your personal key daily/minute limit is exhausted for that model
- Switch to another model: set `DIAL_MODEL=anthropic.claude-sonnet-5` in `.env`

### `No target column found for source 'col_name'`
- Column names don't match between source and target schema files
- Check that the introspection queries ran on the right table/schema
- Snowflake uppercases column names — this is expected and handled automatically

### `ModuleNotFoundError: No module named 'click'`
```powershell
.\.venv\Scripts\pip install click
```

### Column with `NUMERIC(12,2)` is split incorrectly in `--columns`
- This is fixed — commas inside parentheses are not treated as delimiters
- If you see it split, make sure you are using the latest `src/ai_cli.py`

---

## Quick Reference — All CLI Options

```
discover
  --source-type  -t   postgresql | mssql | snowflake   (required)
  --schema       -s   Schema name                       (required)
  --table        -T   Table name (omit to list tables)
  --database     -d   Database name (Snowflake only)

generate
  --source-type      -st   Source DB type               (required)
  --source-schema    -ss   Source schema                (required)
  --source-table     -sT   Source table                 (required)
  --target-type      -tt   Target DB type               (required)
  --target-schema    -ts   Target schema                (required)
  --target-table     -tT   Target table                 (required)
  --target-database  -td   Target database (Snowflake)
  --source-schema-file -sf JSON file from Step 1 (source)
  --target-schema-file -tf JSON file from Step 1 (target)
  --columns        -c   Inline: "col:SRC_TYPE:TGT_TYPE,..."
  --pk             -k   Primary key column(s), repeatable
  --output         -o   console | sql | json            (default: console)
  --output-file    -O   Write to file instead of stdout
  --model          -m   Override DIAL model for this run
```
