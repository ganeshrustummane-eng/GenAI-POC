"""
Query Executor — Run & Display Validation Query Results
========================================================
After the AI generates the SQL queries, this module executes them
against the live PostgreSQL and Snowflake databases and displays
results in a clean, readable format.

Flow
----
  1. User reviews the generated SQL (printed by query_builder.py)
  2. User types "execute" in the CLI
  3. This module runs each query one by one:
       ① Row Count      → PostgreSQL
       ② Row Count      → Snowflake
       ③ Main Validation → PostgreSQL   (first 20 rows shown)
       ④ Main Validation → Snowflake    (first 20 rows shown)
       ⑤ NULL % Check   → PostgreSQL
       ⑥ NULL % Check   → Snowflake
       ⑦ Duplicate PK   → Snowflake
       ⑧ Missing Rows   → both DBs, auto-compared
  4. After each query: PASS / FAIL / WARN verdict is shown
  5. Final summary table printed at the end

Usage
-----
  from query_executor import QueryExecutor
  executor = QueryExecutor(pg_config, sf_config)
  executor.execute_all(query_result)
"""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from models import DatabaseConfig, DatabaseType
from database_connectors import PostgreSQLConnector, SnowflakeConnector


# ─────────────────────────────────────────────────────────────────────────────
# Result containers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class QueryExecutionResult:
    """Result of executing a single query."""
    query_label: str          # e.g. "① ROW COUNT — PostgreSQL"
    database: str             # "postgresql" | "snowflake"
    sql: str                  # The executed SQL
    rows: List[Dict] = field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    status: str = "PENDING"   # PASS | FAIL | WARN | ERROR | SKIP
    verdict_reason: str = ""  # Human-readable explanation
    error: str = ""


@dataclass
class ValidationExecutionSummary:
    """Full summary after executing all queries."""
    table_name: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    results: List[QueryExecutionResult] = field(default_factory=list)
    overall_status: str = "PENDING"

    # Key metrics
    source_row_count: int = 0
    target_row_count: int = 0
    duplicate_pk_count: int = 0
    missing_in_target: int = 0
    extra_in_target: int = 0

    @property
    def row_count_match(self) -> bool:
        return self.source_row_count == self.target_row_count

    @property
    def completeness_pct(self) -> float:
        if self.source_row_count == 0:
            return 100.0
        matched = self.source_row_count - self.missing_in_target
        return round(matched / self.source_row_count * 100, 2)


# ─────────────────────────────────────────────────────────────────────────────
# ANSI colours (reused from validate_cli.py style)
# ─────────────────────────────────────────────────────────────────────────────

class C:
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    CYAN   = "\033[96m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"


def _pass(msg):  print(f"{C.GREEN}  ✓ {msg}{C.RESET}")
def _fail(msg):  print(f"{C.RED}  ✗ {msg}{C.RESET}")
def _warn(msg):  print(f"{C.YELLOW}  ⚠ {msg}{C.RESET}")
def _info(msg):  print(f"{C.CYAN}  ▶ {msg}{C.RESET}")
def _dim(msg):   print(f"{C.DIM}  {msg}{C.RESET}")
def _head(msg):  print(f"\n{C.BOLD}{C.CYAN}{msg}{C.RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# Query Executor
# ─────────────────────────────────────────────────────────────────────────────

class QueryExecutor:
    """
    Executes all 8 generated validation queries against live databases
    and produces a structured summary with PASS / FAIL / WARN verdicts.
    """

    # Max rows to display in terminal for main validation queries
    DISPLAY_ROWS = 20

    # Tolerance thresholds
    NULL_DIFF_THRESHOLD_PCT = 5.0    # FAIL if null% differs by more than this
    ROW_COUNT_WARN_DIFF_PCT = 1.0    # WARN if row counts differ by ≤ 1%
    ROW_COUNT_FAIL_DIFF_PCT = 5.0    # FAIL if row counts differ by > 5%

    def __init__(self):
        self._pg_conn: Optional[PostgreSQLConnector] = None
        self._sf_conn: Optional[SnowflakeConnector] = None

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def execute_all(self, query_result, pg_database: str = None) -> ValidationExecutionSummary:
        """
        Execute all queries in query_result one by one.
        Prompts user before each query group.
        Shows results + verdict after each.

        Args:
            query_result : QueryResult from query_builder.QueryBuilder.build()
            pg_database  : PostgreSQL database name (for connector config)

        Returns:
            ValidationExecutionSummary with all results
        """
        summary = ValidationExecutionSummary(table_name=query_result.table_name)

        _head(f"{'═'*66}")
        _head(f"  🚀  EXECUTING VALIDATION QUERIES  |  {query_result.table_name}")
        _head(f"{'═'*66}")
        print(f"\n  {C.DIM}Queries will be executed one at a time.")
        print(f"  You will see the result + verdict after each query.{C.RESET}\n")

        # ── Connect to both databases ─────────────────────────────────────────
        try:
            _info("Connecting to PostgreSQL...")
            self._pg_conn = self._connect_postgres(pg_database)
            _pass("PostgreSQL connected")

            _info("Connecting to Snowflake...")
            self._sf_conn = self._connect_snowflake()
            _pass("Snowflake connected")
        except Exception as exc:
            _fail(f"Connection failed: {exc}")
            _fail("Cannot execute queries. Run: python check_connections.py")
            summary.overall_status = "ERROR"
            return summary

        try:
            # ── ① Row count — PostgreSQL ──────────────────────────────────────
            r1 = self._run_query(
                label="① ROW COUNT — PostgreSQL",
                sql=query_result.row_count_source_sql,
                db="postgresql",
            )
            summary.results.append(r1)
            if r1.rows:
                summary.source_row_count = int(
                    r1.rows[0].get("source_row_count", 0)
                )
            self._print_rows(r1.rows, max_rows=5)
            print()

            # ── ② Row count — Snowflake ───────────────────────────────────────
            r2 = self._run_query(
                label="② ROW COUNT — Snowflake",
                sql=query_result.row_count_target_sql,
                db="snowflake",
            )
            summary.results.append(r2)
            if r2.rows:
                summary.target_row_count = int(
                    r2.rows[0].get("target_row_count", 0)
                )
            self._print_rows(r2.rows, max_rows=5)

            # Verdict: row count match
            r1.status, r2.status, row_verdict = self._verdict_row_count(
                summary.source_row_count, summary.target_row_count
            )
            r1.verdict_reason = row_verdict
            r2.verdict_reason = row_verdict
            self._print_verdict_box(
                "ROW COUNT CHECK",
                row_verdict,
                r1.status,
                extra=[
                    f"Source (PostgreSQL) : {summary.source_row_count:,} rows",
                    f"Target (Snowflake)  : {summary.target_row_count:,} rows",
                    f"Difference          : {abs(summary.source_row_count - summary.target_row_count):,} rows",
                ]
            )

            # ── ⑤ NULL % — PostgreSQL ─────────────────────────────────────────
            if query_result.null_check_source_sql:
                _head(f"\n  {'─'*60}")
                r5 = self._run_query(
                    label="⑤ NULL % CHECK — PostgreSQL",
                    sql=query_result.null_check_source_sql,
                    db="postgresql",
                )
                summary.results.append(r5)
                self._print_rows(r5.rows, max_rows=5, transpose=True)
                print()

                # ── ⑥ NULL % — Snowflake ──────────────────────────────────────
                r6 = self._run_query(
                    label="⑥ NULL % CHECK — Snowflake",
                    sql=query_result.null_check_target_sql,
                    db="snowflake",
                )
                summary.results.append(r6)
                self._print_rows(r6.rows, max_rows=5, transpose=True)

                # Compare null %
                null_verdicts = self._verdict_null_pct(r5.rows, r6.rows)
                overall_null_status = (
                    "FAIL" if any(v[2] == "FAIL" for v in null_verdicts)
                    else "WARN" if any(v[2] == "WARN" for v in null_verdicts)
                    else "PASS"
                )
                r5.status = overall_null_status
                r6.status = overall_null_status

                self._print_null_comparison(null_verdicts)

            # ── ⑦ Duplicate PK — Snowflake ────────────────────────────────────
            if query_result.duplicate_pk_sql:
                _head(f"\n  {'─'*60}")
                r7 = self._run_query(
                    label="⑦ DUPLICATE PK CHECK — Snowflake",
                    sql=query_result.duplicate_pk_sql,
                    db="snowflake",
                )
                summary.results.append(r7)
                summary.duplicate_pk_count = r7.row_count

                if r7.row_count == 0:
                    r7.status = "PASS"
                    r7.verdict_reason = "No duplicate primary keys found in target ✓"
                    _pass(r7.verdict_reason)
                else:
                    r7.status = "FAIL"
                    r7.verdict_reason = f"{r7.row_count} duplicate PK(s) found in Snowflake!"
                    _fail(r7.verdict_reason)
                    self._print_rows(r7.rows, max_rows=10)

                self._print_verdict_box("DUPLICATE PK CHECK", r7.verdict_reason, r7.status)

            # ── ⑧ Missing Rows ────────────────────────────────────────────────
            if query_result.missing_rows_sql:
                _head(f"\n  {'─'*60}")
                _info("⑧ MISSING ROWS CHECK — comparing PKs between source and target...")

                # Step 1 — PostgreSQL PKs
                step1_sql = query_result.missing_rows_sql.split("-- Step 2")[0].strip()
                # Clean up comment lines, keep only the SELECT
                step1_lines = [
                    l for l in step1_sql.split("\n")
                    if not l.strip().startswith("--") or "Step 1" in l
                ]
                step1_clean = "\n".join(
                    l for l in step1_sql.split("\n")
                    if not l.strip().startswith("--")
                ).strip()

                r8_src = self._run_query(
                    label="⑧ MISSING ROWS — PostgreSQL PKs",
                    sql=step1_clean,
                    db="postgresql",
                )
                summary.results.append(r8_src)

                # Step 2 — Snowflake PKs
                step2_sql = _extract_step2_sql(query_result.missing_rows_sql)
                r8_tgt = self._run_query(
                    label="⑧ MISSING ROWS — Snowflake PKs",
                    sql=step2_sql,
                    db="snowflake",
                )
                summary.results.append(r8_tgt)

                # Compare PKs
                missing_in_tgt, extra_in_tgt = self._compare_pk_sets(
                    r8_src.rows, r8_tgt.rows
                )
                summary.missing_in_target = missing_in_tgt
                summary.extra_in_target   = extra_in_tgt

                if missing_in_tgt == 0 and extra_in_tgt == 0:
                    pk_status = "PASS"
                    pk_verdict = "All source PKs found in target — no missing rows ✓"
                    _pass(pk_verdict)
                elif missing_in_tgt > 0:
                    pk_status = "FAIL"
                    pk_verdict = (
                        f"{missing_in_tgt} row(s) in PostgreSQL are MISSING from Snowflake!"
                    )
                    _fail(pk_verdict)
                else:
                    pk_status = "WARN"
                    pk_verdict = (
                        f"{extra_in_tgt} extra row(s) in Snowflake not in PostgreSQL"
                    )
                    _warn(pk_verdict)

                r8_src.status = pk_status
                r8_tgt.status = pk_status
                r8_src.verdict_reason = pk_verdict
                r8_tgt.verdict_reason = pk_verdict

                self._print_verdict_box(
                    "MISSING ROWS CHECK",
                    pk_verdict,
                    pk_status,
                    extra=[
                        f"Source PKs          : {len(r8_src.rows):,}",
                        f"Target PKs          : {len(r8_tgt.rows):,}",
                        f"Missing in target   : {missing_in_tgt:,}",
                        f"Extra in target     : {extra_in_tgt:,}",
                    ]
                )

            # ── ③ Main Validation — PostgreSQL ───────────────────────────────
            if query_result.source_sql:
                _head(f"\n  {'─'*60}")
                _info("③ MAIN VALIDATION — PostgreSQL  (normalised data, first 20 rows)")
                r3 = self._run_query(
                    label="③ MAIN VALIDATION — PostgreSQL",
                    sql=query_result.source_sql,
                    db="postgresql",
                )
                summary.results.append(r3)
                self._print_rows(r3.rows, max_rows=self.DISPLAY_ROWS)

                # ── ④ Main Validation — Snowflake ─────────────────────────────
                _head(f"\n  {'─'*60}")
                _info("④ MAIN VALIDATION — Snowflake  (normalised data, first 20 rows)")
                r4 = self._run_query(
                    label="④ MAIN VALIDATION — Snowflake",
                    sql=query_result.target_sql,
                    db="snowflake",
                )
                summary.results.append(r4)
                self._print_rows(r4.rows, max_rows=self.DISPLAY_ROWS)

                # Compare normalised rows
                matched, total, diff_rows = self._compare_normalised_rows(
                    r3.rows, r4.rows
                )

                if total == 0:
                    norm_status = "WARN"
                    norm_verdict = "No rows returned to compare"
                elif matched == total:
                    norm_status = "PASS"
                    norm_verdict = f"All {total:,} normalised rows match exactly ✓"
                    _pass(norm_verdict)
                else:
                    norm_status = "FAIL" if (total - matched) > total * 0.01 else "WARN"
                    norm_verdict = (
                        f"{total - matched:,} of {total:,} rows differ after normalisation"
                    )
                    _fail(norm_verdict)
                    if diff_rows:
                        print(f"\n  {C.YELLOW}First differing rows (source vs target):{C.RESET}")
                        self._print_diff_rows(diff_rows[:5])

                r3.status = norm_status
                r4.status = norm_status
                r3.verdict_reason = norm_verdict
                r4.verdict_reason = norm_verdict

                self._print_verdict_box(
                    "NORMALISED DATA MATCH",
                    norm_verdict,
                    norm_status,
                    extra=[
                        f"Rows compared : {total:,}",
                        f"Matched       : {matched:,}",
                        f"Differing     : {total - matched:,}",
                    ]
                )

        except Exception as exc:
            _fail(f"Execution error: {exc}")
            summary.overall_status = "ERROR"

        finally:
            self._disconnect()

        # ── Final summary ─────────────────────────────────────────────────────
        summary.overall_status = self._compute_overall_status(summary)
        self._print_final_summary(summary)

        return summary

    # ─────────────────────────────────────────────────────────────────────────
    # Database helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _connect_postgres(self, database: str = None) -> PostgreSQLConnector:
        """Build and connect a PostgreSQL connector from env vars."""
        config = DatabaseConfig(
            database_type=DatabaseType.POSTGRESQL,
            host=os.getenv("SOURCE_HOST", "localhost"),
            port=int(os.getenv("SOURCE_PORT", "5432")),
            database=database or os.getenv("SOURCE_DATABASE", "postgres"),
            username=os.getenv("SOURCE_USERNAME", "postgres"),
            password=os.getenv("SOURCE_PASSWORD", ""),
            schema=os.getenv("SOURCE_SCHEMA", "public"),
        )
        conn = PostgreSQLConnector(config)
        if not conn.connect():
            raise RuntimeError(
                "Cannot connect to PostgreSQL. "
                "Check SOURCE_* variables in .env and run check_connections.py"
            )
        return conn

    def _connect_snowflake(self) -> SnowflakeConnector:
        """Build and connect a Snowflake connector from env vars."""
        config = DatabaseConfig(
            database_type=DatabaseType.SNOWFLAKE,
            host=os.getenv("SNOWFLAKE_ACCOUNT", ""),
            port=443,
            database=os.getenv("SNOWFLAKE_DATABASE", ""),
            username=os.getenv("SNOWFLAKE_USERNAME", ""),
            password=os.getenv("SNOWFLAKE_PASSWORD", ""),
            schema=os.getenv("SNOWFLAKE_SCHEMA", ""),
        )
        conn = SnowflakeConnector(config)
        if not conn.connect():
            raise RuntimeError(
                "Cannot connect to Snowflake. "
                "Check SNOWFLAKE_* variables in .env and run check_connections.py"
            )
        return conn

    def _disconnect(self):
        """Cleanly close both connections."""
        try:
            if self._pg_conn and self._pg_conn.connection:
                self._pg_conn.disconnect()
        except Exception:
            pass
        try:
            if self._sf_conn and self._sf_conn.connection:
                self._sf_conn.disconnect()
        except Exception:
            pass

    def _run_query(
        self,
        label: str,
        sql: str,
        db: str,          # "postgresql" | "snowflake"
    ) -> QueryExecutionResult:
        """Execute a single query and return the result."""

        qr = QueryExecutionResult(
            query_label=label,
            database=db,
            sql=sql,
        )

        if not sql or not sql.strip():
            qr.status = "SKIP"
            qr.verdict_reason = "No SQL provided — skipped"
            _warn(f"[SKIP] {label} — no SQL")
            return qr

        thin = "─" * 66
        print(f"\n  {thin}")
        print(f"  {C.BOLD}{label}{C.RESET}")
        print(f"  {thin}")

        connector = self._pg_conn if db == "postgresql" else self._sf_conn

        try:
            start = time.time()
            db_result = connector.execute_query(sql)
            qr.execution_time_ms = (time.time() - start) * 1000

            if db_result.error:
                qr.status = "ERROR"
                qr.error = db_result.error
                _fail(f"Query error: {db_result.error}")
            else:
                qr.rows = db_result.rows
                qr.row_count = db_result.row_count
                qr.status = "PASS"
                _dim(f"Returned {qr.row_count:,} row(s) in {qr.execution_time_ms:.0f}ms")

        except Exception as exc:
            qr.status = "ERROR"
            qr.error = str(exc)
            _fail(f"Execution exception: {exc}")

        return qr

    # ─────────────────────────────────────────────────────────────────────────
    # Verdict calculators
    # ─────────────────────────────────────────────────────────────────────────

    def _verdict_row_count(
        self, src: int, tgt: int
    ) -> Tuple[str, str, str]:
        """Return (src_status, tgt_status, verdict_text)."""
        if src == tgt:
            return "PASS", "PASS", f"Row counts match exactly: {src:,} ✓"
        diff = abs(src - tgt)
        diff_pct = diff / max(src, 1) * 100
        if diff_pct <= self.ROW_COUNT_WARN_DIFF_PCT:
            return (
                "WARN", "WARN",
                f"Row counts differ by {diff:,} rows ({diff_pct:.2f}%) — within 1% tolerance"
            )
        return (
            "FAIL", "FAIL",
            f"Row count MISMATCH: source={src:,}, target={tgt:,}, diff={diff:,} ({diff_pct:.1f}%)"
        )

    def _verdict_null_pct(
        self, src_rows: List[Dict], tgt_rows: List[Dict]
    ) -> List[Tuple[str, str, str, str]]:
        """
        Returns list of (column_name, src_pct, tgt_pct, status) tuples.
        Compares null_pct values for each column.
        """
        if not src_rows or not tgt_rows:
            return []

        src_row = src_rows[0]
        tgt_row = tgt_rows[0]
        verdicts = []

        for key in src_row:
            if key == "total_rows":
                continue
            col = key.replace("_null_pct", "")
            src_pct = float(src_row.get(key, 0) or 0)
            tgt_pct = float(tgt_row.get(key, 0) or 0)
            diff = abs(src_pct - tgt_pct)

            if diff == 0:
                status = "PASS"
            elif diff <= self.NULL_DIFF_THRESHOLD_PCT:
                status = "WARN"
            else:
                status = "FAIL"

            verdicts.append((col, src_pct, tgt_pct, status))

        return verdicts

    def _compare_pk_sets(
        self, src_rows: List[Dict], tgt_rows: List[Dict]
    ) -> Tuple[int, int]:
        """
        Compare pk_key sets between source and target.
        Returns (missing_in_target, extra_in_target).
        """
        src_keys = {str(r.get("pk_key", "")).upper() for r in src_rows}
        tgt_keys = {str(r.get("pk_key", "")).upper() for r in tgt_rows}

        missing = len(src_keys - tgt_keys)
        extra   = len(tgt_keys - src_keys)
        return missing, extra

    def _compare_normalised_rows(
        self, src_rows: List[Dict], tgt_rows: List[Dict]
    ) -> Tuple[int, int, List[Dict]]:
        """
        Compare normalised rows from source and target.
        Matches rows by the first column (primary key normalised).
        Returns (matched_count, total_compared, diff_rows).
        """
        if not src_rows or not tgt_rows:
            return 0, 0, []

        # Build target lookup by first column value (normalised PK)
        first_col = list(tgt_rows[0].keys())[0] if tgt_rows else None
        if not first_col:
            return 0, 0, []

        tgt_lookup: Dict[str, Dict] = {}
        for row in tgt_rows:
            pk_val = str(row.get(first_col, "")).upper()
            tgt_lookup[pk_val] = row

        matched = 0
        total   = len(src_rows)
        diff_rows = []

        for src_row in src_rows:
            pk_val = str(src_row.get(first_col, "")).upper()
            tgt_row = tgt_lookup.get(pk_val)

            if tgt_row is None:
                diff_rows.append({
                    "type": "MISSING_IN_TARGET",
                    "source": src_row,
                    "target": None,
                })
                continue

            # Compare all columns
            row_match = True
            for col, src_val in src_row.items():
                tgt_val = tgt_row.get(col)
                if str(src_val).upper() != str(tgt_val).upper():
                    row_match = False
                    diff_rows.append({
                        "type": "VALUE_MISMATCH",
                        "column": col,
                        "source": src_row,
                        "target": tgt_row,
                    })
                    break

            if row_match:
                matched += 1

        return matched, total, diff_rows

    # ─────────────────────────────────────────────────────────────────────────
    # Display helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _print_rows(
        self,
        rows: List[Dict],
        max_rows: int = 20,
        transpose: bool = False,
    ):
        """Print rows as a formatted table."""
        if not rows:
            _dim("  (no rows returned)")
            return

        if transpose:
            # For NULL % queries — show column: value pairs vertically
            for row in rows[:1]:
                for col, val in row.items():
                    icon = "⚠" if (col != "total_rows" and float(val or 0) > 0) else " "
                    print(f"    {C.DIM}{col:<45}{C.RESET}  {icon} {val}")
            return

        # Standard table format
        cols = list(rows[0].keys())
        col_widths = {
            c: max(len(str(c)), max(len(str(r.get(c, ""))) for r in rows[:max_rows]))
            for c in cols
        }

        # Header
        header = "  │ " + " │ ".join(
            str(c).ljust(col_widths[c]) for c in cols
        ) + " │"
        separator = "  ├─" + "─┼─".join("─" * col_widths[c] for c in cols) + "─┤"
        top = "  ┌─" + "─┬─".join("─" * col_widths[c] for c in cols) + "─┐"
        bot = "  └─" + "─┴─".join("─" * col_widths[c] for c in cols) + "─┘"

        print(f"{C.DIM}{top}{C.RESET}")
        print(f"{C.BOLD}{header}{C.RESET}")
        print(f"{C.DIM}{separator}{C.RESET}")

        for row in rows[:max_rows]:
            line = "  │ " + " │ ".join(
                str(row.get(c, "")).ljust(col_widths[c]) for c in cols
            ) + " │"
            print(line)

        print(f"{C.DIM}{bot}{C.RESET}")

        if len(rows) > max_rows:
            _dim(f"  ... and {len(rows) - max_rows:,} more rows (showing first {max_rows})")

    def _print_null_comparison(self, verdicts: List[Tuple]):
        """Print a side-by-side NULL % comparison table."""
        if not verdicts:
            return

        print(f"\n  {C.BOLD}NULL % COMPARISON  (PostgreSQL vs Snowflake):{C.RESET}")
        header = f"  {'Column':<40} {'PG NULL%':>10}  {'SF NULL%':>10}  {'Status':>8}"
        print(f"{C.DIM}  {'─'*74}{C.RESET}")
        print(f"{C.BOLD}{header}{C.RESET}")
        print(f"{C.DIM}  {'─'*74}{C.RESET}")

        for col, src_pct, tgt_pct, status in verdicts:
            if status == "PASS":
                icon = f"{C.GREEN}✓ PASS {C.RESET}"
            elif status == "WARN":
                icon = f"{C.YELLOW}⚠ WARN {C.RESET}"
            else:
                icon = f"{C.RED}✗ FAIL {C.RESET}"
            diff = abs(src_pct - tgt_pct)
            diff_str = f"(+{diff:.2f}%)" if diff > 0 else ""
            print(
                f"  {col:<40} {src_pct:>9.2f}%  {tgt_pct:>9.2f}%  {icon} {diff_str}"
            )
        print(f"{C.DIM}  {'─'*74}{C.RESET}")

    def _print_diff_rows(self, diff_rows: List[Dict]):
        """Show first few differing rows."""
        for i, diff in enumerate(diff_rows, 1):
            if diff["type"] == "MISSING_IN_TARGET":
                print(f"\n  {C.RED}  Row {i} — MISSING IN TARGET:{C.RESET}")
                for k, v in list(diff["source"].items())[:5]:
                    print(f"    {k}: {v}")
            elif diff["type"] == "VALUE_MISMATCH":
                col = diff.get("column", "?")
                src_val = diff["source"].get(col, "?")
                tgt_val = diff["target"].get(col, "?") if diff["target"] else "N/A"
                print(f"\n  {C.YELLOW}  Row {i} — VALUE MISMATCH in '{col}':{C.RESET}")
                print(f"    PostgreSQL : {src_val}")
                print(f"    Snowflake  : {tgt_val}")

    def _print_verdict_box(
        self,
        title: str,
        verdict: str,
        status: str,
        extra: List[str] = None,
    ):
        """Print a coloured verdict box."""
        if status == "PASS":
            colour = C.GREEN
            icon = "✅ PASS"
        elif status == "WARN":
            colour = C.YELLOW
            icon = "⚠️  WARN"
        elif status == "FAIL":
            colour = C.RED
            icon = "❌ FAIL"
        else:
            colour = C.RED
            icon = "🔴 ERROR"

        box_width = 64
        print(f"\n  {colour}{'┌' + '─'*(box_width) + '┐'}{C.RESET}")
        print(f"  {colour}│  {C.BOLD}{icon}  ─  {title}{colour}{'': <{box_width - len(title) - len(icon) - 6}}│{C.RESET}")
        print(f"  {colour}│  {verdict[:box_width-4]:<{box_width-4}}│{C.RESET}")
        if extra:
            print(f"  {colour}│{'─'*box_width}│{C.RESET}")
            for line in extra:
                print(f"  {colour}│  {line[:box_width-4]:<{box_width-4}}│{C.RESET}")
        print(f"  {colour}{'└' + '─'*(box_width) + '┘'}{C.RESET}")

    def _print_final_summary(self, summary: ValidationExecutionSummary):
        """Print the final overall summary table."""
        sep = "═" * 66

        status_colour = {
            "PASS": C.GREEN, "FAIL": C.RED,
            "WARN": C.YELLOW, "ERROR": C.RED,
            "PARTIAL": C.YELLOW,
        }.get(summary.overall_status, C.RESET)

        print(f"\n\n  {C.BOLD}{sep}{C.RESET}")
        print(f"  {C.BOLD}📊  VALIDATION EXECUTION SUMMARY  |  {summary.table_name}{C.RESET}")
        print(f"  {C.BOLD}{sep}{C.RESET}")

        print(f"\n  {'Check':<40} {'Status':>10}  {'Details'}")
        print(f"  {'─'*64}")

        for r in summary.results:
            if r.status == "PASS":
                st = f"{C.GREEN}  ✓ PASS{C.RESET}"
            elif r.status == "WARN":
                st = f"{C.YELLOW}  ⚠ WARN{C.RESET}"
            elif r.status == "FAIL":
                st = f"{C.RED}  ✗ FAIL{C.RESET}"
            elif r.status == "SKIP":
                st = f"{C.DIM}  - SKIP{C.RESET}"
            else:
                st = f"{C.RED}  ! ERR {C.RESET}"
            detail = (r.verdict_reason or r.error or "")[:40]
            print(f"  {r.query_label:<40} {st}  {C.DIM}{detail}{C.RESET}")

        print(f"\n  {'─'*64}")
        print(f"  {'Source rows':<40} {summary.source_row_count:>10,}")
        print(f"  {'Target rows':<40} {summary.target_row_count:>10,}")
        print(f"  {'Duplicate PKs in target':<40} {summary.duplicate_pk_count:>10,}")
        print(f"  {'Rows missing in target':<40} {summary.missing_in_target:>10,}")
        print(f"  {'Extra rows in target':<40} {summary.extra_in_target:>10,}")
        print(f"  {'Data completeness':<40} {summary.completeness_pct:>9.1f}%")

        print(f"\n  {C.BOLD}{sep}{C.RESET}")
        print(
            f"  {C.BOLD}  OVERALL STATUS : "
            f"{status_colour}{summary.overall_status}{C.RESET}"
        )
        print(f"  {C.BOLD}{sep}{C.RESET}\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Overall status
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_overall_status(summary: ValidationExecutionSummary) -> str:
        statuses = [r.status for r in summary.results if r.status != "SKIP"]
        if not statuses:
            return "ERROR"
        if "ERROR" in statuses:
            return "ERROR"
        if all(s == "PASS" for s in statuses):
            return "PASS"
        if "FAIL" in statuses:
            return "FAIL"
        return "WARN"


# ─────────────────────────────────────────────────────────────────────────────
# Helper — extract Step 2 SQL from missing rows block
# ─────────────────────────────────────────────────────────────────────────────

def _extract_step2_sql(missing_rows_sql: str) -> str:
    """Extract only the Step 2 SELECT (Snowflake PKs) from the missing rows SQL."""
    if not missing_rows_sql:
        return ""
    lines = missing_rows_sql.split("\n")
    step2_lines = []
    in_step2 = False
    for line in lines:
        if "Step 2" in line:
            in_step2 = True
            continue
        if in_step2 and line.strip().startswith("--"):
            if "Step 3" in line:
                break
            continue
        if in_step2 and line.strip():
            step2_lines.append(line)
        if in_step2 and line.strip().endswith(";"):
            break
    return "\n".join(step2_lines).strip()
