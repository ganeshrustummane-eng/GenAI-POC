"""
Manifest Writer
================
Writes _manifest.json and _execution_log.txt after a batch run.

_manifest.json schema:
    {
        "execution_id": "batch_run_20260811_143022",
        "started_at": "2026-08-11T14:30:22",
        "completed_at": "2026-08-11T14:35:10",
        "duration_seconds": 288,
        "config_path": "tables.yaml",
        "total_tables": 10,
        "successful": 9,
        "failed": 1,
        "skipped": 0,
        "tables": [
            {
                "source_table": "events",
                "target_table": "EVENTS",
                "status": "success",
                "sql_path": "...",
                "yaml_path": "...",
                "plan_path": "...",
                "columns_matched": 12,
                "primary_keys": ["event_id"],
                "duration_seconds": 8.3,
                "ai_calls_made": 2,
                "error": null
            },
            ...
        ]
    }
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TableResult:
    """Result entry for one table in the manifest."""
    source_table:     str
    target_table:     str
    status:           str       # "success" | "failed" | "skipped"
    sql_path:         str = ""
    yaml_path:        str = ""
    plan_path:        str = ""
    dynamic_sql_path: str = ""
    columns_matched:  int = 0
    primary_keys:     List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    ai_calls_made:    int = 0
    error:            Optional[str] = None


class ManifestWriter:
    """Writes _manifest.json and _execution_log.txt to the batch output directory."""

    def write(
        self,
        run_dir: Path,
        execution_id: str,
        started_at: datetime,
        completed_at: datetime,
        config_path: str,
        table_results: List[TableResult],
    ) -> Path:
        """
        Write _manifest.json and return its path.

        Args:
            run_dir       : Batch run output directory (e.g. validation_sql/batch_run_...)
            execution_id  : Unique run identifier (e.g. 'batch_run_20260811_143022')
            started_at    : Batch start time
            completed_at  : Batch end time
            config_path   : Path to the original tables.yaml
            table_results : Per-table result objects

        Returns:
            Path to the written _manifest.json file.
        """
        run_dir.mkdir(parents=True, exist_ok=True)

        duration = (completed_at - started_at).total_seconds()
        successful = sum(1 for t in table_results if t.status == "success")
        failed     = sum(1 for t in table_results if t.status == "failed")
        skipped    = sum(1 for t in table_results if t.status == "skipped")

        manifest: Dict[str, Any] = {
            "execution_id":     execution_id,
            "started_at":       started_at.isoformat(),
            "completed_at":     completed_at.isoformat(),
            "duration_seconds": round(duration, 2),
            "config_path":      config_path,
            "total_tables":     len(table_results),
            "successful":       successful,
            "failed":           failed,
            "skipped":          skipped,
            "tables":           [_table_result_to_dict(t) for t in table_results],
        }

        manifest_path = run_dir / "_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # Also write a plain-text execution log
        log_path = run_dir / "_execution_log.txt"
        self._write_log(log_path, manifest, table_results)

        return manifest_path

    @staticmethod
    def _write_log(path: Path, manifest: dict, results: List[TableResult]) -> None:
        lines = [
            f"MIGRATION VALIDATOR — Batch Execution Log",
            f"=" * 60,
            f"Execution ID : {manifest['execution_id']}",
            f"Started      : {manifest['started_at']}",
            f"Completed    : {manifest['completed_at']}",
            f"Duration     : {manifest['duration_seconds']}s",
            f"Config       : {manifest['config_path']}",
            f"",
            f"SUMMARY",
            f"-" * 40,
            f"Total tables : {manifest['total_tables']}",
            f"Successful   : {manifest['successful']}",
            f"Failed       : {manifest['failed']}",
            f"Skipped      : {manifest['skipped']}",
            f"",
            f"TABLE DETAILS",
            f"-" * 40,
        ]
        for t in results:
            status_icon = "✓" if t.status == "success" else ("✗" if t.status == "failed" else "–")
            lines.append(
                f"  {status_icon} {t.source_table} → {t.target_table}"
                f"  [{t.status}]  {t.duration_seconds:.1f}s"
                + (f"  ERROR: {t.error}" if t.error else "")
            )
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def _table_result_to_dict(t: TableResult) -> Dict[str, Any]:
    return {
        "source_table":     t.source_table,
        "target_table":     t.target_table,
        "status":           t.status,
        "sql_path":         t.sql_path,
        "yaml_path":        t.yaml_path,
        "plan_path":        t.plan_path,
        "dynamic_sql_path": t.dynamic_sql_path,
        "columns_matched":  t.columns_matched,
        "primary_keys":     t.primary_keys,
        "duration_seconds": round(t.duration_seconds, 2),
        "ai_calls_made":    t.ai_calls_made,
        "error":            t.error,
    }
