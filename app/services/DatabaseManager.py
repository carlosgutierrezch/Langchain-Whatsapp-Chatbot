from typing import List, Any
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy import text
from langchain_community.utilities import SQLDatabase


class DatabaseManager:
    
    def __init__(self,db_path: str = "/Users/main/Desktop/chatbot/app/services/all_data.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")

    def get_schema(self) -> str:
        """Retrieve the database schema and format it as a string."""
        try:
            db= SQLDatabase(engine=self.engine)
            tables = db.get_usable_table_names()
            return tables
        except Exception as e:
            raise Exception(f"Error fetching schema: {str(e)}")
        
    def execute_query(self, query: str) -> List[Any]:
        """Execute an SQL query on the database and return results."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query))
                return [row for row in result]
        except Exception as e:
            raise Exception(f"Error executing query: {str(e)}")

db_manager= DatabaseManager()
print(db_manager.get_schema())