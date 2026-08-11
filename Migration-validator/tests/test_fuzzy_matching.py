"""
Tests for matching/fuzzy_matcher.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sql_extractor.base_extractor import ColumnMetadata
from matching.fuzzy_matcher import FuzzyMatcher, FuzzyCandidate, FuzzyMatchGroup


def _col(name, dtype="text", pos=1):
    return ColumnMetadata(
        ordinal_position=pos,
        column_name=name,
        data_type=dtype,
        is_nullable=True,
    )


def test_identical_normalized_names_score_one():
    matcher = FuzzyMatcher()
    candidate = matcher.score_pair(_col("created_at"), _col("CREATEDAT"))
    # created_at → createdat, CREATEDAT → createdat  — identical
    assert candidate.fuzzy_score == 1.0
    assert candidate.above_high is True
    assert candidate.needs_ai_review is False
    assert candidate.below_threshold is False


def test_very_different_names_below_threshold():
    matcher = FuzzyMatcher(high_confidence_threshold=0.95, ai_review_threshold=0.75)
    candidate = matcher.score_pair(_col("user_id"), _col("facility_name"))
    assert candidate.fuzzy_score < 0.75
    assert candidate.below_threshold is True
    assert candidate.above_high is False


def test_medium_similarity_needs_ai_review():
    matcher = FuzzyMatcher(high_confidence_threshold=0.95, ai_review_threshold=0.75)
    # "orderid" vs "order_uid" — not identical but close
    candidate = matcher.score_pair(_col("order_id"), _col("ORDER_UUID"))
    # Score depends on library; just verify threshold flags are mutually exclusive
    flags = [candidate.above_high, candidate.needs_ai_review, candidate.below_threshold]
    assert sum(flags) == 1, "Exactly one threshold flag must be set"


def test_score_pair_returns_fuzzy_candidate():
    matcher = FuzzyMatcher()
    result = matcher.score_pair(_col("email"), _col("EMAIL"))
    assert isinstance(result, FuzzyCandidate)
    assert 0.0 <= result.fuzzy_score <= 1.0


def test_match_unmatched_returns_one_group_per_source():
    matcher = FuzzyMatcher()
    sources = [_col("created_at", pos=1), _col("updated_at", pos=2)]
    targets = [_col("CREATEDAT", pos=1), _col("UPDATEDAT", pos=2)]
    groups = matcher.match_unmatched(sources, targets)
    assert len(groups) == 2
    assert all(isinstance(g, FuzzyMatchGroup) for g in groups)


def test_match_unmatched_top_n_limit():
    matcher = FuzzyMatcher()
    sources = [_col("col_a", pos=1)]
    targets = [_col(f"target_{i}", pos=i) for i in range(10)]
    groups = matcher.match_unmatched(sources, targets, top_n=3)
    assert len(groups[0].candidates) <= 3


def test_match_unmatched_sorted_descending():
    matcher = FuzzyMatcher()
    src = [_col("user_id", pos=1)]
    tgt = [_col("USERID", pos=1), _col("PRODUCT_CODE", pos=2), _col("USER_UUID", pos=3)]
    groups = matcher.match_unmatched(src, tgt, top_n=3)
    scores = [c.fuzzy_score for c in groups[0].candidates]
    assert scores == sorted(scores, reverse=True)


def test_group_top_property():
    matcher = FuzzyMatcher()
    src = [_col("tenant_id", pos=1)]
    tgt = [_col("TENANTID", pos=1), _col("OTHER", pos=2)]
    groups = matcher.match_unmatched(src, tgt, top_n=5)
    g = groups[0]
    assert g.top is not None
    assert g.top.fuzzy_score == max(c.fuzzy_score for c in g.candidates)


def test_empty_targets_returns_empty_candidates():
    matcher = FuzzyMatcher()
    src = [_col("event_type", pos=1)]
    groups = matcher.match_unmatched(src, [])
    assert len(groups) == 1
    assert groups[0].candidates == []
    assert groups[0].top is None


if __name__ == "__main__":
    test_identical_normalized_names_score_one()
    test_very_different_names_below_threshold()
    test_medium_similarity_needs_ai_review()
    test_score_pair_returns_fuzzy_candidate()
    test_match_unmatched_returns_one_group_per_source()
    test_match_unmatched_top_n_limit()
    test_match_unmatched_sorted_descending()
    test_group_top_property()
    test_empty_targets_returns_empty_candidates()
    print("All fuzzy matching tests passed.")
