"""
End-to-end pipeline tests — no live database connections required.

Tests the full chain:
  synthetic ColumnMetadata
    → CandidateMatcher  (deterministic matching)
    → CanonicalValidationPlan (build from decisions)
    → PlanValidator     (validate plan)
    → SQLQueryGenerator (generate SQL from plan)
    → YAMLConfigWriter  (generate YAML from plan)
"""
import sys
import os
import tempfile
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sql_extractor.base_extractor import ColumnMetadata
from matching.candidate_matcher import CandidateMatcher
from core.validation_plan import CanonicalValidationPlan, ColumnMappingEntry, PlanStatus
from validation.plan_validator import PlanValidator, PlanValidationError
from generated_queries.sql_query_generator import SQLQueryGenerator
from generated_queries.yaml_config_writer import YAMLConfigWriter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _col(name, dtype="text", pos=1):
    return ColumnMetadata(ordinal_position=pos, column_name=name, data_type=dtype, is_nullable=True)


def _build_plan_from_decisions(decisions, source_table="events", target_table="EVENTS"):
    mappings = []
    for d in decisions:
        if d.skip_validation:
            mappings.append(ColumnMappingEntry(
                source_column=d.source_col.column_name,
                source_type=d.source_col.data_type,
                source_normalized=d.source_col.normalized_name,
                target_column=d.target_col.column_name if d.target_col else "",
                target_type=d.target_col.data_type if d.target_col else "",
                target_normalized=d.target_col.normalized_name if d.target_col else "",
                match_method=d.method or "skip",
                confidence=d.final_score,
                transformation_rule="text",
                skip_validation=True,
                skip_reason=d.skip_reason,
            ))
        else:
            mappings.append(ColumnMappingEntry(
                source_column=d.source_col.column_name,
                source_type=d.source_col.data_type,
                source_normalized=d.source_col.normalized_name,
                target_column=d.target_col.column_name,
                target_type=d.target_col.data_type,
                target_normalized=d.target_col.normalized_name,
                match_method=d.method or "fuzzy",
                confidence=d.final_score,
                transformation_rule="text",
                skip_validation=False,
            ))
    return CanonicalValidationPlan(
        source_schema="public",
        source_table=source_table,
        target_schema="schema",
        target_table=target_table,
        mappings=mappings,
    )


# ---------------------------------------------------------------------------
# End-to-end pipeline tests
# ---------------------------------------------------------------------------

def test_full_pipeline_exact_match():
    src_cols = [_col("id", "integer", pos=1), _col("email", "text", pos=2)]
    tgt_cols = [_col("ID", "NUMBER", pos=1), _col("EMAIL", "TEXT", pos=2)]

    matcher = CandidateMatcher()
    decisions = matcher.match(src_cols, tgt_cols)

    plan = _build_plan_from_decisions(decisions)

    validator = PlanValidator()
    result = validator.validate(plan)
    assert result.is_valid, f"Plan invalid: {result.issues}"

    gen = SQLQueryGenerator()
    qs = gen.generate_from_plan(plan)
    assert "id" in qs.main_validation_source
    assert "ID" in qs.main_validation_target
    assert "<<NULL>>" in qs.main_validation_source


def test_full_pipeline_normalized_match():
    # created_at (PG) → CREATEDAT (SF) — normalized_exact match
    src_cols = [_col("created_at", "timestamp without time zone", pos=1)]
    tgt_cols = [_col("CREATEDAT", "TIMESTAMP_NTZ", pos=1)]

    matcher = CandidateMatcher()
    decisions = matcher.match(src_cols, tgt_cols)
    assert decisions[0].is_resolved
    assert decisions[0].method == "normalized_exact"

    plan = _build_plan_from_decisions(decisions)
    validator = PlanValidator()
    result = validator.validate(plan)
    assert result.is_valid


def test_full_pipeline_sql_and_yaml_from_plan():
    src_cols = [
        _col("id", "integer", pos=1),
        _col("status", "text", pos=2),
        _col("created_at", "timestamp without time zone", pos=3),
    ]
    tgt_cols = [
        _col("ID", "NUMBER", pos=1),
        _col("STATUS", "TEXT", pos=2),
        _col("CREATEDAT", "TIMESTAMP_NTZ", pos=3),
    ]

    matcher = CandidateMatcher()
    decisions = matcher.match(src_cols, tgt_cols)
    plan = _build_plan_from_decisions(decisions)

    gen = SQLQueryGenerator()
    qs = gen.generate_from_plan(plan)

    with tempfile.TemporaryDirectory() as tmpdir:
        writer = YAMLConfigWriter()
        yaml_path = writer.write_from_plan(plan, qs, output_dir=Path(tmpdir))
        assert yaml_path.exists()
        content = yaml_path.read_text(encoding="utf-8")
        assert "row_count_validation:" in content
        assert "data_validation:" in content


def test_plan_validator_blocks_invalid_plan():
    # A plan with no active mappings should be blocked
    plan = CanonicalValidationPlan(
        source_schema="public",
        source_table="events",
        target_schema="schema",
        target_table="EVENTS",
        mappings=[ColumnMappingEntry(
            source_column="id",
            source_type="integer",
            source_normalized="id",
            target_column="",
            target_type="",
            target_normalized="",
            match_method="skip",
            confidence=0.0,
            transformation_rule="text",
            skip_validation=True,
            skip_reason="no match",
        )],
    )
    validator = PlanValidator()
    result = validator.validate(plan)
    assert not result.is_valid
    assert plan.status == PlanStatus.INVALID.value


def test_fivetran_column_excluded_from_active_mappings():
    src_cols = [
        _col("id", "integer", pos=1),
        _col("_FIVETRAN_ACTIVE", "boolean", pos=2),
        _col("_FIVETRAN_DELETED", "boolean", pos=3),
    ]
    tgt_cols = [_col("ID", "NUMBER", pos=1)]

    matcher = CandidateMatcher()
    decisions = matcher.match(src_cols, tgt_cols)

    plan = _build_plan_from_decisions(decisions)
    # Fivetran columns should be in mappings but skipped
    skipped = [m.source_column for m in plan.skipped_mappings]
    assert "_FIVETRAN_ACTIVE" in skipped
    assert "_FIVETRAN_DELETED" in skipped
    # Only real column should be active
    assert len(plan.active_mappings) == 1
    assert plan.active_mappings[0].source_column == "id"


def test_all_8_sql_queries_non_empty():
    src_cols = [_col("id", "integer", pos=1), _col("name", "text", pos=2)]
    tgt_cols = [_col("ID", "NUMBER", pos=1), _col("NAME", "TEXT", pos=2)]

    matcher = CandidateMatcher()
    decisions = matcher.match(src_cols, tgt_cols)
    plan = _build_plan_from_decisions(decisions)

    gen = SQLQueryGenerator()
    qs = gen.generate_from_plan(plan)

    assert qs.row_count_source
    assert qs.row_count_target
    assert qs.main_validation_source
    assert qs.main_validation_target
    assert qs.null_pct_source
    assert qs.null_pct_target
    assert qs.distinct_count_source
    assert qs.distinct_count_target


def test_rules_registry_lookup_works_for_common_types():
    from rules import get_rule_for_type
    pairs = [
        ("boolean", "BOOLEAN"),
        ("integer", "NUMBER"),
        ("text", "TEXT"),
        ("numeric", "NUMBER"),
        ("timestamp without time zone", "TIMESTAMP_NTZ"),
        ("timestamp with time zone", "TIMESTAMP_TZ"),
        ("date", "DATE"),
        ("uuid", "VARCHAR"),
        ("json", "VARIANT"),
        ("jsonb", "VARIANT"),
    ]
    for pg, sf in pairs:
        rule = get_rule_for_type(pg, sf)
        assert rule is not None, f"No rule for ({pg}, {sf})"
        # Every rule must produce an expression with the NULL placeholder
        pg_expr = rule.apply_postgresql("test_col")
        sf_expr = rule.apply_snowflake("test_col")
        assert "<<NULL>>" in pg_expr, f"Missing NULL placeholder in PG expr for ({pg}, {sf})"
        assert "<<NULL>>" in sf_expr, f"Missing NULL placeholder in SF expr for ({pg}, {sf})"


if __name__ == "__main__":
    test_full_pipeline_exact_match()
    test_full_pipeline_normalized_match()
    test_full_pipeline_sql_and_yaml_from_plan()
    test_plan_validator_blocks_invalid_plan()
    test_fivetran_column_excluded_from_active_mappings()
    test_all_8_sql_queries_non_empty()
    test_rules_registry_lookup_works_for_common_types()
    print("All end-to-end tests passed.")
