"""
PostgreSQL → Snowflake Transformation Rules
============================================
All type-specific rules for normalizing PostgreSQL (and MSSQL/Athena — their
extractors already map types to PG-compatible names) column values before
comparing them with Snowflake.

Rule application order (innermost → outermost):
  1. integer / uuid / json / bytea / hstore
  2. boolean
  3. timestamp_tz → timestamp_ntz → date
  4. numeric
  5. text (trim) / fallback
  6. null placeholder  ← always LAST (outermost, inherited by base class)
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ── NULL placeholder ─────────────────────────────────────────────────────────
NULL_PLACEHOLDER = "<<NULL>>"


# ── Abstract base ─────────────────────────────────────────────────────────────

class BaseValidationRule(ABC):
    """Abstract base for all validation rules. Subclasses implement the two
    _pg_expression / _sf_expression methods; the public API wraps them with
    COALESCE(CAST(… AS TEXT/STRING), '<<NULL>>')."""

    @property
    @abstractmethod
    def rule_name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def trigger_pairs(self) -> List[Tuple[str, str]]: ...

    @abstractmethod
    def _pg_expression(self, col: str) -> str: ...

    @abstractmethod
    def _sf_expression(self, col: str) -> str: ...

    def apply_postgresql(self, col: str, alias: Optional[str] = None) -> str:
        wrapped = self._coalesce_pg(self._pg_expression(col))
        return f"{wrapped} AS {alias}" if alias else wrapped

    def apply_snowflake(self, col: str, alias: Optional[str] = None) -> str:
        wrapped = self._coalesce_sf(self._sf_expression(col))
        return f"{wrapped} AS {alias}" if alias else wrapped

    @property
    def is_skip_rule(self) -> bool:
        return False

    @staticmethod
    def _coalesce_pg(expr: str) -> str:
        return f"COALESCE(CAST({expr} AS TEXT), '{NULL_PLACEHOLDER}')"

    @staticmethod
    def _coalesce_sf(expr: str) -> str:
        return f"COALESCE(CAST({expr} AS STRING), '{NULL_PLACEHOLDER}')"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} rule='{self.rule_name}'>"


# ── Rule Registry ─────────────────────────────────────────────────────────────

class RuleRegistry:
    """Maps (pg_type, sf_type) pairs to validation rules — first match wins."""

    def __init__(self):
        self._rules: List[BaseValidationRule] = []
        self._default: Optional[BaseValidationRule] = None

    def register(self, rule: BaseValidationRule):
        self._rules.append(rule)
        if rule.rule_name == "text":
            self._default = rule

    def lookup(self, pg_type: str, sf_type: str) -> BaseValidationRule:
        pg_norm = _normalize_type(pg_type)
        sf_norm = _normalize_type(sf_type)
        for rule in self._rules:
            for pg_pat, sf_pat in rule.trigger_pairs:
                if _type_matches(pg_norm, pg_pat) and _type_matches(sf_norm, sf_pat):
                    return rule
        return self._default or (self._rules[0] if self._rules else _NoOpRule())

    def all_rules(self) -> List[BaseValidationRule]:
        return list(self._rules)


def _normalize_type(type_str: str) -> str:
    if not type_str:
        return ""
    normalized = re.sub(r"\([^)]*\)", "", type_str)
    normalized = re.sub(r"\s+without\s+time\s+zone", "_NTZ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+with\s+time\s+zone",    "_TZ",  normalized, flags=re.IGNORECASE)
    return normalized.strip().upper()


def _type_matches(type_str: str, pattern: str) -> bool:
    if pattern == "*":
        return True
    return type_str.upper().startswith(pattern.upper())


class _NoOpRule(BaseValidationRule):
    @property
    def rule_name(self) -> str: return "noop"
    @property
    def description(self) -> str: return "No-op fallback."
    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]: return [("*", "*")]
    def _pg_expression(self, col: str) -> str: return f"CAST({col} AS TEXT)"
    def _sf_expression(self, col: str) -> str: return f"CAST({col} AS STRING)"


# ── Concrete Rules ────────────────────────────────────────────────────────────

class BooleanRule(BaseValidationRule):
    """Boolean: TRUE→'1', FALSE→'0'. NULL→'<<NULL>>'."""

    @property
    def rule_name(self) -> str: return "boolean"

    @property
    def description(self) -> str:
        return "Boolean: TRUE→'1', FALSE→'0'. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [("BOOLEAN", "BOOLEAN"), ("BOOLEAN", "BOOL"),
                ("BOOL", "BOOLEAN"),   ("BOOL", "BOOL")]

    def _pg_expression(self, col: str) -> str:
        return (f"CASE WHEN {col} = true THEN '1' "
                f"WHEN {col} = false THEN '0' ELSE NULL END")

    def _sf_expression(self, col: str) -> str:
        return (f"CASE WHEN {col} = TRUE THEN '1' "
                f"WHEN {col} = FALSE THEN '0' ELSE NULL END")


class IntegerRule(BaseValidationRule):
    """Integer types: cast to text for cross-system comparison. NULL→'<<NULL>>'."""

    @property
    def rule_name(self) -> str: return "integer"

    @property
    def description(self) -> str:
        return "Integer: cast to text. Handles SMALLINT/INT/BIGINT/SERIAL→NUMBER. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [("SMALLINT", "NUMBER"), ("SMALLINT", "INTEGER"),
                ("INTEGER",  "NUMBER"), ("INTEGER",  "INTEGER"),
                ("INT",      "NUMBER"), ("INT",      "INTEGER"),
                ("BIGINT",   "NUMBER"), ("BIGINT",   "INTEGER"),
                ("SERIAL",   "NUMBER"), ("SERIAL",   "INTEGER"),
                ("BIGSERIAL","NUMBER"), ("BIGSERIAL","INTEGER")]

    def _pg_expression(self, col: str) -> str: return f"CAST({col} AS TEXT)"
    def _sf_expression(self, col: str) -> str: return f"CAST({col} AS STRING)"


DEFAULT_DECIMAL_PLACES: int = 2


class NumericRule(BaseValidationRule):
    """Numeric/decimal: round to N decimal places then to text. NULL→'<<NULL>>'."""

    def __init__(self, decimal_places: int = DEFAULT_DECIMAL_PLACES):
        self._dp = decimal_places

    @property
    def rule_name(self) -> str: return "numeric"

    @property
    def description(self) -> str:
        return f"Numeric: round to {self._dp} dp then text. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [("NUMERIC",          "NUMBER"),  ("NUMERIC",          "NUMERIC"),
                ("DECIMAL",          "NUMBER"),  ("DECIMAL",          "DECIMAL"),
                ("FLOAT",            "FLOAT"),   ("REAL",             "FLOAT"),
                ("DOUBLE PRECISION", "FLOAT"),   ("DOUBLE PRECISION", "NUMBER"),
                ("MONEY",            "NUMBER")]

    def _pg_expression(self, col: str) -> str:
        return f"ROUND(CAST({col} AS NUMERIC), {self._dp})"

    def _sf_expression(self, col: str) -> str:
        return f"ROUND(CAST({col} AS NUMBER(38, {self._dp})), {self._dp})"


class TimestampTZRule(BaseValidationRule):
    """Timestamp TZ: convert to UTC then format as 'YYYY-MM-DD HH24:MI:SS'. NULL→'<<NULL>>'."""

    @property
    def rule_name(self) -> str: return "timestamp_tz"

    @property
    def description(self) -> str:
        return "Timestamp TZ: UTC normalize, format YYYY-MM-DD HH24:MI:SS. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [("TIMESTAMP_TZ", "TIMESTAMP_TZ"),
                ("TIMESTAMP_TZ", "TIMESTAMPTZ"),
                ("TIMESTAMPTZ",  "TIMESTAMP_TZ")]

    def _pg_expression(self, col: str) -> str:
        return f"TO_CHAR({col} AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')"

    def _sf_expression(self, col: str) -> str:
        return f"TO_VARCHAR(CONVERT_TIMEZONE('UTC', {col}), 'YYYY-MM-DD HH24:MI:SS')"


class TimestampNTZRule(BaseValidationRule):
    """Timestamp NTZ: format as 'YYYY-MM-DD HH24:MI:SS', strip microseconds. NULL→'<<NULL>>'."""

    @property
    def rule_name(self) -> str: return "timestamp_ntz"

    @property
    def description(self) -> str:
        return "Timestamp NTZ: format YYYY-MM-DD HH24:MI:SS. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [("TIMESTAMP",     "TIMESTAMP_NTZ"),
                ("TIMESTAMP_NTZ", "TIMESTAMP_NTZ"),
                ("TIMESTAMP",     "TIMESTAMP"),
                ("TIMESTAMP_NTZ", "TIMESTAMP")]

    def _pg_expression(self, col: str) -> str:
        return f"TO_CHAR({col}, 'YYYY-MM-DD HH24:MI:SS')"

    def _sf_expression(self, col: str) -> str:
        return f"TO_VARCHAR({col}, 'YYYY-MM-DD HH24:MI:SS')"


class DateRule(BaseValidationRule):
    """Date: format as 'YYYY-MM-DD'. NULL→'<<NULL>>'."""

    @property
    def rule_name(self) -> str: return "date"

    @property
    def description(self) -> str: return "Date: format YYYY-MM-DD. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [("DATE", "DATE")]

    def _pg_expression(self, col: str) -> str: return f"TO_CHAR({col}, 'YYYY-MM-DD')"
    def _sf_expression(self, col: str) -> str: return f"TO_VARCHAR({col}, 'YYYY-MM-DD')"


class TextRule(BaseValidationRule):
    """Text/VARCHAR: TRIM whitespace. Wildcard fallback for all unmatched types. NULL→'<<NULL>>'."""

    @property
    def rule_name(self) -> str: return "text"

    @property
    def description(self) -> str:
        return "Text: trim leading/trailing spaces. Empty string stays empty. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [("CHARACTER VARYING", "TEXT"),    ("CHARACTER VARYING", "VARCHAR"),
                ("CHARACTER VARYING", "STRING"),  ("VARCHAR",           "VARCHAR"),
                ("VARCHAR",           "STRING"),  ("VARCHAR",           "TEXT"),
                ("CHAR",              "CHAR"),    ("CHAR",              "VARCHAR"),
                ("CHAR",              "STRING"),  ("TEXT",              "TEXT"),
                ("TEXT",              "VARCHAR"), ("TEXT",              "STRING"),
                ("*",                 "*")]       # wildcard fallback — must be LAST

    def _pg_expression(self, col: str) -> str: return f"TRIM({col})"
    def _sf_expression(self, col: str) -> str: return f"TRIM({col})"


class UUIDRule(BaseValidationRule):
    """UUID: UPPER(TRIM(CAST AS TEXT)). NULL→'<<NULL>>'."""

    @property
    def rule_name(self) -> str: return "uuid"

    @property
    def description(self) -> str:
        return "UUID: UPPER+TRIM. Handles PG UUID→SF VARCHAR/STRING. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [("UUID", "TEXT"), ("UUID", "VARCHAR"),
                ("UUID", "STRING"), ("UUID", "UUID")]

    def _pg_expression(self, col: str) -> str: return f"UPPER(TRIM(CAST({col} AS TEXT)))"
    def _sf_expression(self, col: str) -> str: return f"UPPER(TRIM(CAST({col} AS STRING)))"


class JSONRule(BaseValidationRule):
    """JSON/JSONB: canonical JSON serialization. NULL→'<<NULL>>'."""

    @property
    def rule_name(self) -> str: return "json"

    @property
    def description(self) -> str:
        return "JSON/JSONB→VARIANT: canonical JSON string. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [("JSON",  "VARIANT"), ("JSON",  "VARCHAR"), ("JSON",  "STRING"), ("JSON",  "TEXT"),
                ("JSONB", "VARIANT"), ("JSONB", "VARCHAR"), ("JSONB", "STRING"), ("JSONB", "TEXT")]

    def _pg_expression(self, col: str) -> str: return f"{col}::jsonb::text"
    def _sf_expression(self, col: str) -> str: return f"TO_JSON(PARSE_JSON(CAST({col} AS STRING)))"


class ByteaRule(BaseValidationRule):
    """Binary/BYTEA: hex encoding for cross-system comparison. NULL→'<<NULL>>'."""

    @property
    def rule_name(self) -> str: return "bytea"

    @property
    def description(self) -> str:
        return "Binary/BYTEA: hex text representation. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [("BYTEA",     "BINARY"),   ("BYTEA",     "VARBINARY"),
                ("BINARY",    "BINARY"),   ("VARBINARY", "BINARY"),
                ("BYTEA",     "VARCHAR"),  ("BYTEA",     "STRING")]

    def _pg_expression(self, col: str) -> str: return f"encode({col}, 'hex')"
    def _sf_expression(self, col: str) -> str: return f"LOWER(HEX_ENCODE({col}))"


class HStoreRule(BaseValidationRule):
    """HStore: CAST to TEXT first (required), then TRIM. NULL→'<<NULL>>'."""

    @property
    def rule_name(self) -> str: return "hstore"

    @property
    def description(self) -> str:
        return "HStore: CAST to TEXT then TRIM. PG TRIM() can't accept hstore directly. NULL→'<<NULL>>'."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [("HSTORE", "TEXT"), ("HSTORE", "VARCHAR"),
                ("HSTORE", "STRING"), ("HSTORE", "VARIANT")]

    def _pg_expression(self, col: str) -> str: return f"TRIM(CAST({col} AS TEXT))"
    def _sf_expression(self, col: str) -> str: return f"TRIM({col})"


class NullPlaceholderRule(BaseValidationRule):
    """Bare NULL→'<<NULL>>' with plain text cast. Used when no other transformation needed."""

    @property
    def rule_name(self) -> str: return "null_placeholder"

    @property
    def description(self) -> str:
        return f"NULL→'{NULL_PLACEHOLDER}'. Cast to text. Universal rule."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return []  # not auto-matched; explicitly registered for direct use

    def _pg_expression(self, col: str) -> str: return f"CAST({col} AS TEXT)"
    def _sf_expression(self, col: str) -> str: return f"CAST({col} AS STRING)"

    def apply_postgresql(self, col: str, alias=None) -> str:
        expr = f"COALESCE(CAST({col} AS TEXT), '{NULL_PLACEHOLDER}')"
        return f"{expr} AS {alias}" if alias else expr

    def apply_snowflake(self, col: str, alias=None) -> str:
        expr = f"COALESCE(CAST({col} AS STRING), '{NULL_PLACEHOLDER}')"
        return f"{expr} AS {alias}" if alias else expr
