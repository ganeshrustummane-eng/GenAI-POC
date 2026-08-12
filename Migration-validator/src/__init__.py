"""
Migration Validator — PostgreSQL → Snowflake Validation Framework v3.0
========================================================================
Modular pipeline:
  1. sql_extractor/      — Live schema extraction (PostgreSQL, MSSQL, Snowflake)
  2. ai_transformation/  — Column mapping + rule assignment (AI or static)
  3. generated_queries/  — SQL + YAML output file generation
  4. rules/              — Type-specific SQL normalization rules
  5. batch/              — Multi-table batch processing
  6. validation_pipeline.py — End-to-end pipeline orchestrator
  7. validate_cli.py     — Interactive CLI with model selection

Quick Start
-----------
  # Single table:
  python src/validate_cli.py generate --pg-table events --sf-table EVENTS

  # Batch mode:
  python src/validate_cli.py batch --config tables.yaml

  # List all commands:
  python src/validate_cli.py --help

Output
------
  validation_sql/<table>_validation.sql   ← SQL queries (including PK-aware ⑨–⑭)
  validation_sql/<table>_validation.yaml  ← YAML config for automation
  validation_sql/batch_run_*/             ← Batch run output directory

Environment Variables (.env)
-----------------------------
  SOURCE_HOST, SOURCE_PORT, SOURCE_DATABASE, SOURCE_SCHEMA
  SOURCE_USERNAME, SOURCE_PASSWORD
  SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA
  SNOWFLAKE_USERNAME, SNOWFLAKE_PASSWORD
  DIAL_API_KEY      (optional — enables AI rule mapping)
  DIAL_MODEL        (optional — default: gpt-4o)
"""

__version__     = "3.0.0"
__author__      = "Migration Validator Team"
__description__ = (
    "PostgreSQL → Snowflake data completeness validation. "
    "Multi-source, batch processing, PK-aware SQL generation."
)

# ── Rule registry helpers (no DB connections at import time) ──────────────────
from rules import get_rule_for_type, get_registry

__all__ = [
    # Pipeline entry point
    "ValidationPipeline",       # import separately: from validation_pipeline import ...

    # Rule registry helpers
    "get_rule_for_type",
    "get_registry",

    # Version info
    "__version__",
    "__author__",
    "__description__",
]
