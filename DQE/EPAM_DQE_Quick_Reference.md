# EPAM Data Quality Engineer - Quick Reference & Study Plan

## 🎯 THE 6 DQ DIMENSIONS (MEMORIZE THIS!)

| Dimension | Definition | Example Check | SQL Pattern |
|-----------|-----------|----------------|------------|
| **ACCURACY** | Data correctly represents real value | Age matches birth date | WHERE calculated_age ≠ real_age |
| **COMPLETENESS** | All required data present | Customer has email | WHERE email IS NULL |
| **CONSISTENCY** | Data same across systems | CRM = Billing status | FULL OUTER JOIN & compare |
| **TIMELINESS** | Data available when needed | Loaded within 4 hours | SELECT MAX(load_time) - NOW() |
| **VALIDITY** | Conforms to required format | Email has @ | WHERE email NOT LIKE '%@%.%' |
| **UNIQUENESS** | No unintended duplicates | Email appears once | GROUP BY email HAVING COUNT() > 1 |

---

## 🔍 COMMON DQ SQL PATTERNS

### Pattern 1: Completeness Check
```sql
SELECT 
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE column_name IS NOT NULL) AS filled,
  ROUND(COUNT(*) FILTER (WHERE column_name IS NOT NULL)::NUMERIC / COUNT(*) * 100, 2) AS pct
FROM table_name;
```

### Pattern 2: Duplicate Check
```sql
SELECT column_name, COUNT(*) as count FROM table_name 
GROUP BY column_name HAVING COUNT(*) > 1;
```

### Pattern 3: Validity Check (Email)
```sql
SELECT * FROM table_name 
WHERE email NOT ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$';
```

### Pattern 4: Consistency Check (Cross-system)
```sql
SELECT * FROM system1_table t1
FULL OUTER JOIN system2_table t2 ON t1.key = t2.key
WHERE t1.status ≠ t2.status OR t1.id IS NULL OR t2.id IS NULL;
```

### Pattern 5: Referential Integrity Check
```sql
SELECT * FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;
```

### Pattern 6: Accuracy Check (Cross-field)
```sql
SELECT * FROM orders 
WHERE total_amount ≠ (quantity * unit_price);
```

---

## 📋 INTERVIEW ANSWER TEMPLATES

### "Explain Data Quality"
```
"Data Quality is the degree to which data meets business requirements 
and is fit for its intended use. I assess it using 6 dimensions:
Accuracy, Completeness, Consistency, Timeliness, Validity, Uniqueness.
Good quality data is essential for reliable decisions, compliance, 
and operational efficiency."
```

### "How would you test data quality?"
```
"I would:
1. Profile the data - Understand structure and content
2. Define requirements - What's acceptable quality?
3. Write validation queries - Check each dimension
4. Create metrics - Track completeness, uniqueness, etc.
5. Set up monitoring - Alert if quality drops
6. Report findings - Document issues and fixes"
```

### "Found 20% quality drop - What do you do?"
```
"1. VERIFY - Is the alert real?
2. QUANTIFY - How many records? Which fields?
3. ALERT - Notify team immediately
4. INVESTIGATE - What changed? ETL? Source data?
5. FIX - Update data or rollback
6. PREVENT - Add validation rule, improve monitoring"
```

### "You found 100k duplicates - How to handle?"
```
"1. Understand scope - How many per email? Root cause?
2. Impact assessment - Effect on business?
3. Solution options - Merge? Flag? Recreate from source?
4. Test thoroughly - Backup first
5. Implement - During maintenance window
6. Prevent - Add unique constraint + validation"
```

---

## 🛠️ KEY DQ CONCEPTS

### Data Profiling
- Analyze source data structure
- Understand content distribution
- Identify patterns and anomalies
- Find relationships between data

### Data Validation
- Check if data meets requirements
- Rule-based checking
- Format validation
- Referential integrity checks

### Data Quality Dimensions
- Accuracy: Correct values
- Completeness: All required data
- Consistency: Same across systems
- Timeliness: Current and available
- Validity: Proper format
- Uniqueness: No duplicates

### Quality Metrics
- Completeness %: Records with all required fields
- Accuracy %: Records with correct values
- Consistency %: Records matching across systems
- Duplication %: Duplicate records / total
- Validity %: Records with valid format

---

## 💡 EPAM WHAT THEY WANT

1. **SQL Skills** ⭐⭐⭐⭐⭐
   - Write efficient queries
   - Know GROUP BY, JOIN, window functions
   - Understand indexes, query optimization

2. **Problem Solving** ⭐⭐⭐⭐
   - Systematic approach
   - Ask clarifying questions
   - Think about edge cases

3. **Communication** ⭐⭐⭐⭐
   - Explain concepts clearly
   - Document findings
   - Work with non-technical people

4. **Attention to Detail** ⭐⭐⭐⭐
   - Find issues others miss
   - Validate thoroughly
   - Document thoroughly

5. **Learning Ability** ⭐⭐⭐⭐
   - Pick up tools quickly
   - Understand domain knowledge
   - Self-motivated learner

---

## 📅 7-DAY STUDY PLAN

### Day 1: Fundamentals (2-3 hours)
- [ ] Read: What is Data Quality?
- [ ] Understand: 6 DQ dimensions
- [ ] Watch: 1-2 YouTube videos on DQ basics
- [ ] Write: Definitions in your own words

### Day 2: Data Profiling (2-3 hours)
- [ ] Study: Data profiling concepts
- [ ] Practice: SQL profiling queries
- [ ] Example: Profile a dataset
- [ ] Document: What you learned

### Day 3: SQL Patterns (2-3 hours)
- [ ] Master: 6 DQ SQL patterns
- [ ] Practice: Write completeness, uniqueness, validity checks
- [ ] Test: Run on sample data
- [ ] Refine: Optimize queries

### Day 4: Scenarios (2-3 hours)
- [ ] Study: Real-world scenarios
- [ ] Practice: Write solutions for each scenario
- [ ] Explain: Out loud why your approach works
- [ ] Document: Key learnings

### Day 5: EPAM-Specific (2-3 hours)
- [ ] Learn: About EPAM's DQ approach
- [ ] Read: Company values/culture
- [ ] Research: Tools they use (Talend, etc.)
- [ ] Prepare: Why I want EPAM answer

### Day 6: Mock Interview (2-3 hours)
- [ ] Practice: Answer technical questions
- [ ] Write: SQL solutions on paper
- [ ] Explain: Your thinking out loud
- [ ] Time yourself: Can you answer in 2 minutes?

### Day 7: Final Review (1-2 hours)
- [ ] Review: 6 dimensions + 6 SQL patterns
- [ ] Review: Common interview questions
- [ ] Review: Your story + why EPAM
- [ ] Prepare: Questions to ask them
- [ ] Relax: You're ready!

---

## ✅ PRE-INTERVIEW CHECKLIST

**3 Days Before:**
- [ ] Review all 6 dimensions with examples
- [ ] Practice 6 SQL patterns
- [ ] Prepare your "why data quality" story
- [ ] Prepare your "why EPAM" story

**1 Day Before:**
- [ ] Get good sleep
- [ ] Review quick reference
- [ ] Prepare what to wear
- [ ] Know directions/login info

**Morning Of:**
- [ ] Light review of key concepts
- [ ] Eat good breakfast
- [ ] Arrive 10 minutes early
- [ ] Take deep breath - you've prepared well!

---

## 🎯 SAMPLE INTERVIEW FLOW

**Introduction (5 min)**
- Tell me about yourself
- Why data quality?
- Why EPAM?

**Technical (20-30 min)**
- Explain 6 DQ dimensions
- Write SQL for completeness
- Write SQL for duplicates
- Scenario: Quality dropped 20%
- Scenario: 100k duplicates found

**Behavioral (10 min)**
- Tell me about a challenge you faced
- How do you learn new tools?
- Tell me about teamwork

**Your Questions (5 min)**
- What tools do you use?
- What does success look like?
- How is the team structured?

---

## 📝 THINGS TO WRITE DOWN (Memory Aids)

### The 6 Dimensions (Acronym: ACCTUV... no that's bad)
Remember: **A**ccuracy, **C**ompleteness, **C**onsistency, **T**imeliness, **V**alidity, **U**niqueness

### Common Queries to Remember
1. **Completeness**: `COUNT(*) FILTER (WHERE col IS NOT NULL)`
2. **Duplicates**: `GROUP BY col HAVING COUNT(*) > 1`
3. **Validity**: `WHERE col NOT ~ 'pattern'`
4. **Consistency**: `FULL OUTER JOIN` then compare
5. **Referential**: `LEFT JOIN ... WHERE right_id IS NULL`
6. **Accuracy**: `WHERE calculated ≠ actual`

---

## 🚀 CONFIDENCE BOOSTERS

### You're Strong In:
- ✅ SQL fundamentals (required for DQ)
- ✅ Understanding database concepts (DDL knowledge helps!)
- ✅ Attention to detail (essential for DQ role)
- ✅ Problem-solving mindset

### You'll Learn On The Job:
- Talend or Great Expectations
- EPAM's specific DQ processes
- Domain knowledge (finance, healthcare, etc.)
- Company tools and workflows

**Remember: As a JUNIOR, they don't expect you to know everything!**
They want to see:
- Strong SQL skills ✓
- Understanding of DQ concepts ✓
- Problem-solving approach ✓
- Willingness to learn ✓

---

## 💬 QUESTIONS TO ASK THEM

1. "What are the biggest data quality challenges the team faces?"
2. "What tools does the team use for data quality?"
3. "What would success look like in my first 3 months?"
4. "How is the team structured and who would I report to?"
5. "What types of projects does the team work on?"
6. "What's the training/mentorship process for junior members?"

---

## 🎁 FINAL TIPS

1. **Be authentic** - Don't pretend to know everything
2. **Show enthusiasm** - You care about data quality
3. **Ask questions** - Shows you're thoughtful
4. **Listen carefully** - Understand before answering
5. **Use examples** - Concrete examples beat abstract talk
6. **Explain your thinking** - How you approach problems matters
7. **Be confident** - You've prepared well!
8. **Smile** - First impression matters

---

## 🔥 GOLDEN RULES

1. **SQL is your superpower** - Be strong in SQL
2. **6 dimensions = everything** - Memorize these
3. **Ask, don't assume** - Clarify requirements
4. **Data first** - Always verify with data
5. **Document everything** - Your findings matter
6. **Prevent > Detect** - Prevention is key
7. **Communication = Success** - Tell people what you found

---

## 🎯 THE ANSWER FORMULA

When asked ANY DQ question, follow this structure:

1. **Define** - What are we talking about?
2. **Why** - Why does it matter?
3. **How** - How do you approach it?
4. **Example** - Give a concrete example
5. **Tools** - What SQL/tools would you use?

Example:
> Q: "How do you check data completeness?"
> A: "Completeness means all required data is present. It matters because missing data impacts decisions. I'd query for NULL values and calculate the percentage. For example, if 5% of customer emails are missing, completeness is 95%. I'd use: `COUNT(*) FILTER (WHERE email IS NOT NULL) / COUNT(*) * 100`"

---

## 📊 DQ METRICS CHEAT SHEET

```
COMPLETENESS = Records with all required fields / Total records × 100
ACCURACY = Correct records / Total records × 100
CONSISTENCY = Matching records in both systems / Total records × 100
VALIDITY = Valid format records / Total records × 100
UNIQUENESS = Unique records / Total records × 100

Expected Targets (typical):
- Completeness: 95-99%
- Accuracy: 98-99%
- Consistency: 99-100%
- Validity: 95-99%
- Uniqueness: 99-100%
```

---

## REMEMBER

Data Quality is like being a **detective for bad data**:
- 🔍 You investigate issues
- 📊 You analyze patterns
- 📝 You document findings
- 🔧 You suggest fixes
- 🚨 You alert when problems arise
- 🛡️ You prevent future issues

**You've got this! Now go ace that EPAM interview! 💪**

---

*Last Updated: 2026-07-29*
*Interview Date: [Fill in your date]*
*Status: READY! 🎯*
