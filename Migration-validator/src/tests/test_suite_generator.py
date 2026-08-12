"""
Tests for DynamicSuiteGenerator
=================================
Integration tests that run the full pipeline (profiling → rule engine →
query optimizer → ValidationSuite) without any database connection.

Run:
    cd src
    python -m pytest tests/test_suite_generator.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_extractor.extractors import ColumnMetadata
from dynamic_suite.suite_generator import DynamicSuiteGenerator
from dynamic_suite.validation_suite import ValidationSuite


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


GEN = DynamicSuiteGenerator()


def generate(*columns: ColumnMetadata, fivetran: bool = False) -> ValidationSuite:
    return GEN.generate(
        source_columns=list(columns),
        source_schema="public",
        source_table="orders",
        sf_database="MY_DB",
        sf_schema="MY_SCHEMA",
        sf_table="ORDERS",
        has_fivetran_active=fivetran,
        use_ai_recommendations=False,   # no AI key in unit tests
        generated_by="static",
        model_used="N/A",
    )


# ---------------------------------------------------------------------------
# ValidationSuite structure
# ---------------------------------------------------------------------------

class TestSuiteStructure:
    def test_returns_validation_suite(self):
        suite = generate(col("id", "integer"))
        assert isinstance(suite, ValidationSuite)

    def test_source_table_set(self):
        suite = generate(col("id", "integer"))
        assert suite.source_table == "orders"
        assert suite.source_schema == "public"

    def test_target_table_set(self):
        suite = generate(col("id", "integer"))
        assert suite.target_table == "ORDERS"
        assert suite.target_database == "MY_DB"
        assert suite.target_schema == "MY_SCHEMA"

    def test_has_queries(self):
        suite = generate(col("id", "integer"))
        assert suite.total_query_pairs > 0

    def test_has_requirements(self):
        suite = generate(col("id", "integer"))
        assert len(suite.requirements) > 0

    def test_profile_attached(self):
        suite = generate(col("id", "integer"))
        assert suite.profile is not None

    def test_fivetran_flag_propagated(self):
        suite = generate(col("id", "integer"), fivetran=True)
        assert suite.has_fivetran_active is True

    def test_baseline_queries_present(self):
        suite = generate(col("id", "integer"))
        assert len(suite.baseline_queries) >= 2


# ---------------------------------------------------------------------------
# Combined SQL output
# ---------------------------------------------------------------------------

class TestCombinedSqlOutput:
    def test_combined_sql_not_empty(self):
        suite = generate(col("id", "integer"))
        sql   = suite.to_combined_sql()
        assert len(sql) > 100

    def test_combined_sql_has_source_header(self):
        suite = generate(col("id", "integer"))
        sql   = suite.to_combined_sql()
        assert "SOURCE" in sql

    def test_combined_sql_has_target_header(self):
        suite = generate(col("id", "integer"))
        sql   = suite.to_combined_sql()
        assert "TARGET" in sql

    def test_combined_sql_has_fivetran_when_active(self):
        suite = generate(col("id", "integer"), fivetran=True)
        sql   = suite.to_combined_sql()
        assert "_FIVETRAN_ACTIVE = TRUE" in sql

    def test_combined_sql_no_fivetran_when_inactive(self):
        suite = generate(col("id", "integer"), fivetran=False)
        sql   = suite.to_combined_sql()
        assert "_FIVETRAN_ACTIVE" not in sql

    def test_combined_sql_has_select_statements(self):
        suite = generate(col("id", "integer"))
        sql   = suite.to_combined_sql()
        assert sql.count("SELECT") >= 2


# ---------------------------------------------------------------------------
# Full orders table — conditional checks included
# ---------------------------------------------------------------------------

class TestOrdersTableSuite:
    def suite(self):
        return generate(
            col("order_id",    "integer",          nullable=False),
            col("customer_id", "bigint",            nullable=False),
            col("amount",      "numeric",           scale=2),
            col("quantity",    "integer"),
            col("status",      "character varying"),
            col("created_at",  "timestamp without time zone"),
            col("is_active",   "boolean"),
        )

    def test_has_conditional_queries(self):
        suite = self.suite()
        assert len(suite.conditional_queries) > 0

    def test_sum_present_in_sql(self):
        suite = self.suite()
        sql   = suite.to_combined_sql()
        assert "SUM(amount)" in sql or "SUM(quantity)" in sql

    def test_min_max_present_in_sql(self):
        suite = self.suite()
        sql   = suite.to_combined_sql()
        assert "MIN(" in sql and "MAX(" in sql

    def test_duplicate_check_present(self):
        suite = self.suite()
        sql   = suite.to_combined_sql()
        assert "DUPLICATE" in sql or "HAVING COUNT(*) > 1" in sql

    def test_null_pct_present(self):
        suite = self.suite()
        sql   = suite.to_combined_sql()
        assert "null_pct" in sql


# ---------------------------------------------------------------------------
# Summary dict
# ---------------------------------------------------------------------------

class TestSummaryDict:
    def test_to_summary_dict_has_expected_keys(self):
        suite = generate(col("id", "integer"))
        d = suite.to_summary_dict()
        for key in ["source_table", "target_table", "generated_at",
                    "total_query_pairs", "requirements"]:
            assert key in d, f"Missing key: {key}"

    def test_requirements_are_listed(self):
        suite = generate(col("id", "integer"))
        d = suite.to_summary_dict()
        assert isinstance(d["requirements"], list)
        assert len(d["requirements"]) > 0

    def test_baseline_count_positive(self):
        suite = generate(col("id", "integer"))
        d = suite.to_summary_dict()
        assert d["baseline_count"] > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
