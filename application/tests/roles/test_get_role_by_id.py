from fastapi.testclient import TestClient
from application.app import application

client = TestClient(application)

def test_get_role_by_id():
    with open("tests/created_role_id.txt") as f:
        created_role_id = int(f.read().strip())

    response = client.get(f"/roles/{created_role_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_role_id
