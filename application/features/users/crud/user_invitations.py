import datetime
import hashlib
import os
from fastapi import HTTPException
from secrets import token_urlsafe
from typing import List, Dict, Optional
from application.database.mssql_connection import get_sql_db_connection
import pyodbc


def create_invited_user(email: str, school_email: str, role_ids: List[int], student_type: Optional[str] = None) -> Dict:
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            if student_type:
                # Insert with pending_student_group_type
                cursor.execute("""
                    INSERT INTO Users (email, gt_email, is_active, created_at, pending_student_group_type)
                    OUTPUT INSERTED.id
                    VALUES (?, ?, 0, GETUTCDATE(), ?)
                """, (email, school_email, student_type))
            else:
                # Insert without pending_student_group_type
                cursor.execute("""
                    INSERT INTO Users (email, gt_email, is_active, created_at)
                    OUTPUT INSERTED.id
                    VALUES (?, ?, 0, GETUTCDATE())
                """, (email, school_email))

            user_id = cursor.fetchone()[0]

            # Assign roles
            cursor.executemany(
                "INSERT INTO UserRoles (user_id, role_id) VALUES (?, ?)",
                [(user_id, rid) for rid in role_ids]
            )

            # Create invite token
            raw_token = token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            expires = datetime.datetime.utcnow() + datetime.timedelta(days=3)

            cursor.execute("""
                INSERT INTO AccountInvites (user_id, token_hash, expires_at)
                VALUES (?, ?, ?)
            """, (user_id, token_hash, expires))

            conn.commit()

            return {"user_id": user_id, "token": raw_token}

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def get_user_id_from_invite_token(token: str) -> int:
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            cursor.execute("""
                SELECT u.id
                FROM AccountInvites ai
                JOIN Users u ON ai.user_id = u.id
                WHERE ai.token_hash = ? 
                  AND ai.expires_at > GETUTCDATE()
                  AND ai.used_at IS NULL
            """, (token_hash,))

            record = cursor.fetchone()
            if not record:
                raise HTTPException(status_code=404, detail="Invite token is invalid or has expired.")

            return record[0]

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def complete_user_invite(token: str, first_name: str, last_name: str, password_hash: str, profile_picture_url: Optional[str]) -> dict:
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            # Verify invite
            cursor.execute("""
                SELECT ai.id, u.id AS user_id
                FROM AccountInvites ai
                JOIN Users u ON ai.user_id = u.id
                WHERE ai.token_hash = ? 
                  AND ai.expires_at > GETUTCDATE()
                  AND ai.used_at IS NULL
            """, (token_hash,))
            record = cursor.fetchone()

            if not record:
                raise HTTPException(status_code=404, detail="Invite token is invalid or has expired.")

            invite_id, user_id = record

            # Update user details
            cursor.execute("""
                UPDATE Users
                SET first_name = ?, last_name = ?, password_hash = ?, 
                    profile_picture_url = ?, is_active = 1
                WHERE id = ?
            """, (first_name, last_name, password_hash, profile_picture_url, user_id))

            # Mark invite as used -- invalidate all other user tokens for this user
            cursor.execute("UPDATE AccountInvites SET used_at = GETUTCDATE() WHERE user_id = ?", (user_id,))

            conn.commit()

            return {"message": "User invite completed successfully.", "user_id": user_id}

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def regenerate_invite_url(user_id: int) -> Optional[str]:
    """
    Gets existing valid invite token or regenerates if expired/missing.
    Returns the complete invite URL (not just the token).
    """
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            
            # Generate new token
            raw_token = token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            expires = datetime.datetime.utcnow() + datetime.timedelta(days=3)
            
            cursor.execute("""
                INSERT INTO AccountInvites (user_id, token_hash, expires_at)
                VALUES (?, ?, ?)
            """, (user_id, token_hash, expires))
            
            conn.commit()
            
            # Build the complete invite URL
            frontend_base_url = os.getenv('FRONTEND_BASE_URL')
            if not frontend_base_url:
                print("Warning: FRONTEND_BASE_URL not set")
                return None
            
            invite_url = f"{frontend_base_url}/complete-invite?token={raw_token}"
            return invite_url
            
    except Exception as e:
        print(f"Error managing invite URL: {e}")
        return None