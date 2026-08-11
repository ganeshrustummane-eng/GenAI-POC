"""
Timestamp With Time Zone (TZ) Validation Rule
==============================================
PostgreSQL TIMESTAMP WITH TIME ZONE (TIMESTAMPTZ)
→  Snowflake TIMESTAMP_TZ

Normalization:
  - Convert to UTC first (AT TIME ZONE 'UTC'), then format as
    'YYYY-MM-DD HH24:MI:SS' for a common, timezone-agnostic comparison.
  - Removes fractional seconds to eliminate microsecond noise.
  - NULL → '<<NULL>>'

Why UTC normalization:
  PostgreSQL TIMESTAMPTZ stores the moment in time and applies session
  timezone on display. Snowflake TIMESTAMP_TZ stores offset alongside
  the value. Converting both to UTC eliminates timezone offset differences
  that may have been introduced during ETL migration.

Example:
  PG:  2024-03-15 14:32:45+05:30  →  '2024-03-15 09:02:45'  (UTC)
  SF:  2024-03-15 09:02:45 +0000  →  '2024-03-15 09:02:45'  ← match ✓
"""

from typing import List, Tuple
from rules.base_rule import BaseValidationRule


class TimestampTZRule(BaseValidationRule):
    """
    Normalizes timezone-aware timestamps to UTC, then formats as
    'YYYY-MM-DD HH24:MI:SS' for consistent cross-system comparison.
    """

    @property
    def rule_name(self) -> str:
        return "timestamp_tz"

    @property
    def description(self) -> str:
        return (
            "Timestamp TZ: converts to UTC, formats as 'YYYY-MM-DD HH24:MI:SS', "
            "strips microseconds. NULL→'<<NULL>>'."
        )

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [
            ("TIMESTAMP_TZ",  "TIMESTAMP_TZ"),
            # PostgreSQL 'timestamp with time zone' normalizes to TIMESTAMP_TZ
            ("TIMESTAMP_TZ",  "TIMESTAMPTZ"),
            ("TIMESTAMPTZ",   "TIMESTAMP_TZ"),
        ]

    def _pg_expression(self, col: str) -> str:
        """
        PostgreSQL:
          AT TIME ZONE 'UTC' converts the stored moment to UTC.
          TO_CHAR then formats without fractional seconds.
        """
        return f"TO_CHAR({col} AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')"

    def _sf_expression(self, col: str) -> str:
        """
        Snowflake:
          CONVERT_TIMEZONE('UTC', col) shifts the stored value to UTC.
          TO_VARCHAR then formats without fractional seconds.
        """
        return f"TO_VARCHAR(CONVERT_TIMEZONE('UTC', {col}), 'YYYY-MM-DD HH24:MI:SS')"
