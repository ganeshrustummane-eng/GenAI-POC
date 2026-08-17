"""Static safety checks for generated source/target SQL pairs."""

import re


class GeneratedSQLValidationError(ValueError):
    """Raised when generated SQL violates the selected dialect contract."""


def validate_sql_pair(source_sql: str, target_sql: str, source_db_type: str) -> None:
    """Reject known cross-dialect constructs before SQL is serialized."""
    dialect = source_db_type.lower().replace("server", "")
    if dialect in {"mssql", "sql"}:
        forbidden = {
            r"::\s*[a-z_]+": "PostgreSQL cast operator",
            r"\bTO_CHAR\s*\(": "PostgreSQL TO_CHAR",
            r"\bAS\s+TEXT\b": "PostgreSQL TEXT cast",
            r"\bAT\s+TIME\s+ZONE\b": "PostgreSQL timezone syntax",
            r"\bJSONB\b": "PostgreSQL JSONB type",
            r"\bencode\s*\(": "PostgreSQL encode()",
        }
        problems = [label for pattern, label in forbidden.items() if re.search(pattern, source_sql, re.I)]
        if problems:
            raise GeneratedSQLValidationError(
                f"{source_db_type} source SQL contains unsupported constructs: {', '.join(problems)}"
            )
    if re.search(r"SELECT\s+[^;]*\bCOUNT\(\*\)\s+AS\s+\w+\s+\w+\(", source_sql, re.I | re.S):
        raise GeneratedSQLValidationError("Source aggregate SELECT appears to be missing a comma")
    if re.search(r"SELECT\s+[^;]*\bCOUNT\(\*\)\s+AS\s+\w+\s+\w+\(", target_sql, re.I | re.S):
        raise GeneratedSQLValidationError("Target aggregate SELECT appears to be missing a comma")