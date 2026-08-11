"""
Tests for generated_queries/yaml_config_writer.py
"""
import sys
import os
import tempfile
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from generated_queries.yaml_config_writer import (
    YAMLConfigWriter,
    _strip_generator_header,
    _indent_for_yaml,
)
from generated_queries.sql_query_generator import SQLQueryGenerator
from ai_transformation.static_rule_mapper import ColumnRuleMapping
from rules import get_rule_for_type


def _mapping(src, tgt, pg_type="text", sf_type="TEXT"):
    return ColumnRuleMapping(
        source_column=src,
        target_column=tgt,
        source_type=pg_type,
        target_type=sf_type,
        rule=get_rule_for_type(pg_type, sf_type),
    )


def _make_query_set():
    gen = SQLQueryGenerator()
    return gen.generate(
        pg_schema="public",
        pg_table="events",
        sf_database="db",
        sf_schema="schema",
        sf_table="EVENTS",
        mappings=[_mapping("id", "ID", "integer", "NUMBER"),
                  _mapping("status", "STATUS")],
        has_fivetran_active=False,
    )


# ---------------------------------------------------------------------------
# _strip_generator_header
# ---------------------------------------------------------------------------

def test_strip_removes_first_comment_line():
    sql = "-- ③ SOURCE: PostgreSQL (public.events)\nSELECT 1;"
    result = _strip_generator_header(sql)
    assert result == "SELECT 1;"


def test_strip_preserves_body_comments():
    sql = "-- header\nSELECT\n-- inline comment\n1;"
    result = _strip_generator_header(sql)
    assert "-- inline comment" in result


def test_strip_empty_string():
    result = _strip_generator_header("")
    assert result == "SELECT 1;"


def test_strip_no_header_unchanged():
    sql = "SELECT COUNT(*) FROM public.events;"
    result = _strip_generator_header(sql)
    assert result == sql


# ---------------------------------------------------------------------------
# _indent_for_yaml
# ---------------------------------------------------------------------------

def test_indent_adds_spaces_to_every_line():
    sql = "SELECT 1;\nFROM table;"
    result = _indent_for_yaml(sql, indent=10)
    for line in result.splitlines():
        assert line.startswith(" " * 10)


def test_indent_zero():
    sql = "SELECT 1;"
    result = _indent_for_yaml(sql, indent=0)
    assert result == "SELECT 1;"


def test_indent_default_is_10():
    sql = "SELECT 1;"
    result = _indent_for_yaml(sql)
    assert result.startswith(" " * 10)


# ---------------------------------------------------------------------------
# YAMLConfigWriter.write
# ---------------------------------------------------------------------------

def test_write_creates_yaml_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = YAMLConfigWriter()
        qs = _make_query_set()
        path = writer.write(
            query_set=qs,
            pg_schema="public",
            pg_table="events",
            sf_database="db",
            sf_schema="schema",
            sf_table="EVENTS",
            mappings=[_mapping("id", "ID", "integer", "NUMBER")],
            has_fivetran_active=False,
            output_dir=Path(tmpdir),
        )
        assert path.exists()
        assert path.suffix == ".yaml"


def test_write_yaml_contains_all_four_validation_blocks():
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = YAMLConfigWriter()
        qs = _make_query_set()
        path = writer.write(
            query_set=qs,
            pg_schema="public",
            pg_table="events",
            sf_database="db",
            sf_schema="schema",
            sf_table="EVENTS",
            mappings=[_mapping("id", "ID", "integer", "NUMBER")],
            has_fivetran_active=False,
            output_dir=Path(tmpdir),
        )
        content = path.read_text(encoding="utf-8")
        assert "row_count_validation:" in content
        assert "data_validation:" in content
        assert "null_pct_validation:" in content
        assert "distinct_count_validation:" in content


def test_write_yaml_includes_fivetran_comment_when_active():
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = YAMLConfigWriter()
        qs = _make_query_set()
        path = writer.write(
            query_set=qs,
            pg_schema="public",
            pg_table="events",
            sf_database="db",
            sf_schema="schema",
            sf_table="EVENTS",
            mappings=[_mapping("id", "ID", "integer", "NUMBER")],
            has_fivetran_active=True,
            output_dir=Path(tmpdir),
        )
        content = path.read_text(encoding="utf-8")
        assert "_FIVETRAN_ACTIVE" in content


def test_write_yaml_has_correct_table_names():
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = YAMLConfigWriter()
        qs = _make_query_set()
        path = writer.write(
            query_set=qs,
            pg_schema="public",
            pg_table="events",
            sf_database="db",
            sf_schema="schema",
            sf_table="EVENTS",
            mappings=[_mapping("id", "ID", "integer", "NUMBER")],
            has_fivetran_active=False,
            output_dir=Path(tmpdir),
        )
        content = path.read_text(encoding="utf-8")
        assert "source_table_name: events" in content
        assert "target_table_name: EVENTS" in content


if __name__ == "__main__":
    test_strip_removes_first_comment_line()
    test_strip_preserves_body_comments()
    test_strip_empty_string()
    test_strip_no_header_unchanged()
    test_indent_adds_spaces_to_every_line()
    test_indent_zero()
    test_indent_default_is_10()
    test_write_creates_yaml_file()
    test_write_yaml_contains_all_four_validation_blocks()
    test_write_yaml_includes_fivetran_comment_when_active()
    test_write_yaml_has_correct_table_names()
    print("All YAML generation tests passed.")
