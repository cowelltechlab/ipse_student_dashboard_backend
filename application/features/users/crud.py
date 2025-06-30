import datetime
import hashlib
from secrets import token_urlsafe
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



def create_invited_user(email: str, school_email: str, role_ids: List[int]) -> Dict:
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO Users (email, gt_email, is_active, created_at)
            OUTPUT INSERTED.id
            VALUES (?, ?, 0, ?)
            """,
            (email, school_email, datetime.now())
        )
        user_id = cursor.fetchone()[0]

        cursor.executemany(
            "INSERT INTO UserRoles (user_id, role_id) VALUES (?, ?)",
            [(user_id, rid) for rid in role_ids]
        )

        raw_token = token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires = datetime.utcnow() + datetime.timedelta(days=3)

        cursor.execute(
            "INSERT INTO AccountInvites (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, token_hash, expires)
        )

        conn.commit()
        return {"user_id": user_id, "token": raw_token}

    except pyodbc.Error as e:
        print(f"Error creating invited user: {str(e)}")
        conn.rollback()
        return {}

    finally:
        conn.close()


def complete_user_invite(token: str, first_name: str, last_name: str, password_hash: str, profile_picture_url: Optional[str]) -> bool:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT ai.id, u.id AS user_id
            FROM AccountInvites ai
            JOIN Users u ON ai.user_id = u.id
            WHERE ai.token_hash = ? AND ai.expires_at > GETDATE() AND ai.used_at IS NULL
        """, (token_hash,))

        record = cursor.fetchone()
        if not record:
            return False

        invite_id, user_id = record

        cursor.execute("""
            UPDATE Users SET
                first_name = ?, last_name = ?, password_hash = ?, profile_picture_url = ?, is_active = 1
            WHERE id = ?
        """, (first_name, last_name, password_hash, profile_picture_url, user_id))

        cursor.execute("UPDATE AccountInvites SET used_at = GETDATE() WHERE id = ?", (invite_id,))
        conn.commit()
        return True

    except pyodbc.Error as e:
        print(f"Error completing user invite: {str(e)}")
        conn.rollback()
        return False

    finally:
        conn.close()
