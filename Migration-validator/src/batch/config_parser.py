"""
Batch Config Parser
====================
Parses the tables.yaml batch configuration file into strongly-typed
dataclasses used by BatchRunner.

Supported YAML format
---------------------
source:
  type: postgresql          # postgresql | mssql | athena | etc.
  host: localhost           # optional — falls back to SOURCE_HOST env
  port: 5432
  database: mydb
  schema: public
  username: user            # optional — falls back to SOURCE_USERNAME env
  password: secret

target:
  type: snowflake           # always snowflake (target is fixed)
  account: org.account
  database: DEV_BRONZE
  schema: MY_SCHEMA
  username: sf_user
  password: sf_secret

tables:
  - source_table: events
    target_table: EVENTS
    primary_keys: [event_id]

  - source_table: customers
    target_table: CUSTOMERS
    primary_keys: [customer_id]
    explicit_mappings:          # optional per-table overrides
      customer_id: CUST_ID

  - source_table: order_lines
    target_table: ORDER_LINES
    primary_keys: [order_id, line_number]   # composite PK

execution:
  parallel: true
  max_workers: 4
  fail_fast: false
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SourceConfig:
    """Source database connection parameters."""
    db_type:  str
    host:     str = ""
    port:     int = 0
    database: str = ""
    schema:   str = ""
    username: str = ""
    password: str = ""

    def effective(self) -> "SourceConfig":
        """Fill blanks from env vars so explicit YAML overrides env."""
        return SourceConfig(
            db_type=self.db_type,
            host=self.host     or os.getenv("SOURCE_HOST",     "localhost"),
            port=self.port     or int(os.getenv("SOURCE_PORT", "5432")),
            database=self.database or os.getenv("SOURCE_DATABASE", ""),
            schema=self.schema   or os.getenv("SOURCE_SCHEMA",   "public"),
            username=self.username or os.getenv("SOURCE_USERNAME", ""),
            password=self.password or os.getenv("SOURCE_PASSWORD", ""),
        )


@dataclass
class TargetConfig:
    """Snowflake target connection parameters."""
    account:  str = ""
    database: str = ""
    schema:   str = ""
    username: str = ""
    password: str = ""

    def effective(self) -> "TargetConfig":
        """Fill blanks from env vars."""
        return TargetConfig(
            account=self.account   or os.getenv("SNOWFLAKE_ACCOUNT",  ""),
            database=self.database or os.getenv("SNOWFLAKE_DATABASE", ""),
            schema=self.schema     or os.getenv("SNOWFLAKE_SCHEMA",   ""),
            username=self.username or os.getenv("SNOWFLAKE_USERNAME", ""),
            password=self.password or os.getenv("SNOWFLAKE_PASSWORD", ""),
        )


@dataclass
class TablePairConfig:
    """One source→target table pair with optional overrides."""
    source_table:      str
    target_table:      str
    primary_keys:      List[str] = field(default_factory=list)
    explicit_mappings: Dict[str, str] = field(default_factory=dict)
    # Optional per-table schema overrides (rare — usually inherited from SourceConfig)
    source_schema_override: Optional[str] = None
    target_schema_override: Optional[str] = None


@dataclass
class ExecutionConfig:
    """Batch execution settings."""
    parallel:    bool = True
    max_workers: int  = 4
    fail_fast:   bool = False


@dataclass
class BatchConfig:
    """Full parsed batch configuration."""
    source:    SourceConfig
    target:    TargetConfig
    tables:    List[TablePairConfig]
    execution: ExecutionConfig
    config_path: Path = field(default_factory=Path)


def load_batch_config(path: str | Path) -> BatchConfig:
    """
    Parse a batch YAML config file into a BatchConfig.

    Args:
        path: Path to the tables.yaml file.

    Returns:
        BatchConfig with all fields populated.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        ValueError: If required fields are missing.
    """
    try:
        import yaml
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required for batch mode. Install with: pip install pyyaml"
        ) from exc

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Batch config not found: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"Invalid batch config: {path} must be a YAML mapping.")

    source_raw = raw.get("source", {})
    target_raw = raw.get("target", {})
    tables_raw = raw.get("tables", [])
    exec_raw   = raw.get("execution", {})

    source = SourceConfig(
        db_type=source_raw.get("type", os.getenv("SOURCE_TYPE", "postgresql")),
        host=str(source_raw.get("host", "")),
        port=int(source_raw.get("port", 0)),
        database=str(source_raw.get("database", "")),
        schema=str(source_raw.get("schema", "")),
        username=str(source_raw.get("username", "")),
        password=str(source_raw.get("password", "")),
    )

    target = TargetConfig(
        account=str(target_raw.get("account", "")),
        database=str(target_raw.get("database", "")),
        schema=str(target_raw.get("schema", "")),
        username=str(target_raw.get("username", "")),
        password=str(target_raw.get("password", "")),
    )

    tables: List[TablePairConfig] = []
    for entry in tables_raw:
        if not isinstance(entry, dict):
            continue
        src_table = entry.get("source_table", "")
        tgt_table = entry.get("target_table", src_table.upper())
        if not src_table:
            raise ValueError("Each table entry must have a 'source_table' key.")
        tables.append(TablePairConfig(
            source_table=src_table,
            target_table=tgt_table,
            primary_keys=list(entry.get("primary_keys", [])),
            explicit_mappings=dict(entry.get("explicit_mappings", {})),
            source_schema_override=entry.get("source_schema"),
            target_schema_override=entry.get("target_schema"),
        ))

    execution = ExecutionConfig(
        parallel=bool(exec_raw.get("parallel", True)),
        max_workers=int(exec_raw.get("max_workers", 4)),
        fail_fast=bool(exec_raw.get("fail_fast", False)),
    )

    return BatchConfig(
        source=source.effective(),
        target=target.effective(),
        tables=tables,
        execution=execution,
        config_path=path,
    )
