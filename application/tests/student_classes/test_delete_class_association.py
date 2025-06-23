import uuid
from fastapi.testclient import TestClient
from application.app import application

client = TestClient(application)

def test_delete_student_class_association():
    # Create a student with unique emails to avoid conflicts
    random_email = f"{uuid.uuid4()}@example.com"
    random_gt_email = f"{uuid.uuid4()}@gatech.edu"
    student_data = {
        "first_name": "Test",
        "last_name": "Student",
        "email": random_email,
        "gt_email": random_gt_email,
        "year_id": 1,
        "reading_level": 1,
        "writing_level": 1,
        "password_hash": "fakehashedpw123",
        "profile_picture_url": None
    }
    student_response = client.post("/students/", json=student_data)
    assert student_response.status_code == 201
    student_id = student_response.json()["id"]

    # Create a class
    class_data = {
        "name": "Test Class",
        "type": "Inclusive",
        "term": "Spring2024"
    }
    class_response = client.post("/classes/", json=class_data)
    assert class_response.status_code == 201
    class_id = class_response.json()["id"]

    # Associate student with class
    associate_data = {
        "class_id": class_id,
        "learning_goal": "Understand basic concepts"
    }
    associate_response = client.post(f"/students/{student_id}/classes", json=associate_data)
    assert associate_response.status_code == 201

    # Now delete the association
    delete_response = client.delete(f"/students/{student_id}/classes/{class_id}")
    assert delete_response.status_code == 204

    # Verify deletion by fetching student's classes
    get_response = client.get(f"/students/{student_id}/classes")
    assert get_response.status_code == 200
    classes = get_response.json()

    # The deleted class should no longer be associated
    assert all(c["id"] != class_id for c in classes)
