"""
Test PostgreSQL Connector
Verifies connection and data retrieval from source database
"""
import sys
sys.path.insert(0, 'src')

from models import DatabaseType, DatabaseConfig
from database_connectors import ConnectorFactory

def test_postgres():
    """Test PostgreSQL connection and data retrieval"""
    
    # Configure PostgreSQL connection
    config = DatabaseConfig(
        database_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="test_bd",  # Your actual PostgreSQL database
        username="postgres",
        password="12345",
        schema="source_data",
        timeout=30
    )
    
    # Test connection
    factory = ConnectorFactory()
    connector = factory.create_connector(config)
    
    print("\n" + "="*80)
    print("🧪 TESTING POSTGRESQL CONNECTOR")
    print("="*80)
    
    print(f"\nConnection Details:")
    print(f"  Host: {config.host}")
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
            print("✗ PostgreSQL connection failed!")
            return False
        
        # Then test the connection
        if connector.test_connection():
            print("✅ PostgreSQL connection successful!")
        else:
            print("✗ PostgreSQL connection test failed!")
            return False
    except Exception as e:
        print(f"✗ Connection error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Read from users table
    print("\n" + "-"*80)
    print("Test 2: Read USERS table")
    print("-"*80)
    try:
        query = "SELECT COUNT(*) as count FROM source_data.users"
        result = connector.execute_query(query)
        if result.error:
            print(f"✗ Error: {result.error}")
        else:
            print(f"✅ Row count: {result.row_count}")
            print(f"   Data: {result.rows}")
            print(f"   Total users: {result.rows[0]['count'] if result.rows else 0}")
    except Exception as e:
        print(f"✗ Query error: {e}")
        return False
    
    # Test 3: Read from customers table
    print("\n" + "-"*80)
    print("Test 3: Read CUSTOMERS table")
    print("-"*80)
    try:
        query = "SELECT COUNT(*) as count FROM source_data.customers"
        result = connector.execute_query(query)
        if result.error:
            print(f"✗ Error: {result.error}")
        else:
            print(f"✅ Row count: {result.row_count}")
            print(f"   Data: {result.rows}")
            print(f"   Total customers: {result.rows[0]['count'] if result.rows else 0}")
    except Exception as e:
        print(f"✗ Query error: {e}")
        return False
    
    # Test 4: Sample data from users
    print("\n" + "-"*80)
    print("Test 4: Sample Data from USERS")
    print("-"*80)
    try:
        query = "SELECT * FROM source_data.users LIMIT 3"
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
    
    print("\n" + "="*80)
    print("✅ POSTGRESQL CONNECTOR TEST COMPLETE - ALL TESTS PASSED!")
    print("="*80 + "\n")
    
    connector.disconnect()
    return True


if __name__ == "__main__":
    success = test_postgres()
    sys.exit(0 if success else 1)
