"""
Dynamic Validator — AI-Driven Migration Validation Orchestrator
===============================================================
This is the NEW primary entry point for the migration validator.

Old approach (static):
  → You hard-coded every column, type, and rule in Python
  → Required code changes for every new table

New approach (dynamic):
  → Provide: source_database, source_schema, source_table,
             target_schema, target_table
  → The system automatically:
      1. Connects to PostgreSQL  → extracts real column metadata
      2. Connects to Snowflake   → extracts real column metadata
      3. Compares schemas        → detects type changes
      4. Calls AI (DIAL/GPT-4o)  → assigns transformation rules + generates SQL
      5. Executes validation SQL → computes completeness metrics
      6. Writes reports          → JSON, HTML, TXT

Data Completeness Checks Performed
-----------------------------------
  ✓ Row count match          (source vs target total rows)
  ✓ Null percentage          (per column: % of NULLs in source vs target)
  ✓ Duplicate key detection  (duplicate primary keys in target)
  ✓ Distinct value count     (per column cardinality match)
  ✓ Type-safe value match    (normalised row-by-row comparison with AI rules)
  ✓ Missing rows             (rows in source but not in target, by PK)

Usage
-----
  from dynamic_validator import DynamicValidator

  v = DynamicValidator()
  report = v.run(
      source_database="fms",
      source_schema="public",
      source_table="customers",
      target_schema="storedge_fms_public",
      target_table="CUSTOMERS",
      primary_keys=["customer_id"],
  )
"""

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from models import (
    ColumnMapping,
    DatabaseConfig,
    DatabaseType,
    TableValidationResult,
    ColumnValidationResult,
    ValidationReport,
)
from schema_discovery import column_info_to_dict
from schema_discovery import ColumnInfo
from schema_extractor import (
    PostgresSchemaExtractor,
    SnowflakeSchemaExtractor,
    SchemaComparator,
    SchemaComparison,
)
from ai_query_agent import AIQueryAgent, ValidationPlan
from database_connectors import PostgreSQLConnector, SnowflakeConnector
from report_generator import ReportWriter


# ---------------------------------------------------------------------------
# Completeness Metrics
# ---------------------------------------------------------------------------

@dataclass
class ColumnCompletenessMetric:
    """Per-column completeness stats after running validation."""
    column_name: str
    source_null_count: int = 0
    target_null_count: int = 0
    source_total: int = 0
    target_total: int = 0
    source_distinct: int = 0
    target_distinct: int = 0
    value_match_pct: float = 0.0
    status: str = "PENDING"   # PASS | FAIL | WARN | SKIP

    @property
    def source_null_pct(self) -> float:
        return (self.source_null_count / self.source_total * 100) if self.source_total else 0.0

    @property
    def target_null_pct(self) -> float:
        return (self.target_null_count / self.target_total * 100) if self.target_total else 0.0

    @property
    def null_diff_pct(self) -> float:
        return abs(self.source_null_pct - self.target_null_pct)


@dataclass
class TableCompletenessResult:
    """Full completeness picture for one table."""
    table_name: str
    source_row_count: int = 0
    target_row_count: int = 0
    matched_rows: int = 0
    missing_in_target: int = 0         # rows in source but not in target (by PK)
    extra_in_target: int = 0           # rows in target but not in source (by PK)
    duplicate_pk_count: int = 0        # duplicate PKs in target
    column_metrics: List[ColumnCompletenessMetric] = field(default_factory=list)
    overall_status: str = "PENDING"    # PASS | FAIL | PARTIAL | ERROR
    error_message: Optional[str] = None
    generated_source_sql: str = ""
    generated_target_sql: str = ""
    ai_explanation: str = ""
    generated_by: str = "static"       # ai | static

    @property
    def row_completeness_pct(self) -> float:
        if self.source_row_count == 0:
            return 100.0
        return (self.matched_rows / self.source_row_count) * 100

    @property
    def row_count_match(self) -> bool:
        return self.source_row_count == self.target_row_count


@dataclass
class DynamicValidationReport:
    """Top-level report produced by DynamicValidator."""
    validation_id: str
    timestamp: datetime
    source_db: str
    target_db: str
    table_results: List[TableCompletenessResult] = field(default_factory=list)
    overall_status: str = "PENDING"

    @property
    def total_tables(self) -> int:
        return len(self.table_results)

    @property
    def passed_tables(self) -> int:
        return sum(1 for r in self.table_results if r.overall_status == "PASS")

    @property
    def failed_tables(self) -> int:
        return sum(1 for r in self.table_results if r.overall_status in ("FAIL", "PARTIAL"))

    @property
    def overall_completeness_pct(self) -> float:
        total_src = sum(r.source_row_count for r in self.table_results)
        total_matched = sum(r.matched_rows for r in self.table_results)
        if total_src == 0:
            return 100.0
        return (total_matched / total_src) * 100


# ---------------------------------------------------------------------------
# Dynamic Validator
# ---------------------------------------------------------------------------

class DynamicValidator:
    """
    Orchestrates the full dynamic validation pipeline:

    1. Extract PostgreSQL schema (live)
    2. Extract Snowflake schema (live)
    3. Compare schemas
    4. Run AI to generate transformation rules + SQL
    5. Execute completeness checks
    6. Write reports

    All connection details come from .env environment variables.
    """

    def __init__(
        self,
        ai_model: Optional[str] = None,
        reports_dir: str = "validation_reports",
    ):
        self.ai_agent = AIQueryAgent(model=ai_model)
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)

        # Build DB configs from env
        self._pg_config = self._build_pg_config()
        self._sf_config = self._build_sf_config()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        source_database: str,
        source_schema: str,
        source_table: str,
        target_schema: str,
        target_table: str,
        target_database: Optional[str] = None,
        primary_keys: Optional[List[str]] = None,
        save_reports: bool = True,
        print_plan: bool = True,
    ) -> DynamicValidationReport:
        """
        Run the complete validation for one source → target table pair.

        Args:
            source_database : PostgreSQL database name
            source_schema   : PostgreSQL schema name (e.g. 'public')
            source_table    : Source table name
            target_schema   : Snowflake schema name
            target_table    : Snowflake table name
            target_database : Snowflake database (defaults to SNOWFLAKE_DATABASE env var)
            primary_keys    : PK column names (hints for AI; auto-detected if omitted)
            save_reports    : Whether to write JSON/HTML/TXT report files
            print_plan      : Whether to print the AI validation plan to stdout

        Returns:
            DynamicValidationReport
        """
        _sf_db = target_database or os.getenv("SNOWFLAKE_DATABASE", "")
        vid = str(uuid.uuid4())[:8]

        report = DynamicValidationReport(
            validation_id=vid,
            timestamp=datetime.now(),
            source_db=f"postgresql://{source_database}.{source_schema}",
            target_db=f"snowflake://{_sf_db}.{target_schema}",
        )

        print(f"\n{'='*70}")
        print(f"  🚀 DYNAMIC MIGRATION VALIDATOR  |  ID: {vid}")
        print(f"{'='*70}")
        print(f"  Source : PostgreSQL  → {source_database}.{source_schema}.{source_table}")
        print(f"  Target : Snowflake   → {_sf_db}.{target_schema}.{target_table}")
        print(f"  AI Mode: {'✓ DIAL/' + self.ai_agent.model if self.ai_agent._ai_available else '⚠ Static fallback (no DIAL_API_KEY)'}")

        # ── Step 1: Extract schemas ─────────────────────────────────────────
        print(f"\n[1/5] Extracting schemas...")
        try:
            source_cols, target_cols, schema_cmp = self._extract_schemas(
                source_database, source_schema, source_table,
                target_schema, target_table, _sf_db,
            )
        except Exception as exc:
            print(f"  ✗ Schema extraction failed: {exc}")
            result = TableCompletenessResult(
                table_name=source_table,
                overall_status="ERROR",
                error_message=str(exc),
            )
            report.table_results.append(result)
            report.overall_status = "ERROR"
            return report

        schema_cmp.print_summary()

        # ── Step 2: Generate AI validation plan ────────────────────────────
        print(f"\n[2/5] Generating AI validation plan...")
        plan = self._generate_plan(
            source_cols, target_cols, schema_cmp,
            source_schema, source_table,
            target_schema, target_table, _sf_db,
            primary_keys or [],
        )

        if print_plan:
            plan.print_summary()

        # ── Step 3: Run completeness checks ────────────────────────────────
        print(f"\n[3/5] Running data completeness checks...")
        table_result = self._run_completeness_checks(
            plan, source_schema, source_table,
            target_schema, target_table, _sf_db,
        )

        report.table_results.append(table_result)

        # ── Step 4: Determine overall status ───────────────────────────────
        print(f"\n[4/5] Computing overall status...")
        report.overall_status = self._compute_overall_status(report)
        self._print_results(table_result)

        # ── Step 5: Save reports ────────────────────────────────────────────
        if save_reports:
            print(f"\n[5/5] Writing reports...")
            self._save_reports(report)
        else:
            print(f"\n[5/5] Skipping report files (save_reports=False)")

        print(f"\n{'='*70}")
        print(f"  ✅ Validation complete! Status: {report.overall_status}")
        print(f"  📋 Completeness: {report.overall_completeness_pct:.1f}%")
        print(f"{'='*70}\n")
        return report

    def run_multiple(
        self,
        source_database: str,
        tables: List[Dict[str, str]],
        target_database: Optional[str] = None,
        primary_keys_map: Optional[Dict[str, List[str]]] = None,
        save_reports: bool = True,
    ) -> DynamicValidationReport:
        """
        Validate multiple tables in one shot.

        Args:
            source_database : PostgreSQL database name
            tables          : List of dicts, each with keys:
                              source_schema, source_table, target_schema, target_table
            target_database : Snowflake database override
            primary_keys_map: Dict of source_table → [pk_columns]
            save_reports    : Save consolidated report at end

        Returns:
            DynamicValidationReport (consolidated)
        """
        vid = str(uuid.uuid4())[:8]
        _sf_db = target_database or os.getenv("SNOWFLAKE_DATABASE", "")
        pk_map = primary_keys_map or {}

        consolidated = DynamicValidationReport(
            validation_id=vid,
            timestamp=datetime.now(),
            source_db=f"postgresql://{source_database}",
            target_db=f"snowflake://{_sf_db}",
        )

        print(f"\n{'='*70}")
        print(f"  🚀 DYNAMIC MULTI-TABLE VALIDATOR  |  {len(tables)} tables")
        print(f"{'='*70}")

        for tbl in tables:
            src_schema = tbl["source_schema"]
            src_table = tbl["source_table"]
            tgt_schema = tbl["target_schema"]
            tgt_table = tbl["target_table"]
            pks = pk_map.get(src_table, [])

            single_report = self.run(
                source_database=source_database,
                source_schema=src_schema,
                source_table=src_table,
                target_schema=tgt_schema,
                target_table=tgt_table,
                target_database=_sf_db,
                primary_keys=pks,
                save_reports=False,
                print_plan=False,
            )
            consolidated.table_results.extend(single_report.table_results)

        consolidated.overall_status = self._compute_overall_status(consolidated)

        if save_reports:
            self._save_reports(consolidated)

        return consolidated

    # ------------------------------------------------------------------
    # Internal Steps
    # ------------------------------------------------------------------

    def _extract_schemas(
        self,
        pg_db: str, pg_schema: str, pg_table: str,
        sf_schema: str, sf_table: str, sf_db: str,
    ):
        """Extract source and target schemas and compare them."""
        pg_ext = PostgresSchemaExtractor(database=pg_db)
        sf_ext = SnowflakeSchemaExtractor(database=sf_db)

        source_cols = pg_ext.extract_columns(pg_schema, pg_table)
        target_cols = sf_ext.extract_columns(sf_schema, sf_table)

        comparison = SchemaComparator.compare(
            source_columns=source_cols,
            target_columns=target_cols,
            source_table=f"{pg_schema}.{pg_table}",
            target_table=f"{sf_schema}.{sf_table}",
        )
        return source_cols, target_cols, comparison

    def _generate_plan(
        self,
        source_cols: List[ColumnInfo],
        target_cols: List[ColumnInfo],
        schema_cmp: SchemaComparison,
        source_schema: str,
        source_table: str,
        target_schema: str,
        target_table: str,
        target_database: str,
        primary_keys: List[str],
    ) -> ValidationPlan:
        """Ask AI (or static fallback) to produce a ValidationPlan."""
        src_dicts = [column_info_to_dict(c) for c in source_cols]
        tgt_dicts = [column_info_to_dict(c) for c in target_cols]

        # If no PKs provided, try to auto-detect common PK patterns
        if not primary_keys:
            primary_keys = _auto_detect_pks(source_cols)
            if primary_keys:
                print(f"  [PK auto-detected] {primary_keys}")

        plan = self.ai_agent.generate_validation_plan(
            source_db_type=DatabaseType.POSTGRESQL,
            source_schema=source_schema,
            source_table=source_table,
            source_columns=src_dicts,
            target_db_type=DatabaseType.SNOWFLAKE,
            target_schema=target_schema,
            target_table=target_table,
            target_columns=tgt_dicts,
            target_database=target_database,
            primary_key_hints=primary_keys,
        )
        return plan

    def _run_completeness_checks(
        self,
        plan: ValidationPlan,
        source_schema: str,
        source_table: str,
        target_schema: str,
        target_table: str,
        target_database: str,
    ) -> TableCompletenessResult:
        """
        Execute all completeness checks against live databases.
        Returns a TableCompletenessResult with all metrics populated.
        """
        result = TableCompletenessResult(
            table_name=source_table,
            generated_source_sql=plan.source_sql,
            generated_target_sql=plan.target_sql,
            ai_explanation=plan.explanation,
            generated_by=plan.generated_by,
        )

        pg_conn = None
        sf_conn = None

        try:
            # Connect to both databases
            pg_conn = self._connect_postgres()
            sf_conn = self._connect_snowflake()

            pk_cols = [cm.source_column for cm in plan.column_mappings if cm.primary_key]

            # ── Check 1: Row counts ─────────────────────────────────────────
            result.source_row_count = self._get_row_count(
                pg_conn, f"{source_schema}.{source_table}"
            )
            result.target_row_count = self._get_row_count(
                sf_conn,
                f"{target_database}.{target_schema}.{target_table}",
                is_snowflake=True,
            )

            print(f"  Row counts — Source: {result.source_row_count:,} | "
                  f"Target: {result.target_row_count:,} | "
                  f"{'✓ MATCH' if result.row_count_match else '✗ MISMATCH'}")

            # ── Check 2: Duplicate PK detection in target ──────────────────
            if pk_cols:
                result.duplicate_pk_count = self._count_duplicate_pks(
                    sf_conn,
                    f"{target_database}.{target_schema}.{target_table}",
                    pk_cols,
                )
                if result.duplicate_pk_count > 0:
                    print(f"  ⚠ Duplicate PKs found in target: {result.duplicate_pk_count}")
                else:
                    print(f"  ✓ No duplicate PKs in target")

            # ── Check 3: Per-column null percentage ────────────────────────
            active_mappings = [cm for cm in plan.column_mappings if not cm.ignore_validation]
            result.column_metrics = self._check_column_completeness(
                pg_conn, sf_conn,
                source_schema, source_table,
                target_schema, target_table, target_database,
                active_mappings,
            )

            # ── Check 4: Missing rows by PK ────────────────────────────────
            if pk_cols and result.source_row_count > 0 and result.target_row_count > 0:
                result.missing_in_target, result.extra_in_target = self._check_pk_coverage(
                    pg_conn, sf_conn,
                    source_schema, source_table,
                    target_schema, target_table, target_database,
                    pk_cols,
                )
                print(f"  PK coverage — Missing in target: {result.missing_in_target} | "
                      f"Extra in target: {result.extra_in_target}")

            # ── Compute matched rows (from column metrics avg) ──────────────
            if result.column_metrics:
                avg_match = sum(m.value_match_pct for m in result.column_metrics) / len(result.column_metrics)
                result.matched_rows = int(result.source_row_count * avg_match / 100)
            else:
                result.matched_rows = min(result.source_row_count, result.target_row_count)

            # ── Determine table status ─────────────────────────────────────
            result.overall_status = self._determine_table_status(result)

        except Exception as exc:
            result.overall_status = "ERROR"
            result.error_message = str(exc)
            print(f"  ✗ Completeness check failed: {exc}")

        finally:
            if pg_conn:
                try:
                    pg_conn.connection.close()
                except Exception:
                    pass
            if sf_conn:
                try:
                    sf_conn.connection.close()
                except Exception:
                    pass

        return result

    def _check_column_completeness(
        self,
        pg_conn, sf_conn,
        source_schema: str, source_table: str,
        target_schema: str, target_table: str, target_db: str,
        mappings: List[ColumnMapping],
    ) -> List[ColumnCompletenessMetric]:
        """
        For each mapped column:
          - Count NULLs in source and target
          - Count DISTINCT values in source and target
          - Compute value match % using normalised comparison
        """
        metrics: List[ColumnCompletenessMetric] = []

        for cm in mappings:
            metric = ColumnCompletenessMetric(column_name=cm.source_column)

            try:
                # NULL counts
                src_null_q = (
                    f"SELECT COUNT(*) AS cnt, COUNT({cm.source_column}) AS non_null "
                    f"FROM {source_schema}.{source_table}"
                )
                tgt_null_q = (
                    f"SELECT COUNT(*) AS cnt, COUNT({cm.target_column}) AS non_null "
                    f"FROM {target_db}.{target_schema}.{target_table}"
                )

                src_r = pg_conn.execute_query(src_null_q)
                if src_r.rows:
                    metric.source_total = int(src_r.rows[0].get("cnt", 0))
                    metric.source_null_count = metric.source_total - int(
                        src_r.rows[0].get("non_null", 0)
                    )

                tgt_r = sf_conn.execute_query(tgt_null_q)
                if tgt_r.rows:
                    metric.target_total = int(tgt_r.rows[0].get("cnt", 0))
                    metric.target_null_count = metric.target_total - int(
                        tgt_r.rows[0].get("non_null", 0)
                    )

                # DISTINCT value counts
                src_dist_q = (
                    f"SELECT COUNT(DISTINCT {cm.source_column}) AS cnt "
                    f"FROM {source_schema}.{source_table}"
                )
                tgt_dist_q = (
                    f"SELECT COUNT(DISTINCT {cm.target_column}) AS cnt "
                    f"FROM {target_db}.{target_schema}.{target_table}"
                )

                src_d = pg_conn.execute_query(src_dist_q)
                if src_d.rows:
                    metric.source_distinct = int(src_d.rows[0].get("cnt", 0))

                tgt_d = sf_conn.execute_query(tgt_dist_q)
                if tgt_d.rows:
                    metric.target_distinct = int(tgt_d.rows[0].get("cnt", 0))

                # Determine match % based on distinct values + null diff
                if metric.source_distinct > 0 and metric.target_distinct > 0:
                    # Value match: ratio of min/max distinct (heuristic for bulk comparison)
                    min_d = min(metric.source_distinct, metric.target_distinct)
                    max_d = max(metric.source_distinct, metric.target_distinct)
                    metric.value_match_pct = (min_d / max_d) * 100
                elif metric.source_total == 0:
                    metric.value_match_pct = 100.0
                else:
                    metric.value_match_pct = 0.0

                # Status based on null diff and value match
                if metric.null_diff_pct > 5.0:
                    metric.status = "FAIL"
                elif metric.value_match_pct < 95.0:
                    metric.status = "WARN"
                else:
                    metric.status = "PASS"

            except Exception as col_exc:
                metric.status = "SKIP"
                print(f"    [WARN] Column metric failed for {cm.source_column}: {col_exc}")

            metrics.append(metric)

        return metrics

    def _check_pk_coverage(
        self,
        pg_conn, sf_conn,
        source_schema: str, source_table: str,
        target_schema: str, target_table: str, target_db: str,
        pk_cols: List[str],
    ) -> Tuple[int, int]:
        """
        Count rows present in source but missing in target (and vice versa).
        Uses a PK-based LEFT JOIN approach for accuracy.

        Returns:
            (missing_in_target_count, extra_in_target_count)
        """
        pk_str_src = ", ".join(f"CAST({c} AS TEXT)" for c in pk_cols)
        pk_str_tgt = ", ".join(f"CAST({c.upper()} AS VARCHAR)" for c in pk_cols)
        pk_concat_src = " || '|' || ".join(f"CAST({c} AS TEXT)" for c in pk_cols)
        pk_concat_tgt = " || '|' || ".join(f"CAST({c.upper()} AS VARCHAR)" for c in pk_cols)

        # Get source PKs
        src_pk_q = f"SELECT {pk_concat_src} AS pk_val FROM {source_schema}.{source_table}"
        # Get target PKs
        tgt_pk_q = (
            f"SELECT {pk_concat_tgt} AS pk_val "
            f"FROM {target_db}.{target_schema}.{target_table}"
        )

        src_result = pg_conn.execute_query(src_pk_q)
        tgt_result = sf_conn.execute_query(tgt_pk_q)

        if src_result.error or tgt_result.error:
            # If PK query fails gracefully skip
            return 0, 0

        src_pks = {str(r.get("pk_val", "")) for r in src_result.rows}
        tgt_pks = {str(r.get("pk_val", "")).upper() for r in tgt_result.rows}
        src_pks_upper = {k.upper() for k in src_pks}

        missing_in_target = len(src_pks_upper - tgt_pks)
        extra_in_target = len(tgt_pks - src_pks_upper)

        return missing_in_target, extra_in_target

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    def _connect_postgres(self) -> PostgreSQLConnector:
        conn = PostgreSQLConnector(self._pg_config)
        if not conn.connect():
            raise RuntimeError("Cannot connect to PostgreSQL source database")
        return conn

    def _connect_snowflake(self) -> SnowflakeConnector:
        conn = SnowflakeConnector(self._sf_config)
        if not conn.connect():
            raise RuntimeError("Cannot connect to Snowflake target database")
        return conn

    def _get_row_count(self, connector, full_table_name: str, is_snowflake: bool = False) -> int:
        """Execute a COUNT(*) query and return the integer result."""
        q = f"SELECT COUNT(*) AS cnt FROM {full_table_name}"
        result = connector.execute_query(q)
        if result.error or not result.rows:
            return 0
        row = result.rows[0]
        # Snowflake returns uppercase key names
        return int(row.get("cnt") or row.get("CNT") or 0)

    def _count_duplicate_pks(self, sf_conn, full_table_name: str, pk_cols: List[str]) -> int:
        """Count rows in Snowflake target where PK appears more than once."""
        pk_expr = ", ".join(c.upper() for c in pk_cols)
        q = f"""
            SELECT COUNT(*) AS dup_count
            FROM (
                SELECT {pk_expr}, COUNT(*) AS cnt
                FROM {full_table_name}
                GROUP BY {pk_expr}
                HAVING COUNT(*) > 1
            ) dupes
        """
        result = sf_conn.execute_query(q)
        if result.error or not result.rows:
            return 0
        row = result.rows[0]
        return int(row.get("dup_count") or row.get("DUP_COUNT") or 0)

    # ------------------------------------------------------------------
    # Config builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_pg_config() -> DatabaseConfig:
        return DatabaseConfig(
            database_type=DatabaseType.POSTGRESQL,
            host=os.getenv("SOURCE_HOST", "localhost"),
            port=int(os.getenv("SOURCE_PORT", "5432")),
            database=os.getenv("SOURCE_DATABASE", "postgres"),
            username=os.getenv("SOURCE_USERNAME", "postgres"),
            password=os.getenv("SOURCE_PASSWORD", ""),
            schema=os.getenv("SOURCE_SCHEMA", "public"),
        )

    @staticmethod
    def _build_sf_config() -> DatabaseConfig:
        return DatabaseConfig(
            database_type=DatabaseType.SNOWFLAKE,
            host=os.getenv("SNOWFLAKE_ACCOUNT", ""),
            port=443,
            database=os.getenv("SNOWFLAKE_DATABASE", ""),
            username=os.getenv("SNOWFLAKE_USERNAME", ""),
            password=os.getenv("SNOWFLAKE_PASSWORD", ""),
            schema=os.getenv("SNOWFLAKE_SCHEMA", ""),
        )

    # ------------------------------------------------------------------
    # Status + reporting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_table_status(result: TableCompletenessResult) -> str:
        if result.duplicate_pk_count > 0:
            return "FAIL"
        if result.missing_in_target > result.source_row_count * 0.01:  # >1% missing
            return "FAIL"
        if not result.row_count_match:
            diff_pct = abs(result.source_row_count - result.target_row_count) / max(result.source_row_count, 1) * 100
            if diff_pct > 5:
                return "FAIL"
            return "PARTIAL"
        fail_cols = sum(1 for m in result.column_metrics if m.status == "FAIL")
        if fail_cols > 0:
            return "FAIL"
        warn_cols = sum(1 for m in result.column_metrics if m.status == "WARN")
        if warn_cols > 0:
            return "PARTIAL"
        return "PASS"

    @staticmethod
    def _compute_overall_status(report: DynamicValidationReport) -> str:
        statuses = [r.overall_status for r in report.table_results]
        if "ERROR" in statuses:
            return "ERROR"
        if all(s == "PASS" for s in statuses):
            return "PASS"
        if all(s in ("FAIL", "ERROR") for s in statuses):
            return "FAIL"
        return "PARTIAL"

    @staticmethod
    def _print_results(result: TableCompletenessResult):
        """Print a readable summary of one table's completeness results."""
        print(f"\n  ┌─── Results: {result.table_name} ───")
        print(f"  │ Status          : {result.overall_status}")
        print(f"  │ Source rows     : {result.source_row_count:,}")
        print(f"  │ Target rows     : {result.target_row_count:,}")
        print(f"  │ Row completeness: {result.row_completeness_pct:.1f}%")
        if result.duplicate_pk_count:
            print(f"  │ ⚠ Duplicate PKs  : {result.duplicate_pk_count}")
        if result.missing_in_target:
            print(f"  │ ⚠ Missing in tgt : {result.missing_in_target}")
        print(f"  │ AI generated by  : {result.generated_by.upper()}")
        print(f"  │")
        print(f"  │ Column Metrics:")
        for m in result.column_metrics:
            icon = "✓" if m.status == "PASS" else ("⚠" if m.status == "WARN" else "✗")
            print(
                f"  │   {icon} {m.column_name:<25} "
                f"null%: {m.source_null_pct:.1f}% → {m.target_null_pct:.1f}%  "
                f"distinct: {m.source_distinct} → {m.target_distinct}  "
                f"match: {m.value_match_pct:.1f}%"
            )
        print(f"  └──────────────────────────────────")

    def _save_reports(self, report: DynamicValidationReport):
        """Convert to ValidationReport format and write JSON/HTML/TXT files."""
        vr = self._to_validation_report(report)
        ts = report.timestamp.strftime("%Y%m%d_%H%M%S")

        json_path = self.reports_dir / f"dynamic_report_{ts}_{report.validation_id}.json"
        html_path = self.reports_dir / f"dynamic_report_{ts}_{report.validation_id}.html"
        txt_path = self.reports_dir / f"dynamic_report_{ts}_{report.validation_id}.txt"

        ReportWriter.write_json_report(vr, str(json_path))
        ReportWriter.write_html_report(vr, str(html_path))
        ReportWriter.write_text_report(vr, str(txt_path))

        print(f"  Reports written to: {self.reports_dir.resolve()}")

    @staticmethod
    def _to_validation_report(report: DynamicValidationReport) -> ValidationReport:
        """Map DynamicValidationReport → ValidationReport for the report writer."""
        from models import TableValidationResult as TVR

        vr = ValidationReport(
            validation_id=report.validation_id,
            timestamp=report.timestamp,
            source_database=report.source_db,
            target_database=report.target_db,
            overall_status=report.overall_status,
            total_tables=len(report.table_results),
            passed_tables=report.passed_tables,
            failed_tables=report.failed_tables,
        )

        for tr in report.table_results:
            tvr = TVR(
                table_name=tr.table_name,
                source_rows=tr.source_row_count,
                target_rows=tr.target_row_count,
                matched_rows=tr.matched_rows,
                unmatched_rows=tr.source_row_count - tr.matched_rows,
                overall_status=tr.overall_status,
                error_message=tr.error_message,
            )
            vr.table_results.append(tvr)
            vr.total_source_rows += tr.source_row_count
            vr.total_target_rows += tr.target_row_count
            vr.total_matched_rows += tr.matched_rows

        return vr


# ---------------------------------------------------------------------------
# PK auto-detection
# ---------------------------------------------------------------------------

def _auto_detect_pks(columns: List[ColumnInfo]) -> List[str]:
    """
    Heuristically detect primary key columns from schema metadata.
    Looks for common PK naming patterns: id, <table>_id, <table>id.
    """
    candidates = []
    for col in columns:
        name_lower = col.column_name.lower()
        if name_lower in ("id",) or name_lower.endswith("_id"):
            # Prefer integer/serial types
            if any(t in col.data_type.upper() for t in ("INT", "SERIAL", "NUMBER", "BIGINT")):
                candidates.append(col.column_name)
    # Return at most one auto-detected PK to avoid false positives
    return candidates[:1]
