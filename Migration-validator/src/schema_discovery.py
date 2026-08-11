"""
Schema Discovery — generates introspection queries users run manually.

Users copy the printed SQL into their SQL client, run it, and paste the
JSON/CSV result back into the AI agent via --schema-file or stdin.
No live DB connection is required here.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from models import DatabaseType


@dataclass
class ColumnInfo:
    """Metadata for a single column, as returned by an introspection query."""
    column_name: str
    data_type: str
    is_nullable: bool = True
    character_maximum_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    column_default: Optional[str] = None
    ordinal_position: int = 0

    def type_summary(self) -> str:
        """Human-readable type string, e.g. VARCHAR(100) or DECIMAL(18,2)."""
        t = self.data_type.upper()
        if self.character_maximum_length:
            return f"{t}({self.character_maximum_length})"
        if self.numeric_precision and self.numeric_scale is not None:
            return f"{t}({self.numeric_precision},{self.numeric_scale})"
        if self.numeric_precision:
            return f"{t}({self.numeric_precision})"
        return t


# ---------------------------------------------------------------------------
# Introspection query builders
# ---------------------------------------------------------------------------

def get_schema_introspection_query(
    db_type: DatabaseType,
    schema: str,
    table: str,
    database: Optional[str] = None,
) -> str:
    """
    Return the SQL that the user should run against their source or target DB
    to obtain column metadata. The result should be exported as JSON/CSV and
    fed to the AI agent via --schema-file.
    """
    if db_type == DatabaseType.MSSQL:
        return f"""-- Run this on your SQL Server source
SELECT
    ORDINAL_POSITION        AS ordinal_position,
    COLUMN_NAME             AS column_name,
    DATA_TYPE               AS data_type,
    CHARACTER_MAXIMUM_LENGTH AS character_maximum_length,
    NUMERIC_PRECISION       AS numeric_precision,
    NUMERIC_SCALE           AS numeric_scale,
    IS_NULLABLE             AS is_nullable,
    COLUMN_DEFAULT          AS column_default
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '{schema}'
  AND TABLE_NAME   = '{table}'
ORDER BY ORDINAL_POSITION;"""

    elif db_type == DatabaseType.POSTGRESQL:
        return f"""-- Run this on your PostgreSQL source
SELECT
    ordinal_position,
    column_name,
    data_type,
    character_maximum_length,
    numeric_precision,
    numeric_scale,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = '{schema}'
  AND table_name   = '{table}'
ORDER BY ordinal_position;"""

    elif db_type == DatabaseType.SNOWFLAKE:
        db_clause = f"AND TABLE_CATALOG = '{database}'" if database else ""
        return f"""-- Run this on your Snowflake target
SELECT
    ORDINAL_POSITION        AS ordinal_position,
    COLUMN_NAME             AS column_name,
    DATA_TYPE               AS data_type,
    CHARACTER_MAXIMUM_LENGTH AS character_maximum_length,
    NUMERIC_PRECISION       AS numeric_precision,
    NUMERIC_SCALE           AS numeric_scale,
    IS_NULLABLE             AS is_nullable,
    COLUMN_DEFAULT          AS column_default
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '{schema}'
  AND TABLE_NAME   = '{table}'
  {db_clause}
ORDER BY ORDINAL_POSITION;"""

    raise ValueError(f"Unsupported db_type: {db_type}")


def get_table_list_query(
    db_type: DatabaseType,
    schema: str,
    database: Optional[str] = None,
) -> str:
    """Return SQL to list all tables in a schema (for discovery)."""
    if db_type == DatabaseType.MSSQL:
        return f"""SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = '{schema}' AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;"""

    elif db_type == DatabaseType.POSTGRESQL:
        return f"""SELECT table_name FROM information_schema.tables
WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE'
ORDER BY table_name;"""

    elif db_type == DatabaseType.SNOWFLAKE:
        db_clause = f"AND TABLE_CATALOG = '{database}'" if database else ""
        return f"""SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = '{schema}' {db_clause} AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;"""

    raise ValueError(f"Unsupported db_type: {db_type}")


# ---------------------------------------------------------------------------
# Result parsers
# ---------------------------------------------------------------------------

def parse_column_info_from_rows(rows: List[Dict[str, Any]]) -> List[ColumnInfo]:
    """
    Convert raw rows returned from an introspection query (as list of dicts)
    into ColumnInfo objects.  Column names are normalised to lowercase.
    """
    result = []
    for row in rows:
        # Normalise key case
        r = {k.lower(): v for k, v in row.items()}
        col = ColumnInfo(
            column_name=str(r.get("column_name", "")),
            data_type=str(r.get("data_type", "VARCHAR")),
            is_nullable=str(r.get("is_nullable", "YES")).upper() in ("YES", "TRUE", "1"),
            character_maximum_length=_to_int(r.get("character_maximum_length")),
            numeric_precision=_to_int(r.get("numeric_precision")),
            numeric_scale=_to_int(r.get("numeric_scale")),
            column_default=r.get("column_default"),
            ordinal_position=_to_int(r.get("ordinal_position")) or 0,
        )
        result.append(col)
    return sorted(result, key=lambda c: c.ordinal_position)


def parse_column_info_from_json(json_data: Any) -> List[ColumnInfo]:
    """Parse from a JSON value — either a list of dicts or dict of lists."""
    import json as _json

    if isinstance(json_data, str):
        json_data = _json.loads(json_data)

    if isinstance(json_data, list):
        return parse_column_info_from_rows(json_data)

    # Some SQL clients export {"columns": [...], "rows": [...]}
    if isinstance(json_data, dict):
        for key in ("rows", "data", "results", "columns"):
            if key in json_data and isinstance(json_data[key], list):
                return parse_column_info_from_rows(json_data[key])

    raise ValueError("Unrecognised JSON schema result format. Expected a list of column-metadata dicts.")


def column_info_to_dict(col: ColumnInfo) -> Dict[str, Any]:
    """Serialise a ColumnInfo to a plain dict for JSON / prompt injection."""
    return {
        "column_name": col.column_name,
        "data_type": col.type_summary(),
        "is_nullable": col.is_nullable,
        "ordinal_position": col.ordinal_position,
    }


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
