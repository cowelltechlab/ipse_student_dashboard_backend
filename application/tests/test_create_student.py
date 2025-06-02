import subprocess
import pytest
from fastapi.testclient import TestClient
from application.app import application 

client = TestClient(application)

def test_create_student_with_names():
    new_student = {
        "user_id": 1,
        "year_id": 2025,
        "reading_level": 3,
        "writing_level": 4,
        "first_name": "Alice",
        "last_name": "Smith"
    }

    response = client.post("/students/", json=new_student)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["user_id"] == new_student["user_id"]
    assert data["year_id"] == new_student["year_id"]
    assert data["reading_level"] == new_student["reading_level"]
    assert data["writing_level"] == new_student["writing_level"]
    assert data["first_name"] == new_student["first_name"]
    assert data["last_name"] == new_student["last_name"]
