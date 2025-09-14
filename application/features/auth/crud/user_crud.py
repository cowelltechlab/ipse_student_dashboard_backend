from typing import Any, Optional, Dict, List
from application.database.mssql_crud_helpers import create_record
import pyodbc
from application.database.mssql_connection import get_sql_db_connection
from datetime import datetime


def get_user_by_email(user_email: str, get_password=False) -> Optional[Dict]:
    """
    DB helper function to fetch a single user record via their email or GT email. 

    TODO: choose which columns are required to be passed back.
    
    :param user_email: email address of the user (regular email or GT email)
    :type user_email: str
    :param get_password: True if including password in response, False if not
    :type get_password: bool
    :returns: user's record in database
    :rtype: Optional[Dict]
    """

    try:
        query = f"""
        SELECT u.id, u.email, u.gt_email, u.first_name, u.last_name, 
               u.created_at{", u.password_hash" if get_password else ""}
        FROM Users u
        WHERE u.email = ? OR u.gt_email = ?
        """

        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_email, user_email))

            record = cursor.fetchone()
            if not record:
                return None

            column_names = [column[0] for column in cursor.description]
            return dict(zip(column_names, record))

    except pyodbc.Error as e:
        return {"error": str(e)}


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

        insert_query = "INSERT INTO UserRoles (user_id, role_id) VALUES (?, ?)"
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
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


def update_user_password(user_id: int, new_hashed_password: str) -> bool:
    """
    Updates a user's password in the Users table.
    
    :param user_id: ID of the user to update
    :param new_hashed_password: The new hashed password
    :returns: True if successful, False otherwise
    """
    try:
        query = """
        UPDATE Users 
        SET password_hash = ?
        WHERE id = ?
        """
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (new_hashed_password, user_id))
            conn.commit()
            return cursor.rowcount > 0
    except pyodbc.Error as e:
        print(f"Error updating user password: {e}")
        return False


def get_user_email_by_id(user_id: int) -> Optional[str]:
    """
    Retrieves user's email address from their DB record via user ID.
    """

    try:
        query = """
        SELECT u.email
        FROM Users u
        WHERE u.id = ?
        """

        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))

            record = cursor.fetchone()
            if not record:
                return None

            return record[0]

    except pyodbc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {str(e)}")
        return None


def get_user_by_student_id(student_id: int) -> Optional[Dict]:
    """
    Retrieves user information by student ID.
    Joins Students table with Users table to get user_id from student_id.

    :param student_id: ID of the student
    :returns: User record if found, None otherwise
    """
    try:
        query = """
        SELECT u.id, u.email, u.gt_email, u.first_name, u.last_name
        FROM Users u
        JOIN Students s ON u.id = s.user_id
        WHERE s.id = ?
        """

        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (student_id,))

            record = cursor.fetchone()
            if not record:
                return None

            column_names = [column[0] for column in cursor.description]
            return dict(zip(column_names, record))

    except pyodbc.Error as e:
        print(f"Error getting user by student ID: {str(e)}")
        return None