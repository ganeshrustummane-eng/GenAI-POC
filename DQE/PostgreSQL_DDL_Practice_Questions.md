# PostgreSQL DDL - Practice Questions for Interviews

## Section 1: Basic Knowledge (Easy)

### Q1.1: What is DDL?
**Your Answer:**
```
[Write your answer here]
```

**Expected Answer:**
Data Definition Language (DDL) consists of SQL commands used to create, modify, and delete database structures (tables, indexes, views, schemas, databases, etc.). Common DDL commands: CREATE, DROP, ALTER, TRUNCATE, COMMENT, RENAME.

---

### Q1.2: What are the 6 main DDL commands in PostgreSQL?
**Your Answer:**
```
[Write your answer here]
```

**Expected Answer:**
1. CREATE - Create database objects
2. DROP - Delete database objects
3. ALTER - Modify existing objects
4. TRUNCATE - Delete all rows from a table
5. COMMENT - Add metadata/descriptions
6. RENAME - Rename objects

---

### Q1.3: Write a CREATE TABLE statement with the following requirements:
- Table name: `students`
- Columns: id (auto-increment, primary key), name (not null), email (unique), age (integer), enrollment_date (default today)

**Your Answer:**
```sql
[Write your CREATE TABLE statement]
```

**Expected Answer:**
```sql
CREATE TABLE students (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE,
  age INT,
  enrollment_date DATE DEFAULT CURRENT_DATE
);
```

---

## Section 2: Intermediate Concepts (Medium)

### Q2.1: What's the difference between DELETE and TRUNCATE?

| Aspect | DELETE | TRUNCATE |
|--------|--------|----------|
| Speed | | |
| Triggers | | |
| WHERE clause | | |
| Disk space | | |

**Your Answer:**
```
[Fill the table above]
```

**Expected Answer:**

| Aspect | DELETE | TRUNCATE |
|--------|--------|----------|
| Speed | Slower (row-by-row) | Very fast (deallocates space) |
| Triggers | Fires DELETE triggers | Does NOT fire triggers |
| WHERE clause | Supported | NOT supported |
| Disk space | Keeps allocated space | Deallocates space |

---

### Q2.2: You need to create an index on a large production table without blocking queries. What command would you use?

**Your Answer:**
```sql
[Write the command]
```

**Expected Answer:**
```sql
CREATE INDEX CONCURRENTLY idx_name ON table_name(column_name);
```
The CONCURRENTLY keyword allows index creation without locking the table.

---

### Q2.3: Write a query to add a FOREIGN KEY constraint to an existing table.

Table name: `orders`
Column: `customer_id`
Reference: `customers(id)`
Behavior: Delete orders when customer is deleted

**Your Answer:**
```sql
[Write the ALTER TABLE statement]
```

**Expected Answer:**
```sql
ALTER TABLE orders 
ADD CONSTRAINT fk_orders_customer 
FOREIGN KEY (customer_id) 
REFERENCES customers(id) 
ON DELETE CASCADE;
```

---

### Q2.4: What is a materialized view and when would you use it?

**Your Answer:**
```
[Write your explanation]
```

**Expected Answer:**
A materialized view is a physical copy of query results stored on disk. 
- Use when: Query is expensive, data doesn't change frequently, need fast reads
- Must be refreshed: REFRESH MATERIALIZED VIEW mv_name;
- Difference from regular view: Regular views are virtual (query on-demand), materialized views store actual data

---

### Q2.5: Write a safe way to drop a table that may have dependent foreign key references.

**Your Answer:**
```sql
[Write the command]
```

**Expected Answer:**
```sql
DROP TABLE IF EXISTS table_name CASCADE;
```
- IF EXISTS prevents error if table doesn't exist
- CASCADE drops the table and all dependent objects
- Alternative: Use RESTRICT to ensure no dependencies exist

---

## Section 3: Real-World Scenarios (Hard)

### Q3.1: Migration Scenario
You have a table with millions of rows and need to rename a column from `user_id` to `customer_id`. Write the steps:

**Your Answer:**
```
Step 1: [Write step]
Step 2: [Write step]
Step 3: [Write step]
```

**Expected Answer:**
```
Step 1: ALTER TABLE users RENAME COLUMN user_id TO customer_id;
Step 2: Verify data integrity with: SELECT COUNT(*) FROM users WHERE customer_id IS NULL;
Step 3: Update any views or dependent objects that reference the old column name
```

---

### Q3.2: Production Problem
Your boss says: "We truncated the wrong table with millions of rows. Can we undo it?"

What would you say?

**Your Answer:**
```
[Your response]
```

**Expected Answer:**
"If the TRUNCATE was within an uncommitted transaction, we can ROLLBACK. If it was committed, we cannot undo directly. However, if we have point-in-time recovery (PITR) or backups, we can restore from backup. This is why we should:
1. Always test TRUNCATE on dev/test environments first
2. Use transactions for critical operations: BEGIN; TRUNCATE...; [verify]; COMMIT;
3. Maintain regular backups
4. Use proper access controls to prevent accidental truncation"
```

---

### Q3.3: Design Decision
You need to create a tracking table for user activities. It will receive thousands of inserts per second. Would you make it a regular table or UNLOGGED table? Why?

**Your Answer:**
```
[Your decision and reasoning]
```

**Expected Answer:**
"UNLOGGED table because:
- Pros: Much faster inserts (not written to WAL), perfect for high-volume logging
- Cons: Data lost if server crashes
- Trade-off: Activity logs are not critical data, speed is more important
- Note: Must have backup/recovery strategy for critical production data

Use regular table if data must survive crashes."
```

---

### Q3.4: Performance Optimization
You have a large `orders` table. Most queries filter by `status = 'active'` and `created_date > '2024-01-01'`. 
Write the optimal index creation:

**Your Answer:**
```sql
[Write the index creation]
```

**Expected Answer:**
```sql
CREATE INDEX CONCURRENTLY idx_active_recent_orders 
ON orders(created_date, status) 
WHERE status = 'active';
```
Reasons:
- Partial index (WHERE clause) is smaller, faster
- Composite index covers both filter conditions
- CONCURRENTLY so it doesn't lock the table

---

### Q3.5: Constraint Scenario
You need to ensure that:
- Product prices are always positive
- Product names are not empty
- Product codes are unique

Write the CREATE TABLE with all constraints:

**Your Answer:**
```sql
[Write CREATE TABLE]
```

**Expected Answer:**
```sql
CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  code VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  price NUMERIC(10, 2) NOT NULL CHECK (price > 0),
  CONSTRAINT uq_product_code UNIQUE (code),
  CONSTRAINT chk_price_positive CHECK (price > 0),
  CONSTRAINT chk_name_not_empty CHECK (name <> '')
);
```

---

## Section 4: Tricky Questions (Expert)

### Q4.1: Identity/Sequence Management
After running `TRUNCATE TABLE users RESTART IDENTITY;`, the next insert has id=1. But your application expects id=1001. How do you fix this?

**Your Answer:**
```
[Your solution]
```

**Expected Answer:**
```sql
-- Option 1: Set sequence manually
ALTER SEQUENCE users_id_seq RESTART WITH 1001;

-- Option 2: Before truncate, save max id
TRUNCATE TABLE users CONTINUE IDENTITY;

-- Option 3: Don't use RESTART IDENTITY, manually reset after
TRUNCATE TABLE users;
SELECT setval('users_id_seq', 1001);
```

---

### Q4.2: Concurrent Operations
Two transactions happen simultaneously:
- TX1: `ALTER TABLE users DROP COLUMN phone;`
- TX2: `SELECT * FROM users;`

What happens?

**Your Answer:**
```
[Your explanation]
```

**Expected Answer:**
"PostgreSQL uses MVCC (Multi-Version Concurrency Control):
- TX1 acquires AccessExclusiveLock (strongest lock) on the table
- TX2 (if started before TX1's ALTER) can still read using old schema
- TX2 (if started after TX1 commits) will read with the new schema (no phone column)
- If TX2 tries to read phone column after TX1 commits, error occurs
- ALTER waits for concurrent transactions to finish"
```

---

### Q4.3: Foreign Key Cascade
Table A (parent) has child tables B and C. Both have ON DELETE CASCADE.
If you `DROP TABLE A CASCADE;`, what happens?

**Your Answer:**
```
[Your explanation]
```

**Expected Answer:**
"All three tables are dropped:
- DROP TABLE A CASCADE drops A
- All objects referencing A are dropped (tables B and C, views using A, etc.)
- This is dangerous and should be used carefully

Better practice:
DROP TABLE A RESTRICT; -- Fails if B or C exist, forcing you to plan drops
DROP TABLE B, C; -- Drop children first
DROP TABLE A; -- Then drop parent"
```

---

### Q4.4: Column Type Conversion
You need to change a VARCHAR column to BIGINT. What's the safe way?

**Your Answer:**
```sql
[Write the ALTER TABLE command with safe conversion]
```

**Expected Answer:**
```sql
-- Option 1: Direct conversion with USING (if data is numeric)
ALTER TABLE table_name ALTER COLUMN column_name TYPE BIGINT USING column_name::BIGINT;

-- Option 2: Safe migration for large tables
-- Step 1: Create new column
ALTER TABLE table_name ADD COLUMN column_name_new BIGINT;

-- Step 2: Copy and convert data
UPDATE table_name SET column_name_new = column_name::BIGINT;

-- Step 3: Drop old column
ALTER TABLE table_name DROP COLUMN column_name;

-- Step 4: Rename new column
ALTER TABLE table_name RENAME COLUMN column_name_new TO column_name;

-- Use USING for inline conversion on smaller tables
ALTER TABLE table_name ALTER COLUMN column_name TYPE BIGINT USING column_name::BIGINT;
```

---

### Q4.5: Index Bloat and Maintenance
Your queries are slow despite having indexes. The indexes were created months ago. What could be the issue and how do you fix it?

**Your Answer:**
```
[Your explanation]
```

**Expected Answer:**
"Issue: Index bloat
- Indexes accumulate dead tuples (from UPDATEs/DELETEs)
- VACUUM processes dead tuples but doesn't shrink indexes

Solutions:
1. REINDEX the index:
   REINDEX INDEX CONCURRENTLY index_name;

2. Drop and recreate (for critical indexes):
   DROP INDEX index_name;
   CREATE INDEX CONCURRENTLY index_name ON table(column);

3. Monitor and maintain:
   SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0; -- Unused indexes
   VACUUM ANALYZE; -- Cleanup

4. Use FILLFACTOR for UPDATE-heavy tables:
   CREATE INDEX idx_name ON table(column) WITH (fillfactor = 70);
```

---

## Self-Assessment

### Score Your Answers:
- **Section 1 (Easy)**: If you got 3/3, you have basics down ✓
- **Section 2 (Medium)**: If you got 4/5, you're interview-ready ✓
- **Section 3 (Hard)**: If you got 3/5, you have good depth ✓
- **Section 4 (Expert)**: If you got 2/5, you're advanced ✓

---

## Tips for Your Interview:

1. **Listen carefully** to the question - understand the requirement before answering
2. **Think step-by-step** - explain your reasoning, not just the answer
3. **Consider edge cases** - what if the table is large? Has dependent objects? Is in production?
4. **Show best practices** - use IF EXISTS, CONCURRENTLY, transactions, backups
5. **Ask clarifying questions** - "Is this production? How many rows? What's the acceptable downtime?"
6. **Mention performance** - talk about CONCURRENT, CASCADE vs RESTRICT, partial indexes
7. **Safety first** - always mention backups, testing, and rollback strategies
8. **Trade-offs** - understand when to use each command and why

---

## Last-Minute Review Checklist:

- [ ] Can create tables with constraints (PK, FK, CHECK, UNIQUE, NOT NULL)
- [ ] Can drop objects safely (IF EXISTS, CASCADE, RESTRICT)
- [ ] Can alter tables (add/drop columns, add constraints, rename)
- [ ] Know when to use TRUNCATE vs DELETE
- [ ] Understand indexes (simple, composite, partial, concurrent creation)
- [ ] Can explain materialized views vs regular views
- [ ] Know how to handle large table migrations safely
- [ ] Understand ON DELETE CASCADE behavior
- [ ] Can identify and fix index bloat
- [ ] Know about sequences and SERIAL/IDENTITY

Good luck! You've got this! 💪
