"""
Core package — CanonicalValidationPlan and related models.

The CanonicalValidationPlan is the single source of truth from which
both SQL and YAML are generated deterministically.
"""

from core.validation_plan import (
    CanonicalValidationPlan,
    ColumnMappingEntry,
    PlanStatus,
)

__all__ = [
    "CanonicalValidationPlan",
    "ColumnMappingEntry",
    "PlanStatus",
]
