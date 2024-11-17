
import sqlite3
from typing import List, Any

class DatabaseManager:
    def __init__(self):
        self.db_path = "all_data.db"

    def get_schema(self) -> str:
        """Retrieve the database schema by querying sqlite_master."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Query the sqlite_master table to get schema details
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
                schema = cursor.fetchall()
                return schema  # Returns a list of table creation SQL statements
        except sqlite3.Error as e:
            raise Exception(f"Error fetching schema: {str(e)}")

    def execute_query(self, query: str) -> List[Any]:
        """Execute an SQL query on the database and return results."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                results = cursor.fetchall()
                return results
        except sqlite3.Error as e:
            raise Exception(f"Error executing query: {str(e)}")