"""
Tests for matching/confidence.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sql_extractor.base_extractor import ColumnMetadata
from matching.confidence import ConfidenceScorer


def _col(name, dtype="text", pos=1):
    return ColumnMetadata(
        ordinal_position=pos,
        column_name=name,
        data_type=dtype,
        is_nullable=True,
    )


def test_high_name_similarity_high_score():
    scorer = ConfidenceScorer()
    bd = scorer.score(
        source_col=_col("created_at", "timestamp without time zone", pos=5),
        target_col=_col("CREATEDAT", "TIMESTAMP_NTZ", pos=5),
        fuzzy_score=0.96,
        total_columns=10,
        has_learned_example=False,
    )
    assert bd.final_score > 0.8


def test_low_name_similarity_low_score():
    scorer = ConfidenceScorer()
    bd = scorer.score(
        source_col=_col("user_id", "integer", pos=1),
        target_col=_col("PRODUCT_NAME", "TEXT", pos=50),
        fuzzy_score=0.35,
        total_columns=100,
        has_learned_example=False,
    )
    assert bd.final_score < 0.6


def test_learned_example_boosts_score():
    scorer = ConfidenceScorer()
    bd_no_learn = scorer.score(
        source_col=_col("amount", "numeric", pos=3),
        target_col=_col("AMOUNT", "NUMBER", pos=3),
        fuzzy_score=0.9,
        total_columns=10,
        has_learned_example=False,
    )
    bd_with_learn = scorer.score(
        source_col=_col("amount", "numeric", pos=3),
        target_col=_col("AMOUNT", "NUMBER", pos=3),
        fuzzy_score=0.9,
        total_columns=10,
        has_learned_example=True,
    )
    assert bd_with_learn.final_score >= bd_no_learn.final_score


def test_compatible_types_boost():
    scorer = ConfidenceScorer()
    # boolean→BOOLEAN is a well-known pair (high type compatibility)
    bd = scorer.score(
        source_col=_col("is_active", "boolean", pos=1),
        target_col=_col("IS_ACTIVE", "BOOLEAN", pos=1),
        fuzzy_score=1.0,
        total_columns=5,
        has_learned_example=False,
    )
    assert bd.type_compatibility > 0.9


def test_score_in_valid_range():
    scorer = ConfidenceScorer()
    bd = scorer.score(
        source_col=_col("x", "jsonb", pos=100),
        target_col=_col("Y", "VARCHAR", pos=1),
        fuzzy_score=0.5,
        total_columns=200,
        has_learned_example=False,
    )
    assert 0.0 <= bd.final_score <= 1.0


if __name__ == "__main__":
    test_high_name_similarity_high_score()
    test_low_name_similarity_low_score()
    test_learned_example_boosts_score()
    test_compatible_types_boost()
    test_score_in_valid_range()
    print("All confidence scorer tests passed.")
