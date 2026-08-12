"""
Batch Processing Package
=========================
Multi-table, multi-source validation batch runner.

Modules:
    config_parser  — YAML batch config parser
    batch_runner   — Orchestrates parallel table processing
    manifest_writer — Writes _manifest.json summary
"""

from batch.config_parser import BatchConfig, TablePairConfig, load_batch_config
from batch.batch_runner import BatchRunner
from batch.manifest_writer import ManifestWriter

__all__ = [
    "BatchConfig",
    "TablePairConfig",
    "load_batch_config",
    "BatchRunner",
    "ManifestWriter",
]
