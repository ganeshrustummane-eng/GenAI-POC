"""
Tests for ValidationRuleEngine
================================
Verifies that the rule engine makes the correct decisions about which
validations to include based on the table profile.

Run:
    cd src
    python -m pytest tests/test_validation_rule_engine.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_extractor.base_extractor import ColumnMetadata
from profiling.schema_profiler import SchemaProfiler
from profiling.validation_rule_engine import ValidationRuleEngine, ValidationType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def col(name: str, dtype: str, nullable: bool = True,
        scale: int = None) -> ColumnMetadata:
    return ColumnMetadata(
        ordinal_position=1,
        column_name=name,
        data_type=dtype,
        is_nullable=nullable,
        numeric_scale=scale,
    )


PROFILER = SchemaProfiler()
ENGINE   = ValidationRuleEngine()


def decide(*columns: ColumnMetadata):
    profile = PROFILER.profile(list(columns), schema="public", table="test")
    return ENGINE.decide(profile)


def req_types(*columns: ColumnMetadata):
    return {r.validation_type for r in decide(*columns)}


# ---------------------------------------------------------------------------
# Baseline validations — always present
# ---------------------------------------------------------------------------

class TestBaselineAlwaysPresent:
    def test_row_count_always_present(self):
        reqs = req_types(col("id", "integer"))
        assert ValidationType.ROW_COUNT in reqs

    def test_data_validation_always_present(self):
        reqs = req_types(col("id", "integer"))
        assert ValidationType.DATA_VALIDATION in reqs

    def test_null_pct_always_present(self):
        reqs = req_types(col("name", "text"))
        assert ValidationType.NULL_PCT in reqs

    def test_distinct_count_always_present(self):
        reqs = req_types(col("name", "text"))
        assert ValidationType.DISTINCT_COUNT in reqs


# ---------------------------------------------------------------------------
# MIN / MAX — conditional on numeric columns
# ---------------------------------------------------------------------------

class TestMinMax:
    def test_triggered_by_financial_column(self):
        reqs = req_types(col("amount", "numeric", scale=2))
        assert ValidationType.MIN_MAX in reqs

    def test_triggered_by_quantity_column(self):
        reqs = req_types(col("quantity", "integer"))
        assert ValidationType.MIN_MAX in reqs

    def test_triggered_by_generic_numeric(self):
        reqs = req_types(col("score", "integer"))
        assert ValidationType.MIN_MAX in reqs

    def test_not_triggered_for_text_only_table(self):
        reqs = req_types(col("name", "text"), col("description", "text"))
        assert ValidationType.MIN_MAX not in reqs

    def test_not_triggered_for_temporal_only_table(self):
        reqs = req_types(col("created_at", "date"))
        assert ValidationType.MIN_MAX not in reqs


# ---------------------------------------------------------------------------
# SUM — conditional on financial or quantity columns
# ---------------------------------------------------------------------------

class TestSum:
    def test_triggered_by_amount(self):
        reqs = req_types(col("amount", "numeric", scale=2))
        assert ValidationType.SUM in reqs

    def test_triggered_by_balance(self):
        reqs = req_types(col("balance", "decimal", scale=4))
        assert ValidationType.SUM in reqs

    def test_triggered_by_quantity(self):
        reqs = req_types(col("quantity", "integer"))
        assert ValidationType.SUM in reqs

    def test_not_triggered_for_generic_score(self):
        # 'score' → NUMERIC_GENERIC, not financial/quantity → no SUM
        reqs = req_types(col("score", "integer"))
        assert ValidationType.SUM not in reqs

    def test_not_triggered_for_text_table(self):
        reqs = req_types(col("name", "character varying"))
        assert ValidationType.SUM not in reqs


# ---------------------------------------------------------------------------
# DUPLICATE_CHECK — conditional on NOT NULL identifier columns
# ---------------------------------------------------------------------------

class TestDuplicateCheck:
    def test_triggered_by_not_null_id(self):
        reqs = req_types(col("customer_id", "bigint", nullable=False))
        assert ValidationType.DUPLICATE_CHECK in reqs

    def test_triggered_by_primary_key(self):
        reqs = req_types(col("id", "integer", nullable=False))
        assert ValidationType.DUPLICATE_CHECK in reqs

    def test_not_triggered_by_nullable_id(self):
        reqs = req_types(col("optional_id", "integer", nullable=True))
        assert ValidationType.DUPLICATE_CHECK not in reqs

    def test_not_triggered_for_text_table(self):
        reqs = req_types(col("name", "text"))
        assert ValidationType.DUPLICATE_CHECK not in reqs


# ---------------------------------------------------------------------------
# VALUE_DISTRIBUTION — conditional on status/enum columns
# ---------------------------------------------------------------------------

class TestValueDistribution:
    def test_triggered_by_boolean(self):
        reqs = req_types(col("is_active", "boolean"))
        assert ValidationType.VALUE_DIST in reqs

    def test_triggered_by_status_varchar(self):
        reqs = req_types(col("status", "character varying"))
        assert ValidationType.VALUE_DIST in reqs

    def test_triggered_by_type_column(self):
        reqs = req_types(col("account_type", "text"))
        assert ValidationType.VALUE_DIST in reqs

    def test_not_triggered_for_numeric_only(self):
        reqs = req_types(col("score", "integer"), col("amount", "numeric"))
        assert ValidationType.VALUE_DIST not in reqs


# ---------------------------------------------------------------------------
# Full table — all conditions present
# ---------------------------------------------------------------------------

class TestFullOrdersTable:
    def requirements(self):
        return decide(
            col("order_id",    "integer",          nullable=False),
            col("customer_id", "bigint",            nullable=False),
            col("amount",      "numeric",           scale=2),
            col("quantity",    "integer"),
            col("status",      "character varying"),
            col("created_at",  "timestamp without time zone"),
            col("is_active",   "boolean"),
        )

    def req_set(self):
        return {r.validation_type for r in self.requirements()}

    def test_all_baseline_present(self):
        rs = self.req_set()
        assert ValidationType.ROW_COUNT       in rs
        assert ValidationType.DATA_VALIDATION in rs
        assert ValidationType.NULL_PCT        in rs
        assert ValidationType.DISTINCT_COUNT  in rs

    def test_all_conditional_triggered(self):
        rs = self.req_set()
        assert ValidationType.MIN_MAX         in rs
        assert ValidationType.SUM             in rs
        assert ValidationType.DUPLICATE_CHECK in rs
        assert ValidationType.VALUE_DIST      in rs

    def test_columns_assigned_to_sum_req(self):
        reqs = self.requirements()
        sum_req = next(r for r in reqs if r.validation_type == ValidationType.SUM)
        col_names = {c.column_name for c in sum_req.columns}
        assert "amount" in col_names or "quantity" in col_names

    def test_columns_assigned_to_duplicate_req(self):
        reqs = self.requirements()
        dup_req = next(r for r in reqs if r.validation_type == ValidationType.DUPLICATE_CHECK)
        # Should be one of the NOT NULL id columns
        assert len(dup_req.columns) > 0

    def test_requirements_ordering(self):
        reqs = self.requirements()
        # Baseline must come before conditional
        baseline_idx = [i for i, r in enumerate(reqs) if not r.is_conditional]
        conditional_idx = [i for i, r in enumerate(reqs) if r.is_conditional]
        if baseline_idx and conditional_idx:
            assert max(baseline_idx) < min(conditional_idx)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
