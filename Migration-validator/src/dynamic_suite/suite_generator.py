"""
Dynamic Suite Generator
========================
Top-level orchestrator for the dynamic validation suite.

Workflow
--------
  1. SchemaProfiler   — classify each column into semantic groups
  2. ValidationRuleEngine — decide which validations are needed
  3. AIRecommendationEngine — (optional) add AI business-rule suggestions
  4. QueryOptimizer   — collapse requirements into minimal SQL queries
  5. ValidationSuite  — assemble output container

Integration with existing pipeline
-----------------------------------
The DynamicSuiteGenerator is additive — it uses the existing
ColumnRuleMapping list (already produced by the main pipeline) for the
normalised ③/④ queries, and extends it with ⑤–⑯ from profiling.

Usage
-----
    from dynamic_suite import DynamicSuiteGenerator

    gen   = DynamicSuiteGenerator()
    suite = gen.generate(
        source_columns=pg_columns,       # from PostgresExtractor
        source_schema="public",
        source_table="orders",
        sf_database="MY_DB",
        sf_schema="MY_SCHEMA",
        sf_table="ORDERS",
        has_fivetran_active=True,
        active_mappings=rule_mappings,   # from existing pipeline
        use_ai_recommendations=True,
    )

    print(suite.to_combined_sql())
    print(suite.to_summary_dict())
"""

from __future__ import annotations

from typing import List, Optional

from sql_extractor.base_extractor import ColumnMetadata
from profiling.schema_profiler import SchemaProfiler
from profiling.validation_rule_engine import ValidationRuleEngine
from profiling.ai_recommendation import AIRecommendationEngine
from dynamic_suite.query_optimizer import QueryOptimizer
from dynamic_suite.validation_suite import ValidationSuite


class DynamicSuiteGenerator:
    """
    Orchestrates the full pipeline: profile → decide → optimise → SQL.

    Args
    ----
    api_key           : DIAL API key for AI recommendations (optional)
    api_base          : DIAL API base URL
    api_version       : DIAL API version
    model             : AI model deployment name
    use_ai_recommendations : If False, skip the AI recommendation step entirely
    """

    def __init__(
        self,
        api_key:               Optional[str] = None,
        api_base:              Optional[str] = None,
        api_version:           Optional[str] = None,
        model:                 Optional[str] = None,
    ):
        self._profiler     = SchemaProfiler()
        self._rule_engine  = ValidationRuleEngine()
        self._ai_engine    = AIRecommendationEngine(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            model=model,
        )
        self._optimizer    = QueryOptimizer()

    # -----------------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------------

    def generate(
        self,
        source_columns:         List[ColumnMetadata],
        source_schema:          str,
        source_table:           str,
        sf_database:            str,
        sf_schema:              str,
        sf_table:               str,
        has_fivetran_active:    bool = False,
        active_mappings:        Optional[list] = None,
        use_ai_recommendations: bool = True,
        generated_by:           str = "static",
        model_used:             str = "N/A",
    ) -> ValidationSuite:
        """
        Build the complete dynamic validation suite for one table pair.

        Args:
            source_columns         : ColumnMetadata from PostgresExtractor
            source_schema          : PostgreSQL schema
            source_table           : PostgreSQL table
            sf_database            : Snowflake database
            sf_schema              : Snowflake schema
            sf_table               : Snowflake table
            has_fivetran_active    : Add WHERE _FIVETRAN_ACTIVE = TRUE on SF side
            active_mappings        : ColumnRuleMapping list (for ③/④ normalised SQL)
            use_ai_recommendations : Call DIAL for business-rule suggestions
            generated_by           : 'ai' | 'static' | 'mixed'
            model_used             : Model name (for metadata)

        Returns:
            ValidationSuite with all generated queries.
        """
        sf_full = ".".join(p for p in [sf_database, sf_schema, sf_table] if p)

        # Step 1: Profile the table
        print(f"  [DynamicSuite] Profiling {source_schema}.{source_table}…")
        profile = self._profiler.profile(source_columns, source_schema, source_table)
        print(profile.summary())

        # Step 2: Decide which validations are needed
        requirements = self._rule_engine.decide(profile)
        conditional_count = sum(1 for r in requirements if r.is_conditional)
        print(
            f"  [DynamicSuite] {len(requirements)} validation type(s) decided "
            f"({conditional_count} conditional)."
        )
        for req in requirements:
            tag = " [conditional]" if req.is_conditional else " [baseline]"
            print(f"    {req.query_number_src}/{req.query_number_tgt} {req.label}{tag}")

        # Step 3: AI recommendations (optional)
        ai_recs = []
        if use_ai_recommendations:
            ai_recs = self._ai_engine.recommend(profile)

        # Step 4: Optimize into minimal SQL queries
        queries = self._optimizer.optimize(
            requirements=requirements,
            profile=profile,
            source_schema=source_schema,
            source_table=source_table,
            sf_full=sf_full,
            fivetran_active=has_fivetran_active,
            active_mappings=active_mappings,
        )
        print(
            f"  [DynamicSuite] Optimised to {len(queries)} query pair(s) "
            f"(down from {_naive_count(requirements)} naive queries)."
        )

        # Step 5: Assemble the suite
        suite = ValidationSuite(
            source_schema=source_schema,
            source_table=source_table,
            target_database=sf_database,
            target_schema=sf_schema,
            target_table=sf_table,
            profile=profile,
            requirements=requirements,
            queries=queries,
            ai_recommendations=ai_recs,
            generated_by=generated_by,
            model_used=model_used,
            has_fivetran_active=has_fivetran_active,
        )

        print(
            f"  [DynamicSuite] ✓ Suite ready: "
            f"{len(queries)} query pair(s), "
            f"{len(ai_recs)} AI recommendation(s)."
        )
        return suite


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _naive_count(requirements) -> int:
    """Estimate how many queries would have been needed without optimization."""
    return sum(2 for _ in requirements)  # 2 per requirement (source + target)
