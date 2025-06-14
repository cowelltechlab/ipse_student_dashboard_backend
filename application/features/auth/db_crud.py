from typing import Optional, Dict
from application.database.mssql_crud_helpers import (
    create_record, 
    delete_record, 
    fetch_by_id, 
)
import pyodbc
from application.database.mssql_connection import get_sql_db_connection

def get_user_by_email(user_email: str) -> Optional[Dict]:
    """
    DB helper function to fetch a single student record using their email. 
    Does not retrieve sensitive information like password or tokens.

    TODO: choose which info is required to be passed back.
    
    :param user_email: email address of the user
    :type user_email: str
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT u.id, u.email, u.gt_email,
               u.first_name, u.last_name
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
    TODO: determine if needed. Likely not needed for auth workflow specifically
          Alternatively, implement only for Google / SSO users. Determine if 
          implementing here or under module such as students.
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
    """
    return ""


def get_user_id_from_refresh_token(refresh_token: str) -> Optional[int]:
    """
    Retrieve user ID based on refresh token.

    TODO: add refresh token to Users table.
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT u.id
        FROM Users u
        WHERE u.refresh_token = ?
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


def delete_refresh_token(refresh_token: str):
    """
    Delete a user's refresh token from DB, effectively signing them out via
    Google SSO.
    
    TODO: add refresh token to user data before implementation.
    """
    pass


def get_user_email_by_id(user_id: int) -> Optional[str]:
    """
    Retrieves user record from DB using ID.
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



