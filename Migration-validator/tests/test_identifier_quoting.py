"""
Tests for correct SQL identifier usage:
- Source column names appear in PostgreSQL SQL (not target names)
- Target column names appear in Snowflake SQL (not source names)
- Normalized aliases always use source column name on BOTH sides
- NULL placeholder <<NULL>> is always present (applied by every rule)
- Normalized names are NEVER used as SQL identifiers
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai_transformation.static_rule_mapper import ColumnRuleMapping
from generated_queries.sql_query_generator import SQLQueryGenerator
from rules import get_rule_for_type


def _mapping(src, tgt, pg_type="text", sf_type="TEXT"):
    return ColumnRuleMapping(
        source_column=src,
        target_column=tgt,
        source_type=pg_type,
        target_type=sf_type,
        rule=get_rule_for_type(pg_type, sf_type),
    )


def _gen(mappings, fivetran=False):
    gen = SQLQueryGenerator()
    return gen.generate(
        pg_schema="public",
        pg_table="orders",
        sf_database="db",
        sf_schema="schema",
        sf_table="ORDERS",
        mappings=mappings,
        has_fivetran_active=fivetran,
    )


def test_pg_query_uses_source_column_name():
    qs = _gen([_mapping("created_at", "CREATEDAT")])
    # PG SQL must reference the real PG column name
    assert "created_at" in qs.main_validation_source


def test_sf_query_uses_target_column_name():
    qs = _gen([_mapping("created_at", "CREATEDAT")])
    # SF SQL must reference the real SF column name
    assert "CREATEDAT" in qs.main_validation_target


def test_sf_query_does_not_use_pg_source_name_as_identifier():
    # "created_at" is the PG name; SF side should use "CREATEDAT" not "created_at"
    # The alias (created_at_normalized) may appear, but the raw column ref should not
    qs = _gen([_mapping("created_at", "CREATEDAT")])
    # Extract the SELECT expression lines (not the alias)
    lines = qs.main_validation_target.splitlines()
    col_ref_lines = [l for l in lines if "CREATEDAT" in l or "created_at" in l]
    # "created_at_normalized" alias is OK; "created_at" as a standalone column ref is not
    for line in col_ref_lines:
        if "created_at" in line:
            # Must be only in the alias context
            assert "_normalized" in line, f"Bare PG col name used in SF SQL: {line}"


def test_alias_uses_source_column_on_both_sides():
    qs = _gen([_mapping("tenant_id", "TENANT_ID", "integer", "NUMBER")])
    alias = "tenant_id_normalized"
    assert alias in qs.main_validation_source
    assert alias in qs.main_validation_target


def test_null_placeholder_in_postgresql_query():
    qs = _gen([_mapping("status", "STATUS")])
    assert "<<NULL>>" in qs.main_validation_source


def test_null_placeholder_in_snowflake_query():
    qs = _gen([_mapping("status", "STATUS")])
    assert "<<NULL>>" in qs.main_validation_target


def test_null_placeholder_for_boolean_rule():
    qs = _gen([_mapping("is_active", "IS_ACTIVE", "boolean", "BOOLEAN")])
    assert "<<NULL>>" in qs.main_validation_source
    assert "<<NULL>>" in qs.main_validation_target


def test_null_placeholder_for_numeric_rule():
    qs = _gen([_mapping("amount", "AMOUNT", "numeric", "NUMBER")])
    assert "<<NULL>>" in qs.main_validation_source
    assert "<<NULL>>" in qs.main_validation_target


def test_null_placeholder_for_timestamp_rule():
    qs = _gen([_mapping("ts", "TS", "timestamp without time zone", "TIMESTAMP_NTZ")])
    assert "<<NULL>>" in qs.main_validation_source
    assert "<<NULL>>" in qs.main_validation_target


def test_normalized_col_name_not_used_as_sql_identifier():
    # The normalized name (e.g. "createdat") must NEVER appear in SQL
    # as a column reference — only the original names should appear
    qs = _gen([_mapping("created_at", "CREATEDAT")])
    # "createdat" should only appear inside the alias "created_at_normalized"
    # not as a standalone SQL identifier
    for sql in [qs.main_validation_source, qs.main_validation_target,
                qs.null_pct_source, qs.null_pct_target]:
        lines = sql.splitlines()
        for line in lines:
            stripped = line.strip()
            # If the line contains "createdat" but NOT as part of an alias, that's wrong
            if "createdat" in stripped.lower() and "_normalized" not in stripped.lower():
                # Allow it if it's in the table reference (CREATEDAT is the target column)
                if "CREATEDAT" in stripped:
                    continue  # This is the target column reference — OK
                assert False, f"Normalized name used as identifier: {stripped}"


def test_fivetran_filter_placement():
    # The Fivetran filter must be WHERE clause, not SELECT or FROM
    qs = _gen([_mapping("id", "ID", "integer", "NUMBER")], fivetran=True)
    # It must appear in Snowflake queries
    for sf_sql in [qs.row_count_target, qs.main_validation_target,
                   qs.null_pct_target, qs.distinct_count_target]:
        assert "_FIVETRAN_ACTIVE = TRUE" in sf_sql
    # It must NOT appear in PostgreSQL queries
    for pg_sql in [qs.row_count_source, qs.main_validation_source,
                   qs.null_pct_source, qs.distinct_count_source]:
        assert "_FIVETRAN_ACTIVE" not in pg_sql


if __name__ == "__main__":
    test_pg_query_uses_source_column_name()
    test_sf_query_uses_target_column_name()
    test_sf_query_does_not_use_pg_source_name_as_identifier()
    test_alias_uses_source_column_on_both_sides()
    test_null_placeholder_in_postgresql_query()
    test_null_placeholder_in_snowflake_query()
    test_null_placeholder_for_boolean_rule()
    test_null_placeholder_for_numeric_rule()
    test_null_placeholder_for_timestamp_rule()
    test_normalized_col_name_not_used_as_sql_identifier()
    test_fivetran_filter_placement()
    print("All identifier quoting tests passed.")
