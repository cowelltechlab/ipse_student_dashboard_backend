import pytest
from fastapi.testclient import TestClient
from application.app import application
from application.database.mssql_connection import get_sql_db_connection

client = TestClient(application)

def delete_user_by_email(email: str):
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM Users WHERE email = ?", (email,))
    user_row = cursor.fetchone()
    if not user_row:
        cursor.close()
        conn.close()
        return

    user_id = user_row[0]
    cursor.execute("DELETE FROM UserRoles WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM Students WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM Users WHERE id = ?", (user_id,))

    conn.commit()
    cursor.close()
    conn.close()

def test_update_student_writing_level():
    # Cleanup before test
    delete_user_by_email("laura.smith@example.com")

    # Create student first
    new_student = {
        "email": "laura.smith@example.com",
        "first_name": "Laura",
        "last_name": "Smith",
        "gt_email": "lsmith@gatech.edu",
        "password_hash": "hashed_pw_here",
        "year_id": 2,
        "reading_level": 2,
        "writing_level": 2,
        "profile_picture_url": "https://example.com/pic.jpg"
    }
    create_response = client.post("/students/", json=new_student)
    assert create_response.status_code == 201
    created_student = create_response.json()
    student_id = created_student["id"]
    print(created_student)

    update_data = {"first_name": "TEST",
                   "writing_level": 4}
    update_response = client.put(f"/students/{student_id}", json=update_data)
    assert update_response.status_code == 200

    updated_student = update_response.json()
    print("Updated student response:", updated_student)

        # Assert updated field
    assert updated_student["first_name"] == update_data["first_name"]
    assert updated_student["writing_level"] == update_data["writing_level"]

    # Assert unchanged fields
    assert updated_student["year_id"] == new_student["year_id"]
    assert updated_student["reading_level"] == new_student["reading_level"]
    #assert updated_student["writing_level"] == new_student["writing_level"]
    #assert updated_student["first_name"] == new_student["first_name"]
    assert updated_student["last_name"] == new_student["last_name"]


    #delete_user_by_email("mark.smith@example.com")