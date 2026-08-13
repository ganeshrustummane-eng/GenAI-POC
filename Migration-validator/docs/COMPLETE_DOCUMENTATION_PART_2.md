# Migration Validator — Complete Documentation (Part 2 of 2)
**From Matching and AI Decisions to Generated Artifacts, Operations, and Maintenance**

---

## Table of Contents — Part 2

8. [Column Matching Pipeline](#8-column-matching-pipeline)
9. [AI-Assisted Resolution](#9-ai-assisted-resolution)
10. [Canonical Validation Plan](#10-canonical-validation-plan)
11. [SQL and YAML Generation](#11-sql-and-yaml-generation)
12. [Command-Line Workflows](#12-command-line-workflows)
13. [Batch Processing](#13-batch-processing)
14. [Dynamic Validation Suite](#14-dynamic-validation-suite)
15. [Learning and Rule Customization](#15-learning-and-rule-customization)
16. [How to Execute and Interpret Validation](#16-how-to-execute-and-interpret-validation)
17. [Failure Handling and Troubleshooting](#17-failure-handling-and-troubleshooting)
18. [Security and Governance](#18-security-and-governance)
19. [Developer Extension Guide](#19-developer-extension-guide)
20. [Operational Recommendations](#20-operational-recommendations)
21. [End-to-End Reference](#21-end-to-end-reference)
22. [Current Boundaries and Important Caveats](#22-current-boundaries-and-important-caveats)

> Part 1 explains the project purpose, architecture, setup, connections, and normalization rules. Part 2 continues from live schema metadata and explains how the system reaches a mapping decision, produces validation artifacts, and is operated safely.

---

## 8. Column Matching Pipeline

### 8.1 Purpose

A source and target table may contain logically equivalent columns whose names, cases, separators, positions, and physical types differ. The matching pipeline determines which source column corresponds to which Snowflake target column.

Examples:

| Source | Target | Expected result |
|---|---|---|
| `customer_id` | `CUSTOMER_ID` | Exact, case-insensitive match |
| `created_at` | `CREATEDAT` | Normalized exact match |
| `transaction_date` | `TRANSACTION_DT` | Fuzzy or AI-assisted match |
| `amount` | `TOTAL_VALUE` | Potentially ambiguous; requires stronger evidence |
| `legacy_note` | No corresponding column | Unmatched and skipped |

The matching system is deliberately layered. Cheap deterministic decisions happen first. AI is reserved for ambiguous cases.

### 8.2 End-to-End Decision Flow

```text
Source and target ColumnMetadata
             │
             ▼
Remove/skip source Fivetran metadata columns
             │
             ▼
Explicit configured mapping
             │ no match
             ▼
Case-insensitive exact match
             │ no match
             ▼
Normalized exact match
             │ no match
             ▼
Generate top five fuzzy candidates
             │
             ▼
Calculate multi-factor confidence
       ┌─────┴─────────────┐
       │                   │
 score >= 0.95       0.75 <= score < 0.95
 auto-resolve              AI review
       │                   │
       └─────────┬─────────┘
                 │
            score < 0.75
          unmatched / skipped
```

The default thresholds are:

- **High-confidence threshold:** `0.95`
- **AI-review threshold:** `0.75`

They can be changed through the `FUZZY_HIGH_CONFIDENCE` and `FUZZY_AI_REVIEW` environment variables or constructor parameters.

### 8.3 Metadata Used in Matching

The pipeline works with metadata, not table rows. Typical `ColumnMetadata` information includes:

- Original column name
- Database data type
- Ordinal position
- Nullability
- Numeric precision and scale where available
- Primary-key information where supported

This makes matching fast and prevents row-level business data from being sent to the AI service.

### 8.4 Explicit Mappings

An explicit mapping is a user-controlled override:

```yaml
explicit_mappings:
  customer_id: CUST_ID
  created_at: CREATED_TIMESTAMP
```

Explicit mappings have the highest priority. Matching is case-insensitive, but the configured target must exist in the extracted target metadata. A valid configured mapping receives confidence `1.0` and match method `configured`.

Use explicit mappings when:

- The target name is completely different.
- Multiple target columns are semantically plausible.
- A known migration convention cannot be inferred from names.
- A reviewed mapping must remain stable across runs.

### 8.5 Exact Matching

`matching/exact_matcher.py` performs deterministic matching in this order:

1. Configured mapping
2. Original-name match, case-insensitive
3. Normalized-name match

Examples:

```text
amount      → AMOUNT       method=exact
created_at  → CREATEDAT    method=normalized_exact
customer_id → CUST_ID      method=configured
```

Exact and normalized-exact matches require no AI call and receive confidence `1.0`.

### 8.6 Name Normalization

`matching/normalizer.py` creates a comparison-only version of each name:

1. Convert to lowercase.
2. Remove every non-alphanumeric character.

Examples:

| Original | Normalized |
|---|---|
| `created_at` | `createdat` |
| `CREATED-AT` | `createdat` |
| `createdAt` | `createdat` |
| `customer id` | `customerid` |

Normalization never changes the SQL identifier used in generated queries. SQL always uses the original extracted name.

### 8.7 Fuzzy Candidate Generation

Columns not resolved exactly are compared against currently unmatched target columns. `matching/fuzzy_matcher.py`:

- Normalizes names.
- Uses RapidFuzz `token_ratio` when installed.
- Falls back to Python `SequenceMatcher` if RapidFuzz is unavailable.
- Sorts candidates by descending similarity.
- Keeps the top five by default.

A fuzzy candidate contains:

- Source and target metadata
- Raw similarity score from `0.0` to `1.0`
- Normalized source and target names
- Threshold classification

The fuzzy matcher ranks possibilities; it does not make the final decision by itself.

### 8.8 Confidence Scoring

`matching/confidence.py` combines four evidence factors:

| Factor | Weight | Meaning |
|---|---:|---|
| Name similarity | 0.40 | Similarity of normalized names |
| Type compatibility | 0.35 | Whether the source-to-target type pair is known |
| Position proximity | 0.10 | Similarity of ordinal positions |
| Learned example | 0.15 | Whether a human-confirmed pair already exists |

Formula:

```text
confidence =
    name_similarity × 0.40
  + type_compatibility × 0.35
  + position_proximity × 0.10
  + learned_example × 0.15
```

The result is clamped to `[0.0, 1.0]`.

This number is an explainable confidence score, not a statistically calibrated probability.

Example:

```text
Name similarity    0.92 × 0.40 = 0.368
Type compatibility 1.00 × 0.35 = 0.350
Position proximity 0.80 × 0.10 = 0.080
Learned example    1.00 × 0.15 = 0.150
---------------------------------------
Final confidence                = 0.948
```

This example remains just below the default automatic threshold and therefore enters AI review.

Unknown type combinations receive a neutral compatibility score of `0.60`; they are not rejected automatically.

### 8.9 Match Decision States

`CandidateMatcher` emits exactly one `MatchDecision` per source column.

| State | Meaning | Next action |
|---|---|---|
| `resolved` | Deterministic evidence is sufficient | Add to plan |
| `ai_needed` | Candidate exists, but evidence is ambiguous | Send focused request to AI |
| `unmatched` | No acceptable candidate | Skip and report |

Additional fields explain the result:

- `method`: `exact`, `normalized_exact`, `configured`, `fuzzy`, or `fuzzy_ai`
- `final_score`
- `fuzzy_score`
- `candidates`
- `skip_validation`
- `skip_reason`

### 8.10 Fivetran Columns

Source columns beginning with `_FIVETRAN_` are marked as skipped metadata. Target `_FIVETRAN_ACTIVE` is detected separately and controls target filtering:

```sql
WHERE _FIVETRAN_ACTIVE = TRUE
```

This prevents historical or inactive Fivetran versions from being compared with current source rows.

---

## 9. AI-Assisted Resolution

### 9.1 AI Is Selective, Not Mandatory

AI is called only for `ai_needed` decisions. Exact matches and high-confidence fuzzy matches never consume AI tokens.

If no `DIAL_API_KEY` is configured, the system continues and accepts the best fuzzy candidate for ambiguous decisions. This is graceful degradation, not a complete failure.

### 9.2 Information Sent to AI

For each ambiguous source column, the prompt contains only:

- Table name for context
- Source column name, normalized name, type, nullability, and position
- Top target candidates with equivalent metadata and fuzzy scores
- A compact transformation-rule summary
- Up to a few relevant learned examples

It does **not** contain:

- Database passwords
- Connection strings
- SQL query results
- Row-level values
- Entire database schemas
- Unrelated tables

### 9.3 One Focused Call per Ambiguous Column

The planner uses one request per ambiguous column. This design offers:

- Smaller prompts
- Easier response validation
- Better explainability
- Isolation when one AI call fails
- Accurate `ai_calls_made` tracking

### 9.4 Required AI Response

The response must be JSON:

```json
{
  "status": "resolved",
  "source_column": "transaction_date",
  "target_column": "TRANSACTION_DT",
  "source_type": "timestamp without time zone",
  "target_type": "TIMESTAMP_NTZ",
  "transformation_rule": "timestamp_ntz",
  "confidence": 0.96,
  "reason": "The names are semantically equivalent and the timestamp types are compatible."
}
```

The parser validates:

- Status is `resolved` or `ambiguous`.
- The target is one of the supplied candidates.
- The rule ID is recognized.
- Confidence can be converted to a number and is within range.

An unknown rule is replaced with `text`. An invented target or invalid JSON causes a safe fallback to the best fuzzy candidate.

### 9.5 AI Failure Behavior

| Failure | Behavior |
|---|---|
| No API key | Accept best fuzzy candidate |
| `openai` package missing | Accept best fuzzy candidate |
| DIAL network/API error | Log error and accept best fuzzy candidate |
| Invalid JSON | Record parse error and accept best fuzzy candidate |
| AI invents target | Reject response and accept best fuzzy candidate |
| AI reports `ambiguous` | Decision remains visible as ambiguous for review |

Because fallback can still produce output, operators must review warnings and low-confidence mappings rather than treating generation success as proof of mapping correctness.

### 9.6 AI for Business-Rule Suggestions

The dynamic suite has a second, independent AI use. `AIRecommendationEngine` may suggest checks such as:

- `amount >= 0`
- `end_date >= start_date`
- Plausible email or telephone formats
- Non-null expectations for likely identifiers

These suggestions are additive and are rendered for human review. AI does not replace baseline checks and does not receive row data.

---

## 10. Canonical Validation Plan

### 10.1 Single Source of Truth

`core/validation_plan.py` defines `CanonicalValidationPlan`. It is the central contract between matching and output generation.

```text
Extracted metadata
       ↓
Matching and AI decisions
       ↓
CanonicalValidationPlan
       ├── SQL generator
       ├── YAML generator
       ├── Plan JSON
       └── Dynamic suite input
```

Both SQL and YAML consume the same plan, preventing one artifact from using a different column mapping than another.

### 10.2 Plan Contents

A plan records:

- Source database type, database, schema, and table
- Target database, schema, and table
- Every source-column mapping
- Fivetran active-filter detection
- Source and target primary-key metadata
- Plan status and warnings
- Ambiguous and unmatched columns
- AI call count and model
- Generation timestamp and strategy

### 10.3 Column Mapping Entry

Each active mapping contains:

```text
source original name and type
source normalized name
target original name and type
target normalized name
match method
fuzzy and final confidence
confidence breakdown
transformation rule
reason / explainability text
AI participation flag
skip state and reason
primary-key metadata
```

Normalized names are informational. Original names are used in SQL.

### 10.4 Plan Status

| Status | Meaning |
|---|---|
| `complete` | All required source columns are resolved |
| `partial` | Some columns are unmatched/skipped; usable with warnings |
| `ambiguous` | Unresolved AI/matching ambiguity remains |
| `invalid` | Integrity checks failed; output should not be trusted/generated |

A partial plan is not equivalent to a complete validation. Review `unmatched_source_columns`, `unmatched_target_columns`, and skipped mapping reasons.

### 10.5 Example Plan Fragment

```json
{
  "source_table": "source_db.public.orders",
  "target_table": "DEV_BRONZE.MIGRATION.ORDERS",
  "status": "complete",
  "generated_by": "mixed",
  "model_used": "gpt-4o",
  "ai_calls_made": 1,
  "has_fivetran_active": true,
  "stats": {
    "total_source_columns": 8,
    "active_mappings": 8,
    "skipped_mappings": 0,
    "exact_matches": 7,
    "fuzzy_matches": 0,
    "ai_resolved": 1,
    "unmatched_source": 0
  },
  "mappings": [
    {
      "source_column": "created_at",
      "source_type": "timestamp without time zone",
      "target_column": "CREATEDAT",
      "target_type": "TIMESTAMP_NTZ",
      "match_method": "normalized_exact",
      "confidence": 1.0,
      "transformation_rule": "timestamp_ntz",
      "reason": "Matched by normalized_exact"
    }
  ]
}
```

---

## 11. SQL and YAML Generation

### 11.1 Core Principle

Migration Validator **generates** validation SQL and configuration. It does not automatically run all generated comparison queries or certify the migration. An engineer or downstream runner executes and compares the results.

### 11.2 Baseline Eight Queries

The core query set contains four source/target pairs:

| Number | Query | Purpose |
|---|---|---|
| ① | Source row count | Count source rows |
| ② | Target row count | Count active target rows |
| ③ | Source normalized data | Produce comparable source values |
| ④ | Target normalized data | Produce comparable target values |
| ⑤ | Source NULL percentages | Detect source null distribution |
| ⑥ | Target NULL percentages | Detect null drift |
| ⑦ | Source distinct counts | Measure source cardinality |
| ⑧ | Target distinct counts | Detect cardinality drift |

### 11.3 Row Count Pair

```sql
-- Source
SELECT COUNT(*) AS source_row_count
FROM public.orders;

-- Target
SELECT COUNT(*) AS target_row_count
FROM DEV_BRONZE.MIGRATION.ORDERS
WHERE _FIVETRAN_ACTIVE = TRUE;
```

Expected result: counts are equal after applying equivalent business filters.

### 11.4 Normalized Data Pair

For every active mapping, the generator applies a type rule and aliases both sides with the source-column name:

```sql
-- Source fragment
COALESCE(
    CAST(ROUND(CAST(amount AS NUMERIC), 2) AS TEXT),
    '<<NULL>>'
) AS amount_normalized

-- Target fragment
COALESCE(
    CAST(ROUND(CAST(AMOUNT AS NUMBER(38, 2)), 2) AS STRING),
    '<<NULL>>'
) AS amount_normalized
```

Using the same output alias makes exported result sets structurally comparable.

### 11.5 NULL Percentage Pair

Each side returns `total_rows` and one metric per active column:

```sql
ROUND(
    100.0 * SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) / COUNT(*),
    2
) AS amount_null_pct
```

A difference can indicate:

- Unexpected NULL introduction
- NULL replaced with a default
- Source/target filtering mismatch
- Parsing or cast failures during migration

### 11.6 Distinct Count Pair

```sql
COUNT(DISTINCT customer_id) AS customer_id_distinct_count
```

A difference can expose:

- Truncation
- Deduplication errors
- Many source values collapsing to one target value
- Incorrect transformation logic

### 11.7 Output Locations

Typical single-table output:

```text
validation_sql/
└── <table>_validation.sql

config/bronze/data_validation/
└── <table>_validation.yaml

config/bronze/count_validation/
└── bronze_count_validation.yaml
```

Batch output additionally creates per-run and per-table folders:

```text
validation_sql/batch_run_<timestamp>/
├── _manifest.json
├── _execution_log.txt
└── <table>/
    ├── <table>_validation.sql
    ├── <table>_validation.yaml or referenced config path
    ├── <table>_plan.json
    └── <table>_dynamic_suite.sql
```

### 11.8 Data Validation YAML

The per-table YAML contains:

- `data_validation`
- `null_pct_validation`
- `distinct_count_validation`

Example structure:

```yaml
tables:
  orders:
    validations:
      data_validation:
        source_table_name: orders
        source: postgresql
        sourcecolumn: order_id
        sourcequery: |
          SELECT ... FROM public.orders;
        target_table_name: ORDERS
        target: snowflake
        targetcolumn: ORDER_ID
        targetquery: |
          SELECT ... FROM DEV_BRONZE.MIGRATION.ORDERS
          WHERE _FIVETRAN_ACTIVE = TRUE;
```

The queries use YAML literal blocks so they remain readable and executable.

### 11.9 Shared Count YAML

`bronze_count_validation.yaml` collects count-validation blocks for multiple tables. The writer appends entries.

Operational warning: repeated generation can create duplicate YAML table keys. Many YAML parsers silently keep only the last duplicate. For controlled deployments, regenerate the shared file cleanly or deduplicate entries before consumption.

### 11.10 Generated SQL Is Deterministic

Once the plan is fixed, SQL generation does not ask AI to write SQL. Strongly typed rule classes produce expressions. This separation improves auditability and reduces SQL-injection risk.

---

## 12. Command-Line Workflows

Run commands from the project root as:

```bash
python src/validate_cli.py <command> [options]
```

Or enter `src` first:

```bash
cd src
python validate_cli.py <command> [options]
```

### 12.1 Interactive Mode

```bash
python src/validate_cli.py
```

Interactive mode guides the operator through connection, model, schema, and table choices. It is recommended for first use and exploratory generation.

### 12.2 Setup

```bash
python src/validate_cli.py setup
```

Use this to create or update environment configuration. Treat the generated `.env` as secret material.

### 12.3 Single-Table Generation

```bash
python src/validate_cli.py generate \
  --pg-table events \
  --sf-table EVENTS
```

Optional model selection:

```bash
python src/validate_cli.py generate \
  --pg-table events \
  --sf-table EVENTS \
  --model gpt-4o-mini
```

Despite the historical `--pg-table` option name, the project supports additional source extractors; source dialect behavior depends on the selected connection type.

### 12.4 Multi-Table Generation

```bash
python src/validate_cli.py multi \
  --tables events,users,orders
```

With a saved connection profile:

```bash
python src/validate_cli.py multi \
  --connection-profile fms-dev \
  --tables events,users,orders
```

### 12.5 Batch YAML

```bash
python src/validate_cli.py batch --config tables.yaml
```

Preview without connecting or generating:

```bash
python src/validate_cli.py batch \
  --config tables.yaml \
  --dry-run
```

### 12.6 Rules and Models

```bash
python src/validate_cli.py rules
python src/validate_cli.py list-models
python src/validate_cli.py add-rule
```

- `rules` displays built-in and learned rule metadata.
- `list-models` displays supported AI model choices.
- `add-rule` adds a learned rule definition.

### 12.7 Table and Profile Management

```bash
python src/validate_cli.py list-tables
python src/validate_cli.py profiles
python src/validate_cli.py profiles delete fms-dev
```

Profile support avoids repeated credential entry, but profile storage must be protected like any other credential store.

---

## 13. Batch Processing

### 13.1 Purpose

Batch mode processes a declared list of source-target table pairs and creates an auditable run manifest. It supports sequential or parallel operation.

### 13.2 Batch Configuration

```yaml
source:
  type: postgresql
  host: localhost
  port: 5432
  database: source_db
  schema: public
  username: validator_user
  password: ""

target:
  type: snowflake
  account: MY_ORG-MY_ACCOUNT
  database: DEV_BRONZE
  schema: MIGRATION
  username: validator_user
  password: ""

tables:
  - source_table: events
    target_table: EVENTS
    primary_keys: [event_id]

  - source_table: customers
    target_table: CUSTOMERS
    primary_keys: [customer_id]
    explicit_mappings:
      customer_id: CUST_ID

  - source_table: order_lines
    target_table: ORDER_LINES
    primary_keys: [order_id, line_number]
    source_schema: sales
    target_schema: SALES_MIGRATION

execution:
  parallel: true
  max_workers: 4
  fail_fast: false
```

Blank YAML connection fields fall back to environment variables. Prefer environment variables or a secret manager over committed plaintext passwords.

### 13.3 Execution Controls

| Setting | Behavior |
|---|---|
| `parallel` | Uses a thread pool when true and multiple tables exist |
| `max_workers` | Maximum simultaneous table tasks |
| `fail_fast` | Stops/cancels remaining work after a failure when possible |
| `dry_run` | Prints planned operations without extraction or generation |

Do not set worker count solely from CPU availability. Database connection limits, Snowflake warehouse capacity, network bandwidth, and DIAL rate limits are usually more important.

### 13.4 Per-Table Processing

For each table, batch mode:

1. Builds source and Snowflake extractors.
2. Extracts both schemas.
3. Detects `_FIVETRAN_ACTIVE`.
4. Uses configured primary keys or attempts detection.
5. Loads learned corrections.
6. Matches columns.
7. Resolves ambiguous columns with AI when configured.
8. Constructs a canonical plan.
9. Writes plan JSON.
10. Generates SQL and YAML.
11. Attempts to generate the dynamic suite.
12. Records success or failure in the manifest.

Dynamic-suite failure is non-fatal to the baseline artifact generation.

### 13.5 Manifest

`_manifest.json` records:

- Execution ID and timestamps
- Duration
- Source config path
- Total, successful, failed, and skipped table counts
- Per-table output paths
- Matched column count
- Primary keys
- AI call count
- Error text

This file is the primary audit summary for a batch generation run.

### 13.6 Execution Log

`_execution_log.txt` is a human-readable summary. Use the manifest for automation and the log for quick operator review.

---

## 14. Dynamic Validation Suite

### 14.1 Purpose

The baseline checks are universal. The dynamic suite adds checks based on schema meaning. It remains metadata-driven: profiling does not read table rows.

### 14.2 Dynamic Workflow

```text
Source column metadata
        ↓
SchemaProfiler
        ↓
ValidationRuleEngine
        ↓
Optional AI recommendations
        ↓
QueryOptimizer
        ↓
ValidationSuite SQL/YAML
```

### 14.3 Semantic Groups

The profiler classifies columns into:

- `numeric_financial`
- `numeric_quantity`
- `numeric_generic`
- `temporal`
- `identifier`
- `status_flag`
- `text_enum`
- `text_generic`
- `skipped`

Classification uses names and types. For example:

- `invoice_amount NUMERIC` → financial
- `item_qty INTEGER` → quantity
- `customer_id BIGINT NOT NULL` → identifier and likely business key
- `is_active BOOLEAN` → status flag
- `order_status VARCHAR` → text enum

JSON, arrays, bytea, hstore, and similar complex types are skipped by the profiler for aggregate profiling, even though some can still be normalized by the baseline rule system.

### 14.4 Dynamic Requirements

Always requested:

- Row count
- Normalized data validation
- NULL percentage
- Distinct count

Conditionally requested:

| Condition | Added check |
|---|---|
| Numeric columns exist | MIN/MAX |
| Financial or quantity columns exist | SUM reconciliation |
| Non-null identifier/business key exists | Duplicate check |
| Status or enum columns exist | Value-distribution proxy |

### 14.5 Query Optimization

NULL percentage, distinct count, MIN/MAX, SUM, and value-distribution metrics are combined into one aggregate query per database. This reduces scans and warehouse cost.

Instead of many queries:

```sql
SELECT MIN(amount), MAX(amount) FROM orders;
SELECT SUM(amount) FROM orders;
SELECT COUNT(DISTINCT status) FROM orders;
```

The optimizer creates one query:

```sql
SELECT
    COUNT(*) AS total_rows,
    ROUND(100.0 * SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 4) AS amount_null_pct,
    COUNT(DISTINCT status) AS status_distinct_count,
    MIN(amount) AS amount_min,
    MAX(amount) AS amount_max,
    SUM(amount) AS amount_sum
FROM public.orders;
```

### 14.6 Duplicate Check

For detected business keys:

```sql
SELECT
    customer_id,
    COUNT(*) AS duplicate_count
FROM public.customers
GROUP BY customer_id
HAVING COUNT(*) > 1;
```

Expected result: zero rows, unless duplicates are valid by business design.

This heuristic treats non-null identifier-like columns as business keys. It can produce false assumptions for foreign keys, so review the selected key columns.

### 14.7 AI Recommendations in Dynamic SQL

AI recommendations are included as reviewed condition fragments and example wrapper queries. They should not be accepted blindly. Confirm business meaning, SQL dialect, NULL semantics, and expected severity.

---

## 15. Learning and Rule Customization

### 15.1 Two Learning Concepts

The project distinguishes:

1. **Learned corrections** — confirmed source-to-target mappings and correct rule IDs.
2. **Learned rule metadata** — custom rule descriptions added through the rule book.

Both are stored in `src/rule_book_learned.json`.

### 15.2 Feedback Recording

A correction may contain:

```json
{
  "source_column": "created_at",
  "target_column": "CREATED_TIMESTAMP",
  "source_type": "timestamp without time zone",
  "target_type": "TIMESTAMP_NTZ",
  "correct_rule": "timestamp_ntz",
  "reason": "Approved migration mapping",
  "table_name": "orders",
  "corrected_at": "2026-08-13T12:00:00"
}
```

If the same source-target pair is recorded again, it is updated rather than duplicated.

### 15.3 How Learning Affects Future Runs

Learned corrections:

- Add a `0.15` confidence factor for an exact learned pair.
- May appear in focused AI prompts.
- Provide human history for mapping review.

Learning does not silently change database contents or execute SQL.

### 15.4 Important Custom-Rule Boundary

Built-in Python rule classes own executable SQL generation. Learned rule entries primarily provide metadata and AI context. Adding text templates to the learned JSON does not automatically create a new executable Python transformation class.

To add a genuinely new SQL transformation:

1. Implement a rule class in `src/rules/`.
2. Register its source/target type matching.
3. Add rule metadata to `src/rules_catalog.json`.
4. Add its ID to AI response validation if AI may choose it.
5. Review both PostgreSQL/source and Snowflake expressions.

This prevents arbitrary learned text from being injected directly into generated SQL.

---

## 16. How to Execute and Interpret Validation

### 16.1 Recommended Sequence

1. Review the plan and mapping summary.
2. Review skipped and ambiguous columns.
3. Run source row count.
4. Run target row count.
5. Run NULL and distinct aggregate checks.
6. Run dynamic aggregate and duplicate checks when available.
7. Run normalized full-data queries.
8. Compare results with a deterministic method.
9. Record evidence and disposition for every mismatch.

### 16.2 Comparison Outcomes

| Check | Pass condition |
|---|---|
| Row count | Source count equals filtered target count |
| NULL percentage | Same value per mapped column, within approved tolerance |
| Distinct count | Same cardinality or an explicitly approved difference |
| MIN/MAX | Same normalized boundaries |
| SUM | Same value after approved precision handling |
| Duplicate check | Same result; normally zero rows |
| Normalized full data | Equivalent rows and values under a stable key/order strategy |

### 16.3 Full-Data Comparison Requires Stable Alignment

A raw `SELECT` without `ORDER BY` does not guarantee row order. Therefore, do not compare two exports by line number unless both are explicitly sorted by the same stable key.

Preferred methods:

- Sort both result sets by a validated primary/composite key.
- Load normalized exports into a comparison engine and join by key.
- Compare canonical row hashes only after stable column and NULL normalization.
- Use multiset comparison when no reliable key exists.

### 16.4 Classifying Mismatches

A mismatch should be classified before changing a rule:

- **Real migration defect:** target value is wrong or missing.
- **Mapping defect:** source column mapped to wrong target.
- **Normalization gap:** equivalent values represented differently.
- **Filter mismatch:** source and target populations differ.
- **Precision policy:** approved rounding differs from default two decimals.
- **Expected transformation:** business-approved change.
- **Comparison-order issue:** rows are equal but exports are not aligned.

### 16.5 Test Dataset

The `dummy-data/` scripts provide PostgreSQL and Snowflake tables covering:

- Text whitespace
- Intentional text case mismatch
- Boolean values and NULL
- Integer limits
- Numeric precision
- Dates and timestamps
- Time-zone normalization
- UUID case
- JSON key order
- Binary encoding
- HSTORE limitations
- All-NULL rows
- Empty strings
- Intentional numeric and boolean mismatches

`dummy-data/TEST_CASES.md` explains expected behavior. These scripts are useful for demonstrations and manual acceptance exercises.

---

## 17. Failure Handling and Troubleshooting

### 17.1 Connection Failures

Symptoms:

- Authentication error
- Timeout
- Host not found
- Database/schema missing
- Permission denied

Actions:

1. Confirm the selected source slot/profile.
2. Verify host, port, database, and schema.
3. Confirm read-only metadata permissions.
4. Confirm firewall, VPN, proxy, and DNS access.
5. For Snowflake, verify account identifier, warehouse, role, and schema grants.
6. For Athena, verify IAM, Glue, workgroup, and S3 result permissions.

### 17.2 No Columns Returned

Likely causes:

- Wrong schema or table case
- Table is a view unsupported by a particular extractor query
- Metadata permissions missing
- Database selected correctly but schema selected incorrectly

Do not generate artifacts from an empty schema without investigating.

### 17.3 Unexpected Unmatched Columns

Actions:

1. Compare original and normalized names.
2. Confirm the target extraction contains the expected column.
3. Check whether another source column already consumed the target candidate.
4. Inspect type compatibility and positions.
5. Add an explicit mapping for known renames.
6. Record a learned correction after human confirmation.

### 17.4 Wrong Normalization Rule

Check:

- Extracted source and target type names
- Rule registry matching order
- AI-selected rule, if applicable
- Whether the migration intentionally converted the physical type

For example, a timestamp migrated to `VARCHAR` may need text treatment rather than timestamp formatting, depending on the stored target format.

### 17.5 AI Not Used

Expected causes:

- All columns resolved deterministically
- `DIAL_API_KEY` absent
- No decision falls between confidence thresholds
- AI package unavailable

Zero AI calls can be a successful and desirable result.

### 17.6 AI API Errors

The baseline workflow falls back to fuzzy matching. Review console warnings and plan confidence before accepting output. Common causes:

- Invalid key
- EPAM network/VPN unavailable
- Wrong endpoint/version
- Unsupported deployment name
- Rate limits
- Invalid response format

### 17.7 Incorrect Target Counts with Fivetran

Check whether `_FIVETRAN_ACTIVE` exists and whether active filtering matches the connector's history model. Some tables may use `_FIVETRAN_DELETED` instead or may not have an active marker.

### 17.8 YAML Problems

Common issues:

- Duplicate keys in shared count YAML
- Manual indentation edits
- Consumer does not support block scalar SQL
- Multiple runs append stale entries

Treat generated YAML as an artifact. Prefer regeneration over manual repair, and validate duplicate-key handling in the downstream parser.

### 17.9 Large Tables

Full normalized scans can be expensive. Recommended approach:

1. Run count and aggregate checks first.
2. Use a reviewed date/partition filter if supported by your process.
3. Compare deterministic samples for triage only.
4. Reserve full scans for release gates or approved windows.
5. Monitor Snowflake warehouse cost and source production impact.

Sampling is not proof of full migration correctness.

---

## 18. Security and Governance

### 18.1 Credential Handling

- Never commit `.env`.
- Do not place passwords in batch YAML committed to Git.
- Restrict profile-file permissions.
- Rotate exposed credentials immediately.
- Prefer environment injection or an enterprise secret manager.

### 18.2 Least Privilege

Source accounts normally need:

- Connect permission
- Metadata/schema read permission
- `SELECT` on validated tables when executing generated SQL

Snowflake accounts normally need:

- Usage on warehouse, database, and schema
- `SELECT` on target tables

The generator does not require write privileges.

### 18.3 AI Data Boundary

Only metadata should be sent to DIAL. Before extending prompts, enforce this rule:

> Do not send credentials, connection strings, row values, customer records, or exported query results to the model.

### 18.4 Artifact Sensitivity

Generated SQL and plans can reveal:

- Internal server/schema naming
- Table and column names
- Business-domain structure
- AI reasoning and migration conventions

Store artifacts in approved repositories and apply normal access controls.

### 18.5 Auditability

For each release, retain:

- Source revision/commit
- Environment identifier without passwords
- Generated plan JSON
- SQL and YAML artifacts
- Batch manifest and execution log
- Query results or hashes
- Approved exceptions
- Reviewer and timestamp

---

## 19. Developer Extension Guide

### 19.1 Adding a Source Database

Implement or extend the extractor abstraction so it can:

1. Connect using source-specific credentials.
2. List schemas/tables where required.
3. Return standard `ColumnMetadata`.
4. Detect primary keys where possible.
5. Quote identifiers correctly.
6. Generate source-dialect normalization expressions or map into existing rule behavior.
7. Register the extractor in `ExtractorFactory`.

Do not let source-specific metadata leak into matching logic; normalize it at the extractor boundary.

### 19.2 Adding a New Type Rule

A type rule needs:

- Source type triggers
- Target type triggers
- Source SQL expression
- Snowflake SQL expression
- NULL-safe wrapping through the base rule pattern
- Human-readable metadata
- AI-recognized rule ID when applicable

Verify semantic equivalence, not merely SQL syntax. For example, JSON text equality depends on canonical serialization.

### 19.3 Changing Matching Thresholds

Use environment configuration:

```bash
FUZZY_HIGH_CONFIDENCE=0.95
FUZZY_AI_REVIEW=0.75
```

Lower thresholds increase automatic mappings but also increase false-match risk. Raise thresholds for regulated or high-impact migrations.

### 19.4 Extending Confidence Evidence

If adding factors:

- Keep scoring explainable.
- Ensure weights sum to `1.0` or normalize them.
- Include factor values in `confidence_breakdown`.
- Avoid row-level data unless explicitly approved.
- Preserve deterministic behavior.

### 19.5 Adding Dynamic Checks

Add a typed `ValidationType`, update `ValidationRuleEngine`, then implement optimizer generation. Keep SQL generation deterministic; AI may recommend a check but should not be the only source of executable production SQL.

### 19.6 Module Dependency Direction

Preferred dependency flow:

```text
CLI / batch
    ↓
Pipeline orchestration
    ↓
Extractors + matching + AI metadata decisions
    ↓
Canonical plan
    ↓
Rules + SQL/YAML generators
```

Avoid making rule classes depend on CLI, connection profiles, or batch modules.

---

## 20. Operational Recommendations

### 20.1 Before Generation

- Confirm source and target environments.
- Confirm schema/table pairs.
- Confirm Fivetran history semantics.
- Define explicit mappings for known renames.
- Define acceptable precision and timezone policies.
- Use read-only accounts.

### 20.2 During Generation

- Review AI and fallback warnings.
- Track plan status.
- Investigate every unmatched column.
- Limit batch concurrency to infrastructure capacity.
- Keep manifests for every batch.

### 20.3 Before Executing SQL

- Review generated identifiers and dialect.
- Confirm target active-row filter.
- Estimate query cost.
- Add only business-approved filters.
- Establish stable row alignment for full-data comparison.

### 20.4 Release Gate

A migration should not pass merely because files were generated. A strong gate requires:

- Complete or approved partial plan
- All mappings reviewed above the project's risk threshold
- Counts reconciled
- Aggregate metrics reconciled
- Full-data or approved equivalent comparison completed
- Exceptions documented and approved
- Evidence retained

---

## 21. End-to-End Reference

### 21.1 Example Scenario

Source:

```text
PostgreSQL: source_db.public.orders
```

Target:

```text
Snowflake: DEV_BRONZE.MIGRATION.ORDERS
```

Known rename:

```text
customer_id → CUST_ID
```

### 21.2 Batch Entry

```yaml
- source_table: orders
  target_table: ORDERS
  primary_keys: [order_id]
  explicit_mappings:
    customer_id: CUST_ID
```

### 21.3 Internal Processing

```text
1. Extract source and target column metadata.
2. Detect _FIVETRAN_ACTIVE in Snowflake.
3. Apply customer_id → CUST_ID configured mapping.
4. Match order_id → ORDER_ID exactly.
5. Normalize created_at and CREATEDAT → normalized exact.
6. Rank unresolved candidates.
7. AI resolves only genuinely ambiguous columns.
8. Assign type-specific rule objects.
9. Build CanonicalValidationPlan.
10. Generate baseline SQL and YAML.
11. Profile schema and create dynamic aggregate/duplicate checks.
12. Write batch manifest.
```

### 21.4 Human Validation

```text
1. Review plan JSON.
2. Verify no unexplained skipped columns.
3. Run counts on source and target.
4. Compare NULL%, distinct, MIN/MAX, and SUM metrics.
5. Run duplicate checks.
6. Run normalized SELECTs.
7. Align results by order_id.
8. Investigate differences.
9. Record approved corrections for future runs.
10. Archive evidence with the manifest.
```

---

## 22. Current Boundaries and Important Caveats

1. **Generation is not execution.** The project produces queries and configurations; a human or external runner must execute and evaluate them.
2. **Generation success is not validation success.** A generated file can contain a partial or fallback mapping.
3. **Fuzzy fallback requires review.** When AI is unavailable, ambiguous columns may be accepted using the top fuzzy candidate.
4. **Full-data result order is not guaranteed.** Compare by stable keys or as multisets, not raw output order.
5. **Primary-key support is informational in the canonical plan.** Baseline query generation is primarily key-independent; business-key duplicate checks are generated by the dynamic suite when heuristics detect suitable identifiers.
6. **Dynamic business-key detection is heuristic.** A non-null foreign key can look like a unique business key and must be reviewed.
7. **The default numeric policy is two decimal places.** This may be unsuitable for rates, scientific values, coordinates, or high-precision finance.
8. **Text normalization is case-sensitive after trimming.** This intentionally exposes case changes unless a reviewed custom implementation says otherwise.
9. **Complex-type handling varies.** Baseline rules support several complex types, while the dynamic profiler skips them for aggregate analysis.
10. **HSTORE may remain format-sensitive.** PostgreSQL HSTORE text and Snowflake JSON-like strings can differ structurally.
11. **Shared count YAML is append-oriented.** Repeated runs can create duplicate table keys unless outputs are cleaned or merged carefully.
12. **Source dialect coverage must be reviewed.** Some module names and comments retain PostgreSQL terminology even though MS SQL Server and Athena extractors exist; generated source expressions must be checked for the selected dialect.
13. **AI suggestions are advisory.** Business-rule recommendations require human approval before use as release criteria.

---

## Final Summary

Migration Validator turns live source and Snowflake metadata into an explainable validation plan, applies deterministic normalization rules, selectively uses AI for ambiguous metadata decisions, and generates auditable SQL/YAML artifacts. Its reliability comes from four controls:

1. **Deterministic-first matching** minimizes AI dependency.
2. **Canonical planning** keeps SQL and YAML synchronized.
3. **Typed rule classes** keep executable SQL controlled and reviewable.
4. **Human review and execution** remain the final authority for migration acceptance.

Used with explicit mappings, stable row alignment, least-privilege access, reviewed tolerances, and retained manifests, the project provides a scalable foundation for validating PostgreSQL, MS SQL Server, or Athena migrations into Snowflake.

---

**End of Complete Documentation — Part 2 of 2**
