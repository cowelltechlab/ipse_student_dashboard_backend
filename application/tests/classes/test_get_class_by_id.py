import subprocess
import pytest
from fastapi.testclient import TestClient
from application.app import application

client = TestClient(application)

def test_get_class_by_id():
    # Assuming at least 1 class with id=1 exists
    response = client.get("/classes/2")
    assert response.status_code == 200
    class_data = response.json()
    assert "id" in class_data
    assert "name" in class_data
    assert "type" in class_data
