# Quick Start: Test & Validate Migration

## 🚀 TL;DR (5 Minutes)

```powershell
# 1. Check PostgreSQL databases
psql -U postgres -l

# 2. Test PostgreSQL connector
python test_postgres_connector.py

# 3. Setup Snowflake (copy-paste snowflake_setup.sql to Snowflake Web UI)
# Then test Snowflake connector
python test_snowflake_connector.py

# 4. Run full validation
python src/main_example.py

# 5. View results
Start-Process "validation_reports\report_*.html"
```

---

## 📋 STEP-BY-STEP

### ✅ Step 1: Check PostgreSQL (30 seconds)

List available databases:
```powershell
psql -U postgres -l
```

Find a database that has `source_data` schema with `users` and `customers` tables.

If unsure, connect and check:
```powershell
psql -U postgres -d postgres

# Inside psql:
\dn                           # Show schemas
\dt source_data.*             # Show tables in source_data
SELECT COUNT(*) FROM source_data.users;
```

**Then update this in src/main_example.py:**
```python
database="postgres"  # Change to your actual database name
```

---

### ✅ Step 2: Test PostgreSQL Connector (1 minute)

```powershell
cd c:\EPAM-Personal\Migration-validator

python test_postgres_connector.py
```

**Expected Output:**
```
Test 1: Connection
✅ PostgreSQL connection successful!

Test 2: Read USERS table
✅ Row count: 1
   Total users: 10

Test 3: Read CUSTOMERS table
✅ Row count: 1
   Total customers: 5

✅ POSTGRESQL CONNECTOR TEST COMPLETE - ALL TESTS PASSED!
```

---

### ✅ Step 3: Setup Snowflake (2 minutes)

1. **Open Snowflake Web UI:**
   ```
   https://ZJAUJWQ-EP12783.ap-southeast-7.snowflakecomputing.com
   ```

2. **Login:**
   - Username: `MANEGANESH99`
   - Password: `Ganeshmane@999`

3. **Create worksheet:**
   - Click `+ Worksheet` at top

4. **Copy & Paste:** All SQL from `snowflake_setup.sql`
   ```powershell
   # View the file
   notepad snowflake_setup.sql
   ```

5. **Execute:**
   - Select all (Ctrl+A)
   - Press Ctrl+Enter to run

6. **Verify:**
   - Should see:
     ```
     USERS     | 10
     CUSTOMERS | 5
     ```

---

### ✅ Step 4: Test Snowflake Connector (1 minute)

```powershell
python test_snowflake_connector.py
```

**Expected Output:**
```
Test 1: Connection
✅ Snowflake connection successful!

Test 2: Read USERS table
✅ Row count: 1
   Total users: 10

Test 3: Read CUSTOMERS table
✅ Row count: 1
   Total customers: 5

✅ SNOWFLAKE CONNECTOR TEST COMPLETE - ALL TESTS PASSED!
```

---

### ✅ Step 5: Run Full Validation (2 minutes)

```powershell
python src/main_example.py
```

**Expected Output:**
```
🚀 MIGRATION VALIDATOR - PROOF OF CONCEPT

Available databases:
  • postgres
  • template0
  • template1

Configuration Loaded:
  Source: PostgreSQL://postgres@localhost:5432/postgres
  Target: Snowflake://MANEGANESH99@ZJAUJWQ-EP12783:443/snowflake_db
  Tables to validate: 2

[Generated validation queries...]

✅ RUNNING FULL VALIDATION (With Database Execution)

Validation ID: abc123def456
Overall Status: PASS
Data Completeness: 100.00%
Success Rate: 100.00%

Table Results:
  users: PASS (100.0%)
  customers: PASS (100.0%)

✅ Validation complete! Open: validation_reports/report_20260805_152954.html
```

---

### ✅ Step 6: View Results (30 seconds)

```powershell
# Open HTML report
Start-Process "validation_reports\report_*.html"

# Or view JSON
code "validation_reports\report_*.json"
```

---

## ⚠️ Common Issues & Fixes

### Issue: "database does not exist"
**Fix:** Update database name in src/main_example.py
```powershell
psql -U postgres -l  # Find correct database
```

### Issue: "Snowflake connection failed"
**Fix:** Verify credentials
```
Account: ZJAUJWQ-EP12783
Username: MANEGANESH99 (uppercase)
Password: Ganeshmane@999
Database: snowflake_db
```

### Issue: "Table not found"
**Fix:** Run snowflake_setup.sql in Snowflake Web UI first

### Issue: "Data doesn't match"
**Fix:** Check that:
1. PostgreSQL tables have 10 users, 5 customers
2. Snowflake tables have same data
3. Both show 100% completeness in HTML report

---

## 📊 Expected Report Structure

After validation runs, you'll have:

```
validation_reports/
├── report_20260805_152954.json    ← Machine-readable
├── report_20260805_152954.html    ← Dashboard view
└── report_20260805_152954.txt     ← Human-readable
```

**HTML Report shows:**
- ✅/❌ Overall Status
- Completeness % (target: 100%)
- Per-table results
- Per-column validation results
- Transformation rules applied

---

## ✨ Success = This Output

```
Overall Status: PASS
Data Completeness: 100.00%
Success Rate: 100.00%

Table Results:
  users: PASS (100.0%)
  customers: PASS (100.0%)
```

---

## 🎯 What's Next?

Once tests pass:

1. **Replace sample data** with your actual migrated data
2. **Run validation again** to verify migration quality
3. **Monitor regularly** by scheduling validations
4. **Adjust rules** if data doesn't match as expected

---

## 📞 Need Help?

- Check `TEST_AND_VALIDATE.md` for detailed step-by-step
- Review individual connector test outputs
- Check HTML report for specific column mismatches
- Verify database names and credentials

**Let's validate!** 🚀
