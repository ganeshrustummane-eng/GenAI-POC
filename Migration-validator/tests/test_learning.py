"""
Tests for learning/retrieval.py and learning/feedback.py
"""
import sys
import os
import json
import tempfile
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from learning.retrieval import LearnedRuleRetriever
from learning.feedback import FeedbackRecorder, MismatchFeedback


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_learned_file(entries):
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump({"learned_corrections": entries}, tmp)
    tmp.close()
    return Path(tmp.name)


def _entry_dict(src="created_at", tgt="CREATEDAT", pg_type="timestamp",
                sf_type="VARCHAR", rule="text", reason=""):
    return {
        "source_column": src,
        "target_column": tgt,
        "source_type": pg_type,
        "target_type": sf_type,
        "correct_rule": rule,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# LearnedRuleRetriever
# ---------------------------------------------------------------------------

def test_finds_by_exact_name():
    path = _make_learned_file([_entry_dict("created_at", "CREATEDAT", rule="text")])
    retriever = LearnedRuleRetriever(learned_path=path)
    results = retriever.find_relevant("created_at", "timestamp")
    assert len(results) == 1
    assert results[0].correct_rule == "text"
    path.unlink()


def test_returns_empty_when_no_match():
    path = _make_learned_file([_entry_dict("user_id", "USER_ID", rule="integer")])
    retriever = LearnedRuleRetriever(learned_path=path)
    results = retriever.find_relevant("email", "text")
    assert results == []
    path.unlink()


def test_returns_empty_when_file_missing():
    retriever = LearnedRuleRetriever(learned_path=Path("/does/not/exist.json"))
    results = retriever.find_relevant("any_col", "text")
    assert results == []


def test_has_correction_for_true():
    path = _make_learned_file([_entry_dict("ts", "TS", rule="text")])
    retriever = LearnedRuleRetriever(learned_path=path)
    assert retriever.has_correction_for("ts", "TS") is True
    path.unlink()


def test_has_correction_for_false():
    path = _make_learned_file([_entry_dict("ts", "TS", rule="text")])
    retriever = LearnedRuleRetriever(learned_path=path)
    assert retriever.has_correction_for("ts", "SOMETHING_ELSE") is False
    path.unlink()


def test_case_insensitive_has_correction():
    path = _make_learned_file([_entry_dict("CREATED_AT", "CREATEDAT")])
    retriever = LearnedRuleRetriever(learned_path=path)
    assert retriever.has_correction_for("created_at", "createdat") is True
    path.unlink()


def test_multiple_entries_returns_best_first():
    path = _make_learned_file([
        _entry_dict("amount", "AMOUNT", rule="numeric"),
        _entry_dict("created_at", "CREATEDAT", rule="text"),
    ])
    retriever = LearnedRuleRetriever(learned_path=path)
    results = retriever.find_relevant("created_at", "timestamp")
    assert any(r.correct_rule == "text" for r in results)
    path.unlink()


# ---------------------------------------------------------------------------
# FeedbackRecorder
# ---------------------------------------------------------------------------

def test_record_creates_entry():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)
    path.unlink()  # Remove so recorder starts fresh

    recorder = FeedbackRecorder(learned_path=path)
    fb = MismatchFeedback(
        source_column="created_at",
        target_column="CREATEDAT",
        source_type="timestamp",
        target_type="VARCHAR",
        correct_rule="text",
        reason="Fivetran serialized timestamp",
        table_name="events",
    )
    success = recorder.record(fb)
    assert success is True

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["learned_corrections"]) == 1
    assert data["learned_corrections"][0]["source_column"] == "created_at"
    path.unlink()


def test_record_deduplicates_same_pair():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)
    path.unlink()

    recorder = FeedbackRecorder(learned_path=path)
    fb = MismatchFeedback(
        source_column="created_at", target_column="CREATEDAT",
        source_type="timestamp", target_type="VARCHAR",
        correct_rule="text", reason="first", table_name="t1",
    )
    recorder.record(fb)
    fb2 = MismatchFeedback(
        source_column="created_at", target_column="CREATEDAT",
        source_type="timestamp", target_type="VARCHAR",
        correct_rule="timestamp_ntz", reason="corrected", table_name="t1",
    )
    recorder.record(fb2)

    data = json.loads(path.read_text(encoding="utf-8"))
    # Should only have one entry for this pair
    assert len(data["learned_corrections"]) == 1
    assert data["learned_corrections"][0]["correct_rule"] == "timestamp_ntz"
    path.unlink()


def test_record_batch_returns_count():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)
    path.unlink()

    recorder = FeedbackRecorder(learned_path=path)
    feedbacks = [
        MismatchFeedback("a", "A", "text", "TEXT", "text"),
        MismatchFeedback("b", "B", "integer", "NUMBER", "integer"),
    ]
    count = recorder.record_batch(feedbacks)
    assert count == 2
    path.unlink()


def test_record_preserves_existing_entries():
    existing = {"learned_corrections": [_entry_dict("existing_col", "EXISTING_COL")]}
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(existing, f)
        path = Path(f.name)

    recorder = FeedbackRecorder(learned_path=path)
    fb = MismatchFeedback("new_col", "NEW_COL", "text", "TEXT", "text")
    recorder.record(fb)

    data = json.loads(path.read_text(encoding="utf-8"))
    names = [e["source_column"] for e in data["learned_corrections"]]
    assert "existing_col" in names
    assert "new_col" in names
    path.unlink()


def test_mismatch_feedback_defaults():
    fb = MismatchFeedback(
        source_column="col", target_column="COL",
        source_type="text", target_type="TEXT", correct_rule="text",
    )
    assert fb.reason == ""
    assert fb.table_name == ""
    assert fb.was_ai_decision is False


if __name__ == "__main__":
    test_finds_by_exact_name()
    test_returns_empty_when_no_match()
    test_returns_empty_when_file_missing()
    test_has_correction_for_true()
    test_has_correction_for_false()
    test_case_insensitive_has_correction()
    test_multiple_entries_returns_best_first()
    test_record_creates_entry()
    test_record_deduplicates_same_pair()
    test_record_batch_returns_count()
    test_record_preserves_existing_entries()
    test_mismatch_feedback_defaults()
    print("All learning tests passed.")
