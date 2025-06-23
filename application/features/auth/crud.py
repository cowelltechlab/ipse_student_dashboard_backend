from typing import Any, Optional, Dict, List
from application.database.mssql_crud_helpers import (
    create_record, 
)
import pyodbc
from application.database.mssql_connection import get_sql_db_connection
from secrets import token_urlsafe
from datetime import datetime, timedelta

def get_user_by_email(user_email: str, get_password = False) -> Optional[Dict]:
    """
    DB helper function to fetch a single user record via their email. 

    TODO: choose which columns are required to be passed back.
    
    :param user_email: email address of the user
    :type user_email: str
    :param get_password: True if including password in response, False if not
    :type get_password: bool
    :returns: user's record in database
    :rtype: Optional[Dict]
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = f"""
        SELECT u.id, u.email, u.gt_email, u.first_name, u.last_name, 
               u.created_at{", u.password_hash" if get_password else ""}
        FROM Users u
        WHERE u.email = ?
        """
        cursor.execute(query, (user_email,))

        record = cursor.fetchone()
        if not record:
            return None

        column_names = [column[0] for column in cursor.description]
        return dict(zip(column_names, record))

    except pyodbc.Error as e:
        return {"error": str(e)}
    finally:
        conn.close()


def create_user(
    first_name: str,
    last_name: str,
    school_email: str,
    password_hash: str,
    role_ids: List[int],
    google_email: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    TODO: Implement user registration
    """
    conn = None

    try:
        # Create new user
        email = google_email or school_email
        new_user: Dict = create_record("Users", {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "gt_email": school_email,
            "password_hash": password_hash,
            "created_at": datetime.now()
        })

        # Add user and newly associated roles to UserRoles table
        user_id = new_user["id"]
        insert_roles = [(user_id, role_id) for role_id in role_ids]

        conn = get_sql_db_connection()
        cursor = conn.cursor()

        insert_query = "INSERT INTO UserRoles (user_id, role_id) VALUES (?, ?)"
        cursor.executemany(insert_query, insert_roles)
        conn.commit()

        return {
            "id": user_id,
            "email": new_user["email"],
            "first_name": new_user["first_name"],
            "last_name": new_user["last_name"],
            "school_email": new_user["gt_email"],
            "role_ids": role_ids,
            
        }
    except pyodbc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {e}")
        return None
    finally:
        if conn:
            conn.close()




def update_user_password(user_id: int, new_hashed_password: str):
    """
    TODO: before implementation, determine if hashing password in backend or 
          frontend.
    TODO: add password column to User DB.
    """
    pass


def store_refresh_token(user_id: int) -> str:
    """
    TODO: choose expiration time for generated refresh token. Default: 30 days
    """
    # Generate token
    app_refresh_token = token_urlsafe(64)
    expires_at = datetime.now() + timedelta(days=30)

    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        INSERT INTO RefreshTokens (user_id, refresh_token, expires_at)
        VALUES (?, ?, ?)
        """
        
        # Execute the query with the corresponding values
        cursor.execute(
            query,
            (user_id, app_refresh_token, expires_at)
        )
        
        conn.commit()

        return app_refresh_token
    except pyodbc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {e}")
        return ""
    finally:
        conn.close()


def get_refresh_token_details(refresh_token: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user ID based on refresh token.
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT rt.user_id, rt.expires_at
        FROM RefreshTokens rt
        WHERE rt.refresh_token = ?
        """
        cursor.execute(query, (refresh_token,))

        record = cursor.fetchone()
        if not record:
            return None

        return {"user_id": record[0], "expires_at": record[1]}

    except pyodbc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {str(e)}")
        return None
    finally:
        conn.close()


def get_refresh_token_from_user_id(user_id: int) -> Optional[str]:
    """
    Retrieves refresh token associated with user from DB.

    :param user_id: ID corresponding to a user in the database
    :type user_id: int
    :returns: refresh token
    :rtype: str
    :raises pyodbc.Error: If error occurs when calling database
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT rt.refresh_token
        FROM RefreshTokens rt
        WHERE rt.user_id = ?
        """
        cursor.execute(query, (user_id,))

        record = cursor.fetchone()
        if not record:
            return None

        return record[0]

    except pyodbc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {str(e)}")
        return None
    finally:
        conn.close()


def delete_refresh_token(refresh_token: str) -> Dict:
    """
    Delete a user's refresh token from DB, effectively signing them out via
    Google SSO.

    :param refresh_token: string token to be deleted from RefreshToken database
    :type refresh_token: str
    :returns: delete message
    :rtype: Dict
    :raises pyodbc.Error: When delete action in database fails. 
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        DELETE FROM RefreshTokens
        WHERE refresh_token = ?
        """
        cursor.execute(query, (refresh_token,))
        conn.commit()
        return {"message": f"Record deleted from RefreshTokens"}
    except pyodbc.Error as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()


def get_user_email_by_id(user_id: int) -> Optional[str]:
    """
    Retrieves user's email address from their DB record via user ID.
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT u.email
        FROM Users u
        WHERE u.id = ?
        """
        cursor.execute(query, (user_id,))

        record = cursor.fetchone()
        if not record:
            return None

        return record[0]

    except pyodbc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {str(e)}")
        return None
    finally:
        conn.close()


def get_user_role_names(user_id: int) -> List[str]:
    """
    Retrieves list of roles associated with a user from DB using user ID.

    :param user_id: ID of user in the Users database table
    :type user_id: int
    :returns: list of roles associated with the user
    :rtype: List[str]
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()
    roles = []

    try:
        query = """
        SELECT r.role_name
        FROM Roles r
        JOIN UserRoles ur ON r.id = ur.role_id
        WHERE ur.user_id = ?
        """
        cursor.execute(query, (user_id,))

        records = cursor.fetchall()
        roles = [row[0] for row in records]


        return roles

    except pyodbc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {str(e)}")
        return []
    finally:
        conn.close()


def get_all_role_ids() -> List[int]:
    """
    Retrieves all unique ID values from Roles SQL table.

    :returns: all IDs
    :rtype: List[int]
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = "SELECT r.id from Roles r"
        cursor.execute(query)

        all_role_ids = [row[0] for row in cursor.fetchall()]
        return all_role_ids

    except pyodbc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {str(e)}")
        return []
    finally:
        conn.close()