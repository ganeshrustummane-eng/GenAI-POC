"""
HStore Validation Rule
========================
PostgreSQL HSTORE (key-value store) → Snowflake VARCHAR / TEXT / STRING

Normalization:
  - PostgreSQL: CAST to TEXT first (required — TRIM() cannot accept hstore directly),
    then TRIM whitespace.
  - Snowflake: TRIM whitespace (Fivetran stores hstore as JSON-formatted text).
  - NULL → '<<NULL>>'

Why explicit CAST is needed:
  PostgreSQL's TRIM() function (pg_catalog.btrim) does not accept the hstore type.
  Calling TRIM(hstore_column) produces:
    ERROR: function pg_catalog.btrim(hstore) does not exist
  The column must be explicitly cast to TEXT before any string function is applied.

How Fivetran migrates hstore:
  Fivetran converts PostgreSQL hstore columns to a JSON-formatted string representation
  in Snowflake (stored as VARCHAR/TEXT). Example:
    PG hstore:  "gate_access_code"=>"02378", "move_in_date"=>"2014-02-01"
    SF text:    {"gate_access_code":"02378","move_in_date":"2014-02-01"}

  Note: The format may differ slightly — hstore's text representation uses
  "key"=>"value" while JSON uses "key":"value". For validation purposes,
  we compare the raw text representation as-is after trimming.

Example:
  PG:  '"key1"=>"val1", "key2"=>"val2"'  →  (trimmed text)
  SF:  '{"key1":"val1","key2":"val2"}'    →  (trimmed text)
  These may NOT match perfectly due to format differences — see notes below.

  PG:  NULL  →  '<<NULL>>'
  SF:  NULL  →  '<<NULL>>'  ← match ✓

Important Notes:
  - The PostgreSQL hstore text format ("key"=>"value") differs from
    Snowflake's JSON format ({"key":"value"}). If exact text comparison
    fails, consider using ignore_validation or custom comparison logic.
  - This rule ensures the SQL is valid and runs without errors.
    Data comparison accuracy depends on Fivetran's conversion format.
"""

from typing import List, Tuple
from rules.base_rule import BaseValidationRule


class HStoreRule(BaseValidationRule):
    """
    Handles PostgreSQL hstore columns by casting to TEXT before trimming.

    PostgreSQL TRIM() does not accept hstore type directly — an explicit
    CAST(col AS TEXT) is required before string operations.

    On Snowflake side, Fivetran stores hstore as VARCHAR/TEXT so
    standard TRIM() works directly.
    """

    @property
    def rule_name(self) -> str:
        return "hstore"

    @property
    def description(self) -> str:
        return (
            "HStore: CAST to TEXT then TRIM. "
            "PostgreSQL hstore requires explicit CAST before TRIM. "
            "NULL→'<<NULL>>'."
        )

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [
            ("HSTORE", "TEXT"),
            ("HSTORE", "VARCHAR"),
            ("HSTORE", "STRING"),
            ("HSTORE", "VARIANT"),
        ]

    def _pg_expression(self, col: str) -> str:
        """
        PostgreSQL: MUST cast hstore to TEXT before applying TRIM.
        Without this cast, btrim(hstore) will fail.
        """
        return f"TRIM(CAST({col} AS TEXT))"

    def _sf_expression(self, col: str) -> str:
        """
        Snowflake: Fivetran stores hstore as TEXT/VARCHAR, so TRIM works directly.
        """
        return f"TRIM({col})"
