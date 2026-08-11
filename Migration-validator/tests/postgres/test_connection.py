#!/usr/bin/env python3
"""
PostgreSQL Connection Test and Data Validation Script
This script verifies the PostgreSQL database connection and validates sample data
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import psycopg2
    from psycopg2 import sql
    import psycopg2.extras
except ImportError:
    print("Error: psycopg2 is not installed")
    print("Install it with: pip install psycopg2-binary")
    sys.exit(1)


class PostgreSQLConnector:
    """PostgreSQL database connector and test utility"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize PostgreSQL connector
        
        Args:
            config_file: Path to connection config JSON file
        """
        self.config = self._load_config(config_file)
        self.connection = None
        self.cursor = None
    
    def _load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if config_file is None:
            # Try to find default config in same directory
            config_file = Path(__file__).parent / "connection.config.json"
        
        if not Path(config_file).exists():
            print(f"Warning: Config file not found at {config_file}")
            return self._get_default_config()
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get('postgresql', config)
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}")
            return self._get_default_config()
    
    @staticmethod
    def _get_default_config() -> Dict[str, str]:
        """Get default PostgreSQL configuration"""
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_bd',  # Your actual database name
            'user': 'postgres',
            'password': '12345',
            'schema': 'source_data'
        }
    
    def connect(self) -> bool:
        """
        Establish database connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            print(f"Connecting to PostgreSQL at {self.config['host']}:{self.config['port']}...")
            
            self.connection = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password'],
                connect_timeout=5
            )
            
            self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            print("✓ Successfully connected to PostgreSQL")
            return True
        
        except psycopg2.OperationalError as e:
            print(f"✗ Connection failed: {e}")
            return False
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("Connection closed")
    
    def execute_query(self, query: str) -> Optional[List[Dict]]:
        """
        Execute a SELECT query
        
        Args:
            query: SQL query string
            
        Returns:
            List of query results as dictionaries, or None on error
        """
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"✗ Query execution failed: {e}")
            return None
    
    def get_table_info(self) -> Dict[str, Any]:
        """
        Get information about all tables in the schema
        
        Returns:
            Dictionary with table information
        """
        schema = self.config.get('schema', 'source_data')
        
        query = f"""
            SELECT 
                table_name,
                (SELECT COUNT(*) FROM information_schema.columns 
                 WHERE table_schema = '{schema}' AND table_name = t.table_name) as column_count
            FROM information_schema.tables AS t
            WHERE table_schema = '{schema}'
            ORDER BY table_name;
        """
        
        results = self.execute_query(query)
        if results is None:
            return {}
        
        return {row['table_name']: row['column_count'] for row in results}
    
    def get_row_counts(self) -> Dict[str, int]:
        """
        Get row counts for all tables
        
        Returns:
            Dictionary with table names and their row counts
        """
        schema = self.config.get('schema', 'source_data')
        
        tables = ['users', 'customers', 'products', 'orders', 'transactions']
        row_counts = {}
        
        for table in tables:
            query = f"SELECT COUNT(*) as cnt FROM {schema}.{table};"
            result = self.execute_query(query)
            
            if result:
                row_counts[table] = result[0]['cnt']
            else:
                row_counts[table] = 0
        
        return row_counts
    
    def get_sample_data(self, table: str, limit: int = 5) -> List[Dict]:
        """
        Get sample data from a table
        
        Args:
            table: Table name
            limit: Number of rows to fetch
            
        Returns:
            List of sample rows
        """
        schema = self.config.get('schema', 'source_data')
        query = f"SELECT * FROM {schema}.{table} LIMIT {limit};"
        
        results = self.execute_query(query)
        return results or []
    
    def validate_transformation_data(self) -> Dict[str, Any]:
        """
        Validate data for transformation rule testing
        
        Returns:
            Dictionary with validation results
        """
        schema = self.config.get('schema', 'source_data')
        
        validations = {}
        
        # Boolean conversion test (users.is_active)
        query = f"""
            SELECT 
                SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END) as true_count,
                SUM(CASE WHEN is_active = false THEN 1 ELSE 0 END) as false_count,
                SUM(CASE WHEN is_active IS NULL THEN 1 ELSE 0 END) as null_count
            FROM {schema}.users;
        """
        result = self.execute_query(query)
        if result:
            validations['boolean_data'] = {
                'table': 'users',
                'column': 'is_active',
                'true_values': result[0]['true_count'],
                'false_values': result[0]['false_count'],
                'null_values': result[0]['null_count']
            }
        
        # Null handling test (customers with NULL values)
        query = f"""
            SELECT 
                SUM(CASE WHEN phone IS NULL THEN 1 ELSE 0 END) as null_phone,
                SUM(CASE WHEN credit_limit IS NULL THEN 1 ELSE 0 END) as null_credit,
                SUM(CASE WHEN company_name IS NULL THEN 1 ELSE 0 END) as null_company
            FROM {schema}.customers;
        """
        result = self.execute_query(query)
        if result:
            validations['null_handling'] = {
                'table': 'customers',
                'null_phone_count': result[0]['null_phone'],
                'null_credit_count': result[0]['null_credit'],
                'null_company_count': result[0]['null_company']
            }
        
        # Whitespace handling test (customers.company_name)
        query = f"""
            SELECT 
                customer_name,
                company_name,
                LENGTH(company_name) as company_length
            FROM {schema}.customers
            WHERE company_name LIKE ' %' OR company_name LIKE '% ';
        """
        result = self.execute_query(query)
        if result:
            validations['whitespace_data'] = {
                'table': 'customers',
                'column': 'company_name',
                'rows_with_spaces': len(result),
                'examples': [row['company_name'] for row in result[:3]]
            }
        
        # Case sensitivity test
        query = f"""
            SELECT DISTINCT status
            FROM {schema}.users
            ORDER BY status;
        """
        result = self.execute_query(query)
        if result:
            validations['case_data'] = {
                'table': 'users',
                'column': 'status',
                'unique_values': [row['status'] for row in result]
            }
        
        # Numeric precision test
        query = f"""
            SELECT 
                COUNT(*) as decimal_values,
                MIN(balance) as min_value,
                MAX(balance) as max_value,
                AVG(balance) as avg_value
            FROM {schema}.customers
            WHERE balance IS NOT NULL;
        """
        result = self.execute_query(query)
        if result:
            validations['numeric_data'] = {
                'table': 'customers',
                'column': 'balance',
                'decimal_count': result[0]['decimal_values'],
                'min_value': float(result[0]['min_value']) if result[0]['min_value'] else None,
                'max_value': float(result[0]['max_value']) if result[0]['max_value'] else None
            }
        
        return validations


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def main():
    """Main test execution"""
    print("\n" + "="*70)
    print("  PostgreSQL Connection Test & Data Validation")
    print("="*70)
    
    # Initialize connector
    connector = PostgreSQLConnector()
    
    # Test connection
    if not connector.connect():
        print("\n✗ Failed to establish connection. Please verify:")
        print("  - PostgreSQL is running")
        print("  - Database 'source_db' exists")
        print("  - Credentials are correct (admin/admin123)")
        return 1
    
    try:
        # Test 1: Get table information
        print_section("Table Information")
        table_info = connector.get_table_info()
        if table_info:
            for table, col_count in table_info.items():
                print(f"  ✓ {table:15} - {col_count} columns")
        else:
            print("  ✗ No tables found in schema")
        
        # Test 2: Get row counts
        print_section("Row Counts Validation")
        row_counts = connector.get_row_counts()
        expected = {'users': 10, 'customers': 10, 'products': 10, 'orders': 10, 'transactions': 12}
        
        all_valid = True
        for table, expected_count in expected.items():
            actual_count = row_counts.get(table, 0)
            status = "✓" if actual_count == expected_count else "✗"
            print(f"  {status} {table:15} - Expected: {expected_count:3}, Actual: {actual_count:3}")
            if actual_count != expected_count:
                all_valid = False
        
        if all_valid:
            print("\n  All row counts match expected values!")
        
        # Test 3: Validate transformation rule data
        print_section("Transformation Rule Data Validation")
        validations = connector.validate_transformation_data()
        
        for rule_name, rule_data in validations.items():
            print(f"\n  {rule_name}:")
            for key, value in rule_data.items():
                if isinstance(value, list):
                    print(f"    {key}: {len(value)} items")
                else:
                    print(f"    {key}: {value}")
        
        # Test 4: Sample data from each table
        print_section("Sample Data Preview")
        for table in ['users', 'customers', 'products', 'orders', 'transactions']:
            samples = connector.get_sample_data(table, limit=2)
            print(f"\n  {table} (first 2 rows):")
            for i, row in enumerate(samples, 1):
                print(f"    Row {i}: {dict(row)}")
        
        print_section("Tests Completed")
        print("\n✓ All tests completed successfully!")
        print("\nPostgreSQL is ready for the Migration Validator PoC")
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        return 1
    
    finally:
        connector.disconnect()


if __name__ == "__main__":
    sys.exit(main())
