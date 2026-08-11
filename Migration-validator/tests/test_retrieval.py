"""
Tests for learning/retrieval.py
"""
import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from learning.retrieval import LearnedRuleRetriever


def _make_learned_file(entries):
    """Write a temporary learned file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump({"learned_corrections": entries}, tmp)
    tmp.close()
    return Path(tmp.name)


def test_finds_by_exact_name():
    path = _make_learned_file([{
        "source_column": "created_at",
        "target_column": "CREATEDAT",
        "source_type": "timestamp",
        "target_type": "VARCHAR",
        "correct_rule": "text",
        "reason": "Fivetran converts timestamps to strings",
    }])
    retriever = LearnedRuleRetriever(learned_path=path)
    results = retriever.find_relevant("created_at", "timestamp")
    assert len(results) == 1
    assert results[0].correct_rule == "text"
    path.unlink()


def test_returns_empty_when_no_match():
    path = _make_learned_file([{
        "source_column": "user_id",
        "target_column": "USER_ID",
        "source_type": "integer",
        "target_type": "NUMBER",
        "correct_rule": "integer",
        "reason": "",
    }])
    retriever = LearnedRuleRetriever(learned_path=path)
    results = retriever.find_relevant("email", "text")
    assert len(results) == 0
    path.unlink()


def test_returns_empty_when_file_missing():
    retriever = LearnedRuleRetriever(learned_path=Path("/does/not/exist.json"))
    results = retriever.find_relevant("any_col", "text")
    assert results == []


def test_has_correction_for():
    path = _make_learned_file([{
        "source_column": "ts",
        "target_column": "TS",
        "source_type": "timestamp",
        "target_type": "VARCHAR",
        "correct_rule": "text",
        "reason": "",
    }])
    retriever = LearnedRuleRetriever(learned_path=path)
    assert retriever.has_correction_for("ts", "TS") is True
    assert retriever.has_correction_for("ts", "SOMETHING_ELSE") is False
    path.unlink()


if __name__ == "__main__":
    test_finds_by_exact_name()
    test_returns_empty_when_no_match()
    test_returns_empty_when_file_missing()
    test_has_correction_for()
    print("All retrieval tests passed.")
