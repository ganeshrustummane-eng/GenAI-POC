# PostgreSQL DDL (Data Definition Language) - Complete Interview Guide

## Overview
DDL commands are used to define and modify database structures (schemas, tables, indexes, etc.). They are auto-committed by default in PostgreSQL.

---

## 1. CREATE - Creating Database Objects

### 1.1 CREATE DATABASE
```sql
-- Basic database creation
CREATE DATABASE my_database;

-- With specific encoding and locale
CREATE DATABASE my_database
  ENCODING 'UTF8'
  LOCALE 'en_US.UTF-8'
  TEMPLATE template0;

-- With owner and tablespace
CREATE DATABASE my_database
  OWNER postgres
  TABLESPACE pg_default;

-- Check if exists before creating
CREATE DATABASE IF NOT EXISTS my_database;
```

### 1.2 CREATE SCHEMA
```sql
-- Create schema
CREATE SCHEMA my_schema;

-- Create schema with owner
CREATE SCHEMA IF NOT EXISTS my_schema AUTHORIZATION user_name;

-- Usage
CREATE TABLE my_schema.my_table (id INT);
```

### 1.3 CREATE TABLE - Core Concept
```sql
-- Basic table
CREATE TABLE employees (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE,
  salary NUMERIC(10, 2),
  hire_date DATE DEFAULT CURRENT_DATE,
  department_id INT REFERENCES departments(id)
);

-- Temporary table (auto-deleted at session end)
CREATE TEMPORARY TABLE temp_data (
  id INT,
  value VARCHAR(50)
);

-- Table with constraints
CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  price NUMERIC(10, 2) CHECK (price > 0),
  category_id INT NOT NULL,
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- Unlogged table (faster, not logged to WAL - good for temp data)
CREATE UNLOGGED TABLE logs (
  id SERIAL PRIMARY KEY,
  message TEXT
);

-- Inheritance (parent-child table relationship)
CREATE TABLE animals (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100)
);

CREATE TABLE dogs (
  breed VARCHAR(50)
) INHERITS (animals);
```

### 1.4 CREATE INDEX
```sql
-- Simple index
CREATE INDEX idx_email ON users(email);

-- Unique index
CREATE UNIQUE INDEX idx_username ON users(username);

-- Composite index (multiple columns)
CREATE INDEX idx_employee_dept_salary ON employees(department_id, salary);

-- Partial index (only certain rows)
CREATE INDEX idx_active_users ON users(id) WHERE status = 'active';

-- BRIN index (good for large ordered data)
CREATE INDEX idx_timestamp ON events USING BRIN (created_at);

-- Concurrent index creation (non-blocking)
CREATE INDEX CONCURRENTLY idx_on_table ON table_name(column_name);

-- Check if index exists
CREATE INDEX IF NOT EXISTS idx_name ON table_name(column_name);
```

### 1.5 CREATE VIEW
```sql
-- Simple view
CREATE VIEW active_employees AS
SELECT id, name, email FROM employees WHERE status = 'active';

-- View with multiple tables (JOIN)
CREATE VIEW employee_details AS
SELECT 
  e.id, 
  e.name, 
  d.department_name,
  e.salary
FROM employees e
JOIN departments d ON e.department_id = d.id;

-- Materialized view (stores actual data, needs refresh)
CREATE MATERIALIZED VIEW mv_sales_summary AS
SELECT 
  DATE(sale_date) as date,
  SUM(amount) as total_sales
FROM sales
GROUP BY DATE(sale_date);

-- Refresh materialized view
REFRESH MATERIALIZED VIEW mv_sales_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_sales_summary; -- Non-blocking
```

### 1.6 CREATE FUNCTION
```sql
-- Simple function
CREATE FUNCTION add_numbers(a INT, b INT)
RETURNS INT AS $$
BEGIN
  RETURN a + b;
END;
$$ LANGUAGE plpgsql;

-- Function with multiple statements
CREATE FUNCTION get_employee_by_id(emp_id INT)
RETURNS TABLE(id INT, name VARCHAR, email VARCHAR) AS $$
BEGIN
  RETURN QUERY
  SELECT e.id, e.name, e.email FROM employees e WHERE e.id = emp_id;
END;
$$ LANGUAGE plpgsql;

-- Immutable function (optimization hint)
CREATE FUNCTION calculate_age(birth_date DATE)
RETURNS INT AS $$
BEGIN
  RETURN DATE_PART('year', AGE(birth_date))::INT;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

---

## 2. DROP - Deleting Database Objects

### 2.1 DROP TABLE
```sql
-- Basic drop (fails if table doesn't exist)
DROP TABLE employees;

-- Drop if exists (safe)
DROP TABLE IF EXISTS employees;

-- Drop multiple tables
DROP TABLE IF EXISTS employees, departments, projects;

-- DROP with CASCADE (deletes dependent objects)
DROP TABLE employees CASCADE;

-- DROP with RESTRICT (fails if has dependent objects)
DROP TABLE employees RESTRICT;
```

### 2.2 DROP DATABASE
```sql
-- Drop database
DROP DATABASE my_database;

-- Drop if exists
DROP DATABASE IF EXISTS my_database;

-- Cannot drop if users are connected - need to terminate sessions
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'my_database' AND pid <> pg_backend_pid();

DROP DATABASE my_database;
```

### 2.3 DROP INDEX/VIEW/SCHEMA
```sql
-- Drop index
DROP INDEX IF EXISTS idx_email;

-- Drop view
DROP VIEW IF EXISTS active_employees;

-- Drop materialized view
DROP MATERIALIZED VIEW IF EXISTS mv_sales_summary;

-- Drop schema
DROP SCHEMA IF EXISTS my_schema CASCADE;
```

---

## 3. ALTER - Modifying Database Objects

### 3.1 ALTER TABLE - Column Operations
```sql
-- Add column
ALTER TABLE employees ADD COLUMN phone VARCHAR(20);

-- Add column with default
ALTER TABLE employees ADD COLUMN department_id INT DEFAULT 1;

-- Add column with constraints
ALTER TABLE employees 
ADD COLUMN salary NUMERIC(10, 2) NOT NULL DEFAULT 0;

-- Drop column
ALTER TABLE employees DROP COLUMN phone;

-- Drop multiple columns
ALTER TABLE employees DROP COLUMN phone, DROP COLUMN fax;

-- Rename column
ALTER TABLE employees RENAME COLUMN emp_name TO name;

-- Change column data type
ALTER TABLE employees ALTER COLUMN salary TYPE NUMERIC(12, 2);

-- Set default value
ALTER TABLE employees ALTER COLUMN hire_date SET DEFAULT CURRENT_DATE;

-- Drop default
ALTER TABLE employees ALTER COLUMN hire_date DROP DEFAULT;

-- Add NOT NULL constraint
ALTER TABLE employees ALTER COLUMN name SET NOT NULL;

-- Remove NOT NULL constraint
ALTER TABLE employees ALTER COLUMN name DROP NOT NULL;
```

### 3.2 ALTER TABLE - Constraints
```sql
-- Add PRIMARY KEY
ALTER TABLE employees ADD PRIMARY KEY (id);

-- Add UNIQUE constraint
ALTER TABLE employees ADD CONSTRAINT uq_email UNIQUE (email);

-- Add FOREIGN KEY
ALTER TABLE employees 
ADD CONSTRAINT fk_department FOREIGN KEY (department_id) 
REFERENCES departments(id) ON DELETE CASCADE;

-- Add CHECK constraint
ALTER TABLE products ADD CONSTRAINT chk_price CHECK (price > 0);

-- Drop constraint
ALTER TABLE employees DROP CONSTRAINT uq_email;

-- Rename constraint
ALTER TABLE employees RENAME CONSTRAINT old_name TO new_name;
```

### 3.3 ALTER TABLE - Table Operations
```sql
-- Rename table
ALTER TABLE employees RENAME TO staff;

-- Change owner
ALTER TABLE employees OWNER TO new_user;

-- Set table schema
ALTER TABLE employees SET SCHEMA public;

-- Enable/Disable trigger
ALTER TABLE employees DISABLE TRIGGER ALL;
ALTER TABLE employees ENABLE TRIGGER ALL;
```

### 3.4 ALTER INDEX
```sql
-- Rename index
ALTER INDEX idx_email RENAME TO idx_user_email;

-- Set tablespace
ALTER INDEX idx_email SET TABLESPACE new_tablespace;
```

### 3.5 ALTER VIEW
```sql
-- Rename view
ALTER VIEW active_employees RENAME TO active_staff;

-- Change schema
ALTER VIEW active_employees SET SCHEMA new_schema;
```

---

## 4. TRUNCATE - Fast Table Clearing

```sql
-- Basic truncate (resets SERIAL)
TRUNCATE TABLE employees;

-- Truncate multiple tables
TRUNCATE TABLE employees, departments;

-- Truncate with cascade (truncates dependent tables)
TRUNCATE TABLE employees CASCADE;

-- Truncate with RESTRICT (fails if foreign key references exist)
TRUNCATE TABLE employees RESTRICT;

-- Restart identity (reset SERIAL to 1)
TRUNCATE TABLE employees RESTART IDENTITY;

-- Do not restart identity (keep counter at current value)
TRUNCATE TABLE employees CONTINUE IDENTITY;
```

### TRUNCATE vs DELETE
| Feature | TRUNCATE | DELETE |
|---------|----------|--------|
| Speed | Very fast | Slower |
| Triggers | Does NOT fire triggers | Fires triggers |
| WHERE clause | Not supported | Supported |
| Transaction | Can be rolled back | Can be rolled back |
| Disk space | Deallocates space | Keeps space |
| Identity reset | RESTART IDENTITY option | Must reset manually |

---

## 5. COMMENT - Adding Metadata

```sql
-- Comment on table
COMMENT ON TABLE employees IS 'Employee information and details';

-- Comment on column
COMMENT ON COLUMN employees.id IS 'Unique employee identifier';

-- Comment on index
COMMENT ON INDEX idx_email IS 'Index for fast email lookups';

-- Comment on function
COMMENT ON FUNCTION add_numbers(INT, INT) IS 'Adds two integers';

-- Comment on schema
COMMENT ON SCHEMA public IS 'Default schema for public objects';

-- View comments
SELECT * FROM pg_description;
SELECT obj_description('employees'::regclass);
```

---

## 6. RENAME - Renaming Objects

```sql
-- Rename table
ALTER TABLE employees RENAME TO staff;

-- Rename column
ALTER TABLE employees RENAME COLUMN emp_id TO id;

-- Rename index
ALTER INDEX idx_old_name RENAME TO idx_new_name;

-- Rename view
ALTER VIEW old_view_name RENAME TO new_view_name;

-- Rename constraint
ALTER TABLE employees RENAME CONSTRAINT old_constraint TO new_constraint;

-- Rename schema
ALTER SCHEMA old_schema RENAME TO new_schema;

-- Rename function
ALTER FUNCTION add_numbers(INT, INT) RENAME TO sum_numbers;
```

---

## 7. Common Interview Questions & Answers

### Q1: What's the difference between DROP and TRUNCATE?
**Answer:**
- **DROP**: Removes table structure and data, deallocates disk space, triggers triggers
- **TRUNCATE**: Removes only data, keeps structure, faster, doesn't fire triggers
- TRUNCATE can be rolled back in a transaction
- DROP is slower but completely removes the object

### Q2: What happens if I drop a table that has foreign key references?
**Answer:**
Use `DROP TABLE ... CASCADE` to drop the table and all dependent objects.
Using `RESTRICT` will fail if dependencies exist.
```sql
DROP TABLE parent_table CASCADE;  -- Success, deletes dependent objects
DROP TABLE parent_table RESTRICT; -- Fails if child tables reference it
```

### Q3: Can I undo a DROP or TRUNCATE command?
**Answer:**
Yes, if it's in a transaction that hasn't been committed:
```sql
BEGIN;
TRUNCATE TABLE employees;
ROLLBACK; -- Undoes the truncate
```
Without a transaction, you cannot undo. Always backup important data.

### Q4: What's the difference between a regular view and a materialized view?
**Answer:**
- **View**: Virtual, queries the underlying tables in real-time, always current
- **Materialized View**: Stores computed data physically, must be refreshed manually, faster queries but may be stale

### Q5: How do I check if a table/index exists before creating?
**Answer:**
```sql
-- Using IF NOT EXISTS (recommended)
CREATE TABLE IF NOT EXISTS employees (id INT);
CREATE INDEX IF NOT EXISTS idx_email ON users(email);

-- Using information_schema
SELECT EXISTS (
  SELECT FROM information_schema.tables 
  WHERE table_name = 'employees'
);
```

### Q6: What's the difference between UNIQUE constraint and UNIQUE INDEX?
**Answer:**
- **UNIQUE Constraint**: Enforces uniqueness, can have multiple NULL values
- **UNIQUE INDEX**: Also enforces uniqueness, faster lookups
- In PostgreSQL, UNIQUE constraint internally creates a unique index
- UNIQUE allows multiple NULLs (in PostgreSQL), but some DBs don't

### Q7: How do I rename a table with minimal impact?
**Answer:**
```sql
ALTER TABLE old_table_name RENAME TO new_table_name;
-- This is a fast metadata operation, doesn't require data movement
-- But application code using old name will break until updated
```

### Q8: What's an unlogged table?
**Answer:**
```sql
CREATE UNLOGGED TABLE temp_logs (id SERIAL, message TEXT);
-- Faster because not written to WAL (Write-Ahead Logging)
-- Data is lost if server crashes
-- Good for: temporary data, logs, cache tables
-- Bad for: critical data that must survive crashes
```

### Q9: How do I drop a database that has active connections?
**Answer:**
```sql
-- Terminate all connections first
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'database_name' AND pid <> pg_backend_pid();

-- Then drop
DROP DATABASE database_name;
```

### Q10: What's the performance impact of adding a column to a large table?
**Answer:**
- PostgreSQL uses lazy initialization for adding columns with defaults
- `ALTER TABLE ADD COLUMN` is fast even on large tables (just metadata change)
- But every read after that will compute the default value
- Better: use `ALTER TABLE ADD COLUMN` without default, then update specific rows

### Q11: Can I use TRUNCATE with a WHERE clause?
**Answer:**
No. TRUNCATE doesn't support WHERE clause. Use DELETE instead:
```sql
TRUNCATE TABLE employees; -- Removes all rows

DELETE FROM employees WHERE department_id = 5; -- With WHERE condition
```

### Q12: What's the purpose of CASCADE and RESTRICT in DROP?
**Answer:**
- **CASCADE**: Drops the object and all dependent objects (risky, use carefully)
- **RESTRICT**: Fails if dependent objects exist (safer, forces you to drop dependencies first)
```sql
DROP TABLE parent CASCADE;   -- Deletes parent and all child tables
DROP TABLE parent RESTRICT;  -- Fails if child tables exist
```

### Q13: How do I add a NOT NULL constraint to an existing column with NULL values?
**Answer:**
```sql
-- Step 1: Update NULL values to a default
UPDATE employees SET department_id = 1 WHERE department_id IS NULL;

-- Step 2: Add NOT NULL constraint
ALTER TABLE employees ALTER COLUMN department_id SET NOT NULL;
```

### Q14: What happens to identity sequence when I drop and recreate a table?
**Answer:**
```sql
CREATE TABLE employees (id SERIAL PRIMARY KEY);
INSERT INTO employees (id) VALUES (1); -- id = 1
DROP TABLE employees;
CREATE TABLE employees (id SERIAL PRIMARY KEY);
INSERT INTO employees DEFAULT VALUES; -- id = 1 (starts fresh)
```

### Q15: How do I find and fix duplicate constraint names?
**Answer:**
```sql
-- Find constraint names
SELECT constraint_name, table_name 
FROM information_schema.table_constraints 
WHERE table_schema = 'public';

-- Rename to fix duplicates
ALTER TABLE table_name RENAME CONSTRAINT old_name TO new_name;
```

---

## 8. Best Practices & Tips

### ✅ DO:
- ✓ Always use `IF NOT EXISTS` for safety
- ✓ Use descriptive constraint names (e.g., `fk_employees_dept`, not `fk1`)
- ✓ Back up before DROP/TRUNCATE on production
- ✓ Use transactions for multiple DDL operations
- ✓ Document schema changes in comments
- ✓ Use CHECK constraints for data validation
- ✓ Create indexes on foreign keys
- ✓ Use SERIAL for simple auto-increment, UUID for distributed systems

### ❌ DON'T:
- ✗ Drop tables without backup on production
- ✗ Use TRUNCATE without testing rollback
- ✗ Create indexes on every column (maintenance overhead)
- ✗ Use CASCADE carelessly (may delete more than intended)
- ✗ Create views on views on views (performance issues)
- ✗ Use VARCHAR without length for critical fields
- ✗ Name columns with SQL keywords (id, name are ok)
- ✗ Forget to restart identity after TRUNCATE if needed

---

## 9. Advanced Scenarios

### Scenario 1: Safely rename a production table
```sql
-- Create new table with new name
CREATE TABLE employees_new AS SELECT * FROM employees;

-- Create indexes and constraints on new table
CREATE INDEX idx_employees_new_email ON employees_new(email);

-- Switch tables (atomically)
BEGIN;
ALTER TABLE employees RENAME TO employees_old;
ALTER TABLE employees_new RENAME TO employees;
COMMIT;

-- Drop old table after verification
DROP TABLE employees_old;
```

### Scenario 2: Add NOT NULL column to populated table
```sql
-- Add with default
ALTER TABLE employees ADD COLUMN department_id INT DEFAULT 1;

-- Fill existing rows
UPDATE employees SET department_id = 1 WHERE department_id IS NULL;

-- Make NOT NULL
ALTER TABLE employees ALTER COLUMN department_id SET NOT NULL;

-- Remove default if not needed
ALTER TABLE employees ALTER COLUMN department_id DROP DEFAULT;
```

### Scenario 3: Change column type with data conversion
```sql
-- Original: id TEXT, need to convert to INT
ALTER TABLE employees 
ALTER COLUMN id TYPE INT USING id::INT;
```

### Scenario 4: Create partial index for optimization
```sql
-- Index only active employees (smaller, faster)
CREATE INDEX idx_active_employees ON employees(id) 
WHERE status = 'active';
```

---

## 10. Quick Reference Cheat Sheet

```sql
-- CREATE
CREATE DATABASE db_name;
CREATE TABLE table_name (columns...);
CREATE INDEX idx_name ON table(column);
CREATE VIEW view_name AS SELECT...;

-- DROP
DROP TABLE IF EXISTS table_name CASCADE;
DROP DATABASE IF EXISTS db_name;

-- ALTER
ALTER TABLE table_name ADD COLUMN col_name TYPE;
ALTER TABLE table_name DROP COLUMN col_name;
ALTER TABLE table_name RENAME TO new_name;
ALTER TABLE table_name ADD CONSTRAINT con_name UNIQUE(col);

-- TRUNCATE
TRUNCATE TABLE table_name RESTART IDENTITY;

-- COMMENT
COMMENT ON TABLE table_name IS 'Description';

-- RENAME
ALTER TABLE old_name RENAME TO new_name;
ALTER TABLE table_name RENAME COLUMN old_col TO new_col;
```

---

## Key Takeaway for Interviews:
DDL operations are structural changes to your database. Be careful with DROP and TRUNCATE on production. Always use transactions, backups, and IF EXISTS/IF NOT EXISTS clauses. Understand the performance implications and know when to use CASCADE vs RESTRICT.

Good luck with your interview! 🎯
