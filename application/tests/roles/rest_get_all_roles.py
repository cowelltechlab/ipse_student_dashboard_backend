from fastapi.testclient import TestClient
from application.app import application

client = TestClient(application)

def test_get_roles():
    with open("tests/created_role_id.txt") as f:
        created_role_id = int(f.read().strip())

    response = client.get("/roles")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(role["id"] == created_role_id for role in data)
