# PostgreSQL Setup - Quick Start Guide

Follow these steps to quickly set up PostgreSQL with sample data for the Migration Validator PoC.

## 🚀 Quick Start (2 Minutes)

### Using Docker (Recommended)

```powershell
# Navigate to project root
cd c:\EPAM-Personal\Migration-validator

# Start PostgreSQL
docker-compose up -d

# Wait a few seconds, then test the connection
docker exec -it migration_validator_source_db psql -U admin -d source_db -c "SELECT COUNT(*) FROM source_data.users;"
```

**Output should show:** `count: 10`

### Using PowerShell Script

```powershell
# Navigate to postgres directory
cd c:\EPAM-Personal\Migration-validator\tests\postgres

# Run setup script (Docker method)
.\setup.ps1 -Method docker

# Or for local PostgreSQL
.\setup.ps1 -Method local
```

## ✅ Verify Setup

```powershell
# Test Python connection
cd c:\EPAM-Personal\Migration-validator

# Install dependencies (first time only)
pip install psycopg2-binary

# Run connection test
python tests\postgres\test_connection.py
```

Expected output:
```
✓ Successfully connected to PostgreSQL
✓ users - 10 rows
✓ customers - 10 rows
✓ products - 10 rows
✓ orders - 10 rows
✓ transactions - 12 rows
```

## 📊 Database Details

| Property | Value |
|----------|-------|
| Host | localhost |
| Port | 5432 |
| Database | source_db |
| User | admin |
| Password | admin123 |
| Schema | source_data |

## 🗂️ Tables Created

1. **users** (10 rows)
   - Tests: Boolean, NULL, case-sensitivity
   - Key columns: user_id, username, email, is_active, status

2. **customers** (10 rows)
   - Tests: Whitespace trim, numeric precision
   - Key columns: customer_id, customer_name, balance, credit_limit, tier

3. **products** (10 rows)
   - Tests: Empty string vs NULL, data types
   - Key columns: product_id, product_code, product_name, unit_price, discontinued

4. **orders** (10 rows)
   - Tests: Date standardization, relationships
   - Key columns: order_id, customer_id, order_date, order_amount, order_status

5. **transactions** (12 rows)
   - Tests: Numeric precision, NULL handling
   - Key columns: transaction_id, user_id, transaction_type, transaction_amount, remarks

## 🔧 Manual Connection

```powershell
# Using Docker
docker exec -it migration_validator_source_db psql -U admin -d source_db

# Using local psql
$env:PGPASSWORD='admin123'
psql -U admin -h localhost -d source_db

# Inside psql, try:
\dt source_data.*          -- List all tables
SELECT * FROM source_data.users;  -- View users table
\q                         -- Quit
```

## 🐛 Troubleshooting

### Port Already in Use
```powershell
# Check what's using port 5432
netstat -ano | findstr :5432

# Or try a different port in docker-compose.yml:
# Change "5432:5432" to "5433:5432"
```

### Docker Container Won't Start
```powershell
# Check logs
docker logs migration_validator_source_db

# Force restart
docker-compose down
docker-compose up -d
```

### Python Connection Error
```powershell
# Install psycopg2
pip install psycopg2-binary

# If that fails, try:
pip install --upgrade pip
pip install psycopg2-binary --no-cache-dir
```

## 🧹 Cleanup

```powershell
# Stop and remove containers
docker-compose down

# Remove volume (warning: deletes data)
docker-compose down -v

# Or using PowerShell script
.\setup.ps1 -Method docker -Cleanup
```

## 📝 Next Steps

Once PostgreSQL is set up:

1. **Create validation framework** in Python
2. **Build SQL generators** for MSSQL, PostgreSQL, Snowflake
3. **Implement transformation rules** engine
4. **Test queries** against this sample data
5. **Set up Snowflake target** database

## 📚 Learn More

- [Full Setup Guide](README.md)
- [Problem Statement](../Problem-statement.md)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)

---

**Status:** ✅ Ready for development

If you need help, check the [README.md](README.md) for detailed information.
