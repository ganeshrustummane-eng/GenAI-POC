# EPAM Junior Data Quality Engineer - Complete Interview Preparation

## TABLE OF CONTENTS
1. [Core DQ Fundamentals](#core-dq-fundamentals)
2. [Data Quality Dimensions](#data-quality-dimensions)
3. [Data Profiling & Assessment](#data-profiling--assessment)
4. [Data Validation Techniques](#data-validation-techniques)
5. [SQL for Data Quality](#sql-for-data-quality)
6. [EPAM Context & Tools](#epam-context--tools)
7. [Common Interview Questions](#common-interview-questions)
8. [Real-World Scenarios](#real-world-scenarios)

---

## CORE DQ FUNDAMENTALS

### What is Data Quality?
Data Quality is the degree to which data is fit for its intended purpose. It measures how well data meets business requirements and can be used reliably in decision-making.

**Key Definition for EPAM Interviews:**
> "Data Quality is the conformance of data to defined formats, patterns, business rules, and standards that make it suitable for its intended use."

### Why is Data Quality Important?
- **Business Impact**: Bad data = bad decisions
- **Cost**: 20-30% of a company's data is dirty (Gartner)
- **Compliance**: GDPR, HIPAA, regulatory requirements
- **ETL Efficiency**: Quality data = reliable pipelines
- **Analytics Accuracy**: Garbage in, garbage out (GIGO)

### Data Quality vs Data Governance
| Aspect | Data Quality | Data Governance |
|--------|--------------|-----------------|
| Focus | Measurement & improvement | Rules & policies |
| Activity | Testing, validation, monitoring | Creating standards, ownership |
| Scope | Technical | Strategic + Technical |
| Example | "Is email valid?" | "Who owns this field?" |

---

## DATA QUALITY DIMENSIONS

### The 6 Key Dimensions (VERY IMPORTANT FOR EPAM)

#### 1. **ACCURACY**
Data correctly represents the real-world value it's supposed to measure.

**Examples:**
- Customer name should match source records
- Product price should match what's in the warehouse
- Age calculated correctly from date of birth

**How to Test:**
```sql
-- Accuracy check: Verify age calculation
SELECT 
  customer_id,
  date_of_birth,
  calculated_age,
  EXTRACT(YEAR FROM AGE(CURRENT_DATE, date_of_birth)) AS correct_age,
  CASE 
    WHEN calculated_age = EXTRACT(YEAR FROM AGE(CURRENT_DATE, date_of_birth)) 
    THEN 'Accurate' 
    ELSE 'Inaccurate' 
  END AS accuracy_status
FROM customers
WHERE calculated_age <> EXTRACT(YEAR FROM AGE(CURRENT_DATE, date_of_birth));
```

---

#### 2. **COMPLETENESS**
All required data is present and no required fields are missing.

**Examples:**
- Every order must have a customer_id
- Every invoice must have an amount
- Required email field is not NULL

**How to Test:**
```sql
-- Completeness check: Find missing required fields
SELECT 
  COUNT(*) AS total_records,
  COUNT(*) FILTER (WHERE customer_id IS NOT NULL) AS filled_customer_ids,
  COUNT(*) FILTER (WHERE customer_id IS NULL) AS missing_customer_ids,
  ROUND(
    COUNT(*) FILTER (WHERE customer_id IS NOT NULL)::NUMERIC / COUNT(*) * 100, 2
  ) AS completeness_percentage
FROM orders;

-- Record-level completeness
SELECT 
  order_id,
  CASE 
    WHEN customer_id IS NULL THEN 'Missing customer_id'
    WHEN order_date IS NULL THEN 'Missing order_date'
    WHEN amount IS NULL THEN 'Missing amount'
    ELSE 'Complete'
  END AS completeness_status
FROM orders
WHERE customer_id IS NULL OR order_date IS NULL OR amount IS NULL;
```

---

#### 3. **CONSISTENCY**
Data is consistent across different systems, databases, and records.

**Examples:**
- Customer status is same in CRM and billing system
- Product name is same in catalog and warehouse
- Order total = sum of order items

**How to Test:**
```sql
-- Consistency check: Compare data across systems
SELECT 
  c1.customer_id,
  c1.status AS crm_status,
  c2.status AS billing_status,
  CASE WHEN c1.status = c2.status THEN 'Consistent' ELSE 'Inconsistent' END AS status
FROM crm_customers c1
FULL OUTER JOIN billing_customers c2 ON c1.customer_id = c2.customer_id
WHERE c1.status <> c2.status OR c1.status IS NULL OR c2.status IS NULL;

-- Check order total consistency
SELECT 
  o.order_id,
  o.total_amount,
  SUM(oi.item_price * oi.quantity) AS calculated_total,
  CASE 
    WHEN o.total_amount = SUM(oi.item_price * oi.quantity) 
    THEN 'Consistent' 
    ELSE 'Inconsistent' 
  END AS consistency_status
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY o.order_id, o.total_amount
HAVING o.total_amount <> SUM(oi.item_price * oi.quantity);
```

---

#### 4. **TIMELINESS**
Data is available when needed and is up-to-date.

**Examples:**
- Data loaded within SLA (4 hours after source update)
- Real-time data is within 5 minutes of actual event
- Historical data is not outdated

**How to Test:**
```sql
-- Timeliness check: Data freshness
SELECT 
  table_name,
  MAX(last_updated) AS last_update_time,
  NOW() - MAX(last_updated) AS time_since_update,
  CASE 
    WHEN (NOW() - MAX(last_updated)) < INTERVAL '4 hours' THEN 'Timely'
    WHEN (NOW() - MAX(last_updated)) < INTERVAL '24 hours' THEN 'Outdated'
    ELSE 'Stale'
  END AS timeliness_status
FROM table_metadata
GROUP BY table_name;

-- Check load completion time
SELECT 
  load_date,
  COUNT(*) AS records_loaded,
  MAX(load_timestamp) AS load_completed_at,
  (MAX(load_timestamp) - MIN(load_timestamp)) AS load_duration
FROM etl_logs
WHERE load_date = CURRENT_DATE
GROUP BY load_date;
```

---

#### 5. **VALIDITY**
Data conforms to the required formats, types, and business rules.

**Examples:**
- Email format is valid (contains @)
- Age is between 0-150
- Product price is numeric and positive
- Date format is YYYY-MM-DD

**How to Test:**
```sql
-- Validity check: Data format and business rules
SELECT 
  customer_id,
  email,
  age,
  CASE 
    WHEN email NOT LIKE '%@%.%' THEN 'Invalid email format'
    WHEN age < 0 OR age > 150 THEN 'Invalid age'
    WHEN NOT email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$' 
      THEN 'Invalid email pattern'
    ELSE 'Valid'
  END AS validity_status
FROM customers
WHERE email NOT LIKE '%@%.%' 
  OR age < 0 OR age > 150
  OR email IS NULL;

-- Product price validity
SELECT 
  product_id,
  price,
  CASE 
    WHEN price IS NULL THEN 'Missing price'
    WHEN NOT price ~ '^\d+(\.\d{2})?$' THEN 'Invalid format'
    WHEN price <= 0 THEN 'Invalid value (must be positive)'
    ELSE 'Valid'
  END AS price_validity
FROM products
WHERE price IS NULL OR price <= 0;
```

---

#### 6. **UNIQUENESS**
There are no unintended duplicate records or values.

**Examples:**
- No duplicate customer records
- Each order_id appears only once
- Email addresses are unique (if required)

**How to Test:**
```sql
-- Uniqueness check: Find duplicates
SELECT 
  email,
  COUNT(*) AS occurrence_count,
  STRING_AGG(customer_id::TEXT, ',') AS customer_ids
FROM customers
GROUP BY email
HAVING COUNT(*) > 1;

-- Duplicate records
SELECT 
  *,
  ROW_NUMBER() OVER (PARTITION BY email, phone ORDER BY created_at) AS rn
FROM customers
WHERE ROW_NUMBER() OVER (PARTITION BY email, phone ORDER BY created_at) > 1;

-- Find primary key violations
SELECT 
  order_id,
  COUNT(*) AS count
FROM orders
GROUP BY order_id
HAVING COUNT(*) > 1;
```

---

## DATA PROFILING & ASSESSMENT

### What is Data Profiling?
Data profiling is the process of analyzing source data to understand its structure, content, quality, and relationships.

### Data Profiling Activities

#### 1. **Structure Analysis**
```sql
-- Column-level metadata
SELECT 
  table_name,
  column_name,
  data_type,
  is_nullable,
  column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- Count columns and relationships
SELECT 
  table_name,
  COUNT(*) AS column_count
FROM information_schema.columns
WHERE table_schema = 'public'
GROUP BY table_name;
```

#### 2. **Content Analysis**
```sql
-- Data type distribution
SELECT 
  'orders' AS table_name,
  COUNT(*) AS total_records,
  COUNT(DISTINCT order_id) AS unique_orders,
  COUNT(*) - COUNT(DISTINCT order_id) AS duplicate_count,
  COUNT(DISTINCT customer_id) AS unique_customers
FROM orders;

-- Null analysis
SELECT 
  'customers' AS table_name,
  COUNT(*) AS total_records,
  COUNT(*) FILTER (WHERE customer_id IS NULL) AS null_id_count,
  COUNT(*) FILTER (WHERE email IS NULL) AS null_email_count,
  COUNT(*) FILTER (WHERE phone IS NULL) AS null_phone_count
FROM customers;

-- Value distribution
SELECT 
  status,
  COUNT(*) AS count,
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders), 2) AS percentage
FROM orders
GROUP BY status
ORDER BY count DESC;
```

#### 3. **Statistical Profiling**
```sql
-- Numeric column statistics
SELECT 
  'salary' AS column_name,
  COUNT(*) AS record_count,
  MIN(salary) AS min_value,
  MAX(salary) AS max_value,
  ROUND(AVG(salary), 2) AS avg_value,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary) AS median,
  STDDEV(salary) AS std_dev
FROM employees
WHERE salary IS NOT NULL;

-- String length analysis
SELECT 
  'product_name' AS column_name,
  COUNT(*) AS record_count,
  MIN(LENGTH(product_name)) AS min_length,
  MAX(LENGTH(product_name)) AS max_length,
  ROUND(AVG(LENGTH(product_name)), 2) AS avg_length
FROM products
WHERE product_name IS NOT NULL;
```

#### 4. **Pattern Analysis**
```sql
-- Format pattern check
SELECT 
  email,
  CASE 
    WHEN email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$' 
      THEN 'Valid format'
    ELSE 'Invalid format'
  END AS email_pattern,
  COUNT(*) AS count
FROM customers
GROUP BY email, email_pattern;

-- Phone number format
SELECT 
  phone,
  LENGTH(phone) AS phone_length,
  CASE 
    WHEN phone ~ '^\d{3}-\d{3}-\d{4}$' THEN 'Valid (XXX-XXX-XXXX)'
    WHEN phone ~ '^\d{10}$' THEN 'Valid (10 digits)'
    ELSE 'Invalid format'
  END AS phone_format,
  COUNT(*) AS count
FROM customers
WHERE phone IS NOT NULL
GROUP BY phone, phone_format;
```

---

## DATA VALIDATION TECHNIQUES

### 1. **Rule-Based Validation**
Pre-defined business rules that data must satisfy.

```sql
-- Validation Rule: Order amount must be positive
SELECT 
  order_id,
  amount,
  'Amount must be positive' AS rule_violated
FROM orders
WHERE amount <= 0
UNION ALL
-- Validation Rule: Order date cannot be in future
SELECT 
  order_id,
  amount,
  'Order date cannot be in future' AS rule_violated
FROM orders
WHERE order_date > CURRENT_DATE;
```

### 2. **Schema Validation**
Ensuring data conforms to expected structure.

```sql
-- Check data types
SELECT 
  column_name,
  data_type,
  CASE 
    WHEN data_type = 'integer' THEN 'Valid'
    ELSE 'Invalid'
  END AS type_validation
FROM information_schema.columns
WHERE table_name = 'orders' AND column_name = 'quantity';
```

### 3. **Cross-Field Validation**
Rules involving multiple fields.

```sql
-- Validation: End date must be after start date
SELECT 
  project_id,
  start_date,
  end_date,
  CASE 
    WHEN end_date < start_date THEN 'Invalid: End before start'
    ELSE 'Valid'
  END AS validation_result
FROM projects
WHERE end_date < start_date;

-- Validation: Order quantity times price should match total
SELECT 
  order_id,
  quantity,
  unit_price,
  (quantity * unit_price) AS calculated_total,
  total_amount,
  CASE 
    WHEN (quantity * unit_price) <> total_amount THEN 'Mismatch'
    ELSE 'Match'
  END AS validation_result
FROM order_items
WHERE (quantity * unit_price) <> total_amount;
```

### 4. **Referential Integrity Validation**
Ensuring foreign key relationships are valid.

```sql
-- Check for orphaned records (FK violation)
SELECT 
  o.order_id,
  o.customer_id,
  'Orphaned: No matching customer' AS issue
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- Check for missing referenced records
SELECT 
  COUNT(*) AS orphaned_records
FROM orders
WHERE customer_id NOT IN (SELECT customer_id FROM customers);
```

### 5. **Uniqueness Validation**
Detecting duplicate or non-unique data.

```sql
-- Find duplicate customers by email
SELECT 
  email,
  COUNT(*) AS email_count,
  COUNT(DISTINCT customer_id) AS unique_ids
FROM customers
GROUP BY email
HAVING COUNT(*) > 1;

-- Detailed duplicate analysis
SELECT 
  customer_id,
  email,
  COUNT(*) OVER (PARTITION BY email) AS email_occurrence_count
FROM customers
WHERE email IN (
  SELECT email FROM customers GROUP BY email HAVING COUNT(*) > 1
)
ORDER BY email, customer_id;
```

---

## SQL FOR DATA QUALITY

### Essential DQ SQL Patterns

#### Pattern 1: Data Quality Scorecard
```sql
CREATE VIEW dq_scorecard AS
SELECT 
  'completeness' AS dq_dimension,
  COUNT(*) FILTER (WHERE customer_id IS NOT NULL)::NUMERIC / COUNT(*) * 100 AS score_percentage,
  'Customers' AS table_name
FROM customers
UNION ALL
SELECT 
  'uniqueness',
  (COUNT(*) - COUNT(DISTINCT email))::NUMERIC / COUNT(*) * 100,
  'Customers'
FROM customers
UNION ALL
SELECT 
  'validity',
  COUNT(*) FILTER (WHERE email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')::NUMERIC / COUNT(*) * 100,
  'Customers'
FROM customers;

SELECT * FROM dq_scorecard;
```

#### Pattern 2: Data Quality Dashboard Query
```sql
WITH quality_metrics AS (
  SELECT 
    'customers' AS table_name,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE customer_id IS NOT NULL) AS complete_records,
    COUNT(DISTINCT customer_id) AS unique_ids,
    COUNT(*) - COUNT(DISTINCT customer_id) AS duplicate_count,
    ROUND(COUNT(*) FILTER (WHERE customer_id IS NOT NULL)::NUMERIC / COUNT(*) * 100, 2) AS completeness_pct,
    ROUND((COUNT(*) - COUNT(DISTINCT customer_id))::NUMERIC / COUNT(*) * 100, 2) AS duplication_pct
  FROM customers
)
SELECT * FROM quality_metrics;
```

#### Pattern 3: Incremental Quality Check (Delta)
```sql
-- Compare quality between two time periods
SELECT 
  DATE(l1.check_date) AS check_date,
  l1.table_name,
  l1.completeness_pct AS prev_day_completeness,
  l2.completeness_pct AS curr_day_completeness,
  (l2.completeness_pct - l1.completeness_pct) AS completeness_delta,
  CASE 
    WHEN (l2.completeness_pct - l1.completeness_pct) < 0 THEN 'Degraded'
    WHEN (l2.completeness_pct - l1.completeness_pct) > 0 THEN 'Improved'
    ELSE 'Stable'
  END AS trend
FROM dq_logs l1
JOIN dq_logs l2 ON l1.table_name = l2.table_name
WHERE DATE(l1.check_date) = CURRENT_DATE - INTERVAL '1 day'
  AND DATE(l2.check_date) = CURRENT_DATE;
```

---

## EPAM CONTEXT & TOOLS

### EPAM's Data Quality Approach

**EPAM typically uses:**
- **Talend** - ETL/Data Quality tool (most common)
- **Great Expectations** - Python-based framework
- **Custom SQL Scripts** - For validation
- **Apache Spark** - For large-scale DQ checks
- **Python** - For automation and custom checks

### Tools You Should Know

#### 1. **SQL (Critical for Junior Role)**
- Write DQ queries
- Validate data rules
- Profile data
- Create DQ dashboards

#### 2. **Python** (Good to know)
```python
# Simple data quality check
import pandas as pd

def check_completeness(df, column):
    """Check completeness of a column"""
    missing = df[column].isnull().sum()
    completeness = (1 - missing / len(df)) * 100
    return {
        'column': column,
        'missing_count': missing,
        'completeness_pct': completeness
    }

def check_validity(df, column, pattern):
    """Check if values match pattern"""
    valid = df[column].str.match(pattern).sum()
    validity_pct = (valid / len(df)) * 100
    return validity_pct
```

#### 3. **Talend (if possible)**
- Data Quality Dashboard
- Rule Engine
- Pattern analysis
- Automated validation

#### 4. **Great Expectations** (Modern approach)
```python
import great_expectations as ge

# Load data
df = ge.read_csv("data.csv")

# Add expectations
df.expect_column_to_exist("customer_id")
df.expect_column_values_to_not_be_null("email")
df.expect_column_values_to_match_regex("email", r'^[A-Za-z0-9._%+-]+@')

# Run validation
results = df.validate()
```

---

## COMMON INTERVIEW QUESTIONS

### Q1: What is Data Quality and why is it important?
**Your Answer Framework:**
```
"Data Quality is the degree to which data meets the business's requirements 
and is fit for its intended use. It's important because:
1. Impacts business decisions - bad data = bad decisions
2. Cost reduction - fixing errors early is cheaper than later
3. Compliance - GDPR, regulatory requirements
4. Operational efficiency - reliable ETL pipelines
5. Analytics accuracy - better insights with clean data

I assess quality using 6 dimensions: Accuracy, Completeness, Consistency, 
Timeliness, Validity, and Uniqueness."
```

---

### Q2: Explain the 6 data quality dimensions with examples.
**Your Answer Framework:**
```
1. ACCURACY: Data correctly represents real-world values
   Example: Customer age matches birth date

2. COMPLETENESS: All required data is present
   Example: Every order has a customer_id

3. CONSISTENCY: Data is consistent across systems
   Example: Customer status same in CRM and billing

4. TIMELINESS: Data is current and available when needed
   Example: Sales data loaded within 4 hours

5. VALIDITY: Data conforms to required formats
   Example: Email contains @ and valid domain

6. UNIQUENESS: No unintended duplicates
   Example: Each order_id appears only once
```

---

### Q3: How would you write a SQL query to check data completeness?
**Your Answer:**
```sql
SELECT 
  column_name,
  COUNT(*) AS total_records,
  COUNT(*) FILTER (WHERE column_value IS NOT NULL) AS filled,
  COUNT(*) FILTER (WHERE column_value IS NULL) AS missing,
  ROUND(
    COUNT(*) FILTER (WHERE column_value IS NOT NULL)::NUMERIC / COUNT(*) * 100, 2
  ) AS completeness_percentage
FROM table_name
GROUP BY column_name;
```

---

### Q4: What's the difference between data validation and data profiling?
**Your Answer Framework:**
```
DATA PROFILING:
- Exploratory process
- Understand structure, content, distribution
- Answer: "What does the data look like?"
- One-time activity typically

DATA VALIDATION:
- Checking against rules/criteria
- Ensure data meets requirements
- Answer: "Does data meet our standards?"
- Ongoing, part of monitoring
```

---

### Q5: How would you detect duplicate records?
**Your Answer:**
```sql
-- Method 1: Using GROUP BY
SELECT 
  email,
  COUNT(*) AS count
FROM customers
GROUP BY email
HAVING COUNT(*) > 1;

-- Method 2: Using window functions
SELECT *,
  ROW_NUMBER() OVER (PARTITION BY email ORDER BY customer_id) AS rn
FROM customers
WHERE ROW_NUMBER() OVER (PARTITION BY email ORDER BY customer_id) > 1;
```

---

### Q6: Describe your approach to data quality testing.
**Your Answer Framework:**
```
1. UNDERSTAND REQUIREMENTS
   - What fields are critical?
   - What are business rules?
   - What is the acceptable quality threshold?

2. DESIGN TESTS
   - Completeness checks
   - Accuracy validations
   - Consistency rules
   - Format validation
   - Uniqueness checks

3. IMPLEMENT
   - SQL queries or scripts
   - Automated checks
   - Logging and monitoring

4. REPORT
   - Document issues
   - Create quality metrics
   - Track improvements

5. REMEDIATE
   - Fix data issues
   - Update processes
   - Prevent future issues
```

---

### Q7: How would you handle data quality issues in production?
**Your Answer Framework:**
```
1. IMMEDIATE ACTIONS:
   - Alert stakeholders
   - Stop dependent processes if critical
   - Document the issue

2. INVESTIGATION:
   - Find root cause
   - Measure impact
   - Assess urgency

3. REMEDIATION:
   - Fix data (if possible)
   - Update validation rules
   - Prevent recurrence

4. REPORTING:
   - Create incident report
   - Add to quality metrics
   - Improve monitoring

5. PREVENTION:
   - Enhance validation rules
   - Add new checks upstream
   - Update documentation
```

---

### Q8: What would you do if a validation rule fails?
**Your Answer:**
```
BEFORE ESCALATING:
1. Verify the rule is correct (not false positive)
2. Check if data actually violates the rule
3. Understand if it's a known issue

IF RULE IS VALID:
1. Identify affected records
2. Determine impact (how many? which systems?)
3. Alert stakeholders
4. Document in ticket/jira
5. Fix data or update rule as needed
6. Re-run validation to confirm
```

---

### Q9: How would you monitor data quality over time?
**Your Answer:**
```
1. CREATE BASELINE METRICS:
   - Calculate quality scores for each dimension
   - Establish SLAs (e.g., 95% completeness)

2. TRACK TRENDS:
   - Daily/weekly quality scores
   - Monitor for degradation
   - Alert if below threshold

3. REPORT:
   - Dashboard showing quality trends
   - Monthly quality reports
   - Root cause analysis for failures

4. IMPROVE:
   - Identify systemic issues
   - Update validation rules
   - Enhance data processes
```

---

### Q10: Describe your experience with data quality tools.
**Your Answer (for Junior role):**
```
"While I'm junior, I have strong SQL skills which is fundamental. 
I'm familiar with:

1. SQL - Main tool for validation queries and checks
2. Data profiling concepts - Understanding data before validation
3. Python basics - Can write simple data quality scripts

I'm eager to learn EPAM's tools like Talend/Great Expectations 
on the job. My SQL foundation will transfer well because most 
tools use SQL under the hood."
```

---

## REAL-WORLD SCENARIOS

### Scenario 1: Incomplete Customer Data
**Problem:** 15% of customers missing email addresses

**Your Approach:**
1. **Analyze**: Are emails truly missing or NULL in wrong way?
2. **Quantify**: How many records? Which customers affected?
3. **Impact**: Can we contact customers? Does it break reports?
4. **Fix**: 
   - Recover from source system
   - Make email nullable if truly optional
   - Add validation to prevent future issues
5. **Prevention**: Add completeness check before data load

---

### Scenario 2: Inconsistent Customer Data Across Systems
**Problem:** Customer status different in CRM vs Billing

**Your Approach:**
```sql
-- Find inconsistencies
SELECT 
  c1.customer_id,
  c1.status AS crm_status,
  c2.status AS billing_status
FROM crm_customers c1
FULL OUTER JOIN billing_customers c2 ON c1.customer_id = c2.customer_id
WHERE c1.status <> c2.status;

-- Root cause analysis
-- Which system is source of truth?
-- When did they diverge?
-- How to reconcile?

-- Action:
-- 1. Define source of truth
-- 2. Sync data from source
-- 3. Add consistency check in ETL
-- 4. Set up reconciliation process
```

---

### Scenario 3: Duplicate Records Found
**Problem:** Same customer appears 3 times with slightly different names

**Your Approach:**
1. **Identify**: Use fuzzy matching to find near-duplicates
2. **Analyze**: Is this data entry error or real duplicates?
3. **Measure**: How many records affected?
4. **Merge**: Combine duplicate records, keeping correct info
5. **Update**: Update foreign key references
6. **Prevent**: Add uniqueness constraint + validation

```sql
-- Find potential duplicates (fuzzy matching)
SELECT 
  c1.customer_id,
  c1.name,
  c2.customer_id,
  c2.name,
  SIMILARITY(c1.name, c2.name) AS similarity_score
FROM customers c1
JOIN customers c2 ON c1.customer_id < c2.customer_id
WHERE SIMILARITY(c1.name, c2.name) > 0.8
ORDER BY similarity_score DESC;
```

---

### Scenario 4: Data Quality Regression After ETL Update
**Problem:** Completeness dropped from 98% to 85% after ETL change

**Your Approach:**
1. **Alert**: Notify stakeholders immediately
2. **Analyze**: 
   ```sql
   SELECT 
     load_date,
     completeness_pct,
     completeness_pct - LAG(completeness_pct) OVER (ORDER BY load_date) AS change
   FROM dq_daily_metrics
   WHERE table_name = 'orders'
   ORDER BY load_date DESC
   LIMIT 10;
   ```
3. **Investigate**: What changed in ETL? Which fields affected?
4. **Fix**: Rollback ETL or fix data issues
5. **Improve**: Add DQ gates before production load
6. **Learn**: Update validation rules, improve monitoring

---

## EPAM-SPECIFIC TIPS

### What EPAM Values (For Junior Role)

1. **SQL Proficiency** ⭐⭐⭐⭐⭐
   - Be strong in SQL
   - Write efficient queries
   - Know query optimization basics

2. **Problem Solving** ⭐⭐⭐⭐
   - Approach systematically
   - Ask clarifying questions
   - Don't jump to solutions

3. **Communication** ⭐⭐⭐⭐
   - Explain your thinking
   - Document your findings
   - Work with stakeholders

4. **Learning Ability** ⭐⭐⭐⭐
   - Pick up new tools quickly
   - Understand domain knowledge
   - Self-motivated learner

5. **Attention to Detail** ⭐⭐⭐⭐
   - Data quality is detail-oriented
   - Catch edge cases
   - Document thoroughly

### How to Answer EPAM Questions

**Structure:**
1. **Understand** - Ask clarifying questions
2. **Plan** - Explain your approach
3. **Execute** - Write SQL or code
4. **Verify** - Double-check results
5. **Document** - Explain findings

**Example Answer Pattern:**
```
Q: "How would you check data quality for a new table?"

A: "First, I'd ask:
   - What are the business requirements? (Key fields, SLAs)
   - What should I validate? (All dimensions or specific ones?)
   - What's the table size? (Affects approach)
   
   Then I'd:
   1. Profile the data (structure, distribution)
   2. Write validation queries (SQL)
   3. Create quality metrics
   4. Set up monitoring
   5. Document in confluence
   
   Here's the SQL I'd start with..."
```

---

## QUICK REFERENCE: Common DQ SQL Patterns

```sql
-- Completeness
SELECT column_name, COUNT(*) FILTER (WHERE column_name IS NULL) AS null_count FROM table_name;

-- Uniqueness
SELECT column_name, COUNT(*) FROM table_name GROUP BY column_name HAVING COUNT(*) > 1;

-- Validity (Email)
SELECT * FROM customers WHERE email NOT ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$';

-- Consistency (Cross-table)
SELECT * FROM orders o LEFT JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_id IS NULL;

-- Accuracy (Cross-field)
SELECT * FROM orders WHERE total_amount <> (quantity * unit_price);

-- Timeliness
SELECT MAX(updated_at) AS last_update, NOW() - MAX(updated_at) AS age FROM table_name;
```

---

## Interview Preparation Checklist

- [ ] **6 DQ Dimensions** - Can explain each with examples
- [ ] **SQL Queries** - Can write completeness, uniqueness, validity checks
- [ ] **Data Profiling** - Understand structure, content, patterns
- [ ] **Data Validation** - Know rule-based, referential, format checks
- [ ] **Problem Solving** - Can approach DQ issues systematically
- [ ] **Communication** - Can explain concepts clearly
- [ ] **Tools** - SQL proficiency, basic Python helpful
- [ ] **EPAM Context** - Understand their tools and approach

---

## Final Tips for EPAM Interview

1. **Show SQL Skills**
   - Write clean, efficient queries
   - Understand query plans
   - Optimize where possible

2. **Ask Questions**
   - "What's the acceptable quality threshold?"
   - "Which dimension is most critical?"
   - "What's the data volume?"

3. **Think Like Data Quality**
   - Always ask "How do I validate this?"
   - Consider edge cases
   - Think about monitoring

4. **Be Honest**
   - As junior, you don't need to know everything
   - Show eagerness to learn
   - Highlight transferable skills

5. **Provide Examples**
   - "I once checked..." or "I would..."
   - Show systematic approach
   - Mention SQL queries you'd write

---

## Resources to Study

- **SQL**: Practice on DataCamp or HackerRank
- **Data Quality**: Read Gartner reports on DQ
- **Python**: Learn pandas for data validation
- **Tools**: Try free Talend or Great Expectations trial

---

## Remember

> "Data Quality is not a one-time task, it's a continuous process. 
> As a Data Quality Engineer, your job is to find issues early, 
> help fix them, and prevent them in the future."

**Good luck with your EPAM interview! You've got this! 🎯**

---

*Last Updated: 2026-07-29*
*For: Junior Data Quality Engineer Position at EPAM*
