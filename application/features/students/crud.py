from http.client import HTTPException
from application.database.mssql_crud_helpers import (
    fetch_by_id, 
)
import pyodbc
from application.database.mssql_connection import get_sql_db_connection

TABLE_NAME = "Students"

def fetch_all_students_with_names():
    """Fetch all students with their first and last names joined from Users table."""
    try:
        # TODO: Improve student activation query
        # Added first name is not null to account for account activation not being done before assignment is given
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            query = """
            SELECT
                students.id,
                students.year_id,
                students.reading_level,
                students.writing_level,
                students.active_status,
                users.first_name,
                users.last_name,
                users.email,
                years.name AS year_name
            FROM students
            JOIN users ON students.user_id = users.id
            JOIN years ON students.year_id = years.id
            WHERE users.is_active = 1
            AND users.first_name IS NOT NULL
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    

def get_students_by_year(year_id: int):
    try:
        query = """
        SELECT
            students.id,
            students.year_id,
            students.reading_level,
            students.writing_level,
            students.active_status,
            users.first_name,
            users.last_name,
            users.email,
            years.name AS year_name
        FROM students
        JOIN users ON students.user_id = users.id
        JOIN years ON students.year_id = years.id
        WHERE students.year_id = ?
        """
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (year_id,))
            rows = cursor.fetchall()
            return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def add_student(data):
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Insert into Users
            insert_user_query = """
            INSERT INTO Users (email, first_name, last_name, gt_email, password_hash, created_at)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, GETUTCDATE())
            """
            cursor.execute(insert_user_query, (
                data["email"],
                data.get("first_name"),
                data.get("last_name"),
                data.get("gt_email"),
                data.get("password_hash")
            ))
            user_id = cursor.fetchone()[0]

            # Insert into UserRoles (role_id=3 → student)
            insert_role_query = "INSERT INTO UserRoles (user_id, role_id) VALUES (?, ?)"
            cursor.execute(insert_role_query, (user_id, 3))

            # Insert into Students
            insert_student_query = """
            INSERT INTO Students (user_id, year_id, reading_level, writing_level, profile_picture_url)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(insert_student_query, (
                user_id,
                data["year_id"],
                data.get("reading_level"),
                data.get("writing_level"),
                data.get("profile_picture_url")
            ))
            student_id = cursor.fetchone()[0]

            # Get year name
            cursor.execute("SELECT name FROM Years WHERE id = ?", (data["year_id"],))
            year_row = cursor.fetchone()
            if not year_row:
                raise HTTPException(status_code=404, detail=f"Year {data['year_id']} not found")
            year_name = year_row[0]

            conn.commit()

            return {
                "id": student_id,
                "user_id": user_id,
                "email": data["email"],
                "first_name": data.get("first_name"),
                "last_name": data.get("last_name"),
                "year_name": year_name,
                "reading_level": data.get("reading_level"),
                "writing_level": data.get("writing_level"),
                "profile_picture_url": data.get("profile_picture_url"),
                "active_status": True
            }

    except HTTPException:
        raise  
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



def update_student(student_id: int, update_data: dict):
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # 1. Fetch existing user and student records
            cursor.execute("""
                SELECT u.id as user_id, u.email, u.first_name, u.last_name, u.gt_email,
                        s.id as student_id, s.year_id, s.reading_level, s.writing_level, 
                        s.profile_picture_url, s.active_status
                FROM Students s
                JOIN Users u ON s.user_id = u.id
                WHERE s.id = ?
            """, (student_id,))
            existing = cursor.fetchone()
            if not existing:
                raise ValueError("Student not found")

            columns = [col[0] for col in cursor.description]
            existing_record = dict(zip(columns, existing))

            # 2. Separate user and student fields
            user_fields = {"email", "first_name", "last_name", "gt_email"}
            student_fields = {"year_id", "reading_level", "writing_level", 
                                "profile_picture_url", "active_status"}

            # 3. Merge update_data with existing data
            user_update_data = {f: update_data.get(f, existing_record[f]) for f in user_fields}
            student_update_data = {f: update_data.get(f, existing_record[f]) for f in student_fields}

            # 4. Validate required fields
            for f in ["first_name", "last_name"]:
                if user_update_data.get(f) is None:
                    raise ValueError(f"Required field '{f}' cannot be None")
            for f in ["writing_level", "active_status"]:
                if student_update_data.get(f) is None:
                    raise ValueError(f"Required field '{f}' cannot be None")

            # 5. Update Users table
            user_set = ", ".join([f"{k} = ?" for k in user_update_data])
            user_query = f"UPDATE Users SET {user_set} WHERE id = ?"
            cursor.execute(user_query, list(user_update_data.values()) + [existing_record["user_id"]])

            # 6. Update Students table
            student_set = ", ".join([f"{k} = ?" for k in student_update_data])
            student_query = f"UPDATE Students SET {student_set} WHERE id = ?"
            cursor.execute(student_query, list(student_update_data.values()) + [student_id])

            conn.commit()

            # 7. Return updated record
            cursor.execute("""
                SELECT s.id, s.user_id, s.year_id, y.name AS year_name,
                        s.reading_level, s.writing_level, s.profile_picture_url, s.active_status,
                        u.email, u.first_name, u.last_name, u.gt_email
                FROM Students s
                JOIN Users u ON s.user_id = u.id
                JOIN Years y ON s.year_id = y.id
                WHERE s.id = ?
            """, (student_id,))
            result = cursor.fetchone()
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, result))

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



def delete_student(student_id: int):
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            # Check student exists
            cursor.execute("SELECT id FROM Students WHERE id = ?", (student_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Student not found")

            # Delete from associated tables
            cursor.execute("DELETE FROM StudentAssignments WHERE student_id = ?", (student_id,))
            cursor.execute("DELETE FROM StudentRatings WHERE student_id = ?", (student_id,))
            cursor.execute("DELETE FROM StudentClasses WHERE student_id = ?", (student_id,))
            cursor.execute("DELETE FROM TutorStudents WHERE student_id = ?", (student_id,))

            # Delete role for the user (role_id=3 for student)
            cursor.execute("""
                DELETE FROM UserRoles 
                WHERE user_id = (SELECT user_id FROM Students WHERE id = ?) 
                    AND role_id = 3
            """, (student_id,))

            # Delete the student record
            cursor.execute("DELETE FROM Students WHERE id = ?", (student_id,))

            conn.commit()

            return {"success": True}

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



def get_student_by_student_id(student_id):
    return fetch_by_id(TABLE_NAME, student_id)


def get_student_by_user_id(user_id: int):
    """Fetch a student record by user_id."""
 
    try:
        query = """
        SELECT s.id, s.user_id, s.year_id, y.name AS year_name,
               s.reading_level, s.writing_level, s.active_status,
               u.email, u.first_name, u.last_name, u.gt_email, u.profile_picture_url
        FROM Students s
        JOIN Users u ON s.user_id = u.id
        JOIN Years y ON s.year_id = y.id
        WHERE s.user_id = ?
        """
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
                
            cursor.execute(query, (user_id,))
            record = cursor.fetchone()
            if not record:
                return None
            column_names = [column[0] for column in cursor.description]
            return dict(zip(column_names, record))
    except pyodbc.Error as e:
        return {"error": str(e)}


def update_student_profile_pic(student_id: int, profile_pic_url: str):
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Check if student exists
            cursor.execute("SELECT id FROM Students WHERE id = ?", student_id)
            if not cursor.fetchone():
                print("Student not found")

            # Update profile picture URL
            update_query = "UPDATE Students SET profile_picture_url = ? WHERE id = ?"
            cursor.execute(update_query, (profile_pic_url, student_id))

            conn.commit()

            # Optionally fetch updated record to return (optional)
            cursor.execute("""
                SELECT 
                    s.id, s.user_id, s.year_id, y.name AS year_name,
                    s.reading_level, s.writing_level, s.profile_picture_url, s.active_status,
                    u.email, u.first_name, u.last_name, u.gt_email
                FROM Students s
                JOIN Users u ON s.user_id = u.id
                JOIN Years y ON s.year_id = y.id
                WHERE s.id = ?
            """, (student_id,))
            updated_student = cursor.fetchone()
            if updated_student:
                columns = [col[0] for col in cursor.description]
                return dict(zip(columns, updated_student))
            else:
                return {"message": "Profile picture updated, but failed to fetch updated record"}

    except Exception as e:
        raise e