# Troubleshooting

## Dependencies Missing

Run:

```powershell
python -m pip install -r requirements.txt
```

Then run:

```powershell
python tests\\e2e\\run_all_tests.py --skip-live
```

## Wrong Python Interpreter

The project may have multiple Python installations. Use the same interpreter for dependencies and tests. The E2E runner searches available interpreters for pytest.

Check the interpreter:

```powershell
python -c "import sys; print(sys.executable)"
```

## Connection Failure

Run:

```powershell
python test_env_connections.py
```

Check the relevant `.env` values and verify the database server, port, driver, schema, and network/VPN access.

## MSSQL Pre-Login Failure

Confirm:

- Microsoft ODBC Driver 18 is installed.
- Host and port are reachable.
- Authentication type is correct.
- `SRC_2_AUTH` is correct.
- The server supports the configured encryption mode.

The adapter uses `Encrypt=optional` and `TrustServerCertificate=yes` for the current environment.

## YAML Not Listed

Place YAML under:

```text
config/bronze/count_validation/
config/bronze/data_validation/
```

Confirm the extension is `.yaml` and the file contains a `tables:` block.

## YAML Source Uses Wrong Database

Ensure the validation block contains:

```yaml
source: mssql
```

When `source_name` is absent, the factory maps the source type to its default `SRC_N` profile.

## Data Validation Key Error

Confirm `pksourcecolumn` and `pktargetcolumn` exist in the query output. Normalized aliases such as `id_normalized` are supported.

## Generated SQL Fails

Check the source dialect. MSSQL queries must not contain PostgreSQL syntax. Run the E2E SQL checks:

```powershell
python tests\\e2e\\run_all_tests.py --skip-live
```

## No CSV Output

Find the run ID in the console or log and inspect:

```text
output/<layer>/validation_<run_id>/
```

## FAIL Versus ERROR

- `FAIL`: source and target ran, but data differs.
- `ERROR`: the validation could not execute.

A FAIL should be investigated as a migration/data-quality finding. An ERROR should be investigated as infrastructure, configuration, SQL, or framework behavior.
