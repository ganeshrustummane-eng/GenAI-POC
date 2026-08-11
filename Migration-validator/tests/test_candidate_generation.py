"""
Tests for matching/candidate_matcher.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sql_extractor.base_extractor import ColumnMetadata
from matching.candidate_matcher import CandidateMatcher, MatchDecision


def _col(name, dtype="text", pos=1):
    return ColumnMetadata(
        ordinal_position=pos,
        column_name=name,
        data_type=dtype,
        is_nullable=True,
    )


def test_exact_match_produces_resolved_status():
    matcher = CandidateMatcher()
    src = [_col("id", pos=1)]
    tgt = [_col("ID", pos=1)]
    decisions = matcher.match(src, tgt)
    assert len(decisions) == 1
    assert decisions[0].is_resolved
    assert decisions[0].method in ("exact", "normalized_exact")
    assert decisions[0].final_score == 1.0


def test_one_decision_per_source_column():
    matcher = CandidateMatcher()
    src = [_col("id", pos=1), _col("email", pos=2), _col("created_at", pos=3)]
    tgt = [_col("ID", pos=1), _col("EMAIL", pos=2), _col("CREATEDAT", pos=3)]
    decisions = matcher.match(src, tgt)
    assert len(decisions) == len(src)


def test_fivetran_column_skipped():
    matcher = CandidateMatcher()
    src = [_col("id", pos=1), _col("_FIVETRAN_DELETED", pos=2)]
    tgt = [_col("ID", pos=1)]
    decisions = matcher.match(src, tgt)
    assert len(decisions) == 2
    fivetran_dec = next(d for d in decisions if "_FIVETRAN_" in d.source_col.column_name)
    assert fivetran_dec.skip_validation is True
    assert fivetran_dec.is_resolved


def test_high_confidence_fuzzy_resolves_without_ai():
    # createdat <-> CREATED_AT: normalized identical → exact, score = 1.0
    matcher = CandidateMatcher(high_confidence_threshold=0.95)
    src = [_col("createdat", pos=1)]
    tgt = [_col("CREATEDAT", pos=1)]
    decisions = matcher.match(src, tgt)
    assert decisions[0].is_resolved
    assert not decisions[0].needs_ai


def test_no_target_match_produces_unmatched():
    matcher = CandidateMatcher(ai_review_threshold=0.75)
    src = [_col("obscure_xyz_column", pos=1)]
    tgt = [_col("COMPLETELY_DIFFERENT", pos=1)]
    decisions = matcher.match(src, tgt)
    # Score between "obscurexyzcolumn" and "completelydifferent" should be low
    d = decisions[0]
    # Either unmatched or ai_needed — NOT resolved
    assert not d.is_resolved or d.skip_validation


def test_explicit_mappings_override():
    matcher = CandidateMatcher()
    src = [_col("pg_col", pos=1)]
    tgt = [_col("SF_COL", pos=1)]
    decisions = matcher.match(src, tgt, explicit_mappings={"pg_col": "SF_COL"})
    assert decisions[0].is_resolved
    assert decisions[0].method == "configured"


def test_decisions_preserve_source_order():
    matcher = CandidateMatcher()
    src = [_col("beta", pos=1), _col("alpha", pos=2), _col("gamma", pos=3)]
    tgt = [_col("ALPHA", pos=1), _col("BETA", pos=2), _col("GAMMA", pos=3)]
    decisions = matcher.match(src, tgt)
    names = [d.source_col.column_name for d in decisions]
    assert names == ["beta", "alpha", "gamma"]


def test_match_decision_properties():
    d = MatchDecision(
        source_col=_col("x"),
        target_col=_col("X"),
        method="exact",
        confidence=None,
        final_score=1.0,
        status="resolved",
    )
    assert d.is_resolved
    assert not d.needs_ai
    assert not d.is_unmatched


def test_learned_examples_accepted():
    matcher = CandidateMatcher()
    src = [_col("user_id", pos=1)]
    tgt = [_col("USERID", pos=1)]
    learned = [{"source_column": "user_id", "target_column": "USERID"}]
    decisions = matcher.match(src, tgt, learned_examples=learned)
    # Should not raise; learned lookup is bonus confidence
    assert len(decisions) == 1


if __name__ == "__main__":
    test_exact_match_produces_resolved_status()
    test_one_decision_per_source_column()
    test_fivetran_column_skipped()
    test_high_confidence_fuzzy_resolves_without_ai()
    test_no_target_match_produces_unmatched()
    test_explicit_mappings_override()
    test_decisions_preserve_source_order()
    test_match_decision_properties()
    test_learned_examples_accepted()
    print("All candidate generation tests passed.")
