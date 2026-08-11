"""
Verification script — confirms YAML auto-generation works correctly.

This script simulates what the pipeline does:
  1. Creates mock ColumnRuleMappings (like the real pipeline would after extraction)
  2. Runs SQLQueryGenerator to build SQL
  3. Runs YAMLConfigWriter to produce the YAML
  4. Prints both outputs to screen so you can verify the format

Run from project root:
    python src/verify_yaml_generation.py

Expected output:
  - validation_sql/events_validation.sql   ← created automatically
  - validation_sql/events_validation.yaml  ← created automatically (NOT manually!)
"""

import sys
from pathlib import Path

# ── Ensure src/ is in path ───────────────────────────────────────────────────
_SRC = Path(__file__).parent
sys.path.insert(0, str(_SRC))

try:
    from dotenv import load_dotenv
    load_dotenv(_SRC.parent / ".env")
except ImportError:
    pass

from rules import get_rule_for_type
from ai_transformation.static_rule_mapper import ColumnRuleMapping
from generated_queries.sql_query_generator import SQLQueryGenerator
from generated_queries.yaml_config_writer import YAMLConfigWriter


def _make_mapping(src_col, tgt_col, src_type, tgt_type) -> ColumnRuleMapping:
    """Helper: build a ColumnRuleMapping for testing."""
    return ColumnRuleMapping(
        source_column=src_col,
        target_column=tgt_col,
        source_type=src_type,
        target_type=tgt_type,
        rule=get_rule_for_type(src_type, tgt_type),
        is_primary_key=False,
        skip_validation=False,
        matched_by="static",
    )


def main():
    print("\n" + "=" * 65)
    print("  YAML Auto-Generation Verification")
    print("=" * 65)

    # ── Mock column mappings for 'events' table ──────────────────────────────
    mappings = [
        _make_mapping("id",               "ID",               "integer",                    "NUMBER"),
        _make_mapping("type",             "TYPE",             "character varying",           "VARCHAR"),
        _make_mapping("needs_followup",   "NEEDS_FOLLOWUP",   "boolean",                    "BOOLEAN"),
        _make_mapping("needs_followup_by","NEEDS_FOLLOWUP_BY","date",                       "DATE"),
        _make_mapping("followup_date",    "FOLLOWUP_DATE",    "date",                       "DATE"),
        _make_mapping("resolved",         "RESOLVED",         "boolean",                    "BOOLEAN"),
        _make_mapping("created_by_id",    "CREATED_BY_ID",    "integer",                    "NUMBER"),
        _make_mapping("updated_by_id",    "UPDATED_BY_ID",    "integer",                    "NUMBER"),
        _make_mapping("unit_id",          "UNIT_ID",          "integer",                    "NUMBER"),
        _make_mapping("tenant_id",        "TENANT_ID",        "integer",                    "NUMBER"),
        _make_mapping("created_at",       "CREATED_AT",       "timestamp without time zone","TIMESTAMP_NTZ"),
        _make_mapping("updated_at",       "UPDATED_AT",       "timestamp without time zone","TIMESTAMP_NTZ"),
        _make_mapping("uuid",             "UUID",             "uuid",                       "TEXT"),
        _make_mapping("status",           "STATUS",           "character varying",           "VARCHAR"),
        _make_mapping("important_task",   "IMPORTANT_TASK",   "boolean",                    "BOOLEAN"),
    ]

    print(f"\n  Table       : events (PostgreSQL) -> EVENTS (Snowflake)")
    print(f"  Schema PG   : public")
    print(f"  Schema SF   : dev_edge_bronze.storedge_fms_public")
    print(f"  Columns     : {len(mappings)} mapped")
    print(f"  Fivetran    : YES (_FIVETRAN_ACTIVE = TRUE)")
    print()

    # ── Step 1: Generate SQL ─────────────────────────────────────────────────
    print("[1/2] Generating SQL queries...")
    gen = SQLQueryGenerator()
    query_set = gen.generate(
        pg_schema="public",
        pg_table="events",
        sf_database="dev_edge_bronze",
        sf_schema="storedge_fms_public",
        sf_table="EVENTS",
        mappings=mappings,
        has_fivetran_active=True,
        generated_by="static",
        model_used="N/A",
    )

    # Show a snippet of the main validation queries
    print("\n  ── PostgreSQL main validation (first 5 lines) ──")
    for line in query_set.main_validation_source.splitlines()[:6]:
        print(f"    {line}")

    print("\n  ── Snowflake main validation (first 5 lines) ──")
    for line in query_set.main_validation_target.splitlines()[:6]:
        print(f"    {line}")

    # ── Step 2: Generate YAML automatically ─────────────────────────────────
    print("\n[2/2] Auto-generating YAML config...")
    writer   = YAMLConfigWriter()
    out_dir  = Path(__file__).parent.parent / "validation_sql"
    yaml_path = writer.write(
        query_set=query_set,
        pg_schema="public",
        pg_table="events",
        sf_database="dev_edge_bronze",
        sf_schema="storedge_fms_public",
        sf_table="EVENTS",
        mappings=mappings,
        has_fivetran_active=True,
        output_dir=out_dir,
    )

    # Save combined SQL too
    sql_path = out_dir / "events_validation.sql"
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write(query_set.combined_sql)
    print(f"  💾 SQL  auto-generated : {sql_path.resolve()}")

    # ── Show YAML preview ────────────────────────────────────────────────────
    print(f"\n  ── YAML file preview (first 40 lines) ──")
    yaml_text = yaml_path.read_text(encoding="utf-8")
    for i, line in enumerate(yaml_text.splitlines()[:40], 1):
        print(f"    {line}")
    if yaml_text.count("\n") > 40:
        print(f"    ... ({yaml_text.count(chr(10))} total lines)")

    print("\n" + "=" * 65)
    print("  ✅ VERIFICATION COMPLETE")
    print(f"  SQL  → {sql_path}")
    print(f"  YAML → {yaml_path}")
    print("=" * 65)
    print()
    print("  Both files are auto-generated by the pipeline.")
    print("  Run validate_cli.py to generate for real tables.")
    print()


if __name__ == "__main__":
    main()
