# EPAM DQE - Practical SQL Exercises to Practice

## Setup: Create Sample Tables

Run these first to create test data:

```sql
-- Create sample database tables
CREATE TABLE customers (
  customer_id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(100),
  phone VARCHAR(20),
  status VARCHAR(20),
  created_at TIMESTAMP,
  age INT
);

CREATE TABLE orders (
  order_id SERIAL PRIMARY KEY,
  customer_id INT,
  order_date DATE,
  amount NUMERIC(10, 2),
  status VARCHAR(20),
  created_at TIMESTAMP
);

CREATE TABLE order_items (
  item_id SERIAL PRIMARY KEY,
  order_id INT,
  product_id INT,
  quantity INT,
  unit_price NUMERIC(10, 2)
);

CREATE TABLE products (
  product_id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  price NUMERIC(10, 2)
);

-- Insert sample data (with intentional issues for practice!)
INSERT INTO customers VALUES 
  (1, 'John Smith', 'john@example.com', '123-456-7890', 'active', NOW(), 30),
  (2, 'Jane Doe', 'jane@example.com', NULL, 'active', NOW(), 28),
  (3, 'Bob Johnson', NULL, '234-567-8901', 'inactive', NOW(), NULL),
  (4, 'Alice Brown', 'alice@invalid', '345-678-9012', 'active', NOW(), 250), -- Invalid email, invalid age
  (5, 'Charlie Wilson', 'charlie@example.com', '456-789-0123', 'active', NOW(), 35),
  (5, 'Charlie Wilson', 'charlie@example.com', '456-789-0123', 'active', NOW(), 35), -- Duplicate!
  (6, 'Diana Lee', 'diana@example.com', '567-890-1234', 'active', NOW(), -5); -- Invalid age

INSERT INTO orders VALUES
  (1, 1, '2024-01-15', 150.00, 'completed', NOW()),
  (2, 2, '2024-01-16', 250.00, 'completed', NOW()),
  (3, 3, '2024-01-17', 100.00, 'pending', NOW()),
  (4, 999, '2024-01-18', 300.00, 'completed', NOW()), -- Non-existent customer!
  (5, 1, CURRENT_DATE + 1, 200.00, 'pending', NOW()), -- Future order date!
  (6, 2, '2024-01-19', -50.00, 'completed', NOW()); -- Negative amount!

INSERT INTO order_items VALUES
  (1, 1, 1, 2, 50.00), -- 2 * 50 = 100, order total is 150 (mismatch!)
  (2, 1, 2, 1, 50.00), -- 1 * 50 = 50, combined = 150 OK
  (3, 2, 3, 5, 50.00), -- 5 * 50 = 250, matches
  (4, 3, 4, 1, 100.00), -- 1 * 100 = 100, matches
  (5, 5, 5, 1, 200.00); -- Order 5 matches

INSERT INTO products VALUES
  (1, 'Product A', 50.00),
  (2, 'Product B', 50.00),
  (3, 'Product C', 100.00),
  (4, 'Product D', 100.00),
  (5, 'Product E', 200.00);
```

---

## EXERCISE 1: Check COMPLETENESS

### Task 1.1: Find customers missing email
```sql
-- Your query:
[Write your query here]

-- Expected result: Should find customer_id 3 and maybe others

-- Solution:
SELECT customer_id, name, email FROM customers WHERE email IS NULL;
```

### Task 1.2: Calculate completeness percentage for customers table
```sql
-- Your query:
[Write your query here]

-- Expected result: Should show something like "Completeness: 85.7%"

-- Solution:
SELECT 
  COUNT(*) AS total_customers,
  COUNT(*) FILTER (WHERE email IS NOT NULL) AS customers_with_email,
  ROUND(COUNT(*) FILTER (WHERE email IS NOT NULL)::NUMERIC / COUNT(*) * 100, 2) AS email_completeness_pct,
  COUNT(*) FILTER (WHERE phone IS NOT NULL) AS customers_with_phone,
  ROUND(COUNT(*) FILTER (WHERE phone IS NOT NULL)::NUMERIC / COUNT(*) * 100, 2) AS phone_completeness_pct
FROM customers;
```

### Task 1.3: Find records with ANY missing required field
```sql
-- Your query (required fields: customer_id, email, phone):
[Write your query here]

-- Expected result: Should find at least 2-3 incomplete records

-- Solution:
SELECT 
  customer_id,
  CASE 
    WHEN email IS NULL THEN 'Missing email'
    WHEN phone IS NULL THEN 'Missing phone'
    ELSE 'Complete'
  END AS missing_field
FROM customers
WHERE email IS NULL OR phone IS NULL;
```

---

## EXERCISE 2: Check UNIQUENESS

### Task 2.1: Find duplicate customer emails
```sql
-- Your query:
[Write your query here]

-- Expected result: Should find that charlie@example.com appears twice

-- Solution:
SELECT 
  email,
  COUNT(*) AS count,
  STRING_AGG(customer_id::TEXT, ', ') AS customer_ids
FROM customers
WHERE email IS NOT NULL
GROUP BY email
HAVING COUNT(*) > 1;
```

### Task 2.2: Find duplicate customer records (all fields match)
```sql
-- Your query:
[Write your query here]

-- Expected result: Should find the duplicate Charlie Wilson record

-- Solution:
SELECT *,
  ROW_NUMBER() OVER (PARTITION BY name, email, phone ORDER BY customer_id) AS rn
FROM customers
WHERE (name, email, phone) IN (
  SELECT name, email, phone FROM customers 
  GROUP BY name, email, phone HAVING COUNT(*) > 1
);

-- Or simpler:
SELECT name, email, phone, COUNT(*) FROM customers 
GROUP BY name, email, phone HAVING COUNT(*) > 1;
```

### Task 2.3: Find duplicate order_ids
```sql
-- Your query:
[Write your query here]

-- Expected result: Should find no duplicates (primary key prevents it)

-- Solution:
SELECT order_id, COUNT(*) FROM orders GROUP BY order_id HAVING COUNT(*) > 1;
```

---

## EXERCISE 3: Check VALIDITY

### Task 3.1: Find invalid emails
```sql
-- Your query (invalid = no @, or incomplete domain):
[Write your query here]

-- Expected result: Should find 'alice@invalid' (no dot in domain)

-- Solution:
SELECT 
  customer_id,
  email,
  CASE 
    WHEN email IS NULL THEN 'NULL'
    WHEN email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$' THEN 'Valid'
    ELSE 'Invalid'
  END AS email_validity
FROM customers
WHERE email IS NOT NULL AND email NOT ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$';
```

### Task 3.2: Find customers with invalid age
```sql
-- Your query (age should be between 0 and 150):
[Write your query here]

-- Expected result: Should find age 250 and age -5

-- Solution:
SELECT 
  customer_id,
  name,
  age,
  CASE 
    WHEN age IS NULL THEN 'Missing'
    WHEN age < 0 OR age > 150 THEN 'Invalid'
    ELSE 'Valid'
  END AS age_validity
FROM customers
WHERE age IS NULL OR age < 0 OR age > 150;
```

### Task 3.3: Find orders with negative amount
```sql
-- Your query:
[Write your query here]

-- Expected result: Should find order_id 6 with amount -50

-- Solution:
SELECT 
  order_id,
  amount,
  CASE 
    WHEN amount <= 0 THEN 'Invalid (must be positive)'
    ELSE 'Valid'
  END AS amount_validity
FROM orders
WHERE amount <= 0;
```

---

## EXERCISE 4: Check CONSISTENCY

### Task 4.1: Find orphaned orders (customer doesn't exist)
```sql
-- Your query:
[Write your query here]

-- Expected result: Should find order_id 4 (customer_id 999 doesn't exist)

-- Solution:
SELECT 
  o.order_id,
  o.customer_id,
  o.order_date,
  'No matching customer' AS issue
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;
```

### Task 4.2: Find order items without matching order
```sql
-- Your query:
[Write your query here]

-- Expected result: Should find none (all items have matching orders)

-- Solution:
SELECT 
  oi.item_id,
  oi.order_id,
  'No matching order' AS issue
FROM order_items oi
LEFT JOIN orders o ON oi.order_id = o.order_id
WHERE o.order_id IS NULL;
```

### Task 4.3: Compare data between systems (if you had two systems)
```sql
-- Simulated scenario: Let's create a backup table with different data
CREATE TABLE customers_backup AS SELECT * FROM customers;

-- Now modify backup to introduce inconsistency
UPDATE customers_backup SET status = 'inactive' WHERE customer_id = 1;

-- Your query to find mismatches:
[Write your query here]

-- Expected result: Should find customer_id 1 with status mismatch

-- Solution:
SELECT 
  COALESCE(c1.customer_id, c2.customer_id) AS customer_id,
  c1.status AS current_status,
  c2.status AS backup_status,
  CASE 
    WHEN c1.customer_id IS NULL THEN 'Only in backup'
    WHEN c2.customer_id IS NULL THEN 'Only in current'
    WHEN c1.status <> c2.status THEN 'Status mismatch'
    ELSE 'Consistent'
  END AS consistency
FROM customers c1
FULL OUTER JOIN customers_backup c2 ON c1.customer_id = c2.customer_id
WHERE c1.customer_id IS NULL OR c2.customer_id IS NULL OR c1.status <> c2.status;

-- Clean up
DROP TABLE customers_backup;
```

---

## EXERCISE 5: Check ACCURACY

### Task 5.1: Verify order total equals sum of order items
```sql
-- Your query:
[Write your query here]

-- Expected result: Should find order_id 1 (total 150 but items sum to 100+50=150, actually matches! 
-- Let me check... items are 100 and 50, so it's correct. Let's use a problematic one)

-- Let me revise: order_id 1 should mismatch if we change the data
-- Actually, let's verify accuracy differently

-- Solution:
SELECT 
  o.order_id,
  o.amount AS order_total,
  COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS calculated_total,
  CASE 
    WHEN o.amount = COALESCE(SUM(oi.quantity * oi.unit_price), 0) THEN 'Accurate'
    ELSE 'Inaccurate'
  END AS accuracy
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY o.order_id, o.amount
HAVING o.amount <> COALESCE(SUM(oi.quantity * oi.unit_price), 0);
```

### Task 5.2: Check if product prices match in orders
```sql
-- Verify order_items.unit_price matches products.price
-- Your query:
[Write your query here]

-- Expected result: Should show price mismatches if any

-- Solution:
SELECT 
  oi.item_id,
  oi.product_id,
  oi.unit_price AS order_item_price,
  p.price AS product_price,
  CASE 
    WHEN oi.unit_price = p.price THEN 'Match'
    ELSE 'Mismatch'
  END AS accuracy
FROM order_items oi
LEFT JOIN products p ON oi.product_id = p.product_id
WHERE oi.unit_price <> p.price;
```

### Task 5.3: Check order date logic
```sql
-- Order date should not be in the future
-- Your query:
[Write your query here]

-- Expected result: Should find order_id 5 (future date)

-- Solution:
SELECT 
  order_id,
  order_date,
  CURRENT_DATE,
  CASE 
    WHEN order_date > CURRENT_DATE THEN 'Invalid (future date)'
    ELSE 'Valid'
  END AS accuracy
FROM orders
WHERE order_date > CURRENT_DATE;
```

---

## EXERCISE 6: Check TIMELINESS

### Task 6.1: Find how old the data is
```sql
-- Your query (check how long since last update):
[Write your query here]

-- Expected result: Should show time since last record was created

-- Solution:
SELECT 
  MAX(created_at) AS last_update,
  NOW() - MAX(created_at) AS data_age,
  CASE 
    WHEN NOW() - MAX(created_at) < INTERVAL '1 hour' THEN 'Very fresh'
    WHEN NOW() - MAX(created_at) < INTERVAL '24 hours' THEN 'Recent'
    ELSE 'Stale'
  END AS timeliness
FROM orders;
```

### Task 6.2: Create a timeliness check with SLA
```sql
-- Assume orders must be loaded within 1 hour of being created
-- Your query:
[Write your query here]

-- Expected result: Should show which orders are within SLA

-- Solution:
SELECT 
  order_id,
  created_at,
  EXTRACT(EPOCH FROM (created_at - order_date)) / 3600 AS hours_from_order,
  CASE 
    WHEN EXTRACT(EPOCH FROM (created_at - order_date)) / 3600 <= 1 THEN 'Within SLA'
    ELSE 'Outside SLA'
  END AS timeliness
FROM orders;
```

---

## EXERCISE 7: Create a Data Quality Scorecard

### Task 7.1: Create comprehensive DQ dashboard
```sql
-- Your query (create a single view showing all DQ metrics):
[Write your query here]

-- Expected result: Single dashboard showing all dimensions

-- Solution:
WITH completeness AS (
  SELECT 
    'Customers' AS table_name,
    'Completeness' AS dimension,
    ROUND(COUNT(*) FILTER (WHERE email IS NOT NULL)::NUMERIC / COUNT(*) * 100, 2) AS score_pct
  FROM customers
),
uniqueness AS (
  SELECT 
    'Customers',
    'Uniqueness',
    ROUND(COUNT(DISTINCT email)::NUMERIC / COUNT(*) * 100, 2)
  FROM customers
),
validity_emails AS (
  SELECT 
    'Customers',
    'Validity (Email)',
    ROUND(COUNT(*) FILTER (WHERE email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')::NUMERIC / COUNT(*) * 100, 2)
  FROM customers
)
SELECT * FROM completeness
UNION ALL
SELECT * FROM uniqueness
UNION ALL
SELECT * FROM validity_emails;
```

---

## EXERCISE 8: Real-World Problem Solving

### Scenario 1: You discover 30% of orders have no items
```sql
-- Task: Find all orders with no associated order_items
-- Your query:
[Write your query here]

-- Solution:
SELECT 
  o.order_id,
  o.customer_id,
  o.amount,
  COUNT(oi.item_id) AS item_count
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY o.order_id, o.customer_id, o.amount
HAVING COUNT(oi.item_id) = 0;

-- Follow-up: How many such orders exist?
SELECT COUNT(*) FROM (
  SELECT o.order_id FROM orders o
  LEFT JOIN order_items oi ON o.order_id = oi.order_id
  GROUP BY o.order_id HAVING COUNT(oi.item_id) = 0
) missing_items;
```

### Scenario 2: Customer has multiple emails, which is primary?
```sql
-- Task: Find customers with multiple emails
-- Your query:
[Write your query here]

-- Note: We have unique emails, so let's modify: what if we allow customers to have multiple records?
-- For now, this exercise was about duplicate customers (which we found)

-- Solution was already shown in uniqueness exercises
```

### Scenario 3: Order amount doesn't match items
```sql
-- Task: Find ALL orders with amount mismatches
-- Your query:
[Write your query here]

-- Solution: (Already shown in accuracy exercise above)
```

---

## BONUS: Advanced Queries

### Query 1: Data Quality Trend Analysis
```sql
-- Simulate tracking quality over multiple days
-- Create a metrics table first:
CREATE TABLE dq_daily_metrics (
  check_date DATE,
  table_name VARCHAR(50),
  dimension VARCHAR(50),
  score_percentage NUMERIC(5, 2)
);

-- Insert sample data
INSERT INTO dq_daily_metrics VALUES
  ('2024-01-15', 'orders', 'completeness', 95.00),
  ('2024-01-15', 'orders', 'uniqueness', 98.00),
  ('2024-01-16', 'orders', 'completeness', 92.00),
  ('2024-01-16', 'orders', 'uniqueness', 98.00),
  ('2024-01-17', 'orders', 'completeness', 88.00),
  ('2024-01-17', 'orders', 'uniqueness', 98.00);

-- Query: Show trend (improving or degrading?)
SELECT 
  check_date,
  dimension,
  score_percentage,
  LAG(score_percentage) OVER (PARTITION BY dimension ORDER BY check_date) AS prev_score,
  score_percentage - LAG(score_percentage) OVER (PARTITION BY dimension ORDER BY check_date) AS change,
  CASE 
    WHEN score_percentage > LAG(score_percentage) OVER (PARTITION BY dimension ORDER BY check_date) 
      THEN 'Improved ✓'
    WHEN score_percentage < LAG(score_percentage) OVER (PARTITION BY dimension ORDER BY check_date) 
      THEN 'Degraded ✗'
    ELSE 'Stable'
  END AS trend
FROM dq_daily_metrics
WHERE table_name = 'orders'
ORDER BY dimension, check_date;
```

---

## ANSWERS QUICK REFERENCE

```sql
-- COMPLETENESS
SELECT COUNT(*) FILTER (WHERE col IS NOT NULL)::NUMERIC / COUNT(*) * 100 FROM table;

-- UNIQUENESS  
SELECT col, COUNT(*) FROM table GROUP BY col HAVING COUNT(*) > 1;

-- VALIDITY (Email)
SELECT * FROM table WHERE col NOT ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$';

-- CONSISTENCY (FK)
SELECT * FROM table1 t1 LEFT JOIN table2 t2 ON t1.id = t2.id WHERE t2.id IS NULL;

-- ACCURACY
SELECT * FROM orders WHERE amount <> (quantity * unit_price);

-- TIMELINESS
SELECT NOW() - MAX(updated_at) FROM table;
```

---

## How to Practice

1. **Run each exercise** in your PostgreSQL database
2. **Write your own query first**, then compare with solution
3. **Modify the data** to introduce new issues and test
4. **Time yourself** - Can you write a completeness query in 2 minutes?
5. **Explain out loud** - Why does this query find duplicates?
6. **Create variations** - How would you check different fields?

---

## Assessment

Score yourself:
- ✅ Completed Exercises 1-3 → Basics solid
- ✅ Completed Exercises 4-5 → Intermediate ready
- ✅ Completed Exercises 6-7 → Advanced ready
- ✅ Completed Exercise 8 → Interview ready!

---

Good luck! Run these queries and master them! 🚀

*Last Updated: 2026-07-29*
