# Migration Validator — Complete Documentation (Part 1 of 2)
**From Foundation to Implementation**

---

## Table of Contents - Part 1

1. [Introduction & Overview](#1-introduction--overview)
2. [Business Problem & Solution](#2-business-problem--solution)
3. [Core Concepts & Terminology](#3-core-concepts--terminology)
4. [Architecture Foundation](#4-architecture-foundation)
5. [Environment Setup & Configuration](#5-environment-setup--configuration)
6. [Data Type Normalization System](#6-data-type-normalization-system)
7. [Connection Management](#7-connection-management)

---

## 1. Introduction & Overview

### 1.1 What Is Migration Validator?

Migration Validator is an **intelligent automation tool** that eliminates the most time-consuming and error-prone part of database migration projects: **validating that data moved correctly from source to target**.

**Traditional Approach (Before Migration Validator):**
- Data engineers manually write 100s of SQL queries per table
- Each query must handle data type differences (timestamp formats, decimal precision, boolean representations)
- 2-4 hours per table to write validation queries
- High risk of human error in query logic
- No consistency across tables or engineers
- No audit trail

**With Migration Validator:**
- Automated SQL generation in <30 seconds per table
- AI-powered column mapping and rule assignment
- Consistent normalization rules across all tables
- Production-ready SQL + YAML configuration files
- Complete audit trail with version control
- Zero SQL writing by hand

### 1.2 Supported Database Systems

**Source Databases (Data Origin):**
| Database | Type | Use Case | Connection Method |
|----------|------|----------|-------------------|
| **PostgreSQL** | Relational OLTP | Primary operational database | `psycopg2` driver |
| **MS SQL Server** | Relational OLTP | Legacy enterprise systems | `pyodbc` driver (Windows Auth supported) |
| **AWS Athena** | Data Lake Query Engine | S3-backed analytical data | AWS SDK (`boto3` + Glue) |

**Target Database (Migration Destination):**
| Database | Type | Connection Method |
|----------|------|-------------------|
| **Snowflake** | Cloud Data Warehouse | `snowflake-connector-python` |

**Multi-Source Architecture:**
- Up to **10 source connections** simultaneously (`SRC_1` to `SRC_10`)
- Each source can be a different database type
- One Snowflake target for all sources
- No code changes needed to add new sources

### 1.3 Key Features

#### 🤖 AI-Powered Intelligence
- Uses **EPAM DIAL** (GPT-4o, Claude, Gemini) for smart column mapping
- Handles renamed columns automatically (e.g., `customer_id` → `CUSTOMER_ID`, `created_at` → `CREATED_TIMESTAMP`)
- Falls back to deterministic fuzzy matching when AI is unavailable
- Learns from custom rules you add

#### 📋 7-Step Validation Plan
1. **Schema Extraction** — Live column discovery from both databases
2. **Exact Matching** — Name-based matching (case-insensitive)
3. **Fuzzy Matching** — Similarity scoring with RapidFuzz
4. **Confidence Scoring** — Multi-factor confidence calculation
5. **AI Consultation** — Only for genuinely ambiguous columns
6. **Plan Integrity Validation** — Ensures every column is mapped correctly
7. **SQL + YAML Generation** — Production-ready outputs

#### 🛡️ Type-Aware Normalization
- 11 built-in normalization rules handle all data type differences
- Boolean → `'1'` / `'0'` comparison
- Numeric → ROUND to 2 decimal places
- Timestamps → UTC normalization + fixed format
- Text → TRIM whitespace
- UUID → uppercase normalization
- JSON → canonical key-sorted serialization
- NULL → sentinel value `<<NULL>>`

#### 📦 Multiple Validation Modes
- **Single Table** — Interactive: pick source → pick table → generate
- **Multi-Table** — Batch process multiple tables at once
- **Parameterized** — CLI flags for CI/CD automation
- **Batch YAML** — Define all tables in a YAML file, run in parallel

#### 📄 Output Artifacts
Every validation run produces:
- **`<table>_validation.sql`** — 8+ ready-to-execute queries
- **`<table>_validation.yaml`** — Machine-readable config for CI/CD
- **`<table>_count_validation.yaml`** — Lightweight row-count-only config
- **`<table>_dynamic_suite.sql`** — Extended edge-case checks (optional)

---

## 2. Business Problem & Solution

### 2.1 The Migration Validation Challenge

When organizations migrate databases (e.g., PostgreSQL → Snowflake), they face a critical question:

> **"Did all the data move correctly?"**

This question breaks down into hundreds of smaller questions:
- Do row counts match?
- Are column values identical after type conversions?
- Are NULLs handled correctly?
- Did timestamps lose timezone information?
- Were decimal precisions rounded consistently?
- Are there any duplicate or missing rows?

### 2.2 Pain Points Without Automation

| Problem | Impact | Cost |
|---------|--------|------|
| **Manual SQL Writing** | Engineers write 6+ queries per table × 100 tables = 600+ queries | 200-400 hours of engineering time |
| **Type Mismatch Errors** | `BOOLEAN TRUE` in PG becomes `1` in Snowflake — queries fail if not handled | Discovered late in UAT, requires rework |
| **Inconsistent Logic** | Different engineers write different comparison logic | Hard to debug discrepancies |
| **No Audit Trail** | Ad-hoc queries not version controlled | Compliance and debugging issues |
| **Multi-Source Complexity** | Each source DB needs custom scripts | Cannot scale to 10+ source systems |

### 2.3 How Migration Validator Solves This

**Before Migration Validator:**
```
Data Engineer → Manually writes SQL for Table_A
                                           ↓
                              30+ minutes per query × 6 queries
                                           ↓
                              Tests queries manually in DB
                                           ↓
                              Finds type error → rewrites
                                           ↓
                              Repeat for next 99 tables
                                           ↓
                              Total: 3-4 weeks of effort
```

**With Migration Validator:**
```
Data Engineer → python validate_cli.py generate --table customers
                                           ↓
                              Tool connects to both DBs (2 seconds)
                                           ↓
                              AI maps columns + assigns rules (5 seconds)
                                           ↓
                              Generates SQL + YAML (1 second)
                                           ↓
                              Engineer reviews + runs → Done in 30 seconds
                                           ↓
                              Repeat for all 100 tables → 1 day total
```

**Key Benefits:**
- ✅ **20x faster** — 30 seconds vs 2-4 hours per table
- ✅ **Zero human error** — All rules applied consistently
- ✅ **Future-proof** — Add new rules without rewriting queries
- ✅ **Audit-ready** — All artifacts version controlled in Git
- ✅ **Multi-source ready** — Same tool for PostgreSQL, MS SQL, Athena

---

## 3. Core Concepts & Terminology

### 3.1 Fundamental Terms

#### Source Database
The **origin system** where data currently lives. Can be:
- PostgreSQL (operational database)
- MS SQL Server (legacy enterprise system)
- AWS Athena (S3 data lake)

#### Target Database
The **destination system** where data is being migrated to:
- Snowflake (cloud data warehouse)

#### Table Pair
A **source table + target table** combination that needs validation:
- Source: `public.customers` (PostgreSQL)
- Target: `dev_edge_bronze.storedge_fms_public.CUSTOMERS` (Snowflake)

#### Column Mapping
The association between a **source column** and **target column**:
- Source: `customer_id` (PostgreSQL `BIGINT`)
- Target: `CUSTOMER_ID` (Snowflake `NUMBER`)
- Mapping Method: `exact` (matched by name)

#### Normalization Rule
A **SQL transformation** applied to a column so that source and target values can be compared:
- Source: `ROUND(CAST(amount AS NUMERIC), 2)` (PostgreSQL)
- Target: `ROUND(CAST(AMOUNT AS FLOAT), 2)` (Snowflake)
- Result: Both produce `'1234.57'` (string) for comparison

### 3.2 Validation Workflow Concepts

#### Schema Extraction
The process of **reading column metadata** from live databases:
- Column names
- Data types
- Ordinal positions
- Nullability
- Primary keys

#### Match Confidence
A **score from 0.0 to 1.0** indicating how certain the tool is about a column mapping:
- **1.0** = Exact name match + compatible types
- **0.95+** = High confidence fuzzy match → auto-accepted
- **0.75-0.94** = Ambiguous → needs AI review
- **< 0.75** = No good match found

#### Validation Plan
A **complete mapping specification** for a table pair:
- All source columns
- All target columns
- Column mappings with confidence scores
- Assigned normalization rules
- Primary keys (if detected)
- Fivetran metadata handling

#### Generated Query Set
The **8+ SQL queries** produced for a table pair:
1. Row count — Source
2. Row count — Target
3. Main validation — Source (normalised)
4. Main validation — Target (normalised)
5. NULL % per column — Source
6. NULL % per column — Target
7. Distinct value count — Source
8. Distinct value count — Target
9-14. (Optional) Primary key integrity checks

### 3.3 Special Column Handling

#### Fivetran Metadata Columns
Columns added by **Fivetran ETL tool** that should not be validated:
- `_FIVETRAN_SYNCED` (timestamp when row was synced)
- `_FIVETRAN_DELETED` (soft-delete flag)
- `_FIVETRAN_ACTIVE` (TRUE = active record, FALSE = historical/deleted)

**Tool Behavior:**
- Automatically detects these columns by prefix
- Excludes them from validation
- Adds `WHERE _FIVETRAN_ACTIVE = TRUE` to all Snowflake queries

#### Excluded Columns
Columns that the user **explicitly excludes** from validation:
- Audit timestamps (`inserted_at`, `updated_at`)
- ETL batch IDs
- Internal flags

**Usage:**
```bash
--exclude inserted_at,batch_id,notes
```

#### Unmatched Columns
Columns that **exist in source but not in target** (or vice versa):
- Marked with `skip_validation = True`
- Logged in the output summary
- User can review and add explicit mappings if needed

---

## 4. Architecture Foundation

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                        │
│  validate_cli.py — Interactive menu + CLI commands                 │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                              │
│  validation_pipeline.py — Coordinates 7-step workflow               │
└─┬───────────────────┬────────────────────┬──────────────────────────┘
  │                   │                    │
  │                   │                    │
  ▼                   ▼                    ▼
┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐
│ EXTRACTION   │  │  MATCHING    │  │   SQL GENERATION        │
│              │  │              │  │                         │
│ - Postgres   │  │ - Exact      │  │ - Query Builder         │
│ - MSSQL      │  │ - Fuzzy      │  │ - YAML Writer           │
│ - Athena     │  │ - Confidence │  │ - File Manager          │
│ - Snowflake  │  │ - AI Planner │  │                         │
└──────────────┘  └──────────────┘  └─────────────────────────┘
       │                   │                    │
       │                   │                    │
       ▼                   ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                  │
│  - rules/ (11 built-in normalization rules)                        │
│  - rule_book.py (rule catalog + learned rules)                     │
│  - rule_book_learned.json (user-defined custom rules)              │
└─────────────────────────────────────────────────────────────────────┘
       │                   │                    │
       │                   │                    │
       ▼                   ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SYSTEMS                               │
│  - PostgreSQL DB  - MS SQL Server  - AWS Athena  - Snowflake       │
│  - EPAM DIAL (AI)                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Module Breakdown

#### **User Interface Layer**
| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `validate_cli.py` | CLI entry point | Interactive menu, command dispatch, profile management |
| `setup_wizard.py` | First-run configuration | Database credential setup, connection testing |

#### **Orchestration Layer**
| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `validation_pipeline.py` | Main workflow orchestrator | 7-step pipeline execution, error handling |
| `core/validation_plan.py` | Plan data model | Canonical representation of validation plan |
| `batch/batch_runner.py` | Parallel multi-table processing | YAML config parsing, thread pool execution |

#### **Extraction Layer**
| Module | Purpose | Databases Supported |
|--------|---------|---------------------|
| `sql_extractor/postgres_extractor.py` | PostgreSQL metadata | `information_schema.columns` |
| `sql_extractor/mssql_extractor.py` | MS SQL Server metadata | `sys.columns` + `sys.types` |
| `sql_extractor/athena_extractor.py` | AWS Athena metadata | AWS Glue API + PyAthena |
| `sql_extractor/snowflake_extractor.py` | Snowflake metadata | `INFORMATION_SCHEMA.COLUMNS` |

#### **Matching & AI Layer**
| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `matching/exact_matcher.py` | Exact name matching | Case-insensitive, normalized matching |
| `matching/fuzzy_matcher.py` | Similarity scoring | RapidFuzz token_ratio, Levenshtein |
| `matching/confidence.py` | Multi-factor confidence | Name + type + position scoring |
| `ai/rule_planner.py` | AI column mapping | DIAL API integration, prompt builder |
| `ai_transformation/orchestrator.py` | AI + static fallback | Hybrid matching strategy |

#### **SQL Generation Layer**
| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `generated_queries/sql_query_generator.py` | SQL query builder | Generates 8+ validation queries |
| `generated_queries/yaml_config_writer.py` | YAML config writer | Machine-readable output |
| `generated_queries/query_output_manager.py` | File orchestration | Writes SQL + YAML to disk |

#### **Rule System Layer**
| Module | Purpose | Rules Provided |
|--------|---------|----------------|
| `rules/*.py` | Type-specific normalization | 11 built-in rules (boolean, numeric, timestamp, etc.) |
| `rule_book.py` | Rule catalog manager | Loads base + learned rules, builds AI prompt |
| `rule_book_learned.json` | User-defined rules | Persistent storage for custom rules |

### 4.3 Data Flow Example (Single Table)

**User Action:**
```bash
python src/validate_cli.py generate --pg-table customers --sf-table CUSTOMERS
```

**Detailed Flow:**

**Step 1: Initialization**
```python
validate_cli.py
  ↓
cmd_generate(args)
  ↓
ValidationPipeline(model='gpt-4o')
```

**Step 2: Schema Extraction**
```python
PostgresExtractor.extract_columns('public', 'customers')
  → Returns: [ColumnMetadata(name='id', type='bigint'), 
              ColumnMetadata(name='name', type='varchar'), ...]

SnowflakeExtractor.extract_columns('DEV_DB', 'SCHEMA', 'CUSTOMERS')
  → Returns: [ColumnMetadata(name='ID', type='NUMBER'), 
              ColumnMetadata(name='NAME', type='VARCHAR'), ...]
```

**Step 3: Column Matching**
```python
CandidateMatcher.match(source_columns, target_columns)
  ↓
ExactMatcher: 'id' → 'ID' (exact, case-insensitive)
  ↓
FuzzyMatcher: 'customer_email' → 'EMAIL' (fuzzy, score=0.82)
  ↓
ConfidenceScorer: Final score=0.89 → needs AI
  ↓
AIRulePlanner: Confirms 'customer_email' → 'EMAIL' (confidence boost to 0.97)
  ↓
Returns: List[MatchDecision]
```

**Step 4: Rule Assignment**
```python
For each MatchDecision:
  get_rule_for_type(source_type='bigint', target_type='NUMBER')
    → Returns: IntegerRule
  
  get_rule_for_type(source_type='varchar', target_type='VARCHAR')
    → Returns: TextRule
```

**Step 5: SQL Generation**
```python
SQLQueryGenerator.generate_from_plan(validation_plan)
  ↓
Builds:
  ① SELECT COUNT(*) FROM public.customers;
  ② SELECT COUNT(*) FROM DEV_DB.SCHEMA.CUSTOMERS WHERE _FIVETRAN_ACTIVE=TRUE;
  ③ SELECT 
       COALESCE(CAST(id AS TEXT), '<<NULL>>') AS id_normalized,
       COALESCE(TRIM(name), '<<NULL>>') AS name_normalized
     FROM public.customers;
  ④ (Same for Snowflake)
  ⑤-⑧ (NULL %, distinct counts)
```

**Step 6: File Output**
```python
QueryOutputManager.write_all(...)
  ↓
Writes:
  - validation_sql/customers_validation.sql
  - config/bronze/data_validation/customers_validation.yaml
  - config/bronze/count_validation/bronze_count_validation.yaml
```

**Step 7: User Review**
```
User opens customers_validation.sql
  → Runs query ① in PostgreSQL → count = 10,000
  → Runs query ② in Snowflake  → count = 10,000 ✓
  → Runs query ③ in PostgreSQL → exports CSV
  → Runs query ④ in Snowflake  → exports CSV
  → Compares CSVs row-by-row    → MATCH ✓
```

---

## 5. Environment Setup & Configuration

### 5.1 Installation Requirements

**System Requirements:**
- Python 3.9 or higher
- pip (package installer)
- Git (for version control)
- Network access to source and target databases

**Operating Systems Supported:**
- Windows (tested on Windows 10/11)
- macOS (tested on macOS 12+)
- Linux (tested on Ubuntu 20.04+)

### 5.2 Python Dependencies

**File:** `requirements.txt`

```txt
# AI and Automation
openai>=1.0.0              # EPAM DIAL uses OpenAI-compatible API
python-dotenv>=1.0.0       # Environment variable management

# Fuzzy Matching
rapidfuzz>=3.0.0           # Fast Levenshtein / token ratio

# Database Drivers
psycopg2-binary==2.9.9     # PostgreSQL
pyodbc==5.1.0              # MS SQL Server
snowflake-connector-python==3.5.0  # Snowflake

# AWS (for Athena)
boto3>=1.26.0              # AWS SDK for Glue metadata
pyathena>=2.25.0           # Athena SQL execution

# Utilities
python-dateutil==2.8.2     # Date parsing
click==8.1.7               # CLI framework
pyyaml>=6.0                # YAML parsing

# Development (Optional)
pytest==7.4.3              # Unit testing
pytest-cov==4.1.0          # Coverage reports
black==23.12.0             # Code formatting
flake8==6.1.0              # Linting
```

**Installation:**
```bash
# Clone the repository
git clone <repository-url>
cd Migration-validator

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5.3 Environment Configuration (.env)

The `.env` file stores **all credentials and configuration** for the tool. It is git-ignored to prevent accidental credential exposure.

**Location:** Project root directory (same level as `requirements.txt`)

**Template:** `.env.example`

#### 5.3.1 AI Configuration (Optional)

```bash
# EPAM DIAL — AI-powered column mapping
DIAL_API_KEY=your_dial_api_key_here
DIAL_API_BASE=https://ai-proxy.lab.epam.com
DIAL_API_VERSION=2025-04-01-preview
DIAL_MODEL=gpt-4o  # Options: gpt-4o, gpt-4o-mini, claude-3-5-sonnet
```

**Notes:**
- Get your DIAL API key at: https://ai-proxy.lab.epam.com (EPAM VPN required)
- If `DIAL_API_KEY` is not set, tool falls back to **static rule matching** (still works, just no AI)
- Model can be changed interactively via menu or `--model` CLI flag

#### 5.3.2 Snowflake Target Configuration (Required)

```bash
# Snowflake — Migration Target
SNOWFLAKE_ACCOUNT=ORGANIZATION-ACCOUNT_NAME  # e.g., ZJAUJWQ-EP12783
SNOWFLAKE_DATABASE=dev_edge_bronze
SNOWFLAKE_SCHEMA=storedge_fms_public
SNOWFLAKE_USERNAME=your_username
SNOWFLAKE_PASSWORD=your_password

# Optional Snowflake Settings
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=DATA_ENGINEER_ROLE
```

**Finding Your Snowflake Account:**
1. Log into Snowflake UI
2. Click **Admin** → **Accounts**
3. Copy **Account Identifier** (format: `ORG-ACCOUNT`)
4. Do NOT include `.snowflakecomputing.com`

#### 5.3.3 Source Database Configuration (Required)

The tool supports **up to 10 source connections** using the `SRC_N_*` pattern:

**PostgreSQL Example (SRC_1):**
```bash
SRC_1_TYPE=postgresql
SRC_1_HOST=localhost
SRC_1_PORT=5432
SRC_1_DATABASE=fms
SRC_1_SCHEMA=public
SRC_1_USERNAME=postgres
SRC_1_PASSWORD=your_password
```

**MS SQL Server Example (SRC_2):**
```bash
SRC_2_TYPE=mssql
SRC_2_HOST=sql-server.internal
SRC_2_PORT=1433
SRC_2_DATABASE=enterprise_db
SRC_2_SCHEMA=dbo
SRC_2_USERNAME=domain\\username  # Windows Auth: use domain\user
SRC_2_PASSWORD=your_password     # Leave blank for Windows Auth
```

**AWS Athena Example (SRC_3):**
```bash
SRC_3_TYPE=athena
SRC_3_HOST=us-east-1          # AWS region (repurposed host field)
SRC_3_PORT=443                # Placeholder (not used)
SRC_3_DATABASE=my_glue_db     # Glue database name
SRC_3_SCHEMA=my_glue_db       # Same as database for Athena
SRC_3_USERNAME=AKIAIOSFODNN7EXAMPLE  # AWS Access Key ID (or blank for IAM role)
SRC_3_PASSWORD=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  # AWS Secret Access Key

# Athena-specific settings
ATHENA_REGION=us-east-1
ATHENA_S3_OUTPUT=s3://your-bucket/athena-results/  # REQUIRED
ATHENA_CATALOG=AwsDataCatalog  # Glue catalog name
ATHENA_WORKGROUP=primary       # Athena workgroup
```

**Multiple Databases on Same Server:**
```bash
# Same PostgreSQL server, different databases = 2 separate connections
SRC_1_TYPE=postgresql
SRC_1_HOST=pg-server.internal
SRC_1_DATABASE=ecommerce
SRC_1_SCHEMA=public
...

SRC_2_TYPE=postgresql
SRC_2_HOST=pg-server.internal  # Same host
SRC_2_DATABASE=analytics       # Different database
SRC_2_SCHEMA=reporting
...
```

#### 5.3.4 Legacy Single-Source Keys (Backward Compatibility)

```bash
# These are auto-populated by the setup wizard and point to SRC_1
# Used by old commands that don't support multi-source
SOURCE_TYPE=postgresql
SOURCE_HOST=localhost
SOURCE_PORT=5432
SOURCE_DATABASE=fms
SOURCE_SCHEMA=public
SOURCE_USERNAME=postgres
SOURCE_PASSWORD=your_password
```

### 5.4 Setup Wizard (First-Run)

**Command:**
```bash
cd src
python validate_cli.py setup
```

**The wizard will:**
1. Ask how many source database servers you have (1-5)
2. Guide you through credentials for each source
3. Test connections to verify credentials
4. Configure Snowflake target
5. Optionally configure DIAL API key
6. Write a clean `.env` file

**Interactive Flow Example:**
```
╔══════════════════════════════════════════════════════════════════╗
║      Migration Validator — First-Run Setup Wizard               ║
╚══════════════════════════════════════════════════════════════════╝

How many source database servers do you want to configure? [1-5]: 2

──────────────────────────────────────────────────────────────────
  SOURCE 1 — Database Server
──────────────────────────────────────────────────────────────────

[1] PostgreSQL
[2] MS SQL Server
[3] AWS Athena

Select database type: 1

PostgreSQL Host [localhost]: db-dev.internal
PostgreSQL Port [5432]: 5432
PostgreSQL Database [postgres]: fms
PostgreSQL Schema [public]: public
PostgreSQL Username [postgres]: reader
PostgreSQL Password: **********

✓ Testing connection to db-dev.internal:5432/fms.public ...
✓ Connection successful — 15 tables found

──────────────────────────────────────────────────────────────────
  SOURCE 2 — Database Server
──────────────────────────────────────────────────────────────────

[1] PostgreSQL
[2] MS SQL Server
[3] AWS Athena

Select database type: 2

MS SQL Server Host: sql-server.corp.local
MS SQL Server Port [1433]: 1433
MS SQL Server Database: CRM
MS SQL Server Schema [dbo]: dbo
MS SQL Server Username: corp\user123
MS SQL Server Password: **********

✓ Testing connection to sql-server.corp.local:1433/CRM.dbo ...
✓ Connection successful — 42 tables found

──────────────────────────────────────────────────────────────────
  SNOWFLAKE TARGET — Migration Destination
──────────────────────────────────────────────────────────────────

Snowflake Account [ZJAUJWQ-EP12783]: ZJAUJWQ-EP12783
Snowflake Database [dev_edge_bronze]: dev_edge_bronze
Snowflake Schema [storedge_fms_public]: storedge_fms_public
Snowflake Username: analyst@company.com
Snowflake Password: **********

✓ Testing Snowflake connection ...
✓ Connection successful — 87 tables found

──────────────────────────────────────────────────────────────────
  EPAM DIAL — AI Configuration (Optional)
──────────────────────────────────────────────────────────────────

Configure EPAM DIAL for AI-powered column mapping? [y/N]: y

DIAL API Key: sk-dial-...
DIAL Model [gpt-4o]: gpt-4o

✓ Testing DIAL API ...
✓ AI mode active — model: gpt-4o

══════════════════════════════════════════════════════════════════
  ✓ SETUP COMPLETE
══════════════════════════════════════════════════════════════════

Configuration saved to: /project/.env

Next steps:
  1. Run: python validate_cli.py connections     ← verify all connections
  2. Run: python validate_cli.py list-tables     ← see available tables
  3. Run: python validate_cli.py                 ← start interactive menu
```

### 5.5 Connection Verification

**Command:**
```bash
python src/validate_cli.py connections
```

**Output:**
```
╔══════════════════════════════════════════════════════════════════╗
║  🔌  CONNECTION REGISTRY  (PostgreSQL / MS SQL Server / Athena)  ║
╚══════════════════════════════════════════════════════════════════╝

Source Connections  (2 configured)

  Slot    Type                Host                    Port  Database            Schema        Status
  ──────────────────────────────────────────────────────────────────────────────────────────────────
  SRC_1   PostgreSQL          db-dev.internal         5432  fms                 public        ✓ OK  15 tables
  SRC_2   MS SQL Server       sql-server.corp.local   1433  CRM                 dbo           ✓ OK  42 tables

Snowflake Target
  ──────────────────────────────────────────────────────────────────────────────────────────────────
  TARGET  Snowflake           ZJAUJWQ-EP12783                 dev_edge_bronze     storedge      ✓ OK  87 tables — Warehouse: COMPUTE_WH

To reconfigure: python validate_cli.py setup
To list tables: python validate_cli.py list-tables
```

---

## 6. Data Type Normalization System

### 6.1 Why Normalization Is Needed

**The Problem:**
Different databases represent the same logical value differently:

| Logical Value | PostgreSQL | Snowflake | Problem |
|---------------|------------|-----------|---------|
| TRUE (boolean) | `TRUE` (boolean type) | `1` or `TRUE` | Direct comparison fails |
| 1234.5678 (decimal) | NUMERIC(10,4) → `1234.5678` | NUMBER → `1234.57` | Precision mismatch |
| 2024-01-15 10:30:00 | TIMESTAMP → includes microseconds | TIMESTAMP_NTZ → truncated | Format mismatch |
| NULL | NULL (special value) | NULL (special value) | Cannot compare in SQL |

**The Solution:**
Apply **normalization rules** that convert both sides to a common text format:

| Logical Value | After PG Rule | After SF Rule | Comparable? |
|---------------|---------------|---------------|-------------|
| TRUE | `'1'` | `'1'` | ✓ YES |
| 1234.5678 | `'1234.57'` | `'1234.57'` | ✓ YES |
| 2024-01-15 10:30:00 | `'2024-01-15 10:30:00'` | `'2024-01-15 10:30:00'` | ✓ YES |
| NULL | `'<<NULL>>'` | `'<<NULL>>'` | ✓ YES |

### 6.2 The 11 Built-In Rules

#### Rule 1: `text` — Text / String Types
**Applies To:**
- PostgreSQL: `VARCHAR`, `TEXT`, `CHAR`, `CHARACTER VARYING`
- Snowflake: `VARCHAR`, `TEXT`, `STRING`

**Transformation:**
- PostgreSQL: `TRIM(column)`
- Snowflake: `TRIM(COLUMN)`

**What It Fixes:**
- Leading/trailing whitespace differences
- ETL adds spaces → TRIM removes them

**Example:**
```sql
-- PostgreSQL
SELECT COALESCE(CAST(TRIM(customer_name) AS TEXT), '<<NULL>>') 
FROM customers;
-- Input:  '  John Doe  '
-- Output: 'John Doe'

-- Snowflake
SELECT COALESCE(CAST(TRIM(CUSTOMER_NAME) AS STRING), '<<NULL>>') 
FROM CUSTOMERS;
-- Input:  'John Doe'
-- Output: 'John Doe'
```

**Does NOT Handle:**
- Case differences (`'john doe'` ≠ `'JOHN DOE'`) — this is intentional
- To handle case: add a custom learned rule with `LOWER()` or `UPPER()`

---

#### Rule 2: `boolean` — Boolean Types
**Applies To:**
- PostgreSQL: `BOOLEAN`, `BOOL`
- Snowflake: `BOOLEAN`, `BOOL`

**Transformation:**
- PostgreSQL:
  ```sql
  CASE 
    WHEN column = true THEN '1' 
    WHEN column = false THEN '0' 
    ELSE NULL 
  END
  ```
- Snowflake:
  ```sql
  CASE 
    WHEN COLUMN = TRUE THEN '1' 
    WHEN COLUMN = FALSE THEN '0' 
    ELSE NULL 
  END
  ```

**What It Fixes:**
- PostgreSQL TRUE/FALSE vs Snowflake 1/0 representation
- Consistent string comparison: `'1'` = `'1'`, `'0'` = `'0'`

**Example:**
```sql
-- Source: is_active = TRUE
-- After PG rule:  '1'
-- After SF rule:  '1'
-- Comparison: '1' = '1' → MATCH ✓
```

---

#### Rule 3: `integer` — Integer Types
**Applies To:**
- PostgreSQL: `SMALLINT`, `INTEGER`, `INT`, `BIGINT`, `SERIAL`, `BIGSERIAL`
- Snowflake: `NUMBER`, `INTEGER`, `BIGINT`

**Transformation:**
- PostgreSQL: `CAST(column AS TEXT)`
- Snowflake: `CAST(COLUMN AS STRING)`

**What It Fixes:**
- Different numeric representations
- Ensures exact digit-by-digit comparison

**Example:**
```sql
-- Source: customer_id = 123456789
-- After PG rule:  '123456789'
-- After SF rule:  '123456789'
-- Comparison: '123456789' = '123456789' → MATCH ✓
```

---

#### Rule 4: `numeric` — Decimal / Floating Point Types
**Applies To:**
- PostgreSQL: `NUMERIC`, `DECIMAL`, `FLOAT`, `DOUBLE PRECISION`, `REAL`, `MONEY`
- Snowflake: `NUMBER`, `FLOAT`, `DECIMAL`

**Transformation:**
- PostgreSQL: `CAST(ROUND(CAST(column AS NUMERIC), 2) AS TEXT)`
- Snowflake: `CAST(ROUND(CAST(COLUMN AS FLOAT), 2) AS STRING)`

**What It Fixes:**
- Precision mismatches (`1234.5678` vs `1234.57`)
- ETL rounding errors
- Scientific notation differences

**Example:**
```sql
-- Source: amount = 1234.567890
-- After PG rule:  '1234.57'
-- After SF rule:  '1234.57'
-- Comparison: '1234.57' = '1234.57' → MATCH ✓
```

**Why ROUND(2)?**
- Most financial applications use 2 decimal places
- Eliminates precision noise from ETL
- Custom rule needed for higher precision (e.g., ROUND(4) for foreign exchange)

---

#### Rule 5: `date` — Date Types
**Applies To:**
- PostgreSQL: `DATE`
- Snowflake: `DATE`

**Transformation:**
- PostgreSQL: `TO_CHAR(column, 'YYYY-MM-DD')`
- Snowflake: `TO_VARCHAR(COLUMN, 'YYYY-MM-DD')`

**What It Fixes:**
- Different date display formats
- Ensures ISO 8601 standard: `YYYY-MM-DD`

**Example:**
```sql
-- Source: order_date = 2024-01-15
-- After PG rule:  '2024-01-15'
-- After SF rule:  '2024-01-15'
-- Comparison: '2024-01-15' = '2024-01-15' → MATCH ✓
```

---

#### Rule 6: `timestamp_ntz` — Timestamp Without Timezone
**Applies To:**
- PostgreSQL: `TIMESTAMP`, `TIMESTAMP WITHOUT TIME ZONE`
- Snowflake: `TIMESTAMP_NTZ`

**Transformation:**
- PostgreSQL: `TO_CHAR(column, 'YYYY-MM-DD HH24:MI:SS')`
- Snowflake: `TO_VARCHAR(COLUMN, 'YYYY-MM-DD HH24:MI:SS')`

**What It Fixes:**
- Microsecond truncation (PG stores microseconds, Fivetran may truncate)
- Consistent second-level precision

**Example:**
```sql
-- Source PG: created_at = 2024-01-15 10:30:00.123456
-- Source SF: CREATED_AT = 2024-01-15 10:30:00.000
-- After PG rule:  '2024-01-15 10:30:00'
-- After SF rule:  '2024-01-15 10:30:00'
-- Comparison: '2024-01-15 10:30:00' = '2024-01-15 10:30:00' → MATCH ✓
```

---

#### Rule 7: `timestamp_tz` — Timestamp With Timezone
**Applies To:**
- PostgreSQL: `TIMESTAMP WITH TIME ZONE`, `TIMESTAMPTZ`
- Snowflake: `TIMESTAMP_TZ`

**Transformation:**
- PostgreSQL: `TO_CHAR(column AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')`
- Snowflake: `TO_VARCHAR(CONVERT_TIMEZONE('UTC', COLUMN), 'YYYY-MM-DD HH24:MI:SS')`

**What It Fixes:**
- Timezone differences
- Both sides normalized to UTC before formatting

**Example:**
```sql
-- Source PG: event_time = 2024-01-15 14:30:00+05:30  (IST)
-- Source SF: EVENT_TIME = 2024-01-15 09:00:00+00     (UTC)
-- After PG rule:  '2024-01-15 09:00:00'  (converted to UTC)
-- After SF rule:  '2024-01-15 09:00:00'  (already UTC)
-- Comparison: '2024-01-15 09:00:00' = '2024-01-15 09:00:00' → MATCH ✓
```

---

#### Rule 8: `uuid` — UUID / GUID Types
**Applies To:**
- PostgreSQL: `UUID`
- Snowflake: `VARCHAR`, `STRING` (Fivetran converts UUID → text)

**Transformation:**
- PostgreSQL: `UPPER(TRIM(CAST(column AS TEXT)))`
- Snowflake: `UPPER(TRIM(COLUMN))`

**What It Fixes:**
- Case differences (PG stores lowercase, SF may be uppercase)
- Whitespace trimming

**Example:**
```sql
-- Source PG: user_uuid = a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a2f
-- Source SF: USER_UUID = A0EEBC99-9C0B-4EF8-BB6D-6BB9BD380A2F
-- After PG rule:  'A0EEBC99-9C0B-4EF8-BB6D-6BB9BD380A2F'
-- After SF rule:  'A0EEBC99-9C0B-4EF8-BB6D-6BB9BD380A2F'
-- Comparison: 'A0EEBC99...' = 'A0EEBC99...' → MATCH ✓
```

---

#### Rule 9: `json` — JSON / JSONB Types
**Applies To:**
- PostgreSQL: `JSON`, `JSONB`
- Snowflake: `VARIANT`

**Transformation:**
- PostgreSQL: `column::jsonb::text` (canonical serialization, sorted keys)
- Snowflake: `TO_JSON(PARSE_JSON(CAST(COLUMN AS STRING)))`

**What It Fixes:**
- Key order differences (`{"b":2,"a":1}` vs `{"a":1,"b":2}`)
- Whitespace differences
- Both sides produce alphabetically sorted JSON keys

**Example:**
```sql
-- Source PG: metadata = {"b":2,"a":1}
-- Source SF: METADATA = {"a":1,"b":2}
-- After PG rule:  '{"a":1,"b":2}'  (jsonb sorts keys)
-- After SF rule:  '{"a":1,"b":2}'  (TO_JSON sorts keys)
-- Comparison: '{"a":1,"b":2}' = '{"a":1,"b":2}' → MATCH ✓
```

---

#### Rule 10: `bytea` — Binary Data Types
**Applies To:**
- PostgreSQL: `BYTEA`
- Snowflake: `BINARY`, `VARBINARY`

**Transformation:**
- PostgreSQL: `encode(column, 'hex')` → lowercase hex
- Snowflake: `LOWER(HEX_ENCODE(COLUMN))` → lowercase hex

**What It Fixes:**
- Binary representation differences
- Hex encoding for text comparison

**Example:**
```sql
-- Source PG: file_data = \x48656c6c6f  ("Hello" in bytes)
-- Source SF: FILE_DATA = 0x48656c6c6f
-- After PG rule:  '48656c6c6f'
-- After SF rule:  '48656c6c6f'
-- Comparison: '48656c6c6f' = '48656c6c6f' → MATCH ✓
```

---

#### Rule 11: `null_placeholder` — NULL Handling (ALWAYS APPLIED)
**Applies To:** **ALL columns** (wrapper rule)

**Transformation:**
- PostgreSQL: `COALESCE(CAST(... AS TEXT), '<<NULL>>')`
- Snowflake: `COALESCE(CAST(... AS STRING), '<<NULL>>')`

**What It Fixes:**
- SQL cannot compare NULL = NULL (always FALSE)
- Sentinel value `<<NULL>>` allows text comparison

**Example:**
```sql
-- Source: customer_name = NULL
-- After text rule:  NULL
-- After null_placeholder:  '<<NULL>>'
-- Comparison: '<<NULL>>' = '<<NULL>>' → MATCH ✓
```

**This rule is ALWAYS the outermost wrapper:**
```sql
COALESCE(
  CAST(
    TRIM(customer_name)  ← text rule
  AS TEXT),
  '<<NULL>>'  ← null_placeholder rule
)
```

### 6.3 Rule Application Order

Rules are applied **inside-out** (innermost first, NULL placeholder last):

**Example: `NUMERIC` column**
```sql
-- Step 1: Type-specific transformation (numeric rule)
ROUND(CAST(amount AS NUMERIC), 2)

-- Step 2: Cast to text
CAST(ROUND(CAST(amount AS NUMERIC), 2) AS TEXT)

-- Step 3: Wrap with NULL placeholder (null_placeholder rule)
COALESCE(
  CAST(ROUND(CAST(amount AS NUMERIC), 2) AS TEXT),
  '<<NULL>>'
)
```

**Example: `TIMESTAMP WITH TIME ZONE` column**
```sql
-- Step 1: Convert to UTC (timestamp_tz rule)
column AT TIME ZONE 'UTC'

-- Step 2: Format to fixed string
TO_CHAR(column AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')

-- Step 3: Cast to text
CAST(TO_CHAR(column AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS TEXT)

-- Step 4: Wrap with NULL placeholder
COALESCE(
  CAST(TO_CHAR(column AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS TEXT),
  '<<NULL>>'
)
```

---

## 7. Connection Management

### 7.1 Multi-Source Connection Model

**Key Concept:** Every source connection is **independent** and has its own slot number (`SRC_1` to `SRC_10`).

**Important Distinction:**
- **One Server ≠ One Connection**
- **One Server + One Database + One Schema = One Connection**

**Example Scenario:**
```
PostgreSQL Server: pg-prod.company.com
├── Database: ecommerce
│   ├── Schema: public       → SRC_1
│   ├── Schema: reporting    → SRC_2
├── Database: analytics
│   ├── Schema: public       → SRC_3
```

**This requires 3 separate connections:**
```bash
# SRC_1: ecommerce.public
SRC_1_TYPE=postgresql
SRC_1_HOST=pg-prod.company.com
SRC_1_DATABASE=ecommerce
SRC_1_SCHEMA=public
...

# SRC_2: ecommerce.reporting (SAME server, SAME database, DIFFERENT schema)
SRC_2_TYPE=postgresql
SRC_2_HOST=pg-prod.company.com
SRC_2_DATABASE=ecommerce
SRC_2_SCHEMA=reporting
...

# SRC_3: analytics.public (SAME server, DIFFERENT database)
SRC_3_TYPE=postgresql
SRC_3_HOST=pg-prod.company.com
SRC_3_DATABASE=analytics
SRC_3_SCHEMA=public
...
```

### 7.2 Connection Profiles (Saved Sessions)

**What Are Connection Profiles?**
- Named, reusable connection sets stored outside the project
- Include both source and Snowflake target credentials
- Eliminates re-entering credentials on every run

**Storage Location:**
```
~/.migration-validator/profiles.json
```

**Profile Structure:**
```json
{
  "fms-dev": {
    "source": {
      "db_type": "postgresql",
      "host": "db-dev.internal",
      "port": 5432,
      "database": "fms",
      "schema": "public",
      "username": "reader",
      "password": "encrypted_or_plain"
    },
    "snowflake": {
      "account": "ZJAUJWQ-EP12783",
      "database": "dev_edge_bronze",
      "schema": "storedge_fms_public",
      "username": "analyst@company.com",
      "password": "encrypted_or_plain",
      "warehouse": "COMPUTE_WH",
      "role": "DATA_ENGINEER"
    },
    "created_at": "2024-08-12T14:00:00"
  }
}
```

**Creating a Profile:**
1. **After a successful validation run:**
   ```
   Save this connection as a reusable profile? [y/N]: y
   Profile name (e.g. fms-dev): fms-dev
   ✓ Profile 'fms-dev' saved to ~/.migration-validator/profiles.json
   ```

2. **Using the CLI:**
   ```bash
   python validate_cli.py profiles
   → [1] List profiles
   → [2] Create profile
   → [3] Delete profile
   ```

**Using a Profile:**
```bash
# Single table with profile
python validate_cli.py generate \
    --connection-profile fms-dev \
    --pg-table customers \
    --sf-table CUSTOMERS

# Multi-table with profile
python validate_cli.py multi \
    --connection-profile fms-dev \
    --tables customers,orders,products
```

### 7.3 Connection Testing

**Built-In Connection Diagnostics:**
```bash
python src/validate_cli.py connections
```

**What This Tests:**
- ✓ Can connect to each source database
- ✓ Can authenticate with provided credentials
- ✓ Can read table list from each schema
- ✓ Can connect to Snowflake target
- ✓ Counts tables in each connection

**Sample Output:**
```
╔══════════════════════════════════════════════════════════════════╗
║  🔌  CONNECTION REGISTRY                                         ║
╚══════════════════════════════════════════════════════════════════╝

Source Connections  (3 configured)

  Slot    Type                Host                    Port  Database            Schema        Status
  ──────────────────────────────────────────────────────────────────────────────────────────────────
  SRC_1   PostgreSQL          db-dev.internal         5432  fms                 public        ✓ OK  15 tables
  SRC_2   MS SQL Server       sql-server.corp.local   1433  CRM                 dbo           ✓ OK  42 tables
  SRC_3   AWS Athena          us-east-1               443   migration_test      migration     ✓ OK  8 tables

Snowflake Target
  ──────────────────────────────────────────────────────────────────────────────────────────────────
  TARGET  Snowflake           ZJAUJWQ-EP12783                 dev_edge_bronze     storedge      ✓ OK  87 tables
```

**If a Connection Fails:**
```
  SRC_2   MS SQL Server       sql-server.corp.local   1433  CRM                 dbo           ✗ FAIL  Login failed for user 'user123'

Troubleshooting:
  • Check SOURCE_* vars in .env for SRC_2
  • Verify username/password are correct
  • For Windows Auth, use: domain\username
  • Check firewall allows port 1433
  • Run: python validate_cli.py setup  to reconfigure
```

### 7.4 AWS Athena Special Configuration

**Athena Differences from Traditional Databases:**
- No traditional "host:port" connection
- Uses **AWS Glue Data Catalog** for schema metadata
- Queries stored data in **S3 buckets**
- Authentication via **IAM credentials** or **IAM role**

**Required Athena Settings:**
```bash
SRC_3_TYPE=athena
SRC_3_HOST=us-east-1             # AWS region (not a server hostname)
SRC_3_DATABASE=my_glue_database  # Glue database name
SRC_3_SCHEMA=my_glue_database    # Same as database for Athena
SRC_3_USERNAME=AKIAIOSFODNN7EXAMPLE      # AWS Access Key ID
SRC_3_PASSWORD=wJalrXUtnFEMI/K7MDENG/... # AWS Secret Access Key

# Athena-specific globals (shared across all Athena connections)
ATHENA_S3_OUTPUT=s3://my-bucket/athena-results/  # REQUIRED
ATHENA_CATALOG=AwsDataCatalog
ATHENA_WORKGROUP=primary
```

**Authentication Options:**

**Option A: IAM User (Access Key Pair)**
```bash
SRC_3_USERNAME=AKIAIOSFODNN7EXAMPLE
SRC_3_PASSWORD=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**Option B: IAM Role (EC2 Instance Profile)**
```bash
SRC_3_USERNAME=  # Leave blank
SRC_3_PASSWORD=  # Leave blank
```
The tool will automatically use the EC2 instance's IAM role.

**Required IAM Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "glue:GetDatabase",
        "glue:GetTable",
        "glue:GetTables",
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:athena:us-east-1:123456789012:workgroup/primary",
        "arn:aws:glue:us-east-1:123456789012:catalog",
        "arn:aws:glue:us-east-1:123456789012:database/my_glue_database",
        "arn:aws:glue:us-east-1:123456789012:table/my_glue_database/*",
        "arn:aws:s3:::my-bucket/athena-results/*"
      ]
    }
  ]
}
```

**Athena Metadata Extraction:**
- **Table list:** AWS Glue API `list_tables()` — instant
- **Column list:** Athena SQL `DESCRIBE TABLE` — ~5-10 seconds per table
- **Future optimization:** Use Glue API `get_table()` instead of SQL (instant)

---

**[Continue to Part 2 for: Matching Pipeline, AI Integration, SQL Generation, CLI Usage, Troubleshooting, and Advanced Topics]**
