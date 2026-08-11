"""
PostgreSQL Schema Extractor
============================
Connects to a PostgreSQL database and extracts column-level metadata
using the information_schema.columns system view.

Credentials are loaded from environment variables (.env file):
    SOURCE_HOST, SOURCE_PORT, SOURCE_DATABASE
    SOURCE_USERNAME, SOURCE_PASSWORD

Usage:
    from sql_extractor import PostgresExtractor

    extractor = PostgresExtractor()
    columns = extractor.extract_columns(schema="public", table="events")
    for col in columns:
        print(col.column_name, col.data_type)
"""

import os
from typing import List, Optional

from sql_extractor.base_extractor import (
    BaseExtractor,
    ColumnMetadata,
    ExtractionError,
)


class PostgresExtractor(BaseExtractor):
    """
    Extracts schema metadata from a PostgreSQL database.

    Credentials are taken from environment variables by default,
    but can be overridden via constructor arguments for testing.
    """

    # SQL query to extract column metadata from information_schema.
    # udt_name is included so USER-DEFINED types (e.g. hstore, citext) resolve
    # to their actual extension type name instead of the generic 'USER-DEFINED'.
    _COLUMNS_SQL = """
        SELECT
            ordinal_position,
            column_name,
            data_type,
            udt_name,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            CASE WHEN is_nullable = 'YES' THEN TRUE ELSE FALSE END AS is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name   = %s
        ORDER BY ordinal_position;
    """

    _TABLES_SQL = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type   = 'BASE TABLE'
        ORDER BY table_name;
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize with explicit credentials or fall back to env vars.

        Environment variables:
            SOURCE_HOST, SOURCE_PORT, SOURCE_DATABASE,
            SOURCE_USERNAME, SOURCE_PASSWORD
        """
        self.host     = host     or os.getenv("SOURCE_HOST",     "localhost")
        self.port     = int(port or os.getenv("SOURCE_PORT",     "5432"))
        self.database = database or os.getenv("SOURCE_DATABASE", "postgres")
        self.username = username or os.getenv("SOURCE_USERNAME", "postgres")
        self.password = password or os.getenv("SOURCE_PASSWORD", "")

    def _get_connection(self):
        """Create and return a psycopg2 connection."""
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError as exc:
            raise ExtractionError(
                "psycopg2 is required for PostgreSQL extraction. "
                "Install with: pip install psycopg2-binary",
                exc,
            )
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                connect_timeout=15,
            )
            return conn
        except Exception as exc:
            raise ExtractionError(
                f"Cannot connect to PostgreSQL at "
                f"{self.host}:{self.port}/{self.database}: {exc}",
                exc,
            )

    def extract_columns(
        self, schema: str, table: str, database: Optional[str] = None
    ) -> List[ColumnMetadata]:
        """
        Extract column metadata for the given schema.table from PostgreSQL.

        Args:
            schema   : PostgreSQL schema (e.g. 'public')
            table    : Table name (case-insensitive in PostgreSQL)
            database : Override database for this call (default: from env/constructor)

        Returns:
            List[ColumnMetadata] ordered by ordinal_position.

        Raises:
            ExtractionError: On connection failure or if table not found.
        """
        import psycopg2.extras

        # Temporarily switch database if override given
        active_db = self.database
        if database:
            self.database = database

        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(self._COLUMNS_SQL, (schema, table.lower()))
                rows = cur.fetchall()
        finally:
            conn.close()
            self.database = active_db  # restore

        if not rows:
            db_label = database or active_db
            raise ExtractionError(
                f"No columns found for {schema}.{table} in PostgreSQL database "
                f"'{db_label}'. Check schema/table name spelling."
            )

        db_label = database or active_db
        columns = [self._row_to_column(dict(row)) for row in rows]
        print(
            f"  ✓ [PostgreSQL] Extracted {len(columns)} columns "
            f"from {db_label}.{schema}.{table}"
        )
        return columns

    def list_tables(self, schema: str) -> List[str]:
        """
        List all base tables in the given PostgreSQL schema.

        Args:
            schema : PostgreSQL schema name

        Returns:
            List of table names, alphabetically sorted.
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(self._TABLES_SQL, (schema,))
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def _row_to_column(row: dict) -> ColumnMetadata:
        """Convert an information_schema row dict to ColumnMetadata."""
        nullable_val = row.get("is_nullable")
        # Handles both boolean (True/False) and string ('YES'/'NO') forms
        if isinstance(nullable_val, bool):
            is_nullable = nullable_val
        else:
            is_nullable = str(nullable_val).upper() in ("YES", "TRUE", "1")

        # information_schema reports extension types (hstore, citext, etc.) as
        # 'USER-DEFINED'; udt_name holds the actual type name in that case.
        raw_type = row["data_type"]
        if raw_type.upper() == "USER-DEFINED":
            raw_type = row.get("udt_name", raw_type)

        return ColumnMetadata(
            ordinal_position=int(row["ordinal_position"]),
            column_name=row["column_name"],
            data_type=raw_type,
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
