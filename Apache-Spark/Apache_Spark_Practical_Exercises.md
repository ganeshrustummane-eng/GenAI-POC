# Apache Spark - Practical Hands-On Exercises

## Prerequisites
```bash
# Install PySpark
pip install pyspark

# Or with conda
conda install pyspark
```

---

## EXERCISE 1: Basic RDD Operations

### Task 1.1: Create RDD and perform basic operations

```python
from pyspark import SparkContext

# Initialize Spark
sc = SparkContext("local", "RDD Exercise 1")

# Create RDD from collection
numbers = sc.parallelize([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

# Task 1: Count elements
count = numbers.count()
print(f"Total numbers: {count}")
# Expected: 10

# Task 2: Sum all numbers
total = numbers.sum()
print(f"Sum: {total}")
# Expected: 55

# Task 3: Get maximum
max_num = numbers.max()
print(f"Maximum: {max_num}")
# Expected: 10

# Task 4: Get minimum
min_num = numbers.min()
print(f"Minimum: {min_num}")
# Expected: 1

# Task 5: Get average
avg = numbers.mean()
print(f"Average: {avg}")
# Expected: 5.5

sc.stop()
```

**Your Turn:**
- [ ] Run the code above
- [ ] Add: Find all numbers greater than 5
- [ ] Add: Find all even numbers
- [ ] Add: Find all numbers divisible by 3

**Solution:**
```python
# Find numbers > 5
greater_than_5 = numbers.filter(lambda x: x > 5)
print(greater_than_5.collect())  # [6, 7, 8, 9, 10]

# Find even numbers
even = numbers.filter(lambda x: x % 2 == 0)
print(even.collect())  # [2, 4, 6, 8, 10]

# Find divisible by 3
divisible_by_3 = numbers.filter(lambda x: x % 3 == 0)
print(divisible_by_3.collect())  # [3, 6, 9]
```

---

## EXERCISE 2: Map and Transformation

### Task 2.1: Transform data

```python
from pyspark import SparkContext

sc = SparkContext("local", "Transformation Exercise")

# Create RDD of numbers
numbers = sc.parallelize([1, 2, 3, 4, 5])

# Task 1: Square each number
squared = numbers.map(lambda x: x ** 2)
print("Squared:", squared.collect())
# Expected: [1, 4, 9, 16, 25]

# Task 2: Convert to strings
string_nums = numbers.map(lambda x: f"Number: {x}")
print("Strings:", string_nums.collect())
# Expected: ['Number: 1', 'Number: 2', ...]

# Task 3: Create key-value pairs
pairs = numbers.map(lambda x: (x, x * 10))
print("Pairs:", pairs.collect())
# Expected: [(1, 10), (2, 20), (3, 30), ...]

sc.stop()
```

**Your Turn:**
- [ ] Create RDD of names: ["John", "Jane", "Bob"]
- [ ] Convert to uppercase
- [ ] Create key-value pairs: (name, length)

**Solution:**
```python
names = sc.parallelize(["John", "Jane", "Bob"])

# Uppercase
upper = names.map(lambda x: x.upper())
print(upper.collect())  # ['JOHN', 'JANE', 'BOB']

# Key-value pairs
name_length = names.map(lambda x: (x, len(x)))
print(name_length.collect())  # [('John', 4), ('Jane', 4), ('Bob', 3)]
```

---

## EXERCISE 3: FlatMap and Word Count

### Task 3.1: Word count (classic Spark example)

```python
from pyspark import SparkContext

sc = SparkContext("local", "Word Count")

# Create sentences
sentences = sc.parallelize([
    "hello world",
    "hello spark",
    "world spark"
])

# Task: Count each word

# Step 1: Split sentences into words
words = sentences.flatMap(lambda x: x.split())
print("Words:", words.collect())
# Expected: ['hello', 'world', 'hello', 'spark', 'world', 'spark']

# Step 2: Create key-value pairs (word, 1)
word_pairs = words.map(lambda x: (x, 1))
print("Pairs:", word_pairs.collect())
# Expected: [('hello', 1), ('world', 1), ('hello', 1), ...]

# Step 3: Sum counts by word
word_counts = word_pairs.reduceByKey(lambda x, y: x + y)
print("Word counts:", word_counts.collect())
# Expected: [('hello', 2), ('world', 2), ('spark', 2)]

sc.stop()
```

**Your Turn:**
- [ ] Create RDD of text lines
- [ ] Convert to words
- [ ] Count word frequency
- [ ] Sort by frequency

**Solution:**
```python
text = sc.parallelize([
    "spark is fast",
    "spark is easy",
    "fast easy"
])

words = text.flatMap(lambda x: x.split())
word_counts = words.map(lambda x: (x, 1)).reduceByKey(lambda x, y: x + y)

# Sort by count (descending)
sorted_counts = word_counts.sortBy(lambda x: x[1], ascending=False)
print(sorted_counts.collect())
# Expected: [('spark', 2), ('fast', 2), ('easy', 2), ('is', 2)]
```

---

## EXERCISE 4: DataFrame Basics

### Task 4.1: Create and manipulate DataFrames

```python
from pyspark.sql import SparkSession

# Initialize Spark
spark = SparkSession.builder.appName("DataFrame Exercise").getOrCreate()

# Create DataFrame from list of tuples
data = [
    ("John", 25, "IT", 5000),
    ("Jane", 30, "HR", 6000),
    ("Bob", 35, "IT", 5500),
    ("Alice", 28, "HR", 6500),
    ("Charlie", 32, "IT", 5800)
]

columns = ["Name", "Age", "Department", "Salary"]

df = spark.createDataFrame(data, columns)

# Task 1: Show data
print("=== Full DataFrame ===")
df.show()

# Task 2: Show schema
print("\n=== Schema ===")
df.printSchema()

# Task 3: Select columns
print("\n=== Name and Age ===")
df.select("Name", "Age").show()

# Task 4: Filter
print("\n=== Age > 25 ===")
df.filter(df.Age > 25).show()

# Task 5: Filter with multiple conditions
print("\n=== IT Department and Salary > 5500 ===")
df.filter((df.Department == "IT") & (df.Salary > 5500)).show()

spark.stop()
```

**Expected Output:**
```
=== Full DataFrame ===
+-------+---+----------+------+
|   Name|Age|Department|Salary|
+-------+---+----------+------+
|  John | 25|    IT    | 5000 |
|  Jane | 30|    HR    | 6000 |
|   Bob | 35|    IT    | 5500 |
| Alice | 28|    HR    | 6500 |
|Charlie| 32|    IT    | 5800 |
+-------+---+----------+------+
```

**Your Turn:**
- [ ] Add a new column for bonus (Salary * 0.1)
- [ ] Filter for salary > 5000
- [ ] Sort by age

**Solution:**
```python
from pyspark.sql.functions import col

# Add bonus column
df_with_bonus = df.withColumn("Bonus", col("Salary") * 0.1)
df_with_bonus.show()

# Filter salary > 5000
high_salary = df.filter(df.Salary > 5000)
high_salary.show()

# Sort by age (descending)
sorted_df = df.sort(col("Age").desc())
sorted_df.show()
```

---

## EXERCISE 5: GroupBy and Aggregation

### Task 5.1: Group and aggregate data

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, sum, count, max, min

spark = SparkSession.builder.appName("GroupBy Exercise").getOrCreate()

# Create employee data
data = [
    ("John", "IT", 5000),
    ("Jane", "HR", 6000),
    ("Bob", "IT", 5500),
    ("Alice", "HR", 6500),
    ("Charlie", "IT", 5800),
    ("Diana", "HR", 6200)
]

columns = ["Name", "Department", "Salary"]
df = spark.createDataFrame(data, columns)

print("=== Original Data ===")
df.show()

# Task 1: Count by department
print("\n=== Employee Count by Department ===")
df.groupBy("Department").count().show()
# Expected: IT=3, HR=3

# Task 2: Average salary by department
print("\n=== Average Salary by Department ===")
df.groupBy("Department").agg(avg("Salary").alias("AvgSalary")).show()
# Expected: IT≈5433, HR≈6233

# Task 3: Multiple aggregations
print("\n=== Department Statistics ===")
df.groupBy("Department").agg(
    count("*").alias("Count"),
    avg("Salary").alias("AvgSalary"),
    max("Salary").alias("MaxSalary"),
    min("Salary").alias("MinSalary"),
    sum("Salary").alias("TotalSalary")
).show()

spark.stop()
```

**Your Turn:**
- [ ] Create sales data: (product, quarter, amount)
- [ ] Group by product
- [ ] Calculate total and average by product
- [ ] Sort by total descending

**Solution:**
```python
sales_data = [
    ("Apple", "Q1", 1000),
    ("Banana", "Q1", 500),
    ("Apple", "Q2", 1200),
    ("Banana", "Q2", 600),
    ("Apple", "Q3", 1500),
    ("Banana", "Q3", 700)
]

sales_df = spark.createDataFrame(sales_data, ["Product", "Quarter", "Amount"])

sales_by_product = sales_df.groupBy("Product").agg(
    sum("Amount").alias("Total"),
    avg("Amount").alias("Average")
).sort(col("Total").desc())

sales_by_product.show()
```

---

## EXERCISE 6: Spark SQL

### Task 6.1: Use SQL queries

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Spark SQL Exercise").getOrCreate()

# Create DataFrame
data = [
    (1, "John", "IT", 5000),
    (2, "Jane", "HR", 6000),
    (3, "Bob", "IT", 5500),
    (4, "Alice", "HR", 6500),
    (5, "Charlie", "IT", 5800)
]

columns = ["EmpId", "Name", "Department", "Salary"]
df = spark.createDataFrame(data, columns)

# Register as SQL view
df.createOrReplaceTempView("employees")

# Task 1: Simple SELECT
print("=== All Employees ===")
spark.sql("SELECT * FROM employees").show()

# Task 2: WHERE clause
print("\n=== IT Department ===")
spark.sql("SELECT Name, Salary FROM employees WHERE Department = 'IT'").show()

# Task 3: GROUP BY
print("\n=== Department Statistics ===")
spark.sql("""
    SELECT 
        Department,
        COUNT(*) as Count,
        AVG(Salary) as AvgSalary,
        MAX(Salary) as MaxSalary
    FROM employees
    GROUP BY Department
""").show()

# Task 4: ORDER BY
print("\n=== Ordered by Salary (High to Low) ===")
spark.sql("SELECT * FROM employees ORDER BY Salary DESC").show()

# Task 5: Complex query
print("\n=== High Earners in IT ===")
spark.sql("""
    SELECT Name, Department, Salary
    FROM employees
    WHERE Department = 'IT' AND Salary > 5400
    ORDER BY Salary DESC
""").show()

spark.stop()
```

**Your Turn:**
- [ ] Run all queries above
- [ ] Add: Query for average salary overall
- [ ] Add: Query for employees with salary > average

**Solution:**
```python
# Average salary overall
spark.sql("SELECT AVG(Salary) as AvgSalary FROM employees").show()

# Employees with salary > average
spark.sql("""
    SELECT Name, Salary
    FROM employees
    WHERE Salary > (SELECT AVG(Salary) FROM employees)
    ORDER BY Salary DESC
""").show()
```

---

## EXERCISE 7: JOIN Operations

### Task 7.1: Join multiple DataFrames

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("JOIN Exercise").getOrCreate()

# Employee data
emp_data = [
    (1, "John", 10),
    (2, "Jane", 20),
    (3, "Bob", 10),
    (4, "Alice", 20)
]

emp_df = spark.createDataFrame(emp_data, ["EmpId", "Name", "DeptId"])

# Department data
dept_data = [
    (10, "IT"),
    (20, "HR"),
    (30, "Finance")
]

dept_df = spark.createDataFrame(dept_data, ["DeptId", "Department"])

print("=== Employees ===")
emp_df.show()

print("\n=== Departments ===")
dept_df.show()

# Task: Join employees with departments
print("\n=== INNER JOIN ===")
joined = emp_df.join(dept_df, "DeptId", "inner")
joined.show()
# Expected: Shows employees with their department

# Task: LEFT JOIN (show all employees, departments if exist)
print("\n=== LEFT JOIN ===")
left_joined = emp_df.join(dept_df, "DeptId", "left")
left_joined.show()

# Task: RIGHT JOIN (show all departments, employees if exist)
print("\n=== RIGHT JOIN ===")
right_joined = emp_df.join(dept_df, "DeptId", "right")
right_joined.show()

# Task: Select specific columns
print("\n=== JOIN with Column Selection ===")
result = emp_df.join(dept_df, "DeptId").select("Name", "Department")
result.show()

spark.stop()
```

**Your Turn:**
- [ ] Create: Orders (OrderId, CustomerId, Amount)
- [ ] Create: Customers (CustomerId, Name)
- [ ] Join Orders with Customers
- [ ] Show each order with customer name

**Solution:**
```python
orders = spark.createDataFrame([
    (1, 101, 1000),
    (2, 102, 1500),
    (3, 101, 2000)
], ["OrderId", "CustomerId", "Amount"])

customers = spark.createDataFrame([
    (101, "John"),
    (102, "Jane")
], ["CustomerId", "Name"])

order_details = orders.join(customers, "CustomerId")
order_details.select("OrderId", "Name", "Amount").show()
```

---

## EXERCISE 8: Data Quality Checks

### Task 8.1: Validate data quality

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, isnull, sum, when, isnan

spark = SparkSession.builder.appName("DQ Exercise").getOrCreate()

# Create data with quality issues
data = [
    ("John", 25, "john@example.com"),
    ("Jane", None, "jane@example.com"),
    (None, 30, "bob@invalid"),
    ("Alice", 28, None),
    ("Alice", 28, None),  # Duplicate
    ("Bob", -5, "bob@example.com")  # Invalid age
]

df = spark.createDataFrame(data, ["Name", "Age", "Email"])

print("=== Raw Data ===")
df.show()

# DQ Check 1: Completeness
print("\n=== Completeness Check ===")
total = df.count()

for col_name in df.columns:
    null_count = df.filter(col(col_name).isNull()).count()
    completeness = ((total - null_count) / total) * 100
    print(f"{col_name}: {completeness:.2f}% complete")

# DQ Check 2: Duplicates
print("\n=== Duplicate Check ===")
total_rows = df.count()
unique_rows = df.dropDuplicates().count()
duplicates = total_rows - unique_rows
print(f"Total rows: {total_rows}, Unique rows: {unique_rows}, Duplicates: {duplicates}")

# DQ Check 3: Validity (Age should be > 0 and < 150)
print("\n=== Age Validity Check ===")
invalid_ages = df.filter((col("Age") < 0) | (col("Age") > 150))
invalid_ages.show()

# DQ Check 4: Email format
print("\n=== Email Format Check ===")
invalid_emails = df.filter(
    ~col("Email").rlike("^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$")
)
invalid_emails.show()

spark.stop()
```

**Your Turn:**
- [ ] Create customer dataset with issues
- [ ] Check completeness for each column
- [ ] Find duplicates
- [ ] Generate quality report

---

## EXERCISE 9: Save Data

### Task 9.1: Save DataFrames in different formats

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Save Exercise").getOrCreate()

# Create sample data
data = [
    (1, "John", 5000),
    (2, "Jane", 6000),
    (3, "Bob", 5500)
]

df = spark.createDataFrame(data, ["Id", "Name", "Salary"])

# Task 1: Save as Parquet (recommended, compressed)
df.write.mode("overwrite").parquet("output/employees.parquet")
print("✓ Saved as Parquet")

# Task 2: Save as CSV
df.write.mode("overwrite").csv("output/employees.csv", header=True)
print("✓ Saved as CSV")

# Task 3: Save as JSON
df.write.mode("overwrite").json("output/employees.json")
print("✓ Saved as JSON")

# Task 4: Read back from Parquet
loaded_df = spark.read.parquet("output/employees.parquet")
loaded_df.show()

# Task 5: Read CSV
csv_df = spark.read.csv("output/employees.csv", header=True, inferSchema=True)
csv_df.show()

spark.stop()
```

---

## EXERCISE 10: Real-World Data Quality Pipeline

### Task 10.1: Build a complete DQ pipeline

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, isnull, sum, when

class DataQualityPipeline:
    def __init__(self, spark):
        self.spark = spark
        self.report = {}
    
    def load_data(self, path):
        """Load data from CSV"""
        self.df = self.spark.read.csv(path, header=True, inferSchema=True)
        print(f"✓ Loaded {self.df.count()} rows")
        return self.df
    
    def check_completeness(self):
        """Check for missing values"""
        total = self.df.count()
        results = {}
        
        for col_name in self.df.columns:
            null_count = self.df.filter(col(col_name).isNull()).count()
            completeness = ((total - null_count) / total) * 100
            results[col_name] = completeness
        
        self.report['completeness'] = results
        return results
    
    def check_duplicates(self):
        """Check for duplicate records"""
        total = self.df.count()
        unique = self.df.dropDuplicates().count()
        duplicates = total - unique
        
        self.report['duplicates'] = duplicates
        return duplicates
    
    def remove_duplicates(self):
        """Remove duplicate records"""
        self.df = self.df.dropDuplicates()
        print(f"✓ Removed duplicates, {self.df.count()} rows remaining")
    
    def generate_report(self):
        """Print quality report"""
        print("\n" + "="*50)
        print("DATA QUALITY REPORT")
        print("="*50)
        
        for check, result in self.report.items():
            print(f"\n{check.upper()}:")
            if isinstance(result, dict):
                for item, value in result.items():
                    print(f"  {item}: {value:.2f}%")
            else:
                print(f"  Result: {result}")
        
        print("\n" + "="*50)
    
    def save_clean_data(self, output_path):
        """Save cleaned data"""
        self.df.write.mode("overwrite").parquet(output_path)
        print(f"✓ Saved clean data to {output_path}")

# Usage
if __name__ == "__main__":
    spark = SparkSession.builder.appName("DQ Pipeline").getOrCreate()
    
    # Initialize pipeline
    pipeline = DataQualityPipeline(spark)
    
    # Run pipeline
    pipeline.load_data("input/customers.csv")
    
    # Check quality
    completeness = pipeline.check_completeness()
    duplicates = pipeline.check_duplicates()
    
    # Clean data
    pipeline.remove_duplicates()
    
    # Generate report
    pipeline.generate_report()
    
    # Save results
    pipeline.save_clean_data("output/clean_customers")
    
    spark.stop()
```

---

## PRACTICE PROJECTS

### Project 1: Sales Analysis
```
Data: sales.csv with columns (Date, Product, Quantity, Price)
Tasks:
1. Load data
2. Calculate total sales amount
3. Group by product
4. Find top selling product
5. Calculate revenue by month
6. Save results
```

### Project 2: Customer Data Quality
```
Data: customers.csv with columns (CustomerId, Name, Email, Phone)
Tasks:
1. Check completeness
2. Find duplicates
3. Validate email format
4. Validate phone format
5. Generate quality report
6. Save clean data
```

### Project 3: Log Analysis
```
Data: app.log with log messages
Tasks:
1. Parse log lines
2. Extract date, level, message
3. Count errors by type
4. Find top 10 errors
5. Generate error report
```

---

## QUICK REFERENCE

### Create Spark Session
```python
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("MyApp").getOrCreate()
```

### Create DataFrame
```python
df = spark.createDataFrame(data, columns)
```

### Common Operations
```python
df.show()                          # Display
df.count()                         # Count rows
df.filter(condition)               # Filter
df.select(columns)                 # Select columns
df.groupBy(col).agg(function)      # Aggregate
df.join(other_df, key)             # Join
```

### Save Data
```python
df.write.parquet("path")           # Parquet
df.write.csv("path")               # CSV
df.write.json("path")              # JSON
```

---

**Complete all exercises and you'll be Spark-ready! 🚀**

*Last Updated: 2026-07-29*
