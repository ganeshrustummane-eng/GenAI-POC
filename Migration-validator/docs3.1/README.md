# Migration Validator 3.1 Documentation

This folder contains the complete version 3.1 handover and operating documentation.

## Start Here

1. [Handover Guide](HANDOVER_GUIDE.md) — complete technical and operational reference.
2. [Environment Setup](ENVIRONMENT_SETUP.md) — install dependencies and configure `.env`.
3. [Operations Guide](OPERATIONS_GUIDE.md) — run generation, YAML validation, reports, and tests.
4. [Architecture](ARCHITECTURE.md) — component responsibilities and data flow.
5. [Validation Methodology](VALIDATION_METHODOLOGY.md) — what each validation means and how results are interpreted.
6. [Future Roadmap](FUTURE_ROADMAP.md) — planned improvements and extension points.

## Quick Commands

From the repository root:

```powershell
python tests\\e2e\\run_all_tests.py --skip-live
python tests\\e2e\\run_all_tests.py
python test_env_connections.py
python -m pytest -q
```

Runtime output is written to `output/`. Generated YAML configuration is written to `config/bronze/`.
