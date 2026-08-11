# Step-by-Step Guide: Test Connectors & Validate Migration

## 🎯 Goal
Verify that both PostgreSQL and Snowflake connectors work, then feed sample data to Snowflake and run validation.

---

## 📋 STEP 1: Verify PostgreSQL Source Database

### Step 1.1: Check PostgreSQL is Running
```powershell
# Test PostgreSQL connection
psql -U postgres -c "SELECT version();"
```

**Expected Output:**
```
PostgreSQL 15.x on ...
```

### Step 1.2: List Available Databases
```powershell
psql -U postgres -l
```

**Look for:** A database containing your source data (e.g., `postgres`, `test_db`, `migration_source`)

### Step 1.3: Check Source Schema & Tables
```powershell
# Connect to your database
psql -U postgres -d postgres

# Then run these commands:
\dn                                          # List schemas
\dt source_data.*                            # List tables in source_data schema
SELECT COUNT(*) FROM source_data.users;      # Check users table
SELECT COUNT(*) FROM source_data.customers;  # Check customers table
```

**Expected Output:**
```
 count
-------
    10
(1 row)
```

---

## 🔧 STEP 2: Create Target Tables in Snowflake

### Step 2.1: Log Into Snowflake

Go to: `https://ZJAUJWQ-EP12783.ap-southeast-7.snowflakecomputing.com`

**Credentials from your account:**
- Account: `ZJAUJWQ-EP12783`
- Username: `MANEGANESH99`
- Password: `Ganeshmane@999`

### Step 2.2: Create Database & Schema

In Snowflake Web UI, run these SQL commands:

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS snowflake_db;

-- Create schema
CREATE SCHEMA IF NOT EXISTS snowflake_db.target_schema;

-- Set as active
USE DATABASE snowflake_db;
USE SCHEMA target_schema;
```

### Step 2.3: Create USERS Table

```sql
CREATE TABLE IF NOT EXISTS target_schema.USERS (
    USER_ID NUMBER PRIMARY KEY,
    USERNAME VARCHAR,
    EMAIL VARCHAR,
    IS_ACTIVE BOOLEAN,
    STATUS VARCHAR,
    CREATED_AT TIMESTAMP,
    UPDATED_AT TIMESTAMP
);
```

### Step 2.4: Create CUSTOMERS Table

```sql
CREATE TABLE IF NOT EXISTS target_schema.CUSTOMERS (
    CUSTOMER_ID NUMBER PRIMARY KEY,
    CUSTOMER_NAME VARCHAR,
    BALANCE NUMERIC(12,2),
    REGISTRATION_DATE DATE
);
```

### Step 2.5: Verify Tables Created

```sql
SHOW TABLES IN snowflake_db.target_schema;

-- Should show:
-- USERS
-- CUSTOMERS
```

---

## 📥 STEP 3: Load Sample Data into Snowflake

### Step 3.1: Insert Data into USERS Table

In Snowflake, run:

```sql
USE DATABASE snowflake_db;
USE SCHEMA target_schema;

INSERT INTO USERS (USER_ID, USERNAME, EMAIL, IS_ACTIVE, STATUS, CREATED_AT, UPDATED_AT) VALUES
(1, 'john_doe', 'john.doe@example.com', TRUE, 'ACTIVE', '2025-01-15 10:30:00', '2026-08-05 10:30:00'),
(2, 'jane_smith', 'jane.smith@example.com', FALSE, 'INACTIVE', '2025-02-20 09:15:00', '2026-08-05 09:15:00'),
(3, 'bob_wilson', 'bob.wilson@example.com', TRUE, 'ACTIVE', '2025-03-10 11:45:00', '2026-08-05 11:45:00'),
(4, 'alice_johnson', 'alice.j@example.com', TRUE, 'ACTIVE', '2025-04-05 13:20:00', '2026-08-05 13:20:00'),
(5, 'charlie_brown', 'charlie.brown@example.com', FALSE, 'SUSPENDED', '2025-05-18 15:10:00', '2026-08-05 15:10:00'),
(6, 'diana_prince', 'diana.prince@example.com', TRUE, 'ACTIVE', '2025-06-22 12:00:00', '2026-08-05 12:00:00'),
(7, 'evan_davis', NULL, TRUE, 'ACTIVE', '2025-07-12 14:30:00', '2026-08-05 14:30:00'),
(8, 'fiona_green', 'fiona.green@example.com', FALSE, 'INACTIVE', '2025-08-08 08:45:00', '2026-08-05 08:45:00'),
(9, 'george_harris', 'george.h@example.com', TRUE, 'ACTIVE', '2025-09-01 08:00:00', '2026-08-05 08:00:00'),
(10, 'hannah_clark', 'hannah.clark@example.com', TRUE, 'ACTIVE', '2025-10-14 10:30:00', '2026-08-05 10:30:00');

-- Verify data inserted
SELECT COUNT(*) FROM USERS;
SELECT * FROM USERS LIMIT 5;
```

### Step 3.2: Insert Data into CUSTOMERS Table

```sql
INSERT INTO CUSTOMERS (CUSTOMER_ID, CUSTOMER_NAME, BALANCE, REGISTRATION_DATE) VALUES
(101, 'Acme Corp', 15000.50, '2024-01-15'),
(102, 'TechStart Inc', 25000.00, '2024-02-20'),
(103, 'Global Solutions', 50000.75, '2024-03-10'),
(104, 'Innovation Labs', 35000.25, '2024-04-05'),
(105, 'Digital Ventures', 40000.00, '2024-05-18');

-- Verify data inserted
SELECT COUNT(*) FROM CUSTOMERS;
SELECT * FROM CUSTOMERS;
```

### Step 3.3: Verify All Data

```sql
-- Check record counts
SELECT 'USERS' as table_name, COUNT(*) as row_count FROM USERS
UNION ALL
SELECT 'CUSTOMERS' as table_name, COUNT(*) as row_count FROM CUSTOMERS;

-- Check for NULL values
SELECT * FROM USERS WHERE EMAIL IS NULL;
```

**Expected Output:**
```
TABLE_NAME    ROW_COUNT
-----------   ---------
USERS         10
CUSTOMERS     5
```

---

## 🧪 STEP 4: Test PostgreSQL Connector

### Step 4.1: Create Test Script

Create file: `test_postgres_connector.py`

```python
import sys
sys.path.insert(0, 'src')

from models import DatabaseType, DatabaseConfig
from database_connectors import ConnectorFactory

# Configure PostgreSQL connection
config = DatabaseConfig(
    database_type=DatabaseType.POSTGRESQL,
    host="localhost",
    port=5432,
    database="postgres",  # Your database name
    username="postgres",
    password="12345",
    schema="source_data",
    timeout=30
)

# Test connection
factory = ConnectorFactory()
connector = factory.create_connector(config)

print("Testing PostgreSQL Connection...")
print("-" * 80)

# Test 1: Connection
if connector.test_connection():
    print("✅ PostgreSQL connection successful!")
else:
    print("✗ PostgreSQL connection failed!")
    sys.exit(1)

# Test 2: Read from users table
print("\nTesting data retrieval from USERS...")
query = "SELECT COUNT(*) as count FROM source_data.users"
result = connector.execute_query(query)
if result.error:
    print(f"✗ Error: {result.error}")
else:
    print(f"✅ Row count: {result.row_count}")
    print(f"   Data: {result.rows}")

# Test 3: Read from customers table
print("\nTesting data retrieval from CUSTOMERS...")
query = "SELECT COUNT(*) as count FROM source_data.customers"
result = connector.execute_query(query)
if result.error:
    print(f"✗ Error: {result.error}")
else:
    print(f"✅ Row count: {result.row_count}")
    print(f"   Data: {result.rows}")

print("\n" + "=" * 80)
print("PostgreSQL Connector Test Complete!")
print("=" * 80)

connector.disconnect()
```

### Step 4.2: Run Test

```powershell
cd c:\EPAM-Personal\Migration-validator
python test_postgres_connector.py
```

**Expected Output:**
```
Testing PostgreSQL Connection...
--------------------------------------------------------------------------------
✅ PostgreSQL connection successful!

Testing data retrieval from USERS...
✅ Row count: 1
   Data: [{'count': 10}]

Testing data retrieval from CUSTOMERS...
✅ Row count: 1
   Data: [{'count': 5}]

================================================================================
PostgreSQL Connector Test Complete!
================================================================================
```

---

## 🔐 STEP 5: Test Snowflake Connector

### Step 5.1: Create Test Script

Create file: `test_snowflake_connector.py`

```python
import sys
sys.path.insert(0, 'src')

from models import DatabaseType, DatabaseConfig
from database_connectors import ConnectorFactory

# Configure Snowflake connection
config = DatabaseConfig(
    database_type=DatabaseType.SNOWFLAKE,
    host="ZJAUJWQ-EP12783",  # Your account ID
    port=443,
    database="snowflake_db",
    username="MANEGANESH99",
    password="Ganeshmane@999",
    schema="target_schema",
    timeout=30
)

# Test connection
factory = ConnectorFactory()
connector = factory.create_connector(config)

print("Testing Snowflake Connection...")
print("-" * 80)

# Test 1: Connection
if connector.test_connection():
    print("✅ Snowflake connection successful!")
else:
    print("✗ Snowflake connection failed!")
    sys.exit(1)

# Test 2: Read from USERS table
print("\nTesting data retrieval from USERS...")
query = "SELECT COUNT(*) as count FROM target_schema.USERS"
result = connector.execute_query(query)
if result.error:
    print(f"✗ Error: {result.error}")
else:
    print(f"✅ Row count: {result.row_count}")
    print(f"   Data: {result.rows}")

# Test 3: Read from CUSTOMERS table
print("\nTesting data retrieval from CUSTOMERS...")
query = "SELECT COUNT(*) as count FROM target_schema.CUSTOMERS"
result = connector.execute_query(query)
if result.error:
    print(f"✗ Error: {result.error}")
else:
    print(f"✅ Row count: {result.row_count}")
    print(f"   Data: {result.rows}")

print("\n" + "=" * 80)
print("Snowflake Connector Test Complete!")
print("=" * 80)

connector.disconnect()
```

### Step 5.2: Run Test

```powershell
python test_snowflake_connector.py
```

**Expected Output:**
```
Testing Snowflake Connection...
--------------------------------------------------------------------------------
✅ Snowflake connection successful!

Testing data retrieval from USERS...
✅ Row count: 1
   Data: [{'COUNT': 10}]

Testing data retrieval from CUSTOMERS...
✅ Row count: 1
   Data: [{'COUNT': 5}]

================================================================================
Snowflake Connector Test Complete!
================================================================================
```

---

## ✅ STEP 6: Run Full Validation

### Step 6.1: Verify Configuration in main_example.py

Open `src/main_example.py` and ensure:

```python
source_config = DatabaseConfig(
    database_type=DatabaseType.POSTGRESQL,
    host="localhost",
    port=5432,
    database="postgres",  # ← Must match your actual PostgreSQL database
    username="postgres",
    password="12345",
    schema="source_data",
    timeout=30
)

target_config = DatabaseConfig(
    database_type=DatabaseType.SNOWFLAKE,
    host="ZJAUJWQ-EP12783",  # ← Your account ID
    port=443,
    database="snowflake_db",
    username="MANEGANESH99",
    password="Ganeshmane@999",
    schema="target_schema",
    timeout=30
)
```

### Step 6.2: Run Validator

```powershell
python src/main_example.py
```

### Step 6.3: Expected Output

```
================================================================================
🚀 MIGRATION VALIDATOR - PROOF OF CONCEPT
================================================================================

================================================================================
CHECKING AVAILABLE POSTGRESQL DATABASES
================================================================================

Available databases:
  • postgres
  • template0
  • template1

📋 Configuration Loaded:
  Source: PostgreSQL://postgres@localhost:5432/postgres
  Target: Snowflake://MANEGANESH99@ZJAUJWQ-EP12783:443/snowflake_db
  Tables to validate: 2

[SQL Queries Generated...]

================================================================================
RUNNING FULL VALIDATION (With Database Execution)
================================================================================

Validation ID: abc123def456
Overall Status: PASS
Data Completeness: 100.00%
Success Rate: 100.00%

Table Results:
  users: PASS (100.0%)
  customers: PASS (100.0%)

================================================================================
EXPORTING REPORTS
================================================================================

✓ JSON report written to: validation_reports\report_20260805_152954.json
✓ HTML report written to: validation_reports\report_20260805_152954.html
✓ Text report written to: validation_reports\report_20260805_152954.txt

✅ Validation complete! Open: validation_reports/report_20260805_152954.html
```

---

## 📊 STEP 7: Review Validation Report

### Step 7.1: View HTML Report

```powershell
# Open the HTML report in default browser
Start-Process "validation_reports\report_*.html"
```

### Step 7.2: View JSON Report

```powershell
# View JSON in VS Code
code "validation_reports\report_*.json"
```

### Step 7.3: Check Text Report

```powershell
# View text report
Get-Content "validation_reports\report_*.txt"
```

---

## 🐛 TROUBLESHOOTING

### PostgreSQL Connection Error
```
✗ Failed to connect to PostgreSQL: database "postgres" does not exist
```

**Solution:**
1. Check available databases: `psql -U postgres -l`
2. Update `database` in `create_example_config()`
3. Ensure schema `source_data` exists in that database

### Snowflake Connection Error
```
✗ Failed to connect to Snowflake: Invalid username/password
```

**Solution:**
1. Verify credentials:
   - Account: ZJAUJWQ-EP12783
   - Username: MANEGANESH99 (uppercase)
   - Password: Ganeshmane@999
2. Check if user is active in Snowflake (Snowflake UI → Admin → Users)
3. Verify password hasn't changed

### Table Not Found
```
✗ relation/table does not exist
```

**Solution:**
1. Verify table names match case-sensitivity rules:
   - PostgreSQL: lowercase (users, customers)
   - Snowflake: uppercase (USERS, CUSTOMERS)
2. Check schema exists: `\dn` (PostgreSQL) or `SHOW SCHEMAS` (Snowflake)

### Data Mismatch in Validation
```
Overall Status: FAIL
Data Completeness: 50.00%
```

**Solution:**
1. Check row counts match: `SELECT COUNT(*) FROM ...`
2. Check for NULL values and whitespace differences
3. Review HTML report for column-level mismatches
4. Verify transformation rules are correct

---

## ✨ Success Checklist

- [ ] PostgreSQL connection test passes
- [ ] Snowflake connection test passes
- [ ] USERS table exists in Snowflake with 10 rows
- [ ] CUSTOMERS table exists in Snowflake with 5 rows
- [ ] Validation runs without errors
- [ ] Overall Status shows "PASS"
- [ ] Data Completeness shows "100.00%"
- [ ] HTML/JSON/Text reports generated

---

## 📞 Next Steps

Once validation passes:

1. **Update with real migration data** - Replace sample data with actual migrated data
2. **Adjust transformation rules** - If data doesn't match, tweak rules
3. **Schedule regular validations** - Automate checks for ongoing migration monitoring
4. **Document results** - Keep reports for audit trail

Good luck! 🚀
