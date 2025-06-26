import random
import pytest
from fastapi.testclient import TestClient
from application.app import application  # or wherever your FastAPI app instance is

client = TestClient(application)

@pytest.fixture
def create_profile():
    # Setup: create a profile first to update later
    profile_data = {
        "student_id": random.randint(1, 100) ,
        "strengths": ["Organized", "Good at writing"],
        "challenges": ["Hard to focus", "Deadlines"],
        "short_term_goals": "Complete all assignments on time",
        "long_term_goals": "Improve writing skills significantly",
        "best_ways_to_help": ["Step-by-step", "Audio response"],
        "summaries": {
            "strength_short": "Well-organized and expressive",
            "goals_short": "Needs help with focus and deadlines"
        }
    }
    response = client.post("/profile/", json=profile_data)
    assert response.status_code == 201
    return response.json()

def test_partial_update_profile(create_profile):
    student_id = create_profile["student_id"]

    update_data = {
        "short_term_goals": "Finish homework earlier than due date",
        "summaries": {"goals_short": "Focus on time management"}
    }

    response = client.put(f"/profile/{student_id}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["student_id"] == student_id
    assert data["short_term_goals"] == "Finish homework earlier than due date"
    assert data["summaries"]["goals_short"] == "Focus on time management"
