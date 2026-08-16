# ETL/Data Warehouse - Advanced Practices & Optimization

## TABLE OF CONTENTS
1. [ETL Fundamentals Review](#etl-fundamentals-review)
2. [Advanced ETL Design Patterns](#advanced-etl-design-patterns)
3. [Data Warehouse Architecture](#data-warehouse-architecture)
4. [Performance Optimization](#performance-optimization)
5. [Error Handling & Recovery](#error-handling--recovery)
6. [Real-World Case Studies](#real-world-case-studies)
7. [Best Practices & Anti-Patterns](#best-practices--anti-patterns)
8. [Interview Questions](#interview-questions)

---

## ETL FUNDAMENTALS REVIEW

### ETL Definition
```
EXTRACT: Get data from sources
TRANSFORM: Clean, validate, enrich, aggregate
LOAD: Store in data warehouse

Simple Example:
EXTRACT: Read customer data from 5 CRM systems
TRANSFORM: Standardize phone numbers, deduplicate
LOAD: Store in single customer table
```

### Your Current Level (4/10)
✓ Understand basic ETL flow
✓ Write simple extraction queries
✓ Transform data with SQL
✓ Load to data warehouse

**What's next (Level 5-10):**
✗ Advanced partitioning strategies
✗ Incremental loading optimization
✗ SCD (Slowly Changing Dimensions)
✗ Performance tuning
✗ Error recovery mechanisms
✗ Data lineage tracking
✗ Cost optimization
✗ Schema evolution handling

---

## ADVANCED ETL DESIGN PATTERNS

### Pattern 1: ELT (Extract, Load, Transform)
Modern approach - reverse of traditional ETL.

```
TRADITIONAL ETL:
Extract → Transform → Load
  └─ Transform in memory/staging
  └ Slow for large volumes
  └ Limited resources
  └ Expensive

MODERN ELT:
Extract → Load → Transform
  └─ Load to cloud first
  └─ Transform in warehouse
  └─ Leverage warehouse compute
  └─ Scales infinitely
  └─ Cost-effective
```

**Example: Processing 10GB daily**

```sql
-- TRADITIONAL ETL (Your current approach)
-- Step 1: Extract & staging (5 min)
INSERT INTO staging_customers 
SELECT * FROM crm_system
WHERE modified_date > '2024-01-14';

-- Step 2: Transform (15 min - in application/ETL tool)
-- Complex calculations, deduplication
-- Application memory limited

-- Step 3: Load (5 min)
INSERT INTO fact_customers SELECT * FROM staging;

-- Total: 25 minutes, limited by application memory

-- MODERN ELT (What you should learn)
-- Step 1: Load directly (2 min)
COPY fact_customers_raw
FROM s3://source-data/customers/2024-01-15
WITH PARQUET FORMAT;

-- Step 2: Transform in warehouse (8 min - parallelized!)
INSERT INTO fact_customers
SELECT 
  customer_id,
  UPPER(TRIM(first_name)) AS first_name,
  CASE 
    WHEN phone LIKE '999%' THEN NULL 
    ELSE FORMAT_PHONE(phone)
  END AS phone,
  ROW_NUMBER() OVER (PARTITION BY email ORDER BY created_at DESC) AS rn
FROM fact_customers_raw
WHERE rn = 1;

-- Total: 10 minutes, warehouse handles parallelization
-- 2.5x faster, infinitely scalable
```

### Pattern 2: CDC (Change Data Capture)
Only process changed data, not everything.

```
TRADITIONAL:
Every run → Extract ALL data → Transform ALL → Load ALL
  └─ Inefficient
  └─ Processes unchanged data
  └─ Slow
  └─ Expensive

CDC:
Every run → Extract ONLY CHANGES → Transform → Load
  └─ Efficient
  └─ Process only new/modified data
  └─ Fast
  └─ Cheap
```

**Implementation Example:**

```sql
-- Track changes with timestamp
CREATE TABLE customers (
  customer_id INT,
  name VARCHAR(100),
  email VARCHAR(100),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track what was processed
CREATE TABLE etl_checkpoint (
  table_name VARCHAR(50),
  last_processed_time TIMESTAMP
);

-- CDC Query
DECLARE @last_time TIMESTAMP;
SELECT @last_time = last_processed_time 
FROM etl_checkpoint 
WHERE table_name = 'customers';

-- Only extract changed records
SELECT customer_id, name, email, updated_at
FROM customers
WHERE updated_at > @last_time
ORDER BY updated_at;

-- Update checkpoint
UPDATE etl_checkpoint 
SET last_processed_time = CURRENT_TIMESTAMP
WHERE table_name = 'customers';

-- BENEFIT:
-- Run 1: Extract 1M records (100% new)
-- Run 2: Extract 10K records (1% new) ← 100x faster!
```

### Pattern 3: SCD Type 2 (Slowly Changing Dimensions)
Track history of changing dimensions.

```
PROBLEM:
Customer "John Smith" moves from NY to CA
How to track both addresses in history?

SOLUTION: SCD Type 2

Original approach:
╔══════════════╦═══════════════╗
║ customer_id  ║ address       ║
╠══════════════╬═══════════════╣
║ 1            ║ NY (OLD)      ║  ← Lost history!
║ 1            ║ CA (NEW)      ║
╚══════════════╩═══════════════╝

SCD Type 2 approach:
╔═════════╦═════════════╦════════════╦════════════╗
║ cust_id ║ address     ║ valid_from ║ valid_to   ║
╠═════════╬═════════════╬════════════╬════════════╣
║ 1       ║ NY          ║ 2023-01-01 ║ 2024-01-14 ║
║ 1       ║ CA          ║ 2024-01-15 ║ 9999-12-31 ║
╚═════════╩═════════════╩════════════╩════════════╝

BENEFIT:
✓ Full history preserved
✓ Can answer: "Where did customer live on date X?"
✓ Historical reports accurate
```

**Implementation:**

```python
# Pseudo-code for SCD Type 2 in Spark

from pyspark.sql import functions as F
from pyspark.sql.window import Window

# New data
new_customers = spark.read.csv("new_customers.csv")

# Existing warehouse data
existing = spark.read.parquet("warehouse/customers")

# Find changes
joined = existing.join(new_customers, "customer_id", "outer")

# Identify what changed
changed = joined.filter(
    (F.col("existing.address") != F.col("new.address")) |
    (F.col("existing.status") != F.col("new.status"))
)

# Update SCD Type 2
# 1. Close old record
existing.filter(F.col("customer_id").isin(changed.select("customer_id"))) \
  .withColumn("valid_to", F.current_date()) \
  .write.mode("overwrite").parquet("warehouse/customers")

# 2. Insert new record
changed.select(
    F.col("customer_id"),
    F.col("new.*"),
    F.lit(F.current_date()).alias("valid_from"),
    F.lit("9999-12-31").alias("valid_to")
).write.mode("append").parquet("warehouse/customers")
```

### Pattern 4: Incremental Aggregation
Update aggregate tables efficiently.

```
TRADITIONAL:
Run query on ENTIRE table → Recalculate EVERYTHING
Slow: 1 hour to recalculate daily sales

INCREMENTAL:
Update only TODAY'S data
Fast: 1 minute to add today

Example:
```

```sql
-- TRADITIONAL (Recalculate all)
DELETE FROM fact_daily_sales;
INSERT INTO fact_daily_sales
SELECT 
  sale_date,
  product_id,
  SUM(amount) AS total_sales,
  COUNT(*) AS num_transactions
FROM transactions
GROUP BY sale_date, product_id;
-- Takes 1 hour for 10 years history

-- INCREMENTAL (Update only new)
-- Add yesterday's data
INSERT INTO fact_daily_sales
SELECT 
  sale_date,
  product_id,
  SUM(amount) AS total_sales,
  COUNT(*) AS num_transactions
FROM transactions
WHERE sale_date = CURRENT_DATE - 1
GROUP BY sale_date, product_id;

-- Takes 10 seconds for 1 day
-- 360x faster!
```

### Pattern 5: Star Schema Optimization
Organize warehouse for fast queries.

```
BAD SCHEMA (Normalized - slow for analytics):
Query needs 8 joins
Takes 30 seconds

GOOD SCHEMA (Denormalized - fast for analytics):
Star schema: 1 fact table + dimension tables
Query needs 2 joins
Takes 1 second

Example:

FACT TABLE (Central):
╔════════════╦═════════════╦════════════╦═══════════╗
║ sale_id    ║ customer_fk ║ product_fk ║ amount    ║
╠════════════╬═════════════╬════════════╬═══════════╣
║ 1          ║ 100         ║ 200        ║ 99.99     ║
║ 2          ║ 101         ║ 201        ║ 149.99    ║
╚════════════╩═════════════╩════════════╩═══════════╝

DIMENSION TABLES (Lookup):
CUSTOMERS:
║ customer_id ║ name         ║ city    ║
║ 100         ║ John Smith   ║ NY      ║

PRODUCTS:
║ product_id ║ name        ║ category ║
║ 200        ║ Laptop      ║ Computers║

BENEFIT:
Fast star query:
SELECT c.name, p.name, SUM(f.amount)
FROM fact_sales f
JOIN customer_dim c ON f.customer_fk = c.customer_id
JOIN product_dim p ON f.product_fk = p.product_id
GROUP BY c.name, p.name
```

---

## DATA WAREHOUSE ARCHITECTURE

### Modern Cloud Data Warehouse

```
┌──────────────────────────────────────────────────────┐
│                    DATA SOURCES                      │
│  CRM, ERP, APIs, Databases, Logs, Streaming        │
└──────────────────┬─────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────┐
│               DATA LAKE (Raw Layer)                 │
│  S3/GCS: Store all data "as-is"                    │
│  Cheap storage, format: Parquet/CSV                │
└──────────────────┬─────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────┐
│            STAGING/PROCESSING LAYER                 │
│  Spark: Extraction, validation, transformation      │
│  Output: Cleaned, standardized data                │
└──────────────────┬─────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────┐
│           DATA WAREHOUSE (Warehouse Layer)          │
│  Snowflake/Redshift/BigQuery: Optimized for        │
│  - Fact tables (transactional)                     │
│  - Dimension tables (reference)                    │
│  - Aggregates (pre-calculated)                     │
└──────────────────┬─────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────┐
│            SERVING LAYER (Data Marts)               │
│  Specific use-case tables                          │
│  - Marketing: Campaign, customer segments          │
│  - Finance: Revenue, costs, margins                │
│  - Operations: Inventory, orders                   │
└──────────────────┬─────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────┐
│           CONSUMPTION LAYER                         │
│  Dashboards, Reports, APIs, ML Models              │
│  End-users get insights                            │
└──────────────────────────────────────────────────────┘
```

### Layer Responsibilities

```
DATA LAKE:
- Store everything as-is
- No schema required
- Cost: $0.02/GB/month
- Purpose: Long-term archive

STAGING:
- Validate data
- Remove duplicates
- Standardize formats
- Purpose: Ensure quality

WAREHOUSE:
- Optimized structure
- Fast queries
- Cost: $2/GB/month (more expensive)
- Purpose: Analytics, reports

MARTS:
- Specific business purpose
- Pre-calculated aggregates
- Purpose: Speed up reports
```

---

## PERFORMANCE OPTIMIZATION

### 1. **Partitioning Strategy**
Split data for faster processing.

```sql
-- GOOD: Partition by date (queries always filter by date)
CREATE TABLE sales (
  sale_id INT,
  customer_id INT,
  amount DECIMAL,
  sale_date DATE
)
PARTITION BY RANGE (YEAR(sale_date), MONTH(sale_date))

-- Query only Jan 2024
SELECT * FROM sales 
WHERE sale_date BETWEEN '2024-01-01' AND '2024-01-31'
-- Scans only 1 partition (fast!)

-- BAD: Partition by random column
-- Query has to scan all partitions (slow!)
```

### 2. **Indexing Strategy**
Speed up lookups.

```sql
-- Good indexes
CREATE INDEX idx_customer_id ON sales(customer_id);
CREATE INDEX idx_sale_date ON sales(sale_date);
CREATE COMPOSITE INDEX idx_customer_date ON sales(customer_id, sale_date);

-- Bad indexes
CREATE INDEX idx_amount ON sales(amount); -- Rarely filtered
CREATE INDEX idx_comments ON sales(comments); -- Large text
```

### 3. **Compression**
Reduce storage and I/O.

```
Format      | Compression | Query Speed | When to Use
------------|-------------|-------------|------------------
Parquet     | High (10x)  | Very Fast   | Spark, Analytical
ORC         | Very High   | Fast        | Hive, Hadoop
Columnar    | Medium      | Fast        | Analytics
Row-based   | Low         | Slow        | OLTP, Updates

RECOMMENDATION:
✓ Use Parquet for data lake
✓ Use Columnar for warehouse
✓ Use Row-based for operational data
```

### 4. **Query Optimization**
Write efficient queries.

```sql
-- SLOW QUERY (10 seconds)
SELECT customer.name, 
       customer.email,
       COUNT(order.id) as num_orders,
       SUM(order.amount) as total_spent
FROM customers
JOIN orders ON customers.id = orders.customer_id
WHERE orders.amount > 100  -- Filter AFTER join
GROUP BY customer.id, customer.name, customer.email;

-- FAST QUERY (1 second)
SELECT c.name, 
       c.email,
       COUNT(o.id) as num_orders,
       SUM(o.amount) as total_spent
FROM customers c
JOIN (
  SELECT customer_id, id, amount 
  FROM orders 
  WHERE amount > 100  -- Filter BEFORE join
) o ON c.id = o.customer_id
GROUP BY c.id, c.name, c.email;

-- Why faster?
-- 1. Filter before join = smaller dataset
-- 2. Less rows to process
-- 3. Better query plan
```

---

## ERROR HANDLING & RECOVERY

### Robust ETL Design

```python
# Pseudo-code for production ETL

import logging
from datetime import datetime

class ETLPipeline:
    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger(name)
        self.start_time = datetime.now()
    
    def log_metric(self, metric_name, value):
        self.logger.info(f"{metric_name}: {value}")
    
    def run(self):
        try:
            # Step 1: Extract
            self.logger.info(f"Starting {self.name}")
            data = self.extract()
            self.log_metric("rows_extracted", len(data))
            
            # Step 2: Validate
            validated = self.validate(data)
            validation_rate = len(validated) / len(data) * 100
            self.log_metric("validation_rate", validation_rate)
            
            if validation_rate < 95:
                raise Exception("Validation rate below 95%!")
            
            # Step 3: Transform
            transformed = self.transform(validated)
            
            # Step 4: Load
            self.load(transformed)
            
            # Step 5: Success
            duration = (datetime.now() - self.start_time).total_seconds()
            self.logger.info(f"Success! Duration: {duration}s")
            
            # Send metrics
            send_to_monitoring({
                "status": "success",
                "duration": duration,
                "rows_loaded": len(transformed)
            })
            
        except Exception as e:
            self.logger.error(f"Failed: {e}")
            send_alert(f"ETL failed: {e}")
            self.rollback()
            raise
    
    def extract(self):
        # TODO: Extract logic
        pass
    
    def validate(self, data):
        # Check: completeness, format, duplicates
        return data
    
    def transform(self, data):
        # Clean, enrich, aggregate
        return data
    
    def load(self, data):
        # Insert into warehouse
        pass
    
    def rollback(self):
        # Undo partial changes
        pass

# Usage
pipeline = ETLPipeline("daily_sales_etl")
pipeline.run()
```

### Recovery Strategies

```
SCENARIO 1: Extraction fails
├─ Detect: Extract returns 0 rows
├─ Alert: Send notification
└─ Action: Retry with backoff

SCENARIO 2: Validation fails
├─ Detect: 80% validation rate (below 95%)
├─ Alert: Data quality issue
└─ Action: Stop load, investigate source

SCENARIO 3: Load fails (duplicate key)
├─ Detect: Database constraint violation
├─ Alert: Duplicate data detected
└─ Action: Run deduplication logic

SCENARIO 4: Partial failure (3 hours into 4-hour job)
├─ Detect: Process crash after 3 hours
├─ Alert: Job failed
└─ Action: Checkpoint system allows restart from hour 3
            (not from beginning)
```

---

## REAL-WORLD CASE STUDIES

### Case Study 1: Retail Company ETL

```
COMPANY: Walmart-like online retailer
DATA: Orders from 10,000 stores

CHALLENGE:
- Orders: 100,000/day
- Complex transformations
- Nightly load window: 2 hours only
- 50 downstream reports depend on data

SOLUTION:

1. ARCHITECTURE
   Sources (Order DB) 
   → Kafka (queue)
   → Data Lake (S3)
   → Spark Transformation
   → Snowflake Warehouse
   → BI Reports

2. ETL DESIGN
   - Use ELT (load first, transform in warehouse)
   - Incremental load (CDC)
   - Partition by store_id and date
   
3. OPTIMIZATION
   - SCD Type 2: Track customer moves
   - Pre-aggregate: Daily sales by store
   - Compress: Parquet format
   
4. PERFORMANCE
   Before: 3 hours → Data arrives 6 AM (late!)
   After: 30 min → Data arrives 2:30 AM (on time!)
   Improvement: 6x faster!

5. MONITORING
   - Track load times
   - Alert on > 45 min duration
   - Monitor data quality metrics
   - Track warehouse costs
```

### Case Study 2: Financial Services ETL

```
COMPANY: Investment bank

CHALLENGE:
- Trades: 1 million/day
- Risk calculations: Real-time
- Regulatory: Data must be audited
- Correctness: Critical (costs $$)

SOLUTION:

1. TWO-TIER APPROACH
   TIER 1 (Speed): Spark streaming
   └─ Real-time risk calc
   └─ Latency: < 1 second
   
   TIER 2 (Accuracy): Batch reconciliation
   └─ Nightly verification
   └─ Reconcile Tier 1 with source
   └─ Find/fix discrepancies

2. DATA LINEAGE
   Track every transformation
   "Which calc used which data?"
   Required for audits

3. VALIDATION
   - Trade count matches source
   - Risk numbers within range
   - No orphaned records
   
4. RECOVERY
   - Replayable: Can reprocess from date X
   - Versioning: Track query changes
   - Rollback: Can revert bad data
```

---

## BEST PRACTICES & ANTI-PATTERNS

### Best Practices

```
✓ EXTRACT:
  - Use incremental loads (CDC)
  - Log source data count
  - Handle failures gracefully

✓ TRANSFORM:
  - Transform in warehouse (ELT)
  - Validate at every step
  - Use SCD Type 2 for dimensions

✓ LOAD:
  - Use bulk insert (fast)
  - Partition for parallelism
  - Compress data

✓ MONITOR:
  - Log everything
  - Track metrics
  - Set up alerts

✓ MAINTAIN:
  - Document transformations
  - Test ETL (unit tests)
  - Version control code
```

### Anti-Patterns (What NOT to do)

```
✗ Extract everything, every time
  → Use CDC for incremental loads

✗ Transform in application code
  → Use ELT, transform in warehouse

✗ No validation
  → Validate at every step

✗ No error handling
  → Implement rollback, retry logic

✗ No monitoring
  → Log metrics, set up alerts

✗ Hardcoded values
  → Use configuration files

✗ No documentation
  → Document every transformation

✗ No version control
  → Use Git for all code
```

---

## INTERVIEW QUESTIONS

### Q1: Design ETL for 10GB daily data
**Answer:**
```
ARCHITECTURE:
1. Extract (Kafka): Stream from source
2. Load (S3): Store raw data
3. Transform (Spark): Clean and aggregate
4. Load (Snowflake): Optimized for queries

OPTIMIZATION:
- Use incremental load (CDC)
- Partition by date
- Compress Parquet format
- SCD Type 2 for dimensions

PERFORMANCE:
- Process time: < 1 hour
- Query latency: < 5 seconds
- Cost: Optimized for scale

MONITORING:
- Track row counts
- Alert on quality issues
- Monitor query performance
```

### Q2: Handle slowly changing dimensions
**Answer:**
```
PROBLEM:
Customer "John" moves NY → CA
How to track both addresses?

SOLUTION: SCD Type 2
- Create valid_from, valid_to columns
- Insert new record when data changes
- Query: WHERE CURRENT_DATE BETWEEN valid_from AND valid_to
- History preserved: Can query old address on old date

SQL:
UPDATE dimension 
SET valid_to = CURRENT_DATE
WHERE customer_id = 1 AND valid_to = '9999-12-31';

INSERT INTO dimension 
VALUES (1, 'John', 'CA', CURRENT_DATE, '9999-12-31');
```

### Q3: Optimize slow ETL job
**Answer:**
```
DIAGNOSIS:
1. Find bottleneck: Which step is slow?
   - Extract? Check source system
   - Transform? Profile Spark job
   - Load? Check database write

2. Metrics to check:
   - CPU usage: If high, parallelize
   - I/O wait: If high, optimize queries
   - Memory: If high, reduce batch size

SOLUTIONS:
- Use CDC (less data to process)
- Partition data (parallelize)
- Compress (faster I/O)
- Batch optimize (rewrite queries)
- Use cache (avoid redundant processing)

RESULT:
Before: 3 hours
After: 1 hour (3x faster)
```

---

## KEY TAKEAWAYS

1. **ELT > ETL**: Load first, transform in warehouse
2. **Use CDC**: Only process changed data
3. **SCD Type 2**: Track dimension history
4. **Partition & Compress**: Speed and cost
5. **Monitor Everything**: Metrics, alerts, logging
6. **Test & Document**: Version control, unit tests
7. **Handle Errors**: Rollback, retry, recovery

---

*Last Updated: 2026-07-29*
*Difficulty Level: Intermediate to Advanced*
*Prerequisites: ETL basics, SQL, Python*
