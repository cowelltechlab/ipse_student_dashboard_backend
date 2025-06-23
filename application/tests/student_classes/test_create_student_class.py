from fastapi.testclient import TestClient
from application.app import application # or wherever your FastAPI app is defined
import uuid

client = TestClient(application)

def test_assign_class_to_student():
    # Step 1: Create a student
    random_email = f"{uuid.uuid4()}@example.com"
    student_data = {
        "first_name": "Test",
        "last_name": "Student",
        "email": random_email,
        "gt_email": f"{uuid.uuid4()}@gatech.edu",
        "year_id": 1,
        "reading_level": 1,
        "writing_level": 1,
        "password_hash": "fakehashedpw123",
        "profile_picture_url": None
    }
    student_response = client.post("/students/", json=student_data)
    print(student_response.json()) 

    assert student_response.status_code == 201
    student_id = student_response.json()["id"]

    # Step 2: Create a class
    class_data = {
        "name": "Physics 101",
        "type": "IPSE",
        "term": "Fall2024"
    }
    class_response = client.post("/classes/", json=class_data)
    assert class_response.status_code == 201
    class_id = class_response.json()["id"]

    # Step 3: Assign class to student
    association_data = {
        "class_id": class_id,
        "learning_goal": "Understand basic physics"
    }
    assign_response = client.post(f"/students/{student_id}/classes", json=association_data)

    # Step 4: Verify assignment worked
    assert assign_response.status_code == 201
    assert assign_response.json() == {"message": "Class successfully assigned to student."}
