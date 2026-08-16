# Version 3.1 Change Record

## Framework and Execution

- Integrated PostgreSQL, MSSQL, Snowflake, and Athena adapters.
- Added `.env`-based credential loading.
- Added database-type profile inference when YAML omits `source_name`.
- Standardized runtime reports under repository `output/`.
- Added non-secret database/schema fallback metadata.

## Validation

- Added count validation.
- Added row-level data validation.
- Added case-insensitive and normalized primary-key resolution.
- Added mismatch CSV output.
- Added summary CSV output and execution logs.
- Added JSON/HStore canonical comparison.
- Added order-independent row comparison.

## SQL and AI

- Added source-dialect-aware SQL generation.
- Added MSSQL SQL safety checks.
- Added source-to-target type/castability context to AI prompts.
- Added AI response validation and deterministic fallback.
- Fixed aggregate SELECT comma generation.
- Implemented real grouped VALUE_DIST queries.
- Preserved Snowflake Fivetran active-row filtering.

## Exclusions

- Added automatic ETL/Fivetran exclusions.
- Added YAML-based exclusion rules.
- Added interactive single-table exclusions.
- Added per-table exclusions for multi-table workflows.
- Excluded columns are removed before mapping and SQL generation.

## Testing

- Added `tests/e2e/run_all_tests.py`.
- Added non-live and live test modes.
- Added dependency, import, YAML, dialect, regression, connection, validation, and output stages.
- Added JSON test reports under `output/test_runs/`.
