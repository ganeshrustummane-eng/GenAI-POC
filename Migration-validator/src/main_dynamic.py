"""
Dynamic Entry Point — Migration Validator
==========================================
This is the NEW main script. No more hard-coded columns, types, or rules.

You only need to provide:
  - PostgreSQL database name
  - PostgreSQL schema name
  - Source table name
  - Snowflake schema name
  - Target table name
  - (Optional) primary key column name(s)

The system does the rest:
  ✓ Connects to PostgreSQL  → pulls real schema
  ✓ Connects to Snowflake   → pulls real schema
  ✓ Compares schemas        → detects type differences
  ✓ Calls AI (GPT-4o/DIAL)  → assigns rules + generates SQL
  ✓ Runs completeness checks → row count, null %, duplicates, PK gaps
  ✓ Writes reports           → JSON + HTML + TXT

Usage
-----
  # Single table
  python main_dynamic.py

  # Or import and call programmatically (see examples below)

Configuration
-------------
  All database credentials come from the .env file.
  See .env.example for required variables.

  Minimum .env requirements:
    SOURCE_HOST, SOURCE_PORT, SOURCE_DATABASE, SOURCE_SCHEMA,
    SOURCE_USERNAME, SOURCE_PASSWORD
    SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA,
    SNOWFLAKE_USERNAME, SNOWFLAKE_PASSWORD
    DIAL_API_KEY  (optional — enables AI mode, falls back to static rules)
"""

import sys
from pathlib import Path

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from dynamic_validator import DynamicValidator


# ===========================================================================
# ► EDIT ONLY THIS SECTION — Everything else is automatic
# ===========================================================================

# ── Single table validation ─────────────────────────────────────────────────
# ► CHANGE 'source_table' and 'target_table' to switch which table you validate
SINGLE_TABLE_CONFIG = {
    # PostgreSQL source
    "source_database": "fms",                        # <- PostgreSQL DB (matches SOURCE_DATABASE in .env)
    "source_schema":   "public",                     # <- PostgreSQL schema (matches SOURCE_SCHEMA in .env)
    "source_table":    "events",                     # <- One of: events | general_ledger_line_items

    # Snowflake target
    "target_schema":   "storedge_fms_public",        # <- Snowflake schema (matches SNOWFLAKE_SCHEMA in .env)
    "target_table":    "EVENTS",                     # <- Snowflake table — MUST be UPPER CASE
    # target_database defaults to SNOWFLAKE_DATABASE in .env (dev_edge_bronze)

    # Primary keys (optional — auto-detected if empty list [])
    # For events: likely 'event_id'   For general_ledger_line_items: likely 'id' or 'line_item_id'
    "primary_keys": [],                              # <- Leave empty for auto-detect or add e.g. ["event_id"]
}

# ── Multi-table validation ──────────────────────────────────────────────────
# Validates BOTH your tables in one run — set MODE = "multi" below to use this
MULTI_TABLE_CONFIG = {
    "source_database": "fms",
    "tables": [
        {
            "source_schema": "public",
            "source_table":  "events",
            "target_schema": "storedge_fms_public",
            "target_table":  "EVENTS",
        },
        {
            "source_schema": "public",
            "source_table":  "general_ledger_line_items",
            "target_schema": "storedge_fms_public",
            "target_table":  "GENERAL_LEDGER_LINE_ITEMS",
        },
        # ← Add more tables here if needed
    ],
    "primary_keys_map": {
        # Leave empty {} to let the system auto-detect PKs for all tables
        # Or specify manually: "events": ["event_id"], "general_ledger_line_items": ["id"]
    },
}

# ===========================================================================
# ► Main execution
# ===========================================================================

def run_single_table():
    """Validate a single table using the SINGLE_TABLE_CONFIG above."""
    print("\n" + "="*70)
    print("  MODE: Single Table Validation")
    print("="*70)

    validator = DynamicValidator()
    report = validator.run(
        source_database=SINGLE_TABLE_CONFIG["source_database"],
        source_schema=SINGLE_TABLE_CONFIG["source_schema"],
        source_table=SINGLE_TABLE_CONFIG["source_table"],
        target_schema=SINGLE_TABLE_CONFIG["target_schema"],
        target_table=SINGLE_TABLE_CONFIG["target_table"],
        primary_keys=SINGLE_TABLE_CONFIG.get("primary_keys", []),
        save_reports=True,
        print_plan=True,
    )

    # Print final summary
    print(f"\n{'='*70}")
    print(f"  FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"  Validation ID    : {report.validation_id}")
    print(f"  Overall Status   : {report.overall_status}")
    print(f"  Data Completeness: {report.overall_completeness_pct:.1f}%")
    for tr in report.table_results:
        row_match = "✓" if tr.row_count_match else "✗"
        print(f"  Table: {tr.table_name:<30} {tr.overall_status} | "
              f"Rows {row_match} {tr.source_row_count} → {tr.target_row_count} | "
              f"Completeness: {tr.row_completeness_pct:.1f}%")
    print(f"{'='*70}\n")

    return report


def run_multiple_tables():
    """Validate multiple tables using the MULTI_TABLE_CONFIG above."""
    print("\n" + "="*70)
    print("  MODE: Multi-Table Validation")
    print("="*70)

    validator = DynamicValidator()
    report = validator.run_multiple(
        source_database=MULTI_TABLE_CONFIG["source_database"],
        tables=MULTI_TABLE_CONFIG["tables"],
        primary_keys_map=MULTI_TABLE_CONFIG.get("primary_keys_map", {}),
        save_reports=True,
    )

    print(f"\n{'='*70}")
    print(f"  MULTI-TABLE SUMMARY")
    print(f"{'='*70}")
    print(f"  Validation ID    : {report.validation_id}")
    print(f"  Overall Status   : {report.overall_status}")
    print(f"  Tables Validated : {report.total_tables}")
    print(f"  Passed Tables    : {report.passed_tables}")
    print(f"  Failed Tables    : {report.failed_tables}")
    print(f"  Data Completeness: {report.overall_completeness_pct:.1f}%")
    print(f"{'='*70}\n")

    return report


def run_schema_discovery_only():
    """
    Only extract and display schemas — no validation queries run.
    Useful to preview what columns will be mapped before running validation.
    """
    from schema_extractor import PostgresSchemaExtractor, SnowflakeSchemaExtractor, SchemaComparator
    import os

    print("\n" + "="*70)
    print("  MODE: Schema Discovery Only")
    print("="*70)

    cfg = SINGLE_TABLE_CONFIG

    print(f"\n[PostgreSQL] Extracting schema...")
    pg_ext = PostgresSchemaExtractor(database=cfg["source_database"])
    src_cols = pg_ext.extract_columns(cfg["source_schema"], cfg["source_table"])

    print(f"\n[Snowflake] Extracting schema...")
    sf_ext = SnowflakeSchemaExtractor()
    tgt_cols = sf_ext.extract_columns(cfg["target_schema"], cfg["target_table"])

    comparison = SchemaComparator.compare(
        source_columns=src_cols,
        target_columns=tgt_cols,
        source_table=f"{cfg['source_schema']}.{cfg['source_table']}",
        target_table=f"{cfg['target_schema']}.{cfg['target_table']}",
    )

    print(f"\n{'='*70}")
    print(f"  SOURCE COLUMNS  ({cfg['source_schema']}.{cfg['source_table']})")
    print(f"{'='*70}")
    for col in src_cols:
        null_str = "NULL" if col.is_nullable else "NOT NULL"
        print(f"  {col.ordinal_position:3}. {col.column_name:<35} {col.type_summary():<25} {null_str}")

    print(f"\n{'='*70}")
    print(f"  TARGET COLUMNS  ({cfg['target_schema']}.{cfg['target_table']})")
    print(f"{'='*70}")
    for col in tgt_cols:
        null_str = "NULL" if col.is_nullable else "NOT NULL"
        print(f"  {col.ordinal_position:3}. {col.column_name:<35} {col.type_summary():<25} {null_str}")

    print(f"\n{'='*70}")
    print(f"  SCHEMA DIFF SUMMARY")
    print(f"{'='*70}")
    comparison.print_summary()


def run_ai_plan_only():
    """
    Generate and print the AI validation plan (SQL queries + rules) without executing checks.
    Useful for reviewing the generated SQL before running it on the databases.
    """
    from schema_extractor import PostgresSchemaExtractor, SnowflakeSchemaExtractor, SchemaComparator
    from schema_discovery import column_info_to_dict
    from ai_query_agent import AIQueryAgent
    from models import DatabaseType

    print("\n" + "="*70)
    print("  MODE: AI Plan Generation Only")
    print("="*70)

    cfg = SINGLE_TABLE_CONFIG

    pg_ext = PostgresSchemaExtractor(database=cfg["source_database"])
    src_cols = pg_ext.extract_columns(cfg["source_schema"], cfg["source_table"])

    sf_ext = SnowflakeSchemaExtractor()
    tgt_cols = sf_ext.extract_columns(cfg["target_schema"], cfg["target_table"])

    agent = AIQueryAgent()
    plan = agent.generate_validation_plan(
        source_db_type=DatabaseType.POSTGRESQL,
        source_schema=cfg["source_schema"],
        source_table=cfg["source_table"],
        source_columns=[column_info_to_dict(c) for c in src_cols],
        target_db_type=DatabaseType.SNOWFLAKE,
        target_schema=cfg["target_schema"],
        target_table=cfg["target_table"],
        target_columns=[column_info_to_dict(c) for c in tgt_cols],
        primary_key_hints=cfg.get("primary_keys", []),
    )

    plan.print_summary()

    # Also save the SQL for review
    sql_dir = Path("validation_sql")
    sql_dir.mkdir(exist_ok=True)
    table_name = cfg["source_table"].lower()
    sql_file = sql_dir / f"{table_name}_validation.sql"

    with open(sql_file, "w", encoding="utf-8") as f:
        db_name = cfg.get("target_database", "")
        f.write(f"-- {'='*66}\n")
        f.write(f"-- SOURCE (PostgreSQL): {cfg['source_schema']}.{cfg['source_table']}\n")
        f.write(f"-- Generated by: {plan.generated_by.upper()}\n")
        f.write(f"-- {'='*66}\n\n")
        f.write(plan.source_sql)
        f.write(f"\n\n-- {'='*66}\n")
        f.write(f"-- TARGET (Snowflake): {cfg['target_schema']}.{cfg['target_table']}\n")
        f.write(f"-- {'='*66}\n\n")
        f.write(plan.target_sql)

    print(f"\n  SQL written to: {sql_file}")


# ===========================================================================
# ► Choose your mode here
# ===========================================================================

if __name__ == "__main__":
    # ── Available modes ───────────────────────────────────────────────────
    #
    #   "single"     → Full validation for one table  (DEFAULT)
    #   "multi"      → Validate multiple tables at once
    #   "schema"     → Schema discovery only (no SQL execution)
    #   "plan"       → AI plan + SQL generation only (no DB execution)
    #
    MODE = "single"   # ← Change this to switch modes

    if MODE == "single":
        run_single_table()
    elif MODE == "multi":
        run_multiple_tables()
    elif MODE == "schema":
        run_schema_discovery_only()
    elif MODE == "plan":
        run_ai_plan_only()
    else:
        print(f"Unknown mode '{MODE}'. Choose: single | multi | schema | plan")
        sys.exit(1)
