"""
Tests for matching/normalizer.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from matching.normalizer import normalize_column_name, are_normalized_equal


def test_lowercase():
    assert normalize_column_name("EMAIL") == "email"


def test_strips_underscores():
    assert normalize_column_name("created_at") == "createdat"


def test_strips_hyphens():
    assert normalize_column_name("created-at") == "createdat"


def test_camel_case_preserved_but_lowercased():
    assert normalize_column_name("createdAt") == "createdat"


def test_mixed_case_and_underscore():
    assert normalize_column_name("CREATED_AT") == "createdat"


def test_already_normalized():
    assert normalize_column_name("createdat") == "createdat"


def test_empty_string():
    assert normalize_column_name("") == ""


def test_only_special_chars_stripped():
    assert normalize_column_name("___") == ""


def test_special_characters_removed():
    # Spaces, dots, etc. stripped
    assert normalize_column_name("user.id") == "userid"


def test_numbers_preserved():
    assert normalize_column_name("col_1") == "col1"


def test_are_normalized_equal_same_after_normalize():
    assert are_normalized_equal("created_at", "CREATEDAT") is True
    assert are_normalized_equal("created_at", "CREATED_AT") is True
    assert are_normalized_equal("createdAt", "created-at") is True


def test_are_normalized_equal_different_names():
    assert are_normalized_equal("user_id", "tenant_id") is False


def test_are_normalized_equal_empty():
    assert are_normalized_equal("", "") is True


if __name__ == "__main__":
    test_lowercase()
    test_strips_underscores()
    test_strips_hyphens()
    test_camel_case_preserved_but_lowercased()
    test_mixed_case_and_underscore()
    test_already_normalized()
    test_empty_string()
    test_only_special_chars_stripped()
    test_special_characters_removed()
    test_numbers_preserved()
    test_are_normalized_equal_same_after_normalize()
    test_are_normalized_equal_different_names()
    test_are_normalized_equal_empty()
    print("All normalization tests passed.")
