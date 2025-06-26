import pytest
from fastapi.testclient import TestClient
from application.app import application  # adjust if your app is elsewhere

client = TestClient(application)

@pytest.fixture
def create_profile():
    import random
    student_id = random.randint(1, 100)
    profile_data = {
        "student_id": student_id,
        "strengths": ["Curious"],
        "challenges": ["Procrastination"],
        "short_term_goals": "Finish homework",
        "long_term_goals": "Become self-motivated",
        "best_ways_to_help": ["Reminders", "Visual aids"],
        "summaries": {
            "goals_short": "Needs time management"
        }
    }
    response = client.post("/profile/", json=profile_data)
    assert response.status_code == 201
    return response.json()

def test_delete_profile(create_profile):
    student_id = create_profile["student_id"]

    # Perform the DELETE request
    response = client.delete(f"/profile/{student_id}")
    assert response.status_code == 200  # No Content

    # Optional: Verify it's deleted
    assert response.status_code == 200
    assert response.json()["message"] == "Profile deleted successfully"
