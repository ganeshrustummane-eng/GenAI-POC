# Snowflake Target Setup & Validation Guide

## 📊 Current Status

```
✅ SOURCE (PostgreSQL - test_bd)
   - Database: test_bd
   - Schema: source_data
   - Tables: users (10), customers (10), products (10), orders (10), transactions (12)
   - Status: READY

❌ TARGET (Snowflake)
   - Database: snowflake_db (needs setup)
   - Schema: target_schema (needs setup)
   - Tables: NOT CREATED YET
   - Status: NEEDS SETUP
```

---

## 🎯 Setup Workflow

```
Step 1: Create Snowflake Target Tables
        ↓
Step 2: Populate with Sample Data
        ↓
Step 3: Configure Validation Tool
        ↓
Step 4: Run Validation
        ↓
Step 5: Review Reports
```

---

## ⚙️ STEP 1: Create Snowflake Target Tables (5 minutes)

### 1.1 Log into Snowflake

Open your browser and go to:
```
https://ZJAUJWQ-EP12783.ap-southeast-7.snowflakecomputing.com
```

Login with:
```
Username: MANEGANESH99
Password: Ganeshmane@999
```

### 1.2 Create New Worksheet

- Click the **+ Worksheet** button at the top
- Name it: "Migration Target Setup"

### 1.3 Copy & Execute Schema Creation SQL

1. Open file: `snowflake_target_schema.sql`
2. Copy all contents
3. Paste into Snowflake worksheet
4. Select all (Ctrl+A)
5. Execute (Ctrl+Enter)

**Expected Output:**
```
┌──────────────────────────────┐
│     Database created         │
│     Schema created           │
│     Table USERS created      │
│     Table CUSTOMERS created  │
│     Table PRODUCTS created   │
│     Table ORDERS created     │
│     Table TRANSACTIONS created
└──────────────────────────────┘
```

### 1.4 Verify Tables

```sql
SHOW TABLES IN snowflake_db.target_schema;
```

Should show all 5 tables:
```
CUSTOMERS
ORDERS
PRODUCTS
TRANSACTIONS
USERS
```

---

## 📥 STEP 2: Populate with Sample Data (2 minutes)

### 2.1 Copy Sample Data SQL

1. Open file: `snowflake_sample_data.sql`
2. Copy all contents
3. Paste into a NEW Snowflake worksheet
4. Execute (Ctrl+A then Ctrl+Enter)

**Expected Output:**
```
10 rows inserted into USERS
10 rows inserted into CUSTOMERS
10 rows inserted into PRODUCTS
10 rows inserted into ORDERS
12 rows inserted into TRANSACTIONS
```

### 2.2 Verify Data Insertion

Run this verification query:
```sql
USE DATABASE snowflake_db;
USE SCHEMA target_schema;

SELECT 'USERS' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM USERS
UNION ALL
SELECT 'CUSTOMERS', COUNT(*) FROM CUSTOMERS
UNION ALL
SELECT 'PRODUCTS', COUNT(*) FROM PRODUCTS
UNION ALL
SELECT 'ORDERS', COUNT(*) FROM ORDERS
UNION ALL
SELECT 'TRANSACTIONS', COUNT(*) FROM TRANSACTIONS;
```

**Expected Output:**
```
TABLE_NAME    | ROW_COUNT
-----------   | ---------
CUSTOMERS     | 10
ORDERS        | 10
PRODUCTS      | 10
TRANSACTIONS  | 12
USERS         | 10
```

---

## ✏️ STEP 3: Configure Validation Tool (5 minutes)

### 3.1 Edit Configuration

Open: `src/main_example.py`

Update the `create_example_config()` function:

```python
# SOURCE (PostgreSQL) - Already correct
source_config = DatabaseConfig(
    database_type=DatabaseType.POSTGRESQL,
    host="localhost",
    port=5432,
    database="test_bd",        # ✓ Correct
    username="postgres",
    password="12345",
    schema="source_data",      # ✓ Correct
    timeout=30
)

# TARGET (Snowflake) - Update these
target_config = DatabaseConfig(
    database_type=DatabaseType.SNOWFLAKE,
    host="ZJAUJWQ-EP12783",    # ✓ Your account ID
    port=443,
    database="snowflake_db",   # ✓ Database you created
    username="MANEGANESH99",   # ✓ Your username
    password="Ganeshmane@999",
    schema="target_schema",    # ✓ Schema you created
    timeout=30
)
```

### 3.2 Define Table Mappings

Below the config, add table mappings (already done in main_example.py):

```python
# Example mapping for USERS table
users_column_mappings = [
    ColumnMapping(
        source_column="user_id",
        target_column="USER_ID",
        source_data_type="SERIAL",
        target_data_type="NUMBER",
        primary_key=True
    ),
    ColumnMapping(
        source_column="username",
        target_column="USERNAME",
        source_data_type="VARCHAR(100)",
        target_data_type="VARCHAR",
        apply_rules=[TransformationRuleType.CASE_INSENSITIVE, TransformationRuleType.WHITESPACE_TRIM]
    ),
    ColumnMapping(
        source_column="is_active",
        target_column="IS_ACTIVE",
        source_data_type="BOOLEAN",
        target_data_type="BOOLEAN",
        apply_rules=[TransformationRuleType.BOOLEAN_CONVERSION]
    ),
    # ... more columns
]
```

---

## 🚀 STEP 4: Run Validation (2 minutes)

### 4.1 Execute Validation

```powershell
cd c:\EPAM-Personal\Migration-validator

python src/main_example.py
```

### 4.2 Expected Output

```
================================================================================
🚀 MIGRATION VALIDATOR - PROOF OF CONCEPT
================================================================================

Configuration Loaded:
  Source: PostgreSQL://postgres@localhost:5432/test_bd
  Target: Snowflake://MANEGANESH99@ZJAUJWQ-EP12783:443/snowflake_db
  Tables to validate: 5

[SQL Queries generated for: users, customers, products, orders, transactions]

================================================================================
RUNNING FULL VALIDATION
================================================================================

Validation ID: abc123def456
Overall Status: PASS
Data Completeness: 100.00%
Success Rate: 100.00%

Table Results:
  users: PASS (100.0%)
  customers: PASS (100.0%)
  products: PASS (100.0%)
  orders: PASS (100.0%)
  transactions: PASS (100.0%)

✓ JSON report written to: validation_reports\report_20260805_143000.json
✓ HTML report written to: validation_reports\report_20260805_143000.html
✓ Text report written to: validation_reports\report_20260805_143000.txt

✅ Validation complete! Open: validation_reports/report_20260805_143000.html
```

---

## 📊 STEP 5: Review Reports (1 minute)

### 5.1 View HTML Report (Best for overview)

```powershell
Start-Process "validation_reports\report_*.html"
```

You'll see a beautiful dashboard showing:
- ✅ Overall Status: PASS
- 📊 Data Completeness: 100%
- 📈 Per-table results
- 🔍 Per-column validation

### 5.2 View JSON Report (Best for parsing)

```powershell
code "validation_reports\report_*.json"
```

Machine-readable format with complete details.

### 5.3 View Text Report (Best for quick review)

```powershell
Get-Content "validation_reports\report_*.txt"
```

Human-readable summary.

---

## 📋 Data Mapping Reference

### USERS Table
| PostgreSQL | Snowflake | Transformation Rules |
|-----------|-----------|---------------------|
| user_id | USER_ID | (primary key, no transform) |
| username | USERNAME | CASE_INSENSITIVE, WHITESPACE_TRIM |
| email | EMAIL | WHITESPACE_TRIM |
| is_active | IS_ACTIVE | BOOLEAN_CONVERSION |
| created_at | CREATED_AT | (timestamp, no special rule) |
| last_login | LAST_LOGIN | (timestamp, nullable) |
| status | STATUS | CASE_INSENSITIVE |

### CUSTOMERS Table
| PostgreSQL | Snowflake | Transformation Rules |
|-----------|-----------|---------------------|
| customer_id | CUSTOMER_ID | (primary key) |
| customer_name | CUSTOMER_NAME | WHITESPACE_TRIM, CASE_INSENSITIVE |
| company_name | COMPANY_NAME | WHITESPACE_TRIM |
| phone | PHONE | WHITESPACE_TRIM |
| balance | BALANCE | NUMERIC_PRECISION (2 decimals) |
| credit_limit | CREDIT_LIMIT | NUMERIC_PRECISION |
| registration_date | REGISTRATION_DATE | DATE_STANDARDIZATION |
| tier | TIER | CASE_INSENSITIVE |

### PRODUCTS Table
| PostgreSQL | Snowflake | Transformation Rules |
|-----------|-----------|---------------------|
| product_id | PRODUCT_ID | (primary key) |
| product_code | PRODUCT_CODE | CASE_INSENSITIVE |
| product_name | PRODUCT_NAME | WHITESPACE_TRIM, CASE_INSENSITIVE |
| description | DESCRIPTION | EMPTY_STRING_NULL |
| category | CATEGORY | CASE_INSENSITIVE |
| unit_price | UNIT_PRICE | NUMERIC_PRECISION |
| stock_quantity | STOCK_QUANTITY | (integer, no rule) |
| reorder_level | REORDER_LEVEL | (integer, no rule) |
| discontinued | DISCONTINUED | BOOLEAN_CONVERSION |

### ORDERS Table
| PostgreSQL | Snowflake | Transformation Rules |
|-----------|-----------|---------------------|
| order_id | ORDER_ID | (primary key) |
| customer_id | CUSTOMER_ID | (foreign key) |
| order_date | ORDER_DATE | DATE_STANDARDIZATION |
| ship_date | SHIP_DATE | DATE_STANDARDIZATION, NULL_STANDARDIZATION |
| order_amount | ORDER_AMOUNT | NUMERIC_PRECISION |
| tax_amount | TAX_AMOUNT | NUMERIC_PRECISION |
| total_amount | TOTAL_AMOUNT | NUMERIC_PRECISION |
| order_status | ORDER_STATUS | CASE_INSENSITIVE |

### TRANSACTIONS Table
| PostgreSQL | Snowflake | Transformation Rules |
|-----------|-----------|---------------------|
| transaction_id | TRANSACTION_ID | (primary key) |
| user_id | USER_ID | (foreign key) |
| order_id | ORDER_ID | (foreign key, nullable) |
| transaction_type | TRANSACTION_TYPE | CASE_INSENSITIVE |
| transaction_amount | TRANSACTION_AMOUNT | NUMERIC_PRECISION |
| transaction_date | TRANSACTION_DATE | DATE_STANDARDIZATION |
| reference_number | REFERENCE_NUMBER | WHITESPACE_TRIM |
| remarks | REMARKS | NULL_STANDARDIZATION |

---

## ✅ Validation Checklist

Before running validation, verify:

- [ ] Snowflake tables created (5 tables)
- [ ] Sample data inserted (52 total rows)
- [ ] PostgreSQL source has data (10+10+10+10+12 rows)
- [ ] main_example.py configured with correct credentials
- [ ] Column mappings defined with transformation rules
- [ ] Transformation rules match your data (case, whitespace, null, etc.)

---

## 🔍 How Validation Actually Works

For each table, the tool:

1. **Generates Row Count Queries**
   ```sql
   SELECT COUNT(*) FROM source_data.users;
   SELECT COUNT(*) FROM snowflake_db.target_schema.USERS;
   ```

2. **Applies Transformation Rules**
   ```sql
   -- Source with transformations
   SELECT 
       user_id,
       LOWER(username),      -- CASE_INSENSITIVE
       CASE WHEN is_active = true THEN 'TRUE' ELSE 'FALSE' END  -- BOOLEAN_CONVERSION
   FROM source_data.users;
   
   -- Target with SAME transformations
   SELECT 
       USER_ID,
       LOWER(USERNAME),
       CASE WHEN IS_ACTIVE = TRUE THEN 'TRUE' ELSE 'FALSE' END
   FROM snowflake_db.target_schema.USERS;
   ```

3. **Compares Results Row-by-Row**
   ```
   Source Row 1: (1, 'john_doe', 'TRUE')
   Target Row 1: (1, 'john_doe', 'TRUE')
                          ↓ MATCH ✓
   ```

4. **Calculates Metrics**
   ```
   Total rows: 10
   Matched rows: 10
   Completeness: 100%
   ```

5. **Generates Reports**
   ```
   HTML, JSON, Text format with detailed results
   ```

---

## 🎯 Success = This Output

```
Overall Status: PASS ✓
Data Completeness: 100.00% ✓
Success Rate: 100.00% ✓

Table Results:
  users: PASS (100.0%)
  customers: PASS (100.0%)
  products: PASS (100.0%)
  orders: PASS (100.0%)
  transactions: PASS (100.0%)
```

---

## ⚠️ If Something Goes Wrong

### Error: Table not found
```
✗ relation/table does not exist
```
**Fix:** Run snowflake_target_schema.sql again

### Error: 0 rows in Snowflake
```
Overall Status: FAIL
Table users: 0/10 rows matched
```
**Fix:** Run snowflake_sample_data.sql again

### Error: Connection failed
```
✗ Failed to connect to Snowflake
```
**Fix:** Verify credentials in main_example.py

### Error: Data mismatch
```
Overall Status: FAIL
Data Completeness: 50%
```
**Fix:** Check transformation rules in config

---

## 📞 Next Steps After Validation

1. **If PASS (100%)** ✓
   - Validation successful!
   - Replace sample data with actual migrated data
   - Run validation on real data

2. **If FAIL (< 100%)**
   - Review HTML report for specific column mismatches
   - Check which rows don't match
   - Adjust transformation rules if needed
   - Re-run validation

---

## 🚀 Summary

```
1. Create Snowflake tables        (5 min)
2. Insert sample data             (2 min)
3. Configure validation tool      (5 min)
4. Run validation                 (2 min)
5. Review reports                 (1 min)
   ──────────────────────────────────
   Total time: 15 minutes!

Result: Data validation proof of concept complete! ✓
```

Now you're ready to:
- ✅ Validate data migration completeness
- ✅ Identify data discrepancies
- ✅ Track transformation rule application
- ✅ Generate audit reports

**Let's validate!** 🚀
