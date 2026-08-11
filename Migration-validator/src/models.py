"""
Data Models for Migration Validator
=====================================
Clean, minimal models used across the entire pipeline.
No static table/column definitions — everything is resolved at runtime
from live database connections.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DatabaseType(Enum):
    """Supported database types."""
    MSSQL      = "MSSQL"
    POSTGRESQL = "PostgreSQL"
    SNOWFLAKE  = "Snowflake"


class TransformationRuleType(Enum):
    """
    All supported transformation rules.
    Values match the enum_value field in rules_catalog.json exactly (lowercase).
    """
    BOOLEAN_CONVERSION  = "boolean_conversion"
    NULL_STANDARDIZATION= "null_standardization"
    WHITESPACE_TRIM     = "whitespace_trim"
    CASE_INSENSITIVE    = "case_insensitive"
    DATE_STANDARDIZATION= "date_standardization"
    NUMERIC_PRECISION   = "numeric_precision"
    EMPTY_STRING_NULL   = "empty_string_null"
    INTEGER_CAST        = "integer_cast"
    TIMESTAMP_TO_DATE   = "timestamp_to_date"
    UUID_TO_VARCHAR     = "uuid_to_varchar"
    JSON_SKIP           = "json_skip"
    ARRAY_SKIP          = "array_skip"
    BYTEA_SKIP          = "bytea_skip"
    TEXT_TO_NUMBER      = "text_to_number"


# ---------------------------------------------------------------------------
# Connection configuration
# ---------------------------------------------------------------------------

@dataclass
class DatabaseConfig:
    """Database connection configuration (credentials only — no table definitions)."""
    database_type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password: str
    schema: Optional[str] = None
    timeout: int = 30

    def __repr__(self) -> str:
        return (
            f"{self.database_type.value}://{self.username}@"
            f"{self.host}:{self.port}/{self.database}"
        )


# ---------------------------------------------------------------------------
# Column mapping — produced entirely by AI from live schema
# ---------------------------------------------------------------------------

@dataclass
class ColumnMapping:
    """
    Describes how one source column maps to one target column.

    Created exclusively by the AIQueryAgent from live-extracted metadata.
    Never hard-coded manually.

    Fields
    ------
    source_column      : Column name in PostgreSQL (original case)
    target_column      : Column name in Snowflake (may differ from source — AI resolves this)
    source_data_type   : PostgreSQL data type string (e.g. 'integer', 'character varying')
    target_data_type   : Snowflake data type string  (e.g. 'NUMBER', 'TEXT')
    apply_rules        : Ordered list of transformation rules to apply
    primary_key        : True if this column is (part of) the primary key
    ignore_validation  : True for un-comparable types (JSON, ARRAY, BYTEA)
    name_mismatch      : True when source and target column names differ
    ai_match_reason    : Human-readable reason why AI matched differently-named columns
    """
    source_column: str
    target_column: str
    source_data_type: str
    target_data_type: str
    apply_rules: List[TransformationRuleType] = field(default_factory=list)
    primary_key: bool = False
    ignore_validation: bool = False
    name_mismatch: bool = False
    ai_match_reason: str = ""

    def __repr__(self) -> str:
        alias = f" [alias: {self.source_column}→{self.target_column}]" if self.name_mismatch else ""
        return (
            f"{self.source_column}({self.source_data_type})"
            f" → {self.target_column}({self.target_data_type})"
            f"{alias}"
        )


# ---------------------------------------------------------------------------
# Validation results
# ---------------------------------------------------------------------------

@dataclass
class ColumnValidationResult:
    """Validation result for a single column pair."""
    column_name: str
    source_count: int
    target_count: int
    matched_count: int
    unmatched_count: int
    status: str                                          # PASS | FAIL | WARN | SKIP
    applied_rules: List[TransformationRuleType] = field(default_factory=list)
    error_message: Optional[str] = None
    name_mismatch: bool = False
    target_column_name: str = ""


@dataclass
class TableValidationResult:
    """Validation result for a full table."""
    table_name: str
    source_rows: int
    target_rows: int
    matched_rows: int
    unmatched_rows: int
    column_results: List[ColumnValidationResult] = field(default_factory=list)
    overall_status: str = "PENDING"                      # PASS | FAIL | PARTIAL | ERROR
    error_message: Optional[str] = None

    @property
    def row_count_match(self) -> bool:
        return self.source_rows == self.target_rows

    @property
    def data_completeness_percentage(self) -> float:
        if self.source_rows == 0:
            return 100.0
        return (self.matched_rows / self.source_rows) * 100


@dataclass
class ValidationReport:
    """Top-level validation report — persisted to JSON/HTML/TXT."""
    validation_id: str
    timestamp: datetime
    source_database: str
    target_database: str
    table_results: List[TableValidationResult] = field(default_factory=list)
    total_tables: int = 0
    passed_tables: int = 0
    failed_tables: int = 0
    error_tables: int = 0
    total_source_rows: int = 0
    total_target_rows: int = 0
    total_matched_rows: int = 0
    overall_status: str = "PENDING"
    notes: Optional[str] = None

    @property
    def overall_data_completeness(self) -> float:
        if self.total_source_rows == 0:
            return 100.0
        return (self.total_matched_rows / self.total_source_rows) * 100

    @property
    def success_rate(self) -> float:
        if self.total_tables == 0:
            return 0.0
        return (self.passed_tables / self.total_tables) * 100


# ---------------------------------------------------------------------------
# Query execution result
# ---------------------------------------------------------------------------

@dataclass
class QueryResult:
    """Result from executing a SQL query against any database."""
    query: str
    row_count: int
    rows: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_ms: float = 0.0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


# ---------------------------------------------------------------------------
# Rule config (used by transformation_rules engine)
# ---------------------------------------------------------------------------

@dataclass
class TransformationRuleConfig:
    """Runtime configuration for a transformation rule."""
    rule_type: TransformationRuleType
    source_data_type: str
    target_data_type: str
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    sql_function: Optional[str] = None
