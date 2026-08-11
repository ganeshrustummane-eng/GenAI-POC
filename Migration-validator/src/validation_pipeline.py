"""
Validation Pipeline — End-to-End Orchestrator
===============================================
Wires all modules together into a single callable pipeline.

New pipeline (run_with_plan — preferred):
  ┌─────────────────────────────────────────────────────────────────────┐
  │  1. Extract schemas       (PostgreSQL + Snowflake)                  │
  │  2. Exact matching        (case-insensitive + normalized name)      │
  │  3. Fuzzy matching        (RapidFuzz — top N candidates per col)   │
  │  4. Confidence scoring    (multi-factor: name+type+position+learned)│
  │  5. AI Rule Planner       (ONLY for ambiguous columns — token eff.) │
  │  6. Plan validation       (structural integrity check)              │
  │  7. SQL + YAML generation (deterministic from plan)                 │
  └─────────────────────────────────────────────────────────────────────┘

Legacy pipeline (run — backward-compatible, still works):
  ┌─────────────────────────────────────────────────────────────────────┐
  │  1. sql_extractor      → Extract live schema from PG + Snowflake    │
  │  2. ai_transformation  → Map columns + assign validation rules      │
  │     └── model selector → User picks AI model or static fallback     │
  │  3. generated_queries  → Build SQL + YAML output files              │
  └─────────────────────────────────────────────────────────────────────┘

PK-Free Design
--------------
Primary key handling is deferred to a future milestone.
All queries operate on full table scans without ORDER BY pk,
duplicate checks, or missing-row checks.

AI Model Selection
------------------
Pass model= to ValidationPipeline() to select which AI model to use:
  - "gpt-4o"           (default — best accuracy)
  - "gpt-4o-mini"      (faster, lower cost)
  - "gpt-4-turbo"
  - "claude-3-5-sonnet"
  - "gemini-pro"
  - Any model on your DIAL endpoint

Usage (Python API)
------------------
    from validation_pipeline import ValidationPipeline

    pipeline = ValidationPipeline(model="gpt-4o")
    result = pipeline.run(
        pg_schema="public",
        pg_table="events",
        sf_database="dev_edge_bronze",
        sf_schema="storedge_fms_public",
        sf_table="EVENTS",
    )
    print(result.summary())

Usage (CLI)
-----------
    python src/validation_pipeline.py \\
        --pg-table events --sf-table EVENTS

    python src/validation_pipeline.py \\
        --pg-table events --sf-table EVENTS --model gpt-4o-mini

Environment Variables (.env)
-----------------------------
    SOURCE_HOST, SOURCE_PORT, SOURCE_DATABASE
    SOURCE_USERNAME, SOURCE_PASSWORD, SOURCE_SCHEMA
    SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA
    SNOWFLAKE_USERNAME, SNOWFLAKE_PASSWORD
    DIAL_API_KEY      ← optional; enables AI rule mapping
    DIAL_MODEL        ← optional; default model name
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Load .env before any env-reading imports
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from sql_extractor import PostgresExtractor, SnowflakeExtractor
from sql_extractor.snowflake_extractor import FIVETRAN_ACTIVE_COLUMN
from ai_transformation import RuleMapperOrchestrator, AVAILABLE_MODELS
from generated_queries import QueryOutputManager, GenerationResult
from generated_queries.yaml_config_writer import YAMLConfigWriter
from dynamic_suite import DynamicSuiteGenerator

# New matching pipeline imports
from matching.candidate_matcher import CandidateMatcher
from ai.rule_planner import RulePlanner
from core.validation_plan import (
    CanonicalValidationPlan,
    ColumnMappingEntry,
    PlanStatus,
)
from validation.plan_validator import PlanValidator, PlanValidationError
from learning.retrieval import LearnedRuleRetriever


class ValidationPipeline:
    """
    Full end-to-end validation pipeline.

    Steps
    -----
      1. Extract live column metadata from PostgreSQL and Snowflake.
      2. Map source → target columns and assign transformation rules
         (AI if DIAL_API_KEY is set, static otherwise).
      3. Generate SQL validation queries + YAML config files.

    Model Selection
    ---------------
    Pass model= to the constructor to control which AI model is used.
    If DIAL_API_KEY is not set, static rule matching is used regardless.
    """

    def __init__(self, model: Optional[str] = None):
        """
        Args:
            model: AI model name to use (e.g. 'gpt-4o', 'gpt-4o-mini').
                   Defaults to DIAL_MODEL env var, then 'gpt-4o'.
                   Has no effect when DIAL_API_KEY is not set.
        """
        self._pg_extractor   = PostgresExtractor()
        self._sf_extractor   = SnowflakeExtractor()
        self._rule_mapper    = RuleMapperOrchestrator(model=model)
        self._output_mgr     = QueryOutputManager()
        self._yaml_writer    = YAMLConfigWriter()
        self._dynamic_gen    = DynamicSuiteGenerator(
            api_key=os.getenv("DIAL_API_KEY"),
            api_base=os.getenv("DIAL_API_BASE"),
            api_version=os.getenv("DIAL_API_VERSION"),
            model=model or os.getenv("DIAL_MODEL", "gpt-4o"),
        )

    def set_model(self, model: str) -> None:
        """
        Switch the AI model at runtime without recreating the pipeline.

        Args:
            model: Model name (e.g. 'gpt-4o-mini', 'claude-3-5-sonnet')
        """
        self._rule_mapper.set_model(model)
        print(f"  [Pipeline] AI model switched to '{model}'.")

    @property
    def active_model(self) -> str:
        """Return the currently active AI model name."""
        return self._rule_mapper.active_model

    @property
    def is_ai_active(self) -> bool:
        """Return True if AI mapping is configured (DIAL_API_KEY set)."""
        return self._rule_mapper.is_ai_active

    @staticmethod
    def list_available_models() -> List[str]:
        """Return all models available for selection."""
        return list(AVAILABLE_MODELS)

    def run(
        self,
        pg_schema: str,
        pg_table: str,
        sf_schema: str,
        sf_table: str,
        sf_database: Optional[str] = None,
        pg_database: Optional[str] = None,
    ) -> GenerationResult:
        """
        Run the complete validation pipeline for one table pair.

        Args:
            pg_schema   : PostgreSQL schema (e.g. 'public')
            pg_table    : PostgreSQL table name
            sf_schema   : Snowflake schema name
            sf_table    : Snowflake table name (UPPER recommended)
            sf_database : Snowflake database name
                          (default: SNOWFLAKE_DATABASE env var)
            pg_database : PostgreSQL database name
                          (default: SOURCE_DATABASE env var)

        Returns:
            GenerationResult with:
              .sql_path   — path to generated .sql file
              .yaml_path  — path to generated .yaml file
              .summary()  — human-readable result summary
        """
        _sf_db = sf_database or os.getenv("SNOWFLAKE_DATABASE", "")

        _pg_db = pg_database or os.getenv("SOURCE_DATABASE", "")
        _print_header(pg_schema, pg_table, _sf_db, sf_schema, sf_table, self, _pg_db)

        # ── Step 1: Extract schemas ──────────────────────────────────────────
        print("\n[1/3] Extracting column schemas from source and target databases...")
        src_columns = self._extract_source(pg_schema, pg_table, _pg_db)
        tgt_columns = self._extract_target(sf_schema, sf_table)

        # Detect Fivetran _FIVETRAN_ACTIVE on Snowflake side
        has_fivetran_active = SnowflakeExtractor.has_fivetran_active(tgt_columns)
        if has_fivetran_active:
            print(
                f"  ℹ  '{FIVETRAN_ACTIVE_COLUMN}' detected — "
                f"Snowflake queries will include WHERE _FIVETRAN_ACTIVE = TRUE."
            )

        print(f"\n  Schema Summary:")
        print(f"    PostgreSQL columns : {len(src_columns)}")
        print(f"    Snowflake  columns : {len(tgt_columns)}")

        # ── Step 2: Map columns + assign rules ───────────────────────────────
        print("\n[2/3] Mapping columns and assigning transformation rules...")
        mappings, explanation = self._rule_mapper.map_columns(
            source_columns=src_columns,
            target_columns=tgt_columns,
            table_name=pg_table,
        )

        if explanation:
            # Show first 400 chars of the AI reasoning in the terminal
            preview = explanation[:400].replace("\n", " ")
            print(f"\n  Rule mapping explanation:\n  {preview}...")

        # ── Step 3: Generate SQL + YAML ──────────────────────────────────────
        print("\n[3/3] Generating SQL validation queries and YAML config file...")
        generated_by = "AI" if self._rule_mapper.is_ai_active else "static"
        model_used   = self._rule_mapper.active_model if self._rule_mapper.is_ai_active else "N/A"

        result = self._output_mgr.generate(
            table_name=pg_table,
            pg_schema=pg_schema,
            pg_table=pg_table,
            sf_database=_sf_db,
            sf_schema=sf_schema,
            sf_table=sf_table,
            mappings=mappings,
            has_fivetran_active=has_fivetran_active,
            generated_by=generated_by,
            model_used=model_used,
        )

        # ── Dynamic suite (additive — runs after baseline) ────────────────────
        print("\n[+] Running dynamic validation suite generator...")
        try:
            suite = self._dynamic_gen.generate(
                source_columns=src_columns,
                source_schema=pg_schema,
                source_table=pg_table,
                sf_database=_sf_db,
                sf_schema=sf_schema,
                sf_table=sf_table,
                has_fivetran_active=has_fivetran_active,
                active_mappings=mappings,
                use_ai_recommendations=bool(os.getenv("DIAL_API_KEY")),
                generated_by=generated_by,
                model_used=model_used,
            )
            dyn_sql_path = result.sql_path.parent / f"{pg_table.lower()}_dynamic_suite.sql"
            dyn_sql_path.write_text(suite.to_combined_sql(), encoding="utf-8")
            print(f"  💾 Dynamic suite saved : {dyn_sql_path.resolve()}")
            result.dynamic_suite_path = dyn_sql_path
            dyn_yaml_path = self._yaml_writer.write_dynamic_suite(
                suite=suite,
                pg_table=pg_table,
                output_dir=result.sql_path.parent,
            )
            result.dynamic_suite_yaml_path = dyn_yaml_path
        except Exception as dyn_exc:
            print(f"  ⚠  Dynamic suite generation failed (baseline still saved): {dyn_exc}")

        return result

    def run_with_plan(
        self,
        pg_schema: str,
        pg_table: str,
        sf_schema: str,
        sf_table: str,
        sf_database: Optional[str] = None,
        pg_database: Optional[str] = None,
        explicit_mappings: Optional[dict] = None,
    ) -> "tuple[GenerationResult, CanonicalValidationPlan]":
        """
        Run the full new pipeline using the CanonicalValidationPlan architecture.

        7-step pipeline:
          1. Extract schemas from PostgreSQL + Snowflake
          2. Exact matching (case-insensitive + normalized)
          3. Fuzzy matching (RapidFuzz top-N candidates)
          4. Confidence scoring (multi-factor)
          5. AI Rule Planner (ONLY for ambiguous columns)
          6. Plan validation
          7. SQL + YAML generation from the plan

        Args:
            pg_schema        : PostgreSQL schema (e.g. 'public')
            pg_table         : PostgreSQL table name
            sf_schema        : Snowflake schema name
            sf_table         : Snowflake table name
            sf_database      : Snowflake database name
            pg_database      : PostgreSQL database name
            explicit_mappings: Optional {src_col: tgt_col} override dict

        Returns:
            (GenerationResult, CanonicalValidationPlan) tuple
        """
        _sf_db = sf_database or os.getenv("SNOWFLAKE_DATABASE", "")
        _pg_db = pg_database or os.getenv("SOURCE_DATABASE", "")

        _print_header_v2(pg_schema, pg_table, _sf_db, sf_schema, sf_table, self, _pg_db)

        # ── Step 1: Extract schemas ──────────────────────────────────────────
        print("\n[1/7] Extracting schemas from source and target databases...")
        src_columns = self._extract_source(pg_schema, pg_table, _pg_db)
        tgt_columns = self._extract_target(sf_schema, sf_table)

        has_fivetran_active = SnowflakeExtractor.has_fivetran_active(tgt_columns)
        if has_fivetran_active:
            print(f"  ℹ  Fivetran _FIVETRAN_ACTIVE detected — Snowflake queries will filter active records.")
        print(f"  PostgreSQL: {len(src_columns)} columns  |  Snowflake: {len(tgt_columns)} columns")

        # ── Steps 2-4: Deterministic matching ────────────────────────────────
        print("\n[2-4/7] Running exact + fuzzy + confidence-scoring matching pipeline...")
        retriever = LearnedRuleRetriever()
        learned   = retriever.all_examples()
        learned_dicts = [ex.to_dict() for ex in learned]

        matcher   = CandidateMatcher()
        decisions = matcher.match(
            source_columns=src_columns,
            target_columns=tgt_columns,
            explicit_mappings=explicit_mappings,
            learned_examples=learned_dicts,
        )

        resolved  = [d for d in decisions if d.is_resolved and not d.skip_validation]
        ai_needed = [d for d in decisions if d.needs_ai]
        skipped   = [d for d in decisions if d.skip_validation]

        print(f"  Exact/fuzzy resolved : {len(resolved)}")
        print(f"  Need AI review       : {len(ai_needed)}")
        print(f"  Skipped              : {len(skipped)}")

        # ── Step 5: AI for ambiguous only ────────────────────────────────────
        ai_calls_made    = 0
        ai_decision_map  = {}

        if ai_needed and self._rule_mapper.is_ai_active:
            print(f"\n[5/7] Sending {len(ai_needed)} ambiguous column(s) to AI...")
            planner = RulePlanner(
                api_key=os.getenv("DIAL_API_KEY", ""),
                model=self._rule_mapper.active_model,
            )
            planner_result = planner.resolve(
                ai_needed_decisions=ai_needed,
                table_name=pg_table,
                learned_examples=learned_dicts,
            )
            # Replace ai_needed decisions with planner's resolved decisions
            resolved_names  = {d.source_col.column_name for d in resolved}
            ai_resolved_map = {d.source_col.column_name: d for d in planner_result.decisions}

            decisions = []
            for orig in [d for d in matcher.match(src_columns, tgt_columns, explicit_mappings, learned_dicts)]:
                name = orig.source_col.column_name
                if name in ai_resolved_map:
                    decisions.append(ai_resolved_map[name])
                else:
                    decisions.append(orig)

            ai_calls_made   = planner_result.ai_calls_made
            ai_decision_map = planner_result.ai_decisions
            print(f"  AI calls made: {ai_calls_made}")
        elif ai_needed:
            print(f"\n[5/7] No DIAL_API_KEY — accepting best fuzzy for {len(ai_needed)} ambiguous column(s).")
        else:
            print(f"\n[5/7] No ambiguous columns — AI not needed.")

        # ── Build CanonicalValidationPlan ─────────────────────────────────────
        from rules import get_rule_for_type as _get_rule
        from matching.normalizer import normalize_column_name as _norm

        plan_mappings: List[ColumnMappingEntry] = []
        unmatched_src: List[str] = []
        ambiguities:   List[str] = []

        # Re-run final decisions (with AI results merged)
        final_decisions = decisions

        for dec in final_decisions:
            src = dec.source_col

            if dec.skip_validation:
                plan_mappings.append(ColumnMappingEntry(
                    source_column=src.column_name,
                    source_type=src.data_type,
                    source_normalized=_norm(src.column_name),
                    target_column=src.column_name,
                    target_type="",
                    target_normalized="",
                    match_method=dec.method or "skip",
                    confidence=dec.final_score,
                    transformation_rule="text",
                    reason=dec.skip_reason or "Skipped",
                    skip_validation=True,
                    skip_reason=dec.skip_reason,
                ))
                if not src.column_name.upper().startswith("_FIVETRAN_"):
                    unmatched_src.append(src.column_name)
                continue

            if dec.target_col is None:
                unmatched_src.append(src.column_name)
                continue

            tgt = dec.target_col

            # Get AI decision for rule/reason if available
            ai_dec     = ai_decision_map.get(src.column_name)
            rule_id    = ai_dec.transformation_rule if ai_dec else "text"
            reason_txt = ai_dec.reason if ai_dec else _default_reason(dec)
            ai_resolved = dec.method == "fuzzy_ai"

            # Confidence breakdown as dict
            breakdown_dict = None
            if dec.confidence:
                bd = dec.confidence
                breakdown_dict = {
                    "name_similarity":  round(bd.name_similarity, 3),
                    "type_compatibility": round(bd.type_compatibility, 3),
                    "position_proximity": round(bd.position_proximity, 3),
                    "learned_example":  round(bd.learned_example, 3),
                    "final_score":      round(bd.final_score, 3),
                }

            plan_mappings.append(ColumnMappingEntry(
                source_column=src.column_name,
                source_type=src.data_type,
                source_normalized=_norm(src.column_name),
                target_column=tgt.column_name,
                target_type=tgt.data_type,
                target_normalized=_norm(tgt.column_name),
                match_method=dec.method or "static",
                fuzzy_score=dec.fuzzy_score,
                confidence=dec.final_score,
                confidence_breakdown=breakdown_dict,
                transformation_rule=rule_id,
                reason=reason_txt,
                ai_resolved=ai_resolved,
                skip_validation=False,
            ))

        # Determine plan status
        if ambiguities:
            plan_status = PlanStatus.AMBIGUOUS.value
        elif unmatched_src:
            plan_status = PlanStatus.PARTIAL.value
        else:
            plan_status = PlanStatus.COMPLETE.value

        plan = CanonicalValidationPlan(
            source_database=_pg_db,
            source_schema=pg_schema,
            source_table=pg_table,
            target_database=_sf_db,
            target_schema=sf_schema,
            target_table=sf_table,
            mappings=plan_mappings,
            has_fivetran_active=has_fivetran_active,
            status=plan_status,
            unmatched_source_columns=unmatched_src,
            ai_calls_made=ai_calls_made,
            model_used=self._rule_mapper.active_model if self._rule_mapper.is_ai_active else "N/A",
            generated_by="ai" if self._rule_mapper.is_ai_active else "fuzzy",
        )

        # ── Step 6: Validate plan ─────────────────────────────────────────────
        print("\n[6/7] Validating canonical plan...")
        validator = PlanValidator()
        val_result = validator.validate(plan)
        if val_result.issues:
            for issue in val_result.issues:
                print(f"  ✗ {issue}")
        if val_result.warnings:
            for w in val_result.warnings:
                print(f"  ⚠ {w}")

        if not val_result:
            print("  Plan validation FAILED — SQL generation blocked.")
            raise PlanValidationError(val_result.issues)

        print(f"  Plan status: {plan.status.upper()}")
        for line in plan.summary_lines()[:6]:
            print(f"  {line}")

        # ── Step 7: Generate SQL + YAML ───────────────────────────────────────
        print("\n[7/7] Generating SQL validation queries and YAML config file...")
        result = self._output_mgr.generate_from_plan(plan)

        # ── Dynamic suite (additive) ───────────────────────────────────────────
        print("\n[+] Running dynamic validation suite generator...")
        try:
            from generated_queries.sql_query_generator import _plan_to_rule_mappings
            rule_mappings = _plan_to_rule_mappings(plan.active_mappings)
            suite = self._dynamic_gen.generate(
                source_columns=src_columns,
                source_schema=pg_schema,
                source_table=pg_table,
                sf_database=_sf_db,
                sf_schema=sf_schema,
                sf_table=sf_table,
                has_fivetran_active=has_fivetran_active,
                active_mappings=rule_mappings,
                use_ai_recommendations=bool(os.getenv("DIAL_API_KEY")),
                generated_by=plan.generated_by,
                model_used=plan.model_used,
            )
            dyn_sql_path = result.sql_path.parent / f"{pg_table.lower()}_dynamic_suite.sql"
            dyn_sql_path.write_text(suite.to_combined_sql(), encoding="utf-8")
            print(f"  💾 Dynamic suite saved : {dyn_sql_path.resolve()}")
            result.dynamic_suite_path = dyn_sql_path
            dyn_yaml_path = self._yaml_writer.write_dynamic_suite(
                suite=suite,
                pg_table=pg_table,
                output_dir=result.sql_path.parent,
            )
            result.dynamic_suite_yaml_path = dyn_yaml_path
        except Exception as dyn_exc:
            print(f"  ⚠  Dynamic suite generation failed (baseline still saved): {dyn_exc}")

        return result, plan

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _extract_source(self, schema: str, table: str, database: str = ""):
        """Extract PostgreSQL column metadata. Raises on failure."""
        try:
            return self._pg_extractor.extract_columns(schema, table, database=database or None)
        except Exception as exc:
            print(f"  ✗ PostgreSQL extraction failed for '{schema}.{table}': {exc}")
            raise

    def _extract_target(self, schema: str, table: str):
        """Extract Snowflake column metadata. Raises on failure."""
        try:
            return self._sf_extractor.extract_columns(schema, table)
        except Exception as exc:
            print(f"  ✗ Snowflake extraction failed for '{schema}.{table}': {exc}")
            raise


# ---------------------------------------------------------------------------
# Internal print helpers
# ---------------------------------------------------------------------------

def _default_reason(dec) -> str:
    """Generate a default reason string from a MatchDecision."""
    method = dec.method or "unknown"
    score  = dec.final_score
    return f"Matched by {method} (confidence={score:.2f})"


def _print_header_v2(
    pg_schema: str,
    pg_table: str,
    sf_db: str,
    sf_schema: str,
    sf_table: str,
    pipeline: ValidationPipeline,
    pg_db: str = "",
) -> None:
    sep = "=" * 65
    ai_line = (
        f"AI ({pipeline.active_model})"
        if pipeline.is_ai_active
        else "Static + Fuzzy (no DIAL_API_KEY)"
    )
    pg_label = f"{pg_db}.{pg_schema}.{pg_table}" if pg_db else f"{pg_schema}.{pg_table}"
    print(f"\n{sep}")
    print(f"  MIGRATION VALIDATOR — Plan-Driven Pipeline (v2)")
    print(f"  Source  : PostgreSQL  → {pg_label}")
    print(f"  Target  : Snowflake   → {sf_db}.{sf_schema}.{sf_table}")
    print(f"  Mode    : {ai_line}")
    print(f"  Steps   : Extract → Exact → Fuzzy → Score → AI(ambiguous only) → Validate → Generate")
    print(sep)


def _print_header(
    pg_schema: str,
    pg_table: str,
    sf_db: str,
    sf_schema: str,
    sf_table: str,
    pipeline: ValidationPipeline,
    pg_db: str = "",
) -> None:
    sep = "=" * 65
    ai_line = (
        f"AI ({pipeline.active_model})"
        if pipeline.is_ai_active
        else "Static (no DIAL_API_KEY)"
    )
    pg_label = f"{pg_db}.{pg_schema}.{pg_table}" if pg_db else f"{pg_schema}.{pg_table}"
    print(f"\n{sep}")
    print(f"  MIGRATION VALIDATOR — Validation Pipeline")
    print(f"  Source  : PostgreSQL  → {pg_label}")
    print(f"  Target  : Snowflake   → {sf_db}.{sf_schema}.{sf_table}")
    print(f"  Mode    : {ai_line}")
    print(sep)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migration Validator — PostgreSQL→Snowflake Validation SQL + YAML Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available AI Models (via DIAL):
  {', '.join(AVAILABLE_MODELS)}

Examples:
  python src/validation_pipeline.py --pg-table events --sf-table EVENTS
  python src/validation_pipeline.py --pg-table events --sf-table EVENTS --model gpt-4o-mini
  python src/validation_pipeline.py \\
      --pg-schema public --pg-table users \\
      --sf-schema MY_SCHEMA --sf-table USERS \\
      --sf-database MY_DB --model gpt-4-turbo
        """,
    )
    parser.add_argument(
        "--pg-schema",
        default=os.getenv("SOURCE_SCHEMA", "public"),
        help="PostgreSQL schema (default: SOURCE_SCHEMA env or 'public')",
    )
    parser.add_argument(
        "--pg-table",
        required=True,
        help="PostgreSQL source table name",
    )
    parser.add_argument(
        "--sf-schema",
        default=os.getenv("SNOWFLAKE_SCHEMA", ""),
        help="Snowflake schema (default: SNOWFLAKE_SCHEMA env)",
    )
    parser.add_argument(
        "--sf-table",
        required=True,
        help="Snowflake target table name",
    )
    parser.add_argument(
        "--sf-database",
        default=os.getenv("SNOWFLAKE_DATABASE", ""),
        help="Snowflake database (default: SNOWFLAKE_DATABASE env)",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("DIAL_MODEL", "gpt-4o"),
        choices=AVAILABLE_MODELS + ["gpt-4o"],  # allow any string too
        help=f"AI model to use. Choices: {', '.join(AVAILABLE_MODELS)}. Default: gpt-4o",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List all available AI models and exit",
    )
    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    if args.list_models:
        print("\nAvailable AI Models:")
        for m in AVAILABLE_MODELS:
            print(f"  • {m}")
        sys.exit(0)

    pipeline = ValidationPipeline(model=args.model)
    try:
        pipeline.run(
            pg_schema=args.pg_schema,
            pg_table=args.pg_table,
            sf_schema=args.sf_schema,
            sf_table=args.sf_table,
            sf_database=args.sf_database,
        )
    except Exception as err:
        print(f"\n✗ Pipeline failed: {err}", file=sys.stderr)
        sys.exit(1)
