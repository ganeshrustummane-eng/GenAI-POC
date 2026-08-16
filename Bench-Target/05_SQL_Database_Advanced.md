# SQL & Database Advanced - Performance Mastery

## ADVANCED QUERY OPTIMIZATION

### 1. Execution Plans (Critical Skill!)

```sql
-- See how SQL executes
EXPLAIN ANALYZE
SELECT c.name, COUNT(o.id) as order_count
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
WHERE c.country = 'USA'
GROUP BY c.id, c.name
HAVING COUNT(o.id) > 5
ORDER BY order_count DESC;

-- Output shows:
-- Sort (by order_count)
--   ├─ Hash Aggregate (GROUP BY)
--   │   └─ Hash Join (LEFT JOIN)
--   │       ├─ Seq Scan on customers (filter: country = 'USA')
--   │       └─ Seq Scan on orders

-- Interpretation:
-- Sequential scans = slow (reads all rows)
-- Hash join = OK (good for medium data)
-- Hash aggregate = OK (acceptable)

-- OPTIMIZATION:
CREATE INDEX idx_country ON customers(country);
CREATE INDEX idx_customer_orders ON orders(customer_id);

-- Now same query:
-- Index Scan (fast!) on customers using idx_country
-- Index Scan (fast!) on orders using idx_customer_orders
-- Result: 10x faster!
```

### 2. Index Strategy

```sql
-- Single column index (basic)
CREATE INDEX idx_email ON users(email);

-- Composite index (for specific queries)
CREATE INDEX idx_user_order ON orders(customer_id, order_date);
-- Good for: WHERE customer_id = ? AND order_date > ?

-- Partial index (only important rows)
CREATE INDEX idx_active_users ON users(id) WHERE status = 'active';
-- Good for: Large table, query filters on status

-- Full-text index (text search)
CREATE INDEX idx_title_fulltext ON products USING gin(to_tsvector('english', title));

-- GUIDELINES:
-- ✓ Index on: Frequently filtered columns
-- ✓ Index on: JOIN columns
-- ✓ Index on: ORDER BY columns
-- ✗ Don't index: Rarely filtered columns
-- ✗ Don't index: Low cardinality (boolean, status)
-- ✗ Don't index: TEXT fields without full-text
```

### 3. Query Patterns (Performance Tips)

```sql
-- SLOW: Subquery with WHERE IN (predicate push-down issue)
SELECT name FROM customers
WHERE id IN (SELECT customer_id FROM orders WHERE amount > 100);
-- Executes: Find all orders > 100, then check each customer

-- FAST: Use JOIN (Catalyst optimizes)
SELECT DISTINCT c.name FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE o.amount > 100;
-- Executes: Filter orders first, then join

-- SLOW: Use function in WHERE (prevents index use)
SELECT * FROM orders
WHERE YEAR(order_date) = 2024;
-- Cannot use index on order_date!

-- FAST: Use column range
SELECT * FROM orders
WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01';
-- Uses index on order_date!

-- SLOW: CASE without optimization
SELECT 
  CASE WHEN amount > 1000 THEN 'High'
       WHEN amount > 100 THEN 'Medium'
       ELSE 'Low' END as tier
FROM orders;

-- FAST: Pre-computed (if needed repeatedly)
CREATE TABLE order_tiers AS
SELECT id, 
  CASE WHEN amount > 1000 THEN 'High'
       WHEN amount > 100 THEN 'Medium'
       ELSE 'Low' END as tier
FROM orders;
```

### 4. Window Functions for Analytics

```sql
-- Ranking
SELECT 
  customer_id,
  order_id,
  amount,
  RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) as rank,
  DENSE_RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) as dense_rank,
  ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY amount DESC) as row_num
FROM orders;

-- Running totals
SELECT
  date,
  sales,
  SUM(sales) OVER (ORDER BY date) as cumulative_sales,
  AVG(sales) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as avg_7day
FROM daily_sales
ORDER BY date;

-- Top N per group
SELECT customer_id, order_id, amount
FROM (
  SELECT 
    *,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY amount DESC) as rn
  FROM orders
) ranked
WHERE rn <= 3;  -- Top 3 orders per customer

-- Identify trends
SELECT
  date,
  value,
  LAG(value) OVER (ORDER BY date) as prev_value,
  LEAD(value) OVER (ORDER BY date) as next_value,
  (value - LAG(value) OVER (ORDER BY date)) / LAG(value) OVER (ORDER BY date) as pct_change
FROM metrics
ORDER BY date;
```

---

## TRANSACTION MANAGEMENT

### ACID Properties

```sql
-- ATOMICITY: All or nothing
BEGIN TRANSACTION;
  UPDATE accounts SET balance = balance - 100 WHERE id = 1;
  UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;
-- Both succeed or both fail (no partial update)

-- CONSISTENCY: Valid state to valid state
-- Database rules enforced (foreign keys, constraints)

-- ISOLATION: Concurrent transactions don't interfere
-- Levels: READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE

-- DURABILITY: Committed data survives failures
-- Stored on disk, not lost on crash
```

### Transaction Levels

```sql
-- READ COMMITTED (most common, good balance)
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
SELECT * FROM accounts WHERE balance > 0;

-- Issue: Dirty read (read uncommitted data)
-- Fix: Wait for commit
-- Impact: Slightly slower

-- REPEATABLE READ (better isolation)
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SELECT * FROM accounts;  -- Read 1
SELECT * FROM accounts;  -- Read 2 (same result)

-- SERIALIZABLE (maximum isolation, slowest)
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
-- Transactions execute one at a time (slowest but safest)

-- Choose based on needs:
-- ✓ READ COMMITTED: Most applications
-- ✓ REPEATABLE READ: Financial systems
-- ✓ SERIALIZABLE: Critical operations
```

---

## PARTITIONING STRATEGIES

### Table Partitioning

```sql
-- RANGE partitioning (by date)
CREATE TABLE sales (
  id INT,
  amount DECIMAL,
  sale_date DATE
)
PARTITION BY RANGE (YEAR(sale_date), MONTH(sale_date)) (
  PARTITION p201401 VALUES LESS THAN (2014, 2),
  PARTITION p201402 VALUES LESS THAN (2014, 3),
  -- ... more partitions
  PARTITION pmax VALUES LESS THAN MAXVALUE
);

-- Query only recent data (fast!)
SELECT * FROM sales PARTITION (p202401) WHERE amount > 100;

-- LIST partitioning (by category)
CREATE TABLE sales (
  id INT,
  region VARCHAR(50)
)
PARTITION BY LIST (region) (
  PARTITION p_east VALUES IN ('NY', 'PA', 'NJ'),
  PARTITION p_west VALUES IN ('CA', 'WA', 'OR'),
  PARTITION p_south VALUES IN ('TX', 'FL', 'GA')
);

-- HASH partitioning (evenly distribute)
CREATE TABLE customers (
  id INT,
  name VARCHAR(100)
)
PARTITION BY HASH (id) PARTITIONS 10;
-- Automatically distributes across 10 partitions
```

---

## MATERIALIZED VIEWS

### Pre-calculated Results

```sql
-- Create materialized view (stores data!)
CREATE MATERIALIZED VIEW sales_summary AS
SELECT 
  DATE(sale_date) as date,
  category,
  SUM(amount) as total_sales,
  COUNT(*) as num_transactions,
  AVG(amount) as avg_sale
FROM sales
GROUP BY DATE(sale_date), category;

-- Query is instant (uses stored data)
SELECT * FROM sales_summary WHERE date = CURRENT_DATE;

-- Refresh when data updates
REFRESH MATERIALIZED VIEW sales_summary;

-- Concurrent refresh (doesn't lock)
REFRESH MATERIALIZED VIEW CONCURRENTLY sales_summary;

-- WHEN TO USE:
-- ✓ Slow complex queries
-- ✓ Frequently accessed aggregates
-- ✗ Real-time data needed
-- ✗ Small queries
```

---

## MONITORING & TUNING

### Query Performance Metrics

```sql
-- Find slow queries
SELECT 
  query,
  calls,
  mean_exec_time,
  total_exec_time,
  max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Table statistics
SELECT 
  schemaname,
  tablename,
  seq_scan,
  seq_tup_read,
  idx_scan,
  idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan  -- More seq scans than index scans = problem!
ORDER BY seq_scan DESC;

-- Index usage
SELECT 
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0  -- Unused indexes
ORDER BY pg_relation_size(indexrelid) DESC;

-- Drop unused indexes (save space)
DROP INDEX idx_unused;
```

---

## REAL-WORLD SCENARIOS

### Scenario: E-commerce Database

```sql
-- Problem: Customer dashboard slow (10 seconds)
-- Shows: Customer info, recent orders, total spent

-- Original (SLOW):
SELECT 
  c.id, c.name, c.email,
  COUNT(o.id) as total_orders,
  SUM(o.amount) as total_spent,
  MAX(o.order_date) as last_order
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
LEFT JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN products p ON oi.product_id = p.id
WHERE c.id = ?
GROUP BY c.id, c.name, c.email;
-- Multiple joins, no indexes

-- Solution:
-- 1. Add indexes
CREATE INDEX idx_customer_orders ON orders(customer_id, order_date);
CREATE INDEX idx_order_items ON order_items(order_id);

-- 2. Simplify query
SELECT 
  c.id, c.name, c.email,
  agg.total_orders,
  agg.total_spent,
  agg.last_order
FROM customers c
LEFT JOIN (
  SELECT 
    customer_id,
    COUNT(*) as total_orders,
    SUM(amount) as total_spent,
    MAX(order_date) as last_order
  FROM orders
  GROUP BY customer_id
) agg ON c.id = agg.customer_id
WHERE c.id = ?;
-- Simpler, indexed, pre-aggregated

-- 3. Materialized view (if used frequently)
CREATE MATERIALIZED VIEW customer_summary AS
SELECT 
  customer_id,
  COUNT(*) as total_orders,
  SUM(amount) as total_spent,
  MAX(order_date) as last_order
FROM orders
GROUP BY customer_id;

-- Result: 10 seconds → 100ms (100x faster!)
```

---

## INTERVIEW QUESTIONS

### Q1: Optimize slow query

**Answer:**
```
Steps:
1. EXPLAIN ANALYZE - Find bottleneck
2. Check indexes - Are indexes used?
3. Check statistics - Run ANALYZE
4. Rewrite query - Simplify joins, use subqueries
5. Measure - Verify improvement

Key techniques:
- Add indexes on filtered/joined columns
- Use partial indexes for filtered queries
- Pre-compute with materialized views
- Rewrite to avoid function calls in WHERE
- Use EXPLAIN to verify index usage
```

### Q2: Design indexing for large table

**Answer:**
```
Step 1: Identify query patterns
- What columns are filtered?
- What columns are joined?
- What columns are ordered?

Step 2: Create indexes
- Single-column index on each filtered column
- Composite index for frequent combinations
- Partial index for filtered subset

Step 3: Monitor
- Check pg_stat_statements for slow queries
- Check pg_stat_user_indexes for unused indexes
- Drop unused, add missing

Example:
SELECT * FROM orders 
WHERE customer_id = ? AND order_date > ? 
ORDER BY amount DESC;

Index: CREATE INDEX idx_cust_date_amt 
       ON orders(customer_id, order_date, amount);
```

### Q3: Handle large table growth

**Answer:**
```
Solutions:
1. Partitioning: Split by date/region
2. Archiving: Move old data out
3. Compression: Reduce storage
4. Optimization: Better indexes
5. Sharding: Distribute across servers

Example:
- Table: 1TB, slowest queries
- Solution: Partition by year
  - 2024: Full, active queries
  - 2023: Archive, rare queries
  - Result: Queries only 1/5 size
```

---

## KEY TAKEAWAYS

1. **EXPLAIN ANALYZE** - Always check execution plan
2. **Indexing Strategy** - Index right columns
3. **Query Rewriting** - JOIN > IN, column range > YEAR()
4. **Window Functions** - Powerful for analytics
5. **Partitioning** - Split large tables
6. **Materialized Views** - Pre-compute aggregates
7. **Monitor** - Track slow queries, unused indexes
8. **Test Changes** - Verify improvements

---

*Last Updated: 2026-07-29*
*Level: Advanced (4 → 5)*
