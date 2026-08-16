"""
AWS Athena database implementation
"""
import boto3
import pandas as pd
from .base import Database


class Athena(Database):
    """AWS Athena database connection"""
    
    def __init__(self, region, database, s3_output, access_key=None, secret_key=None):
        self.region = region
        self.database = database
        self.s3_output = s3_output
        self.access_key = access_key
        self.secret_key = secret_key

    def connect(self):
        """Create Athena session (no persistent connection)"""
        if self.access_key and self.secret_key:
            session = boto3.Session(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
        else:
            session = boto3.Session(region_name=self.region)
        
        return session.client('athena')

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute Athena query and return DataFrame"""
        client = self.connect()
        
        response = client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': self.database},
            ResultConfiguration={'OutputLocation': self.s3_output}
        )
        
        query_execution_id = response['QueryExecutionId']
        
        # Wait for query to complete
        while True:
            query_status = client.get_query_execution(
                QueryExecutionId=query_execution_id
            )
            status = query_status['QueryExecution']['Status']['State']
            if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break
        
        if status != 'SUCCEEDED':
            raise Exception(f"Query failed with status: {status}")
        
        # Get results
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Convert to DataFrame (skip header row)
        rows = results['ResultSet']['Rows']
        if len(rows) > 1:
            columns = [cell['VarCharValue'] for cell in rows[0]['Data']]
            data = []
            for row in rows[1:]:
                data.append([cell.get('VarCharValue', '') for cell in row['Data']])
            return pd.DataFrame(data, columns=columns)
        else:
            return pd.DataFrame()
