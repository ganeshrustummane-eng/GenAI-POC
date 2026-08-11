"""
Tests for ai/response_parser.py and ai/rule_planner.py (planner uses mocks)
"""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai.response_parser import ResponseParser, AIColumnDecision


# ---------------------------------------------------------------------------
# ResponseParser tests
# ---------------------------------------------------------------------------

def _parse(raw, source="col_a", candidates=None):
    if candidates is None:
        candidates = ["COL_A", "COL_B", "COL_C"]
    return ResponseParser().parse(raw, source, candidates)


def test_valid_resolved_response():
    raw = json.dumps({
        "status": "resolved",
        "source_column": "col_a",
        "target_column": "COL_A",
        "transformation_rule": "text",
        "confidence": 0.95,
        "reason": "exact match",
    })
    decision = _parse(raw)
    assert decision.is_resolved
    assert decision.target_column == "COL_A"
    assert decision.transformation_rule == "text"
    assert not decision.had_parse_error


def test_invented_column_rejected():
    raw = json.dumps({
        "status": "resolved",
        "source_column": "col_a",
        "target_column": "INVENTED_COLUMN",
        "transformation_rule": "text",
        "confidence": 0.9,
        "reason": "AI made it up",
    })
    decision = _parse(raw, candidates=["COL_A", "COL_B"])
    assert decision.had_parse_error or not decision.is_resolved


def test_markdown_code_fence_stripped():
    inner = json.dumps({
        "status": "resolved",
        "source_column": "col_a",
        "target_column": "COL_A",
        "transformation_rule": "boolean",
        "confidence": 0.99,
        "reason": "boolean match",
    })
    raw = f"```json\n{inner}\n```"
    decision = _parse(raw)
    assert not decision.had_parse_error
    assert decision.target_column == "COL_A"


def test_invalid_json_returns_parse_error():
    decision = _parse("not valid json at all")
    assert decision.had_parse_error
    assert decision.status == "parse_error"


def test_unknown_rule_id_defaults_to_text():
    raw = json.dumps({
        "status": "resolved",
        "source_column": "col_a",
        "target_column": "COL_A",
        "transformation_rule": "completely_made_up_rule",
        "confidence": 0.8,
        "reason": "test",
    })
    decision = _parse(raw)
    # Unknown rule should be defaulted to "text" without crashing
    assert not decision.had_parse_error
    assert decision.transformation_rule == "text"


def test_confidence_above_1_clamped():
    raw = json.dumps({
        "status": "resolved",
        "source_column": "col_a",
        "target_column": "COL_A",
        "transformation_rule": "text",
        "confidence": 1.5,
        "reason": "test",
    })
    decision = _parse(raw)
    assert decision.confidence <= 1.0


def test_confidence_below_0_clamped():
    raw = json.dumps({
        "status": "resolved",
        "source_column": "col_a",
        "target_column": "COL_A",
        "transformation_rule": "text",
        "confidence": -0.3,
        "reason": "test",
    })
    decision = _parse(raw)
    assert decision.confidence >= 0.0


def test_ambiguous_status_preserved():
    raw = json.dumps({
        "status": "ambiguous",
        "source_column": "col_a",
        "target_column": "COL_A",
        "transformation_rule": "text",
        "confidence": 0.6,
        "reason": "not sure",
    })
    decision = _parse(raw)
    assert decision.status == "ambiguous"
    assert not decision.is_resolved


def test_missing_required_fields_returns_parse_error():
    raw = json.dumps({"status": "resolved"})  # missing target_column, etc.
    decision = _parse(raw)
    assert decision.had_parse_error


def test_ai_column_decision_is_resolved_property():
    d = AIColumnDecision(
        source_column="col_a",
        target_column="COL_A",
        source_type="text",
        target_type="TEXT",
        transformation_rule="text",
        confidence=0.9,
        reason="ok",
        status="resolved",
        parse_error=None,
    )
    assert d.is_resolved
    assert not d.had_parse_error


def test_ai_column_decision_had_parse_error_property():
    d = AIColumnDecision(
        source_column="col_a",
        target_column="",
        source_type="text",
        target_type="",
        transformation_rule="text",
        confidence=0.0,
        reason="",
        status="parse_error",
        parse_error="invalid json",
    )
    assert d.had_parse_error
    assert not d.is_resolved


if __name__ == "__main__":
    test_valid_resolved_response()
    test_invented_column_rejected()
    test_markdown_code_fence_stripped()
    test_invalid_json_returns_parse_error()
    test_unknown_rule_id_defaults_to_text()
    test_confidence_above_1_clamped()
    test_confidence_below_0_clamped()
    test_ambiguous_status_preserved()
    test_missing_required_fields_returns_parse_error()
    test_ai_column_decision_is_resolved_property()
    test_ai_column_decision_had_parse_error_property()
    print("All AI rule planner tests passed.")
