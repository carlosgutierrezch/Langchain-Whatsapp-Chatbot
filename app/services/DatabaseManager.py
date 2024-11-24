from typing import List, Any
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy import text
<<<<<<< HEAD
from langchain_community.utilities import SQLDatabase


class DatabaseManager:
    
    def __init__(self,db_path: str = "/Users/main/Desktop/chatbot/app/services/all_data.db"):
=======

import json



class DatabaseManager:
    def __init__(self, db_path: str = "all_data.db"):
>>>>>>> 69a94044205ec7ebdabb3d49af6431e7c830a426
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")

    def get_schema(self) -> str:
        """Retrieve the database schema and format it as a string."""
        try:
<<<<<<< HEAD
            db= SQLDatabase(engine=self.engine)
            tables = db.get_usable_table_names()
            return tables
=======
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            schema = []
            for table in tables:
                columns = inspector.get_columns(table)
                column_names = [col['name'] for col in columns]
                schema.append(f"Table: {table}\nColumns: {', '.join(column_names)}")
            return "\n\n".join(schema)
>>>>>>> 69a94044205ec7ebdabb3d49af6431e7c830a426
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
<<<<<<< HEAD

db_manager= DatabaseManager()
print(db_manager.get_schema())
=======
        
        
    def get_engine(self) -> Engine:
        """Return the SQLAlchemy engine instance."""
        return self.engine

if __name__=="__main__":
    try:
        db_manager= DatabaseManager()
        print(db_manager.get_schema())
    except Exception as e:
        print(e)
>>>>>>> 69a94044205ec7ebdabb3d49af6431e7c830a426
