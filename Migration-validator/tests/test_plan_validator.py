"""
Tests for validation/plan_validator.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.validation_plan import CanonicalValidationPlan, ColumnMappingEntry, PlanStatus
from validation.plan_validator import PlanValidator, PlanValidationError


def _entry(src="col_a", tgt="COL_A", rule="text", skip=False):
    return ColumnMappingEntry(
        source_column=src,
        source_type="text",
        source_normalized=src.lower(),
        target_column=tgt,
        target_type="TEXT",
        target_normalized=tgt.lower(),
        match_method="exact",
        confidence=0.99,
        transformation_rule=rule,
        skip_validation=skip,
        skip_reason="test skip" if skip else "",
    )


def _plan(mappings=None, source_table="events", target_table="EVENTS"):
    return CanonicalValidationPlan(
        source_schema="public",
        source_table=source_table,
        target_schema="my_schema",
        target_table=target_table,
        mappings=mappings or [_entry()],
    )


def test_valid_plan_passes():
    validator = PlanValidator()
    plan = _plan()
    result = validator.validate(plan)
    assert result.is_valid


def test_empty_source_table_fails():
    validator = PlanValidator()
    plan = _plan(source_table="")
    result = validator.validate(plan)
    assert not result.is_valid
    assert any("source_table" in i for i in result.issues)


def test_no_active_mappings_fails():
    validator = PlanValidator()
    plan = _plan(mappings=[_entry(skip=True)])
    result = validator.validate(plan)
    assert not result.is_valid
    assert any("active" in i.lower() for i in result.issues)


def test_duplicate_source_column_fails():
    validator = PlanValidator()
    plan = _plan(mappings=[_entry("col_a", "COL_A"), _entry("col_a", "COL_B")])
    result = validator.validate(plan)
    assert not result.is_valid
    assert any("Duplicate source column" in i for i in result.issues)


def test_validate_or_raise_raises_on_failure():
    validator = PlanValidator()
    plan = _plan(source_table="")
    try:
        validator.validate_or_raise(plan)
        assert False, "Should have raised PlanValidationError"
    except PlanValidationError as exc:
        assert len(exc.issues) > 0


def test_plan_status_set_to_invalid_on_failure():
    validator = PlanValidator()
    plan = _plan(source_table="")
    validator.validate(plan)
    assert plan.status == PlanStatus.INVALID.value


if __name__ == "__main__":
    test_valid_plan_passes()
    test_empty_source_table_fails()
    test_no_active_mappings_fails()
    test_duplicate_source_column_fails()
    test_validate_or_raise_raises_on_failure()
    test_plan_status_set_to_invalid_on_failure()
    print("All plan validator tests passed.")
