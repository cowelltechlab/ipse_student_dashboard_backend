import os
from typing import List, Dict, Optional

from dotenv import load_dotenv
from application.database.mssql_connection import get_sql_db_connection
import pyodbc
from fastapi import HTTPException

from application.database.nosql_connection import get_cosmos_db_connection

load_dotenv()
DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME")


CONTAINER_NAME = "ai-student-profile"

client = get_cosmos_db_connection()
db = client.get_database_client(DATABASE_NAME)
container = db.get_container_client(CONTAINER_NAME)


def get_all_users_with_roles(role_id: Optional[int] = None, tutor_user_id: Optional[int] = None) -> List[Dict]:
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Base query
            if tutor_user_id is not None:
                # Filter to only students assigned to the tutor
                query = """
                    SELECT u.id, u.first_name, u.last_name, u.email, u.gt_email, 
                           u.profile_picture_url, u.is_active
                    FROM Users u
                    JOIN Students s ON s.user_id = u.id
                    JOIN TutorStudents ts ON ts.student_id = s.id
                    WHERE ts.user_id = ?
                """
                if role_id is not None:
                    query += " AND EXISTS (SELECT 1 FROM UserRoles ur WHERE ur.user_id = u.id AND ur.role_id = ?)"
                    cursor.execute(query, (tutor_user_id, role_id))
                else:
                    cursor.execute(query, (tutor_user_id,))
            elif role_id is not None:
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
                    from .user_invitations import regenerate_invite_url
                    user["invite_url"] = regenerate_invite_url(uid)
                else:
                    user["invite_url"] = None

            return user_dicts

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def get_all_users_with_roles_allowed(
    allowed_role_names: set[str],
    role_id: Optional[int] = None,
    tutor_user_id: Optional[int] = None
) -> List[Dict]:
    """
    Reuses get_all_users_with_roles and filters the results to allowed roles.
    """
    all_users = get_all_users_with_roles(role_id=role_id, tutor_user_id=tutor_user_id)
    if not all_users:
        return []

    # Keep users whose single role is in the allowed set.
    filtered = []
    for u in all_users:
        role_names = u.get("roles", [])
        if not role_names:
            continue
        if role_names[0] in allowed_role_names:
            filtered.append(u)
    return filtered


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
    


def update_user_email(user_id: int, email: Optional[str] = None, gt_email: Optional[str] = None) -> Dict:
    """Update a user's email and/or gt_email. Either or both can be updated."""
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Check if user exists
            cursor.execute("SELECT id FROM Users WHERE id = ?", (user_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

            # Build dynamic update query based on provided fields
            update_fields = []
            update_values = []

            if email is not None:
                update_fields.append("email = ?")
                update_values.append(email)

            if gt_email is not None:
                update_fields.append("gt_email = ?")
                update_values.append(gt_email)

            if not update_fields:
                raise HTTPException(status_code=400, detail="At least one email must be provided")

            # Execute update
            update_query = f"UPDATE Users SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(user_id)
            cursor.execute(update_query, update_values)
            conn.commit()

            # Return updated user details (join with Students if exists)
            cursor.execute("""
                SELECT
                    s.id AS student_id,
                    u.id AS user_id,
                    u.first_name,
                    u.last_name,
                    u.email,
                    u.gt_email,
                    u.profile_picture_url,
                    s.group_type,
                    s.ppt_embed_url,
                    s.ppt_edit_url
                FROM Users u
                LEFT JOIN Students s ON s.user_id = u.id
                WHERE u.id = ?
            """, (user_id,))

            result = cursor.fetchone()
            if result:
                column_names = [desc[0] for desc in cursor.description]
                return dict(zip(column_names, result))
            else:
                raise HTTPException(status_code=404, detail="Failed to retrieve updated user")

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")