"""
AI CLI — command-line interface for the Migration Validator AI agent.

Commands
--------
  discover   Print schema introspection queries to run manually in your SQL client.
  generate   Generate validation SQL queries using AI (or static fallback).

Examples
--------
  # Step 1: Get the introspection query to run on your source DB
  python ai_cli.py discover --source-type postgresql --schema source_data --table users

  # Step 1b: Same for Snowflake target
  python ai_cli.py discover --source-type snowflake --schema TARGET_SCHEMA --table USERS --database SNOWFLAKE_DB

  # Step 2: Run those queries in your SQL client and save the JSON output.
  #         Then generate the validation plan:
  python ai_cli.py generate \\
      --source-type postgresql --source-schema source_data --source-table users \\
      --target-type snowflake  --target-schema TARGET_SCHEMA --target-table USERS \\
      --target-database SNOWFLAKE_DB \\
      --source-schema-file source_users_schema.json \\
      --target-schema-file target_users_schema.json \\
      --pk user_id

  # Step 2b: Or provide schema inline via --columns (quick mode)
  python ai_cli.py generate \\
      --source-type postgresql --source-schema source_data --source-table users \\
      --target-type snowflake  --target-schema TARGET_SCHEMA --target-table USERS \\
      --target-database SNOWFLAKE_DB \\
      --columns "user_id:SERIAL:NUMBER,username:VARCHAR(100):VARCHAR,is_active:BOOLEAN:BOOLEAN" \\
      --pk user_id
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from models import DatabaseType
from schema_discovery import (
    get_schema_introspection_query,
    get_table_list_query,
    parse_column_info_from_json,
    column_info_to_dict,
)
from ai_query_agent import AIQueryAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DB_TYPE_MAP = {
    "postgresql": DatabaseType.POSTGRESQL,
    "postgres":   DatabaseType.POSTGRESQL,
    "pg":         DatabaseType.POSTGRESQL,
    "mssql":      DatabaseType.MSSQL,
    "sqlserver":  DatabaseType.MSSQL,
    "snowflake":  DatabaseType.SNOWFLAKE,
    "sf":         DatabaseType.SNOWFLAKE,
}


def _parse_db_type(value: str) -> DatabaseType:
    key = value.strip().lower()
    if key not in _DB_TYPE_MAP:
        raise click.BadParameter(
            f"Unknown DB type '{value}'. Choose from: postgresql, mssql, snowflake"
        )
    return _DB_TYPE_MAP[key]


def _parse_columns_inline(columns_str: str) -> List[Dict[str, Any]]:
    """
    Parse '--columns' shorthand:  col1:SRC_TYPE:TGT_TYPE,col2:...

    Commas inside parentheses (e.g. NUMERIC(12,2)) are ignored as delimiters
    so type modifiers survive intact.
    """
    # Split on commas that are NOT inside parentheses
    import re as _re
    parts = _re.split(r',(?![^(]*\))', columns_str)
    results = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Split on ':' but not inside parentheses
        segments = _re.split(r':(?![^(]*\))', part)
        if len(segments) < 2:
            raise click.BadParameter(
                f"Column spec '{part}' must be 'name:source_type' or 'name:source_type:target_type'"
            )
        name = segments[0].strip()
        src_type = segments[1].strip()
        tgt_type = segments[2].strip() if len(segments) > 2 else src_type
        results.append({"name": name, "src_type": src_type, "tgt_type": tgt_type})
    return results


def _load_schema_file(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    cols = parse_column_info_from_json(data)
    return [column_info_to_dict(c) for c in cols]


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """Migration Validator AI Agent — generates SQL validation queries."""


# ---------------------------------------------------------------------------
# discover command
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--source-type", "-t", required=True,
              help="DB type: postgresql | mssql | snowflake")
@click.option("--schema", "-s", required=True,
              help="Schema name to introspect")
@click.option("--table", "-T", default=None,
              help="Table name (omit to list all tables in schema)")
@click.option("--database", "-d", default=None,
              help="Database name (required for Snowflake)")
def discover(source_type, schema, table, database):
    """Print schema introspection SQL to run manually in your SQL client."""
    db_type = _parse_db_type(source_type)

    click.echo("\n" + "=" * 70)
    click.echo(f"  DISCOVER MODE  |  {db_type.value}.{schema}" + (f".{table}" if table else ""))
    click.echo("=" * 70)

    if not table:
        click.echo("\n[Step 1] Run this to list tables in the schema:\n")
        click.echo(get_table_list_query(db_type, schema, database))
        click.echo("\nThen re-run with --table <TABLE_NAME> for column introspection.")
        return

    click.echo("\n[Step 1] Run this introspection query on your DB:\n")
    click.echo(get_schema_introspection_query(db_type, schema, table, database))
    click.echo(
        "\n[Step 2] Export the result as JSON (list of row dicts) and save it, e.g.:\n"
        "  psql -c \"COPY (SELECT ...) TO STDOUT WITH CSV HEADER\"\n"
        "  or use your SQL client's JSON export feature.\n"
        "\n[Step 3] Run:\n"
        f"  python ai_cli.py generate \\\n"
        f"    --source-type {source_type} --source-schema {schema} --source-table {table} \\\n"
        f"    --target-type snowflake     --target-schema TARGET_SCHEMA --target-table {table.upper()} \\\n"
        f"    --target-database SNOWFLAKE_DB \\\n"
        f"    --source-schema-file {schema}_{table}_columns.json \\\n"
        f"    --target-schema-file target_{table}_columns.json\n"
    )


# ---------------------------------------------------------------------------
# generate command
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--source-type",    "-st", required=True,  help="Source DB type")
@click.option("--source-schema",  "-ss", required=True,  help="Source schema name")
@click.option("--source-table",   "-sT", required=True,  help="Source table name")
@click.option("--target-type",    "-tt", required=True,  help="Target DB type")
@click.option("--target-schema",  "-ts", required=True,  help="Target schema name")
@click.option("--target-table",   "-tT", required=True,  help="Target table name")
@click.option("--target-database","-td", default=None,   help="Target database (Snowflake)")
@click.option("--source-schema-file", "-sf", default=None,
              help="JSON file with source column metadata (output of introspection query)")
@click.option("--target-schema-file", "-tf", default=None,
              help="JSON file with target column metadata")
@click.option("--columns", "-c", default=None,
              help="Quick inline spec: col1:SRC_TYPE:TGT_TYPE,col2:... (alternative to --*-schema-file)")
@click.option("--pk", "-k", multiple=True,
              help="Primary key column name(s), e.g. --pk user_id --pk order_id")
@click.option("--output", "-o", default="console",
              type=click.Choice(["console", "json", "sql"]),
              help="Output format: console (default), json, sql")
@click.option("--output-file", "-O", default=None,
              help="Write output to this file instead of stdout")
@click.option("--model", "-m", default=None,
              help="Override DIAL deployment name (default: from DIAL_MODEL env or gpt-4o)")
def generate(
    source_type, source_schema, source_table,
    target_type, target_schema, target_table, target_database,
    source_schema_file, target_schema_file,
    columns, pk, output, output_file, model,
):
    """Generate AI-powered validation SQL for a source → target table pair."""

    src_db_type = _parse_db_type(source_type)
    tgt_db_type = _parse_db_type(target_type)

    # ---------- Build column lists ----------
    if columns:
        # Inline quick mode
        inline_cols = _parse_columns_inline(columns)
        source_columns = [
            {"column_name": c["name"], "data_type": c["src_type"],
             "is_nullable": True, "ordinal_position": i}
            for i, c in enumerate(inline_cols, 1)
        ]
        target_columns = [
            {"column_name": c["name"].upper(), "data_type": c["tgt_type"],
             "is_nullable": True, "ordinal_position": i}
            for i, c in enumerate(inline_cols, 1)
        ]
    elif source_schema_file and target_schema_file:
        source_columns = _load_schema_file(source_schema_file)
        target_columns = _load_schema_file(target_schema_file)
    elif source_schema_file:
        # Only source provided — use same columns for target (1:1 mapping assumption)
        source_columns = _load_schema_file(source_schema_file)
        target_columns = [
            {**c, "column_name": c["column_name"].upper()}
            for c in source_columns
        ]
    else:
        click.echo(
            "ERROR: provide either --columns or --source-schema-file "
            "(optionally --target-schema-file).",
            err=True,
        )
        sys.exit(1)

    # ---------- Run agent ----------
    agent = AIQueryAgent(model=model)
    plan = agent.generate_validation_plan(
        source_db_type=src_db_type,
        source_schema=source_schema,
        source_table=source_table,
        source_columns=source_columns,
        target_db_type=tgt_db_type,
        target_schema=target_schema,
        target_table=target_table,
        target_columns=target_columns,
        target_database=target_database,
        primary_key_hints=list(pk),
    )

    # ---------- Output ----------
    out_content = _format_output(plan, output)

    if output_file:
        Path(output_file).write_text(out_content, encoding="utf-8")
        click.echo(f"Output written to: {output_file}")
    else:
        click.echo(out_content)


def _format_output(plan, fmt: str) -> str:
    if fmt == "json":
        return json.dumps({
            "generated_by": plan.generated_by,
            "source": f"{plan.source_db_type.value}.{plan.source_schema}.{plan.source_table}",
            "target": f"{plan.target_db_type.value}.{plan.target_schema}.{plan.target_table}",
            "explanation": plan.explanation,
            "column_mappings": [
                {
                    "source_column": cm.source_column,
                    "target_column": cm.target_column,
                    "source_data_type": cm.source_data_type,
                    "target_data_type": cm.target_data_type,
                    "primary_key": cm.primary_key,
                    "ignore_validation": cm.ignore_validation,
                    "apply_rules": [r.value for r in cm.apply_rules],
                }
                for cm in plan.column_mappings
            ],
            "source_sql": plan.source_sql,
            "target_sql": plan.target_sql,
        }, indent=2)

    if fmt == "sql":
        sep = "-- " + "=" * 66
        return (
            f"{sep}\n-- SOURCE ({plan.source_db_type.value}): "
            f"{plan.source_schema}.{plan.source_table}\n{sep}\n"
            f"{plan.source_sql}\n\n"
            f"{sep}\n-- TARGET ({plan.target_db_type.value}): "
            f"{plan.target_schema}.{plan.target_table}\n{sep}\n"
            f"{plan.target_sql}"
        )

    # Default: console
    import io
    buf = io.StringIO()
    _original_stdout = sys.stdout
    sys.stdout = buf
    plan.print_summary()
    sys.stdout = _original_stdout
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Ensure src/ is on the path when run directly
    sys.path.insert(0, str(Path(__file__).parent))
    cli()
