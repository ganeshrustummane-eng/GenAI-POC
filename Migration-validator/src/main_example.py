"""
Migration Validator - Main Example
Demonstrates complete validation workflow
"""

from models import (
    DatabaseType, DatabaseConfig, ColumnMapping, TableMapping,
    ValidationConfig, TransformationRuleType
)
from validator import DataValidator
from report_generator import ReportWriter
import os


def check_postgresql_databases():
    """Helper function to list available PostgreSQL databases"""
    print("\n" + "="*80)
    print("CHECKING AVAILABLE POSTGRESQL DATABASES")
    print("="*80)
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="postgres",
            user="postgres",
            password="12345"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;")
        databases = cursor.fetchall()
        print("\nAvailable databases:")
        for db in databases:
            print(f"  • {db[0]}")
        cursor.close()
        conn.close()
        return [db[0] for db in databases]
    except Exception as e:
        print(f"✗ Error listing databases: {e}")
        return []


def create_example_config() -> ValidationConfig:
    """
    Create example validation configuration
    You'll update this with your actual database details
    """
    
    # Source Database Configuration (PostgreSQL)
    # Using the correct database: test_bd (found via: psql -U postgres -l)
    source_config = DatabaseConfig(
        database_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="fms",  # Your PostgreSQL database with source_data schema
        username="postgres",
        password="12345",
        schema="public",
        timeout=30
    )
    
    # Target Database Configuration (Snowflake)
    # Updated with your actual Snowflake credentials from account details
    # For organization accounts, use format: ORGANIZATION_NAME.ACCOUNT_NAME
    # Found in Admin > Account Details:
    #   Organization name: ZJAUJWQ
    #   Account name: EP12783
    target_config = DatabaseConfig(
        database_type=DatabaseType.SNOWFLAKE,
        host="ZJAUJWQ-EP12783",  # Organization-Account format (hyphen; dot does not reach the backend)
        port=443,
        database="dev_edge_bronze",  # Your Snowflake database
        username="MANEGANESH99",  # Your Snowflake login name
        password="Ganeshmane@999",
        schema="storedge_fms_public",  # Your schema
        timeout=30
    )
    
    # Define column mappings for USERS table
    users_column_mappings = [
        ColumnMapping(
            source_column="user_id",
            target_column="USER_ID",
            source_data_type="SERIAL",
            target_data_type="NUMBER",
            primary_key=True
        ),
        ColumnMapping(
            source_column="username",
            target_column="USERNAME",
            source_data_type="VARCHAR(100)",
            target_data_type="VARCHAR",
            apply_rules=[TransformationRuleType.CASE_INSENSITIVE, TransformationRuleType.WHITESPACE_TRIM]
        ),
        ColumnMapping(
            source_column="email",
            target_column="EMAIL",
            source_data_type="VARCHAR(100)",
            target_data_type="VARCHAR",
            apply_rules=[TransformationRuleType.WHITESPACE_TRIM]
        ),
        ColumnMapping(
            source_column="is_active",
            target_column="IS_ACTIVE",
            source_data_type="BOOLEAN",
            target_data_type="BOOLEAN",
            apply_rules=[TransformationRuleType.BOOLEAN_CONVERSION]
        ),
        ColumnMapping(
            source_column="status",
            target_column="STATUS",
            source_data_type="VARCHAR(20)",
            target_data_type="VARCHAR",
            apply_rules=[TransformationRuleType.CASE_INSENSITIVE]
        ),
    ]
    
    # Define column mappings for CUSTOMERS table
    customers_column_mappings = [
        ColumnMapping(
            source_column="customer_id",
            target_column="CUSTOMER_ID",
            source_data_type="SERIAL",
            target_data_type="NUMBER",
            primary_key=True
        ),
        ColumnMapping(
            source_column="customer_name",
            target_column="CUSTOMER_NAME",
            source_data_type="VARCHAR(150)",
            target_data_type="VARCHAR",
            apply_rules=[TransformationRuleType.WHITESPACE_TRIM, TransformationRuleType.CASE_INSENSITIVE]
        ),
        ColumnMapping(
            source_column="balance",
            target_column="BALANCE",
            source_data_type="NUMERIC(12,2)",
            target_data_type="NUMERIC",
            apply_rules=[TransformationRuleType.NUMERIC_PRECISION]
        ),
        ColumnMapping(
            source_column="registration_date",
            target_column="REGISTRATION_DATE",
            source_data_type="DATE",
            target_data_type="DATE",
            apply_rules=[TransformationRuleType.DATE_STANDARDIZATION]
        ),
    ]
    
    # Define table mappings
    table_mappings = [
        TableMapping(
            source_table="users",
            target_table="USERS",
            column_mappings=users_column_mappings,
            description="Validates user data migration"
        ),
        TableMapping(
            source_table="customers",
            target_table="CUSTOMERS",
            column_mappings=customers_column_mappings,
            description="Validates customer data migration"
        ),
    ]
    
    # Create validation configuration
    config = ValidationConfig(
        source_db=source_config,
        target_db=target_config,
        table_mappings=table_mappings
    )
    
    return config


def run_validation_with_queries_only(config: ValidationConfig):
    """
    Generate validation queries without executing them
    Useful for manual execution and review
    """
    print("\n" + "="*80)
    print("GENERATING VALIDATION QUERIES (No Execution)")
    print("="*80)
    
    validator = DataValidator(config)
    queries = validator.get_validation_queries()
    
    print("\nGenerated Queries:\n")
    for query_name, query in queries.items():
        print(f"\n{'-'*80}")
        print(f"Query: {query_name}")
        print(f"{'-'*80}")
        print(query)
    
    return queries


def run_full_validation(config: ValidationConfig):
    """
    Execute complete validation with database connections
    """
    print("\n" + "="*80)
    print("RUNNING FULL VALIDATION (With Database Execution)")
    print("="*80)
    
    # Create validator
    validator = DataValidator(config)
    
    # Run validation
    report = validator.run_validation()
    
    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)
    
    # Display results
    print(f"\nValidation ID: {report.validation_id}")
    print(f"Overall Status: {report.overall_status}")
    print(f"Data Completeness: {report.overall_data_completeness:.2f}%")
    print(f"Success Rate: {report.success_rate:.2f}%")
    
    print(f"\nTable Results:")
    for table_result in report.table_results:
        print(f"  {table_result.table_name}: {table_result.overall_status} ({table_result.data_completeness_percentage:.1f}%)")
    
    return report


def export_reports(report):
    """Export validation report in multiple formats"""
    print("\n" + "="*80)
    print("EXPORTING REPORTS")
    print("="*80)
    
    import os
    from datetime import datetime
    
    # Create reports directory if not exists
    reports_dir = "validation_reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Write JSON report
    json_path = os.path.join(reports_dir, f"report_{timestamp}.json")
    ReportWriter.write_json_report(report, json_path)
    
    # Write HTML report
    html_path = os.path.join(reports_dir, f"report_{timestamp}.html")
    ReportWriter.write_html_report(report, html_path)
    
    # Write text report
    text_path = os.path.join(reports_dir, f"report_{timestamp}.txt")
    ReportWriter.write_text_report(report, text_path)
    
    print(f"\nReports saved in: {os.path.abspath(reports_dir)}")
    return {
        'json': json_path,
        'html': html_path,
        'text': text_path
    }


def main():
    """Main execution function"""
    
    print("\n" + "="*80)
    print("🚀 MIGRATION VALIDATOR - PROOF OF CONCEPT")
    print("="*80)
    
    # Check available databases first
    check_postgresql_databases()
    
    # Create example configuration
    config = create_example_config()
    
    print("\n📋 Configuration Loaded:")
    print(f"  Source: {config.source_db}")
    print(f"  Target: {config.target_db}")
    print(f"  Tables to validate: {len(config.table_mappings)}")
    
    # Option 1: Generate queries only (for manual review)
    print("\n\nOption 1: Generate Queries for Manual Review")
    print("-" * 80)
    queries = run_validation_with_queries_only(config)
    
    # Option 2: Run full validation (requires database connections)
    print("\n\nOption 2: Run Full Validation (Requires Database Connections)")
    print("-" * 80)
    print("\nTo run full validation with database connections:")
    print("1. Update Snowflake credentials in create_example_config()")
    print("2. Ensure PostgreSQL is running with sample data")
    print("3. Run: validator.run_validation()")
    print("4. Uncomment the code below:")
    
    # Run full validation with database connections
    try:
        report = run_full_validation(config)
        reports = export_reports(report)
        print(f"\n✅ Validation complete! Open: {reports['html']}")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n\n" + "="*80)
    print("CONFIGURATION & NEXT STEPS")
    print("="*80)
    print("""
✅ STEP 1: Update PostgreSQL Database Name
   • Above you'll see available databases
   • Edit create_example_config() and change:
     database="postgres"  →  database="YOUR_ACTUAL_DB"
   • Ensure schema "source_data" exists with tables: users, customers

✅ STEP 2: Create Target Tables in Snowflake (if not already done)
   • Log into your Snowflake account (ZJAUJWQ-EP12783)
   • Create database: snowflake_db
   • Create schema: target_schema
   • Create tables:
     - USERS (USER_ID, USERNAME, EMAIL, IS_ACTIVE, STATUS)
     - CUSTOMERS (CUSTOMER_ID, CUSTOMER_NAME, BALANCE, REGISTRATION_DATE)
   • Populate with test data that matches source structure

✅ STEP 3: Verify Generated Validation Queries
   • Review the SQL queries generated above
   • These queries will:
     - Compare row counts between source and target
     - Fetch data with transformation rules applied
     - Generate matching results for validation

✅ STEP 4: Execute in Production
   • Once target tables have migrated data:
     1. Copy source query results
     2. Copy target query results
     3. Compare the normalized results
     4. Run full validation to generate HTML/JSON/Text reports

Transformation Rules Applied:
  ✓ Boolean Conversion (BIT ↔ BOOLEAN)
  ✓ Whitespace Trimming
  ✓ Case-Insensitive Comparison
  ✓ Date Standardization (YYYY-MM-DD)
  ✓ Numeric Precision (2 decimal places)
  ✓ Null Standardization
  ✓ Empty String ↔ NULL Handling

For more information, see:
  - models.py: Data structures
  - transformation_rules.py: Rule definitions
  - sql_generators.py: Query generation
  - validator.py: Validation logic
  - report_generator.py: Report generation
""")


if __name__ == "__main__":
    main()
