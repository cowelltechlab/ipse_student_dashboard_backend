import pytest
from fastapi.testclient import TestClient
from application.app import application

client = TestClient(application)

def test_create_class():
    new_class = {
        "name": "Science 202",
        "type": "Inclusive",
        "term": "Spring2024"
    }

    response = client.post("/classes/", json=new_class)
    assert response.status_code == 201

    created_class = response.json()
    assert "id" in created_class
    assert created_class["name"] == new_class["name"]
    assert created_class["type"] == new_class["type"]
    assert created_class["term"] == new_class["term"]
