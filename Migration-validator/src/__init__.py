"""
Migration Validator — PostgreSQL → Snowflake Validation Framework v2.0
========================================================================
Modular pipeline:
  1. sql_extractor/      — Live schema extraction (PostgreSQL + Snowflake)
  2. ai_transformation/  — Column mapping + rule assignment (AI or static)
  3. generated_queries/  — SQL + YAML output file generation
  4. rules/              — Type-specific SQL normalization rules
  5. rule_book.py        — Evolving rule catalog (base + learned rules)
  6. validation_pipeline.py — End-to-end pipeline orchestrator
  7. validate_cli.py     — Interactive CLI with model selection

Quick Start
-----------
  # Interactive CLI (from project root):
  python src/validate_cli.py

  # Direct generation:
  python src/validate_cli.py generate --pg-table events --sf-table EVENTS

  # With model selection:
  python src/validate_cli.py generate \\
      --pg-table events --sf-table EVENTS --model gpt-4o-mini

  # List all commands:
  python src/validate_cli.py --help

Output
------
  validation_sql/<table>_validation.sql   ← 6 SQL queries (PG + Snowflake)
  validation_sql/<table>_validation.yaml  ← YAML config for automation

Environment Variables (.env)
-----------------------------
  SOURCE_HOST, SOURCE_PORT, SOURCE_DATABASE, SOURCE_SCHEMA
  SOURCE_USERNAME, SOURCE_PASSWORD
  SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA
  SNOWFLAKE_USERNAME, SNOWFLAKE_PASSWORD
  DIAL_API_KEY      (optional — enables AI rule mapping)
  DIAL_MODEL        (optional — default: gpt-4o)
"""

__version__     = "2.0.0"
__author__      = "Migration Validator Team"
__description__ = (
    "PostgreSQL → Snowflake data completeness validation. "
    "AI-powered rule assignment, SQL + YAML generation."
)

# ── New modular API (v2) ───────────────────────────────────────────────────────
# These are safe to import — no DB connections at import time.
from rules import get_rule_for_type, get_registry
from rule_book import rule_book, RuleBook, RuleEntry

__all__ = [
    # Pipeline entry point
    "ValidationPipeline",       # import separately: from validation_pipeline import ...

    # Rule book
    "rule_book",
    "RuleBook",
    "RuleEntry",

    # Rule registry helpers
    "get_rule_for_type",
    "get_registry",

    # Version info
    "__version__",
    "__author__",
    "__description__",
]
