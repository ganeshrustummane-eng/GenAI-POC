"""
Migration Validator — Web UI
==============================
A thin Streamlit UI over the existing validate_cli.py logic. Goal: replace
the multi-step interactive terminal flow (pick source -> pick database ->
pick schema -> pick table -> pick Snowflake table -> exclude y/n -> model
y/n -> confirm -> layer choice) with one page per workflow, using live
dropdowns (discovered from the actual database using .env credentials)
instead of sequential prompts.

This file does NOT reimplement any connection/matching/generation logic —
it imports and calls the same functions validate_cli.py and setup_wizard.py
use, so behavior (and correctness fixes made there) stays identical in both
places.

Run with:
    streamlit run webapp/app.py
"""

import difflib
import os
import sys
from pathlib import Path

_WEBAPP_DIR = Path(__file__).parent
_ROOT_DIR   = _WEBAPP_DIR.parent
_SRC_DIR    = _ROOT_DIR / "src"

for p in (str(_SRC_DIR), str(_ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st

from dotenv import load_dotenv
load_dotenv(_ROOT_DIR / ".env")

from setup_wizard import (
    print_connection_registry,
    _discover_postgres_databases, _discover_postgres_schemas,
    _discover_mssql_databases, _discover_mssql_schemas,
    _discover_snowflake_databases, _discover_snowflake_schemas,
)
from validate_cli import (
    _normalize_db_type, _DB_TYPE_LABELS, _apply_database_registry,
    _override_source_env, _make_source_extractor, _get_all_exclusions,
    _save_global_user_exclusion, _exclusions_path_for, STATIC_EXCLUDE_COLUMNS,
)
from validation_pipeline import ValidationPipeline
from sql_extractor import ExtractorFactory, SnowflakeExtractor
from rule_book import rule_book, RuleEntry, RuleValidationError
from ai_transformation.ai_rule_mapper import AVAILABLE_MODELS, MODEL_DESCRIPTIONS
from model_probe import get_working_models
import mapping_store

sys.path.insert(0, str(_ROOT_DIR / "token_usage_analysis"))
from report_token_usage import _load_records as _load_token_records, _load_pricing, _cost_for

st.set_page_config(page_title="Migration Validator", page_icon="🔄", layout="wide")

st.markdown("""
<style>
[data-testid="stTab"] {
    font-weight: 600;
}
[data-testid="stTab"][aria-selected="true"] {
    background: linear-gradient(90deg, #6C5CE7 0%, #A29BFE 100%);
    color: white !important;
    border-radius: 8px 8px 0 0;
}
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #F0F1FA 0%, #E4E7FB 100%);
    border: 1px solid #D6D8F5;
    border-radius: 10px;
    padding: 12px 16px;
}
div[data-testid="stMetricValue"] {
    color: #6C5CE7;
}
</style>
""", unsafe_allow_html=True)

SOURCE_TYPES = ("postgresql", "mssql", "athena")
_TYPE_MANUAL = "✏️  Type manually…"


# ---------------------------------------------------------------------------
# Flash-message / toast helper
# ---------------------------------------------------------------------------
# st.success(...) immediately followed by st.rerun() never actually shows —
# rerun tears down the current run before the message can render. The fix is
# to stash the message in session_state, rerun, and show it as a toast at the
# very top of the NEXT run (toasts persist briefly and are visible regardless
# of which tab is active, so it's obvious the save actually happened).

def flash(message: str, icon: str = "✅"):
    st.session_state["_flash"] = (message, icon)


def _show_pending_flash():
    pending = st.session_state.pop("_flash", None)
    if pending:
        message, icon = pending
        st.toast(message, icon=icon)


_show_pending_flash()


# ---------------------------------------------------------------------------
# Cached discovery calls — one live query per (host, creds, ...) combo, not
# re-run on every widget interaction elsewhere on the page.
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner="Discovering databases…")
def cached_source_databases(db_type, host, port, username, password, auth):
    if db_type == "postgresql":
        return _discover_postgres_databases(host, port, username, password)
    if db_type == "mssql":
        return _discover_mssql_databases(host, port, username, password, auth)
    return []  # Athena: database == fixed Glue database, no server-side listing


@st.cache_data(ttl=300, show_spinner="Discovering schemas…")
def cached_source_schemas(db_type, host, port, database, username, password, auth):
    if db_type == "postgresql":
        return _discover_postgres_schemas(host, port, database, username, password)
    if db_type == "mssql":
        return _discover_mssql_schemas(host, port, database, username, password, auth)
    return []  # Athena: schema == database, no separate listing


@st.cache_data(ttl=300, show_spinner="Loading tables…")
def cached_source_tables(db_type, host, port, database, username, password, auth, s3_output, schema):
    extractor = ExtractorFactory.create(
        db_type, host=host, port=port, database=database,
        username=username, password=password, auth=auth, s3_output=s3_output,
    )
    return extractor.list_tables(schema)


@st.cache_data(ttl=300, show_spinner="Loading columns…")
def cached_source_columns(db_type, host, port, database, username, password, auth, s3_output, schema, table):
    extractor = ExtractorFactory.create(
        db_type, host=host, port=port, database=database,
        username=username, password=password, auth=auth, s3_output=s3_output,
    )
    return [c.column_name for c in extractor.extract_columns(schema, table)]


@st.cache_data(ttl=300, show_spinner="Discovering Snowflake databases…")
def cached_sf_databases(account, username, password, warehouse, role):
    return _discover_snowflake_databases(account, username, password, warehouse, role)


@st.cache_data(ttl=300, show_spinner="Discovering Snowflake schemas…")
def cached_sf_schemas(account, database, username, password, warehouse, role):
    rows = _discover_snowflake_schemas(account, database, username, password, warehouse, role)
    return [r[0] for r in rows]


@st.cache_data(ttl=300, show_spinner="Loading Snowflake tables…")
def cached_sf_tables(database, schema):
    return SnowflakeExtractor(database=database).list_tables(schema)


# ---------------------------------------------------------------------------
# Shared UI helpers
# ---------------------------------------------------------------------------

def load_registry() -> list:
    """Configured source connections from .env, same as the CLI's picker."""
    try:
        registry = print_connection_registry(_ROOT_DIR / ".env")
    except Exception as exc:
        st.error(f"Could not read .env connections: {exc}")
        return []
    out = []
    for rec in registry:
        rec = dict(rec)
        rec["db_type"] = _normalize_db_type(rec["db_type"])
        rec = _apply_database_registry(rec)
        out.append(rec)
    return out


def connection_label(rec: dict) -> str:
    label = _DB_TYPE_LABELS.get(rec["db_type"], rec["db_type"])
    return f"SRC_{rec['index']}  ·  {label}  ·  {rec['host']}/{rec['database']}.{rec['schema']}"


def select_connection(registry: list, key: str):
    if not registry:
        st.warning("No source connections found in .env. Run the setup wizard first: `python src/validate_cli.py setup`")
        return None
    options = {connection_label(r): r for r in registry}
    chosen = st.selectbox("Source connection", list(options.keys()), key=key)
    return options[chosen]


def select_or_type(label: str, options: list, default: str, key: str, format_func=None) -> str:
    """A dropdown of live-discovered values, with a fallback to type a value
    manually (discovery can fail — driver missing, permissions, brand-new
    table not created yet, etc.) so the picker never becomes a dead end."""
    opts = list(dict.fromkeys(options))  # de-dupe, preserve order
    if default and default not in opts:
        opts = [default] + opts
    display_opts = opts + [_TYPE_MANUAL]
    default_idx = display_opts.index(default) if default in display_opts else 0
    kwargs = {"format_func": format_func} if format_func else {}
    choice = st.selectbox(label, display_opts, index=default_idx, key=f"{key}_sel", **kwargs)
    if choice == _TYPE_MANUAL:
        return st.text_input(f"{label} (type manually)", value=default or "", key=f"{key}_txt")
    return choice


@st.cache_data(ttl=300, show_spinner="Checking which AI models are reachable…")
def available_models_for_ui() -> list:
    """Dynamic model list — probes DIAL for reachability when a key is set,
    otherwise returns the full curated registry so the picker still works."""
    api_key = os.getenv("DIAL_API_KEY", "")
    if not api_key:
        return list(AVAILABLE_MODELS)
    try:
        working = get_working_models(
            AVAILABLE_MODELS, api_key,
            os.getenv("DIAL_API_BASE", ""), os.getenv("DIAL_API_VERSION", ""),
        )
        return working or list(AVAILABLE_MODELS)
    except Exception:
        return list(AVAILABLE_MODELS)


def _model_label(model_id: str) -> str:
    if model_id == _TYPE_MANUAL:
        return model_id
    info = MODEL_DESCRIPTIONS.get(model_id)
    if not info:
        return model_id
    vendor, display_name, description = info
    return f"{display_name}  ·  {vendor} — {description}"


def source_password(rec: dict) -> str:
    return os.getenv(f"{rec['prefix']}PASSWORD", "")


_LAYERS = ("bronze", "silver", "gold")


def pick_layer(key: str) -> tuple:
    """Medallion layer picker — mirrors the CLI's interactive '1) bronze
    2) silver 3) gold' prompt (validate_cli.py), which only ever ran in the
    terminal flow. Returns (layer_name, output_dir) where output_dir is where
    the generated YAML/SQL config files are written."""
    layer = st.selectbox(
        "Medallion layer — where to write the generated config",
        _LAYERS, index=0, key=key,
        help="Controls only the output folder for generated YAML/SQL configs (Project/config/<layer>/), "
             "not which Snowflake database/schema is queried — that's chosen above.",
    )
    return layer, _ROOT_DIR / "Project" / "config" / layer


def snowflake_creds() -> dict:
    return {
        "account":   os.getenv("SNOWFLAKE_ACCOUNT", ""),
        "username":  os.getenv("SNOWFLAKE_USERNAME", ""),
        "password":  os.getenv("SNOWFLAKE_PASSWORD", ""),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", ""),
        "role":      os.getenv("SNOWFLAKE_ROLE", ""),
        "database":  os.getenv("SNOWFLAKE_DATABASE", ""),
        "schema":    os.getenv("SNOWFLAKE_SCHEMA", ""),
    }


def pick_source_location(rec: dict, key_prefix: str):
    """Cascading database -> schema -> table picker for a source connection,
    all live-discovered using the credentials already in .env. Returns
    (database, schema, table_options, chosen_table_or_None)."""
    db_type  = rec["db_type"]
    password = source_password(rec)

    if db_type == "athena":
        st.caption(f"Athena database/schema is fixed to the Glue database configured in .env: **{rec['database']}**")
        database = rec["database"]
        schema   = rec["schema"]
    else:
        databases = cached_source_databases(db_type, rec["host"], int(rec.get("port") or 0), rec["username"], password, rec.get("auth", ""))
        c1, c2 = st.columns(2)
        with c1:
            database = select_or_type("Source database", databases, rec["database"], f"{key_prefix}_db")
        schemas = cached_source_schemas(db_type, rec["host"], int(rec.get("port") or 0), database, rec["username"], password, rec.get("auth", ""))
        with c2:
            schema = select_or_type("Source schema", schemas, rec["schema"], f"{key_prefix}_schema")

    try:
        tables = cached_source_tables(
            db_type, rec["host"], int(rec.get("port") or 0), database,
            rec["username"], password, rec.get("auth", ""), rec.get("s3_output", ""), schema,
        )
    except Exception as exc:
        st.error(f"Could not list tables: {exc}")
        tables = []

    return database, schema, tables


def pick_snowflake_target(default_table: str, key_prefix: str):
    """Cascading database -> schema -> table picker for the Snowflake target,
    live-discovered the same way as the source picker."""
    creds = snowflake_creds()
    databases = cached_sf_databases(creds["account"], creds["username"], creds["password"], creds["warehouse"], creds["role"])
    c1, c2 = st.columns(2)
    with c1:
        sf_database = select_or_type("Snowflake database", databases, creds["database"], f"{key_prefix}_sfdb")
    schemas = cached_sf_schemas(creds["account"], sf_database, creds["username"], creds["password"], creds["warehouse"], creds["role"])
    with c2:
        sf_schema = select_or_type("Snowflake schema", schemas, creds["schema"], f"{key_prefix}_sfschema")

    try:
        sf_tables = cached_sf_tables(sf_database, sf_schema)
    except Exception as exc:
        st.error(f"Could not list Snowflake tables: {exc}")
        sf_tables = []

    sf_table = select_or_type("Snowflake table", sf_tables, default_table, f"{key_prefix}_sftable")
    return sf_database, sf_schema, sf_table


# ---------------------------------------------------------------------------
# Sidebar — environment status, always visible regardless of active tab
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🔄 Migration Validator")

    _dial_key = os.getenv("DIAL_API_KEY", "")
    _claude_key = os.getenv("CLAUDE_API_KEY", "")
    if _dial_key:
        st.success(f"AI backend: DIAL ({os.getenv('DIAL_MODEL', 'gpt-4o')})", icon="🤖")
    elif _claude_key:
        st.success(f"AI backend: Claude ({os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')})", icon="🤖")
    else:
        st.error("No AI backend configured (DIAL_API_KEY / CLAUDE_API_KEY missing)", icon="⚠️")

    _sf_account = os.getenv("SNOWFLAKE_ACCOUNT", "")
    if _sf_account:
        st.info(f"Snowflake: {_sf_account}", icon="❄️")
    else:
        st.warning("Snowflake account not configured", icon="⚠️")

    st.divider()
    st.caption("Live dropdowns (databases/schemas/tables) are cached for 5 minutes.")
    if st.button("🔄 Refresh discovery cache", width='stretch'):
        st.cache_data.clear()
        flash("Discovery cache cleared — dropdowns will re-query live data.", icon="🔄")
        st.rerun()

    st.divider()
    st.caption("Token usage & cost for this session:")
    st.code("python token_usage_analysis/report_token_usage.py", language="bash")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("🔄 Migration Validator")
st.caption("PostgreSQL / MSSQL / Athena → Snowflake — pick everything from live dropdowns, powered by the credentials already in .env.")

tab_conn, tab_single, tab_batch, tab_rules, tab_excl, tab_usage = st.tabs(
    ["🔌 Connections", "▶️ Generate — Single Table", "📋 Generate — Batch", "📖 Rule Book", "🚫 Exclusions", "📊 Usage & Cost"]
)

# =============================================================================
# TAB: Connections
# =============================================================================
with tab_conn:
    st.subheader("Configured connections (read from .env — no setup needed here)")
    registry = load_registry()

    if not registry:
        st.info("No SRC_N_* connections found. Configure `.env` or run `python src/validate_cli.py setup`.")
    else:
        rows = [
            {
                "Slot": f"SRC_{r['index']}",
                "Type": _DB_TYPE_LABELS.get(r["db_type"], r["db_type"]),
                "Host": r["host"],
                "Database": r["database"],
                "Schema": r["schema"],
                "Username": r["username"],
            }
            for r in registry
        ]
        st.dataframe(rows, width='stretch', hide_index=True)

    st.divider()
    st.subheader("Snowflake target")
    sf = snowflake_creds()
    col1, col2 = st.columns(2)
    col1.metric("Database", sf["database"] or "not set")
    col2.metric("Schema", sf["schema"] or "not set")

    st.divider()
    if st.button("🔎 Test all connections"):
        results = []
        for rec in registry:
            try:
                extractor = _make_source_extractor(rec)
                extractor.list_tables(rec["schema"])
                results.append((connection_label(rec), True, ""))
            except Exception as exc:
                results.append((connection_label(rec), False, str(exc)))
        try:
            sf_ext = SnowflakeExtractor(database=sf["database"])
            sf_ext.list_tables(sf["schema"])
            results.append(("Snowflake (target)", True, ""))
        except Exception as exc:
            results.append(("Snowflake (target)", False, str(exc)))

        for label, ok, err in results:
            if ok:
                st.success(f"✓ {label}")
            else:
                st.error(f"✗ {label} — {err}")

# =============================================================================
# TAB: Generate — Single Table
# =============================================================================
with tab_single:
    st.subheader("Single table — pick source and target from live dropdowns")
    registry = load_registry()
    rec = select_connection(registry, key="single_conn")

    if rec:
        _override_source_env(rec)
        src_db_type = rec["db_type"]

        with st.container(border=True):
            st.markdown("**① Source**")
            database, schema, table_options = pick_source_location(rec, "single")
            source_table = select_or_type("Source table", table_options, "", "single_table")

        with st.container(border=True):
            st.markdown("**② Target (Snowflake)**")
            suggested_sf_table = source_table.upper() if source_table else ""
            sf_database, sf_schema, sf_table = pick_snowflake_target(suggested_sf_table, "single")

        # ── Exclusions: pre-filled with auto-exclusions, real column list ──
        auto_excluded = set(_get_all_exclusions(src_db_type))
        col_names = []
        if source_table:
            try:
                col_names = cached_source_columns(
                    src_db_type, rec["host"], int(rec.get("port") or 0), database,
                    rec["username"], source_password(rec), rec.get("auth", ""),
                    rec.get("s3_output", ""), schema, source_table,
                )
            except Exception as exc:
                st.warning(f"Could not load columns for exclusion picker: {exc}")

        st.markdown("**③ Columns to exclude** (auto-excluded columns are pre-checked)")
        excluded_cols = st.multiselect(
            "Exclude these columns from validation",
            options=col_names,
            default=[c for c in col_names if c.lower() in auto_excluded],
            key="single_excl",
            label_visibility="collapsed",
        )

        model = select_or_type(
            "AI model", available_models_for_ui(), os.getenv("DIAL_MODEL", "gpt-4o"),
            "single_model", format_func=_model_label,
        )
        layer, output_dir = pick_layer("single_layer")

        if st.button("▶️ Generate SQL + YAML", type="primary", key="single_generate"):
            if not source_table or not sf_table:
                st.error("Source table and Snowflake table are required.")
            else:
                with st.spinner(f"Running pipeline for {source_table} → {sf_table} ..."):
                    try:
                        extractor = ExtractorFactory.create(
                            src_db_type, host=rec["host"], port=int(rec.get("port") or 0),
                            database=database, username=rec["username"], password=source_password(rec),
                            auth=rec.get("auth", ""), s3_output=rec.get("s3_output", ""),
                        )
                        pipeline = ValidationPipeline(model=model, source_extractor=extractor)
                        result = pipeline.run(
                            pg_schema=schema,
                            pg_table=source_table,
                            sf_schema=sf_schema,
                            sf_table=sf_table,
                            sf_database=sf_database,
                            pg_database=database,
                            exclude_columns=excluded_cols or None,
                            source_db_type=src_db_type,
                            output_dir=output_dir,
                        )
                        st.success(f"Generated for {result.table_name}")
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Active columns", result.active_columns)
                        m2.metric("Skipped columns", len(result.skipped_columns))
                        m3.metric("Generated by", f"{result.generated_by} ({result.model_used})")
                        if result.coverage_headline:
                            st.info(result.coverage_headline)
                        st.write("**Output files:**")
                        st.code(str(result.yaml_path))
                        if result.count_yaml_path:
                            st.code(str(result.count_yaml_path))
                    except Exception as exc:
                        st.error(f"Generation failed: {exc}")

# =============================================================================
# TAB: Generate — Batch
# =============================================================================
with tab_batch:
    st.subheader("Batch — pick source/target once, map every table explicitly")
    registry = load_registry()
    rec = select_connection(registry, key="batch_conn")

    if rec:
        _override_source_env(rec)
        src_db_type = rec["db_type"]

        with st.container(border=True):
            st.markdown("**① Source**")
            database, schema, table_options = pick_source_location(rec, "batch")
            source_tables = st.multiselect(
                "Tables to validate — select N source tables",
                options=table_options,
                key="batch_tables_select",
            )
            if not table_options:
                st.caption("Table list unavailable — type names manually below (comma-separated).")
                manual_raw = st.text_input("Table names (comma-separated)", key="batch_tables_manual")
                source_tables = [t.strip() for t in manual_raw.split(",") if t.strip()]

        with st.container(border=True):
            st.markdown("**② Target (Snowflake)**")
            sf_database, sf_schema, _ = pick_snowflake_target("", "batch")

            sf_tables_live = []
            if sf_database and sf_schema:
                try:
                    sf_tables_live = cached_sf_tables(sf_database, sf_schema)
                except Exception as exc:
                    st.warning(f"Could not list Snowflake tables for mapping: {exc}")

        target_map: dict = {}
        ambiguous_tables: set = set()
        if source_tables:
            st.markdown("**③ Map each source table to its Snowflake target — review before generating**")

            creds = snowflake_creds()
            confirmed_mappings = {}
            if sf_database and sf_schema and creds["account"]:
                confirmed_mappings = mapping_store.load_confirmed_mappings(
                    creds["account"], creds["username"], creds["password"], sf_database, sf_schema,
                )

            # Suggest a target the same way the CLI does: exact upper() match,
            # else closest fuzzy match, else the plain upper() guess. A source
            # table is flagged ambiguous when 2+ Snowflake tables are equally
            # plausible (e.g. ADDRESS vs ADDRESSES) — those are left blank so
            # a person has to pick, instead of silently guessing wrong.
            upper_sf = {t.upper(): t for t in sf_tables_live}

            def suggest(src_table: str) -> tuple:
                """Returns (suggested_target, status) where status is one of:
                confirmed / exact / ambiguous / not_found / no_data. Only
                'exact' and 'confirmed' are safe to silently pre-fill — every
                other status leaves the target blank so a human has to pick,
                rather than guessing a Snowflake table name that may not
                exist (the ACCTSOFTWARE-style failure this guards against)."""
                if src_table in confirmed_mappings:
                    return confirmed_mappings[src_table], "confirmed"
                exact = upper_sf.get(src_table.upper())
                if exact:
                    return exact, "exact"
                if not sf_tables_live:
                    # Live Snowflake table discovery failed entirely — nothing
                    # to compare against, fall back to a plain guess (the
                    # manual-entry dropdown still lets a human override it).
                    return src_table.upper(), "no_data"
                close = difflib.get_close_matches(src_table.upper(), list(upper_sf.keys()), n=3, cutoff=0.4)
                if len(close) >= 2:
                    return "", "ambiguous"
                if len(close) == 1:
                    return upper_sf[close[0]], "fuzzy"
                return "", "not_found"

            suggestions = {t: suggest(t) for t in source_tables}
            ambiguous_tables = {t for t, (_, status) in suggestions.items() if status == "ambiguous"}
            not_found_tables = {t for t, (_, status) in suggestions.items() if status == "not_found"}
            select_options = sorted(set(sf_tables_live) | {s for s, _ in suggestions.values() if s})

            _STATUS_LABELS = {
                "confirmed": "✓ Previously confirmed",
                "exact": "",
                "fuzzy": "",
                "ambiguous": "⚠️ Ambiguous — pick manually",
                "not_found": "⚠️ No close match found — pick manually",
                "no_data": "⚠️ Could not verify (Snowflake table list unavailable)",
            }

            def status_for(src_table: str) -> str:
                return _STATUS_LABELS[suggestions[src_table][1]]

            import pandas as pd
            mapping_df = pd.DataFrame({
                "Source Table": source_tables,
                "Snowflake Target Table": [suggestions[t][0] for t in source_tables],
                "Status": [status_for(t) for t in source_tables],
            })

            edited_df = st.data_editor(
                mapping_df,
                column_config={
                    "Source Table": st.column_config.TextColumn(disabled=True),
                    "Snowflake Target Table": st.column_config.SelectboxColumn(
                        options=select_options, required=True,
                        help="Auto-suggested via exact/fuzzy match against live Snowflake tables — override if wrong.",
                    ),
                    "Status": st.column_config.TextColumn(disabled=True),
                },
                hide_index=True,
                width='stretch',
                key="batch_mapping_editor",
            )
            target_map = dict(zip(edited_df["Source Table"], edited_df["Snowflake Target Table"]))

            # ── Quality checks on the mapping before allowing Generate ──────
            empty_targets = [s for s, t in target_map.items() if not t]
            target_counts: dict = {}
            for t in target_map.values():
                if t:
                    target_counts[t] = target_counts.get(t, 0) + 1
            duplicate_targets = [t for t, n in target_counts.items() if n > 1]

            if ambiguous_tables:
                st.warning(
                    f"Ambiguous target for: {', '.join(sorted(ambiguous_tables))} — "
                    f"multiple Snowflake tables matched closely, pick the correct one in the grid above."
                )
            if not_found_tables:
                st.warning(
                    f"No confident Snowflake match for: {', '.join(sorted(not_found_tables))} — "
                    f"pick the correct target manually in the grid above (nothing was auto-filled to avoid guessing wrong)."
                )
            if empty_targets:
                st.error(f"Missing target table for: {', '.join(empty_targets)}")
            if duplicate_targets:
                st.error(
                    f"Two or more source tables are mapped to the same Snowflake target "
                    f"({', '.join(duplicate_targets)}) — each source table needs a distinct target."
                )
            mapping_valid = source_tables and not empty_targets and not duplicate_targets
            if mapping_valid:
                st.success(f"{len(source_tables)} source table(s) mapped to {len(source_tables)} distinct target(s) — ready to generate.")

        st.markdown("**④ Columns to exclude** (per table — auto-excluded columns are pre-checked)")
        auto_excluded = _get_all_exclusions(src_db_type)
        st.caption(f"Auto-excluded for {_DB_TYPE_LABELS.get(src_db_type, src_db_type)}: {', '.join(auto_excluded) or '(none)'}")

        per_table_excl: dict = {}
        for src_table in source_tables:
            with st.expander(f"Columns to exclude — {src_table}", expanded=False):
                try:
                    table_cols = cached_source_columns(
                        src_db_type, rec["host"], int(rec.get("port") or 0), database,
                        rec["username"], source_password(rec), rec.get("auth", ""),
                        rec.get("s3_output", ""), schema, src_table,
                    )
                except Exception as exc:
                    st.warning(f"Could not load columns for {src_table}: {exc}")
                    table_cols = []
                per_table_excl[src_table] = st.multiselect(
                    f"Exclude these columns from {src_table}",
                    options=table_cols,
                    default=[c for c in table_cols if c.lower() in set(auto_excluded)],
                    key=f"batch_excl_{src_table}",
                    label_visibility="collapsed",
                )

        model = select_or_type(
            "AI model", available_models_for_ui(), os.getenv("DIAL_MODEL", "gpt-4o"),
            "batch_model", format_func=_model_label,
        )
        layer, output_dir = pick_layer("batch_layer")

        generate_disabled = not source_tables or not target_map or any(not t for t in target_map.values()) or (
            len(set(target_map.values())) != len(target_map)
        )
        if st.button("▶️ Generate All", type="primary", key="batch_generate", disabled=generate_disabled):
            extractor = ExtractorFactory.create(
                src_db_type, host=rec["host"], port=int(rec.get("port") or 0),
                database=database, username=rec["username"], password=source_password(rec),
                auth=rec.get("auth", ""), s3_output=rec.get("s3_output", ""),
            )
            progress = st.progress(0.0, text="Starting...")
            results = []
            pairs = list(target_map.items())
            for i, (src_table, tgt_table) in enumerate(pairs, 1):
                progress.progress(i / len(pairs), text=f"{src_table} → {tgt_table}  ({i}/{len(pairs)})")
                try:
                    pipeline = ValidationPipeline(model=model, source_extractor=extractor)
                    result = pipeline.run(
                        pg_schema=schema,
                        pg_table=src_table,
                        sf_schema=sf_schema,
                        sf_table=tgt_table,
                        sf_database=sf_database,
                        pg_database=database,
                        exclude_columns=(list(auto_excluded) + per_table_excl.get(src_table, [])) or None,
                        source_db_type=src_db_type,
                        output_dir=output_dir,
                    )
                    results.append({
                        "Source": src_table, "Target": tgt_table, "Status": "✅ Success",
                        "Detail": f"{result.active_columns} cols, {result.generated_by}",
                    })
                    creds = snowflake_creds()
                    if creds["account"]:
                        mapping_store.save_mapping(
                            creds["account"], creds["username"], creds["password"],
                            sf_database, sf_schema, src_table, tgt_table,
                            confirmed_by=creds["username"], source_connection=connection_label(rec),
                        )
                except Exception as exc:
                    results.append({"Source": src_table, "Target": tgt_table, "Status": "❌ Failed", "Detail": str(exc)})
            progress.empty()

            st.dataframe(results, width='stretch', hide_index=True)
            n_ok = sum(1 for r in results if r["Status"].startswith("✅"))
            if n_ok == len(results):
                st.success(f"Batch complete: {n_ok}/{len(results)} table(s) generated successfully.")
            else:
                st.warning(f"Batch complete: {n_ok}/{len(results)} table(s) generated successfully — see failures above.")

# =============================================================================
# TAB: Rule Book
# =============================================================================
with tab_rules:
    st.subheader("Rule book")
    stats = rule_book.stats()
    m1, m2, m3 = st.columns(3)
    m1.metric("Base rules", stats["base_rules"])
    m2.metric("Learned rules", stats["learned_rules"])
    m3.metric("Total", stats["total_rules"])

    def rule_rows(entries):
        return [
            {
                "ID": e.id, "Name": e.display_name,
                "Source type": e.source_type, "Target type": e.target_type,
                "Description": e.description,
            }
            for e in entries
        ]

    st.markdown("**Base rules** (code-defined, `src/rules/postgres_base_rules.py`)")
    st.dataframe(rule_rows(rule_book.base_rules()), width='stretch', hide_index=True)

    st.markdown("**Learned rules** (`src/rule_book_learned.json`)")
    learned = rule_book.learned_rules()
    if learned:
        st.dataframe(rule_rows(learned), width='stretch', hide_index=True)
    else:
        st.caption("No learned rules yet.")

    st.divider()
    st.markdown("**Add a custom (learned) rule**")
    st.caption("No code change, no redeploy — this is metadata that guides the AI, not a code override of the deterministic rule registry.")
    with st.form("add_rule_form"):
        c1, c2 = st.columns(2)
        rule_id = c1.text_input("Rule id (snake_case)")
        display_name = c2.text_input("Display name")
        description = st.text_area("Description")
        when_to_apply = st.text_input("When to apply (e.g. 'source=VARCHAR maps to target=STRING')")
        c3, c4 = st.columns(2)
        source_type = c3.text_input("Source type (e.g. VARCHAR)")
        target_type = c4.text_input("Target type (e.g. STRING)")
        c5, c6 = st.columns(2)
        pg_sql_template = c5.text_input("Source SQL template (use {col})")
        sf_sql_template = c6.text_input("Snowflake SQL template (use {col})")
        submitted = st.form_submit_button("Save learned rule")

        if submitted:
            if not rule_id or not display_name:
                st.error("Rule id and display name are required.")
            else:
                import datetime
                entry = RuleEntry(
                    id=rule_id, display_name=display_name, description=description,
                    when_to_apply=when_to_apply, pg_sql_template=pg_sql_template,
                    sf_sql_template=sf_sql_template, source_type=source_type,
                    target_type=target_type, is_learned=True,
                    learned_at=datetime.date.today().isoformat(),
                )
                try:
                    ok = rule_book.save_learned_rule(entry)
                except RuleValidationError as exc:
                    st.error(f"Rejected: {exc}")
                    ok = None
                if ok:
                    flash(f"Learned rule '{rule_id}' saved to rule_book_learned.json", icon="📖")
                    st.rerun()
                elif ok is not None:
                    st.error("Could not save — a rule with this id may already exist.")

# =============================================================================
# TAB: Exclusions
# =============================================================================
with tab_excl:
    st.subheader("Per-source exclusion policy")
    st.caption("One file per source type — every entry applies to BOTH that source and the Snowflake target.")

    for db_type in SOURCE_TYPES:
        label = _DB_TYPE_LABELS.get(db_type, db_type)
        path = _exclusions_path_for(db_type)
        with st.expander(f"{label}  —  {path.name}", expanded=False):
            all_excl = _get_all_exclusions(db_type)
            static_set = {c.lower() for c in STATIC_EXCLUDE_COLUMNS}
            user_excl = [c for c in all_excl if c not in static_set]
            st.write("**Static (built-in):**", ", ".join(STATIC_EXCLUDE_COLUMNS))
            st.write("**User-saved global exclusions:**", ", ".join(user_excl) or "(none)")

    st.divider()
    st.markdown("**Add a new global exclusion**")
    with st.form("add_exclusion_form"):
        col_names = st.text_input("Column name(s), comma-separated")
        reason = st.text_input("Reason", value="User-defined global exclusion")
        targets = st.multiselect(
            "Applies to source type(s)",
            options=[_DB_TYPE_LABELS.get(t, t) for t in SOURCE_TYPES],
            default=[],
        )
        submitted = st.form_submit_button("Save exclusion")

        if submitted:
            cols = [c.strip() for c in col_names.split(",") if c.strip()]
            label_to_type = {_DB_TYPE_LABELS.get(t, t): t for t in SOURCE_TYPES}
            chosen_types = [label_to_type[t] for t in targets]
            if not cols or not chosen_types:
                st.error("Enter at least one column name and pick at least one source type.")
            else:
                for db_type in chosen_types:
                    for col in cols:
                        _save_global_user_exclusion(db_type, col, reason)
                flash(f"Saved {len(cols)} column(s) to exclusions for {', '.join(targets)}", icon="🚫")
                st.rerun()

# =============================================================================
# TAB: Usage & Cost
# =============================================================================
with tab_usage:
    import datetime
    from collections import defaultdict

    st.subheader("AI token usage & estimated cost")
    st.caption(
        "Real token counts from every AI call (column mapping + SQL generation), "
        "logged to token_usage_analysis/logs/token_usage.jsonl. Cost is estimated "
        "from public list prices — see token_usage_analysis/pricing.json."
    )

    records = _load_token_records()
    pricing = _load_pricing()

    if not records:
        st.info("No AI calls logged yet. Run a Single Table or Batch generation with an AI key configured.")
    else:
        def _record_date(r: dict):
            try:
                return datetime.datetime.strptime(r["timestamp"], "%Y-%m-%dT%H:%M:%S").date()
            except Exception:
                return None

        today = datetime.date.today()
        last_7 = today - datetime.timedelta(days=6)

        today_records = [r for r in records if _record_date(r) == today]
        week_records = [r for r in records if (d := _record_date(r)) and last_7 <= d <= today]

        def _totals(recs):
            tokens = sum(r.get("total_tokens", 0) for r in recs)
            cost = sum(_cost_for(r.get("model", "unknown"), r.get("prompt_tokens", 0), r.get("completion_tokens", 0), pricing) for r in recs)
            return tokens, cost

        today_tokens, today_cost = _totals(today_records)
        week_tokens, week_cost = _totals(week_records)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Today — cost", f"${today_cost:.4f}")
        c2.metric("Today — tokens", f"{today_tokens:,}")
        c3.metric("Last 7 days — cost", f"${week_cost:.4f}")
        c4.metric("Last 7 days — tokens", f"{week_tokens:,}")
        c5.metric("Last 7 days — AI calls", f"{len(week_records):,}")

        st.markdown("**Daily cost — last 7 days**")
        daily_cost = defaultdict(float)
        for d_offset in range(6, -1, -1):
            daily_cost[(today - datetime.timedelta(days=d_offset)).isoformat()] = 0.0
        for r in week_records:
            d = _record_date(r)
            if d:
                daily_cost[d.isoformat()] += _cost_for(
                    r.get("model", "unknown"), r.get("prompt_tokens", 0), r.get("completion_tokens", 0), pricing
                )
        import pandas as pd
        chart_df = pd.DataFrame({"Date": list(daily_cost.keys()), "Cost (USD)": list(daily_cost.values())}).set_index("Date")
        st.bar_chart(chart_df)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Last 7 days — by model**")
            by_model = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})
            for r in week_records:
                m = r.get("model", "unknown")
                by_model[m]["calls"] += 1
                by_model[m]["tokens"] += r.get("total_tokens", 0)
                by_model[m]["cost"] += _cost_for(m, r.get("prompt_tokens", 0), r.get("completion_tokens", 0), pricing)
            st.dataframe(
                [{"Model": m, "Calls": s["calls"], "Tokens": s["tokens"], "Cost (USD)": round(s["cost"], 4)} for m, s in sorted(by_model.items())],
                width='stretch', hide_index=True,
            )
        with col_b:
            st.markdown("**Last 7 days — by call type**")
            by_type = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})
            for r in week_records:
                t = r.get("call_type", "unknown")
                by_type[t]["calls"] += 1
                by_type[t]["tokens"] += r.get("total_tokens", 0)
                by_type[t]["cost"] += _cost_for(r.get("model", "unknown"), r.get("prompt_tokens", 0), r.get("completion_tokens", 0), pricing)
            st.dataframe(
                [{"Call type": t, "Calls": s["calls"], "Tokens": s["tokens"], "Cost (USD)": round(s["cost"], 4)} for t, s in sorted(by_type.items())],
                width='stretch', hide_index=True,
            )

        st.divider()
        all_tokens, all_cost = _totals(records)
        st.caption(f"All-time: {len(records):,} AI calls · {all_tokens:,} tokens · ${all_cost:.4f} estimated cost.")
        st.code("python token_usage_analysis/report_token_usage.py --all", language="bash")
