# Python Advanced - Production-Ready Code

## CORE ADVANCED CONCEPTS

### 1. **Decorators** (Functions as Arguments)
```python
# Simple decorator
def timer(func):
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.time()-start}s")
        return result
    return wrapper

@timer
def slow_function():
    import time
    time.sleep(1)
    return "Done"

slow_function()  # Logs execution time automatically

# REAL EXAMPLE: Data Quality decorator
def validate_data(func):
    def wrapper(df):
        if df.empty:
            raise ValueError("Empty dataframe!")
        if df.isnull().sum().sum() > len(df) * 0.1:
            raise ValueError("Too many nulls!")
        return func(df)
    return wrapper

@validate_data
def process_data(df):
    return df.groupby('category').sum()
```

### 2. **Context Managers** (With Statement)
```python
# Safe file handling
with open('data.csv', 'r') as f:
    data = f.read()
# File automatically closes

# Custom context manager
class DatabaseConnection:
    def __enter__(self):
        print("Connecting...")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Disconnecting...")
        if exc_type:
            print(f"Error: {exc_type}")
        return False

with DatabaseConnection() as db:
    # Use db
    pass
# Automatically disconnects

# REAL EXAMPLE: Spark session
from pyspark.sql import SparkSession

class SparkManager:
    def __enter__(self):
        self.spark = SparkSession.builder \
            .appName("ETL") \
            .getOrCreate()
        return self.spark
    
    def __exit__(self, *args):
        self.spark.stop()

with SparkManager() as spark:
    df = spark.read.parquet("s3://data")
# Spark stops automatically
```

### 3. **Generators** (Memory Efficient)
```python
# Process 1GB file without loading to memory
def read_large_file(filepath, chunk_size=1000):
    """Yield chunks of file"""
    with open(filepath) as f:
        chunk = []
        for line in f:
            chunk.append(line)
            if len(chunk) == chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

# Use it
for chunk in read_large_file("1gb_file.csv"):
    process_chunk(chunk)
# Only 1000 lines in memory at a time!

# REAL EXAMPLE: Batch Spark writes
def batch_generator(df, batch_size=10000):
    """Generate batches for insertion"""
    total = df.count()
    for i in range(0, total, batch_size):
        batch = df.limit(i + batch_size).subtract(df.limit(i))
        yield batch
```

### 4. **List Comprehensions** (Pythonic)
```python
# Slow
result = []
for x in range(10):
    if x % 2 == 0:
        result.append(x ** 2)

# Fast and Pythonic
result = [x**2 for x in range(10) if x % 2 == 0]

# Nested comprehension
matrix = [[i+j for j in range(3)] for i in range(3)]

# Dict comprehension
data = ['a,1', 'b,2', 'c,3']
result = {item[0]: int(item[1]) for item in [x.split(',') for x in data]}
```

### 5. **Lambda Functions** (Inline Functions)
```python
# Instead of:
def get_price(item):
    return item['price']

prices = list(map(get_price, items))

# Use:
prices = list(map(lambda x: x['price'], items))

# REAL EXAMPLE: Pandas transformations
import pandas as pd

df = pd.DataFrame({'price': [100, 200, 300]})

# Traditional
df['discounted'] = df.apply(lambda x: x['price'] * 0.9, axis=1)

# Filter
expensive = df[df['price'].apply(lambda x: x > 150)]
```

### 6. **Class Methods & Static Methods**
```python
class DataProcessor:
    count = 0
    
    @staticmethod
    def validate_email(email):
        """Don't need self, utility function"""
        return '@' in email
    
    @classmethod
    def create_from_config(cls, config_file):
        """Constructor from config"""
        config = load_config(config_file)
        return cls(config['name'], config['path'])
    
    def __init__(self, name, path):
        self.name = name
        self.path = path
        DataProcessor.count += 1

# Use
if DataProcessor.validate_email("user@example.com"):
    print("Valid")

processor = DataProcessor.create_from_config("config.json")
```

### 7. **Exception Handling** (Robust)
```python
# GOOD: Specific exceptions
try:
    df = spark.read.parquet("s3://data")
except FileNotFoundError:
    print("File not found, creating empty df")
    df = spark.createDataFrame([])
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise

# BAD: Generic exception
try:
    df = spark.read.parquet("s3://data")
except:  # Catches everything!
    pass  # Hides errors

# REAL EXAMPLE: Data loading with fallback
def load_data(primary_path, fallback_path):
    try:
        return spark.read.parquet(primary_path)
    except FileNotFoundError:
        logger.warning(f"Primary failed, using fallback")
        return spark.read.parquet(fallback_path)
    except Exception as e:
        logger.critical(f"Both paths failed: {e}")
        raise
```

---

## PANDAS MASTERY

### Efficient Data Manipulation
```python
import pandas as pd
import numpy as np

df = pd.read_csv("data.csv")

# Efficient filtering (don't use .iterrows()!)
# SLOW
for idx, row in df.iterrows():
    if row['age'] > 25:
        process(row)

# FAST: Vectorized
mask = df['age'] > 25
for idx, row in df[mask].iterrows():
    process(row)

# FASTEST: Apply
df[mask].apply(process, axis=1)

# Group and transform
df['age_group'] = df.groupby('city')['age'].transform('mean')

# Merge (join)
result = df1.merge(df2, on='customer_id', how='left')

# Pivot
pivot = df.pivot_table(
    index='date',
    columns='category',
    values='sales',
    aggfunc='sum'
)

# Chaining (clean code)
result = (df
    .query('age > 25')
    .groupby('category')['amount'].sum()
    .sort_values(ascending=False)
    .head(10)
)
```

---

## BEST PRACTICES

### 1. **Type Hints**
```python
from typing import List, Dict, Optional

def process_customers(
    df: pd.DataFrame,
    min_age: int = 18
) -> Dict[str, float]:
    """
    Process customer data.
    
    Args:
        df: Customer dataframe
        min_age: Minimum age filter
    
    Returns:
        Dictionary with statistics
    """
    filtered = df[df['age'] >= min_age]
    return {
        'count': len(filtered),
        'avg_age': filtered['age'].mean()
    }
```

### 2. **Logging**
```python
import logging

# Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use
logger.info(f"Processing {len(df)} rows")
logger.warning("Low data quality detected")
logger.error(f"Failed to load from {path}")

# Don't use print() in production!
# Use logger instead
```

### 3. **Testing**
```python
import unittest

class TestDataProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = DataProcessor()
    
    def test_validate_email(self):
        self.assertTrue(self.processor.validate_email("test@example.com"))
        self.assertFalse(self.processor.validate_email("invalid"))
    
    def test_process_empty_data(self):
        df = pd.DataFrame()
        result = self.processor.process(df)
        self.assertEqual(len(result), 0)

if __name__ == '__main__':
    unittest.main()
```

---

## PERFORMANCE OPTIMIZATION

### Vectorization vs Loops
```python
# Data
df = pd.DataFrame({'value': range(1000000)})

# SLOW: Loop (10+ seconds)
result = []
for i in range(len(df)):
    result.append(df.iloc[i]['value'] * 2)

# FAST: Vectorized (0.1 seconds = 100x faster!)
result = df['value'] * 2

# BENCHMARK
import timeit

loop_time = timeit.timeit(
    lambda: [x * 2 for x in df['value']],
    number=100
)

vector_time = timeit.timeit(
    lambda: df['value'] * 2,
    number=100
)

print(f"Loop: {loop_time}s, Vector: {vector_time}s")
# Result: Vector is 10-50x faster!
```

---

## KEY TAKEAWAYS

1. **Use decorators** for cross-cutting concerns
2. **Context managers** for resource management
3. **Generators** for memory-efficient processing
4. **List comprehensions** for clean code
5. **Type hints** for code clarity
6. **Logging** not print()
7. **Unit tests** for reliability
8. **Vectorization** for speed

---

*Last Updated: 2026-07-29*
