"""
Bytea / Binary Validation Rule
================================
PostgreSQL BYTEA  →  Snowflake BINARY / VARBINARY

Normalization:
  - Converts binary data into a hexadecimal text representation.
  - NULL → '<<NULL>>'

Why hex representation:
  Binary data cannot be compared as raw bytes across different systems
  due to encoding differences and display format variations.
  Converting to a hex string (e.g. '\\xDEADBEEF') gives a stable,
  system-agnostic text representation for comparison.

Note:
  Large binary columns (images, documents) may be expensive to compare
  via SQL. For tables with large BYTEA columns, consider comparing
  hash values (MD5/SHA256) instead of full hex strings.
"""

from typing import List, Tuple
from rules.base_rule import BaseValidationRule


class ByteaRule(BaseValidationRule):
    """
    Converts binary/bytea columns to hex text for comparison.
    NULL → '<<NULL>>'.
    """

    @property
    def rule_name(self) -> str:
        return "bytea"

    @property
    def description(self) -> str:
        return (
            "Binary/BYTEA: converts to hexadecimal text representation. "
            "NULL→'<<NULL>>'."
        )

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [
            ("BYTEA",     "BINARY"),
            ("BYTEA",     "VARBINARY"),
            ("BINARY",    "BINARY"),
            ("VARBINARY", "BINARY"),
            ("BYTEA",     "VARCHAR"),
            ("BYTEA",     "STRING"),
        ]

    def _pg_expression(self, col: str) -> str:
        """
        PostgreSQL:
          encode(col, 'hex') converts BYTEA to its lowercase hex string.
          Example: \\x48656c6c6f → '48656c6c6f'
        """
        return f"encode({col}, 'hex')"

    def _sf_expression(self, col: str) -> str:
        """
        Snowflake:
          HEX_ENCODE converts BINARY to uppercase hex string.
          LOWER() ensures case-consistent comparison with PostgreSQL output.
        """
        return f"LOWER(HEX_ENCODE({col}))"
