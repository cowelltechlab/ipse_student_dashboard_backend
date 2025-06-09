import subprocess
import pytest
from fastapi.testclient import TestClient
from application.app import application

client = TestClient(application)


def test_get_classes_endpoint():
    response = client.get("/classes/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        class_item = data[0]
        assert "id" in class_item
        assert "name" in class_item
        assert "type" in class_item


def test_curl_get_classes():
    result = subprocess.run(
        ["curl", "-s", "-X", "GET", "http://localhost:8000/classes/"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "name" in result.stdout  # crude check if classes appear
