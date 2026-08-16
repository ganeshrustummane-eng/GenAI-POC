# Apache Spark - Quick Cheat Sheet

## ONE-LINER DEFINITIONS

```
Spark = Fast distributed computing framework
RDD = Low-level distributed collection
DataFrame = High-level structured data (USE THIS!)
Transformation = Lazy operation (map, filter)
Action = Eager operation (show, collect)
Driver = Your application
Executor = Worker process
Catalyst = Query optimizer
Lineage = Fault tolerance mechanism
```

---

## INSTALLATION & SETUP

```bash
# Install
pip install pyspark

# Or conda
conda install pyspark

# Download Spark (for local)
# Download from spark.apache.org
```

---

## BASIC SETUP

```python
# Method 1: Spark Context (old way)
from pyspark import SparkContext
sc = SparkContext("local", "App Name")

# Method 2: Spark Session (modern way - RECOMMENDED)
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .appName("MyApp") \
    .config("spark.executor.memory", "4g") \
    .getOrCreate()

# Stop Spark
spark.stop()
```

---

## CREATE DATA

```python
# From list
df = spark.createDataFrame(
    [(1, "John"), (2, "Jane")],
    ["id", "name"]
)

# From pandas (if available)
import pandas as pd
pdf = pd.DataFrame({"id": [1, 2], "name": ["John", "Jane"]})
df = spark.createDataFrame(pdf)

# From file
df = spark.read.csv("file.csv", header=True)
df = spark.read.parquet("file.parquet")
df = spark.read.json("file.json")
df = spark.read.format("jdbc")\
    .option("url", "jdbc:...").load()
```

---

## DISPLAY & INSPECT

```python
# Show data
df.show()           # First 20 rows
df.show(5)          # First 5 rows
df.show(100, False) # 100 rows, no truncation

# Print schema
df.printSchema()

# Get info
df.count()          # Number of rows
df.columns          # Column names
df.dtypes           # Data types

# Sample
df.sample(0.1)      # 10% sample
```

---

## SELECT & FILTER

```python
# Select columns
df.select("name", "age")
df.select(col("name"), col("age") * 2)

# Filter rows
df.filter(df.age > 25)
df.filter((df.age > 25) & (df.name == "John"))
df.filter(df.name.startswith("J"))
df.filter(~df.age.isNull())

# Filter with SQL
df.createOrReplaceTempView("people")
spark.sql("SELECT * FROM people WHERE age > 25")
```

---

## TRANSFORMATIONS (LAZY)

```python
# Map: Transform each row
df.select((col("salary") * 1.1).alias("new_salary"))

# Filter: Keep matching
df.filter(df.age > 25)

# GroupBy: Group data
df.groupBy("department").count()

# Join: Combine DataFrames
df1.join(df2, "id")
df1.join(df2, df1.id == df2.id)
df1.join(df2, "id", "inner")  # inner/left/right/full

# Sort
df.sort(col("age").desc())
df.orderBy("age")

# Distinct: Remove duplicates
df.distinct()
df.dropDuplicates(["email"])

# Add column
df.withColumn("bonus", col("salary") * 0.1)

# Rename column
df.withColumnRenamed("old_name", "new_name")

# Drop column
df.drop("column_name")

# Union: Combine rows
df1.union(df2)
df1.unionByName(df2)  # By column name
```

---

## AGGREGATIONS

```python
from pyspark.sql.functions import sum, avg, count, max, min, mean

# Single aggregation
df.agg(count("*"))
df.agg(sum("salary"))
df.agg(avg("age"))

# Group and aggregate
df.groupBy("department").agg(
    count("*").alias("count"),
    avg("salary").alias("avg_salary"),
    max("salary").alias("max_salary")
)

# Multiple groupings
df.groupBy("department", "location").count()

# Having (filter after aggregation)
df.groupBy("department").agg(count("*")).filter("count > 5")
```

---

## ACTIONS (EAGER - EXECUTE!)

```python
# Show
df.show()

# Collect (WARNING: small data only!)
result = df.collect()  # Returns list

# Count
count = df.count()

# First
first = df.first()

# Take
first_5 = df.take(5)

# Foreach
df.foreach(lambda row: print(row))

# Save
df.write.csv("path")
df.write.parquet("path")
df.write.json("path")
df.write.mode("overwrite").parquet("path")
```

---

## SQL QUERIES

```python
# Register view
df.createOrReplaceTempView("employees")
df.createOrGlobalTempView("employees")

# Query
spark.sql("SELECT * FROM employees WHERE age > 25")

# Complex
spark.sql("""
    SELECT department, AVG(salary) as avg_salary
    FROM employees
    GROUP BY department
    HAVING AVG(salary) > 5000
    ORDER BY avg_salary DESC
""")
```

---

## SPARK FUNCTIONS

```python
from pyspark.sql.functions import (
    col, lit, upper, lower, length,
    substr, concat, trim, coalesce,
    when, otherwise, case,
    sum, avg, count, max, min,
    round, abs, sqrt,
    year, month, day, date_add,
    explode, array, map_keys, map_values,
    row_number, rank, dense_rank,
    lag, lead, first, last
)

# String
upper(col("name"))              # To uppercase
lower(col("name"))              # To lowercase
length(col("name"))             # String length
substr(col("name"), 1, 3)       # Substring
concat(col("first"), col("last")) # Concatenate
trim(col("name"))               # Remove spaces

# Math
round(col("salary"), 2)         # Round to 2 decimals
abs(col("value"))               # Absolute value

# Conditional
when(col("age") > 25, "Adult").otherwise("Child")
when(col("status") == "active", 1).otherwise(0)

# Case statement
when(col("dept") == "IT", 1)
  .when(col("dept") == "HR", 2)
  .otherwise(0)

# Null handling
coalesce(col("email"), col("phone"), "N/A")
col("age").isNull()
col("age").isNotNull()

# Date/Time
year(col("date"))
month(col("date"))
day(col("date"))
date_add(col("date"), 7)

# Window functions
row_number().over(Window.partitionBy("dept").orderBy("salary"))
rank().over(Window.orderBy("salary"))
lag(col("salary")).over(Window.partitionBy("dept"))
```

---

## WINDOW FUNCTIONS

```python
from pyspark.sql.functions import row_number, rank, dense_rank, lag, lead
from pyspark.sql.window import Window

# Define window
w = Window.partitionBy("department").orderBy("salary")

# Row number (1, 2, 3...)
df.withColumn("rn", row_number().over(w))

# Rank (1, 1, 3...)
df.withColumn("rank", rank().over(w))

# Dense rank (1, 1, 2...)
df.withColumn("dense_rank", dense_rank().over(w))

# Lag/Lead (previous/next row)
df.withColumn("prev_salary", lag("salary").over(w))
df.withColumn("next_salary", lead("salary").over(w))
```

---

## DATA QUALITY PATTERNS

```python
from pyspark.sql.functions import isnull, isnan, when, col

# Completeness
df.filter(col("email").isNull()).count()

# Uniqueness
df.groupBy("email").count().filter("count > 1")

# Validity
df.filter(~col("email").rlike("^[A-Za-z0-9._%+-]+@"))

# Accuracy
df.filter(col("total") != col("quantity") * col("price"))

# Timeliness
df.filter(col("load_time") > "1 hour")

# Duplicates
df.dropDuplicates(["email"])

# Quality report
quality = df.select([
    ((df.count() - sum(isnull(col(c)).cast("int"))) / df.count() * 100)
    .alias(f"{c}_completeness")
    for c in df.columns
])
```

---

## OPTIMIZATION TIPS

```python
# Cache (keep in memory)
df.cache()
df.persist()
df.unpersist()

# Repartition (parallel processing)
df.repartition(100)
df.repartitionByRange(100, col("date"))

# Coalesce (reduce partitions)
df.coalesce(10)

# Broadcast (send small data to executors)
broadcast_df = broadcast(small_df)

# Use parquet (compressed, columnar)
df.write.parquet("path")

# Select only needed columns
df.select("name", "age")  # Not df.select("*")

# Filter early (push down filters)
df.filter(...).select(...)  # Not df.select(...).filter(...)

# Avoid shuffle
df.filter(...).count()  # Good
df.groupBy(...).count()  # Causes shuffle, necessary

# Use SQL (Catalyst optimizes)
spark.sql("SELECT...")  # Better than RDD
```

---

## COMMON MISTAKES

```python
# ❌ WRONG: collect() on large data
result = df.collect()  # CRASH!

# ✅ RIGHT: Use show() or save
df.show()
df.write.parquet("path")

# ❌ WRONG: Select all then filter
df.select("*").filter(...)

# ✅ RIGHT: Filter then select specific
df.filter(...).select("name", "age")

# ❌ WRONG: Map on RDD (slow)
rdd.map(...).collect()

# ✅ RIGHT: Use DataFrame (fast)
df.select(...).show()

# ❌ WRONG: Forget transformation is lazy
df.filter(...)  # Does nothing
# Action needed!
df.filter(...).show()

# ❌ WRONG: Use RDD for structured data
sc.parallelize(data)

# ✅ RIGHT: Use DataFrame
spark.createDataFrame(data, schema)
```

---

## COMMAND LINE

```bash
# Submit Spark job
spark-submit \
    --master yarn \
    --deploy-mode cluster \
    --driver-memory 2g \
    --executor-memory 4g \
    --executor-cores 4 \
    --num-executors 10 \
    my_app.py

# PySpark shell (interactive)
pyspark

# SQL shell
spark-sql

# Check version
spark-shell --version
```

---

## CONFIGURATION

```python
spark = SparkSession.builder \
    .appName("MyApp") \
    .master("local[*]") \
    .config("spark.executor.memory", "4g") \
    .config("spark.executor.cores", "4") \
    .config("spark.driver.memory", "2g") \
    .config("spark.sql.shuffle.partitions", "200") \
    .config("spark.default.parallelism", "4") \
    .getOrCreate()

# Via spark-submit
# spark-submit --executor-memory 4g app.py

# spark-defaults.conf
# spark.executor.memory 4g
# spark.executor.cores 4
```

---

## COMMON FILE FORMATS

```python
# Parquet (BEST for Spark)
df.write.parquet("path")
df = spark.read.parquet("path")

# CSV
df.write.csv("path", header=True)
df = spark.read.csv("path", header=True, inferSchema=True)

# JSON
df.write.json("path")
df = spark.read.json("path")

# ORC
df.write.orc("path")
df = spark.read.orc("path")

# Text
df.write.text("path")
df = spark.read.text("path")
```

---

## USEFUL UTILITIES

```python
# Repartition based on row count
from pyspark.sql.functions import spark_partition_id
df.withColumn("partition", spark_partition_id()).groupBy("partition").count()

# Check memory usage
df.cache()
df.count()
# Check Spark UI: localhost:4040

# Explain query plan
df.explain()
df.explain(extended=True)

# Convert to pandas
pdf = df.toPandas()  # Warning: must fit in driver memory

# Convert from pandas
df = spark.createDataFrame(pdf)

# Get execution statistics
df.show()
# Check Spark UI for DAG and metrics
```

---

## SPARK UI

```
URL: http://localhost:4040 (while app running)

View:
- Jobs: Overall progress
- Stages: Intermediate results
- Tasks: Individual computations
- Executor: Memory, CPU, network
- Storage: Cached data
- Environment: Configuration
- SQL: SQL execution plans

Tips:
- Look for slow stages
- Check for data skew
- Monitor memory usage
- Find shuffle operations
```

---

## DEBUGGING

```python
# Print to log
import logging
logging.basicConfig(level=logging.INFO)

# See query plan
df.explain()

# Check partition count
df.rdd.getNumPartitions()

# Sample data
df.sample(0.01).show()

# Collect small portion
df.limit(10).collect()

# Print execution time
import time
start = time.time()
result = df.count()
print(f"Time: {time.time() - start}s")
```

---

## MEMORY ERRORS

```
Error: "java.lang.OutOfMemoryError"

Solutions:
1. Increase executor memory: --executor-memory 8g
2. Reduce data: Use filter() first
3. Repartition: More partitions = less per executor
4. Use Parquet: Better compression
5. Cache less data: df.unpersist()
6. Increase partitions: df.repartition(200)
```

---

## QUICK REFERENCE TABLE

| Task | Code |
|------|------|
| Load CSV | `spark.read.csv("file.csv", header=True)` |
| Load Parquet | `spark.read.parquet("file.parquet")` |
| Show data | `df.show()` |
| Count rows | `df.count()` |
| Select columns | `df.select("col1", "col2")` |
| Filter | `df.filter(df.age > 25)` |
| Group & count | `df.groupBy("dept").count()` |
| Join | `df1.join(df2, "key")` |
| Aggregate | `df.agg(avg("salary"))` |
| Sort | `df.sort("age")` |
| Remove duplicates | `df.distinct()` |
| SQL query | `spark.sql("SELECT ...")` |
| Cache | `df.cache()` |
| Save | `df.write.parquet("path")` |

---

## KEY SHORTCUTS

```python
col = pyspark.sql.functions.col
w = pyspark.sql.window.Window
F = pyspark.sql.functions

# Make imports easier
from pyspark.sql.functions import *
from pyspark.sql.window import Window as W
```

---

## MOST USED PATTERNS

```python
# Pattern 1: Filter & Select
df.filter(df.age > 25).select("name", "salary")

# Pattern 2: Group & Aggregate
df.groupBy("dept").agg(avg("salary"), count("*"))

# Pattern 3: Join
df1.join(df2, on="key").select(...)

# Pattern 3: SQL
spark.sql("SELECT ... FROM ... WHERE ...")

# Pattern 4: Cache & Reuse
df.cache()
result1 = df.filter(...).count()
result2 = df.select(...).show()

# Pattern 5: Quality Check
df.groupBy(df.columns).count().filter("count > 1")
```

---

**Save this for quick reference! 🚀**

*Last Updated: 2026-07-29*
