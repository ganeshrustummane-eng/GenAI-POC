"""
Database Connectors
Handles connections to different database types
"""

import time
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from models import DatabaseConfig, DatabaseType, QueryResult


class BaseConnector(ABC):
    """Base database connector"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish database connection"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close database connection"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str) -> QueryResult:
        """Execute a query"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if connection is working"""
        pass


class MSSQLConnector(BaseConnector):
    """Microsoft SQL Server connector"""
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        try:
            import pyodbc
            self.pyodbc = pyodbc
        except ImportError:
            raise ImportError("pyodbc is required for MSSQL. Install with: pip install pyodbc")
    
    def connect(self) -> bool:
        """Connect to MSSQL Server"""
        try:
            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.config.host},{self.config.port};"
                f"DATABASE={self.config.database};"
                f"UID={self.config.username};"
                f"PWD={self.config.password};"
            )
            self.connection = self.pyodbc.connect(connection_string, timeout=self.config.timeout)
            print(f"✓ Connected to MSSQL: {self.config}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to MSSQL: {e}")
            return False
    
    def disconnect(self):
        """Close MSSQL connection"""
        if self.connection:
            self.connection.close()
            print("✓ MSSQL connection closed")
    
    def execute_query(self, query: str) -> QueryResult:
        """Execute MSSQL query"""
        result = QueryResult(query=query, row_count=0)
        
        if not self.connection:
            result.error = "Not connected to database"
            return result
        
        try:
            start_time = time.time()
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            rows = cursor.fetchall()
            result.rows = [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
            result.row_count = len(result.rows)
            result.execution_time_ms = (time.time() - start_time) * 1000
            
            cursor.close()
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_connection(self) -> bool:
        """Test MSSQL connection"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except:
            return False


class PostgreSQLConnector(BaseConnector):
    """PostgreSQL connector"""
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        try:
            import psycopg2
            import psycopg2.extras
            self.psycopg2 = psycopg2
            self.extras = psycopg2.extras
        except ImportError:
            raise ImportError("psycopg2 is required for PostgreSQL. Install with: pip install psycopg2-binary")
    
    def connect(self) -> bool:
        """Connect to PostgreSQL"""
        try:
            self.connection = self.psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                connect_timeout=self.config.timeout
            )
            print(f"✓ Connected to PostgreSQL: {self.config}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to PostgreSQL: {e}")
            return False
    
    def disconnect(self):
        """Close PostgreSQL connection"""
        if self.connection:
            self.connection.close()
            print("✓ PostgreSQL connection closed")
    
    def execute_query(self, query: str) -> QueryResult:
        """Execute PostgreSQL query"""
        result = QueryResult(query=query, row_count=0)
        
        if not self.connection:
            result.error = "Not connected to database"
            return result
        
        try:
            start_time = time.time()
            cursor = self.connection.cursor(cursor_factory=self.extras.RealDictCursor)
            cursor.execute(query)
            
            rows = cursor.fetchall()
            result.rows = [dict(row) for row in rows]
            result.row_count = len(result.rows)
            result.execution_time_ms = (time.time() - start_time) * 1000
            
            cursor.close()
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_connection(self) -> bool:
        """Test PostgreSQL connection"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except:
            return False


class SnowflakeConnector(BaseConnector):
    """Snowflake connector"""
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        try:
            import snowflake.connector
            self.snowflake = snowflake.connector
        except ImportError:
            raise ImportError("snowflake-connector-python is required. Install with: pip install snowflake-connector-python")
    
    def connect(self) -> bool:
        """Connect to Snowflake"""
        try:
            # For Snowflake Python SDK with organization accounts:
            # Use format: ORGANIZATION_NAME.ACCOUNT_NAME
            # Find in: Snowflake Web UI > Admin > Account Details
            # Examples:
            #   - Organization account: ZJAUJWQ.EP12783 (ORG.ACCOUNT) ✅
            #   - Legacy account: ZJAUJWQ-EP12783 (full identifier) - may need region
            #   - Account locator: EQ88947 (for legacy accounts only)
            
            self.connection = self.snowflake.connect(
                user=self.config.username,
                password=self.config.password,
                account=self.config.host,
                database=self.config.database,
                schema=self.config.schema,
                login_timeout=self.config.timeout
            )
            print(f"✓ Connected to Snowflake: {self.config}")
            return True
        except Exception as e:
            # If connection fails, provide detailed error info for troubleshooting
            print(f"✗ Failed to connect to Snowflake: {e}")
            print(f"\nDEBUG INFO:")
            print(f"  Account: {self.config.host}")
            print(f"  Database: {self.config.database}")
            print(f"  Schema: {self.config.schema}")
            print(f"  Username: {self.config.username}")
            print(f"  Timeout: {self.config.timeout}s")
            print(f"\nIf this persists, verify:")
            print(f"  1. For ORG accounts: Use ORGANIZATION_NAME.ACCOUNT_NAME (e.g., ZJAUJWQ.EP12783)")
            print(f"  2. Find these values in: Admin > Account Details")
            print(f"  3. Check credentials work in Snowflake Web UI")
            print(f"  4. Verify MFA or special authentication (may need authenticator parameter)")
            return False
    
    def disconnect(self):
        """Close Snowflake connection"""
        if self.connection:
            self.connection.close()
            print("✓ Snowflake connection closed")
    
    def execute_query(self, query: str) -> QueryResult:
        """Execute Snowflake query"""
        result = QueryResult(query=query, row_count=0)
        
        if not self.connection:
            result.error = "Not connected to database"
            return result
        
        try:
            start_time = time.time()
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            rows = cursor.fetchall()
            columns = [col[0].lower() for col in cursor.description]
            result.rows = [dict(zip(columns, row)) for row in rows]
            result.row_count = len(result.rows)
            result.execution_time_ms = (time.time() - start_time) * 1000
            
            cursor.close()
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_connection(self) -> bool:
        """Test Snowflake connection"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except:
            return False


class ConnectorFactory:
    """Factory to create database connectors"""

    @staticmethod
    def create_connector(config: DatabaseConfig) -> BaseConnector:
        """Create appropriate connector based on database type"""
        if config.database_type == DatabaseType.MSSQL:
            return MSSQLConnector(config)
        elif config.database_type == DatabaseType.POSTGRESQL:
            return PostgreSQLConnector(config)
        elif config.database_type == DatabaseType.SNOWFLAKE:
            return SnowflakeConnector(config)
        else:
            raise ValueError(f"Unsupported database type: {config.database_type}")

    @staticmethod
    def from_env() -> tuple:
        """
        Build both source (PostgreSQL) and target (Snowflake) connectors
        entirely from environment variables defined in .env.

        Returns:
            (PostgreSQLConnector, SnowflakeConnector)

        Required env vars:
            SOURCE_HOST, SOURCE_PORT, SOURCE_DATABASE,
            SOURCE_USERNAME, SOURCE_PASSWORD, SOURCE_SCHEMA
            SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA,
            SNOWFLAKE_USERNAME, SNOWFLAKE_PASSWORD
        """
        import os

        pg_config = DatabaseConfig(
            database_type=DatabaseType.POSTGRESQL,
            host=os.getenv("SOURCE_HOST", "localhost"),
            port=int(os.getenv("SOURCE_PORT", "5432")),
            database=os.getenv("SOURCE_DATABASE", "postgres"),
            username=os.getenv("SOURCE_USERNAME", "postgres"),
            password=os.getenv("SOURCE_PASSWORD", ""),
            schema=os.getenv("SOURCE_SCHEMA", "public"),
        )

        sf_config = DatabaseConfig(
            database_type=DatabaseType.SNOWFLAKE,
            host=os.getenv("SNOWFLAKE_ACCOUNT", ""),
            port=443,
            database=os.getenv("SNOWFLAKE_DATABASE", ""),
            username=os.getenv("SNOWFLAKE_USERNAME", ""),
            password=os.getenv("SNOWFLAKE_PASSWORD", ""),
            schema=os.getenv("SNOWFLAKE_SCHEMA", ""),
        )

        return (
            PostgreSQLConnector(pg_config),
            SnowflakeConnector(sf_config),
        )
