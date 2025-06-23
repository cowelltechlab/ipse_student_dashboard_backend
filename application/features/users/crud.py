from typing import List, Dict, Optional
from application.database.mssql_connection import get_sql_db_connection
import pyodbc


def get_all_users_with_roles(role_id: Optional[int] = None) -> List[Dict]:
    """
    Fetches all users and their associated roles. Optionally filters by role_id.
    
    :param role_id: Optional role ID to filter users by
    :type role_id: Optional[int]
    :return: List of user records with roles and role_ids
    :rtype: List[Dict]
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        if role_id is not None:
            query = """
                SELECT u.id, u.first_name, u.last_name, u.email, u.gt_email
                FROM Users u
                JOIN UserRoles ur ON u.id = ur.user_id
                WHERE ur.role_id = ?
            """
            cursor.execute(query, (role_id,))
        else:
            query = """
                SELECT u.id, u.first_name, u.last_name, u.email, u.gt_email
                FROM Users u
            """
            cursor.execute(query)

        users = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        user_dicts = [dict(zip(column_names, row)) for row in users]

        for user in user_dicts:
            uid = user["id"]

            cursor.execute("""
                SELECT r.id, r.role_name
                FROM Roles r
                JOIN UserRoles ur ON r.id = ur.role_id
                WHERE ur.user_id = ?
            """, (uid,))
            role_data = cursor.fetchall()

            user["roles"] = [r[1] for r in role_data]
            user["role_ids"] = [r[0] for r in role_data]

        return user_dicts

    except pyodbc.Error as e:
        print(f"Error fetching users: {str(e)}")
        return []
    finally:
        conn.close()
