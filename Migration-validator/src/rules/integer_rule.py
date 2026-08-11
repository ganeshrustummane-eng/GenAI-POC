"""
Integer Validation Rule
========================
PostgreSQL INTEGER / BIGINT / SMALLINT / SERIAL / BIGSERIAL
→  Snowflake NUMBER (integer-mapped)

Normalization:
  - Cast to text for cross-system comparison.
  - Avoids type width differences between PostgreSQL INTEGER and Snowflake NUMBER.
  - NULL → '<<NULL>>'

Why cast to text:
  PostgreSQL INTEGER is 32-bit; BIGINT is 64-bit.
  Snowflake NUMBER is arbitrary precision.
  Converting both to text string representation eliminates type width mismatches
  while preserving the integer value for comparison.

Example:
  PG:  42       →  '42'
  SF:  42       →  '42'   ← match ✓
"""

from typing import List, Tuple
from rules.base_rule import BaseValidationRule


class IntegerRule(BaseValidationRule):
    """
    Casts integer-family columns to text for cross-system comparison.
    NULL → '<<NULL>>'.
    """

    @property
    def rule_name(self) -> str:
        return "integer"

    @property
    def description(self) -> str:
        return (
            "Integer: converts to text for cross-system comparison. "
            "Handles SMALLINT/INT/BIGINT/SERIAL → NUMBER. NULL→'<<NULL>>'."
        )

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [
            ("SMALLINT",  "NUMBER"),
            ("SMALLINT",  "INTEGER"),
            ("INTEGER",   "NUMBER"),
            ("INTEGER",   "INTEGER"),
            ("INT",       "NUMBER"),
            ("INT",       "INTEGER"),
            ("BIGINT",    "NUMBER"),
            ("BIGINT",    "INTEGER"),
            ("SERIAL",    "NUMBER"),
            ("SERIAL",    "INTEGER"),
            ("BIGSERIAL", "NUMBER"),
            ("BIGSERIAL", "INTEGER"),
        ]

    def _pg_expression(self, col: str) -> str:
        """PostgreSQL: cast INTEGER/BIGINT to TEXT."""
        return f"CAST({col} AS TEXT)"

    def _sf_expression(self, col: str) -> str:
        """Snowflake: cast NUMBER to STRING (equivalent to TEXT)."""
        return f"CAST({col} AS STRING)"
# We dont hav cast to text or string (Conditional)