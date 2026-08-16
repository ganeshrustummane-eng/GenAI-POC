# Operations Guide

## Run the Interactive CLI

From the repository root:

```powershell
python src\\validate_cli.py
```

The CLI provides:

- Connections: test configured databases.
- Single Table: generate SQL and YAML for one table.
- Run Tables: generate SQL and YAML for multiple tables.
- List Tables: discover source and target tables.
- Select AI Model: choose the active model for the session.
- View Rule Book: inspect transformation rules.
- Add Custom Rule: add a learned rule.
- Execute YAML: execute saved source and target queries.

Connection profiles are not part of the normal workflow. Credentials come from `.env`.

## Generate One Table

```powershell
python src\\validate_cli.py generate `
  --source 2 `
  --pg-table Addresses `
  --sf-table ADDRESSES `
  --pg-schema dbo `
  --sf-schema AWSDEV_DEVT5000_DBO `
  --sf-database DEV_SITELINK_BRONZE
```

The source profile number maps to `SRC_2_*` in `.env`.

## Exclude Columns

```powershell
python src\\validate_cli.py generate `
  --source 2 `
  --pg-table Addresses `
  --sf-table ADDRESSES `
  --exclude uTS,GeographyData
```

Interactive workflows display source columns and accept column numbers or names. Excluded columns are removed before mapping and are not written into generated SQL.

## Run YAML Validation

Use menu option `[9]`, or execute the Python API:

```python
from src.validation.validation_executor import ValidationExecutor

executor = ValidationExecutor(base_dir=".")
results = executor.execute_batch(
    layer="bronze",
    tables=["all"],
    validation_types=["count_validation", "data_validation"],
    config_dir="config",
)
```

## Test the Whole Framework

Non-live checks:

```powershell
python tests\\e2e\\run_all_tests.py --skip-live
```

Full live checks:

```powershell
python tests\\e2e\\run_all_tests.py
```

Selected tables:

```powershell
python tests\\e2e\\run_all_tests.py --layer bronze --tables Addresses AcctSoftware
```

Selected validation type:

```powershell
python tests\\e2e\\run_all_tests.py --validation-types count_validation
```

## Output Locations

Generated configuration:

```text
config/bronze/count_validation/
config/bronze/data_validation/
```

Runtime reports:

```text
output/bronze/validation_<run_id>/
```

Inside each run:

- `validation_<run_id>.log`
- `count_validation_<run_id>/count_validation_summary.csv`
- `data_validation_<run_id>/data_validation_summary.csv`
- table-specific mismatch CSV files

E2E reports:

```text
output/test_runs/<run_id>/test_report.json
```
