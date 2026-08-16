"""
Query Optimizer
================
Collapses multiple ValidationRequirements into the minimal number of
SQL queries that satisfy all requirements.

The key insight is that many aggregate statistics (NULL %, distinct count,
MIN/MAX, SUM) can share a single table scan.  Instead of:

  Query A: SELECT COUNT(*) AS total_rows, SUM(amount) ...
  Query B: SELECT COUNT(*) AS total_rows, MIN(amount), MAX(amount) ...
  Query C: SELECT COUNT(*) AS total_rows, COUNT(DISTINCT id) ...

the optimizer produces:

  Combined aggregate:
    SELECT
        COUNT(*)               AS total_rows,
        SUM(amount)            AS amount_sum,
        MIN(amount)            AS amount_min,
        MAX(amount)            AS amount_max,
        COUNT(DISTINCT id)     AS id_distinct_count,
        ROUND(100.0 * SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2)
                               AS amount_null_pct
    FROM source_table;

This means the aggregate side of validation becomes exactly 2 queries
(one source, one target) regardless of how many conditional checks were
triggered.

Architecture
------------
  ValidationRequirements (list)
         ↓
  QueryOptimizer.optimize()
         ↓
  ──────────────────────────────────────────────
  | Full-scan queries: DATA_VALIDATION (③ / ④)|
  | Row count queries: ROW_COUNT (① / ②)     |
  | Single combined aggregate query per side  |
  | Duplicate-check query per side            |
  ──────────────────────────────────────────────
         ↓
  List[GeneratedQuery]

All aggregate types (NULL_PCT, DISTINCT_COUNT, MIN_MAX, SUM, VALUE_DIST)
are folded into one combined aggregate query.  ROW_COUNT, DATA_VALIDATION,
and DUPLICATE_CHECK remain as separate queries because they serve different
comparison semantics.
"""

from __future__ import annotations

from typing import List, Optional, Set, Tuple

from profiling.schema_profiler import ColumnGroup, ColumnProfile, TableProfile
from profiling.validation_rule_engine import ValidationType, ValidationRequirement
from profiling.ai_recommendation import AIRecommendation
from dynamic_suite.validation_suite import GeneratedQuery
from dynamic_suite.sql_validator import validate_sql_pair


# ---------------------------------------------------------------------------
# QueryOptimizer
# ---------------------------------------------------------------------------

class QueryOptimizer:
    """
    Converts ValidationRequirements into the minimal set of SQL queries.

    Usage
    -----
        optimizer = QueryOptimizer()
        queries   = optimizer.optimize(
            requirements=requirements,
            profile=table_profile,
            source_schema="public",
            source_table="orders",
            sf_full="MY_DB.MY_SCHEMA.ORDERS",
            fivetran_active=True,
        )
    """

    def optimize(
        self,
        requirements: List[ValidationRequirement],
        profile: TableProfile,
        source_schema: str,
        source_table: str,
        sf_full: str,
        fivetran_active: bool,
        active_mappings: Optional[list] = None,
        source_db_type: str = "postgresql",
    ) -> List[GeneratedQuery]:
        """
        Generate the minimal set of SQL queries for the given requirements.

        Args:
            requirements   : From ValidationRuleEngine.decide()
            profile        : TableProfile used to decide requirements
            source_schema  : PG schema
            source_table   : PG table
            sf_full        : Full Snowflake reference (db.schema.TABLE)
            fivetran_active: Whether to add WHERE _FIVETRAN_ACTIVE = TRUE
            active_mappings: ColumnRuleMapping list for ③④ SQL (from existing generator)

        Returns:
            List[GeneratedQuery] in display order (baseline first, conditional second)
        """
        source_db_type = source_db_type.lower().strip()
        if source_db_type in {"sqlserver", "sql_server", "mssqlserver"}:
            source_db_type = "mssql"
        elif source_db_type in {"postgres", "pg"}:
            source_db_type = "postgresql"
        sf_where = " WHERE _FIVETRAN_ACTIVE = TRUE" if fivetran_active else ""
        pg_full  = f"{source_schema}.{source_table}"
        queries: List[GeneratedQuery] = []

        # Track which types are in requirements for fast lookup
        req_types: Set[ValidationType] = {r.validation_type for r in requirements}
        req_by_type = {r.validation_type: r for r in requirements}

        # ── ① / ② Row Count ───────────────────────────────────────────────
        if ValidationType.ROW_COUNT in req_types:
            req = req_by_type[ValidationType.ROW_COUNT]
            queries.append(GeneratedQuery(
                requirement=req,
                label="Row Count",
                source_sql=(
                    f"-- ① ROW COUNT: PostgreSQL ({pg_full})\n"
                    f"SELECT COUNT(*) AS source_row_count\n"
                    f"FROM {pg_full};"
                ),
                target_sql=(
                    f"-- ② ROW COUNT: Snowflake ({sf_full})\n"
                    f"SELECT COUNT(*) AS target_row_count\n"
                    f"FROM {sf_full}{sf_where};"
                ),
                comparison_note="source_row_count must equal target_row_count",
                query_number="① / ②",
                is_baseline=True,
            ))

        # ── ③ / ④ Full Data Validation ────────────────────────────────────
        if ValidationType.DATA_VALIDATION in req_types:
            req = req_by_type[ValidationType.DATA_VALIDATION]
            src_sql, tgt_sql = self._data_validation_sql(
                pg_full, sf_full, sf_where, active_mappings, source_db_type
            )
            queries.append(GeneratedQuery(
                requirement=req,
                label="Full Data Validation (normalised)",
                source_sql=src_sql,
                target_sql=tgt_sql,
                comparison_note=(
                    "Export both to CSV. Compare row-by-row — must be identical. "
                    "All values are normalised so comparison is type-safe."
                ),
                query_number="③ / ④",
                is_baseline=True,
            ))

        # ── Combined aggregate query ──────────────────────────────────────
        #    Merges: NULL_PCT + DISTINCT_COUNT + MIN_MAX + SUM + VALUE_DIST
        #    into a single SELECT per side — one scan instead of many.
        aggregate_reqs = [
            r for r in requirements
            if r.validation_type in {
                ValidationType.NULL_PCT,
                ValidationType.DISTINCT_COUNT,
                ValidationType.MIN_MAX,
                ValidationType.SUM,
            }
        ]
        if aggregate_reqs:
            src_agg, tgt_agg, agg_label, agg_note = self._combined_aggregate_sql(
                aggregate_reqs, pg_full, sf_full, sf_where, requirements, source_db_type
            )
            # Determine baseline or conditional
            is_base = all(not r.is_conditional for r in aggregate_reqs)
            queries.append(GeneratedQuery(
                requirement=aggregate_reqs[0],
                label=agg_label,
                source_sql=src_agg,
                target_sql=tgt_agg,
                comparison_note=agg_note,
                query_number="⑤–⑫ combined",
                is_baseline=is_base,
            ))

        # VALUE_DIST is a result set, not a scalar aggregate. Keep it as a
        # separate GROUP BY query rather than claiming it is in the aggregate.
        value_dist_reqs = [r for r in requirements if r.validation_type == ValidationType.VALUE_DIST]
        for req in value_dist_reqs:
            for column in req.columns:
                src_dist, tgt_dist = self._value_distribution_sql(
                    column, pg_full, sf_full, sf_where, source_db_type
                )
                queries.append(GeneratedQuery(
                    requirement=req,
                    label=f"Value Distribution ({column.column_name})",
                    source_sql=src_dist,
                    target_sql=tgt_dist,
                    comparison_note="Compare value_count by value; NULL is represented explicitly.",
                    query_number="VALUE_DIST",
                    is_baseline=req.is_conditional is False,
                ))

        # ── ⑬ / ⑭ Duplicate Check ────────────────────────────────────────
        if ValidationType.DUPLICATE_CHECK in req_types:
            req = req_by_type[ValidationType.DUPLICATE_CHECK]
            src_dup, tgt_dup = self._duplicate_sql(req, pg_full, sf_full, sf_where)
            queries.append(GeneratedQuery(
                requirement=req,
                label="Duplicate Check (Business Key)",
                source_sql=src_dup,
                target_sql=tgt_dup,
                comparison_note=(
                    "Both queries should return 0 rows. "
                    "Any row means duplicate business-key values exist."
                ),
                query_number="⑬ / ⑭",
                is_baseline=False,
            ))

        return queries

    # -----------------------------------------------------------------------
    # ③ / ④ Full data validation SQL
    # -----------------------------------------------------------------------

    def _data_validation_sql(
        self,
        pg_full: str,
        sf_full: str,
        sf_where: str,
        active_mappings: Optional[list],
        source_db_type: str,
    ) -> Tuple[str, str]:
        """
        Build the normalised SELECT queries (③ and ④).

        If active_mappings is provided (ColumnRuleMapping list), the full
        normalised expressions are built.  Otherwise a placeholder is returned
        so the caller knows to inject the existing sql_query_generator output.
        """
        if not active_mappings:
            src = (
                f"-- ③ SOURCE: PostgreSQL ({pg_full})\n"
                f"-- (Normalised columns injected from canonical plan — see sql_query_generator)\n"
                f"SELECT * FROM {pg_full}; -- replace with normalised SELECT"
            )
            tgt = (
                f"-- ④ TARGET: Snowflake ({sf_full})\n"
                f"-- (Normalised columns injected from canonical plan — see sql_query_generator)\n"
                f"SELECT * FROM {sf_full}{sf_where}; -- replace with normalised SELECT"
            )
            return src, tgt

        # Build normalised expressions from rule mappings
        src_cols, tgt_cols = [], []
        for m in active_mappings:
            if m.skip_validation:
                continue
            apply_source = getattr(m.rule, f"apply_{source_db_type.lower()}", None)
            if apply_source is None:
                raise ValueError(f"Unsupported source dialect: {source_db_type}")
            src_expr = apply_source(
                m.source_column, alias=f"{m.source_column}_normalized"
            )
            tgt_expr = m.rule.apply_snowflake(
                m.target_column, alias=f"{m.source_column}_normalized"
            )
            src_cols.append(f"    {src_expr}")
            tgt_cols.append(f"    {tgt_expr}")

        src_sql = (
            f"-- ③ SOURCE: PostgreSQL ({pg_full})\n"
            f"SELECT\n" + ",\n".join(src_cols) + f"\nFROM {pg_full};"
        )
        tgt_sql = (
            f"-- ④ TARGET: Snowflake ({sf_full})\n"
            f"SELECT\n" + ",\n".join(tgt_cols) + f"\nFROM {sf_full}{sf_where};"
        )
        return src_sql, tgt_sql

    # -----------------------------------------------------------------------
    # Combined aggregate SQL
    # -----------------------------------------------------------------------

    def _combined_aggregate_sql(
        self,
        aggregate_reqs: List[ValidationRequirement],
        pg_full: str,
        sf_full: str,
        sf_where: str,
        all_requirements: List[ValidationRequirement],
        source_db_type: str,
    ) -> Tuple[str, str, str, str]:
        """
        Build the single combined aggregate SELECT for source and target.

        Merges NULL%, DISTINCT, MIN/MAX, SUM, VALUE_DIST into one scan.
        Returns (source_sql, target_sql, label, comparison_note).
        """
        req_types_present = {r.validation_type for r in aggregate_reqs}
        column_sets = {r.validation_type: r.columns for r in aggregate_reqs}

        all_agg_cols: List[ColumnProfile] = []
        seen_names: Set[str] = set()
        for r in aggregate_reqs:
            for c in r.columns:
                if c.column_name not in seen_names:
                    seen_names.add(c.column_name)
                    all_agg_cols.append(c)

        src_parts = ["COUNT(*) AS total_rows"]
        tgt_parts = ["COUNT(*) AS total_rows"]

        def src_col(c: ColumnProfile) -> str:
            return c.metadata.column_name

        def tgt_col(c: ColumnProfile) -> str:
            # For Snowflake the column name is typically UPPERCASE
            return c.metadata.column_name.upper()

        # ── NULL % ─────────────────────────────────────────────────────────
        null_cols = column_sets.get(ValidationType.NULL_PCT, [])
        for c in null_cols:
            sc, tc = src_col(c), tgt_col(c)
            expr = (
                f"ROUND(100.0 * SUM(CASE WHEN {{col}} IS NULL THEN 1 ELSE 0 END)"
                f" / NULLIF(COUNT(*), 0), 4) AS {c.column_name}_null_pct"
            )
            src_parts.append(expr.format(col=sc))
            tgt_parts.append(expr.format(col=tc))

        # ── DISTINCT COUNT ─────────────────────────────────────────────────
        _JSON_TYPES = {"json"}
        dist_cols = column_sets.get(ValidationType.DISTINCT_COUNT, [])
        for c in dist_cols:
            sc, tc = src_col(c), tgt_col(c)
            # json has no equality operator in PG; cast to jsonb for DISTINCT.
            if getattr(c, "source_type", "").lower() in _JSON_TYPES:
                sc = f"CAST({sc} AS JSONB)" if source_db_type.lower() == "postgresql" else sc
            src_parts.append(
                f"COUNT(DISTINCT {sc}) AS {c.column_name}_distinct_count"
            )
            tgt_parts.append(
                f"COUNT(DISTINCT {tc}) AS {c.column_name}_distinct_count"
            )

        # ── MIN / MAX ──────────────────────────────────────────────────────
        minmax_cols = column_sets.get(ValidationType.MIN_MAX, [])
        for c in minmax_cols:
            sc, tc = src_col(c), tgt_col(c)
            src_parts.append(f"MIN({sc}) AS {c.column_name}_min")
            src_parts.append(f"MAX({sc}) AS {c.column_name}_max")
            tgt_parts.append(f"MIN({tc}) AS {c.column_name}_min")
            tgt_parts.append(f"MAX({tc}) AS {c.column_name}_max")

        # ── SUM ────────────────────────────────────────────────────────────
        sum_cols = column_sets.get(ValidationType.SUM, [])
        for c in sum_cols:
            sc, tc = src_col(c), tgt_col(c)
            src_parts.append(f"SUM({sc}) AS {c.column_name}_sum")
            tgt_parts.append(f"SUM({tc}) AS {c.column_name}_sum")

        # ── What types are included → build label ──────────────────────────
        type_labels = []
        if ValidationType.NULL_PCT in req_types_present:
            type_labels.append("NULL%")
        if ValidationType.DISTINCT_COUNT in req_types_present:
            type_labels.append("DISTINCT")
        if ValidationType.MIN_MAX in req_types_present:
            type_labels.append("MIN/MAX")
        if ValidationType.SUM in req_types_present:
            type_labels.append("SUM")

        included = " + ".join(type_labels)
        label = f"Combined Aggregate Query ({included})"

        indent = "\n    "
        src_select = (",\n    ").join(src_parts)
        tgt_select = (",\n    ").join(tgt_parts)

        src_sql = (
            f"-- ⑤–⑫ COMBINED AGGREGATE: {source_db_type.upper()} ({pg_full})\n"
            f"-- Includes: {included}\n"
            f"-- One scan replaces {len(req_types_present)} separate aggregate query types.\n"
            f"SELECT\n    {src_select}\nFROM {pg_full};"
        )
        tgt_sql = (
            f"-- ⑤–⑫ COMBINED AGGREGATE: Snowflake ({sf_full})\n"
            f"-- Includes: {included}\n"
            f"SELECT\n    {tgt_select}\nFROM {sf_full}{sf_where};"
        )

        note = (
            f"Compare each _null_pct, _distinct_count, _min, _max, _sum column "
            f"between source and target. Column names are identical so direct "
            f"comparison is possible."
        )
        validate_sql_pair(src_sql, tgt_sql, source_db_type)
        return src_sql, tgt_sql, label, note

    def _value_distribution_sql(self, column, pg_full, sf_full, sf_where, source_db_type):
        """Generate a real value-distribution result set for one column."""
        source_column = column.metadata.column_name
        target_column = source_column.upper()
        source_value = f"COALESCE(CAST({source_column} AS VARCHAR(MAX)), '<<NULL>>')" if source_db_type.lower() == "mssql" else f"COALESCE(CAST({source_column} AS TEXT), '<<NULL>>')"
        target_value = f"COALESCE(CAST({target_column} AS STRING), '<<NULL>>')"
        src = f"SELECT\n    {source_value} AS value,\n    COUNT(*) AS value_count\nFROM {pg_full}\nGROUP BY {source_value}\nORDER BY value_count DESC;"
        tgt = f"SELECT\n    {target_value} AS value,\n    COUNT(*) AS value_count\nFROM {sf_full}{sf_where}\nGROUP BY {target_value}\nORDER BY value_count DESC;"
        validate_sql_pair(src, tgt, source_db_type)
        return src, tgt

    # -----------------------------------------------------------------------
    # Duplicate check SQL
    # -----------------------------------------------------------------------

    def _duplicate_sql(
        self,
        req: ValidationRequirement,
        pg_full: str,
        sf_full: str,
        sf_where: str,
    ) -> Tuple[str, str]:
        """Build duplicate-check queries for business-key columns."""
        if not req.columns:
            return "", ""

        key_cols_pg = ", ".join(c.metadata.column_name for c in req.columns)
        key_cols_sf = ", ".join(c.metadata.column_name.upper() for c in req.columns)
        having = "HAVING COUNT(*) > 1"

        # Add count to WHERE for Snowflake so filter is not on aggregate directly
        src_sql = (
            f"-- ⑬ DUPLICATE CHECK: PostgreSQL ({pg_full})\n"
            f"-- Expect: 0 rows returned. Any row = duplicate business key.\n"
            f"SELECT\n"
            f"    {key_cols_pg},\n"
            f"    COUNT(*) AS duplicate_count\n"
            f"FROM {pg_full}\n"
            f"GROUP BY {key_cols_pg}\n"
            f"{having};"
        )

        sf_where_clause = (
            f"WHERE _FIVETRAN_ACTIVE = TRUE\n" if sf_where.strip() else ""
        )
        tgt_sql = (
            f"-- ⑭ DUPLICATE CHECK: Snowflake ({sf_full})\n"
            f"-- Expect: 0 rows returned. Any row = duplicate business key.\n"
            f"SELECT\n"
            f"    {key_cols_sf},\n"
            f"    COUNT(*) AS duplicate_count\n"
            f"FROM {sf_full}\n"
            f"{sf_where_clause}"
            f"GROUP BY {key_cols_sf}\n"
            f"{having};"
        )
        return src_sql, tgt_sql
