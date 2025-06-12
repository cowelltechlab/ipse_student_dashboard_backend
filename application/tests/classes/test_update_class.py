import pytest
from fastapi.testclient import TestClient
from application.app import application
from application.database.mssql_connection import get_sql_db_connection

client = TestClient(application)

def delete_class_by_name(name: str):
    """Utility to delete a class by name (cleanup helper)."""
    conn = get_sql_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Classes WHERE name = ?", (name,))
    conn.commit()
    cursor.close()
    conn.close()


def test_create_and_update_class():
    # Cleanup before and after test
    delete_class_by_name("Test Class")

    # Step 1: Create a class
    new_class = {
        "name": "Test Class",
        "type": "IPSE"
    }
    create_response = client.post("/classes/", json=new_class)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == new_class["name"]
    assert created["type"] == new_class["type"]

    class_id = created["id"]

    # Step 2: Update the class
    update_data = {
        "name": "Test2"
    }
    update_response = client.put(f"/classes/{class_id}", json=update_data)
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == class_id
    assert updated["name"] == "Test2"  # name shouldn't change
    assert updated["type"] == new_class["type"]

    # Cleanup
    delete_class_by_name("Test Class")
