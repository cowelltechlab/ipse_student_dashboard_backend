from fastapi.testclient import TestClient
from application.app import application

client = TestClient(application)

def test_delete_role():
    with open("tests/created_role_id.txt") as f:
        created_role_id = int(f.read().strip())

    response = client.delete(f"/roles/{created_role_id}")
    assert response.status_code == 200
    assert response.json()["detail"] == "Role deleted successfully"
