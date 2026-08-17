# PySpark Advanced - Master Level (2.5 → 5+)

## YOUR CURRENT LEVEL (2.5)
✓ Basic RDD/DataFrame operations
✓ Simple transformations
✓ Can write select, filter, groupBy

**WHAT YOU'LL LEARN (To reach 5+):**
✗ Window functions (critical!)
✗ Optimization techniques
✗ Partitioning strategies
✗ Complex joins
✗ Streaming operations
✗ Performance tuning
✗ Production patterns

---

## SECTION 1: WINDOW FUNCTIONS (GAME CHANGER!)

Window functions = Powerful for row-level operations within groups.

### Basic Window Function

```python
from pyspark.sql import Window
from pyspark.sql.functions import row_number, rank, lag, lead, sum as spark_sum

# Data
data = [
    ("Alice", "IT", 5000),
    ("Bob", "IT", 5500),
    ("Charlie", "HR", 6000),
    ("Diana", "HR", 5800),
]

df = spark.createDataFrame(data, ["name", "dept", "salary"])

# Window: Partition by department, order by salary
window = Window.partitionBy("dept").orderBy("salary")

# Row number within department
result = df.withColumn("row_num", row_number().over(window))
# Alice (IT): 1, Bob (IT): 2, Diana (HR): 1, Charlie (HR): 2

# REAL USE CASE: Find TOP 2 earners per department
top_2 = df.withColumn(
    "rank", rank().over(window.orderBy(col("salary").desc()))
).filter(col("rank") <= 2)
# Returns: Bob, Alice (IT), Charlie, Diana (HR)
```

### Lag & Lead (Previous/Next Row)

```python
# Data: Daily stock prices
stock_data = [
    ("AAPL", "2024-01-01", 100),
    ("AAPL", "2024-01-02", 102),
    ("AAPL", "2024-01-03", 99),
    ("AAPL", "2024-01-04", 105),
]

df = spark.createDataFrame(stock_data, ["ticker", "date", "price"])

window = Window.partitionBy("ticker").orderBy("date")

# Get previous day price
result = df.withColumn("prev_price", lag("price").over(window))

# Get next day price
result = result.withColumn("next_price", lead("price").over(window))

# Calculate day-over-day change
result = result.withColumn(
    "pct_change", 
    ((col("price") - col("prev_price")) / col("prev_price") * 100)
)

# RESULT:
# Date 1: price=100, prev=NULL, pct_change=NULL
# Date 2: price=102, prev=100, pct_change=2.0%
# Date 3: price=99, prev=102, pct_change=-2.94%
# Date 4: price=105, prev=99, pct_change=6.06%

# REAL USE CASE: Identify price jumps
high_jumps = result.filter(col("pct_change") > 5)
# Returns: Date 4 (6.06% jump)
```

### Running Totals

```python
# Data: Monthly sales
sales_data = [
    ("Jan", 1000),
    ("Feb", 1500),
    ("Mar", 800),
    ("Apr", 2000),
]

df = spark.createDataFrame(sales_data, ["month", "amount"])

# Running total
window = Window.orderBy("month") \
    .rangeBetween(Window.unboundedPreceding, Window.currentRow)

df_running = df.withColumn(
    "cumulative_sales",
    spark_sum("amount").over(window)
)

# RESULT:
# Jan: 1000
# Feb: 2500 (1000 + 1500)
# Mar: 3300 (1000 + 1500 + 800)
# Apr: 5300 (1000 + 1500 + 800 + 2000)

# REAL USE CASE: Track quarterly progress
quarterly_progress = df_running.select(
    "month",
    "amount",
    "cumulative_sales",
    (col("cumulative_sales") / 5300).alias("pct_of_annual")
)
```

---

## SECTION 2: OPTIMIZATION TECHNIQUES

### Optimization 1: Broadcast Join

```python
# Problem: Join large table with small reference
large_df = spark.read.parquet("s3://large-data")  # 100GB
small_df = spark.read.parquet("s3://reference")   # 1GB

# SLOW: Shuffle join (default)
result = large_df.join(small_df, "key")
# Takes 10 minutes, moves 100GB across network

# FAST: Broadcast join
from pyspark.sql.functions import broadcast

result = large_df.join(broadcast(small_df), "key")
# Takes 1 minute, sends 1GB to each executor

# When to use:
# - Join table < 2GB
# - Join small reference data to large table
# - Speed up: 5-10x faster
```

### Optimization 2: Caching Strategy

```python
# Analyze with cache
df = spark.read.parquet("s3://data")

# Cache in memory
df.cache()

# First action: loads into cache
count = df.count()  # 1 minute

# Second action: uses cache (fast!)
result = df.filter(col("age") > 25).count()  # 0.1 seconds

# Don't cache if:
# - Only used once (no benefit)
# - Data > available memory (spills to disk)
# - Query job is one-off

# When you're done, remove from cache
df.unpersist()
```

### Optimization 3: Partitioning

```python
# Write with partitions
df.write \
    .partitionBy("year", "month") \
    .parquet("s3://data")

# Structure:
# s3://data/
#   year=2024/
#     month=01/
#       part-00001.parquet
#       part-00002.parquet
#     month=02/
#       part-00001.parquet

# Query only Jan 2024 (fast!)
result = spark.read.parquet("s3://data/year=2024/month=01")
# Reads only 2 files, not entire dataset

# Query all 2024 (fast!)
result = spark.read.parquet("s3://data/year=2024")
# Reads only 2024 files

# GUIDELINES:
# ✓ Partition by: date, region, department (frequently filtered)
# ✗ Don't partition by: customer_id (too many partitions)
```

### Optimization 4: Explain Query Plan

```python
df1 = spark.read.parquet("s3://customers")
df2 = spark.read.parquet("s3://orders")

query = df1.join(df2, "customer_id") \
    .groupBy("customer_id") \
    .agg(sum("amount"))

# See execution plan
query.explain()
# Output shows:
# - Scan operations
# - Filters
# - Joins
# - Aggregations
# - Shuffle operations (expensive!)

# Optimized plan
query.explain(extended=True)
# Shows full optimization steps by Catalyst
```

---

## SECTION 3: COMPLEX JOINS

### Different Join Types

```python
customers = spark.createDataFrame([
    (1, "Alice"), (2, "Bob"), (3, "Charlie")
], ["cust_id", "name"])

orders = spark.createDataFrame([
    (1, 100), (1, 200), (2, 300), (4, 400)
], ["cust_id", "amount"])

# INNER JOIN: Only matching records
result = customers.join(orders, "cust_id", "inner")
# Returns: (1, Alice, 100), (1, Alice, 200), (2, Bob, 300)
# Cust 3 (Charlie) dropped, Order 4 dropped

# LEFT JOIN: All left records
result = customers.join(orders, "cust_id", "left")
# Returns: All customers, orders if exist
# (3, Charlie, NULL) if no order

# FULL OUTER: All records from both
result = customers.join(orders, "cust_id", "full")
# Returns: (3, Charlie, NULL), (4, NULL, 400)

# CROSS JOIN: Cartesian product
result = customers.crossJoin(orders)
# Returns: 3 * 4 = 12 rows (all combinations)
```

### Anti & Semi Joins

```python
# SEMI JOIN: Keep left if exists in right (no duplication)
result = customers.join(orders, "cust_id", "semi")
# Returns: (1, Alice), (2, Bob)
# Only cust with orders, no order details

# Use case: "Which customers have orders?"

# ANTI JOIN: Keep left if NOT in right
result = customers.join(orders, "cust_id", "anti")
# Returns: (3, Charlie)
# Only customers without orders

# Use case: "Which customers have never ordered?"
```

---

## SECTION 4: STREAMING OPERATIONS

```python
# Read from Kafka stream
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "user_events") \
    .load()

# Parse JSON
from pyspark.sql.functions import from_json, col, schema_of_json

schema = "user_id STRING, event_type STRING, timestamp LONG"

events = kafka_df.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

# Transform
events = events.withColumn(
    "date", from_unixtime(col("timestamp"))
)

# Stateful aggregation (track over time)
user_activity = events.groupBy(
    window(col("timestamp"), "5 minutes"),
    col("user_id")
).count()

# Output to console
query = user_activity.writeStream \
    .outputMode("update") \
    .format("console") \
    .start()

# Wait for termination
query.awaitTermination()
```

---

## SECTION 5: DATA QUALITY WITH PYSPARK

```python
class DataQualityValidator:
    def __init__(self, df):
        self.df = df
        self.total_rows = df.count()
    
    # Completeness
    def check_completeness(self):
        from pyspark.sql.functions import isnull
        
        completeness = {}
        for col_name in self.df.columns:
            null_count = self.df.filter(isnull(col(col_name))).count()
            pct = (null_count / self.total_rows) * 100
            completeness[col_name] = 100 - pct
        
        return completeness
    
    # Uniqueness
    def check_uniqueness(self, column):
        duplicates = self.df.groupBy(column) \
            .count() \
            .filter(col("count") > 1) \
            .count()
        
        return {
            "duplicates": duplicates,
            "unique_pct": ((self.total_rows - duplicates) / self.total_rows) * 100
        }
    
    # Validity
    def check_validity_email(self):
        from pyspark.sql.functions import col
        
        valid = self.df.filter(
            col("email").rlike("^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$")
        ).count()
        
        return (valid / self.total_rows) * 100
    
    # Consistency
    def check_consistency(self, other_df, join_key):
        joined = self.df.join(other_df, join_key, "full")
        mismatches = joined.filter(
            col(f"left.status") != col(f"right.status")
        ).count()
        
        return mismatches

# Use it
df = spark.read.parquet("s3://data")
validator = DataQualityValidator(df)

completeness = validator.check_completeness()
duplicates = validator.check_uniqueness("email")
validity = validator.check_validity_email()

print(f"Completeness: {completeness}")
print(f"Email validity: {validity}%")
```

---

## SECTION 6: PRODUCTION PATTERNS

### Error Handling

```python
def robust_spark_job(job_name):
    try:
        logger.info(f"Starting {job_name}")
        
        # Extract
        df = spark.read.parquet("s3://source")
        extract_count = df.count()
        logger.info(f"Extracted {extract_count} rows")
        
        # Validate
        if extract_count == 0:
            raise ValueError("No data extracted!")
        
        # Transform
        df_transformed = transform(df)
        
        # Validate quality
        validator = DataQualityValidator(df_transformed)
        if validator.check_completeness()['customer_id'] < 95:
            raise ValueError("Data quality below threshold!")
        
        # Load
        df_transformed.write \
            .mode("overwrite") \
            .parquet("s3://warehouse")
        
        logger.info(f"Successfully loaded {df_transformed.count()} rows")
        return True
        
    except Exception as e:
        logger.error(f"Job failed: {e}", exc_info=True)
        send_alert(f"Spark job {job_name} failed: {e}")
        return False

# Use it
success = robust_spark_job("daily_etl")
if not success:
    # Retry or alert team
    pass
```

---

## KEY OPTIMIZATIONS SUMMARY

| Technique | Speedup | When to Use |
|-----------|---------|------------|
| Window Functions | 2-5x | Row-level analysis |
| Broadcast Join | 5-10x | Join with small ref |
| Caching | 3-10x | Multiple uses |
| Partitioning | 5-100x | Large datasets |
| Explain Plans | Varies | Debugging slow jobs |

---

## YOUR ACTION PLAN

1. **Understand window functions** (Day 1)
   - Implement row_number, rank, lag, lead
   - Practice with real scenarios

2. **Master joins** (Day 2)
   - Understand all join types
   - Know when to use each

3. **Optimize** (Day 3)
   - Learn broadcast joins
   - Implement caching
   - Use partitioning

4. **Production ready** (Day 4)
   - Error handling
   - Data quality checks
   - Logging and monitoring

---

*Last Updated: 2026-07-29*
*Priority: CRITICAL - You're at 2.5, improve to 4+*
