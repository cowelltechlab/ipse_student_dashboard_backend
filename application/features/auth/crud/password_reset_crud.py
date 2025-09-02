from typing import Optional
import pyodbc
from application.database.mssql_connection import get_sql_db_connection
from secrets import token_urlsafe
from datetime import datetime, timedelta
import hashlib


def create_password_reset_token(user_id: int) -> str:
    """
    Creates a password reset token for a user in the PasswordResetTokens table.
    Token expires in 1 hour.
    
    :param user_id: ID of the user requesting password reset
    :returns: The plain token (not hashed) to send via email
    """
    # Generate token
    plain_token = token_urlsafe(64)
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    expires_at = datetime.now() + timedelta(hours=1)
    
    try:
        query = """
        INSERT INTO PasswordResetTokens (user_id, token_hash, expires_at)
        VALUES (?, ?, ?)
        """
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id, token_hash, expires_at))
            conn.commit()
        
        return plain_token
    except pyodbc.Error as e:
        print(f"Error creating password reset token: {e}")
        return ""


def validate_password_reset_token(token: str) -> Optional[int]:
    """
    Validates a password reset token and returns the associated user ID.
    
    :param token: The plain token to validate
    :returns: User ID if token is valid and not expired, None otherwise
    """
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        current_date = datetime.now()

        query = """
        SELECT user_id
        FROM PasswordResetTokens
        WHERE token_hash = ? 
          AND expires_at > ?
          AND used_at IS NULL
        """
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (token_hash, current_date))
            
            record = cursor.fetchone()
            if not record:
                return None
            
            return record[0]
    except pyodbc.Error as e:
        print(f"Error validating password reset token: {e}")
        return None


def mark_password_reset_token_used(token: str) -> bool:
    """
    Marks a password reset token as used by setting the used_at timestamp.
    
    :param token: The plain token to mark as used
    :returns: True if successful, False otherwise
    """
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        query = """
        UPDATE PasswordResetTokens 
        SET used_at = GETUTCDATE()
        WHERE token_hash = ? AND used_at IS NULL
        """
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (token_hash,))
            conn.commit()
            return cursor.rowcount > 0
    except pyodbc.Error as e:
        print(f"Error marking password reset token as used: {e}")
        return False