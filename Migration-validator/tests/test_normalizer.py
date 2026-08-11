"""
Tests for matching/normalizer.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from matching.normalizer import normalize_column_name, are_normalized_equal


def test_lowercase():
    assert normalize_column_name("CREATED_AT") == "createdat"


def test_strip_underscore():
    assert normalize_column_name("created_at") == "createdat"


def test_strip_hyphen():
    assert normalize_column_name("created-at") == "createdat"


def test_camel_case():
    assert normalize_column_name("createdAt") == "createdat"


def test_empty():
    assert normalize_column_name("") == ""


def test_already_normalized():
    assert normalize_column_name("createdat") == "createdat"


def test_are_normalized_equal_different_forms():
    assert are_normalized_equal("created_at", "CREATEDAT") is True
    assert are_normalized_equal("createdAt", "created-at") is True


def test_are_normalized_equal_different_names():
    assert are_normalized_equal("user_id", "account_id") is False


def test_special_characters_stripped():
    assert normalize_column_name("col!@#$name") == "colname"


if __name__ == "__main__":
    test_lowercase()
    test_strip_underscore()
    test_strip_hyphen()
    test_camel_case()
    test_empty()
    test_already_normalized()
    test_are_normalized_equal_different_forms()
    test_are_normalized_equal_different_names()
    test_special_characters_stripped()
    print("All normalizer tests passed.")
