import pytest
import random
from fastapi.testclient import TestClient
from unittest.mock import patch

from application.app import application

client = TestClient(application)

@pytest.fixture
def mock_create_profile():
    with patch("application.features.studentProfile.crud.container.create_item") as mock_create:
        yield mock_create

def test_create_student_profile(mock_create_profile):
    random_student_id = random.randint(1, 100)
    sample_profile = {
        "student_id": random_student_id,
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
    mock_create_profile.return_value = {**sample_profile, "id": "random-id-123"}

    response = client.post("/profile/", json=sample_profile)
    assert response.status_code == 201
    data = response.json()
    assert data["student_id"] == random_student_id
    assert data["id"] == "random-id-123"
    assert "strengths" in data
    mock_create_profile.assert_called_once()
