"""
Transformation Rules Engine
============================
Defines SQL expression builders for every transformation rule in rules_catalog.json.

Design
------
- Each rule class implements `get_inner_expression(expr, db_type)` — returns a
  SQL fragment that WRAPS the given expression (no alias).
- The engine's `apply_rules()` chains multiple rules in canonical order and
  appends a single `AS {alias}_normalized` at the very end.
- The `build_select_expr()` helper is the main entry point used by the AI
  SQL builder — it takes a ColumnMapping and produces a complete SELECT clause
  for one column on one database side.

Adding a new rule
-----------------
1. Add a class that extends TransformationRule and override get_inner_expression().
2. Register it in TransformationRulesEngine.__init__().
3. Add it to rules_catalog.json with the matching enum_value.
4. Add the enum value to TransformationRuleType in models.py.
"""

from typing import Dict, List, Optional
from models import TransformationRuleType, DatabaseType


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class TransformationRule:
    """Base class for all transformation rules."""

    def __init__(self, rule_type: TransformationRuleType):
        self.rule_type = rule_type

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        """
        Wrap `expr` with this rule's SQL logic.
        Must NOT include a trailing alias — that is added by apply_rules().

        Args:
            expr    : Input SQL expression (column name or already-chained expression)
            db_type : Target database dialect

        Returns:
            SQL expression string (no alias)
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Individual rules
# ---------------------------------------------------------------------------

class BooleanConversionRule(TransformationRule):
    """
    Converts boolean-like values to canonical 'TRUE' / 'FALSE' strings.
    Handles:
      PostgreSQL BOOLEAN  → true / false / NULL
      MSSQL BIT           → 1 / 0 / NULL
      Snowflake BOOLEAN   → TRUE / FALSE / NULL
    All produce identical 'TRUE' / 'FALSE' strings after normalisation.
    """
    def __init__(self):
        super().__init__(TransformationRuleType.BOOLEAN_CONVERSION)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        if db_type == DatabaseType.MSSQL:
            return f"CASE WHEN {expr} = 1 THEN 'TRUE' WHEN {expr} = 0 THEN 'FALSE' ELSE 'NULL' END"
        elif db_type == DatabaseType.POSTGRESQL:
            return f"CASE WHEN {expr} = true THEN 'TRUE' WHEN {expr} = false THEN 'FALSE' ELSE 'NULL' END"
        else:  # Snowflake
            return f"CASE WHEN {expr} = TRUE THEN 'TRUE' WHEN {expr} = FALSE THEN 'FALSE' ELSE 'NULL' END"


class NullStandardizationRule(TransformationRule):
    """
    Wraps expression in COALESCE so SQL NULL → '<NULL>' sentinel.
    Always the OUTERMOST (last applied) rule in any chain.
    Casts to text first so type mismatches inside COALESCE are avoided.
    """
    def __init__(self):
        super().__init__(TransformationRuleType.NULL_STANDARDIZATION)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        if db_type == DatabaseType.MSSQL:
            return f"COALESCE(CAST({expr} AS VARCHAR(MAX)), '<NULL>')"
        elif db_type == DatabaseType.POSTGRESQL:
            return f"COALESCE(CAST({expr} AS TEXT), '<NULL>')"
        else:  # Snowflake
            return f"COALESCE(CAST({expr} AS STRING), '<NULL>')"


class WhitespaceTrimRule(TransformationRule):
    """Strips leading/trailing whitespace from string columns."""
    def __init__(self):
        super().__init__(TransformationRuleType.WHITESPACE_TRIM)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        if db_type == DatabaseType.MSSQL:
            return f"LTRIM(RTRIM({expr}))"
        return f"TRIM({expr})"


class CaseInsensitiveRule(TransformationRule):
    """Lowercases strings for case-insensitive comparison."""
    def __init__(self):
        super().__init__(TransformationRuleType.CASE_INSENSITIVE)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        return f"LOWER({expr})"


class DateStandardizationRule(TransformationRule):
    """Formats date/timestamp as 'YYYY-MM-DD' for uniform comparison."""
    def __init__(self):
        super().__init__(TransformationRuleType.DATE_STANDARDIZATION)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        if db_type == DatabaseType.MSSQL:
            return f"CONVERT(VARCHAR(10), {expr}, 23)"
        elif db_type == DatabaseType.POSTGRESQL:
            return f"TO_CHAR({expr}, 'YYYY-MM-DD')"
        else:  # Snowflake
            return f"TO_VARCHAR({expr}, 'YYYY-MM-DD')"


class NumericPrecisionRule(TransformationRule):
    """Rounds numeric columns to 2 decimal places to absorb precision noise."""
    def __init__(self, decimal_places: int = 2):
        super().__init__(TransformationRuleType.NUMERIC_PRECISION)
        self.decimal_places = decimal_places

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        dp = self.decimal_places
        if db_type == DatabaseType.POSTGRESQL:
            return f"ROUND(CAST({expr} AS NUMERIC), {dp})"
        elif db_type == DatabaseType.SNOWFLAKE:
            return f"ROUND(CAST({expr} AS NUMBER(38,{dp})), {dp})"
        return f"ROUND(CAST({expr} AS DECIMAL(18,{dp})), {dp})"


class EmptyStringNullRule(TransformationRule):
    """Treats empty string '' as NULL — must run BEFORE NULL_STANDARDIZATION."""
    def __init__(self):
        super().__init__(TransformationRuleType.EMPTY_STRING_NULL)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        return f"NULLIF({expr}, '')"


class IntegerCastRule(TransformationRule):
    """Casts INT/BIGINT/SERIAL to canonical integer type for cross-dialect comparison."""
    def __init__(self):
        super().__init__(TransformationRuleType.INTEGER_CAST)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        if db_type == DatabaseType.SNOWFLAKE:
            return f"CAST({expr} AS NUMBER)"
        return f"CAST({expr} AS BIGINT)"


class TimestampToDateRule(TransformationRule):
    """Truncates timestamp to DATE when target stores only DATE."""
    def __init__(self):
        super().__init__(TransformationRuleType.TIMESTAMP_TO_DATE)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        if db_type == DatabaseType.MSSQL:
            return f"CONVERT(DATE, {expr})"
        return f"DATE_TRUNC('day', {expr})::DATE"


class UuidToVarcharRule(TransformationRule):
    """
    Normalises UUID to lowercase text.
    PostgreSQL UUID native type → Snowflake VARCHAR.
    Always lowercase both sides — ETL tools may uppercase UUIDs.
    """
    def __init__(self):
        super().__init__(TransformationRuleType.UUID_TO_VARCHAR)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        if db_type == DatabaseType.POSTGRESQL:
            return f"LOWER(CAST({expr} AS TEXT))"
        else:  # Snowflake
            return f"LOWER(CAST({expr} AS STRING))"


class TextToNumberRule(TransformationRule):
    """
    Casts text/varchar that stores numeric values to NUMBER.
    Uses TRY_CAST on Snowflake side to avoid failures on bad data.
    Only apply when the AI explicitly determines the column holds numeric text.
    """
    def __init__(self):
        super().__init__(TransformationRuleType.TEXT_TO_NUMBER)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        if db_type == DatabaseType.POSTGRESQL:
            return f"CAST(NULLIF(TRIM({expr}), '') AS NUMERIC)"
        elif db_type == DatabaseType.SNOWFLAKE:
            return f"TRY_CAST(TRIM({expr}) AS NUMBER)"
        return f"CAST(NULLIF(TRIM({expr}), '') AS DECIMAL(18,4))"


# ---------------------------------------------------------------------------
# Skip-marker stubs (no SQL generated — set ignore_validation only)
# ---------------------------------------------------------------------------

class JsonSkipRule(TransformationRule):
    def __init__(self):
        super().__init__(TransformationRuleType.JSON_SKIP)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        return expr  # Never called; column is ignored


class ArraySkipRule(TransformationRule):
    def __init__(self):
        super().__init__(TransformationRuleType.ARRAY_SKIP)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        return expr


class ByteaSkipRule(TransformationRule):
    def __init__(self):
        super().__init__(TransformationRuleType.BYTEA_SKIP)

    def get_inner_expression(self, expr: str, db_type: DatabaseType) -> str:
        return expr


# ---------------------------------------------------------------------------
# Rules Engine
# ---------------------------------------------------------------------------

# Skip rules — these mark a column as non-comparable; no SQL is generated.
_SKIP_RULES = {
    TransformationRuleType.JSON_SKIP,
    TransformationRuleType.ARRAY_SKIP,
    TransformationRuleType.BYTEA_SKIP,
}

# Canonical chaining order: type-cast → value-normalise → string-normalise → NULL last
_CHAIN_ORDER = [
    TransformationRuleType.INTEGER_CAST,
    TransformationRuleType.UUID_TO_VARCHAR,
    TransformationRuleType.BOOLEAN_CONVERSION,
    TransformationRuleType.TIMESTAMP_TO_DATE,
    TransformationRuleType.DATE_STANDARDIZATION,
    TransformationRuleType.NUMERIC_PRECISION,
    TransformationRuleType.TEXT_TO_NUMBER,
    TransformationRuleType.EMPTY_STRING_NULL,
    TransformationRuleType.WHITESPACE_TRIM,
    TransformationRuleType.CASE_INSENSITIVE,
    TransformationRuleType.NULL_STANDARDIZATION,
]


class TransformationRulesEngine:
    """
    Applies transformation rules to produce normalised SQL SELECT expressions.

    Usage
    -----
    from transformation_rules import rules_engine
    from models import TransformationRuleType, DatabaseType

    expr = rules_engine.apply_rules(
        column_name="is_active",
        rules=[TransformationRuleType.BOOLEAN_CONVERSION,
               TransformationRuleType.NULL_STANDARDIZATION],
        db_type=DatabaseType.POSTGRESQL,
        alias="is_active_normalized",
    )
    # → "COALESCE(CAST(CASE WHEN is_active = true THEN 'TRUE' ... END AS TEXT), '<NULL>') AS is_active_normalized"
    """

    def __init__(self):
        self._rules: Dict[TransformationRuleType, TransformationRule] = {
            TransformationRuleType.BOOLEAN_CONVERSION:   BooleanConversionRule(),
            TransformationRuleType.NULL_STANDARDIZATION: NullStandardizationRule(),
            TransformationRuleType.WHITESPACE_TRIM:      WhitespaceTrimRule(),
            TransformationRuleType.CASE_INSENSITIVE:     CaseInsensitiveRule(),
            TransformationRuleType.DATE_STANDARDIZATION: DateStandardizationRule(),
            TransformationRuleType.NUMERIC_PRECISION:    NumericPrecisionRule(),
            TransformationRuleType.EMPTY_STRING_NULL:    EmptyStringNullRule(),
            TransformationRuleType.INTEGER_CAST:         IntegerCastRule(),
            TransformationRuleType.TIMESTAMP_TO_DATE:    TimestampToDateRule(),
            TransformationRuleType.UUID_TO_VARCHAR:      UuidToVarcharRule(),
            TransformationRuleType.TEXT_TO_NUMBER:       TextToNumberRule(),
            TransformationRuleType.JSON_SKIP:            JsonSkipRule(),
            TransformationRuleType.ARRAY_SKIP:           ArraySkipRule(),
            TransformationRuleType.BYTEA_SKIP:           ByteaSkipRule(),
        }

    def apply_rules(
        self,
        column_name: str,
        rules: List[TransformationRuleType],
        db_type: DatabaseType,
        alias: Optional[str] = None,
    ) -> str:
        """
        Chain all applicable rules in canonical order and return a full
        SELECT expression with a trailing AS alias.

        Args:
            column_name : Bare SQL column reference (may be quoted)
            rules       : List of rule types to apply (AI-selected)
            db_type     : Database dialect for SQL generation
            alias       : Output alias; defaults to '{column_name}_normalized'

        Returns:
            Complete SQL expression, e.g.:
            COALESCE(LOWER(TRIM(email)), '<NULL>') AS email_normalized
        """
        out_alias = alias or f"{column_name}_normalized"

        # Filter out skip-marker rules (they never produce SQL)
        active_rules = [r for r in rules if r not in _SKIP_RULES]

        if not active_rules:
            return f"{column_name} AS {out_alias}"

        # Sort by canonical chaining order; unknown rules appended last
        ordered = sorted(
            active_rules,
            key=lambda r: _CHAIN_ORDER.index(r) if r in _CHAIN_ORDER else len(_CHAIN_ORDER),
        )

        current_expr = column_name
        for rule_type in ordered:
            rule = self._rules.get(rule_type)
            if rule:
                current_expr = rule.get_inner_expression(current_expr, db_type)

        return f"{current_expr} AS {out_alias}"

    def build_select_expr(
        self,
        column_ref: str,
        rules: List[TransformationRuleType],
        db_type: DatabaseType,
        normalized_alias: str,
    ) -> str:
        """
        Convenience wrapper used by the SQL builder.

        Args:
            column_ref       : The column reference as it appears in SQL
                               (e.g. 'customer_id' or '"CustomerID"')
            rules            : Transformation rules assigned by AI
            db_type          : Database dialect
            normalized_alias : The alias for the output column
                               (always '<source_col>_normalized' for cross-name consistency)

        Returns:
            Complete SELECT expression string
        """
        return self.apply_rules(column_ref, rules, db_type, alias=normalized_alias)

    def get_rule(self, rule_type: TransformationRuleType) -> Optional[TransformationRule]:
        return self._rules.get(rule_type)

    def is_skip_rule(self, rule_type: TransformationRuleType) -> bool:
        return rule_type in _SKIP_RULES

    def get_chain_order(self) -> List[TransformationRuleType]:
        return list(_CHAIN_ORDER)

    def describe_all_rules(self) -> Dict[TransformationRuleType, str]:
        return {
            TransformationRuleType.BOOLEAN_CONVERSION:   "BIT/BOOLEAN → 'TRUE'/'FALSE' string",
            TransformationRuleType.NULL_STANDARDIZATION: "NULL → '<NULL>' sentinel (outermost)",
            TransformationRuleType.WHITESPACE_TRIM:      "Strip leading/trailing whitespace",
            TransformationRuleType.CASE_INSENSITIVE:     "Lowercase for case-insensitive compare",
            TransformationRuleType.DATE_STANDARDIZATION: "Format date/timestamp as YYYY-MM-DD",
            TransformationRuleType.NUMERIC_PRECISION:    "Round to 2 decimal places",
            TransformationRuleType.EMPTY_STRING_NULL:    "Empty string '' → NULL",
            TransformationRuleType.INTEGER_CAST:         "Cast INT/SERIAL → NUMBER/BIGINT",
            TransformationRuleType.TIMESTAMP_TO_DATE:    "Truncate TIMESTAMP → DATE",
            TransformationRuleType.UUID_TO_VARCHAR:      "UUID → lowercase VARCHAR text",
            TransformationRuleType.TEXT_TO_NUMBER:       "Text holding numbers → NUMERIC",
            TransformationRuleType.JSON_SKIP:            "[SKIP] JSON/JSONB — manual review",
            TransformationRuleType.ARRAY_SKIP:           "[SKIP] ARRAY/HSTORE — manual review",
            TransformationRuleType.BYTEA_SKIP:           "[SKIP] BYTEA/BINARY — manual review",
        }


# ---------------------------------------------------------------------------
# Singleton instance — import and use directly
# ---------------------------------------------------------------------------
rules_engine = TransformationRulesEngine()
