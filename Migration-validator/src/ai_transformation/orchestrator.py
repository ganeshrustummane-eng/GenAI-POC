"""
Rule Mapper Orchestrator
=========================
Tries AI-based rule mapping first (AIRuleMapper with the selected model).
Falls back to StaticRuleMapper automatically when:
  - DIAL_API_KEY is not set
  - The AI API is unreachable
  - JSON parsing of AI response fails

This is the single entry-point the pipeline uses.  The caller never needs
to know which mapper was actually used.

Model Selection
---------------
The user can select which AI model to use via:
  1. orchestrator = RuleMapperOrchestrator(model="gpt-4o-mini")
  2. DIAL_MODEL environment variable
  3. Interactive CLI selection (validate_cli.py)

Usage:
    from ai_transformation import RuleMapperOrchestrator

    orchestrator = RuleMapperOrchestrator(model="gpt-4o")
    mappings, explanation = orchestrator.map_columns(
        source_columns=pg_columns,
        target_columns=sf_columns,
        table_name="events",
    )
"""

import sys
from typing import List, Optional, Tuple

from sql_extractor.extractors import ColumnMetadata
from ai_transformation.static_rule_mapper import StaticRuleMapper, ColumnRuleMapping
from ai_transformation.ai_rule_mapper import AIRuleMapper, AVAILABLE_MODELS


class RuleMapperOrchestrator:
    """
    Facade that selects the best available mapper at runtime.

    Priority:
      1. AIRuleMapper with the specified/configured model — if DIAL_API_KEY is set
      2. StaticRuleMapper                                 — always available, no network

    Both mappers return identical output types so the caller is fully decoupled.
    """

    def __init__(self, model: Optional[str] = None):
        """
        Args:
            model: AI model name to use (e.g. 'gpt-4o', 'gpt-4o-mini').
                   Defaults to DIAL_MODEL env var, then 'gpt-4o'.
        """
        self._ai_mapper     = AIRuleMapper(model=model)
        self._static_mapper = StaticRuleMapper()

    def set_model(self, model: str):
        """
        Switch the AI model at runtime.
        Creates a fresh AIRuleMapper with the new model.

        Args:
            model: Model deployment name (e.g. 'gpt-4o-mini', 'claude-3-5-sonnet')
        """
        self._ai_mapper = AIRuleMapper(
            api_key=self._ai_mapper.api_key,
            api_base=self._ai_mapper.api_base,
            api_version=self._ai_mapper.api_version,
            model=model,
        )
        print(f"  [Orchestrator] AI model set to '{model}'.")

    @property
    def active_model(self) -> str:
        """Return the name of the currently active AI model."""
        return self._ai_mapper.model

    @property
    def is_ai_active(self) -> bool:
        """Return True if AI mapping is configured and available."""
        return self._ai_mapper._ai_active

    def map_columns(
        self,
        source_columns: List[ColumnMetadata],
        target_columns: List[ColumnMetadata],
        primary_key_hints: Optional[List[str]] = None,
        table_name: str = "unknown",
    ) -> Tuple[List[ColumnRuleMapping], str]:
        """
        Map source → target columns and assign validation rules.

        Args:
            source_columns    : PostgreSQL column metadata
            target_columns    : Snowflake column metadata
            primary_key_hints : Known PK column names (informational — no PK queries)
            table_name        : Table name for logging and AI context

        Returns:
            Tuple of:
              - List[ColumnRuleMapping] — one per matched column pair
              - str explanation         — reasoning text (empty if static)
        """
        if self._ai_mapper._ai_active:
            print(
                f"  [Orchestrator] Using AI mapper "
                f"(model: '{self._ai_mapper.model}') for '{table_name}'."
            )
            return self._ai_mapper.map_columns(
                source_columns, target_columns, primary_key_hints, table_name
            )

        print(
            f"  [Orchestrator] DIAL_API_KEY not set — "
            f"using StaticRuleMapper for '{table_name}'.",
            file=sys.stderr,
        )
        mappings = self._static_mapper.map_columns(
            source_columns, target_columns, primary_key_hints
        )
        return mappings, (
            "Static type-pair matching used (no DIAL_API_KEY). "
            "Set DIAL_API_KEY in .env to enable AI-powered rule assignment."
        )

    def describe(self) -> str:
        """Return a human-readable description of the active mapper configuration."""
        if self._ai_mapper._ai_active:
            return (
                f"RuleMapperOrchestrator: AI mode ACTIVE "
                f"(model={self._ai_mapper.model}, "
                f"base={self._ai_mapper.api_base})"
            )
        return "RuleMapperOrchestrator: Static mode (DIAL_API_KEY not configured)"

    @staticmethod
    def list_available_models() -> List[str]:
        """Return the list of models available via DIAL."""
        return list(AVAILABLE_MODELS)
