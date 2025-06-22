import uuid
from fastapi.testclient import TestClient
from application.app import application  # adjust if your app is named differently

client = TestClient(application)

def test_get_classes_for_student():
    # Step 1: Create a new student with unique emails using UUID
    student_response = client.post("/students/", json={
        "first_name": "Test",
        "last_name": "Student",
        "email": f"{uuid.uuid4()}@example.com",
        "gt_email": f"{uuid.uuid4()}@gatech.edu",
        "year_id": 1,
        "reading_level": 1,
        "writing_level": 1,
        "password_hash": "fakehashedpw123",
        "profile_picture_url": None
    })
    print(student_response.json())  
    assert student_response.status_code == 201
    student_id = student_response.json()["id"]

    # Step 2: Create a new class
    class_response = client.post("/classes/", json={
        "name": "Test Class",
        "type": "Inclusive",
        "term": "Spring2024"
    })
    print(class_response.json())  
    assert class_response.status_code == 201
    class_id = class_response.json()["id"]

    # Step 3: Associate the student with the class
    associate_response = client.post(f"/students/{student_id}/classes", json={
        "class_id": class_id,
        "learning_goal": "Understand basic concepts"
    })
    assert associate_response.status_code == 201

    # Step 4: Retrieve classes for the student
    get_response = client.get(f"/students/{student_id}/classes")
    assert get_response.status_code == 200

    classes = get_response.json()
    assert isinstance(classes, list)
    assert len(classes) >= 1
    assert any(cls["id"] == class_id for cls in classes)
