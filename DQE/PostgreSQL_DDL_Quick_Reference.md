# PostgreSQL DDL - Quick Reference Cheat Sheet

## 🎯 One-Liner Definitions

| Command | Purpose | Key Syntax |
|---------|---------|-----------|
| **CREATE** | Create objects | `CREATE TABLE/DATABASE/INDEX/VIEW...` |
| **DROP** | Delete objects | `DROP TABLE/DATABASE IF EXISTS ... CASCADE/RESTRICT` |
| **ALTER** | Modify objects | `ALTER TABLE ... ADD/DROP/RENAME COLUMN...` |
| **TRUNCATE** | Fast delete all rows | `TRUNCATE TABLE ... RESTART IDENTITY CASCADE/RESTRICT` |
| **COMMENT** | Add metadata | `COMMENT ON TABLE/COLUMN IS 'text'` |
| **RENAME** | Rename objects | `ALTER TABLE ... RENAME TO ...` |

---

## CREATE Cheat Sheet

### CREATE TABLE
```sql
CREATE TABLE table_name (
  id SERIAL PRIMARY KEY,
  column_name TYPE CONSTRAINT,
  CONSTRAINT name UNIQUE(col),
  CONSTRAINT name FOREIGN KEY(col) REFERENCES other_table(id)
);
```

**Common Constraints:**
- `PRIMARY KEY` - Unique + Not Null
- `NOT NULL` - Must have value
- `UNIQUE` - No duplicates (allows multiple NULL)
- `CHECK (condition)` - Value validation
- `DEFAULT value` - Default value
- `FOREIGN KEY` - Reference another table
- `REFERENCES table(col) ON DELETE CASCADE/RESTRICT`

### CREATE INDEX
```sql
CREATE [UNIQUE] INDEX [CONCURRENTLY] idx_name ON table(col);
CREATE INDEX idx_partial ON table(col) WHERE condition;
CREATE INDEX idx_composite ON table(col1, col2);
```

### CREATE VIEW / MATERIALIZED VIEW
```sql
CREATE VIEW name AS SELECT...;
CREATE MATERIALIZED VIEW name AS SELECT...;
REFRESH MATERIALIZED VIEW name;
```

---

## DROP Cheat Sheet

```sql
-- Safe drops (with IF EXISTS)
DROP TABLE IF EXISTS table_name CASCADE;
DROP DATABASE IF EXISTS db_name;
DROP INDEX IF EXISTS idx_name;
DROP VIEW IF EXISTS view_name;
DROP SCHEMA IF EXISTS schema_name CASCADE;

-- CASCADE vs RESTRICT
CASCADE   -- Also drop dependent objects
RESTRICT -- Fail if dependencies exist (default)
```

---

## ALTER Cheat Sheet

### Column Operations
```sql
ALTER TABLE table_name ADD COLUMN col_name TYPE [DEFAULT val];
ALTER TABLE table_name DROP COLUMN col_name;
ALTER TABLE table_name RENAME COLUMN old TO new;
ALTER TABLE table_name ALTER COLUMN col_name TYPE NEW_TYPE USING col::NEW_TYPE;
ALTER TABLE table_name ALTER COLUMN col_name SET DEFAULT value;
ALTER TABLE table_name ALTER COLUMN col_name DROP DEFAULT;
ALTER TABLE table_name ALTER COLUMN col_name SET NOT NULL;
ALTER TABLE table_name ALTER COLUMN col_name DROP NOT NULL;
```

### Constraints
```sql
ALTER TABLE table_name ADD CONSTRAINT name PRIMARY KEY(col);
ALTER TABLE table_name ADD CONSTRAINT name UNIQUE(col);
ALTER TABLE table_name ADD CONSTRAINT name FOREIGN KEY(col) REFERENCES other(id);
ALTER TABLE table_name ADD CONSTRAINT name CHECK(condition);
ALTER TABLE table_name DROP CONSTRAINT name;
ALTER TABLE table_name RENAME CONSTRAINT old_name TO new_name;
```

### Table Operations
```sql
ALTER TABLE old_name RENAME TO new_name;
ALTER TABLE table_name OWNER TO user_name;
ALTER TABLE table_name SET SCHEMA new_schema;
```

---

## TRUNCATE Cheat Sheet

```sql
TRUNCATE TABLE table_name;                           -- Basic
TRUNCATE TABLE table_name RESTART IDENTITY;         -- Reset sequence
TRUNCATE TABLE table_name CONTINUE IDENTITY;        -- Keep sequence
TRUNCATE TABLE table_name CASCADE;                   -- With dependencies
TRUNCATE TABLE table_name RESTRICT;                 -- Fail if dependencies

-- TRUNCATE vs DELETE
DELETE vs TRUNCATE:
- DELETE: Slower, fires triggers, supports WHERE, keeps space
- TRUNCATE: Fast, no triggers, no WHERE, deallocates space
```

---

## COMMENT Cheat Sheet

```sql
COMMENT ON TABLE table_name IS 'Description';
COMMENT ON COLUMN table_name.col_name IS 'Description';
COMMENT ON INDEX index_name IS 'Description';
COMMENT ON SCHEMA schema_name IS 'Description';
COMMENT ON FUNCTION func_name(params) IS 'Description';

-- View comments
SELECT obj_description('table_name'::regclass);
SELECT * FROM pg_description;
```

---

## RENAME Cheat Sheet

```sql
ALTER TABLE old_name RENAME TO new_name;
ALTER TABLE table_name RENAME COLUMN old_col TO new_col;
ALTER INDEX old_name RENAME TO new_name;
ALTER VIEW old_name RENAME TO new_name;
ALTER SCHEMA old_name RENAME TO new_name;
ALTER FUNCTION old_func(params) RENAME TO new_func;
ALTER CONSTRAINT old_name RENAME TO new_name;
```

---

## Common Patterns

### Safe Table Creation
```sql
CREATE TABLE IF NOT EXISTS table_name (
  id SERIAL PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Safe Table Deletion
```sql
DROP TABLE IF EXISTS table_name CASCADE;
```

### Add Column Safely
```sql
ALTER TABLE table_name ADD COLUMN new_col TYPE DEFAULT value;
UPDATE table_name SET new_col = value WHERE condition;
ALTER TABLE table_name ALTER COLUMN new_col DROP DEFAULT;
ALTER TABLE table_name ALTER COLUMN new_col SET NOT NULL;
```

### Rename Column Safely
```sql
ALTER TABLE table_name RENAME COLUMN old_col TO new_col;
-- Update dependent views/code
```

### Create Index Without Blocking
```sql
CREATE INDEX CONCURRENTLY idx_name ON table_name(column_name);
```

### Make Column NOT NULL
```sql
UPDATE table_name SET col = value WHERE col IS NULL;
ALTER TABLE table_name ALTER COLUMN col SET NOT NULL;
```

### Change Column Type
```sql
ALTER TABLE table_name 
ALTER COLUMN col_name TYPE NEW_TYPE USING col_name::NEW_TYPE;
```

---

## Key Interview Answers

| Question | Answer |
|----------|--------|
| **DROP vs TRUNCATE?** | DROP removes structure+data, TRUNCATE only data. TRUNCATE faster. |
| **How to rename table safely?** | `ALTER TABLE old RENAME TO new;` (metadata only, very fast) |
| **Add NOT NULL to populated column?** | Update NULLs first, then `ALTER COLUMN SET NOT NULL` |
| **Create index on large table?** | Use `CREATE INDEX CONCURRENTLY` (non-blocking) |
| **Drop table with FK references?** | Use `DROP TABLE ... CASCADE` (or drop children first) |
| **Undo TRUNCATE?** | Only if uncommitted: `ROLLBACK;` Otherwise, restore from backup |
| **Partial vs Full index?** | Partial: smaller, faster, for filtered queries. Use `WHERE clause` |
| **View vs Materialized View?** | View: virtual, always current. Materialized: stores data, must refresh |
| **Performance of ADD COLUMN?** | Fast (metadata), but every read computes default. No data movement. |
| **UNIQUE vs UNIQUE INDEX?** | UNIQUE constraint creates unique index internally. Allows multiple NULLs. |

---

## Critical Safety Rules

✅ **DO:**
- Always use `IF NOT EXISTS` / `IF NOT EXISTS` in production
- Back up before DROP/TRUNCATE
- Use transactions for multiple DDL operations
- Test on dev first
- Use descriptive constraint/index names
- Document schema changes
- Use CASCADE carefully, know the impact
- Create indexes on foreign keys

❌ **DON'T:**
- Drop production tables without backup
- Use CASCADE without understanding dependencies
- Create indexes on every column
- Forget to consider data migration in ALTER
- Create views on views on views
- Use generic constraint names (fk1, uc1)
- Assume TRUNCATE is reversible without transaction

---

## Advanced Tricks

### Find Unused Indexes
```sql
SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0;
```

### Drop Unused Indexes
```sql
DROP INDEX idx_name;
```

### Reindex for Performance
```sql
REINDEX INDEX CONCURRENTLY index_name;
```

### Check Table Size
```sql
SELECT pg_size_pretty(pg_total_relation_size('table_name'));
```

### Find Duplicate Indexes
```sql
SELECT * FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname;
```

### Find Missing Indexes on FKs
```sql
SELECT * FROM information_schema.table_constraints 
WHERE constraint_type = 'FOREIGN KEY' AND table_schema = 'public';
```

### Terminate Connections to Database
```sql
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'database_name' AND pid <> pg_backend_pid();
```

---

## Interview Flow

**When asked about DDL:**
1. Define DDL (CREATE, DROP, ALTER, TRUNCATE, COMMENT, RENAME)
2. Explain the specific command asked
3. Give syntax example
4. Mention edge cases/gotchas
5. Discuss safety/best practices
6. Ask clarifying questions (production? data size? downtime tolerance?)

**Example:**
> "DDL (Data Definition Language) includes 6 commands. For CREATE, we use it to define tables, indexes, views. When creating tables, we add constraints like PK, FK, NOT NULL, CHECK. We should always use IF NOT EXISTS for safety. For indexes, we use CONCURRENTLY on production to avoid locks. Here's an example: `CREATE TABLE IF NOT EXISTS...`. Are you asking about a specific scenario?"

---

## Emergency Checklist

- [ ] Do I have a backup?
- [ ] Is this in a transaction?
- [ ] Can I test on dev first?
- [ ] Do I understand CASCADE impact?
- [ ] Will this lock the table long?
- [ ] Is the downtime acceptable?
- [ ] Have I verified the syntax?
- [ ] Can I rollback if needed?

**Remember:** When in doubt, ask for clarification rather than making assumptions! 🎯

---

Last Updated: 2026-07-29
Study Duration: 30-60 minutes to master
Good Luck! 🚀
