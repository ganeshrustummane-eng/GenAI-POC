"""
SQL Extractor Package
======================
Live schema extraction from PostgreSQL (source) and Snowflake (target).

This module connects directly to databases and extracts column-level
metadata needed to generate validation SQL queries. No static schema
definitions — everything is discovered at runtime.

Modules:
  base_extractor      — Abstract interface all extractors implement
  postgres_extractor  — Connects to PostgreSQL via psycopg2
  snowflake_extractor — Connects to Snowflake via snowflake-connector-python

Usage:
    from sql_extractor import PostgresExtractor, SnowflakeExtractor

    pg = PostgresExtractor()
    columns = pg.extract_columns(schema="public", table="events")

    sf = SnowflakeExtractor()
    sf_columns = sf.extract_columns(schema="STOREDGE_FMS_PUBLIC", table="EVENTS")
"""

from sql_extractor.base_extractor import (
    BaseExtractor,
    ColumnMetadata,
    TableMetadata,
    ExtractionError,
)
from sql_extractor.postgres_extractor import PostgresExtractor
from sql_extractor.snowflake_extractor import SnowflakeExtractor

__all__ = [
    "BaseExtractor",
    "ColumnMetadata",
    "TableMetadata",
    "ExtractionError",
    "PostgresExtractor",
    "SnowflakeExtractor",
]
