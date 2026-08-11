"""
Connection Health Checker
=========================
Run this FIRST before running main_dynamic.py.
It verifies every dependency and every database connection individually
so you know exactly what works and what doesn't.

Usage
-----
  cd src
  python check_connections.py

Exit codes
----------
  0  — All checks passed
  1  — One or more checks failed (details printed)
"""

import os
import sys
from pathlib import Path

# ── Load .env from project root ──────────────────────────────────────────────
_root = Path(__file__).parent.parent
_env_file = _root / ".env"

try:
    from dotenv import load_dotenv
    load_dotenv(_env_file)
    print(f"  ✓ Loaded .env from: {_env_file}")
except ImportError:
    print("  ⚠ python-dotenv not installed — reading OS environment only")

# ── Colour helpers (works on Windows 10+ with ANSI enabled) ──────────────────
OK   = "  ✓"
FAIL = "  ✗"
WARN = "  ⚠"
SEP  = "=" * 65


def section(title: str):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


# =============================================================================
# STEP 1 — Python packages
# =============================================================================

def check_packages() -> bool:
    section("STEP 1 — Python Package Check")
    all_ok = True

    packages = [
        ("dotenv",                "python-dotenv",               "pip install python-dotenv"),
        ("psycopg2",              "psycopg2-binary",              "pip install psycopg2-binary"),
        ("snowflake.connector",   "snowflake-connector-python",   "pip install snowflake-connector-python"),
        ("openai",                "openai",                       "pip install openai>=1.0.0"),
    ]

    for module, pkg_name, install_cmd in packages:
        try:
            __import__(module)
            print(f"{OK} {pkg_name}")
        except ImportError:
            print(f"{FAIL} {pkg_name} NOT FOUND  →  run: {install_cmd}")
            all_ok = False

    return all_ok


# =============================================================================
# STEP 2 — Environment variables
# =============================================================================

def check_env_vars() -> bool:
    section("STEP 2 — Environment Variable Check")
    all_ok = True

    required = {
        "SOURCE_HOST":       os.getenv("SOURCE_HOST"),
        "SOURCE_PORT":       os.getenv("SOURCE_PORT"),
        "SOURCE_DATABASE":   os.getenv("SOURCE_DATABASE"),
        "SOURCE_SCHEMA":     os.getenv("SOURCE_SCHEMA"),
        "SOURCE_USERNAME":   os.getenv("SOURCE_USERNAME"),
        "SOURCE_PASSWORD":   os.getenv("SOURCE_PASSWORD"),
        "SNOWFLAKE_ACCOUNT": os.getenv("SNOWFLAKE_ACCOUNT"),
        "SNOWFLAKE_DATABASE":os.getenv("SNOWFLAKE_DATABASE"),
        "SNOWFLAKE_SCHEMA":  os.getenv("SNOWFLAKE_SCHEMA"),
        "SNOWFLAKE_USERNAME":os.getenv("SNOWFLAKE_USERNAME"),
        "SNOWFLAKE_PASSWORD":os.getenv("SNOWFLAKE_PASSWORD"),
    }

    optional = {
        "DIAL_API_KEY":     os.getenv("DIAL_API_KEY"),
        "DIAL_API_BASE":    os.getenv("DIAL_API_BASE"),
        "DIAL_MODEL":       os.getenv("DIAL_MODEL"),
    }

    print("  Required variables:")
    for name, val in required.items():
        if val:
            masked = val[:4] + "****" if "PASSWORD" in name or "KEY" in name else val
            print(f"  {OK} {name} = {masked}")
        else:
            print(f"  {FAIL} {name} is NOT SET  →  edit your .env file")
            all_ok = False

    print("\n  Optional variables (needed for AI mode):")
    for name, val in optional.items():
        if val:
            masked = val[:8] + "****" if "KEY" in name else val
            print(f"  {OK} {name} = {masked}")
        else:
            print(f"  {WARN} {name} is not set  →  AI mode disabled, static fallback will be used")

    return all_ok


# =============================================================================
# STEP 3 — PostgreSQL connection
# =============================================================================

def check_postgres() -> bool:
    section("STEP 3 — PostgreSQL Connection")

    host     = os.getenv("SOURCE_HOST", "localhost")
    port     = int(os.getenv("SOURCE_PORT", "5432"))
    database = os.getenv("SOURCE_DATABASE", "postgres")
    user     = os.getenv("SOURCE_USERNAME", "postgres")
    password = os.getenv("SOURCE_PASSWORD", "")
    schema   = os.getenv("SOURCE_SCHEMA", "public")

    print(f"  Connecting to: {host}:{port}/{database} (schema={schema}) as {user}")

    try:
        import psycopg2
        conn = psycopg2.connect(
            host=host, port=port,
            database=database,
            user=user, password=password,
            connect_timeout=10,
        )
        cursor = conn.cursor()

        # 1. Server version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"{OK} Connection established")
        print(f"  │  Server : {version[:60]}")

        # 2. List tables in schema
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY table_name;
            """,
            (schema,),
        )
        tables = [r[0] for r in cursor.fetchall()]

        if tables:
            print(f"{OK} Schema '{schema}' has {len(tables)} table(s):")
            for t in tables[:10]:
                # Row count per table
                cursor.execute(f"SELECT COUNT(*) FROM {schema}.{t};")
                cnt = cursor.fetchone()[0]
                print(f"  │    • {t:<40} {cnt:>10,} rows")
            if len(tables) > 10:
                print(f"  │    ... and {len(tables) - 10} more")
        else:
            print(f"{WARN} Schema '{schema}' exists but has NO tables.")
            print(f"  │  Check SOURCE_SCHEMA in your .env file.")

        cursor.close()
        conn.close()
        return True

    except Exception as exc:
        print(f"{FAIL} PostgreSQL connection FAILED: {exc}")
        print(f"\n  Troubleshooting tips:")
        print(f"    1. Is PostgreSQL running?  →  pg_isready -h {host} -p {port}")
        print(f"    2. Correct database name?  →  psql -U {user} -l")
        print(f"    3. Firewall / VPN blocking port {port}?")
        print(f"    4. Check SOURCE_PASSWORD in .env")
        return False


# =============================================================================
# STEP 4 — Snowflake connection
# =============================================================================

def check_snowflake() -> bool:
    section("STEP 4 — Snowflake Connection")

    account  = os.getenv("SNOWFLAKE_ACCOUNT", "")
    database = os.getenv("SNOWFLAKE_DATABASE", "")
    schema   = os.getenv("SNOWFLAKE_SCHEMA", "")
    user     = os.getenv("SNOWFLAKE_USERNAME", "")
    password = os.getenv("SNOWFLAKE_PASSWORD", "")

    print(f"  Connecting to: {account}/{database}.{schema} as {user}")

    try:
        import snowflake.connector
        conn = snowflake.connector.connect(
            user=user,
            password=password,
            account=account,
            database=database,
            schema=schema,
            login_timeout=30,
        )
        cursor = conn.cursor()

        # 1. Server version
        cursor.execute("SELECT CURRENT_VERSION(), CURRENT_DATABASE(), CURRENT_SCHEMA();")
        row = cursor.fetchone()
        print(f"{OK} Connection established")
        print(f"  │  Snowflake version : {row[0]}")
        print(f"  │  Active DB         : {row[1]}")
        print(f"  │  Active Schema     : {row[2]}")

        # 2. List tables in schema
        cursor.execute(
            f"""
            SELECT TABLE_NAME, ROW_COUNT
            FROM {database}.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME;
            """,
            (schema.upper(),),
        )
        tables = cursor.fetchall()

        if tables:
            print(f"{OK} Schema '{schema}' has {len(tables)} table(s):")
            for t_name, t_rows in tables[:10]:
                row_str = f"{t_rows:>10,}" if t_rows is not None else "       N/A"
                print(f"  │    • {t_name:<40} {row_str} rows")
            if len(tables) > 10:
                print(f"  │    ... and {len(tables) - 10} more")
        else:
            print(f"{WARN} Schema '{schema}' exists but has NO tables.")
            print(f"  │  Check SNOWFLAKE_SCHEMA in your .env file.")

        cursor.close()
        conn.close()
        return True

    except Exception as exc:
        print(f"{FAIL} Snowflake connection FAILED: {exc}")
        print(f"\n  Troubleshooting tips:")
        print(f"    1. Account format: ORG_NAME-ACCOUNT_NAME  e.g. ZJAUJWQ-EP12783")
        print(f"    2. Verify credentials work at: https://app.snowflake.com")
        print(f"    3. Check SNOWFLAKE_DATABASE / SNOWFLAKE_SCHEMA exist")
        print(f"    4. Ensure MFA is not required (or use keypair auth)")
        print(f"    5. Are you on EPAM VPN?")
        return False


# =============================================================================
# STEP 5 — AI / DIAL connection (optional)
# =============================================================================

def check_dial() -> bool:
    section("STEP 5 — AI / DIAL API Check (Optional)")

    api_key  = os.getenv("DIAL_API_KEY", "")
    api_base = os.getenv("DIAL_API_BASE", "https://ai-proxy.lab.epam.com")
    api_ver  = os.getenv("DIAL_API_VERSION", "2025-04-01-preview")
    model    = os.getenv("DIAL_MODEL", "gpt-4o")

    if not api_key:
        print(f"{WARN} DIAL_API_KEY is not set.")
        print(f"  │  AI mode will be DISABLED — static rule matching will be used.")
        print(f"  │  To enable AI: add DIAL_API_KEY=<your-key> to .env")
        return True   # Not a fatal error

    print(f"  Testing DIAL endpoint: {api_base}")
    print(f"  Model: {model}")

    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_ver,
            azure_endpoint=api_base,
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            temperature=0,
            max_tokens=5,
            extra_headers={"Api-Key": api_key},
        )
        reply = response.choices[0].message.content.strip()
        print(f"{OK} DIAL API responded: '{reply}'")
        print(f"  │  AI mode is ACTIVE — GPT-4o will generate validation queries")
        return True

    except Exception as exc:
        print(f"{WARN} DIAL API check failed: {exc}")
        print(f"  │  AI mode will fall back to static rule matching.")
        print(f"  │  Check: EPAM VPN connected? DIAL_API_KEY valid?")
        return True   # Still not fatal — static fallback exists


# =============================================================================
# STEP 6 — Import check (src modules)
# =============================================================================

def check_src_imports() -> bool:
    section("STEP 6 — Source Module Import Check")
    all_ok = True

    # Add src/ to path
    src_dir = str(Path(__file__).parent)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    modules = [
        ("models",            "Data models (DatabaseConfig, ColumnMapping…)"),
        ("schema_discovery",  "Schema introspection helpers"),
        ("schema_extractor",  "Live schema extractor (PG + Snowflake)"),
        ("ai_query_agent",    "AI / DIAL query agent"),
        ("database_connectors","Database connector classes"),
        ("sql_generators",    "SQL generation engine"),
        ("transformation_rules","Rule application engine"),
        ("report_generator",  "HTML/JSON/TXT report writer"),
        ("dynamic_validator", "Main dynamic validation orchestrator"),
    ]

    for mod_name, description in modules:
        try:
            __import__(mod_name)
            print(f"{OK} {mod_name:<25}  {description}")
        except Exception as exc:
            print(f"{FAIL} {mod_name:<25}  IMPORT ERROR: {exc}")
            all_ok = False

    return all_ok


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(f"\n{SEP}")
    print(f"  MIGRATION VALIDATOR — CONNECTION & SETUP HEALTH CHECK")
    print(SEP)
    print(f"  Project root : {_root}")
    print(f"  .env file    : {_env_file}  ({'FOUND' if _env_file.exists() else 'NOT FOUND — create it!'})")
    print(f"  Python       : {sys.version.split()[0]}")

    results = {
        "Packages"       : check_packages(),
        "Env Vars"       : check_env_vars(),
        "PostgreSQL"     : check_postgres(),
        "Snowflake"      : check_snowflake(),
        "DIAL / AI"      : check_dial(),
        "Src Imports"    : check_src_imports(),
    }

    # ── Final summary ────────────────────────────────────────────────────
    section("SUMMARY")
    all_passed = True
    for name, passed in results.items():
        icon = OK if passed else FAIL
        status = "PASS" if passed else "FAIL"
        print(f"  {icon} {name:<20} {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("  ✅ ALL CHECKS PASSED — you are ready to run:")
        print()
        print("       cd src")
        print("       python main_dynamic.py")
        print()
    else:
        print("  ❌ SOME CHECKS FAILED — fix the issues above first.")
        print("     Then re-run:  python check_connections.py")
        print()

    print(SEP)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
