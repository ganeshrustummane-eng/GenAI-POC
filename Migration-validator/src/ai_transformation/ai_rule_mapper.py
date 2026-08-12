"""
AI Rule Mapper
===============
Uses DIAL/GPT-4o (or any configured model) to intelligently assign the correct
validation rules to each PostgreSQL → Snowflake column pair.

Why AI over static matching:
  - Handles renamed columns (customer_id → cust_id) via semantic understanding.
  - Detects primary keys from context and naming conventions.
  - Produces a reasoning explanation for audit/review.
  - Automatically falls back to StaticRuleMapper on any failure.

Supported AI Models (via EPAM DIAL):
  - gpt-4o            (default — best accuracy)
  - gpt-4o-mini       (faster, lower cost)
  - gpt-4-turbo
  - claude-3-5-sonnet (via DIAL bridge)
  - gemini-pro        (via DIAL bridge)
  - Any model available on your DIAL endpoint

Model Selection:
  1. Pass model= parameter to AIRuleMapper(model="gpt-4o-mini")
  2. Set DIAL_MODEL env var in .env
  3. Select interactively from the CLI (validate_cli.py)

Environment Variables Required:
  DIAL_API_KEY      — EPAM DIAL API key (requires VPN)
  DIAL_API_BASE     — defaults to https://ai-proxy.lab.epam.com
  DIAL_API_VERSION  — defaults to 2025-04-01-preview
  DIAL_MODEL        — defaults to gpt-4o
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from sql_extractor.extractors import ColumnMetadata
from ai_transformation.static_rule_mapper import StaticRuleMapper, ColumnRuleMapping
from rules import get_rule_for_type

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_API_BASE    = "https://ai-proxy.lab.epam.com"
_DEFAULT_API_VERSION = "2025-04-01-preview"
_DEFAULT_MODEL       = "gpt-4o"
_CATALOG_PATH        = Path(__file__).parent.parent / "rules_catalog.json"

# Fivetran metadata column prefix — skip these in validation
_FIVETRAN_PREFIX = "_FIVETRAN_"

# ---------------------------------------------------------------------------
# Available DIAL models — shown to user in CLI model selection
# ---------------------------------------------------------------------------

AVAILABLE_MODELS = [
    # ── OpenAI GPT-5 tier ───────────────────────────────────────────────────
    "gpt-5",
    "gpt-5.6-terra-2026-07-09",
    # ── OpenAI GPT-4o family ────────────────────────────────────────────────
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4o-2024-11-20",
    # ── OpenAI GPT-4 Turbo ──────────────────────────────────────────────────
    "gpt-4-turbo",
    # ── OpenAI o-series (reasoning) ─────────────────────────────────────────
    "o3",
    "o3-mini",
    "o4-mini",
    # ── Anthropic Claude (via DIAL bridge) ──────────────────────────────────
    "anthropic.claude-sonnet-5",
    "anthropic.claude-opus-4",
    "anthropic.claude-sonnet-4",
    "anthropic.claude-haiku-4-5",
    "claude-3-5-sonnet",
    "claude-3-7-sonnet",
    # ── Google Gemini (via DIAL bridge) ─────────────────────────────────────
    "gemini-2.0-flash",
    "gemini-2.0-flash-thinking",
    "gemini-2.5-pro",
    "gemini-pro",
    # ── Meta Llama (via DIAL bridge) ────────────────────────────────────────
    "meta-llama-3-70b-instruct",
    "meta-llama-3-1-405b-instruct",
    # ── Mistral (via DIAL bridge) ────────────────────────────────────────────
    "mistral-large",
    "mistral-large-2",
]

# Human-readable descriptions and tier info for each model
MODEL_DESCRIPTIONS = {
    # GPT-5 tier
    "gpt-5":                        ("OpenAI",    "GPT-5",                     "Frontier reasoning — highest quality"),
    "gpt-5.6-terra-2026-07-09":     ("OpenAI",    "GPT-5 Terra",               "Latest GPT-5 snapshot (2026-07-09)"),
    # GPT-4o family
    "gpt-4o":                       ("OpenAI",    "GPT-4o",                    "Best balance accuracy/speed (default)"),
    "gpt-4o-mini":                  ("OpenAI",    "GPT-4o Mini",               "Fast, low-cost — good for simple tables"),
    "gpt-4o-2024-11-20":            ("OpenAI",    "GPT-4o Nov-20",             "Specific dated snapshot for reproducibility"),
    # GPT-4 Turbo
    "gpt-4-turbo":                  ("OpenAI",    "GPT-4 Turbo",               "128k context — large schema tables"),
    # O-series
    "o3":                           ("OpenAI",    "o3",                        "Advanced reasoning — complex type mappings"),
    "o3-mini":                      ("OpenAI",    "o3-mini",                   "Fast reasoning model"),
    "o4-mini":                      ("OpenAI",    "o4-mini",                   "Latest mini reasoning model"),
    # Anthropic Claude
    "anthropic.claude-sonnet-5":    ("Anthropic", "Claude Sonnet 5",           "Top Anthropic model — best quality"),
    "anthropic.claude-opus-4":      ("Anthropic", "Claude Opus 4",             "Most powerful Claude — complex reasoning"),
    "anthropic.claude-sonnet-4":    ("Anthropic", "Claude Sonnet 4",           "Balanced Claude 4 model"),
    "anthropic.claude-haiku-4-5":   ("Anthropic", "Claude Haiku 4.5",          "Fastest Claude — simple rule assignment"),
    "claude-3-5-sonnet":            ("Anthropic", "Claude 3.5 Sonnet",         "Claude 3.5 via DIAL bridge"),
    "claude-3-7-sonnet":            ("Anthropic", "Claude 3.7 Sonnet",         "Claude 3.7 extended thinking"),
    # Google Gemini
    "gemini-2.0-flash":             ("Google",    "Gemini 2.0 Flash",          "Fast multimodal model"),
    "gemini-2.0-flash-thinking":    ("Google",    "Gemini 2.0 Flash Thinking", "Flash with extended reasoning"),
    "gemini-2.5-pro":               ("Google",    "Gemini 2.5 Pro",            "Google flagship — very large context"),
    "gemini-pro":                   ("Google",    "Gemini Pro",                "Standard Gemini via DIAL bridge"),
    # Meta Llama
    "meta-llama-3-70b-instruct":    ("Meta",      "Llama 3 70B",               "Open-weight — good for offline/on-prem"),
    "meta-llama-3-1-405b-instruct": ("Meta",      "Llama 3.1 405B",            "Largest Llama — near-frontier quality"),
    # Mistral
    "mistral-large":                ("Mistral",   "Mistral Large",             "European flagship LLM"),
    "mistral-large-2":              ("Mistral",   "Mistral Large 2",           "Latest Mistral flagship"),
}


class AIRuleMapper:
    """
    Assigns validation rules to column pairs using DIAL / any OpenAI-compatible model.

    When AI is unavailable (no API key, network error, parse failure),
    automatically falls back to StaticRuleMapper with a clear log message.

    Model Selection Priority:
      1. model= constructor argument
      2. DIAL_MODEL environment variable
      3. Default: gpt-4o
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        api_version: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Args:
            api_key    : DIAL API key (default: DIAL_API_KEY env var)
            api_base   : DIAL endpoint base URL
            api_version: Azure OpenAI API version
            model      : Model deployment name (e.g. 'gpt-4o', 'gpt-4o-mini')
        """
        self.api_key     = api_key     or os.getenv("DIAL_API_KEY", "")
        self.api_base    = api_base    or os.getenv("DIAL_API_BASE", _DEFAULT_API_BASE)
        self.api_version = api_version or os.getenv("DIAL_API_VERSION", _DEFAULT_API_VERSION)
        self.model       = model       or os.getenv("DIAL_MODEL", _DEFAULT_MODEL)
        self._ai_active  = bool(self.api_key)
        self._fallback   = StaticRuleMapper()

    def map_columns(
        self,
        source_columns: List[ColumnMetadata],
        target_columns: List[ColumnMetadata],
        primary_key_hints: Optional[List[str]] = None,
        table_name: str = "unknown",
    ) -> Tuple[List[ColumnRuleMapping], str]:
        """
        Map source → target columns and assign validation rules using AI.

        Args:
            source_columns    : PostgreSQL column metadata list
            target_columns    : Snowflake column metadata list
            primary_key_hints : Optional PK column names (informational only — no PK queries)
            table_name        : Table name for AI context and logging

        Returns:
            Tuple of:
              - List[ColumnRuleMapping]  — one per matched column pair
              - str explanation          — AI reasoning (empty string if static fallback)
        """
        if not self._ai_active:
            print(
                f"  [AIRuleMapper] No DIAL_API_KEY — using StaticRuleMapper for '{table_name}'.",
                file=sys.stderr,
            )
            mappings = self._fallback.map_columns(
                source_columns, target_columns, primary_key_hints
            )
            return mappings, "Static rule matching (no DIAL_API_KEY set)."

        try:
            from openai import AzureOpenAI  # type: ignore
        except ImportError:
            print(
                "  [AIRuleMapper] 'openai' not installed. pip install openai>=1.0. "
                "Using StaticRuleMapper.",
                file=sys.stderr,
            )
            mappings = self._fallback.map_columns(
                source_columns, target_columns, primary_key_hints
            )
            return mappings, "Static rule matching (openai package not installed)."

        print(f"  [AIRuleMapper] Using model '{self.model}' via DIAL for '{table_name}'.")

        client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.api_base,
        )

        system_prompt = self._build_system_prompt()
        user_prompt   = self._build_user_prompt(
            source_columns, target_columns, primary_key_hints or [], table_name
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
                extra_headers={"Api-Key": self.api_key},
            )
            raw = response.choices[0].message.content
            return self._parse_response(raw, source_columns, target_columns, primary_key_hints)

        except Exception as exc:
            print(
                f"  [AIRuleMapper] DIAL API error: {exc} — falling back to StaticRuleMapper.",
                file=sys.stderr,
            )
            mappings = self._fallback.map_columns(
                source_columns, target_columns, primary_key_hints
            )
            return mappings, f"Static fallback used (AI error: {exc})."

    # Prompt builders

    def _build_system_prompt(self) -> str:
        """Load rules catalog and build the system prompt."""
        try:
            with open(_CATALOG_PATH, encoding="utf-8") as f:
                catalog = json.load(f)
            rules_summary = "\n".join(
                f"  - {r['id']}: {r['description']}"
                for r in catalog.get("rules", [])
            )
        except Exception:
            rules_summary = "  (catalog unavailable — use standard PG→Snowflake type mapping)"

        return f"""You are a Senior Data Migration QA Engineer specialising in PostgreSQL → Snowflake migration.

Your task: given source (PostgreSQL) and target (Snowflake) column metadata, produce a JSON
mapping that assigns the correct validation rule to each column pair.

## Validation Rules (PostgreSQL → Snowflake)
{rules_summary}

## Normalization Rules Per Type
  PostgreSQL BOOLEAN         → Snowflake BOOLEAN      : rule = "boolean"    (TRUE/FALSE → '1'/'0')
  PostgreSQL NUMERIC/DECIMAL → Snowflake NUMBER        : rule = "numeric"    (round to 2dp)
  PostgreSQL TIMESTAMP       → Snowflake TIMESTAMP_NTZ : rule = "timestamp_ntz" (YYYY-MM-DD HH24:MI:SS)
  PostgreSQL TIMESTAMPTZ     → Snowflake TIMESTAMP_TZ  : rule = "timestamp_tz"  (UTC normalized)
  PostgreSQL DATE            → Snowflake DATE          : rule = "date"       (YYYY-MM-DD)
  PostgreSQL VARCHAR/TEXT    → Snowflake VARCHAR/STRING: rule = "text"       (TRIM)
  PostgreSQL UUID            → Snowflake VARCHAR/TEXT  : rule = "uuid"       (UPPER + TRIM)
  PostgreSQL INTEGER/BIGINT  → Snowflake NUMBER        : rule = "integer"    (cast to text)
  PostgreSQL JSON/JSONB      → Snowflake VARIANT       : rule = "json"       (canonical JSON)
  PostgreSQL BYTEA           → Snowflake BINARY        : rule = "bytea"      (hex encoding)

## NULL Rule (applies to ALL columns)
  ALL columns: NULL → '<<NULL>>' sentinel via COALESCE wrapper (applied automatically).

## Fivetran Filter
  If the table has _FIVETRAN_ACTIVE column → set has_fivetran_active=true.
  The WHERE _FIVETRAN_ACTIVE = TRUE filter is applied at query level (not per-column).

## Output Contract (JSON only — no markdown):
{{
  "column_mappings": [
    {{
      "source_column": "string",
      "target_column": "string",
      "source_type": "string",
      "target_type": "string",
      "rule": "boolean|numeric|timestamp_ntz|timestamp_tz|date|text|uuid|integer|json|bytea",
      "is_primary_key": true|false,
      "skip_validation": false,
      "skip_reason": ""
    }}
  ],
  "has_fivetran_active": true|false,
  "explanation": "one paragraph of reasoning"
}}

Rules:
- One rule per column pair. Choose the MOST SPECIFIC applicable rule.
- For unrecognised / complex types → use rule = "text".
- Set skip_validation=true for columns with no target match.
- Do NOT skip columns just because they are complex — always attempt a rule.
"""

    def _build_user_prompt(
        self,
        source_cols: List[ColumnMetadata],
        target_cols: List[ColumnMetadata],
        pk_hints: List[str],
        table_name: str,
    ) -> str:
        """Build the user prompt with column metadata as JSON."""
        src_list = [
            {
                "column_name":    c.column_name,
                "data_type":      c.data_type,
                "is_nullable":    c.is_nullable,
                "ordinal_position": c.ordinal_position,
            }
            for c in source_cols
            if not c.column_name.upper().startswith(_FIVETRAN_PREFIX)
        ]
        tgt_list = [
            {
                "column_name":    c.column_name,
                "data_type":      c.data_type,
                "is_nullable":    c.is_nullable,
                "ordinal_position": c.ordinal_position,
            }
            for c in target_cols
        ]
        pk_line = f"Primary key hints: {pk_hints}" if pk_hints else "No PK hints provided — skip PK detection."
        return (
            f"Map PostgreSQL → Snowflake columns for table: {table_name}\n"
            f"{pk_line}\n\n"
            f"Source (PostgreSQL) columns ({len(src_list)} total):\n"
            f"{json.dumps(src_list, indent=2)}\n\n"
            f"Target (Snowflake) columns ({len(tgt_list)} total):\n"
            f"{json.dumps(tgt_list, indent=2)}\n\n"
            f"Return the complete JSON mapping with rule assignments for every matchable column pair."
        )

    # -----------------------------------------------------------------------
    # Response parser
    # -----------------------------------------------------------------------

    def _parse_response(
        self,
        raw_json: str,
        source_cols: List[ColumnMetadata],
        target_cols: List[ColumnMetadata],
        pk_hints: Optional[List[str]],
    ) -> Tuple[List[ColumnRuleMapping], str]:
        """Parse the AI JSON response into ColumnRuleMapping list."""
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            print(
                f"  [AIRuleMapper] Cannot parse AI response: {exc} — using static.",
                file=sys.stderr,
            )
            mappings = self._fallback.map_columns(source_cols, target_cols, pk_hints)
            return mappings, "Static fallback (JSON parse error)."

        mappings: List[ColumnRuleMapping] = []
        explanation = data.get("explanation", "")

        for item in data.get("column_mappings", []):
            src_type = item.get("source_type", "text")
            tgt_type = item.get("target_type", "text")
            rule     = get_rule_for_type(src_type, tgt_type)

            mappings.append(ColumnRuleMapping(
                source_column   = item["source_column"],
                target_column   = item["target_column"],
                source_type     = src_type,
                target_type     = tgt_type,
                rule            = rule,
                is_primary_key  = item.get("is_primary_key", False),
                skip_validation = item.get("skip_validation", False),
                skip_reason     = item.get("skip_reason", ""),
                matched_by      = "ai",
            ))

        active  = sum(1 for m in mappings if not m.skip_validation)
        skipped = sum(1 for m in mappings if m.skip_validation)
        print(
            f"  [AIRuleMapper] ✓ {len(mappings)} columns mapped: "
            f"{active} active, {skipped} skipped  (model: {self.model})"
        )
        return mappings, explanation
