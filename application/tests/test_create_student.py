import pytest
from fastapi.testclient import TestClient
from application.app import application
from application.database.mssql_connection import get_sql_db_connection

client = TestClient(application)

import pyodbc

def delete_user_by_email(email: str):
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    # Find user id first
    cursor.execute("SELECT id FROM Users WHERE email = ?", (email,))
    user_row = cursor.fetchone()
    if not user_row:
        # No such user, nothing to delete
        cursor.close()
        conn.close()
        return

    user_id = user_row[0]

    # Delete related records from UserRoles (to avoid FK conflicts)
    cursor.execute("DELETE FROM UserRoles WHERE user_id = ?", (user_id,))
    # Delete related student record(s)
    cursor.execute("DELETE FROM Students WHERE user_id = ?", (user_id,))
    # Then delete from Users
    cursor.execute("DELETE FROM Users WHERE id = ?", (user_id,))

    conn.commit()
    cursor.close()
    conn.close()

def test_create_student_with_names():
    delete_user_by_email("alice.smith@example.com")
    new_student = {
        "email": "alice.smith@example.com",
        "first_name": "Alice",
        "last_name": "Smith",
        "gt_email": "asmith@gatech.edu",
        "password_hash": "hashed_pw_here",
        "year_id": 3,
        "reading_level": 3,
        "writing_level": 4,
        "profile_picture_url": "https://example.com/pic.jpg"
    }
    
    response = client.post("/students/", json=new_student)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    # assert "user_id" in data
    assert data["year_id"] == new_student["year_id"]
    assert data["reading_level"] == new_student["reading_level"]
    assert data["writing_level"] == new_student["writing_level"]
    assert data["first_name"] == new_student["first_name"]
    assert data["last_name"] == new_student["last_name"]
