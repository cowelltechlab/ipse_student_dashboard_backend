from fastapi.testclient import TestClient
from application.app import application

client = TestClient(application)

test_role = {
    "role_name": "Test Role",
    "description": "A role used for testing"
}

def test_create_role():
    response = client.post("/roles", json=test_role)
    assert response.status_code == 200  # or 201 if set that way
    data = response.json()
    assert "id" in data
    assert data["role_name"] == test_role["role_name"]
    assert data["description"] == test_role["description"]

    # Save for later use
    with open("tests/created_role_id.txt", "w") as f:
        f.write(str(data["id"]))
