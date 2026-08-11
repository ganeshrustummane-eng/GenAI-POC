"""
Tests for SchemaProfiler
=========================
Verifies that columns are classified into the correct semantic groups
based on column name + data type combinations.

Run:
    cd src
    python -m pytest tests/test_schema_profiler.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_extractor.base_extractor import ColumnMetadata
from profiling.schema_profiler import SchemaProfiler, ColumnGroup, TableProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def col(name: str, dtype: str, nullable: bool = True,
        precision: int = None, scale: int = None) -> ColumnMetadata:
    return ColumnMetadata(
        ordinal_position=1,
        column_name=name,
        data_type=dtype,
        is_nullable=nullable,
        numeric_precision=precision,
        numeric_scale=scale,
    )


PROFILER = SchemaProfiler()


def profile_cols(*columns: ColumnMetadata) -> TableProfile:
    return PROFILER.profile(list(columns), schema="public", table="test_table")


# ---------------------------------------------------------------------------
# NUMERIC_FINANCIAL
# ---------------------------------------------------------------------------

class TestFinancialColumns:
    def test_amount_numeric(self):
        p = profile_cols(col("amount", "numeric", scale=2))
        assert p.column_profiles[0].group == ColumnGroup.NUMERIC_FINANCIAL

    def test_balance_decimal(self):
        p = profile_cols(col("balance", "decimal", scale=4))
        assert p.column_profiles[0].group == ColumnGroup.NUMERIC_FINANCIAL

    def test_price_float(self):
        p = profile_cols(col("price", "double precision"))
        assert p.column_profiles[0].group == ColumnGroup.NUMERIC_FINANCIAL

    def test_salary_integer(self):
        # salary is an integer but name keyword overrides
        p = profile_cols(col("salary", "integer"))
        assert p.column_profiles[0].group == ColumnGroup.NUMERIC_FINANCIAL

    def test_transaction_amount_compound_name(self):
        p = profile_cols(col("transaction_amount", "numeric"))
        assert p.column_profiles[0].group == ColumnGroup.NUMERIC_FINANCIAL

    def test_non_financial_integer(self):
        # 'count' is quantity, not financial
        p = profile_cols(col("count", "integer"))
        assert p.column_profiles[0].group != ColumnGroup.NUMERIC_FINANCIAL


# ---------------------------------------------------------------------------
# NUMERIC_QUANTITY
# ---------------------------------------------------------------------------

class TestQuantityColumns:
    def test_quantity(self):
        p = profile_cols(col("quantity", "integer"))
        assert p.column_profiles[0].group == ColumnGroup.NUMERIC_QUANTITY

    def test_qty(self):
        p = profile_cols(col("qty", "smallint"))
        assert p.column_profiles[0].group == ColumnGroup.NUMERIC_QUANTITY

    def test_units_in_stock(self):
        p = profile_cols(col("units_in_stock", "integer"))
        assert p.column_profiles[0].group == ColumnGroup.NUMERIC_QUANTITY

    def test_item_count(self):
        p = profile_cols(col("item_count", "bigint"))
        assert p.column_profiles[0].group == ColumnGroup.NUMERIC_QUANTITY


# ---------------------------------------------------------------------------
# IDENTIFIER
# ---------------------------------------------------------------------------

class TestIdentifierColumns:
    def test_id_column(self):
        p = profile_cols(col("id", "integer", nullable=False))
        assert p.column_profiles[0].group == ColumnGroup.IDENTIFIER

    def test_customer_id(self):
        p = profile_cols(col("customer_id", "bigint", nullable=False))
        assert p.column_profiles[0].group == ColumnGroup.IDENTIFIER

    def test_uuid_type(self):
        p = profile_cols(col("external_ref", "uuid"))
        assert p.column_profiles[0].group == ColumnGroup.IDENTIFIER

    def test_not_null_identifier_is_business_key(self):
        p = profile_cols(col("transaction_id", "integer", nullable=False))
        assert p.column_profiles[0].business_key is True

    def test_nullable_identifier_not_business_key(self):
        p = profile_cols(col("optional_id", "integer", nullable=True))
        assert p.column_profiles[0].business_key is False


# ---------------------------------------------------------------------------
# TEMPORAL
# ---------------------------------------------------------------------------

class TestTemporalColumns:
    def test_date_type(self):
        p = profile_cols(col("created_date", "date"))
        assert p.column_profiles[0].group == ColumnGroup.TEMPORAL

    def test_timestamp_ntz(self):
        p = profile_cols(col("updated_at", "timestamp without time zone"))
        assert p.column_profiles[0].group == ColumnGroup.TEMPORAL

    def test_timestamp_tz(self):
        p = profile_cols(col("event_time", "timestamp with time zone"))
        assert p.column_profiles[0].group == ColumnGroup.TEMPORAL

    def test_timestamptz_alias(self):
        p = profile_cols(col("logged_at", "timestamptz"))
        assert p.column_profiles[0].group == ColumnGroup.TEMPORAL


# ---------------------------------------------------------------------------
# STATUS_FLAG
# ---------------------------------------------------------------------------

class TestStatusFlagColumns:
    def test_boolean_type(self):
        p = profile_cols(col("is_active", "boolean"))
        assert p.column_profiles[0].group == ColumnGroup.STATUS_FLAG

    def test_is_prefix(self):
        p = profile_cols(col("is_deleted", "integer"))
        assert p.column_profiles[0].group == ColumnGroup.STATUS_FLAG

    def test_has_prefix(self):
        p = profile_cols(col("has_children", "boolean"))
        assert p.column_profiles[0].group == ColumnGroup.STATUS_FLAG

    def test_active_name(self):
        p = profile_cols(col("active", "boolean"))
        assert p.column_profiles[0].group == ColumnGroup.STATUS_FLAG


# ---------------------------------------------------------------------------
# TEXT_ENUM
# ---------------------------------------------------------------------------

class TestTextEnumColumns:
    def test_status_varchar(self):
        p = profile_cols(col("status", "character varying"))
        assert p.column_profiles[0].group == ColumnGroup.TEXT_ENUM

    def test_account_type(self):
        p = profile_cols(col("account_type", "text"))
        assert p.column_profiles[0].group == ColumnGroup.TEXT_ENUM

    def test_order_state(self):
        p = profile_cols(col("order_state", "character varying"))
        assert p.column_profiles[0].group == ColumnGroup.TEXT_ENUM


# ---------------------------------------------------------------------------
# SKIPPED
# ---------------------------------------------------------------------------

class TestSkippedColumns:
    def test_json_skipped(self):
        p = profile_cols(col("metadata", "json"))
        assert p.column_profiles[0].group == ColumnGroup.SKIPPED

    def test_jsonb_skipped(self):
        p = profile_cols(col("payload", "jsonb"))
        assert p.column_profiles[0].group == ColumnGroup.SKIPPED

    def test_bytea_skipped(self):
        p = profile_cols(col("binary_data", "bytea"))
        assert p.column_profiles[0].group == ColumnGroup.SKIPPED

    def test_array_skipped(self):
        p = profile_cols(col("tags", "array"))
        assert p.column_profiles[0].group == ColumnGroup.SKIPPED


# ---------------------------------------------------------------------------
# TableProfile aggregate properties
# ---------------------------------------------------------------------------

class TestTableProfile:
    def _orders_table(self) -> TableProfile:
        return profile_cols(
            col("order_id",    "integer",          nullable=False),
            col("customer_id", "bigint",            nullable=False),
            col("amount",      "numeric",           scale=2),
            col("quantity",    "integer"),
            col("status",      "character varying"),
            col("created_at",  "timestamp without time zone"),
            col("is_active",   "boolean"),
            col("metadata",    "jsonb"),
        )

    def test_has_financial(self):
        assert self._orders_table().has_financial

    def test_has_temporal(self):
        assert self._orders_table().has_temporal

    def test_has_identifiers(self):
        assert self._orders_table().has_identifiers

    def test_has_enums(self):
        assert self._orders_table().has_enums

    def test_business_keys_detected(self):
        p = self._orders_table()
        bk_names = [c.column_name for c in p.business_keys]
        assert "order_id" in bk_names or "customer_id" in bk_names

    def test_skipped_columns_detected(self):
        p = self._orders_table()
        assert len(p.skipped_columns) == 1
        assert p.skipped_columns[0].column_name == "metadata"

    def test_numeric_columns_includes_all_numeric_groups(self):
        p = self._orders_table()
        numeric_names = [c.column_name for c in p.numeric_columns]
        # amount (financial) and quantity (quantity) both in numeric_columns
        assert "amount" in numeric_names
        assert "quantity" in numeric_names


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
