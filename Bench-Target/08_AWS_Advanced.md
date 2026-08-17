# AWS Advanced - Data Engineering Mastery

## AWS DATA SERVICES OVERVIEW

```
┌─────────────────────────────────────────────────────┐
│           DATA SOURCES (On-Prem/APIs)               │
└──────────────────────┬────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│      DATA INGESTION (Kinesis, Glue Crawler)         │
└──────────────────────┬────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│         DATA LAKE STORAGE (S3)                       │
│  Raw: s3://data-lake/raw/                           │
│  Processed: s3://data-lake/processed/               │
│  Cost: $0.023/GB/month                              │
└──────────────────────┬────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  DATA PROCESSING (Spark, Glue, Lambda)              │
│  EMR: Hadoop/Spark cluster                          │
│  Glue: Serverless ETL                               │
└──────────────────────┬────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│      DATA WAREHOUSE (Redshift, Athena)              │
│  Redshift: Fast, expensive, for frequent queries    │
│  Athena: Cheap, slow, for ad-hoc queries            │
└──────────────────────┬────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  CONSUMPTION (QuickSight, BI Tools, APIs)           │
└──────────────────────────────────────────────────────┘
```

---

## S3 (SIMPLE STORAGE SERVICE)

### Optimal Organization

```
Bucket structure:
s3://company-data-lake/
├── raw/
│   ├── crm/
│   │   ├── year=2024/month=01/day=15/
│   │   │   ├── customers_001.parquet
│   │   │   ├── customers_002.parquet
│   │   ├── year=2024/month=01/day=16/
│   ├── erp/
│   │   ├── year=2024/month=01/day=15/
│   ├── api/
│
├── processed/
│   ├── customer_master/
│   │   ├── year=2024/month=01/day=15/
│   │   │   └── customer_master_v1.parquet
│   ├── orders_summary/
│
├── analytics/
│   ├── reports/
│   ├── dashboards/
│
└── archive/
    └── old_data_2023/

Advantages:
✓ Partitioning by date: Query only what you need
✓ Format: Parquet (compressed, fast queries)
✓ Lifecycle: Move to Archive after 1 year (cost: $0.004/GB)
✓ Versioning: Track changes
✓ Cost: Raw = expensive to query, move to archive early
```

### S3 Lifecycle Policies

```python
# Move old data to cheaper storage
import boto3

s3 = boto3.client('s3')

lifecycle_policy = {
    'Rules': [
        {
            'Id': 'Archive old raw data',
            'Status': 'Enabled',
            'Filter': {'Prefix': 'raw/'},
            'Transitions': [
                {
                    'Days': 30,
                    'StorageClass': 'STANDARD_IA'  # Cost: $0.0125/GB
                },
                {
                    'Days': 90,
                    'StorageClass': 'GLACIER'  # Cost: $0.004/GB
                }
            ],
            'Expiration': {'Days': 365}  # Delete after 1 year
        }
    ]
}

s3.put_bucket_lifecycle_configuration(
    Bucket='company-data-lake',
    LifecycleConfiguration=lifecycle_policy
)

# Cost example:
# 1GB stored 1 month in STANDARD: $0.023
# 1GB after 1 year in GLACIER: $0.004 (5x cheaper!)
```

---

## EMR (ELASTIC MAPREDUCE)

### Cluster Configuration

```python
import boto3

emr = boto3.client('emr')

# Create cluster
response = emr.create_cluster(
    Name='production-etl-cluster',
    ReleaseLabel='emr-6.13.0',
    Instances={
        'MasterNodeType': 'm5.2xlarge',    # Master node
        'SlaveNodeType': 'm5.2xlarge',     # Worker nodes
        'InstanceCount': 10,               # Total: 1 master + 9 workers
        'AutoScalingGroupConfiguration': {
            'MinSize': 2,
            'MaxSize': 20
        },
        'KeepJobFlowAliveWhenNoSteps': True  # Persistent cluster
    },
    Applications=[
        {'Name': 'Spark'},
        {'Name': 'Hadoop'},
        {'Name': 'Hive'}
    ],
    LogUri='s3://logs-bucket/emr/',
    JobFlowRole='EMR_EC2_DefaultRole',
    ServiceRole='EMR_DefaultRole',
    Configurations=[
        {
            'Classification': 'spark',
            'ConfigurationProperties': {
                'maximizeResourceAllocation': 'true'
            }
        }
    ]
)

# Submit Spark job
emr.add_job_flow_steps(
    JobFlowId=response['JobFlowId'],
    Steps=[{
        'Name': 'daily-etl',
        'ActionOnFailure': 'CONTINUE',
        'HadoopJarStep': {
            'Jar': 'command-runner.jar',
            'Args': [
                'spark-submit',
                's3://scripts-bucket/etl.py',
                '--date', '2024-01-15'
            ]
        }
    }]
)

# Cost example:
# m5.2xlarge: $0.44/hour
# 10 nodes * $0.44 = $4.40/hour
# 24/7 = $106/day
# With on-demand: $3,200/month
# With spot (70% discount): $960/month
```

---

## GLUE (SERVERLESS ETL)

### Glue Job

```python
# Python script running on AWS Glue

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

# Setup
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'date'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# Extract from S3
customers = glueContext.create_dynamic_frame.from_options(
    format_options={'multiline': False},
    connection_type='s3',
    format='parquet',
    connection_options={'paths': [f's3://data-lake/raw/customers/{args["date"]}']},
    transformation_ctx='customers'
)

# Transform
customers_df = customers.toDF()
transformed = customers_df.withColumn('name', F.upper('name'))

# Load to S3
output_path = f's3://data-lake/processed/customers/{args["date"]}'
glueContext.write_dynamic_frame.from_options(
    frame=DynamicFrame.fromDF(transformed, glueContext, 'output'),
    connection_type='s3',
    format='parquet',
    connection_options={'path': output_path},
    transformation_ctx='output'
)

job.commit()

# Schedule in Glue
# Jobs > Create Job > Trigger > Scheduled (Daily at 2 AM)
# Cost: $0.44/DPU-hour (cheaper than EMR for simple jobs!)
```

### Glue Data Catalog

```python
# Crawler: Auto-discover schema
glue = boto3.client('glue')

glue.create_crawler(
    Name='s3-data-crawler',
    Role='service-role/AWSGlueServiceRole',
    DatabaseName='data_lake',
    Targets={
        'S3Targets': [
            {'Path': 's3://data-lake/raw/'}
        ]
    },
    SchemaChangePolicy={
        'UpdateBehavior': 'UPDATE_IN_DATABASE',
        'DeleteBehavior': 'LOG'
    },
    Schedule='cron(0 1 * * ? *)'  # Daily 1 AM
)

# Crawler creates/updates tables automatically:
# Table: customers (from s3://data-lake/raw/customers/)
# - Column: id (int)
# - Column: name (string)
# - Partitions: year, month, day

# Query with Athena
# SELECT * FROM data_lake.customers WHERE year=2024 AND month=1
```

---

## REDSHIFT (DATA WAREHOUSE)

### Setup & Optimization

```python
import boto3

redshift = boto3.client('redshift')

# Create cluster
response = redshift.create_cluster(
    ClusterIdentifier='analytics-warehouse',
    NodeType='ra3.yplusx',  # Latest, best performance
    NumberOfNodes=3,         # 3 nodes for HA
    MasterUsername='admin',
    DBName='analytics',
    
    # Optimization
    EnhancedVpcRouting=True,
    PreferredMaintenanceWindow='sun:03:00-sun:04:00',
    
    # Auto-scaling
    SkipFinalClusterSnapshot=False
)

# Cost:
# ra3.yplusx: $4.26/hour
# 3 nodes: $12.78/hour = $307/day = $9,240/month
```

### Redshift Query Performance

```sql
-- Compression (reduces storage)
-- Choose encoding based on column type:
-- - INT: Usually no compression (fast)
-- - VARCHAR: Use TEXT255 or TEXT32K (saves space)
-- - DATE: Use DELTA (saves 75%)

CREATE TABLE sales (
  order_id INT,
  customer_id INT ENCODE DELTA,
  order_date DATE ENCODE DELTA,
  amount DECIMAL(10,2) ENCODE RAW,
  product_name VARCHAR(100) ENCODE TEXT255
);

-- Distribution key (how to split across nodes)
CREATE TABLE sales (
  order_id INT PRIMARY KEY,
  customer_id INT,  -- DISTSTYLE KEY
  amount DECIMAL
)
DISTSTYLE KEY
DISTKEY (customer_id);  -- Distribute by customer (for joins)

-- Sort key (fast range scans)
CREATE TABLE sales (
  order_id INT,
  order_date DATE,
  amount DECIMAL
)
SORTKEY (order_date);  -- Sort by date for time-range queries

-- Query optimization
VACUUM;        -- Reclaim space, reorder rows
ANALYZE;       -- Update statistics for query planner
EXPLAIN SELECT ... -- See execution plan
```

---

## ATHENA (SQL ON S3)

### Query Data Directly in S3

```python
import boto3

athena = boto3.client('athena')

# Query
response = athena.start_query_execution(
    QueryString='''
        SELECT 
            customer_id,
            COUNT(*) as num_orders,
            SUM(amount) as total_spent
        FROM s3_parquet_data
        WHERE year = 2024 AND month = 1
        GROUP BY customer_id
        ORDER BY total_spent DESC
    ''',
    QueryExecutionContext={'Database': 'default'},
    ResultConfiguration={
        'OutputLocation': 's3://query-results/'
    },
    WorkGroup='primary'
)

# Cost: $5 per TB scanned!
# Example: Scan 100GB = $0.50
# Much cheaper than Redshift for ad-hoc queries!

# Optimization: Use Parquet + Partitioning
# Parquet compression: 4x smaller (scan 25GB instead of 100GB)
# Partitioning: Only scan Jan data (scan 8GB instead of 100GB)
# Result: $0.50 → $0.02 (25x cheaper!)
```

---

## LAMBDA (SERVERLESS FUNCTIONS)

### Data Processing Trigger

```python
import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    """
    Triggered when file uploaded to S3
    Process and move to processed folder
    """
    
    # Get file details
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    try:
        # Process file
        response = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(response['Body'].read())
        
        # Validate
        if not validate_data(data):
            raise ValueError("Data validation failed!")
        
        # Transform
        processed = transform_data(data)
        
        # Save to processed folder
        processed_key = key.replace('raw/', 'processed/')
        s3.put_object(
            Bucket=bucket,
            Key=processed_key,
            Body=json.dumps(processed)
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success'})
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def validate_data(data):
    # Validation logic
    return True

def transform_data(data):
    # Transformation logic
    return data

# Cost: $0.20 per 1M invocations
# 10M invocations/month = $2/month (FREE tier covers 1M free!)
```

---

## CLOUDWATCH MONITORING

### Monitor Data Pipelines

```python
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def log_pipeline_metrics(job_name, duration_seconds, records_processed, status):
    """Log custom metrics"""
    
    cloudwatch.put_metric_data(
        Namespace='DataPipeline',
        MetricData=[
            {
                'MetricName': 'JobDuration',
                'Value': duration_seconds,
                'Unit': 'Seconds',
                'Dimensions': [
                    {'Name': 'JobName', 'Value': job_name}
                ]
            },
            {
                'MetricName': 'RecordsProcessed',
                'Value': records_processed,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'JobName', 'Value': job_name}
                ]
            },
            {
                'MetricName': 'JobStatus',
                'Value': 1 if status == 'SUCCESS' else 0,
                'Unit': 'None',
                'Dimensions': [
                    {'Name': 'JobName', 'Value': job_name}
                ]
            }
        ]
    )

# Create alarm
cloudwatch.put_metric_alarm(
    AlarmName='etl-job-failed',
    MetricName='JobStatus',
    Namespace='DataPipeline',
    Statistic='Average',
    Period=3600,  # 1 hour
    Threshold=1,  # Alarm if < 1 (job failed)
    ComparisonOperator='LessThanThreshold',
    AlarmActions=['arn:aws:sns:us-east-1:123456789:alerts']
)

# Set up SNS for notifications
sns = boto3.client('sns')
sns.publish(
    TopicArn='arn:aws:sns:us-east-1:123456789:alerts',
    Subject='ETL Job Failed',
    Message=f'Job {job_name} failed at {datetime.now()}'
)
```

---

## COST OPTIMIZATION

### Strategies

```
1. STORAGE COSTS:
   - S3 Standard: $0.023/GB
   - S3 IA: $0.0125/GB (70 days+)
   - Glacier: $0.004/GB (1 year+)
   → Use lifecycle policies to move old data
   → Savings: 80% on 1-year-old data

2. COMPUTE COSTS:
   - On-demand: Full price
   - Spot instances: 70% discount
   - Reserved instances: 40% discount
   → Use spot for non-critical, resilient workloads
   → Use reserved for baseline always-running

3. QUERY COSTS (Athena):
   - $5 per TB scanned
   - Parquet: 4x compression
   - Partitioning: 10-100x reduction
   → Only scan needed data
   → Savings: 90% with optimization

4. REDSHIFT vs ATHENA:
   - Redshift: $10K/month for 3 nodes
   - Ad-hoc queries: Use Athena ($0.05 per query)
   - Frequent queries: Use Redshift (amortized cost lower)

EXAMPLE OPTIMIZATION:
Before: 100 Glue jobs/day * $0.44 = $44/day = $1,320/month
After: 50 Lambda functions + 50 Glue = $0.10 + $22 = $22.10/day = $663/month
Savings: 50% ($650/month!)
```

---

## INTERVIEW QUESTIONS

### Q1: Design ETL for 100GB daily data on AWS

**Answer:**
```
ARCHITECTURE:
1. DATA SOURCE: S3 or API
   └─ Ingest to s3://data-lake/raw/

2. PROCESSING:
   Option A: Glue (simpler, cheaper)
   - Serverless, auto-scales
   - Cost: ~$100/month for 100GB

   Option B: EMR (complex, more control)
   - For heavy transformations
   - Cost: ~$1,000/month (always-on)

3. STORAGE:
   - Data Lake: S3 ($0.023/GB)
   - Warehouse: Athena (pay per query)

4. CONSUMPTION:
   - QuickSight dashboards
   - BI tools via Redshift

RECOMMENDATION:
- Small transforms: Use Glue (cheaper)
- Complex transforms: Use EMR (flexible)
- Ad-hoc queries: Use Athena (cheap)
```

### Q2: Optimize AWS data pipeline costs

**Answer:**
```
1. COMPRESSION:
   - Store as Parquet (4x smaller)
   - Saves: 75% on storage

2. PARTITIONING:
   - Query only needed time period
   - Saves: 90% on scan costs

3. LIFECYCLE POLICIES:
   - Move to Glacier after 1 year
   - Saves: 80% on old data storage

4. SPOT INSTANCES:
   - Use for non-critical jobs
   - Saves: 70% on compute

5. SERVERLESS:
   - Glue vs EMR for simple jobs
   - Saves: 80% vs always-on EMR

COMBINED SAVINGS: 70-90% possible!
```

---

## KEY TAKEAWAYS

1. **S3**: Cost-effective storage, use partitioning
2. **Glue**: Serverless ETL, best for simple jobs
3. **EMR**: For complex Spark jobs, control
4. **Redshift**: Fast warehouse, expensive
5. **Athena**: Ad-hoc SQL, pay per GB scanned
6. **Lambda**: Serverless triggers, very cheap
7. **CloudWatch**: Monitor everything
8. **Optimization**: Compression, partitioning, lifecycle policies = 70-90% savings

---

*Last Updated: 2026-07-29*
*Level: Intermediate to Advanced (4 → 5)*
