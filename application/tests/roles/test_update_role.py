from fastapi.testclient import TestClient
from application.app import application

client = TestClient(application)

updated_role = {
    "role_name": "Updated Role",
    "description": "Updated description"
}

def test_update_role():
    with open("tests/created_role_id.txt") as f:
        created_role_id = int(f.read().strip())

    response = client.put(f"/roles/{created_role_id}", json=updated_role)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_role_id
    assert data["role_name"] == updated_role["role_name"]
    assert data["description"] == updated_role["description"]
