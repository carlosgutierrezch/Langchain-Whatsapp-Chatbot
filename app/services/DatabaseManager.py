from typing import List, Any
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
import json
class DatabaseManager:
    def __init__(self, db_path: str = "all_data.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")

    def get_schema(self) -> str:
        """Retrieve the database schema by querying using SQLAlchemy inspector."""
        try:
            inspector = inspect(self.engine)
            schema = inspector.get_table_names()  
            return json.dumps(schema)
        except Exception as e:
            raise Exception(f"Error fetching schema: {str(e)}")
        
    def execute_query(self, query: str) -> List[Any]:
        """Execute an SQL query on the database and return results."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(query)
                return result
        except Exception as e:
            raise Exception(f"Error executing query: {str(e)}")

    def get_engine(self) -> Engine:
        """Return the SQLAlchemy engine instance."""
        return self.engine
    

# class DatabaseManager:
#     def __init__(self):
#         self.endpoint_url = os.getenv("DB_ENDPOINT_URL")

#     def get_schema(self, uuid: str) -> str:
#         """Retrieve the database schema."""
#         try:
#             response = requests.get(
#                 f"{self.endpoint_url}/get-schema/{uuid}"
#             )
#             response.raise_for_status()
#             return response.json()['schema']
#         except requests.RequestException as e:
#             raise Exception(f"Error fetching schema: {str(e)}")

#     def execute_query(self, uuid: str, query: str) -> List[Any]:
#         """Execute SQL query on the remote database and return results."""
#         try:
#             response = requests.post(
#                 f"{self.endpoint_url}/execute-query",
#                 json={"uuid": uuid, "query": query}
#             )
#             response.raise_for_status()
#             return response.json()['results']
#         except requests.RequestException as e:
#             raise Exception(f"Error executing query: {str(e)}")