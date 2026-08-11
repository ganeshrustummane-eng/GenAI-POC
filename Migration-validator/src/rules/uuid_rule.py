"""
UUID Validation Rule
=====================
PostgreSQL UUID (native UUID type)
→  Snowflake TEXT / VARCHAR / STRING (UUID stored as text)

Normalization:
  - Convert to UPPERCASE text and TRIM whitespace.
  - NULL → '<<NULL>>'

Why uppercase:
  The project specification explicitly states:
    "Uppercasing UUIDs → ignores case differences."
  PostgreSQL stores UUID in lowercase by default: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Snowflake may store UUIDs in uppercase (XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX)
  depending on the ETL tool used (Fivetran sometimes uppercases UUIDs).

Why also TRIM:
  Snowflake VARCHAR columns may have been loaded with trailing spaces
  if the ETL tool padded the fixed-width UUID string.

Example:
  PG:  'a1b2c3d4-e5f6-7890-abcd-ef1234567890'  →  'A1B2C3D4-E5F6-7890-ABCD-EF1234567890'
  SF:  'A1B2C3D4-E5F6-7890-ABCD-EF1234567890'  →  'A1B2C3D4-E5F6-7890-ABCD-EF1234567890'  ← match ✓
"""

from typing import List, Tuple
from rules.base_rule import BaseValidationRule


class UUIDRule(BaseValidationRule):
    """
    Normalizes UUID columns to UPPERCASE text with trimmed whitespace.
    NULL → '<<NULL>>'.
    """

    @property
    def rule_name(self) -> str:
        return "uuid"

    @property
    def description(self) -> str:
        return (
            "UUID: converts to UPPERCASE text and trims spaces. "
            "Handles PostgreSQL native UUID → Snowflake VARCHAR/TEXT. "
            "NULL→'<<NULL>>'."
        )

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [
            ("UUID", "TEXT"),
            ("UUID", "VARCHAR"),
            ("UUID", "STRING"),
            ("UUID", "UUID"),
        ]

    def _pg_expression(self, col: str) -> str:
        """
        PostgreSQL:
          CAST to TEXT (UUID native type → text representation)
          then UPPER and TRIM.
        """
        return f"UPPER(TRIM(CAST({col} AS TEXT)))"

    def _sf_expression(self, col: str) -> str:
        """
        Snowflake:
          UUID is stored as VARCHAR/STRING.
          UPPER and TRIM to match the normalized form.
        """
        return f"UPPER(TRIM(CAST({col} AS STRING)))"
