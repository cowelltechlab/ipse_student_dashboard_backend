from application.database.mssql_crud_helpers import (
    create_record, 
    delete_record, 
    fetch_by_id, 
)
import pyodbc
from application.database.mssql_connection import get_sql_db_connection
from application.features.students.schemas import StudentUpdate

TABLE_NAME = "Students"

def fetch_all_students_with_names():
    """Fetch all students with their first and last names joined from Users table."""
    conn = get_sql_db_connection()
    with conn.cursor() as cursor:
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
            users.profile_picture_url,
            years.name AS year_name
        FROM students
        JOIN users ON students.user_id = users.id
        JOIN years ON students.year_id = years.id
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

def fetch_by_id(table_name, record_id):
    """Fetch a single student record by student ID, with user and year joins."""
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT s.id, s.user_id, s.reading_level, s.writing_level, s.active_status,
               u.first_name, u.last_name, u.email, u.gt_email, u.profile_picture_url,
               y.name AS year_name
        FROM students s
        JOIN users u ON s.user_id = u.id
        JOIN years y ON s.year_id = y.id
        WHERE s.id = ?
        """
        cursor.execute(query, (record_id,))

        record = cursor.fetchone()
        if not record:
            return None

        column_names = [column[0] for column in cursor.description]
        return dict(zip(column_names, record))

    except pyodbc.Error as e:
        return {"error": str(e)}
    finally:
        conn.close()


def get_students_by_year(year_id: int):
    conn = get_sql_db_connection()
    with conn.cursor() as cursor:
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
            users.profile_picture_url,
            years.name AS year_name
        FROM students
        JOIN users ON students.user_id = users.id
        JOIN years ON students.year_id = years.id
        WHERE students.year_id = ?
        """
        cursor.execute(query, (year_id,))
        rows = cursor.fetchall()
        return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

def create_record(data):
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
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

        # Insert into UserRoles, create a role of student
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

        # Get year name from Years table
        cursor.execute("SELECT name FROM Years WHERE id = ?", (data["year_id"],))
        year_row = cursor.fetchone()
        year_name = year_row[0] if year_row else None

        conn.commit()

        return {
            "id": student_id,
            "user_id": user_id,
            "email": data["email"],
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "year_name": year_name,  # <-- Add this
            "reading_level": data.get("reading_level"),
            "writing_level": data.get("writing_level"),
            "profile_picture_url": data.get("profile_picture_url"),
            "active_status": True  # Optional: if you want to include this
        }

    except pyodbc.Error as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()

def update_student_record(student_id: int, update_data: dict):
    conn = get_sql_db_connection()
    with conn.cursor() as cursor:
        # 1. Fetch existing user and student records
        cursor.execute("""
            SELECT u.id as user_id, u.email, u.first_name, u.last_name, u.gt_email,
                   s.id as student_id, s.year_id, s.reading_level, s.writing_level, s.profile_picture_url, s.active_status
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
        student_fields = {"year_id", "reading_level", "writing_level", "profile_picture_url", "active_status"}

        # 3. Merge update_data with existing data (retain original if not updated)
        user_update_data = {field: update_data.get(field, existing_record[field]) for field in user_fields}
        student_update_data = {field: update_data.get(field, existing_record[field]) for field in student_fields}

        # 4. Validate required fields individually in their respective dicts
        required_user_fields = ["first_name", "last_name"]
        required_student_fields = ["writing_level", "active_status"]

        for field in required_user_fields:
            if user_update_data.get(field) is None:
                raise ValueError(f"Required field '{field}' cannot be None")

        for field in required_student_fields:
            if student_update_data.get(field) is None:
                raise ValueError(f"Required field '{field}' cannot be None")

        # 5. Update Users table
        user_set_clauses = [f"{k} = ?" for k in user_update_data]
        user_values = list(user_update_data.values()) + [existing_record["user_id"]]
        user_update_query = f"UPDATE Users SET {', '.join(user_set_clauses)} WHERE id = ?"
        cursor.execute(user_update_query, user_values)

        # 6. Update Students table
        student_set_clauses = [f"{k} = ?" for k in student_update_data]
        student_values = list(student_update_data.values()) + [student_id]
        student_update_query = f"UPDATE Students SET {', '.join(student_set_clauses)} WHERE id = ?"
        cursor.execute(student_update_query, student_values)

        conn.commit()

        # 7. Return updated student record
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
        new_student_record = cursor.fetchone()
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, new_student_record))

def delete_student_records(student_id: int):
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    # Check student exists
    cursor.execute("SELECT id FROM Students WHERE id = ?", student_id)
    row = cursor.fetchone()
    if not row:
        return {"error": "Student not found"}

    # Delete from associated tables
    cursor.execute("DELETE FROM StudentAssignments WHERE student_id = ?", student_id)
    cursor.execute("DELETE FROM StudentRatings WHERE student_id = ?", student_id)
    cursor.execute("DELETE FROM StudentClasses WHERE student_id = ?", student_id)
    cursor.execute("DELETE FROM TutorStudents WHERE student_id = ?", student_id)


    # Delete role for the user (assuming Users table and role_id=3 for student)
    cursor.execute("""
        DELETE FROM UserRoles WHERE user_id = (
            SELECT user_id FROM Students WHERE id = ?
        ) AND role_id = 3
    """, student_id)

    # Delete the student record
    cursor.execute("DELETE FROM Students WHERE id = ?", student_id)

    conn.commit()
    cursor.close()
    conn.close()

    return {"success": True}


''' 
*** GET STUDENTS ENDPOINT *** 
Fetch all students in Students table
Joins from Users table to retrieve the first and last name

Depending on Query param, it will fetch by year_id
'''
def get_all_students():
    return fetch_all_students_with_names()

''' 
*** GET STUDENTS BY ID ENDPOINT *** 
Fetch students in Students table based on ID
Joins from Users table to retrieve the first and last name
'''
def get_student_by_student_id(student_id):
    return fetch_by_id(TABLE_NAME, student_id)


def get_student_by_user_id(user_id: int):
    """Fetch a student record by user_id."""
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT s.id, s.user_id, s.year_id, y.name AS year_name,
               s.reading_level, s.writing_level, s.profile_picture_url, s.active_status,
               u.email, u.first_name, u.last_name, u.gt_email
        FROM Students s
        JOIN Users u ON s.user_id = u.id
        JOIN Years y ON s.year_id = y.id
        WHERE s.user_id = ?
        """
        cursor.execute(query, (user_id,))
        record = cursor.fetchone()
        if not record:
            return None
        column_names = [column[0] for column in cursor.description]
        return dict(zip(column_names, record))
    except pyodbc.Error as e:
        return {"error": str(e)}
    finally:
        conn.close()

''' 
*** POST STUDENT ENDPOINT *** 
Add a new Student in Students table
1. create a new user
2. assign a role_id of students (3 == Students)
3. create a student
'''
def add_student(data):
    return create_record(data)

''' 
*** UPDATE STUDENT ENDPOINT *** 
Update existing Student in Students table
Update values can be student fields or user fields
'''
def update_student(student_id, data):
    return update_student_record(student_id, data)

''' 
*** DELETE STUDENT ENDPOINT *** 
Delete a Student Record
Delete all student related records:
- StudentAssignments
- StudentRatings 
- StudentClasses
- TutorStudent
- UserRole
The User is not deleted
'''
def delete_student(student_id):
    return delete_student_records(student_id)


def update_student_profile_pic(student_id: int, profile_pic_url: str):
    conn = get_sql_db_connection()
    try:
        with conn.cursor() as cursor:
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
        conn.rollback()
        raise e
    finally:
        conn.close()

''' 
*** GET STUDENT PROFILE PICTURE *** 
Get a student's profile picture url from Student Record
Based on id (Student_id)
'''
def get_student_profile_picture(student_id: int):
    conn = get_sql_db_connection()
    try:
        with conn.cursor() as cursor:
            query = """
            SELECT profile_picture_url
            FROM Students
            WHERE id = ?
            """
            cursor.execute(query, (student_id,))
            result = cursor.fetchone()
            if result:
                return {"student_id": student_id, "profile_picture_url": result[0]}
            else:
                return None
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()
