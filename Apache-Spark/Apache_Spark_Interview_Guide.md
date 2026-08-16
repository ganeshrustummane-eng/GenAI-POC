# Apache Spark - Interview Questions & Quick Reference

## QUICK REFERENCE

### Most Important Concepts

```
WHAT IS SPARK?
- Fast, distributed computing framework
- Processes large data in parallel across multiple machines
- 100x faster than Hadoop (in-memory)

WHY SPARK FOR DATA QUALITY?
- Process 1TB data in minutes, not hours
- Parallel DQ checks on 100s of machines
- Simple Python/SQL syntax
- Easy data validation at scale
```

### Core Components Table

| Component | Purpose | Role |
|-----------|---------|------|
| **Driver** | Main program | Coordinates execution |
| **Executor** | Worker process | Executes tasks |
| **Task** | Unit of work | Runs in executor |
| **RDD** | Low-level API | Unstructured data |
| **DataFrame** | High-level API | Structured data (RECOMMENDED) |
| **Catalyst** | Query optimizer | Auto-tunes queries |

### 6 Essential Spark Patterns

```python
# 1. MAP - Transform each element
rdd.map(lambda x: x * 2)
df.select((col("salary") * 1.1).alias("increased"))

# 2. FILTER - Keep matching
rdd.filter(lambda x: x > 25)
df.filter(df.age > 25)

# 3. FLATMAP - Map then flatten
rdd.flatMap(lambda x: x.split())

# 4. REDUCEBYKEY - Group and combine
rdd.reduceByKey(lambda x, y: x + y)

# 5. GROUPBY - Group by key
df.groupBy("department").count()

# 6. JOIN - Combine DataFrames
df1.join(df2, "key")
```

### Transformation vs Action (CRITICAL!)

| Transformation (Lazy) | Action (Eager) |
|-----|-----|
| `map` | `collect` |
| `filter` | `show` |
| `select` | `count` |
| `groupBy` | `first` |
| `join` | `take` |
| `flatMap` | `saveAsTextFile` |
| NOT executed immediately | EXECUTES immediately |

---

## INTERVIEW QUESTIONS

### TIER 1: Basic (MUST ANSWER)

#### Q1.1: What is Apache Spark?
**Answer:**
```
Apache Spark is a fast, distributed computing framework 
for processing large amounts of data.

Key points:
1. FAST: 100x faster than Hadoop (in-memory processing)
2. DISTRIBUTED: Runs on cluster of machines in parallel
3. GENERAL: SQL, ML, Streaming, batch processing
4. EASY: Python, Scala, Java, SQL APIs

Real example:
- Process 1TB data on 1 machine: 10 hours
- Process 1TB data on Spark (100 machines): 10 minutes

Why better than Hadoop:
- Hadoop stores to disk (slow)
- Spark uses memory (fast)
- Hadoop only for batch
- Spark for batch + streaming + ML
```

---

#### Q1.2: What's the difference between RDD and DataFrame?
**Answer:**
```
RDD (Resilient Distributed Dataset):
- Low-level API
- Unstructured data (can be anything)
- Manual optimization needed
- Slower (no built-in optimizations)

DataFrame:
- High-level API (structured, like SQL table)
- Named columns with data types
- Auto-optimized by Catalyst
- Faster (recommended for 99% of cases)

When to use:
- RDD: Complex unstructured transformations
- DataFrame: Most real-world work (use this!)

Example:
RDD: sc.parallelize([1,2,3]).map(x => x*2)
DF: spark.createDataFrame([(1,), (2,), (3,)], ["val"]) \
         .select(col("val")*2)
```

---

#### Q1.3: Explain lazy evaluation in Spark
**Answer:**
```
Spark doesn't execute transformations immediately.
Only executes when an action is called.

Example:
df.filter(df.age > 25)      # NOT executed (lazy)
  .select("name")           # NOT executed (lazy)
  .show()                   # EXECUTED (action)

Why lazy evaluation?
1. OPTIMIZATION: Combines operations before execution
2. EFFICIENCY: Skips unnecessary steps
3. PLANNING: Creates optimal execution plan

Difference:
Transformations: map, filter, select (lazy)
Actions: show, collect, count (eager)
```

---

#### Q1.4: What is Spark SQL?
**Answer:**
```
Spark SQL is a module for structured data processing using SQL.

Why use it?
- Familiar SQL syntax
- Automatically optimized
- Works with DataFrames
- Better performance than RDD

Example:
df.createOrReplaceTempView("employees")

spark.sql("""
    SELECT Department, AVG(Salary) as AvgSalary
    FROM employees
    GROUP BY Department
    ORDER BY AvgSalary DESC
""").show()

Same as DataFrame API:
df.groupBy("Department").agg(avg("Salary").alias("AvgSalary"))
```

---

### TIER 2: Intermediate (IMPORTANT)

#### Q2.1: Explain Spark Architecture
**Answer:**
```
Spark uses Master-Slave architecture:

1. DRIVER (Your Application)
   - Main process
   - Creates execution plan
   - Sends tasks to executors
   - Collects results

2. EXECUTORS (Worker Processes)
   - Run on separate machines
   - Execute tasks in parallel
   - Cache data in memory
   - Multiple per machine

3. CLUSTER MANAGER
   - Allocates resources (CPU, memory)
   - Manages executors
   - Types: Spark, YARN, Kubernetes

Flow:
1. User submits Spark app
2. Driver creates execution plan (DAG)
3. Cluster manager allocates executors
4. Executors process partitions in parallel
5. Results returned to driver

Why distributed?
- Parallel processing = Speed
- Multiple nodes = Scales to petabytes
- Fault tolerance = No data loss
```

---

#### Q2.2: How would you check data quality using Spark?
**Answer:**
```
Scenario: Validate 1TB customer data daily

Steps:
1. Load data into DataFrame
2. Run parallel DQ checks:
   - Completeness: COUNT WHERE col IS NULL
   - Uniqueness: Find duplicates
   - Validity: Check format (email, phone)
   - Consistency: Cross-system comparison
   - Accuracy: Cross-field validation

3. Generate metrics
4. Save results to database

Code example:
from pyspark.sql.functions import col, isnull, sum

df = spark.read.parquet("customers")

# Completeness
completeness = df.select([
    ((df.count() - sum(isnull(col(c)).cast("int"))) / df.count() * 100)
    for c in df.columns
])

# Duplicates
duplicates = df.groupBy(df.columns).count().filter("count > 1")

# Invalid emails
invalid = df.filter(~col("email").rlike("^[A-Za-z0-9._%+-]+@"))

Why Spark?
- Process 1TB in minutes (not hours)
- Parallel checks scale well
- Simple to code
- Integrates with pipelines
```

---

#### Q2.3: Difference between map and flatMap
**Answer:**
```
MAP: Transform each element 1-to-1
- Input: [1, 2, 3]
- map(x => x * 2)
- Output: [2, 4, 6]

FLATMAP: Transform then flatten
- Input: ["hello world", "spark rocks"]
- flatMap(x => x.split(" "))
- Output: ["hello", "world", "spark", "rocks"]

Use flatMap when:
- Need to split/expand each element
- Result is collection of elements
- Need to flatten nested structure

Real example:
flatMap is perfect for word count:
text.flatMap(x => x.split(" "))  # Each line becomes multiple words
```

---

#### Q2.4: What's Catalyst Optimizer?
**Answer:**
```
Catalyst is Spark's query optimizer.

What it does:
1. Analyzes query plan
2. Rewrites to optimize
3. Generates efficient code

Example optimization:
Inefficient:
df.select("*")
  .filter(df.age > 25)

Catalyst rewrites to:
df.filter(df.age > 25)
  .select("name", "age")

Why?
- Filter first = fewer rows to read
- Select specific columns = less memory

Benefits:
- You don't optimize manually
- Automatic query rewriting
- Sometimes 100x faster!

Never write for optimization manually.
Trust Catalyst to optimize for you.
```

---

### TIER 3: Advanced (HARD)

#### Q3.1: How does Spark handle fault tolerance?
**Answer:**
```
Spark recovers from failures using RDD Lineage.

How it works:
1. Each RDD remembers parent RDD and transformation
2. If a partition is lost, Spark recomputes it
3. Uses DAG (Directed Acyclic Graph)

Example:
rdd1 = sc.parallelize([1,2,3,4,5])
rdd2 = rdd1.map(lambda x: x*2)      # Remembers: from rdd1 via map
rdd3 = rdd2.filter(lambda x: x>5)   # Remembers: from rdd2 via filter

If executor with rdd3 fails:
- Spark asks: "What was rdd3's lineage?"
- Recomputes from rdd1
- Reapplies transformations
- Gets same result (fault tolerant!)

Why this is important:
✓ No data loss
✓ Automatic recovery
✓ Exactly-once semantics
✓ Can run on unreliable hardware

This is why Spark works on cloud/cluster!
```

---

#### Q3.2: Explain Spark's in-memory computing
**Answer:**
```
Spark keeps data in memory between operations.
Hadoop reads/writes to disk every time (slow).

Memory vs Disk:
- Memory: 1000x faster than disk
- But limited (usually 64-256 GB per machine)

Why it matters:
Operation 1: Load data → MEMORY
Operation 2: Filter → Memory to memory (FAST!)
Operation 3: GroupBy → Memory to memory (FAST!)

Hadoop:
Operation 1: Load → DISK
Operation 2: Filter → DISK to disk
Operation 3: GroupBy → DISK to disk

Result:
- Hadoop: 10 hours for 1TB
- Spark: 10 minutes for 1TB

Important:
- Data must fit in cluster memory
- If data > memory, spills to disk
- Caching keeps important data in memory
```

---

#### Q3.3: How would you optimize a slow Spark job?
**Answer:**
```
1. CACHING
   df.cache()  # Keep in memory for reuse

2. PARTITIONING
   df.repartition(100)  # Split for parallel processing

3. BROADCAST SMALL DATA
   broadcast_var = sc.broadcast(small_lookup)

4. USE SQL (Catalyst optimizes)
   Instead of RDD, use SQL/DataFrame

5. CONFIGURE PROPERLY
   spark.executor.memory = 4g
   spark.executor.cores = 4

6. AVOID SHUFFLES
   Shuffles move data between nodes (expensive)

7. SELECT ONLY NEEDED COLUMNS
   df.select("name", "age")  # Not df.select("*")

8. USE APPROPRIATE DATA FORMAT
   Parquet > CSV > JSON (compression, schema)

9. INCREASE PARTITIONS
   More partitions = more parallelism

10. MONITOR EXECUTION
    Use Spark UI to identify bottlenecks
    
Example optimization:
BEFORE:
df1.select("*")
  .join(df2)
  .groupBy("department")

AFTER:
df1.select("dept_id", "salary")
  .repartition("dept_id")
  .join(df2, "dept_id")
  .groupBy("dept_id")
```

---

#### Q3.4: What are limitations of Spark?
**Answer:**
```
1. IN-MEMORY LIMITATION
   - Data must fit in cluster RAM
   - Workaround: Use disk-based storage

2. LATENCY
   - Startup time: Several seconds
   - Not real-time (low-latency)
   - Workaround: Spark Streaming

3. DEBUGGING DIFFICULTY
   - Distributed execution is complex
   - Error messages can be cryptic

4. MEMORY MANAGEMENT
   - GC pauses affect performance

5. SMALL DATA
   - Overhead > benefit for small datasets
   - Use pandas instead

6. REAL-TIME
   - Not suitable for real-time systems
   - Latency typically > 1 second
   - Use Kafka Streams for true real-time

7. MACHINE LEARNING PRODUCTION
   - Spark ML is basic
   - Use dedicated tools for production ML

When NOT to use Spark:
- Small data: Use pandas
- Real-time systems: Use Kafka
- Low-latency needs: Use specialized tools
- Simple ETL: Python scripts sufficient
```

---

### TIER 4: Data Quality Specific

#### Q4.1: Design a data quality pipeline using Spark
**Answer:**
```
Architecture:
1. DATA INGESTION
   - Read from various sources
   - CSV, Parquet, database, API

2. DATA PROFILING
   - Analyze data structure
   - Calculate statistics
   - Find patterns

3. VALIDATION
   - Completeness: Check nulls
   - Uniqueness: Find duplicates
   - Validity: Format validation
   - Consistency: Cross-system match
   - Accuracy: Cross-field validation

4. QUALITY METRICS
   - Calculate scores
   - Store in metrics database

5. ALERTING
   - If quality below threshold
   - Send notification

6. REMEDIATION
   - Fix/flag bad data
   - Update data source

7. REPORTING
   - Daily quality reports
   - Historical trending

Implementation:
```python
class DQPipeline:
    def __init__(self, spark):
        self.spark = spark
        self.metrics = {}
    
    def ingest(self, path):
        return self.spark.read.parquet(path)
    
    def validate_completeness(self, df):
        # Count nulls per column
        pass
    
    def validate_uniqueness(self, df):
        # Find duplicates
        pass
    
    def validate_validity(self, df):
        # Check format/patterns
        pass
    
    def generate_metrics(self):
        # Calculate quality scores
        pass
    
    def alert(self):
        # Send alerts if needed
        pass
    
    def remediate(self):
        # Fix issues
        pass
    
    def report(self):
        # Generate report
        pass

# Run pipeline
pipeline = DQPipeline(spark)
df = pipeline.ingest("data.parquet")
pipeline.validate_completeness(df)
pipeline.validate_uniqueness(df)
pipeline.validate_validity(df)
pipeline.generate_metrics()
pipeline.report()
```

Why Spark for DQ:
✓ Process 1TB data in minutes
✓ Parallel validation at scale
✓ Easy to code and maintain
✓ Integrates with platforms (Talend, Informatica)
```

---

### TIER 5: Tricky Questions

#### Q5.1: What happens if you call collect() on huge RDD?
**Answer:**
```
DANGER: Don't do this!

collect() returns ALL data to driver memory.

Problem:
rdd = sc.parallelize(range(1000000000))  # 1 billion elements
result = rdd.collect()  # CRASH! Out of memory

Why?
- Driver tries to hold 1 billion elements
- Driver memory: usually 2-4 GB
- Need: Much more memory
- Result: Out of memory error

What to do instead:
# Option 1: Take first N elements
result = rdd.take(1000)  # Get first 1000 safely

# Option 2: Save to disk
rdd.saveAsTextFile("hdfs://path")

# Option 3: Use aggregate
result = rdd.aggregate(0)(lambda a, b: a + b, lambda a, b: a + b)

Rule:
collect() = ONLY for small datasets
For large datasets, save to disk instead
```

---

#### Q5.2: RDD.cache() vs DataFrame.cache() - which is better?
**Answer:**
```
Both serve same purpose but differ in efficiency:

RDD.cache():
- Caches raw objects
- More memory needed
- No compression

DataFrame.cache():
- Caches columnar format
- Less memory (compressed)
- Faster access
- Built-in optimizations

Example:
# RDD: 1GB in memory
rdd = sc.parallelize(large_data)
rdd.cache()

# DataFrame: 100MB in memory (10x compression!)
df = spark.createDataFrame(large_data)
df.cache()

Winner: DataFrame.cache() (use this!)

Why DataFrame is better:
- Columnar storage = compression
- Predicate pushdown = skip unnecessary columns
- Catalyst = optimizations
- Parquet format = native compression

Best practice:
Always use DataFrame instead of RDD
Only use RDD for very special cases
```

---

#### Q5.3: How do you handle skewed data?
**Answer:**
```
Skewed data: Some keys have WAY more data than others

Problem:
df.groupBy("product").count()

If "Apple" appears 1B times, others 1M times:
- One executor gets huge task
- Others finish, wait for slow one
- Total time = time of slowest task

Solution 1: Salt the key
```python
from pyspark.sql.functions import rand, floor

df_salted = df.withColumn("salt", floor(rand() * 100))
df_salted = df_salted.withColumn("product_salted", 
    concat(col("product"), lit("_"), col("salt")))

result = df_salted.groupBy("product_salted").count()
```

Solution 2: Use broadcast join for small data
Solution 3: Repartition on different column
Solution 4: Use adaptive query execution

Result: Even distribution across executors
```

---

## COMMON SPARK PATTERNS FOR DQE

### Pattern 1: Completeness Check
```python
from pyspark.sql.functions import col, isnull, sum as spark_sum

total = df.count()

completeness_checks = df.select([
    ((total - spark_sum(isnull(col(c)).cast("int"))) / total * 100)
    .alias(f"{c}_completeness_pct")
    for c in df.columns
])

completeness_checks.show()
```

### Pattern 2: Duplicate Detection
```python
# Find full duplicates
duplicates = df.groupBy(df.columns).count().filter("count > 1")

# Find duplicates on specific columns
duplicates = df.groupBy("email").count().filter("count > 1")
```

### Pattern 3: Data Validity Check
```python
# Invalid emails
invalid_emails = df.filter(
    ~col("email").rlike("^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$")
)

# Invalid age (0-150)
invalid_ages = df.filter((col("age") < 0) | (col("age") > 150))
```

### Pattern 4: Cross-System Consistency
```python
joined = crm_df.join(billing_df, "customer_id", "full")
mismatches = joined.filter(
    crm_df.status != billing_df.status
)
```

### Pattern 5: Quality Scorecard
```python
report = df.select([
    spark.sql(f"COUNT(*) FILTER (WHERE {col} IS NOT NULL) / COUNT(*) * 100")
    for col in df.columns
])
```

---

## INTERVIEW SUCCESS TIPS

✅ **DO:**
- Understand lazy evaluation
- Know when to use RDD vs DataFrame
- Can write basic transformations
- Understand Spark architecture basics
- Know difference between actions and transformations
- Explain why Spark is fast (in-memory)
- Give real examples

❌ **DON'T:**
- Use collect() on large data
- Confuse RDD and DataFrame
- Forget about partitioning
- Optimize prematurely
- Use RDD when DataFrame works
- Ignore Catalyst optimizer

---

## FINAL CHECKLIST

- [ ] Understand what Spark is and why it's fast
- [ ] Explain RDD vs DataFrame (choose DataFrame!)
- [ ] Know lazy evaluation concept
- [ ] Can write map, filter, groupBy operations
- [ ] Understand Spark SQL basics
- [ ] Know difference between actions/transformations
- [ ] Can explain fault tolerance
- [ ] Know how to optimize (cache, partition, etc.)
- [ ] Can design DQ pipeline
- [ ] Understand architecture (driver, executors, tasks)

---

## KEY TAKEAWAYS

1. **Spark = Fast Distributed Computing**
2. **Use DataFrame (99% of time, not RDD)**
3. **Lazy Evaluation = Optimization before execution**
4. **Actions trigger execution (collect, show, count)**
5. **Transformations are free (map, filter, select)**
6. **In-memory = 100x faster than disk**
7. **Parallel processing = scales to petabytes**
8. **Fault tolerant = no data loss**
9. **Perfect for Data Quality = Process TB in minutes**
10. **Catalyst Optimizer = trust it to optimize for you**

---

**You're ready for Spark interviews! 🚀**

*Last Updated: 2026-07-29*
