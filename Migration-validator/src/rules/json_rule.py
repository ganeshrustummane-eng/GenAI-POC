"""
JSON / JSONB Validation Rule
==============================
PostgreSQL JSON / JSONB  →  Snowflake VARIANT (JSON)

Normalization:
  - Converts JSON into a canonical text representation before comparison.
  - Uses database-native JSON serialization to eliminate key ordering
    and whitespace formatting differences.
  - NULL → '<<NULL>>'

Why canonical JSON:
  JSON objects can be formatted differently:
    {"a":1,"b":2}  vs  { "b": 2, "a": 1 }
  These represent the same data but would fail a plain text comparison.
  Converting to a canonical form (e.g. sorted keys, no extra whitespace)
  eliminates these false mismatches.

Note:
  Full JSON deep-comparison is complex. This rule applies best-effort
  canonical serialization. For production use, consider dedicated JSON diff
  tooling for 100% accuracy.
"""

from typing import List, Tuple
from rules.base_rule import BaseValidationRule


class JSONRule(BaseValidationRule):
    """
    Converts JSON/JSONB to canonical text representation for comparison.
    NULL → '<<NULL>>'.
    """

    @property
    def rule_name(self) -> str:
        return "json"

    @property
    def description(self) -> str:
        return (
            "JSON/JSONB → Variant: converts to canonical JSON string. "
            "Eliminates key-ordering and whitespace differences. NULL→'<<NULL>>'."
        )

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [
            ("JSON",  "VARIANT"),
            ("JSON",  "VARCHAR"),
            ("JSON",  "STRING"),
            ("JSON",  "TEXT"),
            ("JSONB", "VARIANT"),
            ("JSONB", "VARCHAR"),
            ("JSONB", "STRING"),
            ("JSONB", "TEXT"),
        ]

    def _pg_expression(self, col: str) -> str:
        """
        PostgreSQL:
          col::jsonb re-parses the JSON (normalizes whitespace),
          then ::text converts it to a canonical text form.
          jsonb automatically sorts keys alphabetically.
        """
        return f"{col}::jsonb::text"

    def _sf_expression(self, col: str) -> str:
        """
        Snowflake:
          PARSE_JSON re-parses the VARIANT,
          TO_JSON serializes it back as a canonical JSON string.
        """
        return f"TO_JSON(PARSE_JSON(CAST({col} AS STRING)))"
