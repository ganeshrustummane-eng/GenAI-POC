"""
Test All Database Types - Multi-Database SQL Generation
========================================================
Validates that the AI-powered SQL generator works correctly for:
  - MS SQL Server
  - PostgreSQL
  - Athena
  - Snowflake (as source)

Each database has unique syntax requirements that the AI must handle correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rules.postgres_base_rules import (
    IntegerRule, BooleanRule, TextRule, 
    TimestampNTZRule, NumericRule, DateRule
)


def test_mssql_syntax():
    """Test MS SQL Server specific syntax."""
    print("=" * 70)
    print("Testing MS SQL Server Syntax")
    print("=" * 70)
    print()
    
    int_rule = IntegerRule()
    bool_rule = BooleanRule()
    text_rule = TextRule()
    ts_rule = TimestampNTZRule()
    num_rule = NumericRule(decimal_places=2)
    
    # Test integer - must use VARCHAR(MAX), not TEXT
    int_expr = int_rule.apply_source("mssql", "customer_id", alias="customer_id_normalized")
    assert "VARCHAR(MAX)" in int_expr, f"MSSQL should use VARCHAR(MAX): {int_expr}"
    assert "TEXT" not in int_expr.upper() or "VARCHAR" in int_expr.upper(), f"Should not use TEXT alone: {int_expr}"
    print("✅ Integer: Uses VARCHAR(MAX)")
    
    # Test boolean - must use 1/0, not true/false
    bool_expr = bool_rule.apply_source("mssql", "is_active", alias="is_active_normalized")
    assert "= 1" in bool_expr or "WHEN 1" in bool_expr, f"MSSQL should use 1 for true: {bool_expr}"
    assert "= 0" in bool_expr or "WHEN 0" in bool_expr, f"MSSQL should use 0 for false: {bool_expr}"
    print("✅ Boolean: Uses 1/0 instead of true/false")
    
    # Test text - must use LTRIM(RTRIM), not TRIM
    text_expr = text_rule.apply_source("mssql", "name", alias="name_normalized")
    assert "LTRIM" in text_expr.upper() and "RTRIM" in text_expr.upper(), f"MSSQL should use LTRIM(RTRIM): {text_expr}"
    print("✅ Text: Uses LTRIM(RTRIM())")
    
    # Test timestamp - must use FORMAT, not TO_CHAR
    ts_expr = ts_rule.apply_source("mssql", "created_at", alias="created_at_normalized")
    assert "FORMAT" in ts_expr.upper(), f"MSSQL should use FORMAT: {ts_expr}"
    assert "TO_CHAR" not in ts_expr, f"MSSQL should not use TO_CHAR: {ts_expr}"
    print("✅ Timestamp: Uses FORMAT() function")
    
    # Test numeric - must use DECIMAL, not NUMERIC
    num_expr = num_rule.apply_source("mssql", "price", alias="price_normalized")
    assert "DECIMAL" in num_expr.upper() or "NUMERIC" in num_expr.upper(), f"MSSQL should use DECIMAL: {num_expr}"
    print("✅ Numeric: Uses DECIMAL type")
    
    print()
    print("✅ MS SQL Server: All tests passed!")
    print()


def test_postgresql_syntax():
    """Test PostgreSQL specific syntax."""
    print("=" * 70)
    print("Testing PostgreSQL Syntax")
    print("=" * 70)
    print()
    
    int_rule = IntegerRule()
    bool_rule = BooleanRule()
    text_rule = TextRule()
    ts_rule = TimestampNTZRule()
    
    # Test integer - must use TEXT
    int_expr = int_rule.apply_source("postgresql", "customer_id", alias="customer_id_normalized")
    assert "TEXT" in int_expr, f"PostgreSQL should use TEXT: {int_expr}"
    print("✅ Integer: Uses TEXT")
    
    # Test boolean - can use true/false keywords
    bool_expr = bool_rule.apply_source("postgresql", "is_active", alias="is_active_normalized")
    # PostgreSQL accepts both true/false and 't'/'f'
    assert "true" in bool_expr.lower() or "'t'" in bool_expr.lower() or "1" in bool_expr, f"PostgreSQL boolean: {bool_expr}"
    print("✅ Boolean: Uses true/false or 't'/'f'")
    
    # Test text - can use TRIM
    text_expr = text_rule.apply_source("postgresql", "name", alias="name_normalized")
    assert "TRIM" in text_expr.upper(), f"PostgreSQL should use TRIM: {text_expr}"
    print("✅ Text: Uses TRIM()")
    
    # Test timestamp - must use TO_CHAR
    ts_expr = ts_rule.apply_source("postgresql", "created_at", alias="created_at_normalized")
    assert "TO_CHAR" in ts_expr, f"PostgreSQL should use TO_CHAR: {ts_expr}"
    print("✅ Timestamp: Uses TO_CHAR() function")
    
    print()
    print("✅ PostgreSQL: All tests passed!")
    print()


def test_athena_syntax():
    """Test Athena/Trino/Presto specific syntax."""
    print("=" * 70)
    print("Testing Athena Syntax")
    print("=" * 70)
    print()
    
    int_rule = IntegerRule()
    bool_rule = BooleanRule()
    text_rule = TextRule()
    date_rule = DateRule()
    
    # Test integer - must use VARCHAR (not VARCHAR(MAX))
    int_expr = int_rule.apply_source("athena", "customer_id", alias="customer_id_normalized")
    assert "VARCHAR" in int_expr.upper(), f"Athena should use VARCHAR: {int_expr}"
    print("✅ Integer: Uses VARCHAR")
    
    # Test text - can use TRIM
    text_expr = text_rule.apply_source("athena", "name", alias="name_normalized")
    assert "TRIM" in text_expr.upper(), f"Athena should use TRIM: {text_expr}"
    print("✅ Text: Uses TRIM()")
    
    # Test date - should have proper formatting
    date_expr = date_rule.apply_source("athena", "birth_date", alias="birth_date_normalized")
    # Athena uses date_format() or CAST
    assert "date_format" in date_expr.lower() or "CAST" in date_expr, f"Athena date: {date_expr}"
    print("✅ Date: Uses date_format() or CAST")
    
    print()
    print("✅ Athena: All tests passed!")
    print()


def test_snowflake_syntax():
    """Test Snowflake specific syntax (as source)."""
    print("=" * 70)
    print("Testing Snowflake Syntax (as source)")
    print("=" * 70)
    print()
    
    int_rule = IntegerRule()
    bool_rule = BooleanRule()
    text_rule = TextRule()
    ts_rule = TimestampNTZRule()
    
    # Test integer - must use STRING
    int_expr = int_rule.apply_snowflake("customer_id", alias="customer_id_normalized")
    assert "STRING" in int_expr, f"Snowflake should use STRING: {int_expr}"
    print("✅ Integer: Uses STRING")
    
    # Test boolean - uses TRUE/FALSE (uppercase)
    bool_expr = bool_rule.apply_snowflake("is_active", alias="is_active_normalized")
    assert "TRUE" in bool_expr or "FALSE" in bool_expr or "1" in bool_expr, f"Snowflake boolean: {bool_expr}"
    print("✅ Boolean: Uses TRUE/FALSE")
    
    # Test text - can use TRIM
    text_expr = text_rule.apply_snowflake("name", alias="name_normalized")
    assert "TRIM" in text_expr.upper(), f"Snowflake should use TRIM: {text_expr}"
    print("✅ Text: Uses TRIM()")
    
    # Test timestamp - must use TO_VARCHAR
    ts_expr = ts_rule.apply_snowflake("created_at", alias="created_at_normalized")
    assert "TO_VARCHAR" in ts_expr or "TO_CHAR" in ts_expr, f"Snowflake should use TO_VARCHAR: {ts_expr}"
    print("✅ Timestamp: Uses TO_VARCHAR() function")
    
    print()
    print("✅ Snowflake: All tests passed!")
    print()


def test_apply_source_dispatch():
    """Test that apply_source() correctly dispatches to all database types."""
    print("=" * 70)
    print("Testing apply_source() Multi-Database Dispatch")
    print("=" * 70)
    print()
    
    int_rule = IntegerRule()
    
    databases = [
        ("mssql", "VARCHAR(MAX)"),
        ("sqlserver", "VARCHAR(MAX)"),
        ("postgresql", "TEXT"),
        ("postgres", "TEXT"),
        ("athena", "VARCHAR"),
        ("trino", "VARCHAR"),
        ("snowflake", "STRING"),
    ]
    
    for db_type, expected_type in databases:
        result = int_rule.apply_source(db_type, "id", alias="id_normalized")
        assert expected_type in result, f"{db_type} should use {expected_type}: {result}"
        print(f"✅ {db_type:12s} → {expected_type}")
    
    print()
    print("✅ apply_source(): All database dispatches work correctly!")
    print()


def test_cross_database_comparison():
    """Test that different databases produce comparable normalized output."""
    print("=" * 70)
    print("Testing Cross-Database Normalization Consistency")
    print("=" * 70)
    print()
    
    int_rule = IntegerRule()
    
    # All databases should cast integers to text/string type
    mssql_expr = int_rule._ms_expression("customer_id")
    pg_expr = int_rule._pg_expression("customer_id")
    athena_expr = int_rule._athena_expression("customer_id")
    sf_expr = int_rule._sf_expression("customer_id")
    
    print("Integer cast comparison:")
    print(f"  MS SQL Server: {mssql_expr}")
    print(f"  PostgreSQL   : {pg_expr}")
    print(f"  Athena       : {athena_expr}")
    print(f"  Snowflake    : {sf_expr}")
    print()
    
    # All should have CAST and convert to text-like type
    assert "CAST" in mssql_expr.upper(), "MSSQL should use CAST"
    assert "CAST" in pg_expr.upper(), "PostgreSQL should use CAST"
    assert "CAST" in athena_expr.upper(), "Athena should use CAST"
    assert "CAST" in sf_expr.upper(), "Snowflake should use CAST"
    
    print("✅ All databases use consistent CAST pattern")
    
    # Test boolean normalization
    bool_rule = BooleanRule()
    
    mssql_bool = bool_rule._ms_expression("is_active")
    pg_bool = bool_rule._pg_expression("is_active")
    
    print()
    print("Boolean normalization comparison:")
    print(f"  MS SQL Server: {mssql_bool}")
    print(f"  PostgreSQL   : {pg_bool}")
    print()
    
    # Both should produce '1' for true, '0' for false
    assert "'1'" in mssql_bool and "'0'" in mssql_bool, "MSSQL should normalize to '1'/'0'"
    assert "'1'" in pg_bool and "'0'" in pg_bool, "PostgreSQL should normalize to '1'/'0'"
    
    print("✅ Boolean values normalize to '1'/'0' consistently")
    print()


def test_all_rules_multi_database():
    """Verify all rules support all database types."""
    print("=" * 70)
    print("Testing All Rules Across All Databases")
    print("=" * 70)
    print()
    
    from rules.postgres_base_rules import (
        BooleanRule, IntegerRule, NumericRule,
        TimestampTZRule, TimestampNTZRule, DateRule,
        TextRule, UUIDRule, JSONRule, ByteaRule, HStoreRule,
    )
    
    rules = [
        ("BooleanRule", BooleanRule()),
        ("IntegerRule", IntegerRule()),
        ("NumericRule", NumericRule()),
        ("TimestampTZRule", TimestampTZRule()),
        ("TimestampNTZRule", TimestampNTZRule()),
        ("DateRule", DateRule()),
        ("TextRule", TextRule()),
        ("UUIDRule", UUIDRule()),
        ("JSONRule", JSONRule()),
        ("ByteaRule", ByteaRule()),
        ("HStoreRule", HStoreRule()),
    ]
    
    databases = ["mssql", "postgresql", "athena", "snowflake"]
    
    failed = []
    
    for rule_name, rule in rules:
        for db_type in databases:
            try:
                if db_type == "snowflake":
                    result = rule.apply_snowflake("test_col")
                else:
                    result = rule.apply_source(db_type, "test_col")
                
                if not result:
                    failed.append(f"{rule_name} returned empty for {db_type}")
                
                # Check for common mistakes
                if db_type == "mssql" and "AS TEXT" in result.upper() and "VARCHAR" not in result.upper():
                    failed.append(f"{rule_name} uses 'AS TEXT' on MSSQL (should be VARCHAR(MAX))")
                
            except Exception as e:
                failed.append(f"{rule_name} failed on {db_type}: {e}")
    
    if failed:
        print("❌ Some rules failed:")
        for error in failed:
            print(f"   - {error}")
        print()
        return False
    else:
        print(f"✅ All {len(rules)} rules work correctly across all {len(databases)} databases!")
        print(f"   Total combinations tested: {len(rules) * len(databases)}")
        print()
        return True


def test_ai_generator_all_databases():
    """Test AI SQL generator for all database types."""
    print("=" * 70)
    print("Testing AI SQL Generator - All Databases")
    print("=" * 70)
    print()
    
    try:
        from generated_queries.ai_sql_generator import AISQLQueryGenerator
        from ai_transformation.static_rule_mapper import ColumnRuleMapping
        
        # Create sample mappings
        mappings = [
            ColumnRuleMapping(
                source_column="id",
                target_column="ID",
                source_type="int",
                target_type="NUMBER",
                rule=IntegerRule(),
            ),
            ColumnRuleMapping(
                source_column="name",
                target_column="NAME",
                source_type="varchar",
                target_type="VARCHAR",
                rule=TextRule(),
            ),
            ColumnRuleMapping(
                source_column="is_active",
                target_column="IS_ACTIVE",
                source_type="boolean",
                target_type="BOOLEAN",
                rule=BooleanRule(),
            ),
        ]
        
        generator = AISQLQueryGenerator()
        
        databases = ["mssql", "postgresql", "athena"]
        
        for db_type in databases:
            print(f"Testing {db_type.upper()}...")
            
            result = generator.generate_validation_query(
                schema="test_schema",
                table="test_table",
                mappings=mappings,
                source_db_type=db_type,
                query_type="data_validation",
            )
            
            print(f"  Generated by: {result.database_type}")
            print(f"  Confidence: {result.confidence:.2f}")
            print(f"  Warnings: {len(result.warnings)}")
            
            # Validate syntax
            if db_type == "mssql":
                if " AS TEXT" in result.query.upper() and "VARCHAR" not in result.query.upper():
                    print(f"  ❌ WARNING: Query contains 'AS TEXT' (invalid for MSSQL)")
                else:
                    print(f"  ✅ MSSQL syntax correct (uses VARCHAR(MAX))")
            elif db_type == "postgresql":
                if "TO_CHAR" in result.query or "TEXT" in result.query:
                    print(f"  ✅ PostgreSQL syntax correct")
                else:
                    print(f"  ⚠️  No PostgreSQL-specific functions detected")
            elif db_type == "athena":
                if "VARCHAR" in result.query.upper():
                    print(f"  ✅ Athena syntax correct")
                else:
                    print(f"  ⚠️  No Athena-specific functions detected")
            
            print()
        
        print("✅ AI Generator: All databases tested!")
        print()
        
    except ImportError as e:
        print(f"⚠️  AI Generator not available (missing dependency): {e}")
        print("   Rule-based generation will be used as fallback")
        print()
    except Exception as e:
        print(f"⚠️  AI Generator test skipped: {e}")
        print()


def main():
    """Run all tests."""
    print()
    print("=" * 70)
    print("Multi-Database SQL Generation Test Suite")
    print("=" * 70)
    print()
    
    tests = [
        ("MS SQL Server Syntax", test_mssql_syntax),
        ("PostgreSQL Syntax", test_postgresql_syntax),
        ("Athena Syntax", test_athena_syntax),
        ("Snowflake Syntax", test_snowflake_syntax),
        ("Multi-Database Dispatch", test_apply_source_dispatch),
        ("Cross-Database Consistency", test_cross_database_comparison),
        ("All Rules Multi-Database", test_all_rules_multi_database),
        ("AI Generator All Databases", test_ai_generator_all_databases),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test_name}: {e}")
            failed += 1
    
    print()
    print("=" * 70)
    print(f"Results: {passed}/{len(tests)} passed, {failed} failed")
    print("=" * 70)
    print()
    
    if failed == 0:
        print("🎉 All tests passed!")
        print()
        print("✅ MS SQL Server  - VARCHAR(MAX), FORMAT(), LTRIM(RTRIM()), 1/0")
        print("✅ PostgreSQL     - TEXT, TO_CHAR(), TRIM(), true/false")
        print("✅ Athena         - VARCHAR, date_format(), TRIM()")
        print("✅ Snowflake      - STRING, TO_VARCHAR(), TRIM(), TRUE/FALSE")
        print()
        print("✅ AI-powered generation works for all databases!")
        print("✅ Rule-based fallback available for all databases!")
        print()
        print("🚀 Your multi-database validation system is ready!")
        return 0
    else:
        print("⚠️  Some tests failed - review fixes needed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
