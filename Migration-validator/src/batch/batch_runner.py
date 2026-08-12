"""
Batch Runner
=============
Orchestrates multi-table validation using a BatchConfig.

Output layout
--------------
    validation_sql/
    └── batch_run_<timestamp>/
        ├── _manifest.json
        ├── _execution_log.txt
        ├── <table1>/
        │   ├── <table1>_validation.sql
        │   ├── <table1>_validation.yaml
        │   ├── <table1>_dynamic_suite.sql
        │   └── <table1>_plan.json
        └── <table2>/
            └── ...

Usage (Python API)
-------------------
    from batch import load_batch_config, BatchRunner

    config = load_batch_config("tables.yaml")
    runner = BatchRunner(dry_run=False, verbose=False)
    runner.run(config)

Usage (CLI)
-----------
    python src/validate_cli.py batch --config tables.yaml
    python src/validate_cli.py batch --config tables.yaml --dry-run
    python src/validate_cli.py batch --config tables.yaml --verbose --workers 8
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from batch.config_parser import BatchConfig, TablePairConfig
from batch.manifest_writer import ManifestWriter, TableResult


# Default output root (project_root/validation_sql)
_OUTPUT_ROOT = Path(__file__).parent.parent.parent / "validation_sql"


class BatchRunner:
    """
    Runs validation for every table in a BatchConfig.

    Features:
        - Parallel execution via ThreadPoolExecutor
        - Graceful error handling — failures are logged and processing continues
        - Per-table output directories
        - _manifest.json after completion
        - Dry-run mode: prints what WOULD be done without executing
    """

    def __init__(
        self,
        dry_run:  bool = False,
        verbose:  bool = False,
        model:    Optional[str] = None,
        output_root: Optional[Path] = None,
    ):
        self.dry_run     = dry_run
        self.verbose     = verbose
        self.model       = model
        self.output_root = output_root or _OUTPUT_ROOT

    def run(self, config: BatchConfig) -> Path:
        """
        Run the full batch validation.

        Args:
            config: Parsed BatchConfig from load_batch_config().

        Returns:
            Path to the _manifest.json file written after the run.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        execution_id = f"batch_run_{ts}"
        run_dir = self.output_root / execution_id
        run_dir.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now()
        print(f"\n{'='*65}")
        print(f"  MIGRATION VALIDATOR — Batch Run")
        print(f"  Execution ID : {execution_id}")
        print(f"  Tables       : {len(config.tables)}")
        print(f"  Parallel     : {config.execution.parallel} (max_workers={config.execution.max_workers})")
        print(f"  Dry run      : {self.dry_run}")
        print(f"  Output dir   : {run_dir}")
        print(f"{'='*65}\n")

        if self.dry_run:
            self._print_dry_run_plan(config, run_dir)
            return run_dir / "_manifest.json"

        # ── Source extractor (shared — thread-safe read-only usage) ─────────
        from sql_extractor import ExtractorFactory, SnowflakeExtractor
        src_cfg = config.source
        tgt_cfg = config.target

        results: List[TableResult] = []

        if config.execution.parallel and len(config.tables) > 1:
            results = self._run_parallel(config, run_dir, src_cfg, tgt_cfg)
        else:
            for pair in config.tables:
                result = self._process_table(pair, config, run_dir, src_cfg, tgt_cfg)
                results.append(result)
                if result.status == "failed" and config.execution.fail_fast:
                    print(f"\n  ✗ fail_fast=true — stopping after failure on '{pair.source_table}'")
                    break

        completed_at = datetime.now()

        # Write manifest
        writer = ManifestWriter()
        manifest_path = writer.write(
            run_dir=run_dir,
            execution_id=execution_id,
            started_at=started_at,
            completed_at=completed_at,
            config_path=str(config.config_path),
            table_results=results,
        )

        # Print summary
        successful = sum(1 for r in results if r.status == "success")
        failed     = sum(1 for r in results if r.status == "failed")
        duration   = (completed_at - started_at).total_seconds()

        print(f"\n{'='*65}")
        print(f"  BATCH COMPLETE")
        print(f"  Successful   : {successful} / {len(results)}")
        print(f"  Failed       : {failed}")
        print(f"  Duration     : {duration:.1f}s")
        print(f"  Manifest     : {manifest_path}")
        print(f"{'='*65}\n")

        return manifest_path

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _run_parallel(self, config, run_dir, src_cfg, tgt_cfg) -> List[TableResult]:
        """Fan out table processing across a ThreadPoolExecutor."""
        max_w = min(config.execution.max_workers, len(config.tables))
        results = [None] * len(config.tables)

        with ThreadPoolExecutor(max_workers=max_w) as executor:
            future_to_index = {
                executor.submit(
                    self._process_table,
                    pair, config, run_dir, src_cfg, tgt_cfg,
                ): idx
                for idx, pair in enumerate(config.tables)
            }
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                pair = config.tables[idx]
                try:
                    result = future.result()
                except Exception as exc:
                    result = TableResult(
                        source_table=pair.source_table,
                        target_table=pair.target_table,
                        status="failed",
                        error=str(exc),
                    )
                results[idx] = result

                icon = "✓" if result.status == "success" else "✗"
                print(
                    f"  {icon} [{result.status.upper():7}] "
                    f"{result.source_table} → {result.target_table}  "
                    f"({result.duration_seconds:.1f}s)"
                )

                if result.status == "failed" and config.execution.fail_fast:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

        return [r for r in results if r is not None]

    def _process_table(
        self,
        pair:    TablePairConfig,
        config:  BatchConfig,
        run_dir: Path,
        src_cfg,
        tgt_cfg,
    ) -> TableResult:
        """
        Process a single table pair end-to-end.
        Returns a TableResult regardless of success/failure.
        """
        start = time.time()
        table_dir = run_dir / pair.source_table.lower()
        table_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n  ── Processing: {pair.source_table} → {pair.target_table} ──")

        try:
            result = self._run_pipeline_for_pair(pair, config, src_cfg, tgt_cfg, table_dir)
            result.duration_seconds = time.time() - start
            return result
        except Exception as exc:
            if self.verbose:
                traceback.print_exc()
            else:
                print(f"  ✗ FAILED: {pair.source_table}: {exc}")
            return TableResult(
                source_table=pair.source_table,
                target_table=pair.target_table,
                status="failed",
                duration_seconds=time.time() - start,
                error=str(exc),
            )

    def _run_pipeline_for_pair(
        self,
        pair:      TablePairConfig,
        config:    BatchConfig,
        src_cfg,
        tgt_cfg,
        table_dir: Path,
    ) -> TableResult:
        """
        Wire source extractor + pipeline for one table pair.
        Overrides extractors to use the batch src_cfg/tgt_cfg credentials.
        """
        from sql_extractor import ExtractorFactory, SnowflakeExtractor

        # Build per-table extractors with batch credentials
        src_extractor = ExtractorFactory.create(
            src_cfg.db_type,
            host=src_cfg.host,
            port=src_cfg.port,
            database=src_cfg.database,
            username=src_cfg.username,
            password=src_cfg.password,
        )
        sf_extractor = SnowflakeExtractor(
            account=tgt_cfg.account,
            database=tgt_cfg.database,
            username=tgt_cfg.username,
            password=tgt_cfg.password,
        )

        src_schema = pair.source_schema_override or src_cfg.schema
        tgt_schema = pair.target_schema_override or tgt_cfg.schema

        # Extract columns
        src_columns = src_extractor.extract_columns(src_schema, pair.source_table)
        tgt_columns = sf_extractor.extract_columns(tgt_schema, pair.target_table)

        has_fivetran = sf_extractor.has_fivetran_active(tgt_columns)

        # PK detection — prefer YAML-declared PKs, fall back to DB detection
        if pair.primary_keys:
            from sql_extractor.extractors import PrimaryKeyInfo
            src_pk = PrimaryKeyInfo(
                table_name=pair.source_table,
                columns=pair.primary_keys,
                detected=True,
                detection_note="Declared in batch YAML",
            )
            # For target we use the same column names unless a mapping resolves them
            # (pk_mismatch handled in plan)
            tgt_pk = src_pk
        else:
            src_pk = src_extractor.detect_primary_key(src_schema, pair.source_table)
            tgt_pk = sf_extractor.detect_primary_key(tgt_schema, pair.target_table)

        # Run matching + plan + SQL generation via ValidationPipeline internals
        from validation_pipeline import ValidationPipeline
        from generated_queries import QueryOutputManager
        from generated_queries.yaml_config_writer import YAMLConfigWriter
        from matching.candidate_matcher import CandidateMatcher
        from ai.rule_planner import RulePlanner
        from core.validation_plan import CanonicalValidationPlan, ColumnMappingEntry, PlanStatus
        from matching.normalizer import normalize_column_name as _norm
        from learning.retrieval import LearnedRuleRetriever
        from rules import get_rule_for_type
        from dataclasses import replace as _dc_replace

        retriever = LearnedRuleRetriever()
        learned_dicts = [ex.to_dict() for ex in retriever.all_examples()]

        matcher = CandidateMatcher()
        decisions = matcher.match(
            source_columns=src_columns,
            target_columns=tgt_columns,
            explicit_mappings=pair.explicit_mappings or None,
            learned_examples=learned_dicts,
        )

        # AI resolution for ambiguous (if DIAL key present)
        dial_key = os.getenv("DIAL_API_KEY", "")
        ai_calls_made = 0
        ai_decision_map = {}
        ai_needed = [d for d in decisions if d.needs_ai]

        if ai_needed and dial_key:
            planner = RulePlanner(api_key=dial_key, model=self.model or os.getenv("DIAL_MODEL", "gpt-4o"))
            result_plan = planner.resolve(
                ai_needed_decisions=ai_needed,
                table_name=pair.source_table,
                learned_examples=learned_dicts,
            )
            ai_calls_made   = result_plan.ai_calls_made
            ai_decision_map = result_plan.ai_decisions
            ai_resolved_map = {d.source_col.column_name: d for d in result_plan.decisions}
            decisions = [
                ai_resolved_map.get(d.source_col.column_name, d) for d in decisions
            ]

        # Build plan
        plan_mappings = []
        unmatched_src = []
        for dec in decisions:
            src = dec.source_col
            if dec.skip_validation:
                if not src.column_name.upper().startswith("_FIVETRAN_"):
                    unmatched_src.append(src.column_name)
                plan_mappings.append(ColumnMappingEntry(
                    source_column=src.column_name,
                    source_type=src.data_type,
                    source_normalized=_norm(src.column_name),
                    target_column=src.column_name,
                    target_type="",
                    target_normalized="",
                    match_method="skip",
                    confidence=dec.final_score,
                    transformation_rule="text",
                    reason="Skipped",
                    skip_validation=True,
                    skip_reason=dec.skip_reason or "No match",
                ))
                continue
            if dec.target_col is None:
                unmatched_src.append(src.column_name)
                continue
            tgt = dec.target_col
            ai_dec   = ai_decision_map.get(src.column_name)
            rule_id  = ai_dec.transformation_rule if ai_dec else "text"
            reason   = ai_dec.reason if ai_dec else f"Matched by {dec.method}"
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
                transformation_rule=rule_id,
                reason=reason,
                ai_resolved=dec.method == "fuzzy_ai",
                skip_validation=False,
            ))

        # Determine PK mismatch
        src_pk_cols = src_pk.columns if src_pk.has_pk else []
        tgt_pk_cols = tgt_pk.columns if tgt_pk.has_pk else []
        pk_mismatch = False
        pk_mismatch_reason = ""
        if src_pk_cols and tgt_pk_cols:
            if [_norm(c) for c in src_pk_cols] != [_norm(c) for c in tgt_pk_cols]:
                pk_mismatch = True
                pk_mismatch_reason = (
                    f"Source PK {src_pk_cols} ≠ target PK {tgt_pk_cols} — verify mapping manually."
                )

        # Mark PK columns
        src_pk_upper = {c.upper() for c in src_pk_cols}
        for i, m in enumerate(plan_mappings):
            if m.source_column.upper() in src_pk_upper:
                plan_mappings[i] = _dc_replace(m, is_primary_key=True)

        plan_warnings = []
        if not src_pk_cols:
            plan_warnings.append(f"No PK detected — duplicate/missing row checks skipped.")
        if pk_mismatch:
            plan_warnings.append(f"PK mismatch (WARNING): {pk_mismatch_reason}")

        plan_status = PlanStatus.PARTIAL.value if unmatched_src else PlanStatus.COMPLETE.value

        plan = CanonicalValidationPlan(
            source_database=src_cfg.database,
            source_schema=src_schema,
            source_table=pair.source_table,
            target_database=tgt_cfg.database,
            target_schema=tgt_schema,
            target_table=pair.target_table,
            mappings=plan_mappings,
            has_fivetran_active=has_fivetran,
            source_primary_keys=src_pk_cols,
            target_primary_keys=tgt_pk_cols,
            pk_mismatch=pk_mismatch,
            pk_mismatch_reason=pk_mismatch_reason,
            status=plan_status,
            warnings=plan_warnings,
            unmatched_source_columns=unmatched_src,
            ai_calls_made=ai_calls_made,
            model_used=self.model or os.getenv("DIAL_MODEL", "N/A"),
            generated_by="ai" if (ai_calls_made > 0) else "fuzzy",
        )

        # Save plan JSON
        plan_path = table_dir / f"{pair.source_table.lower()}_plan.json"
        with open(plan_path, "w", encoding="utf-8") as f:
            import json as _json
            _json.dump(plan.to_dict(), f, indent=2, ensure_ascii=False)

        # Generate SQL + YAML into table_dir
        out_mgr = QueryOutputManager(output_dir=table_dir)
        gen_result = out_mgr.generate_from_plan(plan)

        # Dynamic suite
        dyn_sql_path_str = ""
        try:
            from dynamic_suite import DynamicSuiteGenerator
            from generated_queries.sql_query_generator import _plan_to_rule_mappings
            from generated_queries.yaml_config_writer import YAMLConfigWriter

            rule_mappings = _plan_to_rule_mappings(plan.active_mappings)
            dyn_gen = DynamicSuiteGenerator(
                api_key=dial_key or None,
                model=self.model or os.getenv("DIAL_MODEL", "gpt-4o"),
            )
            suite = dyn_gen.generate(
                source_columns=src_columns,
                source_schema=src_schema,
                source_table=pair.source_table,
                sf_database=tgt_cfg.database,
                sf_schema=tgt_schema,
                sf_table=pair.target_table,
                has_fivetran_active=has_fivetran,
                active_mappings=rule_mappings,
                use_ai_recommendations=bool(dial_key),
                generated_by=plan.generated_by,
                model_used=plan.model_used,
            )
            dyn_sql_path = table_dir / f"{pair.source_table.lower()}_dynamic_suite.sql"
            dyn_sql_path.write_text(suite.to_combined_sql(), encoding="utf-8")
            dyn_sql_path_str = str(dyn_sql_path)
        except Exception as dyn_exc:
            print(f"  ⚠  Dynamic suite failed for {pair.source_table}: {dyn_exc}")

        active_count = len(plan.active_mappings)
        return TableResult(
            source_table=pair.source_table,
            target_table=pair.target_table,
            status="success",
            sql_path=str(gen_result.sql_path),
            yaml_path=str(gen_result.yaml_path),
            plan_path=str(plan_path),
            dynamic_sql_path=dyn_sql_path_str,
            columns_matched=active_count,
            primary_keys=src_pk_cols,
            ai_calls_made=ai_calls_made,
        )

    def _print_dry_run_plan(self, config: BatchConfig, run_dir: Path) -> None:
        """Print what WOULD happen without executing."""
        print(f"  [DRY RUN] Would create: {run_dir}")
        print(f"  [DRY RUN] Source: {config.source.db_type} @ {config.source.host}/{config.source.database}.{config.source.schema}")
        print(f"  [DRY RUN] Target: snowflake @ {config.target.database}.{config.target.schema}")
        print(f"\n  [DRY RUN] Tables ({len(config.tables)}):")
        for i, pair in enumerate(config.tables, 1):
            pk_str = f" PK={pair.primary_keys}" if pair.primary_keys else " PK=auto-detect"
            map_str = f" explicit_mappings={pair.explicit_mappings}" if pair.explicit_mappings else ""
            print(f"    {i:3}. {pair.source_table} → {pair.target_table}{pk_str}{map_str}")
        print(f"\n  [DRY RUN] Would generate:")
        print(f"    {run_dir}/_manifest.json")
        print(f"    {run_dir}/_execution_log.txt")
        for pair in config.tables:
            tbl_dir = run_dir / pair.source_table.lower()
            print(f"    {tbl_dir}/{pair.source_table.lower()}_validation.sql")
            print(f"    {tbl_dir}/{pair.source_table.lower()}_validation.yaml")
            print(f"    {tbl_dir}/{pair.source_table.lower()}_dynamic_suite.sql")
            print(f"    {tbl_dir}/{pair.source_table.lower()}_plan.json")
        print()
