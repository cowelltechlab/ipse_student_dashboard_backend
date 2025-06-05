from fastapi.testclient import TestClient
from application.app import application
import pyodbc
import pytest
from application.database.mssql_connection import get_sql_db_connection

client = TestClient(application)

@pytest.fixture
def db_connection():
    conn = get_sql_db_connection()
    yield conn
    conn.close()

def test_delete_student_and_associated_records(db_connection):
    cursor = db_connection.cursor()
        # Clean up if user already exists
    cursor.execute("SELECT id FROM Users WHERE email = ?", "frank@example.com")
    existing = cursor.fetchone()
    if existing:
        existing_user_id = existing[0]
        # Delete student-related data first (respecting FK constraints)
        cursor.execute("DELETE FROM TutorStudents WHERE student_id IN (SELECT id FROM Students WHERE user_id = ?)", existing_user_id)
        cursor.execute("DELETE FROM StudentAssignments WHERE student_id IN (SELECT id FROM Students WHERE user_id = ?)", existing_user_id)
        cursor.execute("DELETE FROM StudentRatings WHERE student_id IN (SELECT id FROM Students WHERE user_id = ?)", existing_user_id)
        cursor.execute("DELETE FROM StudentClasses WHERE student_id IN (SELECT id FROM Students WHERE user_id = ?)", existing_user_id)
        cursor.execute("DELETE FROM Students WHERE user_id = ?", existing_user_id)
        cursor.execute("DELETE FROM UserRoles WHERE user_id = ?", existing_user_id)
        cursor.execute("DELETE FROM Users WHERE id = ?", existing_user_id)
        db_connection.commit()

    # Continue as normal
    cursor.execute("""
        INSERT INTO Users (email, first_name, last_name, gt_email, password_hash, created_at)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, GETDATE())
    """, "frank@example.com", "Frank", "Doe", "frank@gatech.edu", "hashed_pw_here")
    student_user_id = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO Students (user_id, year_id, reading_level, writing_level, profile_picture_url, active_status)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, 1)
    """, student_user_id, 2, 3, 4, "https://example.com/pic.jpg")
    student_id = cursor.fetchone()[0]
    
   # student_id = 108
    tutor_user_id = 4
    #student_user_id = 116  # user_id in Users table for the student
    
    # Insert related records manually for test setup
    cursor.execute("""
        INSERT INTO StudentAssignments (student_id, assignment_id, date_modified, is_final_version)
        VALUES (?, 1, GETDATE(), 1)
    """, student_id)
    
    cursor.execute("""
        INSERT INTO StudentRatings (student_id, assignment_id, difficulty_rating, best_changes, disliked_changes, date_submitted)
        VALUES (?, 1, 4, 'Clear intro', 'Long conclusion', GETDATE())
    """, student_id)
    
    cursor.execute("""
        INSERT INTO StudentClasses (student_id, class_id, learning_goal)
        VALUES (?, 5, 'Improve thesis writing')
    """, student_id)
    
    cursor.execute("""
        INSERT INTO TutorStudents (user_id, student_id)
        VALUES (?, ?)
    """, tutor_user_id, student_id)
    
    cursor.execute("""
        SELECT 1 FROM UserRoles WHERE user_id = ? AND role_id = 3
    """, student_user_id)
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO UserRoles (user_id, role_id)
            VALUES (?, 3)
        """, student_user_id)

    
    db_connection.commit()
    
    # 2. Delete the student
    delete_response = client.delete(f"/students/{student_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": f"Student with id {student_id} deleted successfully."}

    # 3. Verify student no longer exists
    get_response = client.get(f"/students/{student_id}")
    assert get_response.status_code == 404

    # 4. Optionally verify associated records no longer exist, e.g.:
    # assignment_response = client.get(f"/student_assignments/?student_id={student_id}")
    # assert assignment_response.json() == []

    # rating_response = client.get(f"/student_ratings/?student_id={student_id}")
    # assert rating_response.json() == []

    # Now run your delete student test logic here...
    
    # For example, call your API endpoint to delete the student
    # And assert the results
    
    cursor.close()


