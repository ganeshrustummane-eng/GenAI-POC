"""
Date Validation Rule
=====================
PostgreSQL DATE  →  Snowflake DATE

Normalization:
  - Format as 'YYYY-MM-DD' text string for uniform cross-system comparison.
  - NULL → '<<NULL>>'

Note: DATE is consistent between PostgreSQL and Snowflake — both store only
the calendar date without a time component. The normalization to text is
still required to make the comparison symmetric (TEXT vs TEXT).

Example:
  PG:  2024-03-15  →  '2024-03-15'
  SF:  2024-03-15  →  '2024-03-15'  ← match ✓
"""

from typing import List, Tuple
from rules.base_rule import BaseValidationRule


class DateRule(BaseValidationRule):
    """
    Formats DATE columns as 'YYYY-MM-DD' text for uniform comparison.
    """

    @property
    def rule_name(self) -> str:
        return "date"

    @property
    def description(self) -> str:
        return "Date: formats as 'YYYY-MM-DD'. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [
            ("DATE", "DATE"),
        ]

    def _pg_expression(self, col: str) -> str:
        """PostgreSQL: TO_CHAR with ISO date format."""
        return f"TO_CHAR({col}, 'YYYY-MM-DD')"

    def _sf_expression(self, col: str) -> str:
        """Snowflake: TO_VARCHAR with ISO date format."""
        return f"TO_VARCHAR({col}, 'YYYY-MM-DD')"
