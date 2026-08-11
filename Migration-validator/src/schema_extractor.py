"""
Schema Extractor — Live Dynamic Schema Discovery
=================================================
Connects directly to PostgreSQL (source) and Snowflake (target) using
credentials from the .env file and extracts REAL column metadata at runtime.

This eliminates all static column definitions from the old main_example.py.
You only provide: database name, schema name, table name — the rest is automatic.

Flow
----
  PostgreSQL  ──► extract_postgres_schema()  ──► List[ColumnInfo]
  Snowflake   ──► extract_snowflake_schema() ──► List[ColumnInfo]
  Both        ──► SchemaComparison            ──► side-by-side diff for AI

Environment variables consumed (from .env)
------------------------------------------
  SOURCE_HOST, SOURCE_PORT, SOURCE_DATABASE, SOURCE_SCHEMA,
  SOURCE_USERNAME, SOURCE_PASSWORD
  SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA,
  SNOWFLAKE_USERNAME, SNOWFLAKE_PASSWORD
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

from schema_discovery import ColumnInfo, parse_column_info_from_rows


# ---------------------------------------------------------------------------
# Schema Comparison result
# ---------------------------------------------------------------------------

@dataclass
class ColumnDiff:
    """Represents a type difference between source and target for a single column."""
    column_name: str
    source_type: str
    target_type: str
    is_type_changed: bool
    is_missing_in_target: bool = False
    is_missing_in_source: bool = False

    def __str__(self) -> str:
        if self.is_missing_in_target:
            return f"  [MISSING IN TARGET] {self.column_name} (source: {self.source_type})"
        if self.is_missing_in_source:
            return f"  [MISSING IN SOURCE] {self.column_name} (target: {self.target_type})"
        if self.is_type_changed:
            return f"  [TYPE CHANGED] {self.column_name}: {self.source_type} → {self.target_type}"
        return f"  [OK] {self.column_name}: {self.source_type} → {self.target_type}"


@dataclass
class SchemaComparison:
    """Result of comparing source vs target schemas for a single table."""
    source_table: str
    target_table: str
    source_columns: List[ColumnInfo] = field(default_factory=list)
    target_columns: List[ColumnInfo] = field(default_factory=list)
    diffs: List[ColumnDiff] = field(default_factory=list)
    matched_column_count: int = 0
    missing_in_target: List[str] = field(default_factory=list)
    missing_in_source: List[str] = field(default_factory=list)

    @property
    def type_mismatches(self) -> List[ColumnDiff]:
        return [d for d in self.diffs if d.is_type_changed]

    @property
    def is_schema_compatible(self) -> bool:
        """True if all source columns exist in target (types may differ)."""
        return len(self.missing_in_target) == 0

    def print_summary(self):
        print(f"\n  Schema Comparison: {self.source_table} → {self.target_table}")
        print(f"  Source columns : {len(self.source_columns)}")
        print(f"  Target columns : {len(self.target_columns)}")
        print(f"  Matched        : {self.matched_column_count}")
        print(f"  Missing target : {len(self.missing_in_target)}")
        print(f"  Type changes   : {len(self.type_mismatches)}")
        for d in self.diffs:
            print(str(d))


# ---------------------------------------------------------------------------
# PostgreSQL Schema Extractor
# ---------------------------------------------------------------------------

class PostgresSchemaExtractor:
    """
    Connects to PostgreSQL and extracts column metadata for a given table.
    Uses environment variables for credentials if not explicitly provided.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host or os.getenv("SOURCE_HOST", "localhost")
        self.port = int(port or os.getenv("SOURCE_PORT", "5432"))
        self.database = database or os.getenv("SOURCE_DATABASE", "postgres")
        self.username = username or os.getenv("SOURCE_USERNAME", "postgres")
        self.password = password or os.getenv("SOURCE_PASSWORD", "")

    def extract_columns(self, schema: str, table: str) -> List[ColumnInfo]:
        """
        Connect to PostgreSQL and return full column metadata for schema.table.

        Args:
            schema: PostgreSQL schema name (e.g. 'public', 'source_data')
            table:  Table name (case-insensitive in PostgreSQL)

        Returns:
            List of ColumnInfo ordered by ordinal_position
        """
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            raise ImportError(
                "psycopg2 is required. Install with: pip install psycopg2-binary"
            )

        sql = """
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
            WHERE table_schema = %s
              AND table_name   = %s
            ORDER BY ordinal_position;
        """

        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                connect_timeout=15,
            )
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, (schema, table.lower()))
            rows = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()

            if not rows:
                raise ValueError(
                    f"No columns found for {schema}.{table} in database '{self.database}'. "
                    f"Check schema/table name spelling."
                )

            columns = parse_column_info_from_rows(rows)
            print(f"  ✓ Extracted {len(columns)} columns from PostgreSQL: "
                  f"{self.database}.{schema}.{table}")
            return columns

        except Exception as exc:
            raise RuntimeError(
                f"Failed to extract schema from PostgreSQL "
                f"({self.host}:{self.port}/{self.database}.{schema}.{table}): {exc}"
            ) from exc

    def list_tables(self, schema: str) -> List[str]:
        """List all base tables in the given schema."""
        try:
            import psycopg2
        except ImportError:
            raise ImportError("psycopg2-binary required")

        sql = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """
        conn = psycopg2.connect(
            host=self.host, port=self.port,
            database=self.database,
            user=self.username, password=self.password,
        )
        cursor = conn.cursor()
        cursor.execute(sql, (schema,))
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables


# ---------------------------------------------------------------------------
# Snowflake Schema Extractor
# ---------------------------------------------------------------------------

class SnowflakeSchemaExtractor:
    """
    Connects to Snowflake and extracts column metadata for a given table.
    Uses environment variables for credentials if not explicitly provided.
    """

    def __init__(
        self,
        account: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.account = account or os.getenv("SNOWFLAKE_ACCOUNT", "")
        self.database = database or os.getenv("SNOWFLAKE_DATABASE", "")
        self.default_schema = schema or os.getenv("SNOWFLAKE_SCHEMA", "")
        self.username = username or os.getenv("SNOWFLAKE_USERNAME", "")
        self.password = password or os.getenv("SNOWFLAKE_PASSWORD", "")

    def extract_columns(self, schema: str, table: str) -> List[ColumnInfo]:
        """
        Connect to Snowflake and return full column metadata for schema.table.

        Args:
            schema: Snowflake schema name (e.g. 'TARGET_SCHEMA')
            table:  Table name (Snowflake stores names in UPPER CASE by default)

        Returns:
            List of ColumnInfo ordered by ordinal_position
        """
        try:
            import snowflake.connector
        except ImportError:
            raise ImportError(
                "snowflake-connector-python required. "
                "Install with: pip install snowflake-connector-python"
            )

        sql = f"""
            SELECT
                ORDINAL_POSITION        AS ordinal_position,
                COLUMN_NAME             AS column_name,
                DATA_TYPE               AS data_type,
                CHARACTER_MAXIMUM_LENGTH AS character_maximum_length,
                NUMERIC_PRECISION       AS numeric_precision,
                NUMERIC_SCALE           AS numeric_scale,
                IS_NULLABLE             AS is_nullable,
                COLUMN_DEFAULT          AS column_default
            FROM {self.database}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME   = %s
            ORDER BY ORDINAL_POSITION;
        """

        try:
            conn = snowflake.connector.connect(
                user=self.username,
                password=self.password,
                account=self.account,
                database=self.database,
                schema=schema,
                login_timeout=30,
            )
            cursor = conn.cursor(snowflake.connector.DictCursor)
            cursor.execute(sql, (schema.upper(), table.upper()))
            rows = [{k.lower(): v for k, v in row.items()} for row in cursor.fetchall()]
            cursor.close()
            conn.close()

            if not rows:
                raise ValueError(
                    f"No columns found for {schema}.{table} in Snowflake database "
                    f"'{self.database}'. Check schema/table name spelling."
                )

            columns = parse_column_info_from_rows(rows)
            print(f"  ✓ Extracted {len(columns)} columns from Snowflake: "
                  f"{self.database}.{schema}.{table}")
            return columns

        except Exception as exc:
            raise RuntimeError(
                f"Failed to extract schema from Snowflake "
                f"({self.account}/{self.database}.{schema}.{table}): {exc}"
            ) from exc

    def list_tables(self, schema: str) -> List[str]:
        """List all base tables in the given Snowflake schema."""
        try:
            import snowflake.connector
        except ImportError:
            raise ImportError("snowflake-connector-python required")

        sql = f"""
            SELECT TABLE_NAME FROM {self.database}.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME;
        """
        conn = snowflake.connector.connect(
            user=self.username, password=self.password,
            account=self.account, database=self.database, schema=schema,
        )
        cursor = conn.cursor()
        cursor.execute(sql, (schema.upper(),))
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables


# ---------------------------------------------------------------------------
# Schema Comparator
# ---------------------------------------------------------------------------

class SchemaComparator:
    """
    Compares source (PostgreSQL) and target (Snowflake) schemas side-by-side
    and produces a SchemaComparison report that the AI agent and validator consume.
    """

    @staticmethod
    def compare(
        source_columns: List[ColumnInfo],
        target_columns: List[ColumnInfo],
        source_table: str,
        target_table: str,
    ) -> SchemaComparison:
        """
        Align columns by normalised name and detect type differences.

        Column matching is case-insensitive. Snowflake target names are
        stored in UPPER CASE by convention; PostgreSQL names are lower case.

        Returns:
            SchemaComparison with full diff details
        """
        comparison = SchemaComparison(
            source_table=source_table,
            target_table=target_table,
            source_columns=source_columns,
            target_columns=target_columns,
        )

        # Build lookup: normalised_name -> ColumnInfo
        tgt_map: Dict[str, ColumnInfo] = {
            c.column_name.upper(): c for c in target_columns
        }
        src_map: Dict[str, ColumnInfo] = {
            c.column_name.upper(): c for c in source_columns
        }

        # Check every source column against target
        for src_col in source_columns:
            key = src_col.column_name.upper()
            tgt_col = tgt_map.get(key)

            if tgt_col is None:
                comparison.missing_in_target.append(src_col.column_name)
                comparison.diffs.append(ColumnDiff(
                    column_name=src_col.column_name,
                    source_type=src_col.type_summary(),
                    target_type="—",
                    is_type_changed=False,
                    is_missing_in_target=True,
                ))
            else:
                comparison.matched_column_count += 1
                type_changed = (
                    src_col.data_type.upper() != tgt_col.data_type.upper()
                )
                comparison.diffs.append(ColumnDiff(
                    column_name=src_col.column_name,
                    source_type=src_col.type_summary(),
                    target_type=tgt_col.type_summary(),
                    is_type_changed=type_changed,
                ))

        # Extra columns only in target
        for tgt_col in target_columns:
            key = tgt_col.column_name.upper()
            if key not in src_map:
                comparison.missing_in_source.append(tgt_col.column_name)
                comparison.diffs.append(ColumnDiff(
                    column_name=tgt_col.column_name,
                    source_type="—",
                    target_type=tgt_col.type_summary(),
                    is_type_changed=False,
                    is_missing_in_source=True,
                ))

        return comparison


# ---------------------------------------------------------------------------
# Convenience function — extract both sides in one call
# ---------------------------------------------------------------------------

def extract_and_compare(
    pg_database: str,
    pg_schema: str,
    pg_table: str,
    sf_schema: str,
    sf_table: str,
    sf_database: Optional[str] = None,
) -> Tuple[List[ColumnInfo], List[ColumnInfo], SchemaComparison]:
    """
    High-level convenience function:
    1. Connect to PostgreSQL → extract source schema
    2. Connect to Snowflake  → extract target schema
    3. Compare and return both column lists plus a SchemaComparison

    All credentials come from environment variables (.env file).

    Args:
        pg_database : PostgreSQL database name
        pg_schema   : PostgreSQL schema name
        pg_table    : Source table name
        sf_schema   : Snowflake schema name
        sf_table    : Target table name (usually UPPER CASE)
        sf_database : Snowflake database override (defaults to SNOWFLAKE_DATABASE env var)

    Returns:
        (source_columns, target_columns, comparison)
    """
    print("\n  [Schema Extractor] Extracting source schema from PostgreSQL...")
    pg_extractor = PostgresSchemaExtractor(database=pg_database)
    source_cols = pg_extractor.extract_columns(pg_schema, pg_table)

    print("  [Schema Extractor] Extracting target schema from Snowflake...")
    sf_extractor = SnowflakeSchemaExtractor(database=sf_database)
    target_cols = sf_extractor.extract_columns(sf_schema, sf_table)

    comparison = SchemaComparator.compare(
        source_columns=source_cols,
        target_columns=target_cols,
        source_table=f"{pg_schema}.{pg_table}",
        target_table=f"{sf_schema}.{sf_table}",
    )

    return source_cols, target_cols, comparison
