from typing import Any, Optional, Dict
import pyodbc
from application.database.mssql_connection import get_sql_db_connection
from secrets import token_urlsafe
from datetime import datetime, timedelta


def store_refresh_token(user_id: int) -> str:
    """
    TODO: choose expiration time for generated refresh token. Default: 30 days
    """
    # Generate token
    app_refresh_token = token_urlsafe(64)
    expires_at = datetime.now() + timedelta(days=30)

    try:
        query = """
        INSERT INTO RefreshTokens (user_id, refresh_token, expires_at)
        VALUES (?, ?, ?)
        """

        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
        
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


def get_refresh_token_details(refresh_token: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user ID based on refresh token.
    """

    try:
        query = """
        SELECT rt.user_id, rt.expires_at
        FROM RefreshTokens rt
        WHERE rt.refresh_token = ?
        """
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (refresh_token,))

            record = cursor.fetchone()
            if not record:
                return None

            return {"user_id": record[0], "expires_at": record[1]}

    except pyodbc.Error as e:
        # TODO: integrate into future logging functionality
        print(f"Error: {str(e)}")
        return None


def get_refresh_token_from_user_id(user_id: int) -> Optional[str]:
    """
    Retrieves refresh token associated with user from DB.

    :param user_id: ID corresponding to a user in the database
    :type user_id: int
    :returns: refresh token
    :rtype: str
    :raises pyodbc.Error: If error occurs when calling database
    """

    try:
        query = """
        SELECT rt.refresh_token
        FROM RefreshTokens rt
        WHERE rt.user_id = ?
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

    try:
        query = """
        DELETE FROM RefreshTokens
        WHERE refresh_token = ?
        """
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (refresh_token,))
            conn.commit()
            return {"message": f"Record deleted from RefreshTokens"}
    except pyodbc.Error as e:
        return {"error": str(e)}