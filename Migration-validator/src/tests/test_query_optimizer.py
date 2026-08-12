"""
Tests for QueryOptimizer
==========================
Verifies the optimizer produces valid SQL and correctly collapses
multiple requirements into the minimum number of queries.

Run:
    cd src
    python -m pytest tests/test_query_optimizer.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_extractor.extractors import ColumnMetadata
from profiling.schema_profiler import SchemaProfiler
from profiling.validation_rule_engine import ValidationRuleEngine
from dynamic_suite.query_optimizer import QueryOptimizer
from dynamic_suite.validation_suite import GeneratedQuery


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


PROFILER  = SchemaProfiler()
ENGINE    = ValidationRuleEngine()
OPTIMIZER = QueryOptimizer()


def run_optimizer(
    columns,
    source_schema="public",
    source_table="orders",
    sf_full="MY_DB.MY_SCHEMA.ORDERS",
    fivetran=False,
):
    profile  = PROFILER.profile(list(columns), schema=source_schema, table=source_table)
    reqs     = ENGINE.decide(profile)
    queries  = OPTIMIZER.optimize(
        requirements=reqs,
        profile=profile,
        source_schema=source_schema,
        source_table=source_table,
        sf_full=sf_full,
        fivetran_active=fivetran,
    )
    return queries


def sql_contains(queries: list, fragment: str) -> bool:
    combined = " ".join(q.source_sql + q.target_sql for q in queries)
    return fragment in combined


def source_sqls(queries) -> str:
    return "\n".join(q.source_sql for q in queries)


def target_sqls(queries) -> str:
    return "\n".join(q.target_sql for q in queries)


# ---------------------------------------------------------------------------
# Row count queries
# ---------------------------------------------------------------------------

class TestRowCountQueries:
    def test_row_count_always_generated(self):
        queries = run_optimizer([col("id", "integer")])
        labels  = [q.label for q in queries]
        assert any("Row Count" in l for l in labels)

    def test_source_row_count_sql(self):
        queries = run_optimizer([col("id", "integer")])
        src_sql = source_sqls(queries)
        assert "COUNT(*) AS source_row_count" in src_sql
        assert "FROM public.orders" in src_sql

    def test_target_row_count_sql(self):
        queries = run_optimizer([col("id", "integer")])
        tgt_sql = target_sqls(queries)
        assert "COUNT(*) AS target_row_count" in tgt_sql
        assert "FROM MY_DB.MY_SCHEMA.ORDERS" in tgt_sql

    def test_fivetran_filter_in_target(self):
        queries = run_optimizer([col("id", "integer")], fivetran=True)
        tgt_sql = target_sqls(queries)
        assert "_FIVETRAN_ACTIVE = TRUE" in tgt_sql

    def test_no_fivetran_filter_when_disabled(self):
        queries = run_optimizer([col("id", "integer")], fivetran=False)
        tgt_sql = target_sqls(queries)
        assert "_FIVETRAN_ACTIVE" not in tgt_sql


# ---------------------------------------------------------------------------
# Combined aggregate — optimisation correctness
# ---------------------------------------------------------------------------

class TestCombinedAggregate:
    def _full_table_queries(self):
        columns = [
            col("order_id",   "integer",          nullable=False),
            col("amount",     "numeric",           scale=2),
            col("quantity",   "integer"),
            col("status",     "character varying"),
        ]
        return run_optimizer(columns)

    def test_aggregate_collapsed_to_one_query(self):
        # All aggregate types (NULL%, DISTINCT, MIN/MAX, SUM) → max 1 combined
        queries = self._full_table_queries()
        agg_queries = [q for q in queries if "COMBINED AGGREGATE" in q.source_sql]
        assert len(agg_queries) == 1, (
            f"Expected exactly 1 combined aggregate query, got {len(agg_queries)}"
        )

    def test_combined_has_null_pct(self):
        queries = self._full_table_queries()
        src = source_sqls(queries)
        assert "null_pct" in src

    def test_combined_has_distinct_count(self):
        queries = self._full_table_queries()
        src = source_sqls(queries)
        assert "distinct_count" in src

    def test_combined_has_sum(self):
        queries = self._full_table_queries()
        src = source_sqls(queries)
        # amount is financial → SUM included
        assert "SUM(amount)" in src

    def test_combined_has_min_max(self):
        queries = self._full_table_queries()
        src = source_sqls(queries)
        assert "MIN(amount)" in src
        assert "MAX(amount)" in src

    def test_single_scan_not_multiple(self):
        # A table with amount (financial) should not have separate SUM and MIN/MAX
        queries = self._full_table_queries()
        # Should be: row_count + data_validation + combined_aggregate + maybe duplicate
        # All aggregate types → 1 combined query
        agg_queries = [q for q in queries if "COMBINED AGGREGATE" in q.source_sql]
        assert len(agg_queries) == 1

    def test_fewer_queries_than_naive(self):
        # Naive: 2 queries per requirement × N requirements. Optimized: fewer.
        columns = [
            col("order_id", "integer", nullable=False),
            col("amount",   "numeric", scale=2),
            col("quantity", "integer"),
            col("status",   "character varying"),
        ]
        profile  = PROFILER.profile(columns, schema="public", table="orders")
        reqs     = ENGINE.decide(profile)
        naive_count = len(reqs) * 2
        queries  = OPTIMIZER.optimize(
            requirements=reqs,
            profile=profile,
            source_schema="public",
            source_table="orders",
            sf_full="DB.SCHEMA.ORDERS",
            fivetran_active=False,
        )
        optimized_count = len(queries) * 2  # each GeneratedQuery is a pair
        assert optimized_count < naive_count


# ---------------------------------------------------------------------------
# Duplicate check queries
# ---------------------------------------------------------------------------

class TestDuplicateCheck:
    def test_not_generated_for_nullable_id(self):
        queries = run_optimizer([col("optional_ref", "integer", nullable=True)])
        dup_queries = [q for q in queries if "DUPLICATE" in q.label]
        assert len(dup_queries) == 0

    def test_generated_for_not_null_id(self):
        queries = run_optimizer([col("customer_id", "bigint", nullable=False)])
        dup_queries = [q for q in queries if "Duplicate" in q.label or "DUPLICATE" in q.label]
        assert len(dup_queries) == 1

    def test_duplicate_check_sql_structure(self):
        queries = run_optimizer([col("order_id", "integer", nullable=False)])
        dup_queries = [q for q in queries if "Duplicate" in q.label or "DUPLICATE" in q.label]
        if dup_queries:
            sql = dup_queries[0].source_sql
            assert "GROUP BY" in sql
            assert "HAVING COUNT(*) > 1" in sql

    def test_duplicate_check_0_rows_expected(self):
        queries = run_optimizer([col("order_id", "integer", nullable=False)])
        dup_queries = [q for q in queries if "Duplicate" in q.label or "DUPLICATE" in q.label]
        if dup_queries:
            note = dup_queries[0].comparison_note
            assert "0 rows" in note


# ---------------------------------------------------------------------------
# Text-only table — minimal requirements
# ---------------------------------------------------------------------------

class TestTextOnlyTable:
    def test_no_sum_for_text_table(self):
        queries = run_optimizer([
            col("first_name", "text"),
            col("last_name",  "text"),
        ])
        src = source_sqls(queries)
        # Must not have a direct SUM(column) — only SUM(CASE WHEN …) for null_pct is allowed
        import re
        direct_sums = re.findall(r"SUM\([a-z_]+\)", src)  # SUM(col_name), not SUM(CASE …)
        assert direct_sums == [], f"Unexpected SUM aggregate on text table: {direct_sums}"

    def test_no_minmax_for_text_table(self):
        queries = run_optimizer([
            col("first_name", "text"),
            col("last_name",  "text"),
        ])
        src = source_sqls(queries)
        assert "MIN(" not in src
        assert "MAX(" not in src

    def test_null_pct_still_present(self):
        queries = run_optimizer([col("name", "text")])
        src = source_sqls(queries)
        assert "null_pct" in src


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
