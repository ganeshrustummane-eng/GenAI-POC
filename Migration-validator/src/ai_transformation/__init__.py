"""
AI Transformation Package
===========================
Maps PostgreSQL columns to Snowflake columns and assigns the correct
validation rule for each column pair.

Two mappers provided
--------------------
  1. AIRuleMapper       — DIAL/GPT-4o (or any configured model).
                          Best accuracy; requires DIAL_API_KEY env var.
                          Model is user-selectable at runtime.
  2. StaticRuleMapper   — Deterministic type-pair matching.
                          No API key required; fully offline.

RuleMapperOrchestrator
----------------------
  Single entry point. Tries AI first, falls back to static automatically.
  Supports runtime model switching via orchestrator.set_model('gpt-4o-mini').

Available Models (DIAL)
-----------------------
  gpt-4o            ← default, best accuracy
  gpt-4o-mini       ← faster, lower cost
  gpt-4-turbo
  claude-3-5-sonnet
  gemini-pro
  (any model on your DIAL endpoint)

Usage
-----
    from ai_transformation import RuleMapperOrchestrator, AVAILABLE_MODELS

    # List models user can choose from:
    print(AVAILABLE_MODELS)

    # Use specific model:
    mapper = RuleMapperOrchestrator(model="gpt-4o-mini")
    mappings, explanation = mapper.map_columns(
        source_columns=pg_columns,
        target_columns=sf_columns,
        table_name="events",
    )
"""

from ai_transformation.static_rule_mapper import StaticRuleMapper, ColumnRuleMapping
from ai_transformation.ai_rule_mapper import AIRuleMapper, AVAILABLE_MODELS, MODEL_DESCRIPTIONS
from ai_transformation.orchestrator import RuleMapperOrchestrator

__all__ = [
    "ColumnRuleMapping",
    "StaticRuleMapper",
    "AIRuleMapper",
    "RuleMapperOrchestrator",
    "AVAILABLE_MODELS",
    "MODEL_DESCRIPTIONS",
]
