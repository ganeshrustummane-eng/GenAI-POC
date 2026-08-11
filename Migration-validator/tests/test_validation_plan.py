"""
Tests for core/validation_plan.py and validation/plan_validator.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.validation_plan import (
    CanonicalValidationPlan,
    ColumnMappingEntry,
    PlanStatus,
    MatchMethod,
)
from validation.plan_validator import PlanValidator, PlanValidationError


# ---------------------------------------------------------------------------
# ColumnMappingEntry helpers
# ---------------------------------------------------------------------------

def _entry(src="col_a", tgt="COL_A", rule="text", skip=False, method="exact",
           confidence=0.99, ai=False):
    return ColumnMappingEntry(
        source_column=src,
        source_type="text",
        source_normalized=src.lower(),
        target_column=tgt,
        target_type="TEXT",
        target_normalized=tgt.lower(),
        match_method=method,
        confidence=confidence,
        transformation_rule=rule,
        skip_validation=skip,
        skip_reason="skip" if skip else "",
        ai_resolved=ai,
    )


def _plan(mappings=None, source_table="events", target_table="EVENTS"):
    return CanonicalValidationPlan(
        source_schema="public",
        source_table=source_table,
        target_schema="my_schema",
        target_table=target_table,
        mappings=mappings or [_entry()],
    )


# ---------------------------------------------------------------------------
# PlanStatus enum
# ---------------------------------------------------------------------------

def test_plan_status_values():
    assert PlanStatus.COMPLETE.value == "complete"
    assert PlanStatus.PARTIAL.value == "partial"
    assert PlanStatus.AMBIGUOUS.value == "ambiguous"
    assert PlanStatus.INVALID.value == "invalid"


# ---------------------------------------------------------------------------
# MatchMethod enum
# ---------------------------------------------------------------------------

def test_match_method_values():
    assert MatchMethod.EXACT.value == "exact"
    assert MatchMethod.NORMALIZED_EXACT.value == "normalized_exact"
    assert MatchMethod.FUZZY.value == "fuzzy"
    assert MatchMethod.FUZZY_AI.value == "fuzzy_ai"
    assert MatchMethod.SKIP.value == "skip"


# ---------------------------------------------------------------------------
# CanonicalValidationPlan properties
# ---------------------------------------------------------------------------

def test_active_mappings_excludes_skipped():
    plan = _plan(mappings=[_entry("a", skip=False), _entry("b", "COL_B", skip=True)])
    assert len(plan.active_mappings) == 1
    assert plan.active_mappings[0].source_column == "a"


def test_skipped_mappings():
    plan = _plan(mappings=[_entry("a", skip=False), _entry("b", "COL_B", skip=True)])
    assert len(plan.skipped_mappings) == 1
    assert plan.skipped_mappings[0].source_column == "b"


def test_exact_matches_filter():
    plan = _plan(mappings=[
        _entry("a", method="exact"),
        _entry("b", "COL_B", method="fuzzy"),
        _entry("c", "COL_C", method="normalized_exact"),
    ])
    exacts = plan.exact_matches
    assert len(exacts) == 2
    assert all(m.match_method in ("exact", "normalized_exact") for m in exacts)


def test_fuzzy_matches_filter():
    plan = _plan(mappings=[
        _entry("a", method="exact"),
        _entry("b", "COL_B", method="fuzzy"),
    ])
    assert len(plan.fuzzy_matches) == 1


def test_ai_resolved_matches():
    plan = _plan(mappings=[
        _entry("a", ai=False),
        _entry("b", "COL_B", ai=True, method="fuzzy_ai"),
    ])
    assert len(plan.ai_resolved_matches) == 1


def test_is_valid_true_by_default():
    plan = _plan()
    assert plan.is_valid


def test_is_valid_false_when_invalid():
    plan = _plan()
    plan.status = PlanStatus.INVALID.value
    assert not plan.is_valid


def test_to_dict_has_expected_keys():
    plan = _plan()
    d = plan.to_dict()
    assert "source_table" in d
    assert "target_table" in d
    assert "status" in d
    assert "mappings" in d
    assert "stats" in d


def test_column_mapping_entry_to_dict():
    e = _entry("created_at", "CREATEDAT", rule="timestamp_ntz")
    d = e.to_dict()
    assert d["source_column"] == "created_at"
    assert d["target_column"] == "CREATEDAT"
    assert d["transformation_rule"] == "timestamp_ntz"
    assert "confidence" in d


# ---------------------------------------------------------------------------
# PlanValidator
# ---------------------------------------------------------------------------

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


def test_confidence_out_of_range_fails():
    validator = PlanValidator()
    plan = _plan(mappings=[_entry("col_a", confidence=1.5)])
    result = validator.validate(plan)
    assert not result.is_valid


if __name__ == "__main__":
    test_plan_status_values()
    test_match_method_values()
    test_active_mappings_excludes_skipped()
    test_skipped_mappings()
    test_exact_matches_filter()
    test_fuzzy_matches_filter()
    test_ai_resolved_matches()
    test_is_valid_true_by_default()
    test_is_valid_false_when_invalid()
    test_to_dict_has_expected_keys()
    test_column_mapping_entry_to_dict()
    test_valid_plan_passes()
    test_empty_source_table_fails()
    test_no_active_mappings_fails()
    test_duplicate_source_column_fails()
    test_validate_or_raise_raises_on_failure()
    test_plan_status_set_to_invalid_on_failure()
    test_confidence_out_of_range_fails()
    print("All validation plan tests passed.")
