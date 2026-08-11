# PostgreSQL Source Database Setup Guide

This directory contains the configuration and scripts to set up a PostgreSQL database with sample data for the Migration Validator PoC.

## Overview

The PostgreSQL database contains 5 sample tables designed to test various data transformation and validation rules:

| Table | Purpose | Key Features |
|-------|---------|--------------|
| `users` | Tests boolean, null, and case-sensitivity | BOOLEAN type, NULL handling |
| `customers` | Tests whitespace trim and numeric precision | VARCHAR with spaces, NUMERIC types |
| `products` | Tests empty strings and data types | NULL vs empty string distinction |
| `orders` | Tests date standardization | DATE types, complex relationships |
| `transactions` | Tests numeric precision and nulls | NUMERIC precision, NULL remarks |

## Setup Options

### Option 1: Docker Compose (Recommended)

#### Prerequisites
- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)
- Windows PowerShell or Command Prompt

#### Steps

1. **Start PostgreSQL Container**
   ```powershell
   cd c:\EPAM-Personal\Migration-validator
   docker-compose up -d
   ```

2. **Verify Container is Running**
   ```powershell
   docker-compose ps
   docker logs migration_validator_source_db
   ```

3. **Verify Data Loaded**
   ```powershell
   # Connect to PostgreSQL
   docker exec -it migration_validator_source_db psql -U admin -d source_db
   
   # Inside psql:
   \dt source_data.*
   SELECT * FROM source_data.users;
   \q
   ```

4. **Stop PostgreSQL Container**
   ```powershell
   docker-compose down
   ```

### Option 2: Local PostgreSQL Installation

#### Prerequisites
- PostgreSQL 15+ installed locally
- psql CLI tool available
- Administrator access

#### Steps

1. **Create Database**
   ```powershell
   $env:PGPASSWORD='admin123'
   psql -U admin -h localhost -c "CREATE DATABASE source_db;"
   ```

2. **Run Initialization Scripts**
   ```powershell
   $env:PGPASSWORD='admin123'
   
   # Run schema creation
   psql -U admin -h localhost -d source_db -f "tests\postgres\init\01-init-schema.sql"
   
   # Run data insertion
   psql -U admin -h localhost -d source_db -f "tests\postgres\init\02-insert-sample-data.sql"
   ```

3. **Verify Data**
   ```powershell
   $env:PGPASSWORD='admin123'
   psql -U admin -h localhost -d source_db -c "SELECT * FROM source_data.users LIMIT 5;"
   ```

### Option 3: PowerShell Setup Script

A setup script is provided for Windows users:

```powershell
# From the project root
.\tests\postgres\setup.ps1
```

## Database Details

### Connection Information

| Parameter | Value |
|-----------|-------|
| Host | localhost (or `postgres` if using Docker) |
| Port | 5432 |
| Database | source_db |
| User | admin |
| Password | admin123 |
| Schema | source_data |

### Connection String

```
postgresql://admin:admin123@localhost:5432/source_db
```

## Sample Data Statistics

```sql
-- Run this query to see data counts
SELECT 'Users' as table_name, COUNT(*) as row_count FROM source_data.users
UNION ALL
SELECT 'Customers', COUNT(*) FROM source_data.customers
UNION ALL
SELECT 'Products', COUNT(*) FROM source_data.products
UNION ALL
SELECT 'Orders', COUNT(*) FROM source_data.orders
UNION ALL
SELECT 'Transactions', COUNT(*) FROM source_data.transactions;
```

Expected Results:
- Users: 10 rows
- Customers: 10 rows
- Products: 10 rows
- Orders: 10 rows
- Transactions: 12 rows

## Test Data Features

The sample data is specifically designed to test transformation rules:

### Boolean Conversion Testing
- `users.is_active`: Mix of TRUE and FALSE values
- `products.discontinued`: Tests boolean representation

### Null Handling Testing
- `users.email`: Some NULL values
- `customers.phone`: Some NULL values
- `customers.credit_limit`: Some NULL values
- `transactions.remarks`: Some NULL values

### Whitespace/Trim Testing
- `customers.customer_name`: Some with leading/trailing spaces
- `customers.company_name`: Intentional spaces (' Tech Solutions Inc ')

### Case Sensitivity Testing
- `users.status`: Stored in lowercase ('active', 'inactive')
- `products.product_code`: Stored with hyphens ('PROD-001')

### Numeric Precision Testing
- `customers.balance`: NUMERIC(12, 2) with values like 1500.00, 2500.50
- `orders.tax_amount`: NUMERIC(10, 2) values

### Date Standardization Testing
- `customers.registration_date`: DATE type (2024-01-10, etc.)
- `orders.order_date` and `ship_date`: DATE values

### Empty String vs NULL Testing
- `products.description`: Some with empty string '', some with NULL

## Troubleshooting

### PostgreSQL Won't Connect
```powershell
# Check if Docker container is running
docker ps | grep postgres

# View logs
docker logs migration_validator_source_db

# Restart container
docker-compose restart
```

### Connection Refused
- Ensure PostgreSQL is running on port 5432
- Check firewall settings
- Verify credentials in `connection.config.json`

### Data Not Loaded
```powershell
# Check if schema exists
docker exec -it migration_validator_source_db psql -U admin -d source_db -c "\dn"

# Check if tables exist
docker exec -it migration_validator_source_db psql -U admin -d source_db -c "\dt source_data.*"

# Check table contents
docker exec -it migration_validator_source_db psql -U admin -d source_db -c "SELECT COUNT(*) FROM source_data.users;"
```

### Permission Denied
- Ensure you have admin/sudoer privileges
- For Docker: Ensure Docker daemon is running
- For local: Ensure PostgreSQL service is running

## Cleanup

### Docker
```powershell
# Stop containers
docker-compose down

# Remove volume (warning: deletes data)
docker-compose down -v
```

### Local PostgreSQL
```powershell
$env:PGPASSWORD='admin123'
psql -U admin -h localhost -c "DROP DATABASE source_db;"
```

## Next Steps

Once PostgreSQL is set up with sample data:

1. Create the validation framework in Python
2. Generate SQL queries for comparison with Snowflake
3. Test transformation rules against this data
4. Document validation results

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [psql Command Reference](https://www.postgresql.org/docs/current/app-psql.html)
