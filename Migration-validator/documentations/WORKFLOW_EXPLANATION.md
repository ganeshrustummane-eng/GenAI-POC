# Migration Validation Workflow - Complete Explanation

## 📊 Your Current Setup

### SOURCE DATABASE (PostgreSQL - test_bd)
```
Database: test_bd
Schema: source_data
Tables:
  ✅ users           (10 rows)
  ✅ customers       (10 rows)
  ✅ products        (10 rows)
  ✅ orders          (10 rows)
  ✅ transactions    (12 rows)
```

**Data already exists in PostgreSQL!** ✓

---

### TARGET DATABASE (Snowflake - NEEDS SETUP)
```
Database: snowflake_db
Schema: target_schema
Tables:
  ❌ USERS          (needs to be created + populated)
  ❌ CUSTOMERS      (needs to be created + populated)
  ❌ PRODUCTS       (needs to be created + populated)
  ❌ ORDERS         (needs to be created + populated)
  ❌ TRANSACTIONS   (needs to be created + populated)
```

**You need to migrate data here before validation!**

---

## 🔄 HOW VALIDATION WORKS

### Step 1: Define Source & Target Details
```python
source = {
    "database": "test_bd",
    "schema": "source_data",
    "tables": ["users", "customers", "products", "orders", "transactions"]
}

target = {
    "database": "snowflake_db",
    "schema": "target_schema",
    "tables": ["USERS", "CUSTOMERS", "PRODUCTS", "ORDERS", "TRANSACTIONS"]
}
```

### Step 2: Define Column Mappings with Transformation Rules
```python
# Example: Users table
ColumnMapping(
    source_column="is_active",
    target_column="IS_ACTIVE",
    source_data_type="BOOLEAN",
    target_data_type="BOOLEAN",
    apply_rules=[TransformationRuleType.BOOLEAN_CONVERSION]
),
ColumnMapping(
    source_column="status",
    target_column="STATUS",
    source_data_type="VARCHAR",
    target_data_type="VARCHAR",
    apply_rules=[TransformationRuleType.CASE_INSENSITIVE]
),
```

### Step 3: Validation Tool Generates SQL Queries

**The framework generates queries for each table:**

#### Query A: Row Count Comparison
```sql
-- SOURCE
SELECT COUNT(*) as row_count FROM source_data.users;

-- TARGET
SELECT COUNT(*) as row_count FROM snowflake_db.target_schema.USERS;
```

#### Query B: Data Extraction with Transformation Rules Applied
```sql
-- SOURCE (PostgreSQL)
SELECT 
    user_id AS user_id_normalized,
    LOWER(status) AS status_normalized,           -- Case Insensitive
    CASE 
        WHEN is_active = true THEN 'TRUE'          -- Boolean Conversion
        WHEN is_active = false THEN 'FALSE'
        ELSE 'NULL'
    END AS is_active_normalized,
    ROW_NUMBER() OVER (ORDER BY user_id) as rn,
    CURRENT_TIMESTAMP as extracted_at
FROM source_data.users
ORDER BY user_id;

-- TARGET (Snowflake)
SELECT 
    USER_ID AS USER_ID_normalized,
    LOWER(STATUS) AS STATUS_normalized,           -- Same Rule
    CASE 
        WHEN IS_ACTIVE = TRUE THEN 'TRUE'          -- Same Rule
        WHEN IS_ACTIVE = FALSE THEN 'FALSE'
        ELSE 'NULL'
    END AS IS_ACTIVE_normalized,
    ROW_NUMBER() OVER (ORDER BY USER_ID) as rn,
    CURRENT_TIMESTAMP() as extracted_at
FROM snowflake_db.target_schema.USERS
ORDER BY USER_ID;
```

### Step 4: Execute Queries & Compare Results

```
SOURCE Query Results        TARGET Query Results
───────────────────────    ───────────────────────
user_id | status | active | USER_ID | STATUS | ACTIVE
1       | active | TRUE   | 1       | ACTIVE | TRUE    ✓ MATCH
2       | active | FALSE  | 2       | ACTIVE | FALSE   ✓ MATCH
3       | active | TRUE   | 3       | ACTIVE | TRUE    ✓ MATCH
```

### Step 5: Generate Report

```
Validation Report:
  Overall Status: PASS ✓
  Data Completeness: 100%
  
  Table: users
    Status: PASS
    Source Rows: 10
    Target Rows: 10
    Matched Rows: 10
    Completeness: 100%
    
  Columns:
    ✓ user_id: 10/10 matched
    ✓ status: 10/10 matched (CASE_INSENSITIVE applied)
    ✓ is_active: 10/10 matched (BOOLEAN_CONVERSION applied)
```

---

## ⚙️ TRANSFORMATION RULES APPLIED

### What They Do

| Rule | Source | Target | Example |
|------|--------|--------|---------|
| **BOOLEAN_CONVERSION** | BIT/INT (0/1) | BOOLEAN | 0 → FALSE ✓ |
| **CASE_INSENSITIVE** | 'ACTIVE' | 'active' | Lowercase both ✓ |
| **WHITESPACE_TRIM** | ' John ' | 'John' | Trim spaces ✓ |
| **NULL_STANDARDIZATION** | NULL | NULL | Treat same ✓ |
| **NUMERIC_PRECISION** | 100 | 100.00 | Round to 2 decimals ✓ |
| **DATE_STANDARDIZATION** | Any format | YYYY-MM-DD | Standardize ✓ |
| **EMPTY_STRING_NULL** | '' | NULL | Treat equivalent ✓ |

---

## 📋 YOUR TASK BREAKDOWN

### PHASE 1: Setup Snowflake Target ⚙️

**What to do:**
1. Create schema in Snowflake
2. Create table structures matching source
3. Migrate/populate data from PostgreSQL to Snowflake

**How:**
```sql
-- In Snowflake Web UI:

-- 1. Create database
CREATE DATABASE snowflake_db;

-- 2. Create schema
CREATE SCHEMA snowflake_db.target_schema;

-- 3. Create USERS table (matching PostgreSQL structure)
CREATE TABLE snowflake_db.target_schema.USERS (
    USER_ID NUMBER PRIMARY KEY,
    USERNAME VARCHAR,
    EMAIL VARCHAR,
    IS_ACTIVE BOOLEAN,
    CREATED_AT TIMESTAMP,
    LAST_LOGIN TIMESTAMP,
    STATUS VARCHAR
);

-- 4. Similar for CUSTOMERS, PRODUCTS, ORDERS, TRANSACTIONS
-- 5. Populate with migrated data
```

### PHASE 2: Configure Validation Tool ✏️

**You provide:**
- Source database: `test_bd` in PostgreSQL
- Source schema: `source_data`
- Target database: `snowflake_db` in Snowflake
- Target schema: `target_schema`
- Table names and column mappings

**Tool does:**
- ✅ Generates SQL for both source and target
- ✅ Applies transformation rules automatically
- ✅ Executes queries
- ✅ Compares normalized data
- ✅ Generates validation report

### PHASE 3: Run Validation 🚀

```python
# In src/main_example.py

source_config = DatabaseConfig(
    database_type=DatabaseType.POSTGRESQL,
    host="localhost",
    port=5432,
    database="test_bd",           # ← Your source DB
    username="postgres",
    password="12345",
    schema="source_data",          # ← Your source schema
    timeout=30
)

target_config = DatabaseConfig(
    database_type=DatabaseType.SNOWFLAKE,
    host="ZJAUJWQ-EP12783",       # ← Your Snowflake account
    port=443,
    database="snowflake_db",       # ← Your target DB
    username="MANEGANESH99",
    password="Ganeshmane@999",
    schema="target_schema",        # ← Your target schema
    timeout=30
)

# Define table and column mappings
table_mappings = [
    TableMapping(
        source_table="users",
        target_table="USERS",
        column_mappings=[...],     # ← Define which rules to apply
        description="Validate users migration"
    ),
    # ... repeat for customers, products, orders, transactions
]

# Run validation
validator = DataValidator(config)
report = validator.run_validation()
```

---

## 📊 WHAT THE TOOL OUTPUTS

### 1. SQL Queries (Generated)
```
✓ query_users_row_count_source
✓ query_users_row_count_target
✓ query_users_data_source
✓ query_users_data_target
✓ query_customers_row_count_source
✓ query_customers_row_count_target
... (and so on for all tables)
```

### 2. Validation Report

**HTML Report** (Beautiful Dashboard)
```
┌─────────────────────────────────────────┐
│   MIGRATION VALIDATION REPORT            │
│   Status: PASS ✓                         │
│   Data Completeness: 100%                │
└─────────────────────────────────────────┘

┌─ users (PASS) ─────────────────────────┐
│ 10 ✓ / 10 rows matched (100%)           │
└─────────────────────────────────────────┘

┌─ customers (PASS) ─────────────────────┐
│ 10 ✓ / 10 rows matched (100%)           │
└─────────────────────────────────────────┘
```

**JSON Report** (Machine Readable)
```json
{
  "validation_id": "abc123",
  "overall_status": "PASS",
  "overall_data_completeness_percentage": 100.0,
  "table_results": [
    {
      "table_name": "users",
      "status": "PASS",
      "source_rows": 10,
      "target_rows": 10,
      "matched_rows": 10,
      "data_completeness_percentage": 100.0
    }
  ]
}
```

**Text Report** (Human Readable)
```
================================================================================
MIGRATION VALIDATION REPORT
================================================================================

Overall Status: PASS
Data Completeness: 100.00%

Table: users
  Source Rows: 10
  Target Rows: 10
  Matched Rows: 10
  Status: PASS
```

---

## 🎯 NEXT STEPS

### Step 1: Create Snowflake Target Tables
```sql
-- Log into Snowflake
-- Copy SQL schema from source (adapt to Snowflake syntax)
-- Create database/schema/tables
-- Populate with migrated data
```

### Step 2: Configure main_example.py
```python
# Update database credentials (already done ✓)
# Add table mappings with transformation rules
# Specify which columns to validate
```

### Step 3: Run Validation
```powershell
python src/main_example.py
```

### Step 4: Review Report
```powershell
Start-Process "validation_reports\report_*.html"
```

---

## 💡 KEY POINTS

1. **Source Data Exists**: Your PostgreSQL has 5 tables with real data ✓
2. **Target Doesn't Exist**: You need to create tables and populate in Snowflake
3. **Tool is Ready**: Framework generates all queries automatically
4. **You Just Provide**: Source/target DB details + table/column mappings
5. **Tool Does**: Generates queries, applies rules, compares, reports

---

## 📁 SOURCE DATA REFERENCE

Your PostgreSQL source has these exact tables:

```
users (10 rows)
├── user_id (SERIAL)
├── username (VARCHAR)
├── email (VARCHAR)
├── is_active (BOOLEAN)
├── created_at (TIMESTAMP)
├── last_login (TIMESTAMP)
└── status (VARCHAR)

customers (10 rows)
├── customer_id (SERIAL)
├── customer_name (VARCHAR)
├── company_name (VARCHAR)
├── phone (VARCHAR)
├── balance (NUMERIC)
├── credit_limit (NUMERIC)
├── registration_date (DATE)
└── tier (VARCHAR)

products (10 rows)
orders (10 rows)
transactions (12 rows)
```

---

## ✅ WORKFLOW COMPLETE

```
PostgreSQL (source_data)     Validation Tool        Snowflake (target_schema)
       ↓                            ↓                           ↓
    5 Tables            Generate SQL Queries        Create 5 Tables
    52 Rows            Apply Transformation Rules   Populate Data
   (EXISTS)            Compare Normalized Results      (YOU CREATE)
                       Generate HTML/JSON Report
                              ↓
                       Validation Report
                       (HTML, JSON, Text)
```

Now you're ready to set up Snowflake and run validation! 🚀
