"""
Base Extractor — Abstract Schema Extraction Interface
======================================================
Defines the common data structures and abstract interface that all
database-specific extractors must implement.

Data Structures:
  ColumnMetadata  — Single column description (name, type, nullability, position)
  TableMetadata   — Table description with all columns
  ExtractionError — Raised when schema extraction fails
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class ColumnMetadata:
    """
    Metadata for a single database column.

    Attributes:
        ordinal_position  : Column position in the table (1-based)
        column_name       : Original column name as stored in the DB
        data_type         : Raw data type string (e.g. 'character varying', 'TIMESTAMP_NTZ')
        is_nullable       : True if column allows NULL values
        char_max_length   : Max character length for VARCHAR/CHAR types (None if not applicable)
        numeric_precision : Numeric precision for NUMERIC/DECIMAL types
        numeric_scale     : Numeric scale (decimal places) for NUMERIC/DECIMAL types
        column_default    : Default value expression (None if no default)

    Computed (auto-populated, never stored):
        normalized_name   : column_name normalized for matching (lowercase, no separators)
                            e.g. 'created_at' → 'createdat', 'CREATEDAT' → 'createdat'
                            NEVER use this as a SQL identifier — use column_name.
    """
    ordinal_position: int
    column_name: str
    data_type: str
    is_nullable: bool = True
    char_max_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    column_default: Optional[str] = None

    @property
    def normalized_name(self) -> str:
        """
        Normalized column name for matching — lowercase, alphanumeric only.
        NEVER use this as a SQL identifier. Always use column_name for SQL.
        """
        import re
        return re.sub(r"[^a-z0-9]", "", self.column_name.lower())

    @property
    def type_summary(self) -> str:
        """
        Returns a human-readable type string with precision/scale info.
        Example: 'NUMERIC(10,2)', 'VARCHAR(255)', 'TIMESTAMP_NTZ'
        """
        dtype = self.data_type.upper()
        if self.char_max_length:
            return f"{dtype}({self.char_max_length})"
        if self.numeric_precision and self.numeric_scale is not None:
            return f"{dtype}({self.numeric_precision},{self.numeric_scale})"
        if self.numeric_precision:
            return f"{dtype}({self.numeric_precision})"
        return dtype

    @property
    def normalized_type(self) -> str:
        """
        Returns the base type without precision/scale for rule matching.
        Example: 'CHARACTER VARYING(100)' → 'CHARACTER VARYING'
        """
        import re
        return re.sub(r"\s*\([^)]*\)", "", self.data_type).strip().upper()

    def __repr__(self) -> str:
        null_str = "NULL" if self.is_nullable else "NOT NULL"
        return f"Column({self.column_name}: {self.type_summary} {null_str})"


@dataclass
class TableMetadata:
    """
    Metadata for a database table, including all its columns.

    Attributes:
        database   : Database name
        schema     : Schema name
        table_name : Table name
        columns    : List of ColumnMetadata ordered by ordinal_position
    """
    database: str
    schema: str
    table_name: str
    columns: List[ColumnMetadata] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        """Returns fully qualified table name: database.schema.table"""
        return f"{self.database}.{self.schema}.{self.table_name}"

    @property
    def column_names(self) -> List[str]:
        """Returns list of all column names in ordinal order."""
        return [c.column_name for c in self.columns]

    def get_column(self, name: str) -> Optional[ColumnMetadata]:
        """Look up a column by name (case-insensitive)."""
        name_upper = name.upper()
        for col in self.columns:
            if col.column_name.upper() == name_upper:
                return col
        return None

    def __repr__(self) -> str:
        return f"Table({self.full_name}, {len(self.columns)} columns)"


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class ExtractionError(Exception):
    """
    Raised when schema extraction fails.
    Wraps the original exception with context information.
    """
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


# ---------------------------------------------------------------------------
# Abstract Base Extractor
# ---------------------------------------------------------------------------

class BaseExtractor(ABC):
    """
    Abstract interface for database schema extractors.

    All extractors must implement:
        extract_columns() — fetch columns for a specific table
        list_tables()     — list all tables in a schema
    """

    @abstractmethod
    def extract_columns(self, schema: str, table: str) -> List[ColumnMetadata]:
        """
        Connect to the database and extract column metadata for schema.table.

        Args:
            schema : Schema name (e.g. 'public', 'STOREDGE_FMS_PUBLIC')
            table  : Table name

        Returns:
            List of ColumnMetadata ordered by ordinal_position.

        Raises:
            ExtractionError: If connection fails or table not found.
        """

    @abstractmethod
    def list_tables(self, schema: str) -> List[str]:
        """
        List all base tables in the given schema.

        Args:
            schema : Schema name

        Returns:
            List of table names in the schema.

        Raises:
            ExtractionError: If connection fails.
        """

    def extract_table(self, schema: str, table: str, database: str = "") -> TableMetadata:
        """
        Convenience method: extract columns and return as TableMetadata.

        Args:
            schema   : Schema name
            table    : Table name
            database : Database name (for display/YAML; not used for connection)

        Returns:
            TableMetadata with all columns populated.
        """
        columns = self.extract_columns(schema, table)
        return TableMetadata(
            database=database,
            schema=schema,
            table_name=table,
            columns=columns,
        )
