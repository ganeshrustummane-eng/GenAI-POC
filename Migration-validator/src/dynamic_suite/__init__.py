"""
Dynamic Validation Suite Package
==================================
Orchestrates schema profiling → rule decisions → query optimisation →
SQL generation into a single dynamic validation suite per table.

Public API
----------
  ValidationSuite           — output container (all SQL + metadata)
  DynamicSuiteGenerator     — top-level orchestrator
  QueryOptimizer            — collapses requirements into minimal queries
"""

from dynamic_suite.validation_suite import ValidationSuite, GeneratedQuery
from dynamic_suite.query_optimizer import QueryOptimizer
from dynamic_suite.suite_generator import DynamicSuiteGenerator

__all__ = [
    "ValidationSuite",
    "GeneratedQuery",
    "QueryOptimizer",
    "DynamicSuiteGenerator",
]
