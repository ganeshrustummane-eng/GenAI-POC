"""
Tests for generated_queries/sql_query_generator.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sql_extractor.base_extractor import ColumnMetadata
from ai_transformation.static_rule_mapper import ColumnRuleMapping
from generated_queries.sql_query_generator import SQLQueryGenerator, ValidationQuerySet, _plan_to_rule_mappings
from rules import get_rule_for_type
from core.validation_plan import CanonicalValidationPlan, ColumnMappingEntry


def _col(name, dtype="text", pos=1):
    return ColumnMetadata(ordinal_position=pos, column_name=name, data_type=dtype, is_nullable=True)


def _mapping(src, tgt, pg_type="text", sf_type="TEXT"):
    return ColumnRuleMapping(
        source_column=src,
        target_column=tgt,
        source_type=pg_type,
        target_type=sf_type,
        rule=get_rule_for_type(pg_type, sf_type),
    )


def _plan_entry(src="col_a", tgt="COL_A", pg_type="text", sf_type="TEXT", skip=False):
    return ColumnMappingEntry(
        source_column=src,
        source_type=pg_type,
        source_normalized=src.lower().replace("_", ""),
        target_column=tgt,
        target_type=sf_type,
        target_normalized=tgt.lower().replace("_", ""),
        match_method="exact",
        confidence=0.99,
        transformation_rule="text",
        skip_validation=skip,
    )


# ---------------------------------------------------------------------------
# Row count queries
# ---------------------------------------------------------------------------

def test_row_count_source_contains_pg_table():
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[_mapping("id", "ID")], has_fivetran_active=False)
    assert "public.events" in qs.row_count_source
    assert "source_row_count" in qs.row_count_source


def test_row_count_target_no_fivetran_filter():
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[_mapping("id", "ID")], has_fivetran_active=False)
    assert "_FIVETRAN_ACTIVE" not in qs.row_count_target
    assert "target_row_count" in qs.row_count_target


def test_row_count_target_with_fivetran_filter():
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[_mapping("id", "ID")], has_fivetran_active=True)
    assert "_FIVETRAN_ACTIVE = TRUE" in qs.row_count_target


# ---------------------------------------------------------------------------
# Main validation queries
# ---------------------------------------------------------------------------

def test_main_validation_source_contains_normalized_alias():
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[_mapping("created_at", "CREATEDAT", "timestamp without time zone", "TIMESTAMP_NTZ")],
                      has_fivetran_active=False)
    assert "created_at_normalized" in qs.main_validation_source


def test_main_validation_target_uses_target_column_name():
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[_mapping("created_at", "CREATEDAT", "timestamp without time zone", "TIMESTAMP_NTZ")],
                      has_fivetran_active=False)
    assert "CREATEDAT" in qs.main_validation_target


def test_main_validation_target_alias_uses_source_name():
    # Both PG and SF sides use the same alias (source column name) for CSV comparison
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[_mapping("event_type", "EVENT_TYPE")],
                      has_fivetran_active=False)
    assert "event_type_normalized" in qs.main_validation_target


def test_main_validation_target_with_fivetran_filter():
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[_mapping("id", "ID")], has_fivetran_active=True)
    assert "_FIVETRAN_ACTIVE = TRUE" in qs.main_validation_target


def test_empty_mappings_produces_select_1():
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[], has_fivetran_active=False)
    assert "SELECT 1" in qs.main_validation_source
    assert "SELECT 1" in qs.main_validation_target


# ---------------------------------------------------------------------------
# NULL % queries
# ---------------------------------------------------------------------------

def test_null_pct_source_contains_col_null_pct():
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[_mapping("status", "STATUS")], has_fivetran_active=False)
    assert "status_null_pct" in qs.null_pct_source
    assert "total_rows" in qs.null_pct_source


def test_null_pct_target_uses_target_column():
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[_mapping("tenant_id", "TENANT_ID", "integer", "NUMBER")],
                      has_fivetran_active=False)
    assert "TENANT_ID IS NULL" in qs.null_pct_target


# ---------------------------------------------------------------------------
# Distinct count queries
# ---------------------------------------------------------------------------

def test_distinct_count_source_contains_distinct():
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[_mapping("id", "ID", "integer", "NUMBER")],
                      has_fivetran_active=False)
    assert "DISTINCT" in qs.distinct_count_source
    assert "id_distinct_count" in qs.distinct_count_source


# ---------------------------------------------------------------------------
# NULL placeholder
# ---------------------------------------------------------------------------

def test_null_placeholder_in_main_validation():
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[_mapping("id", "ID", "integer", "NUMBER")],
                      has_fivetran_active=False)
    assert "<<NULL>>" in qs.main_validation_source
    assert "<<NULL>>" in qs.main_validation_target


# ---------------------------------------------------------------------------
# All 8 queries populated
# ---------------------------------------------------------------------------

def test_all_8_queries_populated():
    gen = SQLQueryGenerator()
    qs = gen.generate("public", "events", "db", "schema", "EVENTS",
                      mappings=[_mapping("id", "ID", "integer", "NUMBER")],
                      has_fivetran_active=False)
    assert qs.row_count_source
    assert qs.row_count_target
    assert qs.main_validation_source
    assert qs.main_validation_target
    assert qs.null_pct_source
    assert qs.null_pct_target
    assert qs.distinct_count_source
    assert qs.distinct_count_target
    assert qs.combined_sql


# ---------------------------------------------------------------------------
# generate_from_plan
# ---------------------------------------------------------------------------

def test_generate_from_plan_produces_same_output():
    gen = SQLQueryGenerator()
    plan = CanonicalValidationPlan(
        source_schema="public",
        source_table="events",
        target_database="db",
        target_schema="schema",
        target_table="EVENTS",
        mappings=[_plan_entry("id", "ID", "integer", "NUMBER")],
        has_fivetran_active=False,
    )
    qs = gen.generate_from_plan(plan)
    assert "events" in qs.row_count_source
    assert "EVENTS" in qs.row_count_target


def test_plan_to_rule_mappings_skips_skip_validation():
    entries = [
        _plan_entry("id", "ID", skip=False),
        _plan_entry("internal", "INTERNAL", skip=True),
    ]
    mappings = _plan_to_rule_mappings(entries)
    assert len(mappings) == 1
    assert mappings[0].source_column == "id"


if __name__ == "__main__":
    test_row_count_source_contains_pg_table()
    test_row_count_target_no_fivetran_filter()
    test_row_count_target_with_fivetran_filter()
    test_main_validation_source_contains_normalized_alias()
    test_main_validation_target_uses_target_column_name()
    test_main_validation_target_alias_uses_source_name()
    test_main_validation_target_with_fivetran_filter()
    test_empty_mappings_produces_select_1()
    test_null_pct_source_contains_col_null_pct()
    test_null_pct_target_uses_target_column()
    test_distinct_count_source_contains_distinct()
    test_null_placeholder_in_main_validation()
    test_all_8_queries_populated()
    test_generate_from_plan_produces_same_output()
    test_plan_to_rule_mappings_skips_skip_validation()
    print("All SQL generation tests passed.")
