# AI-Powered SQL Query Generation

## Overview

The Migration Validator now includes **AI-powered SQL query generation** that dynamically creates database-specific validation queries based on the source and target database types.

## Problem Solved

### Before (Manual/Static Approach)
```sql
-- WRONG for MS SQL Server ❌
SELECT CAST(AddressID AS TEXT) AS AddressID_normalized
FROM dbo.Addresses;

-- Error: Msg 529, Level 16, State 1, Line 16
-- Explicit conversion from data type int to text is not allowed.
```

### After (AI-Powered Generation) ✅
```sql
-- CORRECT for MS SQL Server
SELECT COALESCE(CAST(AddressID AS VARCHAR(MAX)), '<<NULL>>') AS AddressID_normalized
FROM dbo.Addresses;
```

## Key Features

### 1. Database-Specific Syntax
The AI generates queries with correct syntax for each database:

| Database | Integer Cast | Timestamp Format | String Trim |
|----------|-------------|------------------|-------------|
| **MS SQL Server** | `CAST(col AS VARCHAR(MAX))` | `FORMAT(col, 'yyyy-MM-dd HH:mm:ss')` | `LTRIM(RTRIM(col))` |
| **PostgreSQL** | `CAST(col AS TEXT)` | `TO_CHAR(col, 'YYYY-MM-DD HH24:MI:SS')` | `TRIM(col)` |
| **Snowflake** | `CAST(col AS STRING)` | `TO_VARCHAR(col, 'YYYY-MM-DD HH24:MI:SS')` | `TRIM(col)` |
| **Athena** | `CAST(col AS VARCHAR)` | `date_format(col, '%Y-%m-%d %H:%i:%s')` | `TRIM(col)` |

### 2. Intelligent Type Conversions
```python
# AI understands context and generates appropriate casts
IntegerRule._ms_expression("customer_id")
# Output: "CAST(customer_id AS VARCHAR(MAX))"

BooleanRule._ms_expression("is_active")
# Output: "CASE WHEN is_active = 1 THEN '1' WHEN is_active = 0 THEN '0' ELSE NULL END"

TimestampNTZRule._ms_expression("created_at")
# Output: "FORMAT(created_at, 'yyyy-MM-dd HH:mm:ss')"
```

### 3. NULL Placeholder Handling
All queries include proper NULL handling:
```sql
-- MS SQL Server
COALESCE(CAST(column AS VARCHAR(MAX)), '<<NULL>>')

-- PostgreSQL
COALESCE(CAST(column AS TEXT), '<<NULL>>')

-- Snowflake
COALESCE(CAST(column AS STRING), '<<NULL>>')
```

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Validation Pipeline                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│          AISQLQueryGenerator (New!)                          │
│  - Analyzes source DB type (MSSQL, PostgreSQL, Athena)     │
│  - Generates database-specific SQL via AI model             │
│  - Validates syntax against known rules                     │
│  - Falls back to rule-based generation if AI unavailable    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│          BaseValidationRule (Enhanced!)                      │
│  - apply_postgresql(col) → PostgreSQL syntax                │
│  - apply_mssql(col) → MS SQL Server syntax                  │
│  - apply_athena(col) → Athena/Trino syntax                  │
│  - apply_snowflake(col) → Snowflake syntax                  │
│  - apply_source(db_type, col) → Auto-dispatch              │
└─────────────────────────────────────────────────────────────┘
```

### Code Flow

1. **Query Generation Request**
```python
from generated_queries.ai_sql_generator import AISQLQueryGenerator

generator = AISQLQueryGenerator(model="gpt-4o")
result = generator.generate_validation_query(
    schema="dbo",
    table="Addresses",
    mappings=column_mappings,
    source_db_type="mssql",  # ← AI uses this to generate MSSQL syntax
    query_type="data_validation",
)
```

2. **AI Prompt Construction**
```python
System Prompt:
  - Database-specific syntax rules for MSSQL
  - Examples of correct CAST operations
  - NULL handling requirements
  - Format function mappings

User Prompt:
  - Table: dbo.Addresses
  - Columns: [{source_column, source_type, rule}, ...]
  - Source DB: mssql
  - Query type: data_validation
```

3. **AI Response & Validation**
```python
# AI generates:
SELECT
    COALESCE(CAST(AddressID AS VARCHAR(MAX)), '<<NULL>>') AS AddressID_normalized,
    COALESCE(LTRIM(RTRIM(sFName)), '<<NULL>>') AS sFName_normalized,
    COALESCE(FORMAT(dUpdated, 'yyyy-MM-dd HH:mm:ss') AS VARCHAR(MAX)), '<<NULL>>') AS dUpdated_normalized
FROM dbo.Addresses;

# Generator validates:
- No "AS TEXT" (invalid for MSSQL) ✓
- Uses VARCHAR(MAX) instead ✓
- FORMAT() for timestamps ✓
- Returns AIGeneratedQuery with confidence score
```

## Configuration

### Environment Variables

```bash
# Required for AI-powered generation
DIAL_API_KEY=your-epam-dial-api-key
DIAL_API_BASE=https://ai-proxy.lab.epam.com
DIAL_API_VERSION=2025-04-01-preview
DIAL_MODEL=gpt-4o  # or gpt-4o-mini, claude-3-5-sonnet, etc.

# Source database type (auto-detected from connection, or set explicitly)
SOURCE_TYPE=mssql  # mssql, postgresql, athena, trino
```

### Programmatic Configuration

```python
from generated_queries.ai_sql_generator import AISQLQueryGenerator

# Option 1: Use environment variables
generator = AISQLQueryGenerator()

# Option 2: Explicit configuration
generator = AISQLQueryGenerator(
    api_key="your-key",
    api_base="https://ai-proxy.lab.epam.com",
    api_version="2025-04-01-preview",
    model="gpt-4o-mini",  # Faster, cheaper for simple tables
)

# Option 3: Switch models at runtime
generator = AISQLQueryGenerator()
generator.model = "claude-3-5-sonnet"  # Use Claude for complex queries
```

## Usage Examples

### Example 1: MS SQL Server → Snowflake

```python
from generated_queries.ai_sql_generator import AISQLQueryGenerator
from ai_transformation.static_rule_mapper import ColumnRuleMapping

generator = AISQLQueryGenerator(model="gpt-4o")

# Column mappings with rules
mappings = [
    ColumnRuleMapping(
        source_column="AddressID",
        target_column="ADDRESSID",
        source_type="int",
        target_type="NUMBER",
        rule=IntegerRule(),
    ),
    ColumnRuleMapping(
        source_column="sFName",
        target_column="SFNAME",
        source_type="varchar",
        target_type="VARCHAR",
        rule=TextRule(),
    ),
    ColumnRuleMapping(
        source_column="dUpdated",
        target_column="DUPDATED",
        source_type="datetime",
        target_type="TIMESTAMP_NTZ",
        rule=TimestampNTZRule(),
    ),
]

# Generate source query (MSSQL)
result = generator.generate_validation_query(
    schema="dbo",
    table="Addresses",
    mappings=mappings,
    source_db_type="mssql",
    query_type="data_validation",
)

print(result.query)
# Output:
# SELECT
#     COALESCE(CAST(AddressID AS VARCHAR(MAX)), '<<NULL>>') AS AddressID_normalized,
#     COALESCE(LTRIM(RTRIM(sFName)), '<<NULL>>') AS sFName_normalized,
#     COALESCE(CAST(FORMAT(dUpdated, 'yyyy-MM-dd HH:mm:ss') AS VARCHAR(MAX)), '<<NULL>>') AS dUpdated_normalized
# FROM dbo.Addresses;

print(f"Confidence: {result.confidence}")
print(f"Warnings: {result.warnings}")
```

### Example 2: PostgreSQL → Snowflake (Same Logic)

```python
# Same mappings, different source_db_type
result = generator.generate_validation_query(
    schema="public",
    table="addresses",
    mappings=mappings,
    source_db_type="postgresql",
    query_type="data_validation",
)

print(result.query)
# Output:
# SELECT
#     COALESCE(CAST(AddressID AS TEXT), '<<NULL>>') AS AddressID_normalized,
#     COALESCE(TRIM(sFName), '<<NULL>>') AS sFName_normalized,
#     COALESCE(CAST(TO_CHAR(dUpdated, 'YYYY-MM-DD HH24:MI:SS') AS TEXT), '<<NULL>>') AS dUpdated_normalized
# FROM public.addresses;
```

### Example 3: Fallback Mode (No AI Available)

```python
# When DIAL_API_KEY is not set
generator = AISQLQueryGenerator()  # _ai_active = False

result = generator.generate_validation_query(
    schema="dbo",
    table="Addresses",
    mappings=mappings,
    source_db_type="mssql",
    query_type="data_validation",
)

# Automatically uses rule-based generation
# Each rule's _ms_expression() method is called
print(result.explanation)
# Output: "Rule-based fallback query (AI unavailable)"
```

## Benefits

### 1. **Correctness**
- Eliminates syntax errors (no more "AS TEXT" errors on MS SQL Server)
- Database-specific functions (FORMAT vs TO_CHAR vs TO_VARCHAR)
- Proper boolean handling (1/0 vs true/false)

### 2. **Flexibility**
- Supports multiple source databases (MSSQL, PostgreSQL, Athena, Trino)
- Single target (Snowflake) with extensibility for others
- Easy to add new database types

### 3. **Maintainability**
- AI learns from database documentation
- Reduces hard-coded SQL patterns
- Self-documenting (AI explains its decisions)

### 4. **Developer Experience**
- No manual SQL writing for new database types
- Automatic adaptation to database quirks
- Clear error messages and warnings

## Rule Classes Enhanced

All validation rules now support multi-database syntax:

### BooleanRule
```python
# PostgreSQL
CASE WHEN col = true THEN '1' WHEN col = false THEN '0' ELSE NULL END

# MS SQL Server
CASE WHEN col = 1 THEN '1' WHEN col = 0 THEN '0' ELSE NULL END
```

### IntegerRule
```python
# PostgreSQL
CAST(col AS TEXT)

# MS SQL Server
CAST(col AS VARCHAR(MAX))

# Snowflake
CAST(col AS STRING)
```

### TimestampNTZRule
```python
# PostgreSQL
TO_CHAR(col, 'YYYY-MM-DD HH24:MI:SS')

# MS SQL Server
FORMAT(col, 'yyyy-MM-dd HH:mm:ss')

# Snowflake
TO_VARCHAR(col, 'YYYY-MM-DD HH24:MI:SS')
```

### TextRule
```python
# PostgreSQL / Athena
TRIM(col)

# MS SQL Server
LTRIM(RTRIM(col))
```

## Troubleshooting

### Error: "Explicit conversion from data type int to text is not allowed"

**Cause**: Using PostgreSQL syntax on MS SQL Server
```sql
-- Wrong (PostgreSQL syntax)
CAST(AddressID AS TEXT)
```

**Solution**: Ensure `source_db_type="mssql"` is set
```python
generator.generate_validation_query(
    ...
    source_db_type="mssql",  # ← Set this explicitly
)
```

### Low Confidence Warnings

```python
result = generator.generate_validation_query(...)
if result.confidence < 0.8:
    print(f"⚠️  Low confidence ({result.confidence:.2f})")
    print(f"Warnings: {result.warnings}")
    # Consider manual review or using a more powerful model
```

### Fallback to Rule-Based Generation

```python
# When AI is unavailable, the system automatically falls back
result = generator.generate_validation_query(...)
if "fallback" in result.explanation.lower():
    print("Using rule-based generation (AI unavailable)")
    # Query is still correct, just not AI-optimized
```

## Advanced Usage

### Custom Model Selection
```python
# Use faster model for simple queries
fast_gen = AISQLQueryGenerator(model="gpt-4o-mini")

# Use more powerful model for complex schema
power_gen = AISQLQueryGenerator(model="gpt-4o")
power_gen.model = "claude-3-5-sonnet"  # Switch dynamically
```

### Validation Types
```python
# Data validation (full row comparison)
data_query = generator.generate_validation_query(
    ...
    query_type="data_validation",
)

# NULL percentage check
null_query = generator.generate_validation_query(
    ...
    query_type="null_pct",
)

# Distinct value count
distinct_query = generator.generate_validation_query(
    ...
    query_type="distinct_count",
)
```

### Fivetran Integration
```python
# For Snowflake targets synced by Fivetran
result = generator.generate_validation_query(
    ...
    has_fivetran_active=True,  # Adds WHERE _FIVETRAN_ACTIVE = TRUE
)
```

## Future Enhancements

1. **More Source Databases**
   - Oracle
   - MySQL/MariaDB
   - IBM Db2
   - SAP HANA

2. **More Target Databases**
   - BigQuery
   - Redshift
   - Azure Synapse
   - Databricks

3. **Query Optimization**
   - AI suggests indexes
   - AI recommends partitioning strategies
   - AI detects inefficient joins

4. **Self-Learning**
   - Learn from successful migrations
   - Adapt to company-specific patterns
   - Build custom rule libraries

## Summary

The AI-powered SQL query generation feature:

✅ **Fixes** the MS SQL Server "AS TEXT" error
✅ **Supports** multiple source databases (MSSQL, PostgreSQL, Athena)
✅ **Generates** database-specific SQL syntax automatically
✅ **Falls back** to rule-based generation when AI is unavailable
✅ **Maintains** backward compatibility with existing code
✅ **Provides** confidence scores and warnings for quality assurance

**Migration from old approach**: Zero code changes required — the system automatically detects the source database type and generates correct syntax.
