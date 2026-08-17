"""
Test Script for MS SQL Server Syntax Fix
==========================================
Verifies that the MS SQL Server rules generate correct syntax.
"""

from rules.postgres_base_rules import IntegerRule, BooleanRule, TextRule, TimestampNTZRule, NumericRule

def test_mssql_integer_rule():
    """Test integer casting for MS SQL Server."""
    rule = IntegerRule()
    
    # Test PostgreSQL syntax
    pg_expr = rule._pg_expression("customer_id")
    assert pg_expr == "CAST(customer_id AS TEXT)", f"PG failed: {pg_expr}"
    
    # Test MS SQL Server syntax (should NOT use TEXT)
    ms_expr = rule._ms_expression("customer_id")
    assert ms_expr == "CAST(customer_id AS VARCHAR(MAX))", f"MSSQL failed: {ms_expr}"
    assert "TEXT" not in ms_expr, "MS SQL Server should not use TEXT type"
    
    print("✅ IntegerRule: MS SQL Server uses VARCHAR(MAX) correctly")


def test_mssql_boolean_rule():
    """Test boolean conversion for MS SQL Server."""
    rule = BooleanRule()
    
    # Test MS SQL Server syntax (should use 1/0, not true/false)
    ms_expr = rule._ms_expression("is_active")
    assert "= 1" in ms_expr, f"MSSQL should use 1 for true: {ms_expr}"
    assert "= 0" in ms_expr, f"MSSQL should use 0 for false: {ms_expr}"
    assert "true" not in ms_expr.lower() or "TRUE" not in ms_expr, "MSSQL should not use true/false"
    
    print("✅ BooleanRule: MS SQL Server uses 1/0 correctly")


def test_mssql_text_rule():
    """Test text trimming for MS SQL Server."""
    rule = TextRule()
    
    # Test PostgreSQL syntax
    pg_expr = rule._pg_expression("name")
    assert pg_expr == "TRIM(name)", f"PG failed: {pg_expr}"
    
    # Test MS SQL Server syntax (should use LTRIM(RTRIM))
    ms_expr = rule._ms_expression("name")
    assert ms_expr == "LTRIM(RTRIM(name))", f"MSSQL failed: {ms_expr}"
    
    print("✅ TextRule: MS SQL Server uses LTRIM(RTRIM()) correctly")


def test_mssql_timestamp_rule():
    """Test timestamp formatting for MS SQL Server."""
    rule = TimestampNTZRule()
    
    # Test PostgreSQL syntax
    pg_expr = rule._pg_expression("created_at")
    assert "TO_CHAR" in pg_expr, f"PG should use TO_CHAR: {pg_expr}"
    
    # Test MS SQL Server syntax (should use FORMAT)
    ms_expr = rule._ms_expression("created_at")
    assert "FORMAT" in ms_expr, f"MSSQL should use FORMAT: {ms_expr}"
    assert "yyyy-MM-dd" in ms_expr, f"MSSQL should use yyyy-MM-dd format: {ms_expr}"
    assert "TO_CHAR" not in ms_expr, "MSSQL should not use TO_CHAR"
    
    print("✅ TimestampNTZRule: MS SQL Server uses FORMAT() correctly")


def test_mssql_numeric_rule():
    """Test numeric rounding for MS SQL Server."""
    rule = NumericRule(decimal_places=2)
    
    # Test PostgreSQL syntax
    pg_expr = rule._pg_expression("price")
    assert "NUMERIC" in pg_expr.upper(), f"PG should cast to NUMERIC: {pg_expr}"
    
    # Test MS SQL Server syntax (should use DECIMAL)
    ms_expr = rule._ms_expression("price")
    assert "DECIMAL" in ms_expr.upper(), f"MSSQL should use DECIMAL: {ms_expr}"
    assert "ROUND" in ms_expr.upper(), f"MSSQL should use ROUND: {ms_expr}"
    
    print("✅ NumericRule: MS SQL Server uses DECIMAL correctly")


def test_apply_source_dispatch():
    """Test that apply_source() correctly dispatches to MS SQL Server methods."""
    rule = IntegerRule()
    
    # Test dispatch to MSSQL
    ms_result = rule.apply_source("mssql", "id", alias="id_normalized")
    assert "VARCHAR(MAX)" in ms_result, f"MSSQL dispatch failed: {ms_result}"
    assert "id_normalized" in ms_result, f"Alias missing: {ms_result}"
    
    # Test dispatch to PostgreSQL
    pg_result = rule.apply_source("postgresql", "id", alias="id_normalized")
    assert "TEXT" in pg_result, f"PG dispatch failed: {pg_result}"
    
    print("✅ apply_source(): Correctly dispatches to database-specific methods")


def test_coalesce_wrapper():
    """Test that COALESCE wrapper uses correct type for MS SQL Server."""
    rule = IntegerRule()
    
    # Get full expression with COALESCE for MSSQL
    full_expr = rule.apply_mssql("customer_id")
    
    assert "COALESCE" in full_expr, f"Should have COALESCE: {full_expr}"
    assert "VARCHAR(MAX)" in full_expr, f"Should cast to VARCHAR(MAX): {full_expr}"
    assert "'<<NULL>>'" in full_expr, f"Should have NULL placeholder: {full_expr}"
    assert "TEXT" not in full_expr, f"Should not have TEXT: {full_expr}"
    
    print("✅ COALESCE: MS SQL Server wrapper uses VARCHAR(MAX)")


def test_all_rules_have_ms_expression():
    """Verify all rules implement _ms_expression()."""
    from rules.postgres_base_rules import (
        BooleanRule, IntegerRule, NumericRule,
        TimestampTZRule, TimestampNTZRule, DateRule,
        TextRule, UUIDRule, JSONRule, ByteaRule, HStoreRule,
    )
    
    rules = [
        BooleanRule(),
        IntegerRule(),
        NumericRule(),
        TimestampTZRule(),
        TimestampNTZRule(),
        DateRule(),
        TextRule(),
        UUIDRule(),
        JSONRule(),
        ByteaRule(),
        HStoreRule(),
    ]
    
    for rule in rules:
        # Test that _ms_expression exists and returns something
        result = rule._ms_expression("test_col")
        assert result, f"{rule.__class__.__name__} returned empty _ms_expression"
        assert "TEXT" not in result.upper() or "VARCHAR" in result.upper(), \
            f"{rule.__class__.__name__} might use TEXT incorrectly: {result}"
    
    print(f"✅ All {len(rules)} rules implement _ms_expression()")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing MS SQL Server Syntax Fix")
    print("=" * 70)
    print()
    
    tests = [
        test_mssql_integer_rule,
        test_mssql_boolean_rule,
        test_mssql_text_rule,
        test_mssql_timestamp_rule,
        test_mssql_numeric_rule,
        test_apply_source_dispatch,
        test_coalesce_wrapper,
        test_all_rules_have_ms_expression,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test.__name__}: {e}")
            failed += 1
    
    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print()
        print("🎉 All tests passed!")
        print("✅ MS SQL Server syntax is correct")
        print("✅ No more 'AS TEXT' errors")
        print("✅ Ready to generate addresses.yaml")
        return 0
    else:
        print()
        print("⚠️  Some tests failed - review fixes needed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
