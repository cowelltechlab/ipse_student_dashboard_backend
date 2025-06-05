import pytest
from fastapi.testclient import TestClient
from application.app import application
from application.database.mssql_connection import get_sql_db_connection

client = TestClient(application)

def delete_class_by_name(name: str):
    """Cleanup utility: delete any class with the given name."""
    conn = get_sql_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Classes WHERE name = ?", (name,))
    conn.commit()
    cursor.close()
    conn.close()

def test_create_delete_and_verify_class():
    # Clean up if class already exists
    delete_class_by_name("DeleteTestClass")

    # Step 1: Create a class
    new_class = {
        "name": "DeleteTestClass",
        "type": "IPSE"
    }
    create_response = client.post("/classes/", json=new_class)
    assert create_response.status_code == 201

    created_class = create_response.json()
    class_id = created_class["id"]
    assert created_class["name"] == "DeleteTestClass"

    # Step 2: Delete the class
    delete_response = client.delete(f"/classes/{class_id}")
    assert delete_response.status_code == 200
    assert f"{class_id}" in delete_response.json()["message"]

    # Step 3: Attempt to fetch the deleted class (expect 404)
    fetch_response = client.get(f"/classes/{class_id}")
    assert fetch_response.status_code == 404
