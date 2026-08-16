# Environment Setup

## 1. Install Python Dependencies

From the repository root:

```powershell
python -m pip install -r requirements.txt
```

or 

```Powershell

python -m pip install --only-binary=:all: -r requirements.txt

```

Important packages include:

- `python-dotenv` for `.env` loading
- `pyyaml` for validation configuration
- `pandas` for comparison and CSV reports
- `psycopg2-binary` for PostgreSQL
- `pyodbc` for Microsoft SQL Server
- `snowflake-connector-python` for Snowflake
- `boto3` for Athena
- `pytest` for regression tests

For MSSQL, install an appropriate Microsoft ODBC Driver separately.

## 2. Configure `.env`

Copy the example file if needed:

```powershell
copy .env.example .env
```

Never commit `.env`.

### PostgreSQL source

```env
SRC_1_TYPE=postgresql
SRC_1_HOST=<host>
SRC_1_PORT=5432
SRC_1_DATABASE=<database>
SRC_1_SCHEMA=<schema>
SRC_1_USERNAME=<username>
SRC_1_PASSWORD=<password>
```

### MSSQL source

```env
SRC_2_TYPE=mssql
SRC_2_HOST=<server>
SRC_2_PORT=1433
SRC_2_DATABASE=<database>
SRC_2_SCHEMA=dbo
SRC_2_USERNAME=<username>
SRC_2_PASSWORD=<password>
SRC_2_AUTH=sql
```

For Windows authentication, use `SRC_2_AUTH=windows` and configure the account accordingly.

### Athena source

```env
SRC_3_TYPE=athena
SRC_3_REGION=<aws-region>
SRC_3_DATABASE=<catalog-database>
SRC_3_QUERY_RESULT_LOCATION=s3://<bucket>/<prefix>/
SRC_3_USERNAME=<access-key-optional>
SRC_3_PASSWORD=<secret-key-optional>
```

### Snowflake target

```env
SNOWFLAKE_ACCOUNT=<account>
SNOWFLAKE_DATABASE=<database>
SNOWFLAKE_SCHEMA=<schema>
SNOWFLAKE_USERNAME=<username>
SNOWFLAKE_PASSWORD=<password>
SNOWFLAKE_WAREHOUSE=<warehouse>
SNOWFLAKE_ROLE=<role-optional>
```

### AI configuration

AI is optional. Without a DIAL key, deterministic static rules are used.

```env
DIAL_API_KEY=<optional-key>
DIAL_API_BASE=https://ai-proxy.lab.epam.com
DIAL_API_VERSION=2025-04-01-preview
DIAL_MODEL=gpt-4o
```

## 3. Non-Secret Metadata Fallback

`config/database_registry.yaml` can provide database and schema names when those values are missing from `.env`.

It must contain metadata only. Do not put passwords, usernames, API keys, or tokens in this file.

## 4. Verify Environment

```powershell
python test_env_connections.py
python tests\\e2e\\run_all_tests.py --skip-live
```

Expected connection result:

```text
PostgreSQL  PASS
MSSQL       PASS
Snowflake   PASS
Athena      PASS
```
