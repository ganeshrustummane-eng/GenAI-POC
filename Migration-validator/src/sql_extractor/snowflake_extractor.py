"""
Snowflake Schema Extractor
===========================
Connects to a Snowflake database and extracts column-level metadata
using the INFORMATION_SCHEMA.COLUMNS system view.

Also applies the Fivetran-specific filter logic:
  - Detects presence of _FIVETRAN_ACTIVE column.
  - Generated Snowflake queries automatically include
    WHERE _FIVETRAN_ACTIVE = TRUE to compare only active (latest) records.

Credentials loaded from environment variables:
    SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA
    SNOWFLAKE_USERNAME, SNOWFLAKE_PASSWORD

Usage:
    from sql_extractor import SnowflakeExtractor

    extractor = SnowflakeExtractor()
    columns = extractor.extract_columns(schema="STOREDGE_FMS_PUBLIC", table="EVENTS")
    print(extractor.has_fivetran_active(columns))  # True/False
"""

import os
from typing import List, Optional

from sql_extractor.base_extractor import (
    BaseExtractor,
    ColumnMetadata,
    ExtractionError,
)

# Fivetran metadata column that marks the latest active record
FIVETRAN_ACTIVE_COLUMN = "_FIVETRAN_ACTIVE"


class SnowflakeExtractor(BaseExtractor):
    """
    Extracts schema metadata from a Snowflake database.

    Additionally detects Fivetran metadata columns so that generated SQL
    can filter to only the latest active records (_FIVETRAN_ACTIVE = TRUE).
    """

    _COLUMNS_SQL = """
        SELECT
            ORDINAL_POSITION         AS ordinal_position,
            COLUMN_NAME              AS column_name,
            DATA_TYPE                AS data_type,
            CHARACTER_MAXIMUM_LENGTH AS character_maximum_length,
            NUMERIC_PRECISION        AS numeric_precision,
            NUMERIC_SCALE            AS numeric_scale,
            CASE WHEN IS_NULLABLE = 'YES' THEN TRUE ELSE FALSE END AS is_nullable,
            COLUMN_DEFAULT           AS column_default
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME   = %s
        ORDER BY ORDINAL_POSITION;
    """

    _TABLES_SQL = """
        SELECT TABLE_NAME
        FROM {database}.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = %s
          AND TABLE_TYPE   = 'BASE TABLE'
        ORDER BY TABLE_NAME;
    """

    def __init__(
        self,
        account: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize with explicit credentials or fall back to env vars.

        Environment variables:
            SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA,
            SNOWFLAKE_USERNAME, SNOWFLAKE_PASSWORD
        """
        self.account  = account  or os.getenv("SNOWFLAKE_ACCOUNT",  "")
        self.database = database or os.getenv("SNOWFLAKE_DATABASE", "")
        self.schema   = schema   or os.getenv("SNOWFLAKE_SCHEMA",   "")
        self.username = username or os.getenv("SNOWFLAKE_USERNAME", "")
        self.password = password or os.getenv("SNOWFLAKE_PASSWORD", "")

    def _get_connection(self):
        """Create and return a Snowflake connector connection."""
        try:
            import snowflake.connector
        except ImportError as exc:
            raise ExtractionError(
                "snowflake-connector-python is required. "
                "Install with: pip install snowflake-connector-python",
                exc,
            )
        try:
            conn = snowflake.connector.connect(
                user=self.username,
                password=self.password,
                account=self.account,
                database=self.database,
                login_timeout=30,
            )
            return conn
        except Exception as exc:
            raise ExtractionError(
                f"Cannot connect to Snowflake account '{self.account}': {exc}",
                exc,
            )

    def extract_columns(self, schema: str, table: str) -> List[ColumnMetadata]:
        """
        Extract column metadata for schema.table from Snowflake.

        Args:
            schema : Snowflake schema name (case-insensitive, stored UPPER)
            table  : Table name (case-insensitive, stored UPPER in Snowflake)

        Returns:
            List[ColumnMetadata] ordered by ordinal_position.

        Raises:
            ExtractionError: On connection failure or if table not found.
        """
        import snowflake.connector

        conn = self._get_connection()
        sql = self._COLUMNS_SQL.format(database=self.database)
        try:
            with conn.cursor(snowflake.connector.DictCursor) as cur:
                cur.execute(sql, (schema.upper(), table.upper()))
                rows = [{k.lower(): v for k, v in row.items()} for row in cur.fetchall()]
        finally:
            conn.close()

        if not rows:
            raise ExtractionError(
                f"No columns found for {schema}.{table} in Snowflake database "
                f"'{self.database}'. Check schema/table name spelling."
            )

        columns = [self._row_to_column(row) for row in rows]
        print(
            f"  ✓ [Snowflake] Extracted {len(columns)} columns "
            f"from {self.database}.{schema}.{table}"
        )
        return columns

    def list_tables(self, schema: str) -> List[str]:
        """
        List all base tables in the given Snowflake schema.

        Args:
            schema : Snowflake schema name (auto-uppercased)

        Returns:
            List of table names in the schema.
        """
        import snowflake.connector

        conn = self._get_connection()
        sql = self._TABLES_SQL.format(database=self.database)
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (schema.upper(),))
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def has_fivetran_active(columns: List[ColumnMetadata]) -> bool:
        """
        Returns True if the table has the Fivetran _FIVETRAN_ACTIVE column.
        When True, generated Snowflake queries should include:
            WHERE _FIVETRAN_ACTIVE = TRUE

        This ensures only the latest active record is compared,
        not historical snapshots created by Fivetran's change tracking.
        """
        return any(
            col.column_name.upper() == FIVETRAN_ACTIVE_COLUMN
            for col in columns
        )

    @staticmethod
    def _row_to_column(row: dict) -> ColumnMetadata:
        """Convert an INFORMATION_SCHEMA row dict to ColumnMetadata."""
        nullable_val = row.get("is_nullable")
        if isinstance(nullable_val, bool):
            is_nullable = nullable_val
        else:
            is_nullable = str(nullable_val).upper() in ("YES", "TRUE", "1")

        return ColumnMetadata(
            ordinal_position=int(row["ordinal_position"]),
            column_name=row["column_name"],
            data_type=row["data_type"],
            is_nullable=is_nullable,
            char_max_length=(
                int(row["character_maximum_length"])
                if row.get("character_maximum_length") is not None
                else None
            ),
            numeric_precision=(
                int(row["numeric_precision"])
                if row.get("numeric_precision") is not None
                else None
            ),
            numeric_scale=(
                int(row["numeric_scale"])
                if row.get("numeric_scale") is not None
                else None
            ),
            column_default=row.get("column_default"),
        )
