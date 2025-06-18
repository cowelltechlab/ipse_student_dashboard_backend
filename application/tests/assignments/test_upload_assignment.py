import pytest
from fastapi.testclient import TestClient
from application.app import application
import os

client = TestClient(application)

def test_upload_assignment_with_file():
    test_file_path = os.path.join(os.path.dirname(__file__), "test_assignment_ipse.pdf")

    with open(test_file_path, "rb") as file:
        data = {
            "student_id": "1",
            "title": "Test Assignment IPSE",
            "class_id": "2"
        }

        files = {
            "file": ("test_assignment_ipse.pdf", file, "application/pdf")
        }

        response = client.post("/assignments/upload", data=data, files=files)

        assert response.status_code == 200, f"Failed with: {response.text}"

        response_json = response.json()
        assert "id" in response_json
        assert response_json["title"] == data["title"]
        assert response_json["blob_url"].startswith("https://")
        assert "content" in response_json and len(response_json["content"].strip()) > 0
