from typing import List
import pyodbc
from application.database.mssql_connection import get_sql_db_connection


def get_all_role_ids() -> List[int]:
    """
    Retrieves all unique ID values from Roles SQL table.

    :returns: all IDs
    :rtype: List[int]
    """
  
    try:
        query = "SELECT r.id from Roles r"
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)

            all_role_ids = [row[0] for row in cursor.fetchall()]
            return all_role_ids
    
    except pyodbc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {str(e)}")
        return []