"""
Snowflake database implementation
"""
import snowflake.connector
import pandas as pd
from .base import Database


class Snowflake(Database):
    """Snowflake database connection"""
    
    def __init__(self, account, user, password, database, schema, warehouse, role=None):
        self.account = account
        self.user = user
        self.password = password
        self.database = database
        self.schema = schema
        self.warehouse = warehouse
        self.role = role

    def connect(self):
        """Create Snowflake connection"""
        conn_params = {
            'account': self.account,
            'user': self.user,
            'password': self.password,
            'database': self.database,
            'schema': self.schema,
            'warehouse': self.warehouse,
        }
        if self.role:
            conn_params['role'] = self.role
        
        conn = snowflake.connector.connect(**conn_params)
        return conn

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute query and return DataFrame"""
        conn = self.connect()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(query)
            # Fetch all results
            data = cur.fetchall()
            # Get column names
            columns = [desc[0].lower() for desc in cur.description]
            return pd.DataFrame(data, columns=columns)
        finally:
            if cur is not None:
                cur.close()
            conn.close()
