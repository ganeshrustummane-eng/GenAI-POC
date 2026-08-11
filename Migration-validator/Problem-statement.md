# Proof of Concept (PoC): Data Completeness Validation for Source-to-Snowflake Migration



## Background



As part of the data migration initiative, data is being migrated from multiple source systems, primarily Microsoft SQL Server and PostgreSQL, into Snowflake.



The objective of this Proof of Concept (PoC) is to design a reusable SQL-based validation approach to verify data completeness after migration.



For the PoC, the validation will consider **only one source system at a time**, as confirmed by the project lead. Multi-source consolidation scenarios will be addressed in later phases.



---



# Objective



Develop a generic and reusable approach to validate that data has been completely migrated from a source database to the corresponding Snowflake table.



The solution should generate SQL queries that can be executed manually by testers.



---



# Scope (Current PoC)



The PoC will validate:



* Row count (Data Completeness)

* Basic metadata required for validation

* Static transformation rules

* Generic SQL generation based on source database type



Only one source database will be considered for each validation.



Supported source systems:



* Microsoft SQL Server

* PostgreSQL



Target system:



* Snowflake



---



# Assumptions



For this PoC:



* Every Snowflake table maps to a single source table.

* The tester will provide:



  * Source Database

  * Source Schema

  * Source Table

  * Target Database

  * Target Schema

  * Target Table

* SQL queries will be executed manually.

* Static transformation rules will be defined initially.

* Dynamic business rules are out of scope for this phase.



---



# Problem Statement



During migration, the source and target tables may not have identical structures.



Differences may include:



* Different data types

* Different representations of values

* Renamed columns

* Standardization of values

* Default values

* Null handling



Therefore, direct data comparison may produce false validation failures.



To overcome this, a predefined set of static transformation rules will be applied during validation.



These rules will normalize the source and target data before comparison.



---



# Static Transformation Rules (Initial Version)



Examples of rules to be considered:



## Boolean Conversion



SQL Server



BIT



0 → FALSE



1 → TRUE



Snowflake



BOOLEAN



FALSE



TRUE



Validation Rule:



Treat BIT(0) and BOOLEAN(FALSE) as equivalent.



Treat BIT(1) and BOOLEAN(TRUE) as equivalent.



---



## Null Standardization



Treat NULL values consistently between source and target.



---



## Whitespace Handling



Ignore leading and trailing spaces during comparison.



Example:



'John'



and



' John '



should be considered equal.



---



## Case Insensitive Comparison



Compare text values ignoring case.



Example:



john



JOHN



John



should all be treated as equivalent.



---



## Date Standardization



Different databases may store dates in different formats.



Comparison should be based on the actual date value rather than the displayed format.



---



## Numeric Precision



Ignore insignificant decimal differences where applicable.



Example:



100



100.0



100.00



should be treated as equivalent.



---



## Empty String Handling



If required by business rules,



''



and



NULL



may be treated as equivalent.



(This rule will be enabled only if approved.)



---



# Validation Flow



1. Receive source and target details.

2. Identify the source database type.

3. Generate source SQL.

4. Generate Snowflake SQL.

5. Apply static transformation rules where applicable.

6. Compare source and target results.

7. Report Pass/Fail.



---



# Future Enhancements



The PoC is intentionally limited to a single source system.



Future phases may include:



* Multi-source validation (SQL Server + PostgreSQL → Snowflake)

* Dynamic transformation rules

* Source-to-Target Mapping (STM) integration

* Automated SQL generation

* Metadata-driven validation

* Column-level reconciliation

* Aggregate validations

* Duplicate detection

* Null count validation

* Primary key validation

* Data profiling

* Automated validation reports



---



# Expected Outcome



The PoC should provide a reusable framework that enables testers to manually validate migrated data using SQL queries while accounting for predefined static transformation rules.



This framework should be extensible so that additional business rules, transformations, and multi-source validations can be incorporated in future project phases without significant redesign.



