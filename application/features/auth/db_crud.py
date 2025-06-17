from typing import Optional, Dict, List
from application.database.mssql_crud_helpers import (
    create_record, 
    delete_record, 
    fetch_by_id, 
)
import pyodbc
from application.database.mssql_connection import get_sql_db_connection
from secrets import token_urlsafe
from datetime import datetime, timedelta

def get_user_by_email(user_email: str) -> Optional[Dict]:
    """
    DB helper function to fetch a single user record via their email. 

    TODO: choose which columns are required to be passed back.
    
    :param user_email: email address of the user
    :type user_email: str
    :returns: user's record in database
    :rtype: Optional[Dict]
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT *
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


def create_user():
    """
    TODO: Implement user registration
    """
    pass


def update_user_password(user_id: int, new_hashed_password: str):
    """
    TODO: before implementation, determine if hashing password in backend or 
          frontend.
    TODO: add password column to User DB.
    """
    pass


def store_refresh_token(user_id: int) -> str:
    """
    TODO: add refresh token to user data before implementation. Must be hashed.
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


def get_user_id_from_refresh_token(refresh_token: str) -> Optional[int]:
    """
    Retrieve user ID based on refresh token.
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT rt.user_id
        FROM RefreshTokens rt
        WHERE rt.refresh_token = ?
        """
        cursor.execute(query, (refresh_token,))

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
        for role_name in records:
            roles.append(role_name)

        return roles

    except pyodbc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {str(e)}")
        return []
    finally:
        conn.close()
