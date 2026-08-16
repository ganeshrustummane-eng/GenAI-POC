"""
AI-Powered SQL Query Generator
================================
Uses AI to dynamically generate database-specific SQL queries for validation.

This module leverages the AI model to write optimized, database-specific SQL
queries based on the source and target database types, ensuring proper syntax
and data type conversions for:
  - MS SQL Server → Snowflake
  - PostgreSQL → Snowflake
  - Athena → Snowflake
  - Any database → Any database

Key Features:
  - Database-specific syntax (CAST, CONVERT, FORMAT functions)
  - Proper data type conversions (INT → VARCHAR(MAX) for MSSQL, TEXT for PG)
  - Timezone handling per database
  - NULL placeholder insertion
  - Fivetran active record filtering

Environment Variables Required:
  DIAL_API_KEY      — EPAM DIAL API key
  DIAL_API_BASE     — defaults to https://ai-proxy.lab.epam.com
  DIAL_API_VERSION  — defaults to 2025-04-01-preview
  DIAL_MODEL        — defaults to gpt-4o
"""

import json
import os
import re
from typing import List, Optional, Tuple
from dataclasses import dataclass

from ai_transformation.static_rule_mapper import ColumnRuleMapping


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_API_BASE = "https://ai-proxy.lab.epam.com"
_DEFAULT_API_VERSION = "2025-04-01-preview"
_DEFAULT_MODEL = "gpt-4o"
NULL_PLACEHOLDER = "<<NULL>>"


# ---------------------------------------------------------------------------
# AI SQL Generator
# ---------------------------------------------------------------------------

@dataclass
class AIGeneratedQuery:
    """Container for AI-generated SQL query with metadata."""
    query: str
    database_type: str
    explanation: str
    confidence: float
    warnings: List[str]


class AISQLQueryGenerator:
    """
    Generates database-specific SQL queries using AI.
    
    This generator understands the nuances of different SQL dialects and
    produces optimized, correct queries for each source/target combination.
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
        self.api_key = api_key or os.getenv("DIAL_API_KEY", "")
        self.api_base = api_base or os.getenv("DIAL_API_BASE", _DEFAULT_API_BASE)
        self.api_version = api_version or os.getenv("DIAL_API_VERSION", _DEFAULT_API_VERSION)
        self.model = model or os.getenv("DIAL_MODEL", _DEFAULT_MODEL)
        self._ai_active = bool(self.api_key)

    def generate_validation_query(
        self,
        schema: str,
        table: str,
        mappings: List[ColumnRuleMapping],
        source_db_type: str,
        target_db_type: str = "snowflake",
        query_type: str = "data_validation",
        has_fivetran_active: bool = False,
    ) -> AIGeneratedQuery:
        """
        Generate a database-specific validation query using AI.

        Args:
            schema              : Source schema name
            table               : Source table name
            mappings            : Column rule mappings
            source_db_type      : Source database type (mssql, postgresql, athena)
            target_db_type      : Target database type (default: snowflake)
            query_type          : Type of query (data_validation, null_pct, distinct_count)
            has_fivetran_active : Whether to include Fivetran filter

        Returns:
            AIGeneratedQuery with the generated SQL and metadata
        """
        if not self._ai_active:
            return self._fallback_query(
                schema, table, mappings, source_db_type, query_type, has_fivetran_active
            )

        try:
            from openai import AzureOpenAI
        except ImportError:
            return self._fallback_query(
                schema, table, mappings, source_db_type, query_type, has_fivetran_active
            )

        client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.api_base,
        )

        system_prompt = self._build_system_prompt(source_db_type, target_db_type)
        user_prompt = self._build_user_prompt(
            schema, table, mappings, source_db_type, query_type, has_fivetran_active
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                extra_headers={"Api-Key": self.api_key},
            )
            raw = response.choices[0].message.content
            result = self._parse_response(raw, source_db_type, mappings, query_type)
            if result.warnings:
                print("  [AISQLGenerator] AI response failed SQL checks — using fallback")
                return self._fallback_query(
                    schema, table, mappings, source_db_type, query_type, has_fivetran_active
                )
            return result

        except Exception as exc:
            print(f"  [AISQLGenerator] AI error: {exc} — using fallback query")
            return self._fallback_query(
                schema, table, mappings, source_db_type, query_type, has_fivetran_active
            )

    def _build_system_prompt(self, source_db: str, target_db: str) -> str:
        """Build the system prompt with database-specific instructions."""
        return f"""You are an expert SQL Query Generator specializing in data migration validation.

Your task: Generate database-specific SQL queries for validation between {source_db.upper()} (source) and {target_db.upper()} (target).

## Database-Specific Syntax Rules:

### MS SQL Server (MSSQL)
- NO TEXT data type — use VARCHAR(MAX) for text casting
- NO TO_CHAR function — use FORMAT() or CONVERT()
- Integers: CAST(column AS VARCHAR(MAX)) NOT CAST(column AS TEXT)
- Timestamps: FORMAT(column, 'yyyy-MM-dd HH:mm:ss')
- Booleans: Use BIT type (0/1), no true/false keywords
- String trimming: LTRIM(RTRIM(column))
- NULL coalesce: COALESCE(CAST(column AS VARCHAR(MAX)), '<<NULL>>')

### PostgreSQL
- Use TEXT for text casting: CAST(column AS TEXT)
- Use TO_CHAR for formatting: TO_CHAR(column, 'YYYY-MM-DD HH24:MI:SS')
- Booleans: true/false keywords supported
- String trimming: TRIM(column)
- NULL coalesce: COALESCE(CAST(column AS TEXT), '<<NULL>>')

### Snowflake
- Use STRING for text casting: CAST(column AS STRING)
- Use TO_VARCHAR for formatting: TO_VARCHAR(column, 'YYYY-MM-DD HH24:MI:SS')
- Booleans: TRUE/FALSE keywords
- String trimming: TRIM(column)
- NULL coalesce: COALESCE(CAST(column AS STRING), '<<NULL>>')

### Athena/Trino/Presto
- Use VARCHAR for text casting: CAST(column AS VARCHAR)
- Use date_format for formatting: date_format(column, '%Y-%m-%d %H:%i:%s')
- String trimming: TRIM(column)
- NULL coalesce: COALESCE(CAST(column AS VARCHAR), '<<NULL>>')

## Critical Requirements:
1. ALWAYS use database-specific syntax — never mix dialects.
2. Treat every source→target type pair as a compatibility decision; choose a cast
    legal in the source dialect that produces a comparable value.
3. Preserve numeric precision and scale before text conversion; use intermediate
    conversions for types that cannot be cast directly.
4. Normalize timezone semantics before formatting timestamps; do not silently drop offsets.
5. Handle NULL, empty strings, booleans, JSON/JSONB, binary, UUID, date, numeric,
    and character padding explicitly according to the source dialect.
6. ALL normalized data-validation columns MUST have COALESCE(..., '<<NULL>>').
7. Text casts MUST match the database type (VARCHAR(MAX) for MSSQL, TEXT for PG, STRING for SF).
8. Format functions MUST match the database (FORMAT for MSSQL, TO_CHAR for PG, TO_VARCHAR for SF).
9. Use commas between every SELECT expression and preserve requested aliases exactly.
10. Include the target active-record filter when requested; never mix source and target syntax.
11. Return ONLY the SQL query — no markdown, no explanation.
12. Mentally validate the complete query as executable SQL before returning it.

## NULL Handling (CRITICAL):
- Source query: COALESCE(CAST(expression AS <database_text_type>), '<<NULL>>')
- Target query: COALESCE(CAST(expression AS STRING), '<<NULL>>')

## Output Format:
Return plain SQL query only. No markdown, no comments, no explanations outside the SQL.
"""

    def _build_user_prompt(
        self,
        schema: str,
        table: str,
        mappings: List[ColumnRuleMapping],
        source_db_type: str,
        query_type: str,
        has_fivetran_active: bool,
    ) -> str:
        """Build the user prompt with column details."""
        columns_json = [
            {
                "source_column": m.source_column,
                "target_column": m.target_column,
                "source_type": m.source_type,
                "target_type": m.target_type,
                "rule": m.rule.rule_name,
            }
            for m in mappings if not m.skip_validation
        ]

        fivetran_note = ""
        if has_fivetran_active and query_type == "data_validation":
            fivetran_note = "\nTarget query MUST include: WHERE _FIVETRAN_ACTIVE = TRUE"

        query_descriptions = {
            "data_validation": "SELECT normalized columns for row-by-row comparison",
            "null_pct": "SELECT NULL percentage per column: ROUND(100.0 * SUM(CASE WHEN col IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2)",
            "distinct_count": "SELECT distinct value count per column: COUNT(DISTINCT col)",
        }

        compatibility = self._build_compatibility_matrix(mappings, source_db_type, "snowflake")
        return f"""Generate {source_db_type.upper()} SQL query for: {schema}.{table}

Query Type: {query_descriptions.get(query_type, query_type)}

Columns to process ({len(columns_json)} total):
{json.dumps(columns_json, indent=2)}

Source → target compatibility decisions:
{compatibility}

Requirements:
1. Use {source_db_type.upper()}-specific syntax
2. Apply proper data type conversions per column rule
3. ALL columns MUST be wrapped: COALESCE(CAST(expression AS {self._get_text_type(source_db_type)}), '<<NULL>>')
4. Integers: CAST(col AS {self._get_text_type(source_db_type)})
5. Timestamps: {self._get_format_function(source_db_type)}
6. Booleans: CASE WHEN col = {self._get_bool_true(source_db_type)} THEN '1' WHEN col = {self._get_bool_false(source_db_type)} THEN '0' ELSE NULL END
7. Each normalized column should have alias: column_name_normalized{fivetran_note}

Generate the complete SELECT query now:
"""

    def _build_compatibility_matrix(
        self,
        mappings: List[ColumnRuleMapping],
        source_db_type: str,
        target_db_type: str,
    ) -> str:
        """Give the model explicit per-column castability context."""
        lines = []
        for mapping in mappings:
            if mapping.skip_validation:
                continue
            lines.append(
                f"- {mapping.source_column} -> {mapping.target_column}: "
                f"{mapping.source_type.upper()} -> {mapping.target_type.upper()}; "
                f"rule={mapping.rule.rule_name}; "
                f"source_text_cast={self._get_text_type(source_db_type)}; "
                f"target_text_cast={self._get_text_type(target_db_type)}"
            )
        return "\n".join(lines) or "- No comparable columns"

    def _get_text_type(self, db_type: str) -> str:
        """Get the text data type for the database."""
        db = db_type.lower()
        if db in ("mssql", "sqlserver", "sql_server"):
            return "VARCHAR(MAX)"
        elif db in ("postgres", "postgresql"):
            return "TEXT"
        elif db in ("snowflake",):
            return "STRING"
        elif db in ("athena", "trino", "presto"):
            return "VARCHAR"
        return "TEXT"

    def _get_format_function(self, db_type: str) -> str:
        """Get the timestamp format function for the database."""
        db = db_type.lower()
        if db in ("mssql", "sqlserver", "sql_server"):
            return "FORMAT(col, 'yyyy-MM-dd HH:mm:ss')"
        elif db in ("postgres", "postgresql"):
            return "TO_CHAR(col, 'YYYY-MM-DD HH24:MI:SS')"
        elif db in ("snowflake",):
            return "TO_VARCHAR(col, 'YYYY-MM-DD HH24:MI:SS')"
        elif db in ("athena", "trino", "presto"):
            return "date_format(col, '%Y-%m-%d %H:%i:%s')"
        return "TO_CHAR(col, 'YYYY-MM-DD HH24:MI:SS')"

    def _get_bool_true(self, db_type: str) -> str:
        """Get the boolean TRUE value for the database."""
        db = db_type.lower()
        if db in ("mssql", "sqlserver", "sql_server"):
            return "1"
        return "true"

    def _get_bool_false(self, db_type: str) -> str:
        """Get the boolean FALSE value for the database."""
        db = db_type.lower()
        if db in ("mssql", "sqlserver", "sql_server"):
            return "0"
        return "false"

    def _parse_response(
        self,
        raw: str,
        db_type: str,
        mappings: Optional[List[ColumnRuleMapping]] = None,
        query_type: str = "data_validation",
    ) -> AIGeneratedQuery:
        """Parse AI response and extract the query."""
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            # Remove first line (```sql or ```) and last line (```)
            if lines[-1].strip() == "```":
                cleaned = "\n".join(lines[1:-1])
            else:
                cleaned = "\n".join(lines[1:])
            cleaned = cleaned.strip()

        warnings = self._validate_generated_query(cleaned, db_type, mappings or [], query_type)

        return AIGeneratedQuery(
            query=cleaned,
            database_type=db_type,
            explanation=f"AI-generated query for {db_type}",
            confidence=0.95 if not warnings else 0.7,
            warnings=warnings,
        )

    def _validate_generated_query(
        self,
        query: str,
        db_type: str,
        mappings: List[ColumnRuleMapping],
        query_type: str,
    ) -> List[str]:
        """Reject unsafe or incomplete AI output before it reaches SQL files."""
        warnings = []
        upper = query.upper()
        dialect = db_type.lower().replace("server", "")
        if not re.search(r"\bSELECT\b", upper) or not re.search(r"\bFROM\b", upper):
            warnings.append("AI response is not a complete SELECT query")
        if dialect in {"mssql", "sqlserver"}:
            forbidden = {
                r"::\s*[A-Z_]": "PostgreSQL cast operator (::)",
                r"\bTO_CHAR\s*\(": "PostgreSQL TO_CHAR",
                r"\bAS\s+TEXT\b": "PostgreSQL TEXT cast",
                r"\bJSONB\b": "PostgreSQL JSONB",
                r"\bENCODE\s*\(": "PostgreSQL encode()",
            }
            for pattern, label in forbidden.items():
                if re.search(pattern, upper):
                    warnings.append(f"MSSQL query contains {label}")
        if query_type == "data_validation":
            if "<<NULL>>" not in query:
                warnings.append("Data-validation query is missing the NULL placeholder")
            for mapping in mappings:
                if mapping.skip_validation:
                    continue
                alias = f"{mapping.source_column}_normalized".upper()
                if alias not in upper:
                    warnings.append(f"Missing required alias {mapping.source_column}_normalized")
            # Detect adjacent SELECT function expressions without a comma.
            if re.search(r"\)\s+\w+\s*\(", query, re.I):
                warnings.append("SELECT expressions may be missing commas")
        return warnings

    def _fallback_query(
        self,
        schema: str,
        table: str,
        mappings: List[ColumnRuleMapping],
        source_db_type: str,
        query_type: str,
        has_fivetran_active: bool,
    ) -> AIGeneratedQuery:
        """Generate a basic fallback query when AI is unavailable."""
        # Use the existing rule-based approach
        select_lines = []
        for m in mappings:
            if not m.skip_validation:
                expr = m.rule.apply_source(
                    source_db_type,
                    m.source_column,
                    alias=f"{m.source_column}_normalized",
                )
                select_lines.append(f"    {expr}")

        cols = ",\n".join(select_lines)
        query = f"SELECT\n{cols}\nFROM {schema}.{table};"

        return AIGeneratedQuery(
            query=query,
            database_type=source_db_type,
            explanation="Rule-based fallback query (AI unavailable)",
            confidence=0.8,
            warnings=["Using rule-based fallback - AI was not available"],
        )
