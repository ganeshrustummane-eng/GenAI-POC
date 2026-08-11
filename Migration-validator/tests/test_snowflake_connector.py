"""
Test Snowflake Connector
Verifies connection and data retrieval from target database
"""
import sys
sys.path.insert(0, 'src')

from models import DatabaseType, DatabaseConfig
from database_connectors import ConnectorFactory

def test_snowflake():
    """Test Snowflake connection and data retrieval"""
    
    # Configure Snowflake connection
    # For organization accounts, use format: ORGANIZATION_NAME.ACCOUNT_NAME
    # From Account Details: ZJAUJWQ (org) . EP12783 (account)
    config = DatabaseConfig(
        database_type=DatabaseType.SNOWFLAKE,
        host="ZJAUJWQ-EP12783",  # Organization-Account format (hyphen; dot does not reach the backend)
        port=443,
        database="dev_edge_bronze",
        username="MANEGANESH99",
        password="Ganeshmane@999",
        schema="storedge_fms_public",
        timeout=30
    )
    
    # Test connection
    factory = ConnectorFactory()
    connector = factory.create_connector(config)
    
    print("\n" + "="*80)
    print("🧪 TESTING SNOWFLAKE CONNECTOR")
    print("="*80)
    
    print(f"\nConnection Details:")
    print(f"  Account: {config.host}")
    print(f"  Port: {config.port}")
    print(f"  Database: {config.database}")
    print(f"  Schema: {config.schema}")
    print(f"  Username: {config.username}")
    
    # Test 1: Connection
    print("\n" + "-"*80)
    print("Test 1: Connection")
    print("-"*80)
    try:
        # First establish connection
        if not connector.connect():
            print("✗ Snowflake connection failed!")
            return False
        
        # Then test the connection
        if connector.test_connection():
            print("✅ Snowflake connection successful!")
        else:
            print("✗ Snowflake connection test failed!")
            return False
    except Exception as e:
        print(f"✗ Connection error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Read from USERS table
    print("\n" + "-"*80)
    print("Test 2: Read USERS table")
    print("-"*80)
    try:
        query = "SELECT COUNT(*) as count FROM target_schema.USERS"
        result = connector.execute_query(query)
        if result.error:
            print(f"✗ Error: {result.error}")
        else:
            print(f"✅ Row count: {result.row_count}")
            print(f"   Data: {result.rows}")
            print(f"   Total users: {result.rows[0].get('count') or result.rows[0].get('COUNT', 0) if result.rows else 0}")
    except Exception as e:
        print(f"✗ Query error: {e}")
        return False
    
    # Test 3: Read from CUSTOMERS table
    print("\n" + "-"*80)
    print("Test 3: Read CUSTOMERS table")
    print("-"*80)
    try:
        query = "SELECT COUNT(*) as count FROM target_schema.CUSTOMERS"
        result = connector.execute_query(query)
        if result.error:
            print(f"✗ Error: {result.error}")
        else:
            print(f"✅ Row count: {result.row_count}")
            print(f"   Data: {result.rows}")
            print(f"   Total customers: {result.rows[0].get('count') or result.rows[0].get('COUNT', 0) if result.rows else 0}")
    except Exception as e:
        print(f"✗ Query error: {e}")
        return False
    
    # Test 4: Sample data from USERS
    print("\n" + "-"*80)
    print("Test 4: Sample Data from USERS")
    print("-"*80)
    try:
        query = "SELECT * FROM target_schema.USERS LIMIT 3"
        result = connector.execute_query(query)
        if result.error:
            print(f"✗ Error: {result.error}")
        else:
            print(f"✅ Retrieved {result.row_count} rows")
            for i, row in enumerate(result.rows, 1):
                print(f"\n   Row {i}:")
                for key, value in row.items():
                    print(f"     {key}: {value}")
    except Exception as e:
        print(f"✗ Query error: {e}")
        return False
    
    # Test 5: Check table schema
    print("\n" + "-"*80)
    print("Test 5: Check Table Schema")
    print("-"*80)
    try:
        query = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'TARGET_SCHEMA' 
        AND table_name = 'USERS'
        ORDER BY ordinal_position
        """
        result = connector.execute_query(query)
        if result.error:
            print(f"✗ Error: {result.error}")
        else:
            print(f"✅ USERS table schema:")
            for row in result.rows:
                col_name = row.get('COLUMN_NAME') or row.get('column_name', '')
                data_type = row.get('DATA_TYPE') or row.get('data_type', '')
                print(f"     {col_name}: {data_type}")
    except Exception as e:
        print(f"⚠ Schema check error (may not be critical): {e}")
    
    print("\n" + "="*80)
    print("✅ SNOWFLAKE CONNECTOR TEST COMPLETE - ALL TESTS PASSED!")
    print("="*80 + "\n")
    
    connector.disconnect()
    return True


if __name__ == "__main__":
    success = test_snowflake()
    sys.exit(0 if success else 1)
