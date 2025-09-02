import datetime
import hashlib
import os
from http.client import HTTPException
from secrets import token_urlsafe
from typing import List, Dict, Optional
from application.database.mssql_connection import get_sql_db_connection
import pyodbc

from application.database.nosql_connection import get_cosmos_db_connection

DATABASE_NAME = "ai-prompt-storage"
CONTAINER_NAME = "ai-student-profile"

client = get_cosmos_db_connection()
db = client.get_database_client(DATABASE_NAME)
container = db.get_container_client(CONTAINER_NAME)


def get_all_users_with_roles(role_id: Optional[int] = None) -> List[Dict]:
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Base query
            if role_id is not None:
                query = """
                    SELECT u.id, u.first_name, u.last_name, u.email, u.gt_email, 
                           u.profile_picture_url, u.is_active
                    FROM Users u
                    JOIN UserRoles ur ON u.id = ur.user_id
                    WHERE ur.role_id = ?
                """
                cursor.execute(query, (role_id,))
            else:
                query = """
                    SELECT u.id, u.first_name, u.last_name, u.email, u.gt_email, 
                           u.profile_picture_url, u.is_active
                    FROM Users u
                """
                cursor.execute(query)

            users = cursor.fetchall()
            if not users:
                return []

            column_names = [desc[0] for desc in cursor.description]
            user_dicts = [dict(zip(column_names, row)) for row in users]

            # Process each user
            for user in user_dicts:
                uid = user["id"]

                # --- Roles ---
                cursor.execute("""
                    SELECT r.id, r.role_name
                    FROM Roles r
                    JOIN UserRoles ur ON r.id = ur.role_id
                    WHERE ur.user_id = ?
                """, (uid,))
                role_data = cursor.fetchall()
                role_ids = [r[0] for r in role_data]
                role_names = [r[1] for r in role_data]

                user["roles"] = role_names
                user["role_ids"] = role_ids

                # --- Profile Tag Logic ---
                tag = None
                if not user.get("is_active", True):
                    tag = "Awaiting Activation"

                elif "Peer Tutor" in role_names:
                    cursor.execute("SELECT 1 FROM TutorStudents WHERE user_id = ?", (uid,))
                    if not cursor.fetchone():
                        tag = "No Students Assigned"

                elif "Student" in role_names:
                    cursor.execute("""
                        SELECT s.id AS student_id, y.name AS year_name
                        FROM Students s
                        JOIN Years y ON s.year_id = y.id
                        WHERE s.user_id = ?
                    """, (uid,))
                    row = cursor.fetchone()

                    if row:
                        student_id, year_name = row
                        user["student_id"] = student_id
                        user["year_name"] = year_name

                        # CosmosDB Profile Check
                        try:
                            cosmos_result = list(container.query_items(
                                "SELECT c.id FROM c WHERE c.student_id = @sid",
                                parameters=[{"name": "@sid", "value": student_id}],
                                enable_cross_partition_query=True,
                            ))
                            if not cosmos_result:
                                tag = "Profile Incomplete"
                        except Exception as ce:
                            # Fail gracefully but log
                            print(f"CosmosDB query failed for student {student_id}: {ce}")
                            tag = "Profile Incomplete"

                    else:
                        tag = "Profile Incomplete"

                user["profile_tag"] = tag
                
                # Add invite URL for inactive users
                if not user.get("is_active", True):
                    user["invite_url"] = get_or_regenerate_invite_url(uid)
                else:
                    user["invite_url"] = None

            return user_dicts

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def get_users_with_roles(user_ids: list[int]) -> dict[int, dict]:
    """Batch fetch names and roles for multiple users."""
    if not user_ids:
        return {}

    placeholders = ",".join("?" for _ in user_ids)
    query = f"""
    SELECT u.id AS user_id, u.first_name, u.last_name, r.role_name
    FROM Users u
    LEFT JOIN UserRoles ur ON ur.user_id = u.id
    LEFT JOIN Roles r ON r.id = ur.role_id
    WHERE u.id IN ({placeholders})
    """
    with get_sql_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(user_ids))
        results = cursor.fetchall()

    return {
        row.user_id: {
            "name": f"{row.first_name} {row.last_name}",
            "role": row.role_name
        }
        for row in results
    }



def get_user_with_roles_by_id(user_id: int) -> Dict:
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Fetch base user info
            cursor.execute("""
                SELECT u.id, u.first_name, u.last_name, u.email, u.gt_email, 
                       u.profile_picture_url, u.is_active
                FROM Users u
                WHERE u.id = ?
            """, (user_id,))
            row = cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="User not found.")

            column_names = [desc[0] for desc in cursor.description]
            user = dict(zip(column_names, row))

            # Fetch roles
            cursor.execute("""
                SELECT r.id, r.role_name
                FROM Roles r
                JOIN UserRoles ur ON r.id = ur.role_id
                WHERE ur.user_id = ?
            """, (user_id,))
            role_data = cursor.fetchall()
            role_ids = [r[0] for r in role_data]
            role_names = [r[1] for r in role_data]

            user["roles"] = role_names
            user["role_ids"] = role_ids

            # Profile tag logic
            tag = None
            if not user.get("is_active", True):
                tag = "Awaiting Activation"

            elif "Peer Tutor" in role_names:
                cursor.execute("SELECT 1 FROM TutorStudents WHERE user_id = ?", (user_id,))
                if not cursor.fetchone():
                    tag = "No Students Assigned"

            elif "Student" in role_names:
                cursor.execute("""
                    SELECT s.id AS student_id, y.name AS year_name
                    FROM Students s
                    JOIN Years y ON s.year_id = y.id
                    WHERE s.user_id = ?
                """, (user_id,))
                student_row = cursor.fetchone()
                if student_row:
                    user["student_id"] = student_row[0]
                    user["year_name"] = student_row[1]
                else:
                    tag = "Profile Incomplete"

            user["profile_tag"] = tag

            return user

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")




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

            # Mark invite as used
            cursor.execute("UPDATE AccountInvites SET used_at = GETUTCDATE() WHERE id = ?", (invite_id,))

            conn.commit()

            return {"message": "User invite completed successfully.", "user_id": user_id}

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



def delete_user_db(user_id: int) -> dict:
    """
    Deletes a user by ID.

    :param user_id: ID of the user to delete
    :type user_id: int
    :return: A message confirming deletion
    :rtype: dict
    """
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM Users WHERE id = ?", (user_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found.")

            conn.commit()
            return {"message": "User deleted successfully.", "user_id": user_id}

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def get_or_regenerate_invite_url(user_id: int) -> Optional[str]:
    """
    Gets existing valid invite token or regenerates if expired/missing.
    Returns the complete invite URL (not just the token).
    """
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check for existing valid token
            cursor.execute("""
                SELECT 1
                FROM AccountInvites
                WHERE user_id = ? 
                  AND used_at IS NULL
                  AND expires_at > GETUTCDATE()
            """, (user_id,))
            
            if cursor.fetchone():
                # Valid token exists but we can't retrieve it (it's hashed)
                # So we'll regenerate it by deleting old and creating new
                cursor.execute("""
                    DELETE FROM AccountInvites
                    WHERE user_id = ?
                """, (user_id,))
            
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
