"""
Database factory using .env credentials
Reads credentials from environment variables instead of YAML files
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class DatabaseFactory:
    """Factory for creating database connections from .env credentials"""
    
    @staticmethod
    def get_database(source_type: str, source_name: str = "SRC_1"):
        """
        Get database connection from .env credentials
        
        Args:
            source_type: 'postgresql', 'mssql', 'snowflake', or 'athena'
            source_name: Credential prefix in .env (e.g., 'SRC_1', 'SRC_2', 'SNOWFLAKE')
        
        Returns:
            Database instance (Postgres, Mssqlserver, Snowflake, or Athena)
        
        Example:
            >>> db = DatabaseFactory.get_database('postgresql', 'SRC_1')
            >>> results = db.execute_query("SELECT * FROM users LIMIT 10")
        """
        
        normalized_type = source_type.lower()
        if source_name == "SRC_1":
            source_name = {
                "postgresql": "SRC_1",
                "postgres": "SRC_1",
                "mssql": "SRC_2",
                "mssqlserver": "SRC_2",
                "sqlserver": "SRC_2",
                "athena": "SRC_3",
                "snowflake": "SNOWFLAKE",
            }.get(normalized_type, source_name)

        if normalized_type == 'postgresql' or normalized_type == 'postgres':
            return DatabaseFactory._get_postgresql(source_name)
        elif normalized_type == 'mssql' or normalized_type == 'mssqlserver' or normalized_type == 'sqlserver':
            return DatabaseFactory._get_mssql(source_name)
        elif normalized_type == 'snowflake':
            return DatabaseFactory._get_snowflake(source_name)
        elif normalized_type == 'athena':
            return DatabaseFactory._get_athena(source_name)
        else:
            raise ValueError(f"Unsupported database type: {source_type}")
    
    @staticmethod
    def _get_postgresql(source_name: str = "SRC_1") -> "Postgres":
        """Create PostgreSQL connection from .env"""
        from .postgres import Postgres

        host = os.getenv(f'{source_name}_HOST')
        port = os.getenv(f'{source_name}_PORT', '5432')
        database = os.getenv(f'{source_name}_DATABASE')
        username = os.getenv(f'{source_name}_USERNAME')
        password = os.getenv(f'{source_name}_PASSWORD')
        
        if not all([host, database, username, password]):
            raise ValueError(f"Missing PostgreSQL credentials in .env for {source_name}")
        
        return Postgres(
            dbname=database,
            host=host,
            user=username,
            password=password,
            port=int(port)
        )
    
    @staticmethod
    def _get_mssql(source_name: str = "SRC_2") -> "Mssqlserver":
        """Create MSSQL connection from .env"""
        from .mssqlserver import Mssqlserver

        server = os.getenv(f'{source_name}_HOST')
        port = os.getenv(f'{source_name}_PORT', '1433')
        database = os.getenv(f'{source_name}_DATABASE')
        username = os.getenv(f'{source_name}_USERNAME')
        password = os.getenv(f'{source_name}_PASSWORD')
        auth_type = os.getenv(f'{source_name}_AUTH', 'sql')  # 'sql' or 'windows'
        
        if not all([server, database]):
            raise ValueError(f"Missing MSSQL credentials in .env for {source_name}")
        
        # If Windows auth, don't require password; if SQL auth, require both user and password
        if auth_type.lower() == 'windows':
            username = username or None  # Use current Windows user if not specified
        elif not all([username, password]):
            raise ValueError(f"Missing MSSQL credentials in .env for {source_name}")
        
        return Mssqlserver(
            server=server,
            database=database,
            username=username,
            password=password or "",
            port=int(port),
            auth_type=auth_type
        )
    
    @staticmethod
    def _get_snowflake(source_name: str = "SNOWFLAKE") -> "Snowflake":
        """Create Snowflake connection from .env"""
        from .snowflake import Snowflake

        account = os.getenv(f'{source_name}_ACCOUNT')
        user = os.getenv(f'{source_name}_USERNAME')
        password = os.getenv(f'{source_name}_PASSWORD')
        database = os.getenv(f'{source_name}_DATABASE')
        schema = os.getenv(f'{source_name}_SCHEMA')
        warehouse = os.getenv(f'{source_name}_WAREHOUSE', 'compute_wh')
        role = os.getenv(f'{source_name}_ROLE')
        
        if not all([account, user, password, database, schema]):
            raise ValueError(f"Missing Snowflake credentials in .env for {source_name}")
        
        return Snowflake(
            account=account,
            user=user,
            password=password,
            database=database,
            schema=schema,
            warehouse=warehouse,
            role=role
        )
    
    @staticmethod
    def _get_athena(source_name: str = "SRC_3") -> "Athena":
        """Create Athena connection from .env"""
        from .athena import Athena

        region = os.getenv(f'{source_name}_REGION')
        database = os.getenv(f'{source_name}_DATABASE')
        s3_output = os.getenv(f'{source_name}_QUERY_RESULT_LOCATION')
        access_key = os.getenv(f'{source_name}_USERNAME')
        secret_key = os.getenv(f'{source_name}_PASSWORD')
        
        if not all([region, database, s3_output]):
            raise ValueError(f"Missing Athena credentials in .env for {source_name}")
        
        return Athena(
            region=region,
            database=database,
            s3_output=s3_output,
            access_key=access_key,
            secret_key=secret_key
        )


# Convenience function for backward compatibility
def get_database(db_type: str, source_name: str = "SRC_1"):
    """
    Get database connection from .env
    
    Usage:
        from src.db.factory import get_database
        db = get_database('postgresql', 'SRC_1')
        result = db.execute_query("SELECT * FROM table")
    """
    return DatabaseFactory.get_database(db_type, source_name)
