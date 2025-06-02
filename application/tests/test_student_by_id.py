import pytest
from fastapi.testclient import TestClient
from application.app import application  # your FastAPI app import

client = TestClient(application)
def test_fetch_student_by_id_success():
    # Assume student with id=1 exists in your test DB setup
    student_id = 1

    response = client.get(f"/students/{student_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == student_id
    assert "first_name" in data
    assert "last_name" in data
    assert "reading_level" in data
    assert "writing_level" in data

def test_fetch_student_by_id_not_found():
    # Use an ID that you know does NOT exist
    non_existing_id = 999999

    response = client.get(f"/students/{non_existing_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": f"Student with id {non_existing_id} not found."}