"""
NULL Placeholder Rule
======================
Universal rule: SQL NULL → '<<NULL>>' text placeholder.

This is a STANDALONE rule used when you need ONLY the NULL wrapping
without any other transformation. In practice, all other rules
already include the COALESCE wrapper via BaseValidationRule.apply_postgresql()
and apply_snowflake().

This rule exists in the registry for:
  1. Columns that have no type-specific transformation needed (bare cast to text).
  2. Direct invocation when building composite rule chains manually.

Why <<NULL>> instead of 'NULL':
  SQL does NOT allow NULL = NULL comparisons (NULL ≠ NULL).
  Converting NULL to a visible string makes equality checks work correctly.
  The '<<NULL>>' sentinel is chosen to be visually distinct and
  extremely unlikely to appear as actual data in a real column.

Per Project Spec:
  "If NULL, shows <<NULL>>."  ← applied to ALL column types.
"""

from typing import List, Tuple
from rules.base_rule import BaseValidationRule, NULL_PLACEHOLDER


class NullPlaceholderRule(BaseValidationRule):
    """
    Converts SQL NULL to '<<NULL>>' sentinel text.
    For all other values, casts directly to text without transformation.

    This is effectively the baseline rule — cast to text + null placeholder.
    """

    @property
    def rule_name(self) -> str:
        return "null_placeholder"

    @property
    def description(self) -> str:
        return (
            f"NULL placeholder: SQL NULL → '{NULL_PLACEHOLDER}'. "
            f"Other values cast directly to text. Universal rule."
        )

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        # This rule is used when explicitly requested; not auto-matched by type.
        # Real auto-matching goes through TextRule ('*', '*') fallback.
        return []

    def _pg_expression(self, col: str) -> str:
        """PostgreSQL: plain cast to TEXT (COALESCE added by base class)."""
        return f"CAST({col} AS TEXT)"

    def _sf_expression(self, col: str) -> str:
        """Snowflake: plain cast to STRING (COALESCE added by base class)."""
        return f"CAST({col} AS STRING)"

    def apply_postgresql(self, col: str, alias=None) -> str:
        """Override to produce just COALESCE without double-casting."""
        expr = f"COALESCE(CAST({col} AS TEXT), '{NULL_PLACEHOLDER}')"
        return f"{expr} AS {alias}" if alias else expr

    def apply_snowflake(self, col: str, alias=None) -> str:
        """Override to produce just COALESCE without double-casting."""
        expr = f"COALESCE(CAST({col} AS STRING), '{NULL_PLACEHOLDER}')"
        return f"{expr} AS {alias}" if alias else expr
