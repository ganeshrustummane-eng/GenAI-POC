# EPAM Junior Data Quality Engineer - Interview Q&A

## TECHNICAL QUESTIONS

### TIER 1: Basic Understanding (You MUST answer these)

#### Q1.1: What do you understand by Data Quality?
**Model Answer:**
```
"Data Quality refers to the degree to which data is:
1. Accurate - Correctly represents the real value
2. Complete - All required data is present
3. Consistent - Same across different systems
4. Timely - Available when needed
5. Valid - Conforms to required format
6. Unique - No unintended duplicates

It's important because good data leads to good decisions, 
reduces costs, ensures compliance, and enables reliable analytics."
```

**How to improve your answer:**
- Give industry example (healthcare, finance, etc.)
- Mention business impact (cost of bad data)
- Show you understand it's ongoing, not one-time

---

#### Q1.2: Name and explain the 6 data quality dimensions.
**Model Answer:**
```
1. ACCURACY: Data correctly represents real-world value
   Example: Customer name = official record
   Check: SELECT * WHERE calculated_age ≠ real_age

2. COMPLETENESS: All required data present
   Example: Every order has customer_id
   Check: SELECT COUNT(*) WHERE customer_id IS NULL

3. CONSISTENCY: Data same across systems
   Example: Customer status same in CRM & Billing
   Check: Compare CRM table with Billing table

4. TIMELINESS: Data current and available when needed
   Example: Data loaded within 4 hours of source update
   Check: SELECT MAX(load_time) - NOW()

5. VALIDITY: Data conforms to required format
   Example: Email contains @ and valid domain
   Check: SELECT * WHERE email NOT LIKE '%@%.%'

6. UNIQUENESS: No unintended duplicates
   Example: Each order_id appears once
   Check: SELECT col, COUNT(*) GROUP BY col HAVING COUNT(*) > 1
```

---

#### Q1.3: What is data profiling?
**Model Answer:**
```
Data profiling is the process of analyzing source data to understand:
- Structure: Tables, columns, data types
- Content: What data is there, data distribution
- Relationships: Foreign keys, dependencies
- Quality: Issues, anomalies, patterns

Activities:
1. Statistical analysis - Min, max, avg, distribution
2. Pattern analysis - Formats, ranges
3. Uniqueness analysis - Duplicates
4. Null analysis - Missing values
5. Relationship analysis - Foreign key integrity

Tools: SQL queries, Python pandas, Talend, Great Expectations
```

---

#### Q1.4: Difference between data validation and data quality testing?
**Model Answer:**
```
DATA VALIDATION:
- Checks if data conforms to rules
- Example: Is email format valid?
- Checks against: Formats, business rules, constraints
- Happens: During/after data load
- Tools: SQL, Python, validation rules

DATA QUALITY TESTING:
- Comprehensive assessment of data
- Example: Is the customer table 95%+ complete?
- Includes: All 6 DQ dimensions
- Happens: Ongoing monitoring
- Tools: DQ dashboards, metrics, monitoring

Relation: Testing uses validation as a component
```

---

### TIER 2: Intermediate SQL Skills (Critical for EPAM)

#### Q2.1: Write a query to check COMPLETENESS of a table
**Question:** Check how many records have complete data in the 'orders' table.

**Your Query:**
```sql
SELECT 
  COUNT(*) AS total_records,
  COUNT(*) FILTER (WHERE order_id IS NOT NULL) AS complete_order_id,
  COUNT(*) FILTER (WHERE customer_id IS NOT NULL) AS complete_customer_id,
  COUNT(*) FILTER (WHERE order_date IS NOT NULL) AS complete_order_date,
  COUNT(*) FILTER (WHERE amount IS NOT NULL) AS complete_amount,
  ROUND(
    COUNT(*) FILTER (WHERE order_id IS NOT NULL AND customer_id IS NOT NULL 
      AND order_date IS NOT NULL AND amount IS NOT NULL)::NUMERIC 
    / COUNT(*) * 100, 2
  ) AS overall_completeness_percentage
FROM orders;
```

**Better version with column-level detail:**
```sql
WITH completeness_check AS (
  SELECT 
    'order_id' AS column_name,
    COUNT(*) FILTER (WHERE order_id IS NOT NULL)::NUMERIC / COUNT(*) * 100 AS completeness_pct
  FROM orders
  UNION ALL
  SELECT 'customer_id', COUNT(*) FILTER (WHERE customer_id IS NOT NULL)::NUMERIC / COUNT(*) * 100 FROM orders
  UNION ALL
  SELECT 'order_date', COUNT(*) FILTER (WHERE order_date IS NOT NULL)::NUMERIC / COUNT(*) * 100 FROM orders
  UNION ALL
  SELECT 'amount', COUNT(*) FILTER (WHERE amount IS NOT NULL)::NUMERIC / COUNT(*) * 100 FROM orders
)
SELECT * FROM completeness_check ORDER BY completeness_pct;
```

---

#### Q2.2: Write a query to detect DUPLICATE records
**Question:** Find customers with duplicate emails

**Your Query:**
```sql
-- Simple approach
SELECT 
  email,
  COUNT(*) AS occurrence_count,
  STRING_AGG(customer_id::TEXT, ', ') AS customer_ids
FROM customers
GROUP BY email
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC;

-- Better approach showing all duplicate records
SELECT 
  *,
  ROW_NUMBER() OVER (PARTITION BY email ORDER BY customer_id) AS rn
FROM customers
WHERE email IN (
  SELECT email FROM customers 
  GROUP BY email HAVING COUNT(*) > 1
)
ORDER BY email, customer_id;

-- Even better with details
WITH duplicate_emails AS (
  SELECT email, COUNT(*) AS count FROM customers GROUP BY email HAVING COUNT(*) > 1
)
SELECT 
  c.customer_id,
  c.email,
  c.created_at,
  de.count AS total_with_email
FROM customers c
INNER JOIN duplicate_emails de ON c.email = de.email
ORDER BY c.email, c.customer_id;
```

---

#### Q2.3: Write a query to check VALIDITY of email format
**Question:** Find customers with invalid email addresses

**Your Query:**
```sql
-- PostgreSQL regex approach
SELECT 
  customer_id,
  email,
  CASE 
    WHEN email IS NULL THEN 'NULL'
    WHEN email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$' THEN 'Valid'
    ELSE 'Invalid'
  END AS email_validity
FROM customers
WHERE NOT (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
  OR email IS NULL;

-- Find specific issues
SELECT 
  customer_id,
  email,
  CASE 
    WHEN email IS NULL THEN 'Missing email'
    WHEN email NOT LIKE '%@%' THEN 'No @ symbol'
    WHEN LENGTH(email) < 5 THEN 'Too short'
    WHEN email LIKE '% %' THEN 'Contains space'
    ELSE 'Unknown issue'
  END AS issue_type
FROM customers
WHERE email IS NULL 
  OR email NOT LIKE '%@%' 
  OR LENGTH(email) < 5 
  OR email LIKE '% %';
```

---

#### Q2.4: Write a query to check CONSISTENCY across systems
**Question:** Compare customer data between CRM and Billing systems

**Your Query:**
```sql
SELECT 
  COALESCE(crm.customer_id, billing.customer_id) AS customer_id,
  crm.customer_name AS crm_name,
  billing.customer_name AS billing_name,
  crm.status AS crm_status,
  billing.status AS billing_status,
  CASE 
    WHEN crm.customer_id IS NULL THEN 'Only in Billing'
    WHEN billing.customer_id IS NULL THEN 'Only in CRM'
    WHEN crm.status <> billing.status THEN 'Status Mismatch'
    WHEN crm.customer_name <> billing.customer_name THEN 'Name Mismatch'
    ELSE 'Consistent'
  END AS consistency_status
FROM crm_customers crm
FULL OUTER JOIN billing_customers billing ON crm.customer_id = billing.customer_id
WHERE crm.customer_id IS NULL 
  OR billing.customer_id IS NULL 
  OR crm.status <> billing.status
  OR crm.customer_name <> billing.customer_name;
```

---

#### Q2.5: Write a query to check REFERENTIAL INTEGRITY
**Question:** Find orphaned orders (orders with non-existent customers)

**Your Query:**
```sql
-- Find orphaned records
SELECT 
  o.order_id,
  o.customer_id,
  o.order_date,
  'No matching customer' AS issue
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- Or using NOT IN
SELECT 
  order_id,
  customer_id,
  order_date
FROM orders
WHERE customer_id NOT IN (SELECT customer_id FROM customers WHERE customer_id IS NOT NULL);

-- Count and summary
SELECT 
  COUNT(*) AS orphaned_order_count,
  COUNT(DISTINCT customer_id) AS affected_customers
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;
```

---

#### Q2.6: Write a query to check ACCURACY
**Question:** Verify that order total equals sum of order items

**Your Query:**
```sql
SELECT 
  o.order_id,
  o.total_amount AS order_total,
  SUM(oi.quantity * oi.unit_price) AS calculated_total,
  ABS(o.total_amount - SUM(oi.quantity * oi.unit_price)) AS difference,
  CASE 
    WHEN o.total_amount = SUM(oi.quantity * oi.unit_price) THEN 'Accurate'
    ELSE 'Inaccurate'
  END AS accuracy_status
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY o.order_id, o.total_amount
HAVING o.total_amount <> SUM(oi.quantity * oi.unit_price) OR SUM(oi.quantity * oi.unit_price) IS NULL
ORDER BY difference DESC;
```

---

### TIER 3: Real-World Scenarios

#### Q3.1: Design a data quality framework for a new table
**Question:** "A new 'payments' table has been created. How would you ensure its quality?"

**Your Answer Structure:**
```
1. UNDERSTAND REQUIREMENTS
   Questions to ask:
   - What are critical fields? (payment_id, amount, customer_id)
   - What are SLAs? (95%+ completeness?)
   - When is data loaded? (Daily? Real-time?)
   - What are business rules? (amount > 0?)

2. IDENTIFY QUALITY DIMENSIONS
   For payments table:
   - Completeness: All payment_id, amount, customer_id present
   - Validity: amount is numeric and positive
   - Consistency: customer_id exists in customers table
   - Uniqueness: No duplicate payment_ids
   - Accuracy: Amount matches invoice
   - Timeliness: Loaded within 1 hour of transaction

3. WRITE VALIDATION QUERIES
   [Show SQL examples for each check]

4. CREATE METRICS & MONITORING
   - Daily quality score
   - Alert if below 95%
   - Dashboard for stakeholders

5. IMPLEMENT IN PIPELINE
   - Add checks before/after load
   - Log results
   - Alert on failures
```

---

#### Q3.2: Scenario - Data quality drops 20% overnight
**Question:** "Your quality check shows 20% drop in completeness. What do you do?"

**Your Approach:**
```
IMMEDIATE (First 5 minutes):
1. Verify the alert is real (not false positive)
   - Run query manually
   - Check data actually has issue

2. Quantify impact
   - How many records affected?
   - Which fields?
   - Which customers/products?

3. Alert stakeholders
   - Send message to team
   - Document in ticket

INVESTIGATION (Next 15 minutes):
1. Check what changed
   - Did ETL change?
   - Did source data change?
   - Any recent deployments?

2. Compare with historical data
   - When did quality drop?
   - Which specific records?

3. Root cause analysis
   - Query on source system?
   - ETL logic error?
   - Intentional change?

REMEDIATION (Next 30-60 minutes):
1. Fix the issue
   - Update data if possible
   - Rollback ETL if needed
   - Update source data

2. Validate fix
   - Re-run quality checks
   - Confirm quality restored

3. Prevent future
   - Add validation rule
   - Improve monitoring
   - Update documentation

EXAMPLE QUERY TO INVESTIGATE:
SELECT 
  load_date,
  completeness_pct,
  completeness_pct - LAG(completeness_pct) OVER (ORDER BY load_date) AS change
FROM dq_daily_metrics
WHERE table_name = 'payments'
ORDER BY load_date DESC
LIMIT 10;
```

---

#### Q3.3: You find 100,000 duplicate customer records
**Question:** "How would you handle this?"

**Your Approach:**
```
1. UNDERSTAND THE SCOPE
   SELECT COUNT(*) FROM customers;                  -- Total count
   SELECT COUNT(DISTINCT email) FROM customers;     -- Unique emails
   SELECT COUNT(*) / COUNT(DISTINCT email) FROM customers; -- Avg duplicates per email

2. IDENTIFY ROOT CAUSE
   - Is this from data entry?
   - Is this from ETL bug?
   - Are they truly duplicates or different people?

3. IMPACT ASSESSMENT
   - Which customers affected?
   - Impact on sales? Analytics?
   - Any foreign key violations?

4. SOLUTION OPTIONS
   
   Option A: Merge duplicates
   - Identify which record is primary
   - Update all foreign keys
   - Delete duplicates
   - Time-consuming, risky
   
   Option B: Flag as duplicates
   - Add 'is_duplicate' flag
   - Exclude from reports
   - Manual review process
   
   Option C: Recreate from source
   - Extract clean from source
   - Replace entirely
   - Fastest, safest

5. IMPLEMENTATION STEPS
   Step 1: Backup table
   Step 2: Write deduplication logic
   Step 3: Test thoroughly
   Step 4: Execute on prod (during maintenance window)
   Step 5: Verify results
   Step 6: Monitor for issues

6. PREVENT FUTURE
   - Add UNIQUE constraint on email
   - Add validation before load
   - Add duplicate check in ETL
   - Update monitoring

7. EXAMPLE DEDUPLICATION QUERY:
   WITH ranked_duplicates AS (
     SELECT *,
       ROW_NUMBER() OVER (PARTITION BY email ORDER BY created_at DESC) AS rn
     FROM customers
   )
   DELETE FROM customers
   WHERE customer_id IN (
     SELECT customer_id FROM ranked_duplicates WHERE rn > 1
   );
```

---

## BEHAVIORAL QUESTIONS (EPAM Culture)

### Q4.1: Describe a time you found a data quality issue. How did you solve it?
**How to answer (even if you haven't actually experienced this):**

```
Situation:
"During my [project/internship/assignment], I was analyzing a customer dataset 
and noticed that 5% of orders had NULL customer_id values."

Task:
"I was responsible for ensuring data quality before the data went to analytics team."

Action:
"I:
1. First validated the issue with a query
2. Quantified impact (5000 out of 100,000 records)
3. Investigated root cause (ETL didn't handle missing IDs from source)
4. Wrote validation query to find affected records
5. Communicated findings to the team
6. Suggested adding a validation check in the ETL to prevent this"

Result:
"This prevented bad data from reaching analysts and led to adding 
new validation rules in the pipeline."

Learning:
"I learned the importance of testing data early and having 
monitoring in place to catch issues before they impact users."
```

---

### Q4.2: How do you approach learning new tools/technologies?
**How to answer:**

```
"I learn through:
1. Documentation - Read official docs first
2. Practice - Write queries/code to practice
3. Examples - Learn from real examples
4. Experimentation - Try different approaches
5. Asking - Ask experienced colleagues

For data quality tools:
- I'd learn SQL fundamentals first (already strong)
- Then practice on sample datasets
- Then apply to real projects
- I'm comfortable learning Talend or Great Expectations on the job"
```

---

### Q4.3: Tell us about a time you worked with a team
**How to answer:**

```
"In my [project/internship]:
- I worked with [role] to understand data requirements
- Communicated findings clearly through [email/meetings/dashboard]
- Received feedback and improved my approach
- Documented my work so others could use it

I believe clear communication is key in data quality 
because we're ensuring data for the entire organization."
```

---

## EPAM-SPECIFIC QUESTIONS

### Q5.1: Why do you want to join EPAM?
**How to answer:**

```
"I'm interested in EPAM because:
1. Global presence - Work with international teams
2. Strong focus on data quality - Aligns with my interest
3. Modern tools and technologies - Talend, Great Expectations
4. Career growth - Junior role with mentorship
5. Variety of projects - Work with different clients/industries

I'm excited to grow as a Data Quality Engineer 
and contribute to EPAM's data initiatives."
```

---

### Q5.2: What do you know about data quality in banking/finance/healthcare?
**How to answer (if asked about specific industry):**

```
BANKING EXAMPLE:
"Data quality is critical because:
- Compliance: Regulations require accurate records
- Risk: Bad data can lead to wrong decisions
- Money: Even small data errors multiply at scale
- Example: Customer address must be accurate for KYC (Know Your Customer)"

HEALTHCARE EXAMPLE:
"Data quality is critical because:
- Patient safety: Wrong data = wrong treatment
- Compliance: HIPAA requires data accuracy
- Example: Medication allergies must be 100% accurate"

GENERAL ANSWER:
"Regardless of industry, quality data is essential for 
compliance, decision-making, and customer trust."
```

---

## TECHNICAL ASSESSMENT TIPS

### If they ask you to write a query on the spot:

1. **Take a moment** - Don't rush, think through it
2. **Ask clarifying questions**
   - "Which fields should I check?"
   - "Is NULL acceptable?"
   - "What's the expected result?"
3. **Explain your approach**
   - "I'll use GROUP BY to find..."
   - "I'll join tables to check..."
4. **Write clean SQL**
   - Proper indentation
   - Clear aliases
   - Comments if complex
5. **Test mentally**
   - "This would find records where..."
   - "The result would show..."
6. **Ask for feedback**
   - "Does this approach look right?"
   - "Should I optimize further?"

---

## Interview Day Checklist

- [ ] Arrive 10 minutes early
- [ ] Have pen and paper (for notes)
- [ ] Bring a copy of your resume
- [ ] Bring a notebook (show you take notes)
- [ ] Have 2-3 questions ready to ask them
- [ ] Examples prepared (issues you've solved)
- [ ] Laptop ready (if technical assessment)

---

## Questions to Ask Them

1. "What are the main data quality challenges at EPAM?"
2. "What tools does the team currently use?"
3. "What would success look like in the first 3 months?"
4. "Who would I be reporting to?"
5. "What training or mentorship is available?"
6. "What does a typical day look like?"

---

## Final Interview Tips

✅ **DO:**
- Show enthusiasm for data quality
- Give specific examples
- Ask clarifying questions
- Explain your thinking process
- Admit if you don't know something
- Show willingness to learn

❌ **DON'T:**
- Rush answers
- Over-complicate explanations
- Pretend to know tools you don't
- Be negative about previous roles
- Show up late
- Forget to ask questions

---

## Remember

You're interviewing them as much as they're interviewing you.
Make sure EPAM is the right fit for your career growth.

Good luck! You've prepared well! 🎯

---

*Last Updated: 2026-07-29*
*For: EPAM Junior Data Quality Engineer Interview*
