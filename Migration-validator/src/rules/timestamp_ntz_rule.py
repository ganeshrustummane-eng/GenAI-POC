"""
Timestamp Without Time Zone (NTZ) Validation Rule
===================================================
PostgreSQL TIMESTAMP / TIMESTAMP WITHOUT TIME ZONE
→  Snowflake TIMESTAMP_NTZ

Normalization:
  - Format as 'YYYY-MM-DD HH24:MI:SS' — removes fractional seconds
    so microsecond differences (common after Fivetran migration) do NOT
    create false mismatches.
  - NULL → '<<NULL>>'

Why strip microseconds:
  PostgreSQL stores TIMESTAMP with up to 6 decimal places (microseconds).
  Snowflake TIMESTAMP_NTZ may store different fractional precision.
  Fivetran sometimes truncates or rounds microseconds during load.
  Comparing at second-level precision eliminates this noise.

Example:
  PG:  2024-03-15 14:32:45.123456  →  '2024-03-15 14:32:45'
  SF:  2024-03-15 14:32:45.000     →  '2024-03-15 14:32:45'  ← match ✓
"""

from typing import List, Tuple
from rules.base_rule import BaseValidationRule


class TimestampNTZRule(BaseValidationRule):
    """
    Formats timestamp-without-timezone as 'YYYY-MM-DD HH24:MI:SS'
    to eliminate microsecond formatting differences.
    """

    @property
    def rule_name(self) -> str:
        return "timestamp_ntz"

    @property
    def description(self) -> str:
        return (
            "Timestamp NTZ: formats as 'YYYY-MM-DD HH24:MI:SS', "
            "strips microseconds. NULL→'<<NULL>>'."
        )

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [
            ("TIMESTAMP",       "TIMESTAMP_NTZ"),
            ("TIMESTAMP_NTZ",   "TIMESTAMP_NTZ"),
            ("TIMESTAMP",       "TIMESTAMP"),
            # PostgreSQL verbose form is normalized to TIMESTAMP_NTZ by base_rule._normalize_type
            ("TIMESTAMP_NTZ",   "TIMESTAMP"),
        ]

    def _pg_expression(self, col: str) -> str:
        """
        PostgreSQL: TO_CHAR formats the timestamp and strips microseconds
        by using HH24:MI:SS (no fractional seconds in the format string).
        """
        return f"TO_CHAR({col}, 'YYYY-MM-DD HH24:MI:SS')"

    def _sf_expression(self, col: str) -> str:
        """
        Snowflake: TO_VARCHAR with the same format string produces
        an identical string to PostgreSQL's TO_CHAR output.
        """
        return f"TO_VARCHAR({col}, 'YYYY-MM-DD HH24:MI:SS')"
