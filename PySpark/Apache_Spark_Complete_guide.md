# Apache Spark - Complete Beginner-Friendly Guide

## TABLE OF CONTENTS
1. [What is Spark?](#what-is-spark)
2. [Spark Architecture](#spark-architecture)
3. [RDD vs DataFrame vs Dataset](#rdd-vs-dataframe-vs-dataset)
4. [Spark SQL](#spark-sql)
5. [Transformations & Actions](#transformations--actions)
6. [Real-World Examples](#real-world-examples)
7. [Data Quality with Spark](#data-quality-with-spark)
8. [Performance Optimization](#performance-optimization)
9. [Interview Q&A](#interview-qa)

---

## WHAT IS SPARK?

### Simple Definition
**Apache Spark** is a fast, distributed computing framework that processes large amounts of data in parallel across multiple machines.

**In Simple Terms:**
- **Traditional Computing:** Process data on 1 computer (slow)
- **Spark:** Process data on 100 computers at same time (FAST!)

### Why Spark?
```
Problem: Need to process 1 TB of data
- Old way (Hadoop): 10 hours
- Spark way: 10 minutes
- Why? Parallel processing + in-memory computation
```

### Key Characteristics
```
✓ FAST: 100x faster than Hadoop (in-memory processing)
✓ GENERAL-PURPOSE: SQL, Machine Learning, Streaming
✓ SCALABLE: Works on 1 machine or 1000 machines
✓ EASY TO USE: Python, Scala, Java, SQL
✓ UNIFIED: One framework for all data tasks
```

### Spark vs Hadoop
| Feature | Hadoop | Spark |
|---------|--------|-------|
| Speed | Slow (disk I/O) | 100x faster (in-memory) |
| Complexity | Complex | Simple, concise |
| Languages | Java | Python, Scala, Java, SQL |
| Learning Curve | Steep | Gentle |
| Use Case | Batch processing | Batch + Streaming + ML |

---

## SPARK ARCHITECTURE

### How Spark Works (High Level)

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR SPARK CODE                      │
│                  (Python/Scala/SQL)                     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│                  SPARK CONTEXT                          │
│        (Entry point for your Spark application)         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│                  SPARK DRIVER                           │
│        (Manages job distribution, coordinates)          │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
    ┌────────┐   ┌────────┐   ┌────────┐
    │Executor│   │Executor│   │Executor│  ← Worker Nodes
    │        │   │        │   │        │
    │ Tasks  │   │ Tasks  │   │ Tasks  │
    └────────┘   └────────┘   └────────┘
    
    Parallel processing on multiple machines!
```

### Key Components

#### 1. **Spark Context (SC)**
Entry point for Spark functionality. Tells Spark how to access a cluster.

```python
from pyspark import SparkContext

# Create Spark Context
sc = SparkContext("local", "Simple App")
# "local" = run on single machine
# "spark://master:7077" = connect to cluster
```

#### 2. **Spark Session**
Higher-level entry point (modern way). Combines SQL and DataFrame functionality.

```python
from pyspark.sql import SparkSession

# Create Spark Session
spark = SparkSession.builder \
    .appName("MyApp") \
    .getOrCreate()

# This is more common now than SparkContext
```

#### 3. **Driver**
- The main process that coordinates job execution
- Coordinates between executors
- Collects results and sends back to user

#### 4. **Executor**
- Worker processes that execute tasks
- Run on separate machines
- Each has its own memory for caching

#### 5. **Task**
- Unit of work sent to executor
- Runs in parallel

### Example: Word Count (Understanding the Flow)

```python
# Step 1: Create Spark Session
spark = SparkSession.builder.appName("WordCount").getOrCreate()

# Step 2: Load data
lines = spark.read.text("data.txt")

# Step 3: Transform (Lazy - not executed yet!)
words = lines.rdd.flatMap(lambda x: x[0].split())
word_count = words.map(lambda x: (x, 1)).reduceByKey(lambda x, y: x + y)

# Step 4: Action (Execute!)
results = word_count.collect()
print(results)
```

**What happens internally:**
1. Driver creates execution plan
2. Breaks into stages
3. Sends tasks to executors
4. Executors process in parallel
5. Results collected to driver
6. Returned to user

---

## RDD vs DATAFRAME vs DATASET

### Quick Comparison

| Feature | RDD | DataFrame | Dataset |
|---------|-----|-----------|---------|
| **Type** | Low-level | Structured (SQL-like) | Strongly-typed |
| **Ease** | Hard | Easy | Medium |
| **Performance** | Slow | Fast | Fast |
| **Languages** | All | All | Scala/Java |
| **Schema** | No | Yes | Yes |
| **Use Case** | Low-level transform | SQL queries | Type-safe operations |

---

### 1. RDD (Resilient Distributed Dataset)

**What it is:** Low-level collection of objects distributed across cluster.

**Key Features:**
- Immutable (cannot change)
- Distributed (spread across machines)
- Lazy evaluation (compute when action called)
- Fault-tolerant (can recover from node failure)

**Simple Example:**
```python
from pyspark import SparkContext

sc = SparkContext("local", "RDD Example")

# Create RDD from list
numbers = sc.parallelize([1, 2, 3, 4, 5])

# Transform (lazy - not executed yet)
squared = numbers.map(lambda x: x ** 2)

# Action (executes the computation)
result = squared.collect()
print(result)  # [1, 4, 9, 16, 25]
```

**When to use RDD:**
- Unstructured data
- Low-level transformations
- Complex operations
- Not recommended for beginners

---

### 2. DataFrame

**What it is:** Structured data organized in named columns (like SQL table or pandas DataFrame).

**Key Features:**
- Organized in rows and columns
- Has schema (column names, types)
- Optimized execution
- SQL-queryable

**Simple Example:**
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("DataFrame Example").getOrCreate()

# Create DataFrame from list of tuples
data = [("John", 25), ("Jane", 30), ("Bob", 35)]
columns = ["Name", "Age"]

df = spark.createDataFrame(data, columns)

# Show data
df.show()
# +----+---+
# |Name|Age|
# +----+---+
# |John| 25|
# |Jane| 30|
# | Bob| 35|
# +----+---+

# Filter
df.filter(df.Age > 25).show()
# +----+---+
# |Name|Age|
# +----+---+
# |Jane| 30|
# | Bob| 35|
# +----+---+

# SQL Query
df.createOrReplaceTempView("people")
spark.sql("SELECT * FROM people WHERE Age > 25").show()
```

**Creating DataFrames:**
```python
# From CSV
df = spark.read.csv("data.csv", header=True)

# From JSON
df = spark.read.json("data.json")

# From Parquet
df = spark.read.parquet("data.parquet")

# From database
df = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://localhost/mydb") \
    .option("dbtable", "users") \
    .option("user", "username") \
    .option("password", "password") \
    .load()

# From Python list
df = spark.createDataFrame([(1, "a"), (2, "b")], ["id", "value"])
```

**DataFrame Operations:**
```python
# Select columns
df.select("Name", "Age").show()

# Filter rows
df.filter(df.Age > 25).show()

# Group by
df.groupBy("Age").count().show()

# Sort
df.sort(df.Age.desc()).show()

# Join
df_joined = df1.join(df2, "id")

# Aggregate
df.agg({"Age": "max", "Salary": "avg"}).show()
```

---

### 3. Dataset

**What it is:** Type-safe collection (like DataFrame but with compile-time type checking).

**Note:** Available in Scala and Java, not Python.

**Example (Scala):**
```scala
case class Person(name: String, age: Int)

val data = Seq(
  Person("John", 25),
  Person("Jane", 30)
)

val ds = spark.createDataset(data)
ds.filter(_.age > 25).show()
```

**Why Dataset?**
- Type-safe: Errors caught at compile time
- Better performance than RDD
- More structured than RDD, stricter than DataFrame

---

### Which Should You Use?

```
IF you're using Python:
  → Use DataFrame (99% of cases)
  
IF you need low-level control:
  → Use RDD
  
IF you're using Scala/Java and need type safety:
  → Use Dataset
  
IF you're doing SQL:
  → Use DataFrame with SQL
```

---

## SPARK SQL

### What is Spark SQL?

Module for structured data processing using SQL queries.

**Why Spark SQL?**
- Familiar SQL syntax
- Automatically optimized
- Works with DataFrames
- Better performance

### Creating and Querying

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("SparkSQL").getOrCreate()

# Create DataFrame
data = [
    ("John", "IT", 5000),
    ("Jane", "HR", 6000),
    ("Bob", "IT", 5500),
    ("Alice", "HR", 6500)
]
columns = ["Name", "Department", "Salary"]

df = spark.createDataFrame(data, columns)

# Method 1: Register as temporary view
df.createOrReplaceTempView("employees")

# Method 2: Query using SQL
spark.sql("""
    SELECT Department, AVG(Salary) as AvgSalary
    FROM employees
    GROUP BY Department
    ORDER BY AvgSalary DESC
""").show()

# Output:
# +----------+----------+
# |Department|AvgSalary |
# +----------+----------+
# |HR        |6250.0    |
# |IT        |5250.0    |
# +----------+----------+
```

### Spark SQL vs DataFrame API

```python
# Same query, two ways:

# Method 1: SQL
spark.sql("SELECT * FROM employees WHERE Salary > 5000").show()

# Method 2: DataFrame API
df.filter(df.Salary > 5000).show()

# Both are equivalent!
# SQL is easier to understand
# DataFrame API is more programmatic
```

### Common SQL Operations

```python
# SELECT
spark.sql("SELECT Name, Salary FROM employees").show()

# WHERE
spark.sql("SELECT * FROM employees WHERE Salary > 5000").show()

# GROUP BY
spark.sql("""
    SELECT Department, COUNT(*) as Count
    FROM employees
    GROUP BY Department
""").show()

# ORDER BY
spark.sql("SELECT * FROM employees ORDER BY Salary DESC").show()

# JOIN
spark.sql("""
    SELECT e.Name, e.Salary, d.DepartmentName
    FROM employees e
    JOIN departments d ON e.Department = d.Code
""").show()

# Aggregate Functions
spark.sql("""
    SELECT 
        Department,
        COUNT(*) as Count,
        AVG(Salary) as AvgSalary,
        MAX(Salary) as MaxSalary,
        MIN(Salary) as MinSalary
    FROM employees
    GROUP BY Department
""").show()
```

---

## TRANSFORMATIONS & ACTIONS

### Understanding Lazy Evaluation

**Key Concept:** Spark is LAZY!

```python
# These DON'T execute immediately (lazy):
transformed = df.filter(df.Age > 25).select("Name")

# This EXECUTES (action):
result = transformed.show()
```

**Why is Spark lazy?**
- Optimize computation before execution
- Combine multiple operations
- Skip unnecessary steps

---

### Transformations (Lazy - Don't Execute)

#### 1. **map** - Transform each element

```python
rdd = sc.parallelize([1, 2, 3, 4])

# Map: apply function to each element
squared = rdd.map(lambda x: x ** 2)

# Result not computed yet (lazy!)
# Only computed when action called:
squared.collect()  # [1, 4, 9, 16]
```

#### 2. **filter** - Keep matching elements

```python
rdd = sc.parallelize([1, 2, 3, 4, 5])

# Keep only > 2
filtered = rdd.filter(lambda x: x > 2)

filtered.collect()  # [3, 4, 5]
```

#### 3. **flatMap** - Map then flatten

```python
rdd = sc.parallelize(["hello world", "spark is cool"])

# Split each line, then flatten
words = rdd.flatMap(lambda x: x.split())

words.collect()  # ['hello', 'world', 'spark', 'is', 'cool']
```

#### 4. **reduceByKey** - Group and combine

```python
rdd = sc.parallelize([
    ("apple", 1),
    ("banana", 1),
    ("apple", 1),
    ("banana", 1),
    ("apple", 1)
])

# Sum by key
result = rdd.reduceByKey(lambda x, y: x + y)

result.collect()
# [('apple', 3), ('banana', 2)]
```

#### 5. **groupByKey** - Group values by key

```python
rdd = sc.parallelize([
    ("apple", 1),
    ("banana", 2),
    ("apple", 3),
    ("banana", 4)
])

grouped = rdd.groupByKey()

result = grouped.mapValues(list)
# [('apple', [1, 3]), ('banana', [2, 4])]
```

#### 6. **join** - Join two RDDs

```python
rdd1 = sc.parallelize([("a", 1), ("b", 2)])
rdd2 = sc.parallelize([("a", 10), ("b", 20)])

joined = rdd1.join(rdd2)

joined.collect()
# [('a', (1, 10)), ('b', (2, 20))]
```

#### 7. **select & filter** - DataFrame transformations

```python
# Select columns
df.select("Name", "Age")

# Filter rows
df.filter(df.Age > 25)

# Select with conditions
df.select("Name", (df.Salary * 1.1).alias("IncreasedSalary"))

# Multiple conditions
df.filter((df.Age > 25) & (df.Department == "IT"))
```

#### 8. **groupBy** - DataFrame grouping

```python
# Group and count
df.groupBy("Department").count()

# Group and aggregate
df.groupBy("Department").agg({
    "Salary": "avg",
    "Name": "count"
})
```

---

### Actions (Eager - Execute Immediately)

#### 1. **collect** - Return all data to driver

```python
rdd = sc.parallelize([1, 2, 3, 4, 5])

result = rdd.map(lambda x: x ** 2).collect()
print(result)  # [1, 4, 9, 16, 25]

# WARNING: Only use on small datasets!
# If RDD is huge, this will crash driver
```

#### 2. **show** - Display DataFrame

```python
df.show()           # Show 20 rows
df.show(5)          # Show 5 rows
df.show(truncate=False)  # Don't truncate columns
```

#### 3. **count** - Count elements

```python
count = rdd.count()  # How many elements?
count = df.count()   # How many rows?
```

#### 4. **first** - Get first element

```python
first = rdd.first()  # Get first element
first = df.first()   # Get first row
```

#### 5. **take** - Get first N elements

```python
first_5 = rdd.take(5)  # Get first 5 elements
```

#### 6. **saveAsTextFile** - Save to file

```python
rdd.saveAsTextFile("hdfs://path/to/output")
```

#### 7. **foreach** - Apply function to each element

```python
rdd.foreach(lambda x: print(x))  # Print each element
```

#### 8. **write** - Save DataFrame

```python
# Save as Parquet
df.write.parquet("path/to/output")

# Save as CSV
df.write.csv("path/to/output")

# Save as JSON
df.write.json("path/to/output")

# Save to database
df.write \
    .format("jdbc") \
    .mode("overwrite") \
    .option("url", "jdbc:postgresql://localhost/mydb") \
    .option("dbtable", "users") \
    .option("user", "username") \
    .option("password", "password") \
    .save()
```

---

### Transformation vs Action Summary

| Type | Executes? | Example | Returns |
|------|-----------|---------|---------|
| **Transformation** | No (lazy) | map, filter, select | RDD/DataFrame |
| **Action** | Yes (eager) | collect, show, count | Result |

**Golden Rule:**
```
Transformations are free (lazy)
Actions cost (execute)
```

---

## REAL-WORLD EXAMPLES

### Example 1: Customer Sales Analysis

**Scenario:** Analyze customer purchase patterns

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import sum, avg, count

spark = SparkSession.builder.appName("SalesAnalysis").getOrCreate()

# Load sales data
sales_df = spark.read.csv("sales.csv", header=True, inferSchema=True)

# Show data
sales_df.show(3)
# +-----------+--------+----------+
# |CustomerId |Product |  Amount  |
# +-----------+--------+----------+
# |    1      | Apple  |  100.00  |
# |    1      | Orange |  50.00   |
# |    2      | Apple  |  200.00  |
# +-----------+--------+----------+

# Analysis 1: Total sales by customer
customer_sales = sales_df.groupBy("CustomerId").agg(
    sum("Amount").alias("TotalSales"),
    count("*").alias("Purchases")
)

customer_sales.show()
# +-----------+----------+----------+
# |CustomerId |TotalSales|Purchases |
# +-----------+----------+----------+
# |    1      |  150.00  |    2     |
# |    2      |  200.00  |    1     |
# +-----------+----------+----------+

# Analysis 2: Average sale by product
product_avg = sales_df.groupBy("Product").agg(
    avg("Amount").alias("AvgSale")
).orderBy("AvgSale", ascending=False)

product_avg.show()
# +--------+--------+
# |Product |AvgSale |
# +--------+--------+
# | Apple  | 150.00 |
# | Orange |  50.00 |
# +--------+--------+

# Analysis 3: Using SQL
sales_df.createOrReplaceTempView("sales")

top_customers = spark.sql("""
    SELECT 
        CustomerId,
        SUM(Amount) as TotalSpent
    FROM sales
    GROUP BY CustomerId
    HAVING SUM(Amount) > 100
    ORDER BY TotalSpent DESC
""")

top_customers.show()
```

---

### Example 2: Data Quality Check (Perfect for your DQE role!)

**Scenario:** Validate customer data quality

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, isnan, isnull, when

spark = SparkSession.builder.appName("DataQuality").getOrCreate()

# Load customer data
df = spark.read.csv("customers.csv", header=True, inferSchema=True)

# DQ Check 1: Find null values
null_check = df.select([
    (isnull(col(c)).cast("int").alias(f"{c}_null")) 
    for c in df.columns
])

null_counts = null_check.select([
    sum(c).alias(c) 
    for c in null_check.columns
])

print("Null counts per column:")
null_counts.show()

# DQ Check 2: Completeness percentage
total_rows = df.count()

completeness = df.select([
    ((total_rows - sum(isnull(col(c)).cast("int"))) / total_rows * 100).alias(f"{c}_completeness")
    for c in df.columns
])

print("Completeness percentage:")
completeness.show()

# DQ Check 3: Find duplicates
duplicates = df.groupBy(df.columns).count().filter("count > 1")

print(f"Found {duplicates.count()} duplicate records")

# DQ Check 4: Data type validation
print("Schema:")
df.printSchema()

# DQ Check 5: Invalid emails
invalid_emails = df.filter(~col("email").rlike("^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$"))

print(f"Found {invalid_emails.count()} invalid emails")

# Save results
completeness.write.csv("dq_completeness_report.csv", header=True)
```

---

### Example 3: Processing Log Files

**Scenario:** Analyze application logs

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, split, substring

spark = SparkSession.builder.appName("LogAnalysis").getOrCreate()

# Load logs
logs = spark.read.text("application.log")

# Sample log: 2024-01-15 10:30:45 ERROR Database connection failed
logs.show(3)

# Parse log line
parsed_logs = logs.select(
    substring(col("value"), 1, 10).alias("Date"),
    substring(col("value"), 12, 8).alias("Time"),
    split(col("value"), " ").getItem(4).alias("Level"),
    substring(col("value"), 24, 100).alias("Message")
)

parsed_logs.show()

# Analyze errors
error_logs = parsed_logs.filter(col("Level") == "ERROR")

print(f"Total errors: {error_logs.count()}")

# Errors by type
error_summary = error_logs.groupBy("Message").count().orderBy("count", ascending=False)

print("Top 10 errors:")
error_summary.show(10)
```

---

## DATA QUALITY WITH SPARK

### Complete Data Quality Framework

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, sum, count, isnull, isnan,
    when, avg, lit
)

spark = SparkSession.builder.appName("DQFramework").getOrCreate()

class DataQualityValidator:
    def __init__(self, df):
        self.df = df
        self.total_rows = df.count()
        self.quality_report = {}
    
    def check_completeness(self):
        """Check for missing values"""
        completeness_scores = {}
        
        for col_name in self.df.columns:
            non_null_count = self.df.filter(col(col_name).isNotNull()).count()
            completeness = (non_null_count / self.total_rows) * 100
            completeness_scores[col_name] = completeness
        
        self.quality_report['completeness'] = completeness_scores
        return completeness_scores
    
    def check_duplicates(self):
        """Check for duplicate records"""
        duplicate_count = self.df.count() - self.df.dropDuplicates().count()
        self.quality_report['duplicates'] = duplicate_count
        return duplicate_count
    
    def check_validity(self, column, pattern):
        """Check if values match pattern"""
        invalid_count = self.df.filter(~col(column).rlike(pattern)).count()
        self.quality_report[f'{column}_validity'] = invalid_count
        return invalid_count
    
    def check_consistency(self, df2, join_key, columns):
        """Check consistency between two DataFrames"""
        mismatches = 0
        
        for col_name in columns:
            joined = self.df.join(df2, join_key, "inner")
            mismatches += joined.filter(
                col(f"df1.{col_name}") != col(f"df2.{col_name}")
            ).count()
        
        self.quality_report['consistency'] = mismatches
        return mismatches
    
    def generate_report(self):
        """Generate summary report"""
        print("\n========== DATA QUALITY REPORT ==========")
        for check, result in self.quality_report.items():
            print(f"{check}: {result}")
        print("=========================================\n")

# Usage
df = spark.read.csv("customers.csv", header=True, inferSchema=True)

validator = DataQualityValidator(df)
validator.check_completeness()
validator.check_duplicates()
validator.check_validity("email", "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$")
validator.generate_report()
```

---

## PERFORMANCE OPTIMIZATION

### 1. **Caching**
Store frequently-used DataFrames in memory.

```python
df = spark.read.csv("large_file.csv")

# Cache in memory (persist)
df.cache()  # or df.persist()

# Now operations on df will be fast
result1 = df.filter(df.Age > 25).count()
result2 = df.filter(df.Age < 30).count()  # Faster!

# Remove from cache when done
df.unpersist()
```

**When to cache:**
- DataFrame used multiple times
- Expensive transformations

---

### 2. **Partitioning**
Split data into chunks for parallel processing.

```python
# Write with partitions
df.write \
    .partitionBy("Department") \
    .csv("output_path")

# Read partitioned data
df = spark.read.csv("output_path")
# Spark automatically uses partitions

# Filter on partition (smart!)
# Skips irrelevant partitions
df.filter(df.Department == "IT")
```

---

### 3. **Broadcast Variables**
Send small data to all executors.

```python
# Small reference data
small_lookup = {"A": "Apple", "B": "Banana"}

# Broadcast to executors
broadcast_lookup = sc.broadcast(small_lookup)

# Use in RDD
rdd = sc.parallelize(["A", "B", "A"])
result = rdd.map(lambda x: broadcast_lookup.value[x])

result.collect()  # ['Apple', 'Banana', 'Apple']
```

---

### 4. **Avoid Shuffling**
Minimize data movement between nodes.

```python
# BAD: Causes shuffle
df.groupBy("Department").count()

# BETTER: If already partitioned by Department
df.repartition("Department").groupBy("Department").count()
```

---

### 5. **Use SQL Instead of RDD**
DataFrames are optimized by Catalyst optimizer.

```python
# SLOW (RDD)
rdd = sc.parallelize([1, 2, 3, 4, 5])
result = rdd.map(lambda x: x ** 2).filter(lambda x: x > 5)

# FAST (DataFrame)
df = spark.createDataFrame([(1,), (2,), (3,), (4,), (5,)], ["value"])
result = df.select((col("value") ** 2).alias("squared")) \
    .filter(col("squared") > 5)
```

---

### 6. **Configure Spark**

```python
spark = SparkSession.builder \
    .appName("MyApp") \
    .config("spark.executor.memory", "4g") \
    .config("spark.executor.cores", "4") \
    .config("spark.driver.memory", "2g") \
    .config("spark.sql.shuffle.partitions", "200") \
    .getOrCreate()

# Or via spark-submit
# spark-submit --executor-memory 4g --executor-cores 4 app.py
```

---

## INTERVIEW Q&A

### Q1: What is Apache Spark? Why use it?
**Answer:**
```
Apache Spark is a fast, distributed computing framework for processing large data.

Why use it:
1. SPEED: 100x faster than Hadoop (in-memory processing)
2. EASE: Simple Python/SQL APIs
3. GENERALITY: SQL, ML, Streaming in one framework
4. SCALABILITY: From laptop to cluster
5. FAULT TOLERANCE: Recovers from node failures

Real example: Processing 1TB of data
- Hadoop: 10 hours
- Spark: 10 minutes
```

---

### Q2: Explain Spark Architecture
**Answer:**
```
Spark has Master-Slave architecture:

DRIVER (Master):
- Your main application
- Creates tasks
- Coordinates execution
- Collects results

EXECUTORS (Slaves):
- Run on worker nodes
- Execute tasks
- Cache data in memory

CLUSTER MANAGER:
- Allocates resources
- Manages nodes
- Types: Spark, YARN, Kubernetes

Flow:
1. User submits Spark application
2. Driver creates execution plan
3. Cluster manager allocates executors
4. Executors process data in parallel
5. Results collected by driver
```

---

### Q3: RDD vs DataFrame vs Dataset?
**Answer:**
```
RDD (Resilient Distributed Dataset):
- Low-level API
- Unstructured data
- Requires manual optimization
- Use: Complex transformations, unstructured data

DataFrame:
- High-level API (structured)
- SQL-like operations
- Auto-optimized by Catalyst
- Use: 99% of cases, recommended

Dataset:
- Type-safe (Scala/Java only)
- Combines DataFrame + RDD benefits
- Compile-time type checking
- Use: When you need type safety

Example:
RDD: sc.parallelize([1,2,3]).map(x => x*2)
DF: spark.createDataFrame([(1,), (2,), (3,)], ["val"]).select(col("val")*2)
```

---

### Q4: What is Lazy Evaluation?
**Answer:**
```
Spark doesn't execute transformations immediately.
Executes only when an action is called.

Example:
df.filter(df.Age > 25)        # Not executed (lazy)
  .select("Name")             # Not executed (lazy)
  .show()                     # EXECUTES (action)

Why?
1. Optimization: Combines operations
2. Efficiency: Skips unnecessary steps
3. Planning: Creates optimal plan before execution

Key difference:
- Transformations: map, filter, select (lazy)
- Actions: show, collect, count (eager)
```

---

### Q5: How do you optimize Spark performance?
**Answer:**
```
1. CACHING
   df.cache()  # Keep in memory for reuse

2. PARTITIONING
   df.repartition(100)  # Split data for parallel processing

3. BROADCAST VARIABLES
   broadcast_var = sc.broadcast(small_data)

4. USE SQL
   Catalyst optimizer auto-tunes SQL queries

5. CONFIGURE PROPERLY
   spark.executor.memory = 4g
   spark.executor.cores = 4

6. AVOID SHUFFLES
   Shuffles move data between nodes (expensive)

7. SELECT ONLY NEEDED COLUMNS
   df.select("name", "age")  # Not df.select("*")
```

---

### Q6: What is Catalyst Optimizer?
**Answer:**
```
Catalyst is Spark's query optimizer.

What it does:
1. Analyzes query plan
2. Rewrites to optimize
3. Generates efficient code

Example:
Inefficient:
df.select("*")
  .filter(df.Age > 25)

Catalyst optimizes to:
df.filter(df.Age > 25)
  .select("Age", "Name")

Pushes filter before select (fewer rows to process)
```

---

### Q7: Real-world Spark use case for Data Quality
**Answer:**
```
Scenario: Need to validate 1TB of customer data daily

Solution:
1. Load data into Spark DataFrame
2. Run parallel DQ checks:
   - Completeness (check NULLs)
   - Uniqueness (find duplicates)
   - Validity (regex patterns)
   - Consistency (cross-system match)
   - Accuracy (cross-field validation)
3. Generate quality metrics
4. Save results to database

Why Spark:
- Processes 1TB in minutes (not hours)
- Parallel checks on 100s of machines
- Scales with data growth
- Simple to code

Code:
from pyspark.sql.functions import col, isnull, sum

df = spark.read.parquet("customers")

# Completeness check
completeness = df.select([
    ((df.count() - sum(isnull(col(c)).cast("int"))) / df.count() * 100).alias(f"{c}_pct")
    for c in df.columns
])

completeness.show()
```

---

### Q8: What are the limitations of Spark?
**Answer:**
```
1. IN-MEMORY LIMITATION
   - Data must fit in cluster memory
   - Workaround: Use disk-based storage

2. LATENCY
   - Startup time: Several seconds
   - Not good for real-time (low-latency) systems
   - Workaround: Use Spark Streaming for near real-time

3. DEBUGGING DIFFICULTY
   - Distributed execution is hard to debug
   - Error messages can be cryptic

4. MEMORY MANAGEMENT
   - GC pauses can affect performance
   - Requires tuning

5. NOT SUITABLE FOR:
   - Very small data (use pandas)
   - Real-time systems (use Kafka Streams)
   - Machine learning in production (use dedicated tools)
```

---

### Q9: Explain Transformation vs Action
**Answer:**
```
TRANSFORMATIONS (Lazy):
- Create new RDD/DataFrame from existing
- Not executed immediately
- Chained together for optimization
- Examples: map, filter, select, groupBy

Example:
df.filter(df.age > 25)      # Not executed
  .select("name", "salary") # Not executed
  .show()                   # EXECUTED (action)

ACTIONS (Eager):
- Trigger computation
- Return result to driver or save to disk
- Execute immediately
- Examples: show, collect, count, save

Why distinction?
- Optimization: Spark can combine transformations
- Efficiency: Only execute what's needed
- Lazy evaluation prevents unnecessary computation
```

---

### Q10: How does Spark handle fault tolerance?
**Answer:**
```
Spark is fault-tolerant through RDD lineage tracking.

How it works:
1. RDD remembers parent RDD and transformation
2. If a node fails, Spark recomputes lost partition
3. Uses DAG (Directed Acyclic Graph)

Example:
rdd1 = sc.parallelize([1,2,3,4,5])
rdd2 = rdd1.map(lambda x: x*2)     # Remembers: came from rdd1 via map
rdd3 = rdd2.filter(lambda x: x>5)  # Remembers: came from rdd2 via filter

If executor with rdd3 data fails:
- Spark recalculates from rdd1
- Reapplies transformations
- Gets same result

Lineage ensures:
✓ No data loss
✓ Fault recovery is automatic
✓ Exactly-once semantics
```

---

## SUMMARY TABLE

| Concept | What | Use | Example |
|---------|------|-----|---------|
| **Spark Context** | Entry point | Create SC first | `sc = SparkContext(...)` |
| **RDD** | Low-level API | Complex transforms | `rdd.map(...).filter(...)` |
| **DataFrame** | High-level API | SQL queries | `df.filter(...).select(...)` |
| **Dataset** | Type-safe | Scala/Java | `ds.filter(_.age > 25)` |
| **Transformation** | Create new RDD | Lazy operation | `map, filter, select` |
| **Action** | Compute result | Execute now | `collect, show, count` |
| **Cache** | Keep in memory | Reuse data | `df.cache()` |
| **Partition** | Split data | Parallel process | `df.repartition(100)` |

---

## KEY TAKEAWAYS

1. **Spark is Fast** - 100x faster than Hadoop
2. **Lazy Evaluation** - Optimize before execute
3. **Use DataFrames** - Preferred over RDDs (99%)
4. **Transformations vs Actions** - First is lazy, second executes
5. **Distributed Computing** - Process on many machines
6. **Fault Tolerant** - Recovers from node failures
7. **Unified Platform** - SQL, ML, Streaming together
8. **Spark SQL** - Use familiar SQL syntax
9. **Optimization** - Cache, partition, broadcast
10. **Perfect for DQ** - Process large data fast

---

## NEXT STEPS

- Practice examples on Spark
- Run sample code
- Understand executors and drivers
- Learn Spark Streaming (real-time)
- Study Spark ML (Machine Learning)

**You're ready to use Spark in your Data Quality role! 🚀**

---

*Last Updated: 2026-07-29*
*Difficulty: Beginner-Friendly with Examples*
