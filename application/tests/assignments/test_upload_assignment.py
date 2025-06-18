import pytest
from fastapi.testclient import TestClient
from application.app import application
import os

client = TestClient(application)

def test_upload_assignment_with_file():
    base_filename = "test_assignment_ipse"
    pdf_path = os.path.join(os.path.dirname(__file__), f"{base_filename}.pdf")
    docx_path = os.path.join(os.path.dirname(__file__), f"{base_filename}.docx")

    # Test PDF upload
    with open(pdf_path, "rb") as pdf_file:
        data = {
            "student_id": "1",
            "title": "Test Assignment IPSE PDF",
            "class_id": "2"
        }

        files = {
            "file": (f"{base_filename}.pdf", pdf_file, "application/pdf")
        }

        response = client.post("/assignments/upload", data=data, files=files)

        assert response.status_code == 200, f"PDF upload failed: {response.text}"

        response_json = response.json()
        assert "id" in response_json
        assert response_json["title"] == data["title"]
        assert response_json["blob_url"].startswith("https://")
        assert "content" in response_json and len(response_json["content"].strip()) > 0

    # Test DOCX upload
    with open(docx_path, "rb") as docx_file:
        data["title"] = "Test Assignment IPSE DOCX"  # Change title to differentiate
        files = {
            "file": (f"{base_filename}.docx", docx_file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }

        response = client.post("/assignments/upload", data=data, files=files)

        assert response.status_code == 200, f"DOCX upload failed: {response.text}"

        response_json = response.json()
        assert "id" in response_json
        assert response_json["title"] == data["title"]
        assert response_json["blob_url"].startswith("https://")
        assert "content" in response_json and len(response_json["content"].strip()) > 0
