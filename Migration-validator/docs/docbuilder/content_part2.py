"""Content sections 9-16 of the Migration Validator documentation."""
import os
from .style import (
    add_heading, add_body, add_bullet, add_number, add_code,
    add_callout, add_table, add_image, page_break,
)

ASSETS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")


def _img(name):
    return os.path.join(ASSETS, name)


def build_part_two(doc):
    # ---------- 9. Output ----------
    add_heading(doc, "9. Output — What Gets Generated", 1)
    add_body(doc,
        "The primary output of the tool is a set of validation YAML suites. Each suite contains the "
        "normalized SQL for both source and target sides, along with metadata describing the "
        "matched columns and the rules applied to each. These suites are consumed by an automated "
        "validation runner that executes the queries and compares results.")
    add_bullet(doc, "**Data validation suites** — per-column normalized comparison queries.")
    add_bullet(doc, "**Count validation suites** — row-count checks between source and target.")
    add_bullet(doc, "**Manifest** — an index of all generated suites for a batch run.")

    # ---------- 10. Batch mode ----------
    add_heading(doc, "10. Batch Mode (Multiple Tables)", 1)
    add_body(doc,
        "For migrations spanning many tables, batch mode processes a list of tables in a single run. "
        "A configuration file enumerates the source and target tables; the config parser reads it, "
        "and the batch runner iterates over each entry, generating suites and recording a manifest.")
    add_image(doc, _img("batch.png"),
              "Figure 4 — Batch mode processes multiple tables and produces a consolidated manifest.")
    add_body(doc,
        "Batch mode is the recommended approach for production migrations because it guarantees "
        "consistent configuration across tables and produces a single manifest for traceability.")

    # ---------- 11. YAML config ----------
    add_heading(doc, "11. The YAML Config Files Explained", 1)
    add_body(doc,
        "Configuration files under config/bronze/ define both count and data validation suites. "
        "They are human-readable and version-controlled, making validation logic auditable and "
        "reproducible.")
    add_table(doc,
        ["Config Type", "Location", "Purpose"],
        [
            ["Count validation", "config/bronze/count_validation/", "Row-count parity checks."],
            ["Data validation", "config/bronze/data_validation/", "Column-level value comparisons."],
            ["Dynamic suites", "*_dynamic_suite.yaml", "Auto-generated, optimized query suites."],
        ])
    add_body(doc,
        "A typical data-validation entry declares the source and target expressions, the applied "
        "rule, and any thresholds that govern acceptable mismatch rates.")

    page_break(doc)

    # ---------- 12. Fuzzy match & thresholds ----------
    add_heading(doc, "12. Fuzzy Match & Failure Thresholds", 1)
    add_body(doc,
        "Two categories of thresholds control the tool's behavior. Match thresholds decide whether a "
        "fuzzy column match is accepted automatically, while failure thresholds decide whether a "
        "validation result is considered a pass or a failure.")
    add_bullet(doc, "**Match threshold** — the minimum similarity score for an automatic fuzzy match. Below this, the pair is flagged for review.")
    add_bullet(doc, "**Failure threshold** — the maximum tolerated mismatch rate before a validation is marked as failed.")
    add_callout(doc, "Guidance:",
        "Start with conservative thresholds and relax them only after reviewing real mismatch "
        "patterns. Overly permissive thresholds can mask genuine data issues.")

    # ---------- 13. Static exclusion list ----------
    add_heading(doc, "13. Static Column Exclusion List", 1)
    add_body(doc,
        "Some columns should never participate in validation — for example, audit timestamps, "
        "surrogate keys regenerated on load, or system-managed metadata. The static exclusion list "
        "lets you declare these columns so they are skipped consistently across runs.")
    add_number(doc, "Add the column name to the exclusion configuration.")
    add_number(doc, "Re-run generation; excluded columns are omitted from the produced suites.")
    add_number(doc, "Document why each column is excluded to preserve institutional knowledge.")

    # ---------- 14. Common workflows ----------
    add_heading(doc, "14. Common Workflows", 1)
    add_heading(doc, "14.1 Validate a Single Table", 2)
    add_body(doc, "Run the CLI with the source and target table names to generate and inspect one suite.")
    add_heading(doc, "14.2 Validate a Full Schema", 2)
    add_body(doc, "Populate a batch config with all tables, then run batch mode to produce a complete manifest.")
    add_heading(doc, "14.3 Re-run After a Fix", 2)
    add_body(doc, "After correcting a rule or exclusion, regenerate only the affected suites and re-validate.")

    page_break(doc)

    # ---------- 15. Environment variables ----------
    add_heading(doc, "15. Environment Variables Reference", 1)
    add_body(doc,
        "All connection and behavioral settings are supplied through environment variables loaded "
        "from the .env file. The table below lists the most important variables.")
    add_table(doc,
        ["Variable", "Description"],
        [
            ["SOURCE_DB_HOST", "Hostname of the source database."],
            ["SOURCE_DB_USER", "Source database username."],
            ["SOURCE_DB_PASSWORD", "Source database password."],
            ["SNOWFLAKE_ACCOUNT", "Snowflake account identifier."],
            ["SNOWFLAKE_USER", "Snowflake username."],
            ["SNOWFLAKE_PASSWORD", "Snowflake password."],
            ["AI_API_KEY", "API key for the AI matching/rule service."],
        ])

    # ---------- 16. Key design decisions ----------
    add_heading(doc, "16. Key Design Decisions", 1)
    add_body(doc,
        "The following decisions shape the architecture and are important context for anyone "
        "extending the tool.")
    add_bullet(doc, "**Text normalization for comparison** — all values are cast to text and null-guarded so that comparisons are engine-agnostic.")
    add_bullet(doc, "**Cascade matching** — deterministic exact and fuzzy matching are preferred over AI, which is reserved for genuinely ambiguous cases.")
    add_bullet(doc, "**Config as code** — validation logic lives in version-controlled YAML for auditability and reproducibility.")
    add_bullet(doc, "**Engine-specific rules** — casting and formatting differences are isolated per database engine to keep logic clear.")
    add_bullet(doc, "**Confidence everywhere** — every automated decision carries a confidence signal to guide human review.")

    add_callout(doc, "Handover Summary:",
        "You now have the full picture: how the tool extracts, matches, transforms, generates, and "
        "validates. Start with a single-table run to build intuition, then scale to batch mode for "
        "production migrations.")
