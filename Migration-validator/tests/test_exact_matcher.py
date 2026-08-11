"""
Tests for matching/exact_matcher.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sql_extractor.base_extractor import ColumnMetadata
from matching.exact_matcher import ExactMatcher


def _col(name, dtype="text", pos=1):
    return ColumnMetadata(
        ordinal_position=pos,
        column_name=name,
        data_type=dtype,
        is_nullable=True,
    )


def test_exact_case_insensitive():
    matcher = ExactMatcher()
    src = [_col("user_id", pos=1), _col("email", pos=2)]
    tgt = [_col("USER_ID", pos=1), _col("EMAIL", pos=2)]
    matched, unmatched_tgt = matcher.match_all(src, tgt)

    assert len([r for r in matched if r.matched]) == 2
    assert not unmatched_tgt


def test_normalized_name_match():
    matcher = ExactMatcher()
    src = [_col("created_at", pos=1)]
    tgt = [_col("CREATEDAT", pos=1)]
    matched, unmatched = matcher.match_all(src, tgt)

    assert matched[0].matched
    assert matched[0].method == "normalized_exact"


def test_no_match_returned_correctly():
    matcher = ExactMatcher()
    src = [_col("event_type", pos=1)]
    tgt = [_col("EVENTKIND", pos=1)]
    matched, unmatched = matcher.match_all(src, tgt)

    assert not matched[0].matched
    assert len(unmatched) == 1


def test_configured_override():
    matcher = ExactMatcher()
    src = [_col("src_col", pos=1)]
    tgt = [_col("TGT_COL", pos=1)]
    matched, unmatched = matcher.match_all(
        src, tgt, explicit_mappings={"src_col": "TGT_COL"}
    )
    assert matched[0].matched
    assert matched[0].method == "configured"


if __name__ == "__main__":
    test_exact_case_insensitive()
    test_normalized_name_match()
    test_no_match_returned_correctly()
    test_configured_override()
    print("All exact matcher tests passed.")
