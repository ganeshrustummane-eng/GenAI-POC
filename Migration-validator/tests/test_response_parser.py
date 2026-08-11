"""
Tests for ai/response_parser.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai.response_parser import ResponseParser


def test_valid_resolved_response():
    parser = ResponseParser()
    raw = '''{"status": "resolved", "source_column": "created_at",
              "target_column": "CREATEDAT", "source_type": "timestamp",
              "target_type": "VARCHAR", "transformation_rule": "text",
              "confidence": 0.92, "reason": "Normalized names match."}'''
    decision = parser.parse(raw, "created_at", ["CREATEDAT", "UPDATED_AT"])
    assert decision.is_resolved
    assert decision.target_column == "CREATEDAT"
    assert decision.transformation_rule == "text"
    assert 0.0 <= decision.confidence <= 1.0


def test_invented_column_rejected():
    parser = ResponseParser()
    raw = '''{"status": "resolved", "source_column": "x",
              "target_column": "INVENTED_COL", "source_type": "text",
              "target_type": "text", "transformation_rule": "text",
              "confidence": 0.9, "reason": "AI hallucinated this."}'''
    decision = parser.parse(raw, "x", ["COL_A", "COL_B"])
    assert decision.had_parse_error
    assert "not in" in decision.parse_error


def test_markdown_stripped():
    parser = ResponseParser()
    raw = '''```json
{"status": "resolved", "source_column": "id",
 "target_column": "ID", "source_type": "integer",
 "target_type": "NUMBER", "transformation_rule": "integer",
 "confidence": 0.99, "reason": "Exact name match."}
```'''
    decision = parser.parse(raw, "id", ["ID", "IDENTIFIER"])
    assert decision.is_resolved
    assert decision.target_column == "ID"


def test_invalid_json_returns_parse_error():
    parser = ResponseParser()
    decision = parser.parse("not valid json {{{", "col", ["COL"])
    assert decision.had_parse_error
    assert "JSON parse failed" in decision.parse_error


def test_unknown_rule_defaults_to_text():
    parser = ResponseParser()
    raw = '''{"status": "resolved", "source_column": "col",
              "target_column": "COL", "source_type": "text",
              "target_type": "text", "transformation_rule": "nonexistent_rule",
              "confidence": 0.8, "reason": "whatever"}'''
    decision = parser.parse(raw, "col", ["COL"])
    assert not decision.had_parse_error
    assert decision.transformation_rule == "text"


def test_confidence_clamped_to_range():
    parser = ResponseParser()
    raw = '''{"status": "resolved", "source_column": "col",
              "target_column": "COL", "source_type": "text",
              "target_type": "text", "transformation_rule": "text",
              "confidence": 1.5, "reason": "whatever"}'''
    decision = parser.parse(raw, "col", ["COL"])
    assert decision.confidence == 1.0


if __name__ == "__main__":
    test_valid_resolved_response()
    test_invented_column_rejected()
    test_markdown_stripped()
    test_invalid_json_returns_parse_error()
    test_unknown_rule_defaults_to_text()
    test_confidence_clamped_to_range()
    print("All response parser tests passed.")
