from fastapi.testclient import TestClient
from application.app import application 

client = TestClient(application)

def test_get_students_by_year_3():
    response = client.get("/students/", params={"year_id": 3})
    assert response.status_code == 200
    
    students = response.json()
    assert isinstance(students, list)
    assert len(students) == 3  # You expect exactly 3 students with year_id=3
    
    # Optional: check the year_id in returned students
    for student in students:
        assert student["year_id"] == 3
