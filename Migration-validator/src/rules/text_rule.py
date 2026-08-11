"""
Text Validation Rule
=====================
PostgreSQL VARCHAR / CHAR / TEXT / CHARACTER VARYING
→  Snowflake VARCHAR / TEXT / STRING

Normalization:
  - TRIM leading and trailing whitespace.
  - Empty string ('') remains as '' — kept distinct from NULL.
  - NULL → '<<NULL>>'

Why trim whitespace:
  ETL tools (Fivetran, custom scripts) may introduce trailing spaces
  when padding CHAR columns or during CSV-based load.

Why preserve empty strings:
  An empty string is semantically different from NULL.
  The project spec explicitly states:
    "Empty string remains blank (kept different from NULL)."
  Therefore we do NOT use NULLIF(col, '') here — only TRIM.

Example:
  PG:  '  hello world  '  →  'hello world'
  SF:  'hello world'      →  'hello world'  ← match ✓

  PG:  ''  (empty)  →  ''
  SF:  ''  (empty)  →  ''               ← match ✓

  PG:  NULL  →  '<<NULL>>'
  SF:  NULL  →  '<<NULL>>'              ← match ✓
"""

from typing import List, Tuple
from rules.base_rule import BaseValidationRule


class TextRule(BaseValidationRule):
    """
    Trims leading/trailing whitespace from text columns.
    Empty strings remain empty (not converted to NULL).
    NULL → '<<NULL>>'.

    This rule is also the DEFAULT FALLBACK for any type not matched
    by a more specific rule.
    """

    @property
    def rule_name(self) -> str:
        return "text"

    @property
    def description(self) -> str:
        return (
            "Text: trims leading/trailing spaces. "
            "Empty string stays empty (≠ NULL). NULL→'<<NULL>>'."
        )

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [
            ("CHARACTER VARYING", "TEXT"),
            ("CHARACTER VARYING", "VARCHAR"),
            ("CHARACTER VARYING", "STRING"),
            ("VARCHAR",           "VARCHAR"),
            ("VARCHAR",           "STRING"),
            ("VARCHAR",           "TEXT"),
            ("CHAR",              "CHAR"),
            ("CHAR",              "VARCHAR"),
            ("CHAR",              "STRING"),
            ("TEXT",              "TEXT"),
            ("TEXT",              "VARCHAR"),
            ("TEXT",              "STRING"),
            # Wildcard fallback — text handles any unmatched type pair
            ("*",                 "*"),
        ]

    def _pg_expression(self, col: str) -> str:
        """
        PostgreSQL: standard TRIM() removes both leading and trailing spaces.
        """
        return f"TRIM({col})"

    def _sf_expression(self, col: str) -> str:
        """
        Snowflake: TRIM() is equivalent to PostgreSQL's TRIM().
        """
        return f"TRIM({col})"
