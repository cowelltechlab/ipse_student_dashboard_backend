
from fastapi import HTTPException, status
import pyodbc
from typing import Iterable, List, Optional

from application.database.mssql_connection import get_sql_db_connection

ROLE_ORDER = {"Admin": 0, "Advisor": 1, "Peer Tutor": 2, "Student": 3}



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
    except pyodbc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {e}")
        return None
    except Exception as e:
        print(f"""An unexpected error occured in 
              get_multiple_role_names_from_ids: {e}""")
        return None
    
def fetch_roles_by_names(role_names: Iterable[str]) -> List[dict]:
    """
    Fetch rows from Roles limited to the provided role_names.
    Columns returned: id, role_name, description
    """
    names = list(set(role_names))
    if not names:
        return []

    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(names))
            query = f"""
                SELECT id, role_name, description
                FROM Roles
                WHERE role_name IN ({placeholders})
            """
            cursor.execute(query, names)
            rows = cursor.fetchall()
            cols = [c[0] for c in cursor.description]
            records = [dict(zip(cols, row)) for row in rows]
            # sort using our hierarchy order
            records.sort(key=lambda r: ROLE_ORDER.get(str(r.get("role_name")), 999))
            return records
    except pyodbc.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {e}"
        )