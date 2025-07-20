import datetime
import hashlib
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
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        if role_id is not None:
            query = """
                SELECT u.id, u.first_name, u.last_name, u.email, u.gt_email, u.profile_picture_url, u.is_active
                FROM Users u
                JOIN UserRoles ur ON u.id = ur.user_id
                WHERE ur.role_id = ?
            """
            cursor.execute(query, (role_id,))
        else:
            query = """
                SELECT u.id, u.first_name, u.last_name, u.email, u.gt_email, u.profile_picture_url, u.is_active
                FROM Users u
            """
            cursor.execute(query)

        users = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        user_dicts = [dict(zip(column_names, row)) for row in users]

        for user in user_dicts:
            uid = user["id"]

            # Roles
            cursor.execute("""
                SELECT r.id, r.role_name
                FROM Roles r
                JOIN UserRoles ur ON r.id = ur.role_id
                WHERE ur.user_id = ?
            """, (uid,))
            role_data = cursor.fetchall()
            role_names = [r[1] for r in role_data]
            role_ids = [r[0] for r in role_data]

            user["roles"] = role_names
            user["role_ids"] = role_ids

            # Tags for home page display
            # Default: No tag
            tag = None

            if not user.get("is_active", True):
                tag = "Awaiting Activation"
            elif "Peer Tutor" in role_names:
                cursor.execute("""
                    SELECT 1 FROM TutorStudents WHERE user_id = ?
                """, (uid,))
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

                    # New: Check if Cosmos profile exists
                    cosmos_result = list(container.query_items(
                        "SELECT c.id FROM c WHERE c.student_id = @sid",
                        parameters=[{"name": "@sid", "value": student_id}],
                        enable_cross_partition_query=True,
                    ))

                    if not cosmos_result:
                        tag = "Profile Incomplete"

                else:
                    tag = "Profile Incomplete"

            user["profile_tag"] = tag

        return user_dicts

    except pyodbc.Error as e:
        print(f"Error fetching users: {str(e)}")
        return []
    finally:
        conn.close()


def get_user_with_roles_by_id(user_id: int) -> Optional[Dict]:
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        # Fetch base user info
        cursor.execute("""
            SELECT u.id, u.first_name, u.last_name, u.email, u.gt_email, u.profile_picture_url, u.is_active
            FROM Users u
            WHERE u.id = ?
        """, (user_id,))
        row = cursor.fetchone()

        if not row:
            return None

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
        role_names = [r[1] for r in role_data]
        role_ids = [r[0] for r in role_data]

        user["roles"] = role_names
        user["role_ids"] = role_ids

        # Profile tag logic
        tag = None

        if not user.get("is_active", True):
            tag = "Awaiting Activation"
        elif "Peer Tutor" in role_names:
            cursor.execute("""
                SELECT 1 FROM TutorStudents WHERE user_id = ?
            """, (user_id,))
            if not cursor.fetchone():
                tag = "No Students Assigned"
        elif "Student" in role_names:
            cursor.execute("""
                SELECT s.id AS student_id, y.name AS year_name
                FROM Students s
                JOIN Years y ON s.year_id = y.id
                WHERE s.user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            if row:
                user["student_id"] = row[0]
                user["year_name"] = row[1]
            else:
                tag = "Profile Incomplete"

        user["profile_tag"] = tag

        return user

    except pyodbc.Error as e:
        print(f"Error fetching user by ID: {str(e)}")
        return None
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
            (email, school_email, datetime.datetime.now())
        )
        user_id = cursor.fetchone()[0]

        cursor.executemany(
            "INSERT INTO UserRoles (user_id, role_id) VALUES (?, ?)",
            [(user_id, rid) for rid in role_ids]
        )

        raw_token = token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires = datetime.datetime.utcnow() + datetime.timedelta(days=3)

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



def get_user_id_from_invite_token(token: str) -> Optional[int]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT u.id
            FROM AccountInvites ai
            JOIN Users u ON ai.user_id = u.id
            WHERE ai.token_hash = ? AND ai.expires_at > GETDATE() AND ai.used_at IS NULL
        """, (token_hash,))

        record = cursor.fetchone()
        return record[0] if record else None

    except pyodbc.Error as e:
        print(f"Error fetching user from token: {str(e)}")
        return None
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


def delete_user_db(user_id: int) -> bool:
    """
    Deletes a user by ID. Returns True if successful, False otherwise.
    
    :param user_id: ID of the user to delete
    :type user_id: int
    :return: True if deletion was successful, False otherwise
    :rtype: bool
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM Users WHERE id = ?", (user_id,))
        conn.commit()
        return True

    except pyodbc.Error as e:
        print(f"Error deleting user: {str(e)}")
        conn.rollback()
        return False

    finally:
        conn.close()