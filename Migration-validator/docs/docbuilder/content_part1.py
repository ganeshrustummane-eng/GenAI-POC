"""Content sections 1-8 of the Migration Validator documentation."""
import os
from .style import (
    add_heading, add_body, add_bullet, add_number, add_code,
    add_callout, add_table, add_image, page_break,
)

ASSETS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")


def _img(name):
    return os.path.join(ASSETS, name)


def build_part_one(doc):
    # ---------- 1. Overview ----------
    add_heading(doc, "1. What This Tool Does", 1)
    add_body(doc,
        "The **Migration Validator** compares data between a source database and Snowflake after a "
        "migration to confirm that the data landed correctly. It provides a repeatable, automated "
        "mechanism for verifying data integrity across heterogeneous database platforms, eliminating "
        "manual spot-checks and reducing the risk of silent data corruption during migration.")
    add_body(doc,
        "Given a source table (PostgreSQL, MSSQL, or Athena) and a Snowflake target table, the tool "
        "performs the following operations end-to-end:")
    add_number(doc, "Extracts column schemas from both the source and target databases.")
    add_number(doc, "Matches source columns to target columns using a three-tier cascade: exact, then fuzzy, then AI.")
    add_number(doc, "Assigns a transformation rule to each column pair (for example, casting a boolean to '1'/'0', or normalizing timestamps to a UTC string).")
    add_number(doc, "Generates validation SQL queries that produce comparable, normalized output from both sides.")
    add_number(doc, "Writes those queries into YAML files that are ready for an automated validation runner.")

    add_image(doc, _img("pipeline.png"),
              "Figure 1 — End-to-end pipeline from schema extraction to YAML suite generation.")

    add_heading(doc, "The Core Idea", 2)
    add_body(doc,
        "The central design principle is to wrap every column in "
        "COALESCE(CAST(expr AS TEXT), '<<NULL>>') on both sides, then compare the results. In SQL, "
        "the expression NULL != NULL evaluates to unknown, which breaks straightforward equality "
        "comparisons. The '<<NULL>>' sentinel converts nulls into a concrete, comparable token so "
        "that null values on the source side correctly match null values on the target side.")
    add_image(doc, _img("null_sentinel.png"),
              "Figure 2 — The NULL sentinel normalization strategy makes nulls comparable across systems.")

    # ---------- 2. Project Structure ----------
    add_heading(doc, "2. Project Structure", 1)
    add_body(doc,
        "The repository is organized into a configuration layer, a source-code layer, and a "
        "documentation layer. The key top-level directories and files are summarized below.")
    add_table(doc,
        ["Path", "Purpose"],
        [
            [".env", "Your private credentials — never committed to version control."],
            [".env.example", "Template file; copy this to .env and fill in values."],
            ["config/bronze/", "YAML configuration for count and data validation suites."],
            ["src/ai/", "Prompt building, response parsing, and AI rule planning."],
            ["src/matching/", "Exact, fuzzy, and candidate column matchers with confidence scoring."],
            ["src/rules/", "Database-specific transformation rules (Athena, MSSQL, Postgres, Snowflake)."],
            ["src/dynamic_suite/", "Suite generation and query optimization logic."],
            ["src/batch/", "Batch runner, config parser, and manifest writer for multi-table runs."],
            ["src/generated_queries/", "SQL query generation and YAML config writing."],
            ["src/validate_cli.py", "Command-line entry point for running validations."],
        ])

    page_break(doc)

    # ---------- 3. Setup ----------
    add_heading(doc, "3. Setup — First Time", 1)
    add_body(doc,
        "Before running the tool for the first time, install the Python dependencies and configure "
        "your database credentials. The steps below assume a working Python 3 installation.")
    add_heading(doc, "3.1 Install Dependencies", 2)
    add_code(doc, "pip install -r requirements.txt")
    add_heading(doc, "3.2 Configure Credentials", 2)
    add_body(doc,
        "Copy the provided template to a private .env file and populate it with your source and "
        "target connection details:")
    add_code(doc, "cp .env.example .env\n# then edit .env with your credentials")
    add_callout(doc, "Security Note:",
        "The .env file contains sensitive credentials and must never be committed to version "
        "control. It is already listed in .gitignore.")

    # ---------- 4. Running the tool ----------
    add_heading(doc, "4. Running the Tool", 1)
    add_body(doc,
        "The primary entry point is the command-line interface. A single-table validation run "
        "extracts schemas, matches columns, assigns rules, and writes the resulting YAML suite.")
    add_code(doc,
        "python src/validate_cli.py \\\n"
        "  --source-table public.customers \\\n"
        "  --target-table BRONZE.CUSTOMERS \\\n"
        "  --source-type postgres")
    add_body(doc,
        "The tool prints progress for each stage and writes the generated validation suite to the "
        "configured output directory. Review the console output for any low-confidence matches that "
        "may require manual verification.")

    # ---------- 5. Column matching ----------
    add_heading(doc, "5. How Column Matching Works", 1)
    add_body(doc,
        "Column matching is performed as a prioritized cascade. Each source column is first tested "
        "for an exact match; if none is found, a fuzzy similarity match is attempted; and finally, "
        "for ambiguous or unmatched columns, an AI-based semantic match may be used.")
    add_image(doc, _img("matching.png"),
              "Figure 3 — The three-tier column matching cascade with confidence scoring.")
    add_bullet(doc, "**Exact match** — column names are normalized (case, underscores, whitespace) and compared directly. Highest confidence.")
    add_bullet(doc, "**Fuzzy match** — a string-similarity score is computed; matches above a configurable threshold are accepted.")
    add_bullet(doc, "**AI match** — a language model resolves semantic equivalence when names differ substantially. Used as a fallback.")
    add_body(doc,
        "Every matched pair carries a confidence score. Pairs below the configured threshold are "
        "flagged for human review rather than being silently accepted.")

    page_break(doc)

    # ---------- 6. How rules work ----------
    add_heading(doc, "6. How Rules Work", 1)
    add_body(doc,
        "A rule defines how a column's value is transformed into a normalized, comparable text form. "
        "Rules are database-specific because each engine has different casting semantics, date "
        "formats, and boolean representations. The rule engine selects the appropriate rule based on "
        "the source data type and the target data type.")
    add_table(doc,
        ["Rule Type", "Example Transformation"],
        [
            ["Boolean", "TRUE/FALSE  →  '1'/'0' text."],
            ["Timestamp", "Local timestamp  →  normalized UTC string."],
            ["Numeric", "Cast to text with consistent precision/scale."],
            ["Default", "COALESCE(CAST(expr AS TEXT), '<<NULL>>')."],
        ])
    add_body(doc,
        "Rules live under src/rules/, with one module per database engine. A shared base module "
        "captures common logic so that engine-specific modules only override what differs.")

    # ---------- 7. Adding a new rule ----------
    add_heading(doc, "7. How to Add a New Rule", 1)
    add_body(doc,
        "Extending the tool with a new transformation rule follows a consistent pattern. This keeps "
        "the rule catalog maintainable and ensures new rules are discoverable by the rule engine.")
    add_number(doc, "Identify the correct engine module under src/rules/ (for example, postgres_base_rules.py).")
    add_number(doc, "Add a rule function that accepts the column expression and returns normalized SQL text.")
    add_number(doc, "Register the rule so the rule engine can select it based on data type.")
    add_number(doc, "Add or update the entry in rules_catalog.json if the rule is catalog-driven.")
    add_number(doc, "Validate the output on a representative table before rolling it out broadly.")
    add_callout(doc, "Tip:",
        "Always return values wrapped with the NULL sentinel so new rules remain consistent with "
        "the framework's comparison strategy.")

    # ---------- 8. AI integration ----------
    add_heading(doc, "8. AI Integration", 1)
    add_body(doc,
        "AI is used in two complementary ways: to resolve ambiguous column matches and to recommend "
        "transformation rules for unusual data types. The AI layer under src/ai/ is composed of a "
        "prompt builder, a response parser, and a rule planner.")
    add_bullet(doc, "**Prompt Builder** — assembles structured prompts describing source and target schemas.")
    add_bullet(doc, "**Response Parser** — converts the model's response into structured match and rule decisions.")
    add_bullet(doc, "**Rule Planner** — plans which rules apply, using AI suggestions where static logic is insufficient.")
    add_body(doc,
        "AI decisions are always accompanied by confidence signals so that human reviewers can "
        "prioritize verification where it matters most.")

    page_break(doc)
