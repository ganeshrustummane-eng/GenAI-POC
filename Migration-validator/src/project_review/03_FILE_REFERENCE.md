# 03 — File-by-File Reference

Every file in the project, grouped by folder, with a plain-language description of what it does.

---

## Root Level Files

| File | Lines | What It Does |
|------|-------|--------------|
| `__init__.py` | ~15 | Package init. Declares `__version__ = "2.0.0"`. Exports the main public API. |
| `README.md` | ~200 | Full architecture guide: all modules, 11 rules, pipeline modes, env vars, quick start. |
| `validate_cli.py` | 1013 | **Primary entry point.** Interactive Click CLI with menu. `generate`, `rules`, `add-rule`, `list-models`, `list-tables` commands. Calls `ValidationPipeline.run_with_plan()`. |
| `validation_pipeline.py` | 703 | **Core orchestrator.** `run()` = legacy 3-step; `run_with_plan()` = new 7-step plan-driven flow. |
| `query_builder.py` | 809 | Connects to both DBs, extracts schema, asks AI for rules, builds 8 SQL queries — without executing them. |
| `query_executor.py` | 867 | Executes generated SQL against live PG + SF. Prints coloured PASS/WARN/FAIL verdicts in terminal. |
| `model_probe.py` | ~120 | Tests which DIAL models actually respond. 24h disk cache. 6-thread parallel probing. |
| `rule_book.py` | ~150 | `RuleBook` loads `rules_catalog.json` + `rule_book_learned.json`. Builds prompt text block from all rules. |
| `models.py` | ~120 | All shared dataclasses and enums: `DatabaseType`, `ColumnMapping`, `ValidationReport`, etc. |
| `database_connectors.py` | ~200 | DB connection classes: `MSSQLConnector`, `PostgreSQLConnector`, `SnowflakeConnector`, `ConnectorFactory`. |
| `schema_extractor.py` | ~200 | Legacy PG + SF schema extractors + `SchemaComparator`. |
| `schema_discovery.py` | ~100 | Legacy: generates `information_schema` SQL for 3 DB types. |
| `transformation_rules.py` | ~300 | Legacy: 14 rule classes + `TransformationRulesEngine` chain executor. |
| `sql_generators.py` | ~250 | Legacy: `MSSQLGenerator`, `PostgreSQLGenerator`, `SnowflakeGenerator`, `QueryGenerator`. |
| `ai_query_agent.py` | ~300 | Legacy: `AIQueryAgent` — sends full schema to AI in one call. |
| `dynamic_validator.py` | ~300 | Legacy: live 5-step validation pipeline (extract → AI plan → completeness → status → report). |
| `report_generator.py` | ~250 | Legacy: JSON / HTML / plain-text report generation. |
| `validator.py` | ~150 | Legacy: `DataValidator` — row-count + per-column match counting. |
| `main_dynamic.py` | ~150 | New primary entry point with hard-coded table config (developer's own env). |
| `main_example.py` | ~200 | Legacy example. **CONTAINS HARD-CODED CREDENTIALS. Do not share.** |
| `ai_cli.py` | ~150 | Alternative Click CLI: `discover` (prints schema SQL) + `generate` (runs AIQueryAgent). |
| `verify_yaml_generation.py` | ~80 | Test script (not pytest). Builds mock data and tests YAML generation without DB. |
| `check_connections.py` | ~120 | 6-step health check: packages → env vars → PG → SF → DIAL API → module imports. |
| `rules_catalog.json` | ~400 | Machine-readable rule definitions v3.0. 13 rules with PG + SF SQL templates. Source of truth. |
| `rule_book_learned.json` | ~30 | Auto-generated learned rules. One entry (`ex_strip`) added 2026-08-10 as test/example. |

---

## `rules/` Package — Type Normalisation Rules

Each rule wraps a column expression in `COALESCE(CAST(...), '<<NULL>>')` so PG and SF can be compared as text.

| File | Rule Name | What It Normalises |
|------|-----------|-------------------|
| `base_rule.py` | (base) | ABC + `RuleRegistry` + `NULL_PLACEHOLDER = "<<NULL>>"` |
| `__init__.py` | (registry) | Creates global registry. Registration order matters (Text is last/wildcard). |
| `boolean_rule.py` | boolean | TRUE/FALSE/t/f/yes/no → string `'TRUE'` or `'FALSE'` |
| `numeric_rule.py` | numeric | NUMERIC/DECIMAL/FLOAT → ROUND to 10 decimal places, cast to TEXT |
| `timestamp_ntz_rule.py` | timestamp_ntz | TIMESTAMP WITHOUT TIME ZONE → ISO 8601 format |
| `timestamp_tz_rule.py` | timestamp_tz | TIMESTAMP WITH TIME ZONE → UTC → ISO 8601 |
| `date_rule.py` | date | DATE → `'YYYY-MM-DD'` string |
| `text_rule.py` | text | Catch-all: TRIM + UPPER on both sides |
| `uuid_rule.py` | uuid | UUID → `UPPER(CAST AS TEXT)` |
| `integer_rule.py` | integer | SMALLINT/INT/BIGINT/SERIAL → `CAST AS TEXT` |
| `json_rule.py` | json | JSON/JSONB → both cast to TEXT |
| `bytea_rule.py` | bytea | BYTEA → hex encoding |
| `hstore_rule.py` | hstore | HSTORE (user-defined PG type) → CAST AS TEXT |
| `null_rule.py` | null_placeholder | COALESCE(col, '<<NULL>>') — the universal null wrapper |

---

## `sql_extractor/` Package

| File | What It Does |
|------|--------------|
| `base_extractor.py` | `ColumnMetadata` + `TableMetadata` dataclasses. `BaseExtractor` ABC. |
| `postgres_extractor.py` | Queries `information_schema.columns`. Detects USER-DEFINED types (hstore, citext) via `udt_name`. |
| `snowflake_extractor.py` | Same but for Snowflake. Detects `_FIVETRAN_ACTIVE` column. Column names returned in UPPERCASE. |

---

## `ai_transformation/` Package (legacy AI path)

| File | What It Does |
|------|--------------|
| `ai_rule_mapper.py` | 26-model `AVAILABLE_MODELS` list. `AzureOpenAI` client. Falls back to static on error. |
| `static_rule_mapper.py` | Rule assignment by name heuristics + `rules_catalog.json` trigger pairs. No AI. |
| `orchestrator.py` | `RuleMapperOrchestrator`: tries AI first, falls back to static. Used by legacy `run()`. |

---

## `generated_queries/` Package

| File | What It Does |
|------|--------------|
| `sql_query_generator.py` | Builds 8 SQL strings into `ValidationQuerySet`. Has both `generate()` (from ColumnMapping) and `generate_from_plan()` (from CanonicalValidationPlan). |
| `yaml_config_writer.py` | Writes 4-block YAML file: row_count_check, data_completeness, null_percentage, distinct_count. |
| `query_output_manager.py` | Orchestrates SQL + YAML generation. Saves files to `validation_sql/`. Returns `GenerationResult`. |

---

## `matching/` Package

| File | What It Does |
|------|--------------|
| `normalizer.py` | `normalize_column_name()`: lowercase + remove all non-alphanumeric chars. |
| `exact_matcher.py` | 3-priority matching: configured → case-insensitive exact → normalized name. |
| `fuzzy_matcher.py` | RapidFuzz `token_ratio` scoring. Difflib fallback. Returns top-N candidates. |
| `confidence.py` | Weighted confidence score: name_similarity (40%) + type_compat (35%) + position (10%) + learned (15%). 40+ known type-compatibility pairs. |
| `candidate_matcher.py` | Classifies each column: `resolved` (≥0.95) / `ai_needed` (0.75–0.95) / `unmatched` (<0.75). |

---

## `core/` Package

| File | What It Does |
|------|--------------|
| `validation_plan.py` | `CanonicalValidationPlan` — the central data object for the v2 pipeline. `ColumnMappingEntry` — one per column pair. `PlanStatus` + `MatchMethod` enums. |

---

## `ai/` Package (new AI path)

| File | What It Does |
|------|--------------|
| `prompt_builder.py` | Builds the system prompt (rules + JSON contract) and user prompt (one ambiguous column + candidates). Sends only what's needed — no full schema. |
| `response_parser.py` | Validates AI response: status must be resolved/ambiguous, target must be from provided candidates (no hallucinated names), rule must be a known ID. |
| `rule_planner.py` | Calls AI once per ambiguous column. Falls back to best fuzzy candidate on error. Assembles `PlannerResult`. |

---

## `validation/` Package

| File | What It Does |
|------|--------------|
| `plan_validator.py` | 8-check integrity validation on the plan before SQL generation. Raises `PlanValidationError` on critical failures. |

---

## `profiling/` Package

| File | What It Does |
|------|--------------|
| `schema_profiler.py` | Classifies columns into 9 `ColumnGroup` types using name + type heuristics. Produces `TableProfile`. |
| `validation_rule_engine.py` | Decides which extra checks (MIN/MAX, SUM, DUPLICATE_CHECK, VALUE_DIST) are needed based on `TableProfile`. |
| `ai_recommendation.py` | Optional: asks AI to suggest business-rule checks. Validates AI only references real column names. |

---

## `dynamic_suite/` Package

| File | What It Does |
|------|--------------|
| `validation_suite.py` | `GeneratedQuery` + `ValidationSuite` dataclasses. `to_combined_sql()` produces one labelled SQL file. |
| `query_optimizer.py` | Collapses NULL% + DISTINCT + MIN/MAX + SUM + VALUE_DIST into ONE SELECT per side (one table scan). |
| `suite_generator.py` | 5-step orchestration: profile → decide → AI recommend → optimize → assemble suite. |

---

## `learning/` Package

| File | What It Does |
|------|--------------|
| `retrieval.py` | `LearnedRuleRetriever`: loads `rule_book_learned.json`, scores matches, injects into AI prompt. |
| `feedback.py` | `FeedbackRecorder`: persists human corrections back to `rule_book_learned.json`. Deduplicates by column pair. `prompt_for_feedback()` for CLI interaction. |

---

## `tests/` Package

| File | Tests | What It Covers |
|------|-------|----------------|
| `test_query_optimizer.py` | 19 | Row count generation, combined aggregate, Fivetran filter, duplicate check, text-only table |
| `test_schema_profiler.py` | 35 | All 9 column groups, business key detection, table profile properties |
| `test_suite_generator.py` | 21 | Suite structure, combined SQL output, orders table conditional checks |
| `test_validation_rule_engine.py` | 30 | Baseline always present, conditional checks, full orders table |

**Total: 107 tests. All passing (`lastfailed = {}`).**

---

## `docs/codemie/analytics/` — Session Logs

6 JSON files from EPAM CodeMie — one per development session, used for analytics. See `10_KNOWN_ISSUES_AND_HISTORY.md` for session-by-session summary.
