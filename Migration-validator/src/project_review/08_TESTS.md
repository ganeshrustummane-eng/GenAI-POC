# 08 — Test Suite

## Summary

| File | Tests | Status |
|------|-------|--------|
| `tests/test_query_optimizer.py` | 19 | All passing |
| `tests/test_schema_profiler.py` | 35 | All passing |
| `tests/test_suite_generator.py` | 21 | All passing |
| `tests/test_validation_rule_engine.py` | 30 | All passing |
| **Total** | **107** | **All passing** |

Evidence: `.pytest_cache/v/cache/lastfailed` = `{}` (empty dict = zero failures recorded).

---

## How to Run

```bash
cd C:\EPAM-Personal\Migration-validator\src
pytest tests/ -v
```

No database connection needed — all tests use mock/in-memory data.

---

## test_query_optimizer.py — 19 Tests

Tests the `dynamic_suite/query_optimizer.py` which collapses multiple aggregate queries into one scan.

### Class: TestRowCountQueries (5 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_row_count_always_generated` | Row count queries are always present, even for a minimal table |
| `test_source_sql_contains_count_star` | Source SQL contains `SELECT COUNT(*)` |
| `test_target_sql_contains_count_star` | Target SQL contains `SELECT COUNT(*)` |
| `test_fivetran_filter_present_when_active` | When `has_fivetran_active=True`, target SQL has `WHERE _FIVETRAN_ACTIVE = TRUE` |
| `test_fivetran_filter_absent_when_inactive` | When `has_fivetran_active=False`, no Fivetran filter in SQL |

### Class: TestCombinedAggregate (7 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_exactly_one_combined_aggregate_query` | All aggregates (NULL%, distinct, MIN/MAX, SUM) collapse into exactly 1 query pair |
| `test_null_pct_present_in_combined_sql` | Combined SQL contains `null_pct` expressions |
| `test_distinct_count_present_in_combined_sql` | Combined SQL contains `distinct_count` expressions |
| `test_sum_for_financial_columns` | SUM aggregate present for NUMERIC_FINANCIAL columns |
| `test_min_max_for_numeric_columns` | MIN/MAX present for numeric columns |
| `test_fewer_queries_than_naive` | Total query count < naive (separate-scan) count |
| `test_combined_sql_one_select_per_side` | Only one SELECT statement in combined aggregate per database side |

### Class: TestDuplicateCheck (4 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_not_generated_for_nullable_id` | Duplicate check NOT generated when the id column is nullable |
| `test_generated_for_not_null_id` | Duplicate check IS generated when id is NOT NULL |
| `test_sql_has_group_by_having_count` | SQL structure: `GROUP BY <pk_cols> HAVING COUNT(*) > 1` |
| `test_comparison_note_says_zero_rows` | Comparison note says "expect 0 rows" |

### Class: TestTextOnlyTable (3 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_no_sum_for_text_only_table` | SUM not generated when table has no numeric columns |
| `test_no_min_max_for_text_only_table` | MIN/MAX not generated for text-only table |
| `test_null_pct_still_present` | NULL% always present regardless of column types (baseline) |

---

## test_schema_profiler.py — 35 Tests

Tests the `profiling/schema_profiler.py` column classification logic.

### Class: TestFinancialColumns (5 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_amount_is_financial` | Column named `amount` with numeric type → NUMERIC_FINANCIAL |
| `test_balance_is_financial` | Column named `balance` with numeric type → NUMERIC_FINANCIAL |
| `test_price_is_financial` | Column named `price` with numeric type → NUMERIC_FINANCIAL |
| `test_salary_integer_is_financial` | Column named `salary` with integer type → NUMERIC_FINANCIAL (name keyword wins) |
| `test_count_is_not_financial` | Column named `count` → NUMERIC_QUANTITY, not FINANCIAL |

### Class: TestQuantityColumns (4 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_quantity_column` | `quantity` → NUMERIC_QUANTITY |
| `test_qty_column` | `qty` → NUMERIC_QUANTITY |
| `test_units_in_stock` | `units_in_stock` → NUMERIC_QUANTITY |
| `test_item_count` | `item_count` → NUMERIC_QUANTITY |

### Class: TestIdentifierColumns (4 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_id_column` | `id` → IDENTIFIER |
| `test_customer_id` | `customer_id` → IDENTIFIER |
| `test_uuid_type` | Any column with `uuid` type → IDENTIFIER |
| `test_not_null_id_is_business_key` | NOT NULL id column → `business_key = True` |
| `test_nullable_id_is_not_business_key` | nullable id → `business_key = False` |

### Class: TestTemporalColumns (4 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_date_type` | `date` type → TEMPORAL |
| `test_timestamp_ntz` | `timestamp without time zone` → TEMPORAL |
| `test_timestamp_tz` | `timestamp with time zone` → TEMPORAL |
| `test_timestamptz_shorthand` | `timestamptz` → TEMPORAL |

### Class: TestStatusFlagColumns (5 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_boolean_type` | `boolean` type → STATUS_FLAG |
| `test_is_prefix` | `is_active` → STATUS_FLAG |
| `test_has_prefix` | `has_errors` → STATUS_FLAG |
| `test_active_column` | `active` → STATUS_FLAG |
| `test_can_prefix` | `can_edit` → STATUS_FLAG |

### Class: TestTextEnumColumns (4 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_status_column` | `status` varchar → TEXT_ENUM |
| `test_account_type` | `account_type` varchar → TEXT_ENUM |
| `test_order_state` | `order_state` varchar → TEXT_ENUM |
| `test_category_column` | `category` varchar → TEXT_ENUM |

### Class: TestSkippedColumns (4 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_json_type` | `json` type → SKIPPED |
| `test_jsonb_type` | `jsonb` type → SKIPPED |
| `test_bytea_type` | `bytea` type → SKIPPED (no validation generated for binary) |
| `test_array_type` | `array` type → SKIPPED |

### Class: TestTableProfile (5 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_has_financial` | `TableProfile.has_financial` True when financial columns present |
| `test_has_temporal` | `TableProfile.has_temporal` True when temporal columns present |
| `test_has_identifiers` | `TableProfile.has_identifiers` True when identifier columns present |
| `test_business_keys` | `business_keys` property returns only NOT NULL identifier columns |
| `test_skipped_columns` | `skipped_columns` property returns only SKIPPED group columns |

---

## test_suite_generator.py — 21 Tests

Tests the full `dynamic_suite/suite_generator.py` end-to-end (with mocked AI recommendations).

### Class: TestSuiteStructure (8 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_returns_validation_suite` | Returns a `ValidationSuite` instance |
| `test_source_table_set` | Source table name populated correctly |
| `test_target_table_set` | Target table name populated correctly |
| `test_has_queries` | Suite has at least one query |
| `test_has_requirements` | Suite has at least one requirement |
| `test_profile_attached` | `suite.profile` is a `TableProfile` |
| `test_fivetran_propagated` | `has_fivetran_active` propagated from input to suite |
| `test_baseline_queries_present` | `baseline_queries` property returns non-empty list |

### Class: TestCombinedSqlOutput (5 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_combined_sql_not_empty` | `to_combined_sql()` returns non-empty string |
| `test_combined_sql_has_source_target_headers` | SQL contains `SOURCE` and `TARGET` labels |
| `test_fivetran_filter_in_sql_when_active` | Fivetran filter in combined SQL when active |
| `test_no_fivetran_filter_when_inactive` | No Fivetran filter when not active |
| `test_multiple_select_statements` | Combined SQL has multiple SELECT statements |

### Class: TestOrdersTableSuite (5 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_conditional_queries_present` | Conditional queries present for orders table with amounts |
| `test_sum_in_sql` | SUM expression present in SQL for amount columns |
| `test_min_max_in_sql` | MIN/MAX present in SQL |
| `test_duplicate_check_present` | Duplicate check present (orders has NOT NULL id) |
| `test_null_pct_present` | NULL% always in SQL |

### Class: TestSummaryDict (3 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_expected_keys` | Summary dict has required keys: table, profile, requirements, queries, etc. |
| `test_requirements_listed` | Requirements listed in summary |
| `test_baseline_count_positive` | `baseline_count > 0` in summary |

---

## test_validation_rule_engine.py — 30 Tests

Tests `profiling/validation_rule_engine.py` — which extra checks get generated for which table types.

### Class: TestBaselineAlwaysPresent (4 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_row_count_always_generated` | `ROW_COUNT` requirement always in output |
| `test_data_validation_always_generated` | `DATA_VALIDATION` requirement always in output |
| `test_null_pct_always_generated` | `NULL_PCT` requirement always in output |
| `test_distinct_count_always_generated` | `DISTINCT_COUNT` requirement always in output |

### Class: TestMinMax (5 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_min_max_triggered_by_financial` | MIN_MAX generated when table has NUMERIC_FINANCIAL columns |
| `test_min_max_triggered_by_quantity` | MIN_MAX generated when table has NUMERIC_QUANTITY columns |
| `test_min_max_triggered_by_generic_numeric` | MIN_MAX generated for NUMERIC_GENERIC columns |
| `test_min_max_not_for_text_only` | MIN_MAX NOT generated for text-only table |
| `test_min_max_not_for_temporal_only` | MIN_MAX NOT generated for temporal-only table |

### Class: TestSum (5 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_sum_triggered_by_amount` | SUM generated for column named `amount` |
| `test_sum_triggered_by_balance` | SUM generated for `balance` |
| `test_sum_triggered_by_quantity` | SUM generated for quantity-group columns |
| `test_sum_not_for_generic_score` | SUM NOT generated for generic numeric (score, rating) |
| `test_sum_not_for_text_table` | SUM NOT generated for text-only table |

### Class: TestDuplicateCheck (5 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_duplicate_check_triggered_by_not_null_id` | DUPLICATE_CHECK generated for NOT NULL `id` column |
| `test_duplicate_check_not_for_nullable_id` | DUPLICATE_CHECK NOT generated for nullable id |
| `test_duplicate_check_not_for_text_table` | DUPLICATE_CHECK NOT generated for text-only table with no identifier |
| `test_duplicate_check_columns_include_id` | The requirement's `columns` field contains the id column |
| `test_duplicate_check_is_conditional` | `is_conditional = True` on the requirement |

### Class: TestValueDistribution (5 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_value_dist_triggered_by_boolean` | VALUE_DIST generated for boolean column |
| `test_value_dist_triggered_by_status_varchar` | VALUE_DIST generated for `status` varchar column |
| `test_value_dist_triggered_by_type_column` | VALUE_DIST generated for `type` varchar column |
| `test_value_dist_not_for_numeric_only` | VALUE_DIST NOT generated for numeric-only table |
| `test_value_dist_columns_include_status` | The requirement's `columns` field contains the status column |

### Class: TestFullOrdersTable (6 tests)

| Test | What It Verifies |
|------|-----------------|
| `test_all_baseline_present` | All 4 baseline requirements present |
| `test_all_conditional_triggered` | All 4 conditional requirements triggered for a full orders table |
| `test_correct_columns_for_sum` | SUM requirement references amount/price columns, not id |
| `test_correct_columns_for_min_max` | MIN_MAX references numeric columns |
| `test_correct_columns_for_value_dist` | VALUE_DIST references status/boolean columns |
| `test_baseline_before_conditional` | Baseline requirements come before conditional in the list |
