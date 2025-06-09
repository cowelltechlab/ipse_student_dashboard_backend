import subprocess
import pytest
from fastapi.testclient import TestClient
from application.app import application 

client = TestClient(application)


def test_get_students_endpoint():
    response = client.get("/students/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        student = data[0]
        assert "id" in student
        assert "first_name" in student
        assert "last_name" in student
        assert "reading_level" in student
        assert "writing_level" in student


def test_curl_get_students():
    result = subprocess.run(
        ["curl", "-s", "-X", "GET", "http://localhost:8000/students/"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "first_name" in result.stdout  # crude check if names appear
