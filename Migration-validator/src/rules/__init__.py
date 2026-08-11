"""
Rules Package — PostgreSQL → Snowflake Validation Transformation Rules
=======================================================================
This package contains all type-specific transformation rules that normalize
data from PostgreSQL (source) to Snowflake (target) for accurate comparison.

Each rule handles a specific PostgreSQL → Snowflake type pair and produces
SQL expressions that eliminate false mismatches caused by:
  - Type representation differences   (boolean TRUE/FALSE vs 1/0)
  - Precision differences             (numeric rounding)
  - Timestamp formatting              (microsecond noise)
  - Whitespace differences            (leading/trailing spaces)
  - Case differences                  (UUID uppercase/lowercase)
  - NULL handling                     (SQL NULL ≠ NULL, use <<NULL>> sentinel)
  - JSON formatting                   (canonical serialization)
  - Binary encoding                   (hex text representation)

Additionally, Snowflake-specific filter:
  - _FIVETRAN_ACTIVE = TRUE filter is applied on Snowflake side
    to ensure only the LATEST active record is compared (not history).

Rule Application Order (innermost → outermost):
  1. integer_cast / uuid_upper / json_canonical / bytea_hex
  2. boolean_to_flag
  3. timestamp_format / date_format
  4. numeric_round
  5. text_trim / empty_string_null
  6. null_placeholder  ← always LAST (outermost)

Usage:
    from rules import get_rule_for_type, RuleRegistry
    rule = get_rule_for_type("boolean", "boolean")
    pg_expr  = rule.apply_postgresql("is_active")
    sf_expr  = rule.apply_snowflake("IS_ACTIVE")
"""

from rules.base_rule import BaseValidationRule, RuleRegistry
from rules.boolean_rule import BooleanRule
from rules.numeric_rule import NumericRule
from rules.timestamp_ntz_rule import TimestampNTZRule
from rules.timestamp_tz_rule import TimestampTZRule
from rules.date_rule import DateRule
from rules.text_rule import TextRule
from rules.uuid_rule import UUIDRule
from rules.integer_rule import IntegerRule
from rules.json_rule import JSONRule
from rules.bytea_rule import ByteaRule
from rules.hstore_rule import HStoreRule
from rules.null_rule import NullPlaceholderRule

# ---------------------------------------------------------------------------
# Build the global registry — single source of truth for rule lookup
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Registration ORDER is critical!
# Specific rules MUST come before the TextRule wildcard ('*', '*') catch-all.
# The registry returns the FIRST matching rule — so specifics go first.
# ---------------------------------------------------------------------------
_registry = RuleRegistry()

# 1. Exact / specific type rules (registered first — win over wildcard)
_registry.register(BooleanRule())
_registry.register(NumericRule())
_registry.register(TimestampTZRule())   # TZ before NTZ (more specific)
_registry.register(TimestampNTZRule())
_registry.register(DateRule())
_registry.register(UUIDRule())
_registry.register(IntegerRule())
_registry.register(JSONRule())
_registry.register(ByteaRule())
_registry.register(HStoreRule())
_registry.register(NullPlaceholderRule())

# 2. Text/wildcard fallback — MUST be registered LAST
# TextRule has trigger_pairs including ('*', '*') which matches any type pair.
# If registered before specific rules it would swallow everything.
_registry.register(TextRule())


def get_rule_for_type(pg_type: str, sf_type: str) -> BaseValidationRule:
    """
    Look up the correct validation rule for a PostgreSQL → Snowflake type pair.

    Args:
        pg_type: PostgreSQL data type (e.g. 'boolean', 'timestamp without time zone')
        sf_type: Snowflake data type  (e.g. 'BOOLEAN', 'TIMESTAMP_NTZ')

    Returns:
        The matching BaseValidationRule instance.
        Falls back to TextRule (trim + null placeholder) if no specific rule found.
    """
    return _registry.lookup(pg_type, sf_type)


def get_registry() -> RuleRegistry:
    """Return the global rule registry for introspection or extension."""
    return _registry


__all__ = [
    "BaseValidationRule",
    "RuleRegistry",
    "BooleanRule",
    "NumericRule",
    "TimestampNTZRule",
    "TimestampTZRule",
    "DateRule",
    "TextRule",
    "UUIDRule",
    "IntegerRule",
    "JSONRule",
    "ByteaRule",
    "HStoreRule",
    "NullPlaceholderRule",
    "get_rule_for_type",
    "get_registry",
]
