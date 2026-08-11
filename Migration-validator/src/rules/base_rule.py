"""
Base Validation Rule — Abstract Interface & Registry
=====================================================
Defines the contract every rule must implement and provides a
central RuleRegistry for rule lookup by PostgreSQL/Snowflake type pairs.

Design Principles
-----------------
- Rules are STATELESS — all context is passed as arguments.
- Rules produce SQL FRAGMENTS only (no aliases, no SELECT keyword).
- The NULL placeholder wrapper (<<NULL>>) is always the LAST step and
  is automatically applied inside apply_postgresql() / apply_snowflake().
- Each rule lists its trigger type pairs so the registry can auto-select.

Rule Application (innermost → outermost):
  1. Type-specific expression   (_pg_expression / _sf_expression)
  2. COALESCE(CAST(… AS TEXT/STRING), '<<NULL>>')   ← always outermost

Fivetran Filter (Snowflake side only):
  WHERE _FIVETRAN_ACTIVE = TRUE  is injected at the query level,
  NOT inside individual rule expressions.
"""

import re
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# NULL placeholder constant — used instead of SQL NULL for comparability
# ---------------------------------------------------------------------------
NULL_PLACEHOLDER = "<<NULL>>"


class BaseValidationRule(ABC):
    """
    Abstract base class for all PostgreSQL → Snowflake validation rules.

    Subclasses must implement:
        - rule_name: str  property
        - trigger_pairs: list of (pg_type_pattern, sf_type_pattern)
        - _pg_expression(col): raw SQL fragment for PostgreSQL (no alias)
        - _sf_expression(col): raw SQL fragment for Snowflake  (no alias)

    The public methods apply_postgresql() / apply_snowflake() automatically
    wrap the inner expression with the <<NULL>> placeholder COALESCE.
    """

    # ── Abstract properties ──────────────────────────────────────────────

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Short identifier, e.g. 'boolean', 'timestamp_ntz'."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description shown in YAML comments and logs."""

    @property
    @abstractmethod
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        """
        List of (pg_type_regex, sf_type_regex) pairs that trigger this rule.
        Patterns are matched case-insensitively against the raw type string.
        Use '*' to match any type (wildcard).

        Example:
            [("boolean", "boolean"), ("bool", "boolean")]
        """

    # ── Abstract SQL builders ────────────────────────────────────────────

    @abstractmethod
    def _pg_expression(self, col: str) -> str:
        """
        Build the inner SQL expression for PostgreSQL (no COALESCE wrapper).
        The result will be wrapped by apply_postgresql().
        """

    @abstractmethod
    def _sf_expression(self, col: str) -> str:
        """
        Build the inner SQL expression for Snowflake (no COALESCE wrapper).
        The result will be wrapped by apply_snowflake().
        """

    # ── Public API ───────────────────────────────────────────────────────

    def apply_postgresql(self, col: str, alias: Optional[str] = None) -> str:
        """
        Returns a complete PostgreSQL SELECT expression with:
          - Type normalization inner expression
          - NULL → '<<NULL>>' COALESCE wrapper (outermost)
          - Optional AS alias

        Args:
            col  : Column reference as it appears in SQL (e.g. 'is_active')
            alias: Optional AS alias (e.g. 'is_active_normalized')

        Returns:
            Full SQL expression string ready to embed in a SELECT clause.
        """
        inner = self._pg_expression(col)
        wrapped = self._coalesce_pg(inner)
        return f"{wrapped} AS {alias}" if alias else wrapped

    def apply_snowflake(self, col: str, alias: Optional[str] = None) -> str:
        """
        Returns a complete Snowflake SELECT expression with:
          - Type normalization inner expression
          - NULL → '<<NULL>>' COALESCE wrapper (outermost)
          - Optional AS alias

        Args:
            col  : Column reference as it appears in SQL (e.g. 'IS_ACTIVE')
            alias: Optional AS alias (e.g. 'is_active_normalized')

        Returns:
            Full SQL expression string ready to embed in a SELECT clause.
        """
        inner = self._sf_expression(col)
        wrapped = self._coalesce_sf(inner)
        return f"{wrapped} AS {alias}" if alias else wrapped

    @property
    def is_skip_rule(self) -> bool:
        """
        Return True if this rule marks the column as non-comparable.
        Skip rules (JSON, Bytea) generate a comment instead of SQL.
        """
        return False

    # ── NULL wrapper helpers ─────────────────────────────────────────────

    @staticmethod
    def _coalesce_pg(expr: str) -> str:
        """Wrap expr with PostgreSQL COALESCE → '<<NULL>>' sentinel."""
        return f"COALESCE(CAST({expr} AS TEXT), '{NULL_PLACEHOLDER}')"

    @staticmethod
    def _coalesce_sf(expr: str) -> str:
        """Wrap expr with Snowflake COALESCE → '<<NULL>>' sentinel."""
        return f"COALESCE(CAST({expr} AS STRING), '{NULL_PLACEHOLDER}')"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} rule='{self.rule_name}'>"


# ---------------------------------------------------------------------------
# Rule Registry
# ---------------------------------------------------------------------------

class RuleRegistry:
    """
    Central registry that maps (pg_type, sf_type) pairs to validation rules.

    Rules are matched in registration order.
    The first rule whose trigger_pairs match wins.
    If no rule matches, TextRule is used as the default fallback.
    """

    def __init__(self):
        self._rules: List[BaseValidationRule] = []
        self._default: Optional[BaseValidationRule] = None

    def register(self, rule: BaseValidationRule):
        """
        Register a rule. If rule_name == 'text', it becomes the default fallback.
        """
        self._rules.append(rule)
        if rule.rule_name == "text":
            self._default = rule

    def lookup(self, pg_type: str, sf_type: str) -> BaseValidationRule:
        """
        Find the best matching rule for the given type pair.

        Matching logic:
          1. Normalize both types: strip size/precision modifiers, uppercase.
          2. Try each registered rule's trigger_pairs in order.
          3. Return the first match.
          4. Fall back to default (TextRule) if nothing matches.
        """
        pg_norm = _normalize_type(pg_type)
        sf_norm = _normalize_type(sf_type)

        for rule in self._rules:
            for pg_pat, sf_pat in rule.trigger_pairs:
                if _type_matches(pg_norm, pg_pat) and _type_matches(sf_norm, sf_pat):
                    return rule

        # Fallback: return default (TextRule) or first registered rule
        return self._default or (self._rules[0] if self._rules else _NoOpRule())

    def all_rules(self) -> List[BaseValidationRule]:
        """Return all registered rules in registration order."""
        return list(self._rules)

    def describe(self) -> str:
        """Return a human-readable summary of all registered rules."""
        lines = ["Registered Validation Rules:", "=" * 50]
        for rule in self._rules:
            pairs = ", ".join(f"{p} → {t}" for p, t in rule.trigger_pairs[:3])
            lines.append(f"  [{rule.rule_name}] {rule.description}")
            lines.append(f"    Triggers: {pairs}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_type(type_str: str) -> str:
    """
    Normalize a type string for matching:
      - Strip size/precision: VARCHAR(100) → VARCHAR
      - Strip 'without time zone' suffixes
      - Uppercase
      - Strip extra whitespace
    """
    if not type_str:
        return ""
    # Remove precision/size modifiers
    normalized = re.sub(r"\([^)]*\)", "", type_str)
    # Normalize common PostgreSQL verbose type names
    normalized = re.sub(r"\s+without\s+time\s+zone", "_NTZ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+with\s+time\s+zone", "_TZ", normalized, flags=re.IGNORECASE)
    return normalized.strip().upper()


def _type_matches(type_str: str, pattern: str) -> bool:
    """
    Check if a normalized type string matches a pattern.
    '*' is a wildcard that matches anything.
    Pattern matching is case-insensitive prefix/substring match.
    """
    if pattern == "*":
        return True
    return type_str.upper().startswith(pattern.upper())


# ---------------------------------------------------------------------------
# No-op fallback (should never be reached in practice)
# ---------------------------------------------------------------------------

class _NoOpRule(BaseValidationRule):
    """Fallback rule — returns column as-is with NULL placeholder."""

    @property
    def rule_name(self) -> str:
        return "noop"

    @property
    def description(self) -> str:
        return "No-op fallback — casts column to text with NULL placeholder."

    @property
    def trigger_pairs(self) -> List[Tuple[str, str]]:
        return [("*", "*")]

    def _pg_expression(self, col: str) -> str:
        return f"CAST({col} AS TEXT)"

    def _sf_expression(self, col: str) -> str:
        return f"CAST({col} AS STRING)"
