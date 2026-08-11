"""
Static Rule Mapper
===================
Maps PostgreSQL → Snowflake column pairs to validation rules using
deterministic type-pair matching against the rules catalog.

No AI / API key required — works fully offline.
Accuracy depends on how well the type pairs are defined in the rules catalog.

The mapper uses the rules/ package to look up the correct rule for each
(pg_type, sf_type) pair. It also handles:
  - Column name matching (case-insensitive)
  - Primary key auto-detection
  - Fivetran metadata column filtering (_FIVETRAN_* columns skipped)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from sql_extractor.base_extractor import ColumnMetadata
from rules import get_rule_for_type, BaseValidationRule


# Fivetran metadata column prefixes — skip these in validation
_FIVETRAN_SKIP_PREFIXES = ("_FIVETRAN_",)


@dataclass
class ColumnRuleMapping:
    """
    Represents a single source→target column pair with its assigned rule.

    Attributes:
        source_column   : Column name in PostgreSQL
        target_column   : Column name in Snowflake
        source_type     : PostgreSQL data type string
        target_type     : Snowflake data type string
        rule            : The validation rule assigned to this column pair
        is_primary_key  : True if this column is (part of) the table's PK
        skip_validation : True if column should be excluded from validation
                          (Fivetran metadata columns, unmatched columns)
        skip_reason     : Human-readable reason for skipping (if applicable)
        matched_by      : 'name' | 'ai' | 'position' — how the columns were paired
    """
    source_column: str
    target_column: str
    source_type: str
    target_type: str
    rule: BaseValidationRule
    is_primary_key: bool = False
    skip_validation: bool = False
    skip_reason: str = ""
    matched_by: str = "name"

    @property
    def normalized_alias(self) -> str:
        """
        Returns the normalized alias for this column pair.
        Always uses the SOURCE column name to ensure both sides have the same alias.
        Example: 'event_id' → 'event_id_normalized'
        """
        return f"{self.source_column}_normalized"

    def __repr__(self) -> str:
        pk_tag  = " [PK]"  if self.is_primary_key  else ""
        skip_tag = " [SKIP]" if self.skip_validation else ""
        return (
            f"ColumnRuleMapping({self.source_column}({self.source_type})"
            f" → {self.target_column}({self.target_type})"
            f" rule={self.rule.rule_name}{pk_tag}{skip_tag})"
        )


class StaticRuleMapper:
    """
    Assigns validation rules to column pairs using deterministic type matching.

    Algorithm:
      1. Build a case-insensitive name lookup for target columns.
      2. For each source column, find the matching target column by name.
      3. Call rules.get_rule_for_type(pg_type, sf_type) to get the rule.
      4. Auto-detect primary key columns by name heuristics.
      5. Skip Fivetran metadata columns (_FIVETRAN_*).
    """

    def map_columns(
        self,
        source_columns: List[ColumnMetadata],
        target_columns: List[ColumnMetadata],
        primary_key_hints: Optional[List[str]] = None,
    ) -> List[ColumnRuleMapping]:
        """
        Map source columns to target columns and assign validation rules.

        Args:
            source_columns    : PostgreSQL column metadata list
            target_columns    : Snowflake column metadata list
            primary_key_hints : Optional list of column names that are PKs

        Returns:
            List[ColumnRuleMapping] — one entry per matched column pair.
            Unmatched source columns are included with skip_validation=True.
        """
        pk_hints_upper = {h.upper() for h in (primary_key_hints or [])}
        target_by_name: Dict[str, ColumnMetadata] = {
            col.column_name.upper(): col for col in target_columns
        }

        mappings: List[ColumnRuleMapping] = []

        for src_col in source_columns:
            # Skip Fivetran internal metadata columns
            if _is_fivetran_column(src_col.column_name):
                continue

            # Try to find matching target column by name
            tgt_col = target_by_name.get(src_col.column_name.upper())

            if tgt_col is None:
                # Log unmatched and skip
                print(
                    f"  [WARN] Source column '{src_col.column_name}' "
                    f"has no matching target column — skipped."
                )
                mappings.append(ColumnRuleMapping(
                    source_column=src_col.column_name,
                    target_column=src_col.column_name,
                    source_type=src_col.data_type,
                    target_type="UNKNOWN",
                    rule=get_rule_for_type("text", "text"),
                    skip_validation=True,
                    skip_reason="No matching target column found",
                ))
                continue

            # Skip Fivetran metadata on target side too
            if _is_fivetran_column(tgt_col.column_name):
                continue

            # Determine if primary key
            is_pk = (
                src_col.column_name.upper() in pk_hints_upper
                or _is_likely_pk(src_col.column_name, src_col.data_type)
                and not pk_hints_upper  # Only auto-detect when no hints provided
            )

            # Get the validation rule
            rule = get_rule_for_type(src_col.data_type, tgt_col.data_type)

            mappings.append(ColumnRuleMapping(
                source_column=src_col.column_name,
                target_column=tgt_col.column_name,
                source_type=src_col.data_type,
                target_type=tgt_col.data_type,
                rule=rule,
                is_primary_key=is_pk,
                matched_by="name",
            ))

        print(
            f"  [StaticMapper] Mapped {sum(1 for m in mappings if not m.skip_validation)} columns "
            f"({sum(1 for m in mappings if m.skip_validation)} skipped)"
        )
        return mappings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_fivetran_column(column_name: str) -> bool:
    """Returns True if the column is a Fivetran internal metadata column."""
    upper = column_name.upper()
    return any(upper.startswith(prefix) for prefix in _FIVETRAN_SKIP_PREFIXES)


def _is_likely_pk(column_name: str, data_type: str) -> bool:
    """
    Heuristically detect if a column is a primary key.
    Only triggers when no explicit PK hints are provided.
    """
    name_lower = column_name.lower()
    is_integer_type = any(
        t in data_type.upper()
        for t in ("INT", "SERIAL", "NUMBER", "BIGINT", "SMALLINT")
    )
    return (
        is_integer_type
        and (name_lower == "id" or name_lower.endswith("_id"))
    )
