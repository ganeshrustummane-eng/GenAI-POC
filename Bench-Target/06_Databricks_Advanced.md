# Databricks - Production Deployment & Optimization

## DATABRICKS ARCHITECTURE

### Compute Cluster Setup

```python
# Cluster Configuration (JSON)
{
  "cluster_name": "production-etl",
  "spark_version": "13.3.x-scala2.12",
  "node_type_id": "i3.xlarge",  # Instance type
  "num_workers": 10,  # Scales from 1-100
  
  # Auto-scaling
  "autoscale": {
    "min_workers": 2,
    "max_workers": 20
  },
  
  # Optimization
  "spark_conf": {
    "spark.databricks.delta.preview.enabled": "true",
    "spark.sql.adaptive.enabled": "true",  # Adaptive query execution
    "spark.sql.shuffle.partitions": "200"
  },
  
  # Storage
  "ebs_volume_count": 1,
  "ebs_volume_size": 100,  # GB
  
  # Timeout
  "idle_timeout_minutes": 30  # Auto-terminate after 30 min idle
}

# Cost optimization:
# - Use smaller instances for dev (lower cost)
# - Auto-scaling: Only pay for what you use
# - Spot instances: Up to 70% cheaper (if acceptable)
# - Jobs cluster: Terminate after job completes
```

### Jobs Configuration

```python
# Define job in Databricks UI or API

# Daily ETL Job
{
  "name": "daily_customer_etl",
  "cluster_id": "production-etl",
  "spark_python_task": {
    "python_file": "s3://repo/etl/customer_etl.py",
    "parameters": ["--date", "2024-01-15"]
  },
  "schedule": {
    "quartz_cron_expression": "0 0 2 * * ?",  # 2 AM daily
    "timezone_id": "US/Eastern"
  },
  "timeout_seconds": 3600,  # 1 hour max
  "max_retries": 2
}

# Monitor job execution
GET /api/2.1/jobs/get-run
GET /api/2.1/jobs/runs/list
```

---

## DELTA LAKE FEATURES

### ACID Transactions

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("DeltaLake").getOrCreate()

# Create Delta table
df.write.mode("overwrite").format("delta").save("s3://data/customers")

# Read Delta table
df = spark.read.format("delta").load("s3://data/customers")

# ACID Update (not possible with Parquet!)
from delta.tables import DeltaTable

deltaTable = DeltaTable.forPath(spark, "s3://data/customers")
deltaTable.update(
    condition="id = 1",
    set={"name": "John Updated", "updated_at": "2024-01-15"}
)

# Delete with condition
deltaTable.delete("status = 'inactive'")

# Merge (Upsert)
updates = spark.createDataFrame([
    (1, "Alice", "active"),
    (2, "Bob", "inactive")
], ["id", "name", "status"])

deltaTable.alias("existing").merge(
    updates.alias("updates"),
    "existing.id = updates.id"
).whenMatchedUpdate(set={
    "name": col("updates.name"),
    "status": col("updates.status")
}).whenNotMatchedInsert(values={
    "id": col("updates.id"),
    "name": col("updates.name"),
    "status": col("updates.status")
}).execute()

# Time travel (query past versions!)
df_yesterday = spark.read.format("delta") \
    .option("timestampAsOf", "2024-01-14") \
    .load("s3://data/customers")

# Optimization
deltaTable.optimize().executeCompaction()
```

---

## SECURITY & GOVERNANCE

### Access Control

```python
# Using SQL in Databricks
CREATE SCHEMA finance;
GRANT SELECT ON SCHEMA finance TO `data-analysts@company.com`;
GRANT MODIFY, OWNER ON SCHEMA finance TO `finance-lead@company.com`;

# Table-level access
GRANT SELECT ON TABLE finance.transactions TO `data-analysts@company.com`;

# Column-level access (newer feature)
CREATE TABLE finance.sensitive (
    id INT,
    customer_name STRING MASK MASK_HASH(),  # Hash PII
    ssn STRING MASK WITH (CASE WHEN is_member('data-scientists') THEN ssn ELSE '***-**-****' END)
)

# Unity Catalog (enterprise governance)
CREATE CATALOG company_data;
CREATE SCHEMA company_data.raw;
CREATE SCHEMA company_data.processed;

GRANT USAGE ON CATALOG company_data TO `data-team@company.com`;
```

### Data Lineage & Quality

```python
# Track data lineage
import logging

logger = logging.getLogger("data_pipeline")

def load_data(source_path):
    logger.info(f"Loading from {source_path}")
    df = spark.read.parquet(source_path)
    logger.info(f"Loaded {df.count()} rows")
    return df

def transform(df):
    logger.info("Starting transformation")
    df = df.filter(col("status") != "inactive")
    logger.info(f"After filter: {df.count()} rows")
    return df

def save_data(df, target_path):
    df.write.mode("overwrite").parquet(target_path)
    logger.info(f"Saved to {target_path}")

# Databricks tracks this automatically in Jobs > Runs
```

---

## PERFORMANCE OPTIMIZATION

### Auto Optimize

```python
# Enable on cluster
spark.conf.set("spark.databricks.delta.autoOptimize.enabled", "true")

# Benefits:
# - Automatic file compaction
# - Optimal file size
# - 2-5x query speedup

# Manual optimization
DeltaTable.forPath(spark, "s3://data").optimize() \
    .executeCompaction()
```

### Caching Strategy

```python
# Cache in Databricks (built-in optimization)
df = spark.read.parquet("s3://large-data")
df.cache()  # Stores in Databricks cache

# Query 1: Loads from source (slow)
df.count()

# Query 2-N: Use cache (fast)
df.filter(...).count()

# When done
df.unpersist()

# Alternative: Use Databricks IO Cache
spark.conf.set("spark.databricks.io.cache.enabled", "true")
# Caches reads across multiple jobs
```

---

## REAL-WORLD ARCHITECTURE

### Production ETL Pipeline

```python
class DatabricksETL:
    def __init__(self, spark, config):
        self.spark = spark
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        try:
            # Extract
            self.logger.info("Starting ETL")
            df = self.extract()
            
            # Validate
            if not self.validate_quality(df):
                raise Exception("Quality checks failed!")
            
            # Transform
            df = self.transform(df)
            
            # Load
            self.load(df)
            
            self.logger.info("ETL completed successfully")
            
        except Exception as e:
            self.logger.error(f"ETL failed: {e}")
            # Send alert via Databricks notification
            raise
    
    def extract(self):
        # Read from Delta table (versioned, ACID)
        return self.spark.read.format("delta") \
            .load(f"s3://{self.config['source_path']}")
    
    def validate_quality(self, df):
        # Data quality checks
        total = df.count()
        if total == 0:
            return False
        
        # Check completeness
        null_pct = df.filter(col("id").isNull()).count() / total
        if null_pct > 0.01:
            return False
        
        return True
    
    def transform(self, df):
        # Complex transformations
        return df.withColumn("processed_date", F.current_date())
    
    def load(self, df):
        # Write to Delta (ACID, time travel, versioning)
        df.write.mode("overwrite").format("delta") \
            .option("mergeSchema", "true") \
            .save(f"s3://{self.config['target_path']}")

# Schedule in Databricks
# Jobs > Create Job > Run this notebook daily
```

---

## COST OPTIMIZATION

### Strategies

```
1. INSTANCE SELECTION:
   - Dev/Test: Use smaller instances (i3.xlarge = $0.30/hr)
   - Prod: Use optimized instances (i3.2xlarge = $0.70/hr)
   - Savings: 50-70% with right sizing

2. CLUSTER SCALING:
   - Min 2 workers: Baseline cost
   - Max 20 workers: Auto-scale up/down
   - Result: Pay only for what you use

3. SPOT INSTANCES:
   - On-demand: i3.xlarge = $0.30/hr
   - Spot: i3.xlarge = $0.10/hr (70% cheaper!)
   - Risk: Can be interrupted
   - Solution: Use for non-critical jobs

4. AUTO-TERMINATE:
   - idle_timeout_minutes: 30
   - Stops unused clusters
   - Cost example: 24/7 cluster = $175/month
                  30-min timeout = $40/month (77% savings!)

5. QUERY OPTIMIZATION:
   - Optimize queries FIRST (biggest impact)
   - Auto optimize Delta tables
   - Use partitioning
   - Result: 10x faster = 10x cheaper

EXAMPLE COST REDUCTION:
Before:
- 5 always-on clusters
- Large instances
- No optimization
- Cost: $20,000/month

After:
- 1 prod cluster (auto-scale)
- Right-sized instances
- Delta optimization
- Query optimization
- Cost: $3,000/month (85% reduction!)
```

---

## INTERVIEW QUESTIONS

### Q1: Design Databricks pipeline for 10TB daily data

**Answer:**
```
ARCHITECTURE:
1. Cluster: 
   - Type: i3.2xlarge for prod
   - Workers: Auto-scale 2-20
   - Timeout: 30 min idle

2. Storage:
   - Source: S3 (raw data)
   - Processing: Delta table (ACID)
   - Output: Delta table (Parquet format)

3. Optimization:
   - Partition by date
   - Enable auto-optimize
   - Use broadcast joins
   - Cache intermediate

4. Monitoring:
   - Databricks jobs UI
   - CloudWatch logs
   - Data quality metrics

5. Cost:
   - Spot instances: 70% cheaper
   - Auto-scale: Pay for 2-20 workers
   - Estimated: $500-1000/month

PERFORMANCE:
- Daily load: 10-30 minutes
- Queries: Sub-second (Delta optimized)
- Cost: Optimal for scale
```

### Q2: How to handle schema evolution in Delta?

**Answer:**
```
Problem:
- Source schema changes
- New column added
- Need to update Delta table

Solution:
mergeSchema = true

df.write.mode("append") \
    .option("mergeSchema", "true") \
    .format("delta") \
    .save("s3://data")

Benefits:
- New columns added automatically
- No manual schema updates
- Backward compatible
- Non-breaking changes supported

Example:
Original schema: id, name, email
New schema: id, name, email, phone_number
Result: Phone_number added, all existing data stays
```

---

## KEY TAKEAWAYS

1. **Use Delta Lake** - ACID, time travel, versioning
2. **Auto-scale clusters** - Pay only for what you use
3. **Enable auto-optimize** - 2-5x faster queries
4. **Cost optimization** - 70-85% savings possible
5. **Security** - Unity Catalog for governance
6. **Monitoring** - Jobs UI shows everything
7. **Time travel** - Query past versions
8. **Merge operations** - Upsert at scale

---

*Last Updated: 2026-07-29*
*Level: Intermediate to Advanced (3 → 4.5)*
