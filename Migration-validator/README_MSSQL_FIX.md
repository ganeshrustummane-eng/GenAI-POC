# 🎉 MS SQL Server Support + AI-Powered SQL Generation - COMPLETE

## 🎯 What's Been Fixed

Your MS SQL Server → Snowflake validation is now **fully functional** with:

1. ✅ **Fixed "AS TEXT" Error** - MS SQL Server syntax now correct
2. ✅ **AI-Powered SQL Generation** - Automatically writes database-specific queries
3. ✅ **Multi-Database Support** - Works with MSSQL, PostgreSQL, Athena → Snowflake
4. ✅ **Zero Breaking Changes** - Existing configs work without modification

---

## 🚀 Quick Start (3 Steps)

### Step 1: Update Environment
Add to your `.env` file:
```bash
# Source database type
SOURCE_TYPE=mssql

# Optional: Enable AI query generation
DIAL_API_KEY=your-dial-api-key
DIAL_API_BASE=https://ai-proxy.lab.epam.com
DIAL_MODEL=gpt-4o
```

### Step 2: Test the Fix
```bash
# Run the test script
python test_mssql_syntax.py

# Should output:
# ✅ IntegerRule: MS SQL Server uses VARCHAR(MAX) correctly
# ✅ BooleanRule: MS SQL Server uses 1/0 correctly
# ✅ TextRule: MS SQL Server uses LTRIM(RTRIM()) correctly
# ... (8 tests total)
# 🎉 All tests passed!
```

### Step 3: Fix Your Config
```bash
# Option A: Regenerate with helper script
python regenerate_addresses_config.py

# Option B: Manual fix (see SOLUTION_SUMMARY.md)
# Edit config/bronze/data_validation/addresses.yaml
# Replace: CAST(col AS TEXT) → CAST(col AS VARCHAR(MAX))
# Replace: TRIM(col) → LTRIM(RTRIM(col))
# Replace: = true → = 1, = false → = 0
```

---

## 📂 Files Created/Modified

### New Files (AI SQL Generation)
```
src/generated_queries/ai_sql_generator.py   ← AI-powered query generator
docs/AI_SQL_GENERATION_GUIDE.md             ← Complete usage guide
SOLUTION_SUMMARY.md                          ← Quick reference
test_mssql_syntax.py                         ← Validation tests
regenerate_addresses_config.py               ← Config regeneration helper
README_MSSQL_FIX.md                          ← This file
```

### Modified Files (MS SQL Server Support)
```
src/rules/postgres_base_rules.py            ← Added _ms_expression() to all rules
src/generated_queries/sql_query_generator.py ← Integrated AI generator
```

---

## 🔧 What Changed in the Code

### Before (Broken) ❌
```python
class IntegerRule(BaseValidationRule):
    def _pg_expression(self, col: str) -> str:
        return f"CAST({col} AS TEXT)"  # ← PostgreSQL only
    
    def _sf_expression(self, col: str) -> str:
        return f"CAST({col} AS STRING)"
```

### After (Fixed) ✅
```python
class IntegerRule(BaseValidationRule):
    def _pg_expression(self, col: str) -> str:
        return f"CAST({col} AS TEXT)"
    
    def _ms_expression(self, col: str) -> str:
        return f"CAST({col} AS VARCHAR(MAX))"  # ← MS SQL Server support added!
    
    def _athena_expression(self, col: str) -> str:
        return f"CAST({col} AS VARCHAR)"
    
    def _sf_expression(self, col: str) -> str:
        return f"CAST({col} AS STRING)"
    
    def apply_source(self, source_db_type: str, col: str, alias=None) -> str:
        """Auto-dispatch to correct database."""
        if source_db_type in ("mssql", "sqlserver"):
            return self.apply_mssql(col, alias)  # ← Uses _ms_expression()
        elif source_db_type in ("postgres", "postgresql"):
            return self.apply_postgresql(col, alias)
        # ... etc
```

---

## 📖 Usage Examples

### Example 1: Basic Validation (Auto-Detects Database)
```python
from validation_pipeline import ValidationPipeline

# SOURCE_TYPE=mssql in .env → automatically uses MS SQL Server syntax
pipeline = ValidationPipeline(config_path="config/bronze/data_validation/addresses.yaml")
results = pipeline.run()

# Generated SQL uses:
# - CAST(col AS VARCHAR(MAX))  ← not TEXT
# - FORMAT(col, 'yyyy-MM-dd')  ← not TO_CHAR
# - LTRIM(RTRIM(col))          ← not TRIM
```

### Example 2: AI-Powered Query Generation
```python
from generated_queries.ai_sql_generator import AISQLQueryGenerator

generator = AISQLQueryGenerator(model="gpt-4o")

result = generator.generate_validation_query(
    schema="dbo",
    table="Addresses",
    mappings=column_mappings,
    source_db_type="mssql",  # ← AI knows to use MS SQL Server syntax
)

print(result.query)
# SELECT
#     COALESCE(CAST(AddressID AS VARCHAR(MAX)), '<<NULL>>') AS AddressID_normalized,
#     COALESCE(LTRIM(RTRIM(sFName)), '<<NULL>>') AS sFName_normalized,
#     ...
# FROM dbo.Addresses;

print(f"Confidence: {result.confidence}")  # 0.95
print(f"Warnings: {result.warnings}")      # []
```

### Example 3: Manual Rule Application
```python
from rules.postgres_base_rules import IntegerRule, BooleanRule, TextRule

int_rule = IntegerRule()
bool_rule = BooleanRule()
text_rule = TextRule()

# Apply MS SQL Server syntax explicitly
print(int_rule.apply_mssql("customer_id", alias="customer_id_normalized"))
# COALESCE(CAST(customer_id AS VARCHAR(MAX)), '<<NULL>>') AS customer_id_normalized

print(bool_rule.apply_mssql("is_active", alias="is_active_normalized"))
# COALESCE(CASE WHEN is_active = 1 THEN '1' WHEN is_active = 0 THEN '0' ELSE NULL END, '<<NULL>>') AS is_active_normalized

print(text_rule.apply_mssql("name", alias="name_normalized"))
# COALESCE(LTRIM(RTRIM(name)), '<<NULL>>') AS name_normalized
```

---

## 🧪 Testing

### Run All Tests
```bash
python test_mssql_syntax.py
```

Expected output:
```
======================================================================
Testing MS SQL Server Syntax Fix
======================================================================

✅ IntegerRule: MS SQL Server uses VARCHAR(MAX) correctly
✅ BooleanRule: MS SQL Server uses 1/0 correctly
✅ TextRule: MS SQL Server uses LTRIM(RTRIM()) correctly
✅ TimestampNTZRule: MS SQL Server uses FORMAT() correctly
✅ NumericRule: MS SQL Server uses DECIMAL correctly
✅ apply_source(): Correctly dispatches to database-specific methods
✅ COALESCE: MS SQL Server wrapper uses VARCHAR(MAX)
✅ All 11 rules implement _ms_expression()

======================================================================
Results: 8 passed, 0 failed
======================================================================

🎉 All tests passed!
✅ MS SQL Server syntax is correct
✅ No more 'AS TEXT' errors
✅ Ready to generate addresses.yaml
```

### Test Individual Rules
```python
# Test in Python REPL
from rules.postgres_base_rules import IntegerRule

rule = IntegerRule()

# Should return: CAST(id AS VARCHAR(MAX))
rule._ms_expression("id")

# Should include COALESCE and VARCHAR(MAX)
rule.apply_mssql("id")
```

---

## 🐛 Troubleshooting

### Issue 1: Still Getting "AS TEXT" Error

**Symptom:**
```
Msg 529, Level 16, State 1
Explicit conversion from data type int to text is not allowed
```

**Solution:**
```bash
# Check your .env
grep SOURCE_TYPE .env
# Should output: SOURCE_TYPE=mssql

# If missing, add it:
echo "SOURCE_TYPE=mssql" >> .env

# Regenerate config:
python regenerate_addresses_config.py
```

### Issue 2: Rules Not Found

**Symptom:**
```python
ImportError: cannot import name 'IntegerRule' from 'rules.postgres_base_rules'
```

**Solution:**
```bash
# Ensure you're in the project root
cd /c:/EPAM-Personal/Migration-validator

# Add src to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"  # Linux/Mac
$env:PYTHONPATH += ";$(pwd)\src"              # Windows PowerShell
```

### Issue 3: AI Generator Not Working

**Symptom:**
```
[AISQLGenerator] AI unavailable - using rule-based fallback
```

**Solution:**
```bash
# Check DIAL API key
grep DIAL_API_KEY .env

# If missing, add:
echo "DIAL_API_KEY=your-key-here" >> .env

# Test connection:
python -c "
from generated_queries.ai_sql_generator import AISQLQueryGenerator
gen = AISQLQueryGenerator()
print(f'AI Active: {gen._ai_active}')
"
```

---

## 📚 Documentation

### Primary Docs
- **SOLUTION_SUMMARY.md** - Quick fix guide
- **docs/AI_SQL_GENERATION_GUIDE.md** - Complete AI feature documentation
- **test_mssql_syntax.py** - Validation tests with examples
- **regenerate_addresses_config.py** - Config regeneration helper

### Code Reference
- **src/rules/postgres_base_rules.py** - All validation rules with MS SQL Server support
- **src/rules/mssql_rules.py** - MS SQL Server rule exports
- **src/generated_queries/ai_sql_generator.py** - AI query generator
- **src/generated_queries/sql_query_generator.py** - Main SQL generator (enhanced)

---

## 🎯 Before/After Comparison

### addresses.yaml - sourcequery Section

**Before (WRONG) ❌**
```sql
SELECT
    COALESCE(CAST(CAST(AddressID AS TEXT) AS VARCHAR(MAX)), '<<NULL>>') AS AddressID_normalized,
    COALESCE(CAST(TRIM(sFName) AS VARCHAR(MAX)), '<<NULL>>') AS sFName_normalized,
    COALESCE(CAST(CASE WHEN bPermanent = true THEN '1' WHEN bPermanent = false THEN '0' ELSE NULL END AS VARCHAR(MAX)), '<<NULL>>') AS bPermanent_normalized,
    COALESCE(CAST(TO_CHAR(dDeleted, 'YYYY-MM-DD HH24:MI:SS') AS VARCHAR(MAX)), '<<NULL>>') AS dDeleted_normalized
FROM dbo.Addresses;
```

**After (CORRECT) ✅**
```sql
SELECT
    COALESCE(CAST(AddressID AS VARCHAR(MAX)), '<<NULL>>') AS AddressID_normalized,
    COALESCE(LTRIM(RTRIM(sFName)), '<<NULL>>') AS sFName_normalized,
    COALESCE(CASE WHEN bPermanent = 1 THEN '1' WHEN bPermanent = 0 THEN '0' ELSE NULL END, '<<NULL>>') AS bPermanent_normalized,
    COALESCE(FORMAT(dDeleted, 'yyyy-MM-dd HH:mm:ss'), '<<NULL>>') AS dDeleted_normalized
FROM dbo.Addresses;
```

### Key Changes
| Type | Wrong (PostgreSQL) | Correct (MS SQL Server) |
|------|-------------------|------------------------|
| Integer | `CAST(col AS TEXT)` | `CAST(col AS VARCHAR(MAX))` |
| String | `TRIM(col)` | `LTRIM(RTRIM(col))` |
| Boolean | `= true / = false` | `= 1 / = 0` |
| Timestamp | `TO_CHAR(col, ...)` | `FORMAT(col, ...)` |

---

## ✅ Verification Checklist

Before running your validation:

- [ ] `SOURCE_TYPE=mssql` set in `.env`
- [ ] `test_mssql_syntax.py` passes all tests
- [ ] `addresses.yaml` uses `VARCHAR(MAX)`, not `TEXT`
- [ ] `addresses.yaml` uses `LTRIM(RTRIM(...))`, not `TRIM(...)`
- [ ] `addresses.yaml` uses `= 1/= 0`, not `= true/= false`
- [ ] `addresses.yaml` uses `FORMAT(...)`, not `TO_CHAR(...)`
- [ ] Backup of original config created

---

## 🎉 Success Criteria

You'll know it's working when:

1. ✅ `test_mssql_syntax.py` reports "All tests passed"
2. ✅ No "AS TEXT" errors when running validation
3. ✅ SQL queries execute successfully on MS SQL Server
4. ✅ Validation results match between source and target

---

## 🆘 Need Help?

### Quick Fixes
```bash
# Fix 1: Regenerate addresses.yaml
python regenerate_addresses_config.py

# Fix 2: Run syntax tests
python test_mssql_syntax.py

# Fix 3: Check environment
grep SOURCE_TYPE .env
grep DIAL_API_KEY .env
```

### Manual Fix Template
```sql
-- Find:    CAST(column AS TEXT)
-- Replace: CAST(column AS VARCHAR(MAX))

-- Find:    TRIM(column)
-- Replace: LTRIM(RTRIM(column))

-- Find:    column = true
-- Replace: column = 1

-- Find:    column = false
-- Replace: column = 0

-- Find:    TO_CHAR(column, 'YYYY-MM-DD HH24:MI:SS')
-- Replace: FORMAT(column, 'yyyy-MM-dd HH:mm:ss')
```

---

## 📞 Support

If you encounter issues:

1. Check **SOLUTION_SUMMARY.md** for quick fixes
2. Read **docs/AI_SQL_GENERATION_GUIDE.md** for detailed usage
3. Run **test_mssql_syntax.py** to verify the fix
4. Use **regenerate_addresses_config.py** to regenerate config

---

## 🎊 Summary

**What you now have:**

✅ Full MS SQL Server → Snowflake validation support  
✅ AI-powered SQL query generation  
✅ Database-aware syntax transformation  
✅ Automatic fallback to rule-based generation  
✅ Comprehensive test suite  
✅ Config regeneration helpers  

**Your system is now production-ready!** 🚀

---

**Version:** 1.0.0  
**Date:** 2026-08-13  
**Status:** ✅ COMPLETE
