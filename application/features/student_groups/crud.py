from typing import List, Dict, Optional
from application.database.mssql_connection import get_sql_db_connection
import pyodbc
from fastapi import HTTPException

def get_students_with_details(tutor_user_id: Optional[int] = None) -> List[Dict]:
    """
    Fetch students with their details from Users and Students tables.
    If tutor_user_id is provided, filter to only students assigned to that tutor.
    """
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            if tutor_user_id is not None:
                # Filter to only students assigned to the tutor
                query = """
                    SELECT
                        s.id AS student_id,
                        u.first_name,
                        u.last_name,
                        u.email,
                        u.gt_email,
                        u.profile_picture_url,
                        s.group_type,
                        s.ppt_embed_url,
                        s.ppt_edit_url
                    FROM Users u
                    JOIN Students s ON s.user_id = u.id
                    JOIN TutorStudents ts ON ts.student_id = s.id
                    WHERE ts.user_id = ?
                    AND u.is_active = 1
                    AND u.first_name IS NOT NULL
                """
                cursor.execute(query, (tutor_user_id,))
            else:
                # Get all students
                query = """
                    SELECT
                        s.id AS student_id,
                        u.first_name,
                        u.last_name,
                        u.email,
                        u.gt_email,
                        u.profile_picture_url,
                        s.group_type,
                        s.ppt_embed_url,
                        s.ppt_edit_url
                    FROM Users u
                    JOIN Students s ON s.user_id = u.id
                    WHERE u.is_active = 1
                    AND u.first_name IS NOT NULL
                """
                cursor.execute(query)

            rows = cursor.fetchall()
            if not rows:
                return []

            column_names = [desc[0] for desc in cursor.description]
            return [dict(zip(column_names, row)) for row in rows]

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

def update_student_group_type(student_id: int, group_type: str) -> Dict:
    """Update a student's group_type."""
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Check if student exists
            cursor.execute("SELECT id FROM Students WHERE id = ?", (student_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"Student with id {student_id} not found")

            # Update group_type
            update_query = "UPDATE Students SET group_type = ? WHERE id = ?"
            cursor.execute(update_query, (group_type, student_id))
            conn.commit()

            # Return updated student details
            cursor.execute("""
                SELECT
                    s.id AS student_id,
                    u.first_name,
                    u.last_name,
                    u.profile_picture_url,
                    s.group_type,
                    s.ppt_embed_url,
                    s.ppt_edit_url
                FROM Students s
                JOIN Users u ON s.user_id = u.id
                WHERE s.id = ?
            """, (student_id,))

            result = cursor.fetchone()
            if result:
                column_names = [desc[0] for desc in cursor.description]
                return dict(zip(column_names, result))
            else:
                raise HTTPException(status_code=404, detail="Failed to retrieve updated student")

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

def update_student_ppt_urls(student_id: int, ppt_embed_url: Optional[str] = None, ppt_edit_url: Optional[str] = None) -> Dict:
    """Update a student's PowerPoint URLs. Either or both URLs can be updated."""
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Check if student exists
            cursor.execute("SELECT id FROM Students WHERE id = ?", (student_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"Student with id {student_id} not found")

            # Build dynamic update query based on provided fields
            update_fields = []
            update_values = []

            if ppt_embed_url is not None:
                update_fields.append("ppt_embed_url = ?")
                update_values.append(ppt_embed_url)

            if ppt_edit_url is not None:
                update_fields.append("ppt_edit_url = ?")
                update_values.append(ppt_edit_url)

            if not update_fields:
                raise HTTPException(status_code=400, detail="At least one URL must be provided")

            # Execute update
            update_query = f"UPDATE Students SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(student_id)
            cursor.execute(update_query, update_values)
            conn.commit()

            # Return updated student details
            cursor.execute("""
                SELECT
                    s.id AS student_id,
                    u.first_name,
                    u.last_name,
                    u.profile_picture_url,
                    s.group_type,
                    s.ppt_embed_url,
                    s.ppt_edit_url
                FROM Students s
                JOIN Users u ON s.user_id = u.id
                WHERE s.id = ?
            """, (student_id,))

            result = cursor.fetchone()
            if result:
                column_names = [desc[0] for desc in cursor.description]
                return dict(zip(column_names, result))
            else:
                raise HTTPException(status_code=404, detail="Failed to retrieve updated student")

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
def update_student_email(student_id: int, email: Optional[str] = None, gt_email: Optional[str] = None) -> Dict:
    """Update a student's email and/or gt_email. Either or both can be updated."""
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Check if student exists and get associated user_id
            cursor.execute("SELECT user_id FROM Students WHERE id = ?", (student_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Student with id {student_id} not found")
            user_id = row[0]

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

            # Return updated student details
            cursor.execute("""
                SELECT
                    s.id AS student_id,
                    u.first_name,
                    u.last_name,
                    u.email,
                    u.gt_email,
                    u.profile_picture_url,
                    s.group_type,
                    s.ppt_embed_url,
                    s.ppt_edit_url
                FROM Students s
                JOIN Users u ON s.user_id = u.id
                WHERE s.id = ?
            """, (student_id,))

            result = cursor.fetchone()
            if result:
                column_names = [desc[0] for desc in cursor.description]
                return dict(zip(column_names, result))
            else:
                raise HTTPException(status_code=404, detail="Failed to retrieve updated student")

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")