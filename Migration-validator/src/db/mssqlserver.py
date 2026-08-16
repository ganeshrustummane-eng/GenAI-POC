"""
MSSQL Server database implementation
"""
import pyodbc
import pandas as pd
from .base import Database


class Mssqlserver(Database):
    """MSSQL Server database connection (supports SQL and Windows auth)"""
    
    def __init__(self, server, database, username=None, password=None, driver=None, port=1433, auth_type='sql'):
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.port = port
        self.driver = driver or "{ODBC Driver 18 for SQL Server}"
        self.auth_type = auth_type.lower()

    def connect(self):
        """Create MSSQL connection (Windows or SQL auth)"""
        base = (
            f"DRIVER={self.driver};"
            f"SERVER={self.server},{self.port};"
            f"DATABASE={self.database};"
            "TrustServerCertificate=yes;"
            "Encrypt=optional;"
            "Connection Timeout=30;"
        )
        if self.auth_type == 'windows':
            # Windows integrated authentication
            connection_string = base + "Trusted_Connection=yes;"
        else:
            # SQL Server authentication
            connection_string = base + f"UID={self.username};PWD={self.password};"
        
        conn = pyodbc.connect(connection_string, autocommit=True)
        return conn

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute query and return DataFrame"""
        conn = self.connect()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(query)
            data = [tuple(row) for row in cur.fetchall()]
            columns = [desc[0] for desc in cur.description]
            return pd.DataFrame(data, columns=columns)
        finally:
            if cur is not None:
                cur.close()
            conn.close()
