"""
Numeric / Decimal Validation Rule
===================================
PostgreSQL NUMERIC / DECIMAL / FLOAT / REAL / DOUBLE PRECISION
→  Snowflake NUMBER / FLOAT / DECIMAL

Normalization:
  - Round to 2 decimal places (agreed precision) then convert to text.
  - Avoids false mismatches from floating-point precision differences
    introduced by ETL tools like Fivetran.
  - NULL → '<<NULL>>'

Example:
  PG:  1234.5678  →  '1234.57'
  SF:  1234.57    →  '1234.57'   ← match ✓
"""

from typing import List, Tuple
from rules.base_rule import BaseValidationRule


# Default precision used across the project; can be overridden per column.
DEFAULT_DECIMAL_PLACES: int = 2


class NumericRule(BaseValidationRule):
    """
    Rounds numeric/decimal values to a fixed number of decimal places
    before converting to text for cross-system comparison.
    """

    def __init__(self, decimal_places: int = DEFAULT_DECIMAL_PLACES):
        """
        Args:
            decimal_places: Number of decimal places to round to (default: 2).
        """
        self._decimal_places = decimal_places

    @property
    def rule_name(self) -> str:
        return "numeric"

    @property
    def description(self) -> str:
        return (
            f"Numeric: rounds to {self._decimal_places} decimal places, "
            f"then converts to text. Avoids precision noise. NULL→'<<NULL>>'."
        )

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [
            ("NUMERIC",           "NUMBER"),
            ("NUMERIC",           "NUMERIC"),
            ("DECIMAL",           "NUMBER"),
            ("DECIMAL",           "DECIMAL"),
            ("FLOAT",             "FLOAT"),
            ("REAL",              "FLOAT"),
            ("DOUBLE PRECISION",  "FLOAT"),
            ("DOUBLE PRECISION",  "NUMBER"),
            ("MONEY",             "NUMBER"),
        ]

    def _pg_expression(self, col: str) -> str:
        """
        PostgreSQL: ROUND(CAST(col AS NUMERIC), N)
        CAST to NUMERIC first ensures ROUND works on all numeric types.
        """
        dp = self._decimal_places
        return f"ROUND(CAST({col} AS NUMERIC), {dp})"

    def _sf_expression(self, col: str) -> str:
        """
        Snowflake: ROUND(CAST(col AS NUMBER(38, N)), N)
        NUMBER(38,2) is the canonical Snowflake numeric type for 2dp.
        """
        dp = self._decimal_places
        return f"ROUND(CAST({col} AS NUMBER(38, {dp})), {dp})"
