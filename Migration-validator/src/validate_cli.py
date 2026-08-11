"""
╔══════════════════════════════════════════════════════════════════════╗
║   Migration Validator CLI  —  PostgreSQL → Snowflake                ║
║   Interactive + command-line interface                               ║
╚══════════════════════════════════════════════════════════════════════╝

Commands
--------
  generate      Full workflow: extract schema → assign rules → SQL + YAML
  rules         Show the full rule book (base + learned)
  add-rule      Add a new rule to the evolving rule book
  list-models   Show all available AI models
  list-tables   List tables in PostgreSQL and Snowflake
  help / (none) Interactive menu

Usage
-----
  cd src
  python validate_cli.py                         ← interactive menu
  python validate_cli.py generate \\
      --pg-table events --sf-table EVENTS        ← direct args
  python validate_cli.py generate \\
      --pg-table events --sf-table EVENTS \\
      --model gpt-4o-mini                        ← choose model
  python validate_cli.py rules                   ← view rule book
  python validate_cli.py list-models             ← list AI models
  python validate_cli.py add-rule                ← add custom rule
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# ── Ensure src/ is in path ────────────────────────────────────────────────────
_SRC_DIR = Path(__file__).parent
sys.path.insert(0, str(_SRC_DIR))

# ── Load .env ─────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(_SRC_DIR.parent / ".env")
except ImportError:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# ANSI colour helpers
# ─────────────────────────────────────────────────────────────────────────────

class _C:
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    CYAN   = "\033[96m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"


def _ok(msg):   print(f"{_C.GREEN}  ✓ {msg}{_C.RESET}")
def _warn(msg): print(f"{_C.YELLOW}  ⚠ {msg}{_C.RESET}")
def _err(msg):  print(f"{_C.RED}  ✗ {msg}{_C.RESET}")
def _head(msg): print(f"\n{_C.BOLD}{_C.CYAN}{msg}{_C.RESET}")
def _dim(msg):  print(f"{_C.DIM}  {msg}{_C.RESET}")
def _sep(char="─", width=62): print(f"  {char * width}")


def _banner():
    print(f"""
{_C.CYAN}{_C.BOLD}
╔══════════════════════════════════════════════════════════════════╗
║      Migration Validator  —  AI Query Generator                 ║
║      PostgreSQL  →  Snowflake  Data Completeness Checks         ║
╚══════════════════════════════════════════════════════════════════╝{_C.RESET}""")


def _prompt(label: str, default: str = "") -> str:
    """Prompt the user with an optional default value."""
    if default:
        display = f"  {_C.BOLD}{label}{_C.RESET} [{_C.DIM}{default}{_C.RESET}]: "
    else:
        display = f"  {_C.BOLD}{label}{_C.RESET}: "
    value = input(display).strip()
    return value if value else default


# ─────────────────────────────────────────────────────────────────────────────
# MODEL SELECTOR — Interactive + CLI
# ─────────────────────────────────────────────────────────────────────────────

def _get_display_models(verbose_probe: bool = False) -> list:
    """
    Return the list of models to show the user.
    If a DIAL key is configured, probe the API and return only working models.
    Falls back to the full AVAILABLE_MODELS list on any probing error.
    """
    from ai_transformation import AVAILABLE_MODELS
    from model_probe import get_working_models

    dial_key     = os.getenv("DIAL_API_KEY", "")
    api_base     = os.getenv("DIAL_API_BASE",    "https://ai-proxy.lab.epam.com")
    api_version  = os.getenv("DIAL_API_VERSION", "2025-04-01-preview")

    if not dial_key:
        return AVAILABLE_MODELS

    working = get_working_models(
        AVAILABLE_MODELS, dial_key, api_base, api_version, verbose=verbose_probe
    )
    return working if working else AVAILABLE_MODELS


def _select_model_interactive(current_model: str) -> str:
    """
    Show a numbered, provider-grouped model list and let the user choose.
    Only working models (verified against the DIAL API) are shown.
    Returns the selected model name (unchanged if user presses Enter).
    """
    from ai_transformation.ai_rule_mapper import MODEL_DESCRIPTIONS

    _head("🤖  AI MODEL SELECTION")
    print()

    dial_key = os.getenv("DIAL_API_KEY", "")
    if not dial_key:
        _warn("DIAL_API_KEY is not set — AI mode is inactive.")
        _dim("Model selection has no effect until DIAL_API_KEY is configured in .env.")
        print()
        from ai_transformation import AVAILABLE_MODELS
        display_models = AVAILABLE_MODELS
    else:
        _dim("Checking which models are available on your API key (cached 24h)...")
        display_models = _get_display_models()
        _ok(f"{len(display_models)} working model(s) found")
        print()

    print(f"  Current model : {_C.GREEN}{current_model}{_C.RESET}\n")
    print(f"  {'#':<4} {'Provider':<12} {'Model ID':<36} Description")
    _sep("─", 80)

    # Group by provider for readability
    by_provider: dict = {}
    providers_seen = []
    for model in display_models:
        info = MODEL_DESCRIPTIONS.get(model, ("Other", model, "Available via EPAM DIAL"))
        provider = info[0]
        if provider not in by_provider:
            by_provider[provider] = []
            providers_seen.append(provider)
        by_provider[provider].append((model, info[2]))

    numbered: list = []  # (idx, model)
    idx = 1
    for provider in providers_seen:
        for model, desc in by_provider[provider]:
            marker = f"  {_C.GREEN}← current{_C.RESET}" if model == current_model else ""
            print(
                f"    {_C.CYAN}[{idx}]{_C.RESET}  "
                f"{_C.YELLOW}{provider:<12}{_C.RESET}"
                f"{model:<36} {_C.DIM}{desc}{_C.RESET}{marker}"
            )
            numbered.append(model)
            idx += 1

    print(f"\n    {_C.DIM}[Enter]  Keep current model  ({current_model}){_C.RESET}")
    print()

    choice = input("  Select model number (or press Enter to keep current): ").strip()
    if not choice:
        return current_model

    try:
        num = int(choice) - 1
        if 0 <= num < len(numbered):
            selected = numbered[num]
            _ok(f"Model selected: {selected}")
            return selected
        else:
            _warn(f"Invalid choice '{choice}'. Keeping current model.")
            return current_model
    except ValueError:
        _warn(f"Invalid input '{choice}'. Keeping current model.")
        return current_model


def _list_models_cmd():
    """Print available (working) models and exit."""
    from ai_transformation import AVAILABLE_MODELS
    from ai_transformation.ai_rule_mapper import MODEL_DESCRIPTIONS

    _banner()
    _head("🤖  AVAILABLE AI MODELS  (via EPAM DIAL)")
    print()

    dial_key = os.getenv("DIAL_API_KEY", "")
    current  = os.getenv("DIAL_MODEL", "gpt-4o")
    status   = f"{_C.GREEN}✓ ACTIVE{_C.RESET}" if dial_key else f"{_C.YELLOW}✗ NOT CONFIGURED{_C.RESET}"
    print(f"  DIAL API Key  : {status}")
    print(f"  Current model : {_C.GREEN}{current}{_C.RESET}")
    print()

    if dial_key:
        _dim("Probing API to find working models (cached 24h)...")
        display_models = _get_display_models(verbose_probe=False)
        skipped = len(AVAILABLE_MODELS) - len(display_models)
        _ok(f"{len(display_models)} working model(s) on your key"
            + (f"  ({skipped} unavailable — hidden)" if skipped else ""))
    else:
        display_models = AVAILABLE_MODELS
        _warn("No API key — showing all models (availability not verified)")
    print()

    # Group models by provider
    providers_seen = []
    by_provider: dict = {}
    for model in display_models:
        info = MODEL_DESCRIPTIONS.get(model, ("Other", model, "Available via EPAM DIAL"))
        provider = info[0]
        if provider not in by_provider:
            by_provider[provider] = []
            providers_seen.append(provider)
        by_provider[provider].append((model, info[1], info[2]))

    print(f"  {'#':<4} {'Provider':<12} {'Model ID':<38} {'Display Name':<26} Description")
    _sep("─", 98)

    idx = 1
    for provider in providers_seen:
        for model, display, desc in by_provider[provider]:
            marker = f" {_C.GREEN}← active{_C.RESET}" if model == current else ""
            print(
                f"  {_C.DIM}{idx:<4}{_C.RESET}"
                f"{_C.YELLOW}{provider:<12}{_C.RESET}"
                f"{_C.CYAN}{model:<38}{_C.RESET}"
                f"{display:<26} {_C.DIM}{desc}{_C.RESET}{marker}"
            )
            idx += 1
    print()
    _dim(f"Showing {len(display_models)} working model(s).")
    _dim("To set a default model, add  DIAL_MODEL=<model_name>  to your .env file.")
    _dim("To select per-run: python validate_cli.py generate --model gpt-4o")
    _dim("To refresh availability: delete .dial_model_cache.json next to .env")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: generate
# ─────────────────────────────────────────────────────────────────────────────

def cmd_generate(args):
    """
    Full validation workflow:
      1. Collect source/target table details
      2. Let user review/update rule book
      3. Select AI model
      4. Run ValidationPipeline (extract → map rules → generate SQL + YAML)
      5. Show where files were saved
    """
    from validation_pipeline import ValidationPipeline
    from rule_book import rule_book
    from ai_transformation import AVAILABLE_MODELS

    _banner()
    _head("📋  GENERATE VALIDATION QUERIES  (SQL + YAML)")

    stats = rule_book.stats()
    _dim(
        f"Rule book: {stats['base_rules']} base rules "
        f"+ {stats['learned_rules']} learned rules = {stats['total_rules']} total"
    )

    # ── Collect inputs ────────────────────────────────────────────────────────
    pg_database = getattr(args, "pg_database", None) or _prompt(
        "PostgreSQL database name", os.getenv("SOURCE_DATABASE", "")
    )
    pg_schema = getattr(args, "pg_schema", None) or _prompt(
        "PostgreSQL schema", os.getenv("SOURCE_SCHEMA", "public")
    )
    pg_table = getattr(args, "pg_table", None) or _prompt(
        "PostgreSQL table name", ""
    )
    if not pg_table:
        _err("PostgreSQL table name is required.")
        return

    sf_schema = getattr(args, "sf_schema", None) or _prompt(
        "Snowflake schema", os.getenv("SNOWFLAKE_SCHEMA", "")
    )
    sf_table = getattr(args, "sf_table", None) or _prompt(
        "Snowflake table name (UPPER CASE recommended)", pg_table.upper()
    )
    sf_database = getattr(args, "sf_database", None) or os.getenv("SNOWFLAKE_DATABASE", "")

    # ── Show config summary ───────────────────────────────────────────────────
    ai_status = (
        f"{_C.GREEN}✓ ACTIVE{_C.RESET}"
        if os.getenv("DIAL_API_KEY")
        else f"{_C.YELLOW}⚠ Not active — static fallback{_C.RESET}"
    )
    current_model = getattr(args, "model", None) or os.getenv("DIAL_MODEL", "gpt-4o")
    _pg_db_display = pg_database or os.getenv("SOURCE_DATABASE", "?")

    print(f"""
  {_C.BOLD}Config Summary:{_C.RESET}
    PG Database : {_C.GREEN}{_pg_db_display}{_C.RESET}
    Source      : PostgreSQL  →  {_C.GREEN}{_pg_db_display}.{pg_schema}.{pg_table}{_C.RESET}
    Target      : Snowflake   →  {_C.GREEN}{sf_database}.{sf_schema}.{sf_table}{_C.RESET}
    AI Mode     : {ai_status}
    Model       : {_C.CYAN}{current_model}{_C.RESET}
""")

    # ── Rule book review ──────────────────────────────────────────────────────
    current_model = _rule_review_step(args, current_model)

    # ── Model selection (if not passed as CLI arg) ────────────────────────────
    if not getattr(args, "model", None):
        change = input(
            f"\n  Change AI model? Current: {_C.CYAN}{current_model}{_C.RESET} [y/N]: "
        ).strip().lower()
        if change in ("y", "yes"):
            current_model = _select_model_interactive(current_model)

    # ── Confirm ───────────────────────────────────────────────────────────────
    confirm = input("\n  Proceed with query generation? [Y/n]: ").strip().lower()
    if confirm in ("n", "no"):
        _dim("Cancelled.")
        return

    # ── Run pipeline ──────────────────────────────────────────────────────────
    print()
    try:
        pipeline = ValidationPipeline(model=current_model)
        result   = pipeline.run(
            pg_schema=pg_schema,
            pg_table=pg_table,
            sf_schema=sf_schema,
            sf_table=sf_table,
            sf_database=sf_database,
            pg_database=pg_database,
        )
        _show_output_summary(result, pg_database=pg_database)

    except Exception as exc:
        _err(f"Generation failed: {exc}")
        print()
        print("  Troubleshooting:")
        print("    • Check SOURCE_* vars in .env for PostgreSQL")
        print("    • Check SNOWFLAKE_* vars in .env for Snowflake")
        print("    • Run: python check_connections.py  for diagnostics")
        sys.exit(1)


def _run_queries_terminal(result, pg_database: str = "", mode: str = "all") -> None:
    """
    Execute the generated SQL queries against live databases and display
    results in the terminal. Wraps QueryExecutor with a GenerationResult adapter.

    mode="all"         — execute all 8 queries (row count + validation + null% + distinct)
    mode="counts_only" — execute only row count queries (① and ②)
    """
    from generated_queries.sql_query_generator import ValidationQuerySet

    qs = result.query_set

    _head("🚀  EXECUTING QUERIES IN TERMINAL")
    print()

    # Describe what will run
    queries_map = {
        "① ROW COUNT — PostgreSQL":      ("postgresql", qs.row_count_source),
        "② ROW COUNT — Snowflake":       ("snowflake",  qs.row_count_target),
    }
    if mode == "all":
        queries_map.update({
            "⑤ NULL % CHECK — PostgreSQL":      ("postgresql", qs.null_pct_source),
            "⑥ NULL % CHECK — Snowflake":       ("snowflake",  qs.null_pct_target),
            "⑦ DISTINCT COUNT — PostgreSQL":    ("postgresql", qs.distinct_count_source),
            "⑧ DISTINCT COUNT — Snowflake":     ("snowflake",  qs.distinct_count_target),
            "③ MAIN VALIDATION — PostgreSQL":   ("postgresql", qs.main_validation_source),
            "④ MAIN VALIDATION — Snowflake":    ("snowflake",  qs.main_validation_target),
        })

    # ── Connect to PostgreSQL ────────────────────────────────────────────────
    pg_conn = None
    sf_conn = None
    try:
        _dim("Connecting to PostgreSQL...")
        import psycopg2
        import psycopg2.extras
        pg_conn = psycopg2.connect(
            host=os.getenv("SOURCE_HOST", "localhost"),
            port=int(os.getenv("SOURCE_PORT", "5432")),
            database=pg_database or os.getenv("SOURCE_DATABASE", "postgres"),
            user=os.getenv("SOURCE_USERNAME", "postgres"),
            password=os.getenv("SOURCE_PASSWORD", ""),
            connect_timeout=15,
        )
        _ok("PostgreSQL connected")
    except Exception as exc:
        _err(f"PostgreSQL connection failed: {exc}")
        _warn("Cannot execute PostgreSQL queries. Snowflake queries will still run.")

    try:
        _dim("Connecting to Snowflake...")
        import snowflake.connector
        sf_conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT", ""),
            database=os.getenv("SNOWFLAKE_DATABASE", ""),
            schema=os.getenv("SNOWFLAKE_SCHEMA", ""),
            user=os.getenv("SNOWFLAKE_USERNAME", ""),
            password=os.getenv("SNOWFLAKE_PASSWORD", ""),
        )
        _ok("Snowflake connected")
    except Exception as exc:
        _err(f"Snowflake connection failed: {exc}")
        _warn("Cannot execute Snowflake queries. PostgreSQL queries will still run.")

    if not pg_conn and not sf_conn:
        _err("Both connections failed. Run: python check_connections.py")
        return

    # ── Execute each query ────────────────────────────────────────────────────
    source_count = 0
    target_count = 0

    for label, (db, sql) in queries_map.items():
        if not sql:
            continue

        conn = pg_conn if db == "postgresql" else sf_conn
        if not conn:
            _warn(f"  [SKIP] {label} — {db} not connected")
            continue

        print(f"\n  {_C.BOLD}{_C.CYAN}{'─'*64}{_C.RESET}")
        print(f"  {_C.BOLD}{label}{_C.RESET}")
        print(f"  {_C.DIM}{'─'*64}{_C.RESET}")

        try:
            import time
            start = time.time()
            if db == "postgresql":
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql)
                    rows = [dict(r) for r in cur.fetchall()]
            else:
                cur = sf_conn.cursor(snowflake.connector.DictCursor)
                cur.execute(sql)
                rows = [dict(r) for r in cur.fetchall()]
                cur.close()

            elapsed = (time.time() - start) * 1000
            _ok(f"Returned {len(rows):,} row(s) in {elapsed:.0f}ms")
            _print_table(rows, max_rows=25)

            # Capture row counts for comparison
            # Snowflake returns uppercase column names; check both cases
            if "① ROW COUNT" in label and rows:
                source_count = int(
                    rows[0].get("source_row_count") or rows[0].get("SOURCE_ROW_COUNT") or 0
                )
            elif "② ROW COUNT" in label and rows:
                target_count = int(
                    rows[0].get("target_row_count") or rows[0].get("TARGET_ROW_COUNT") or 0
                )

        except Exception as exc:
            _err(f"Query failed: {exc}")
            # psycopg2 leaves the connection in an aborted-transaction state
            # after any error; rollback so the next query can still execute.
            if db == "postgresql" and conn:
                try:
                    conn.rollback()
                except Exception:
                    pass

    # ── Row count verdict ─────────────────────────────────────────────────────
    if source_count or target_count:
        print(f"\n  {'═'*64}")
        print(f"  {_C.BOLD}ROW COUNT COMPARISON{_C.RESET}")
        print(f"  {'─'*64}")
        print(f"    PostgreSQL rows : {_C.GREEN}{source_count:,}{_C.RESET}")
        print(f"    Snowflake  rows : {_C.GREEN}{target_count:,}{_C.RESET}")
        if source_count == target_count:
            _ok(f"Row counts MATCH ✓  ({source_count:,} rows)")
        else:
            diff = abs(source_count - target_count)
            diff_pct = diff / max(source_count, 1) * 100
            if diff_pct <= 1.0:
                _warn(f"Row counts differ by {diff:,} ({diff_pct:.2f}%) — within 1% tolerance")
            else:
                _err(f"Row count MISMATCH  |  diff = {diff:,} rows ({diff_pct:.1f}%)")
        print(f"  {'═'*64}")

    # ── Disconnect ────────────────────────────────────────────────────────────
    try:
        if pg_conn:
            pg_conn.close()
    except Exception:
        pass
    try:
        if sf_conn:
            sf_conn.close()
    except Exception:
        pass


def _print_table(rows: list, max_rows: int = 25) -> None:
    """Print query results as a clean ASCII table."""
    if not rows:
        _dim("  (no rows returned)")
        return

    cols = list(rows[0].keys())
    widths = {c: max(len(str(c)), max(len(str(r.get(c, ""))) for r in rows[:max_rows])) for c in cols}
    widths = {c: min(w, 40) for c, w in widths.items()}  # cap column width at 40

    top = "  ┌─" + "─┬─".join("─" * widths[c] for c in cols) + "─┐"
    hdr = "  │ " + " │ ".join(str(c).ljust(widths[c]) for c in cols) + " │"
    sep = "  ├─" + "─┼─".join("─" * widths[c] for c in cols) + "─┤"
    bot = "  └─" + "─┴─".join("─" * widths[c] for c in cols) + "─┘"

    print(f"{_C.DIM}{top}{_C.RESET}")
    print(f"{_C.BOLD}{hdr}{_C.RESET}")
    print(f"{_C.DIM}{sep}{_C.RESET}")
    for row in rows[:max_rows]:
        line = "  │ " + " │ ".join(str(row.get(c, ""))[:widths[c]].ljust(widths[c]) for c in cols) + " │"
        print(line)
    print(f"{_C.DIM}{bot}{_C.RESET}")
    if len(rows) > max_rows:
        _dim(f"  ... {len(rows) - max_rows:,} more rows not shown (first {max_rows} displayed)")


def _show_output_summary(result, pg_database: str = "") -> None:
    """Pretty-print where the output files were saved, then offer to execute queries."""
    _sep("═")
    print(f"\n  {_C.BOLD}{_C.GREEN}✓  GENERATION COMPLETE{_C.RESET}")
    _sep()
    print(f"\n  {_C.BOLD}Table          :{_C.RESET} {result.table_name}")
    print(f"  {_C.BOLD}Generated by   :{_C.RESET} {result.generated_by.upper()}")
    print(f"  {_C.BOLD}AI Model       :{_C.RESET} {result.model_used}")
    print(f"  {_C.BOLD}Active columns :{_C.RESET} {result.active_columns}")
    if result.skipped_columns:
        print(f"  {_C.BOLD}Skipped        :{_C.RESET} {', '.join(result.skipped_columns)}")
    fivetran_str = (
        f"{_C.GREEN}YES — WHERE _FIVETRAN_ACTIVE = TRUE{_C.RESET}"
        if result.has_fivetran_active
        else f"{_C.DIM}NO{_C.RESET}"
    )
    print(f"  {_C.BOLD}Fivetran filter:{_C.RESET} {fivetran_str}")

    print(f"\n  {_C.BOLD}Output files:{_C.RESET}")
    print(f"    {_C.GREEN}💾 SQL        :{_C.RESET}  {result.sql_path}")
    print(f"    {_C.CYAN}📋 YAML       :{_C.RESET}  {result.yaml_path}")
    if getattr(result, "dynamic_suite_path", None):
        print(f"    {_C.GREEN}💾 Dynamic SQL :{_C.RESET}  {result.dynamic_suite_path}")
    if getattr(result, "dynamic_suite_yaml_path", None):
        print(f"    {_C.CYAN}📋 Dynamic YAML:{_C.RESET}  {result.dynamic_suite_yaml_path}")

    print(f"\n  {_C.BOLD}How to use:{_C.RESET}")
    print(f"    ① Run ① PostgreSQL row count")
    print(f"    ② Run ② Snowflake row count — compare with ①")
    print(f"    ③ Run ③ PostgreSQL normalised validation query → export CSV")
    print(f"    ④ Run ④ Snowflake normalised validation query  → export CSV")
    print(f"    ⑤ NULL % check — PostgreSQL")
    print(f"    ⑥ NULL % check — Snowflake — compare with ⑤")
    print(f"    ⑦ Distinct values per column — PostgreSQL")
    print(f"    ⑧ Distinct values per column — Snowflake")
    print(f"    Use YAML file with your automated validation runner")
    if getattr(result, "dynamic_suite_path", None):
        print(f"\n  {_C.BOLD}Dynamic suite (schema-aware conditional checks):{_C.RESET}")
        print(f"    Open the Dynamic SQL file for column-type-specific checks:")
        print(f"    MIN/MAX, SUM (financial), DUPLICATE checks, VALUE_DIST, AI business rules")
    _sep("═")

    # ── Offer to execute queries in terminal ──────────────────────────────────
    print(f"\n  {_C.BOLD}Execute queries now in the terminal?{_C.RESET}")
    print(f"    {_C.GREEN}[y]{_C.RESET}  Execute ALL queries and show results")
    print(f"    {_C.CYAN}[s]{_C.RESET}  Execute SELECT queries (row counts + validation)")
    print(f"    {_C.DIM}[n]{_C.RESET}  Skip — I'll run them manually")
    print()

    choice = input("  Choice [y/s/N]: ").strip().lower()
    if choice in ("y", "yes"):
        _run_queries_terminal(result, pg_database=pg_database, mode="all")
    elif choice in ("s", "select"):
        _run_queries_terminal(result, pg_database=pg_database, mode="counts_only")
    else:
        _dim("Skipped. Open the SQL file to run queries manually.")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Rule book review (shown before generation)
# ─────────────────────────────────────────────────────────────────────────────

def _rule_review_step(args, current_model: str) -> str:
    """
    Show rule book summary and allow user to view / add rules before
    the AI generates queries. Returns (possibly updated) model string.
    """
    from rule_book import rule_book

    stats   = rule_book.stats()
    learned = rule_book.learned_rules()

    print(f"\n  {_C.BOLD}{'─' * 60}{_C.RESET}")
    print(f"  {_C.BOLD}📚  RULE BOOK REVIEW  (Before Query Generation){_C.RESET}")
    print(f"  {_C.BOLD}{'─' * 60}{_C.RESET}")
    _dim("The AI uses these rules to decide how to normalise each column.")
    _dim("Review now and add any missing rules before proceeding.")
    print()
    print(f"    Base rules   : {_C.GREEN}{stats['base_rules']}{_C.RESET}")
    print(f"    Learned rules: {_C.CYAN}{stats['learned_rules']}{_C.RESET}")
    print(f"    Total        : {_C.BOLD}{stats['total_rules']}{_C.RESET}")
    print()

    if learned:
        print(f"  {_C.BOLD}Your learned rules (injected into AI prompt):{_C.RESET}")
        for r in learned:
            print(f"    {_C.CYAN}• {r.id}{_C.RESET}  —  {r.description[:65]}")
            print(f"      PG: {r.pg_sql_template}")
            print(f"      SF: {r.sf_sql_template}")
        print()

    print(f"  Options:")
    print(f"    {_C.GREEN}[v]{_C.RESET}  View all rules in detail")
    print(f"    {_C.CYAN}[a]{_C.RESET}  Add a new rule to the rule book")
    print(f"    {_C.DIM}[c]{_C.RESET}  Continue — rules look good")
    print()

    while True:
        choice = input("  Choice [v/a/C]: ").strip().lower()
        if choice in ("", "c", "continue"):
            _ok("Rules confirmed. Proceeding...")
            break
        elif choice == "v":
            _print_rules_full(rule_book)
            print(f"\n  {_C.CYAN}[a]{_C.RESET} Add rule  |  {_C.DIM}[c]{_C.RESET} Continue")
        elif choice == "a":
            cmd_add_rule(args)
            updated = rule_book.stats()
            _ok(f"Rule book updated: {updated['total_rules']} total rules")
        else:
            _warn(f"Unknown choice '{choice}'. Enter v, a, or c.")

    return current_model


def _print_rules_full(rb) -> None:
    """Print detailed view of all rules."""
    print(f"\n  {_C.BOLD}── BASE RULES ─────────────────────────────────────────────{_C.RESET}")
    for r in rb.base_rules():
        print(f"\n    {_C.GREEN}{_C.BOLD}{r.id}{_C.RESET}  {_C.DIM}({r.display_name}){_C.RESET}")
        print(f"      What  : {r.description[:90]}")
        print(f"      PG SQL: {r.pg_sql_template}")
        print(f"      SF SQL: {r.sf_sql_template}")

    learned = rb.learned_rules()
    if learned:
        print(f"\n  {_C.BOLD}── YOUR LEARNED RULES ─────────────────────────────────────{_C.RESET}")
        for r in learned:
            added = r.learned_at[:10] if r.learned_at else "unknown"
            print(f"\n    {_C.CYAN}{_C.BOLD}{r.id}{_C.RESET}  {_C.DIM}added {added}{_C.RESET}")
            print(f"      What  : {r.description}")
            print(f"      When  : {r.when_to_apply}")
            print(f"      PG SQL: {r.pg_sql_template}")
            print(f"      SF SQL: {r.sf_sql_template}")
            if r.example:
                print(f"      Example: {r.example}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: rules
# ─────────────────────────────────────────────────────────────────────────────

def cmd_rules(args):
    """Display the full rule book with all transformation rules."""
    from rule_book import rule_book

    _banner()
    _head("📚  RULE BOOK — All Transformation Rules")

    stats = rule_book.stats()
    print(f"\n  Base rules   : {_C.GREEN}{stats['base_rules']}{_C.RESET}")
    print(f"  Learned rules: {_C.CYAN}{stats['learned_rules']}{_C.RESET}")
    print(f"  Total        : {_C.BOLD}{stats['total_rules']}{_C.RESET}")
    print()

    # Base rules
    print(f"{_C.BOLD}  ── BASE RULES (Built-in, apply automatically) ──────────────{_C.RESET}")
    for r in rule_book.base_rules():
        print(f"\n  {_C.BOLD}{_C.GREEN}{r.id}{_C.RESET}  {_C.DIM}({r.display_name}){_C.RESET}")
        print(f"    Description : {r.description[:100]}")
        print(f"    Triggers on : {r.source_type} → {r.target_type}")
        print(f"    PG SQL      : {r.pg_sql_template}")
        print(f"    SF SQL      : {r.sf_sql_template}")

    # Learned rules
    learned = rule_book.learned_rules()
    if learned:
        print(f"\n{_C.BOLD}  ── YOUR LEARNED RULES (injected into AI prompt) ───────────{_C.RESET}")
        for r in learned:
            added = r.learned_at[:10] if r.learned_at else "unknown"
            print(f"\n  {_C.BOLD}{_C.CYAN}{r.id}{_C.RESET}  {_C.DIM}(added {added}){_C.RESET}")
            print(f"    Description : {r.description}")
            print(f"    Apply when  : {r.when_to_apply}")
            print(f"    PG SQL      : {r.pg_sql_template}")
            print(f"    SF SQL      : {r.sf_sql_template}")
            if r.example:
                print(f"    Example     : {r.example}")
    else:
        print(f"\n  {_C.DIM}No learned rules yet. Use 'add-rule' to add your first custom rule.{_C.RESET}")

    # Also print the AI prompt block structure
    print(f"\n{_C.BOLD}  ── RULE APPLICATION ORDER ──────────────────────────────────{_C.RESET}")
    print(f"  {_C.DIM}(Innermost → Outermost — applied per column){_C.RESET}")
    order = [
        "integer / uuid / json / bytea  (type-specific inner transform)",
        "boolean  (CASE WHEN → '1'/'0')",
        "timestamp_tz  (UTC conversion → format)",
        "timestamp_ntz / date  (format only)",
        "numeric  (ROUND to 2dp)",
        "text  (TRIM)",
        "NULL placeholder  ← ALWAYS LAST: COALESCE(…, '<<NULL>>')",
    ]
    for i, step in enumerate(order, 1):
        print(f"    {i}. {step}")

    print(f"\n  {_C.BOLD}Fivetran filter (Snowflake side only):{_C.RESET}")
    print(f"    WHERE _FIVETRAN_ACTIVE = TRUE")
    print(f"    {_C.DIM}Auto-applied when _FIVETRAN_ACTIVE column is detected{_C.RESET}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: add-rule
# ─────────────────────────────────────────────────────────────────────────────

def cmd_add_rule(args):
    """
    Interactive wizard to add a new rule to rule_book_learned.json.
    The rule is saved permanently and injected into ALL future AI prompts.
    """
    from rule_book import rule_book, RuleEntry

    _banner()
    _head("➕  ADD NEW RULE TO RULE BOOK")

    print(f"""
  {_C.DIM}Rules you add here are saved to rule_book_learned.json and
  automatically injected into the AI prompt on every future run.
  Use this for column-level transformations not in the base rules
  (e.g. phone number normalisation, currency stripping, etc.).{_C.RESET}
""")

    # ── Collect rule details ──────────────────────────────────────────────────
    rule_id = _prompt("Rule ID (snake_case, e.g. phone_strip)", "").strip()
    if not rule_id:
        _warn("Rule ID cannot be empty. Cancelled.")
        return

    # Normalise to snake_case
    rule_id = rule_id.lower().replace(" ", "_").replace("-", "_")

    # Check for duplicates
    if rule_book.rule_exists(rule_id):
        ow = input(f"  Rule '{rule_id}' already exists. Overwrite? [y/N]: ").strip().lower()
        if ow not in ("y", "yes"):
            _dim("Cancelled.")
            return

    display_name  = _prompt("Display name (e.g. 'Phone Number Strip')", rule_id)
    description   = _prompt("What does this rule do? (plain English)", "")
    when_to_apply = _prompt(
        "When to apply? (e.g. 'VARCHAR phone numbers migrated from PG to Snowflake')", ""
    )
    source_type   = _prompt("Source (PostgreSQL) type that triggers this (e.g. VARCHAR)", "*")
    target_type   = _prompt("Target (Snowflake)  type that triggers this (e.g. VARCHAR)", "*")
    pg_template   = _prompt(
        "PostgreSQL SQL template — use {col} for column reference\n"
        "  e.g. REGEXP_REPLACE({col}, '[^0-9]', '', 'g')",
        "{col}",
    )
    sf_template   = _prompt(
        "Snowflake SQL template — use {col} for column reference\n"
        "  e.g. REGEXP_REPLACE({col}, '[^0-9]', '')",
        "{col}",
    )
    example = _prompt("Optional: example or scenario (press Enter to skip)", "")

    # ── Preview ───────────────────────────────────────────────────────────────
    print(f"""
  {_C.BOLD}Preview:{_C.RESET}
    ID          : {_C.GREEN}{rule_id}{_C.RESET}
    Display     : {display_name}
    Description : {description}
    When        : {when_to_apply}
    Src type    : {source_type}  →  Tgt type : {target_type}
    PG SQL      : {pg_template}
    SF SQL      : {sf_template}
    Example     : {example or '(none)'}
""")

    confirm = input("  Save this rule? [Y/n]: ").strip().lower()
    if confirm in ("n", "no"):
        _dim("Cancelled.")
        return

    entry = RuleEntry(
        id=rule_id,
        display_name=display_name,
        description=description,
        when_to_apply=when_to_apply,
        pg_sql_template=pg_template,
        sf_sql_template=sf_template,
        source_type=source_type,
        target_type=target_type,
        is_learned=True,
        example=example or None,
    )

    if rule_book.save_learned_rule(entry):
        _ok(f"Rule '{rule_id}' saved to rule_book_learned.json ✓")
        _ok("It will be included in ALL future AI prompts automatically.")
        print(f"\n  {_C.DIM}File: {_SRC_DIR / 'rule_book_learned.json'}{_C.RESET}")
    else:
        _err("Failed to save rule — check write permissions.")


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: list-tables
# ─────────────────────────────────────────────────────────────────────────────

def cmd_list_tables(args):
    """List tables available in both PostgreSQL and Snowflake schemas."""
    _banner()
    _head("🔍  AVAILABLE TABLES")

    # PostgreSQL
    pg_db     = os.getenv("SOURCE_DATABASE", "?")
    pg_schema = os.getenv("SOURCE_SCHEMA", "public")
    print(f"\n  {_C.BOLD}PostgreSQL{_C.RESET} — {pg_db}.{pg_schema}")

    try:
        from sql_extractor import PostgresExtractor
        tables = PostgresExtractor().list_tables(pg_schema)
        if tables:
            for t in tables:
                print(f"    {_C.GREEN}•{_C.RESET} {t}")
        else:
            _warn(f"No tables found in schema '{pg_schema}'")
    except Exception as exc:
        _err(f"PostgreSQL list failed: {exc}")

    # Snowflake
    sf_db     = os.getenv("SNOWFLAKE_DATABASE", "?")
    sf_schema = os.getenv("SNOWFLAKE_SCHEMA", "?")
    print(f"\n  {_C.BOLD}Snowflake{_C.RESET} — {sf_db}.{sf_schema}")

    try:
        from sql_extractor import SnowflakeExtractor
        tables = SnowflakeExtractor().list_tables(sf_schema)
        if tables:
            for t in tables:
                print(f"    {_C.CYAN}•{_C.RESET} {t}")
        else:
            _warn(f"No tables found in schema '{sf_schema}'")
    except Exception as exc:
        _err(f"Snowflake list failed: {exc}")

    print()


# ─────────────────────────────────────────────────────────────────────────────
# INTERACTIVE MENU (no command given)
# ─────────────────────────────────────────────────────────────────────────────

def cmd_interactive():
    """Show interactive top-level menu when no command is given."""
    from rule_book import rule_book
    from ai_transformation import AVAILABLE_MODELS

    _banner()

    stats = rule_book.stats()
    dial_key      = os.getenv("DIAL_API_KEY", "")
    current_model = os.getenv("DIAL_MODEL", "gpt-4o")
    ai_status = (
        f"{_C.GREEN}✓ ACTIVE — model: {current_model}{_C.RESET}"
        if dial_key
        else f"{_C.YELLOW}⚠ Not active — static fallback{_C.RESET}"
    )

    print(f"""
  {_C.DIM}AI Mode   : {ai_status}
  Rule Book : {stats['base_rules']} base rules + {stats['learned_rules']} learned rules{_C.RESET}

  {_C.BOLD}What would you like to do?{_C.RESET}

    {_C.GREEN}[1]{_C.RESET}  Generate SQL + YAML validation files   ← Full workflow
    {_C.CYAN}[2]{_C.RESET}  Select AI model
    {_C.CYAN}[3]{_C.RESET}  View rule book
    {_C.CYAN}[4]{_C.RESET}  Add a custom rule to rule book
    {_C.CYAN}[5]{_C.RESET}  List tables in both databases
    {_C.DIM}[q]{_C.RESET}  Quit
""")

    choice = input("  Enter choice: ").strip().lower()
    ns     = argparse.Namespace()

    if choice in ("1", "generate"):
        cmd_generate(ns)
    elif choice in ("2", "model", "select-model"):
        new_model = _select_model_interactive(current_model)
        # Persist selection to runtime env for this session
        os.environ["DIAL_MODEL"] = new_model
        _ok(f"Model set to '{new_model}' for this session.")
        _dim("To make this permanent, update DIAL_MODEL in your .env file.")
    elif choice in ("3", "rules"):
        cmd_rules(ns)
    elif choice in ("4", "add-rule", "add"):
        cmd_add_rule(ns)
    elif choice in ("5", "list-tables", "list"):
        cmd_list_tables(ns)
    elif choice in ("q", "quit", "exit"):
        _dim("Bye!")
    else:
        _warn(f"Unknown choice '{choice}'. Please enter 1–5 or q.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI argument parser + entry point
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate_cli",
        description="Migration Validator — AI-Powered SQL + YAML Generator (PostgreSQL → Snowflake)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Run  python validate_cli.py list-models  to see which models work with your API key.

Examples:
  python validate_cli.py                                        ← interactive menu
  python validate_cli.py generate --pg-database fms --pg-table events --sf-table EVENTS
  python validate_cli.py generate --pg-database fms --pg-table events --sf-table EVENTS --model gpt-4o
  python validate_cli.py rules
  python validate_cli.py add-rule
  python validate_cli.py list-models
  python validate_cli.py list-tables
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # ── generate ─────────────────────────────────────────────────────────────
    gen = sub.add_parser(
        "generate",
        help="Generate SQL + YAML validation files (full workflow)",
    )
    gen.add_argument("--pg-database", dest="pg_database", default=None, help="PostgreSQL database name (overrides SOURCE_DATABASE in .env)")
    gen.add_argument("--pg-schema",   dest="pg_schema",   default=None, help="PostgreSQL schema")
    gen.add_argument("--pg-table",    dest="pg_table",    default=None, help="PostgreSQL table")
    gen.add_argument("--sf-schema",   dest="sf_schema",   default=None, help="Snowflake schema")
    gen.add_argument("--sf-table",    dest="sf_table",    default=None, help="Snowflake table")
    gen.add_argument("--sf-database", dest="sf_database", default=None, help="Snowflake database")
    gen.add_argument(
        "--model",
        default=None,
        metavar="MODEL",
        help="AI model to use. Run 'list-models' to see working options for your API key.",
    )

    # ── rules ─────────────────────────────────────────────────────────────────
    sub.add_parser("rules", help="Show the full rule book (base + learned)")

    # ── add-rule ──────────────────────────────────────────────────────────────
    sub.add_parser("add-rule", help="Add a custom rule to the evolving rule book")

    # ── list-models ───────────────────────────────────────────────────────────
    sub.add_parser("list-models", help="List all available AI models")

    # ── list-tables ───────────────────────────────────────────────────────────
    sub.add_parser("list-tables", help="List tables in PostgreSQL and Snowflake")

    return parser


def main():
    parser = _build_parser()
    args   = parser.parse_args()

    commands = {
        "generate":    cmd_generate,
        "rules":       cmd_rules,
        "add-rule":    cmd_add_rule,
        "list-models": lambda _: _list_models_cmd(),
        "list-tables": cmd_list_tables,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        # No command → interactive menu
        cmd_interactive()


if __name__ == "__main__":
    main()
