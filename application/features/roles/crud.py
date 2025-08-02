
import pydoc
from typing import List, Optional

from application.database.mssql_connection import get_sql_db_connection


def get_multiple_role_names_from_ids(role_ids: List[int]) -> Optional[List[str]]:
    """
    Converts role IDs into role names based on corresponding values in Roles 
    SQL table.

    :param role_ids: List of role IDs 
    :type role_ids: List[int]
    :returns: list of role names matching role IDs
    :rtype: List[str]
    """

    try:
        placeholders = ','.join(['?' for _ in role_ids])
        get_query = f"""
        SELECT r.role_name 
        FROM Roles r 
        WHERE r.id IN ({placeholders})
        """
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(get_query, tuple(role_ids))

            role_name_rows = cursor.fetchall()
            return [row[0] for row in role_name_rows]
    except pydoc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {e}")
        return None
    except Exception as e:
        print(f"""An unexpected error occured in 
              get_multiple_role_names_from_ids: {e}""")
        return None