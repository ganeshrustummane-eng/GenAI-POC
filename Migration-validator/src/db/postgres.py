"""
PostgreSQL database implementation
"""
import psycopg2
import pandas as pd
from .base import Database


class Postgres(Database):
    """PostgreSQL database connection"""
    
    def __init__(self, dbname, user, password, host, port=5432):
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port

    def connect(self):
        """Create PostgreSQL connection"""
        conn = psycopg2.connect(
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port
        )
        return conn

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute query and return DataFrame"""
        conn = self.connect()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(query)
            data = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return pd.DataFrame(data, columns=columns)
        finally:
            if cur is not None:
                cur.close()
            conn.close()
