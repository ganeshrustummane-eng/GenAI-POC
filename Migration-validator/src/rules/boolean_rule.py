"""
Boolean Validation Rule
========================
PostgreSQL BOOLEAN  →  Snowflake BOOLEAN

Normalization:
  - TRUE  → text '1'
  - FALSE → text '0'
  - NULL  → '<<NULL>>'

Why '1'/'0' instead of 'TRUE'/'FALSE':
  PostgreSQL stores 'true'/'false' (lowercase).
  Snowflake stores TRUE/FALSE (uppercase boolean).
  Fivetran may store BIT 1/0 for some boolean columns.
  Using '1'/'0' as the canonical form avoids all case-sensitivity issues
  and is consistent with the project specification.
"""

from typing import List, Tuple
from rules.base_rule import BaseValidationRule


class BooleanRule(BaseValidationRule):
    """
    Converts boolean values to canonical '1' (true) or '0' (false) strings.
    NULL becomes '<<NULL>>' via the inherited COALESCE wrapper.
    """

    @property
    def rule_name(self) -> str:
        return "boolean"

    @property
    def description(self) -> str:
        return (
            "Boolean: TRUE→'1', FALSE→'0'. "
            "Handles PostgreSQL BOOLEAN (true/false) and Snowflake BOOLEAN (TRUE/FALSE). "
            "NULL→'<<NULL>>'."
        )

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [
            ("BOOLEAN", "BOOLEAN"),
            ("BOOLEAN", "BOOL"),
            ("BOOL",    "BOOLEAN"),
            ("BOOL",    "BOOL"),
        ]

    def _pg_expression(self, col: str) -> str:
        """
        PostgreSQL: BOOLEAN stores true/false literals.
        Cast CASE result to TEXT before COALESCE wraps it.
        """
        return (
            f"CASE "
            f"WHEN {col} = true  THEN '1' "
            f"WHEN {col} = false THEN '0' "
            f"ELSE NULL "
            f"END"
        )

    def _sf_expression(self, col: str) -> str:
        """
        Snowflake: BOOLEAN stores TRUE/FALSE.
        Fivetran may also land BOOLEAN columns as TRUE/FALSE strings.
        """
        return (
            f"CASE "
            f"WHEN {col} = TRUE  THEN '1' "
            f"WHEN {col} = FALSE THEN '0' "
            f"ELSE NULL "
            f"END"
        )
