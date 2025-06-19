import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from application.app import application  # adjust import to your FastAPI app entrypoint

client = TestClient(application)

@pytest.fixture
def sample_profile():
    return {
        "student_id": 42,
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

@patch("application.features.studentProfile.crud.get_profile")
def test_get_student_profile(mock_get_profile, sample_profile):
    mock_get_profile.return_value = sample_profile

    response = client.get("/profile/42")
    assert response.status_code == 200

    data = response.json()
    assert data["student_id"] == 42
    assert data["id"] == "42"
    assert "strengths" in data
    assert "challenges" in data
    assert data["short_term_goals"] == "Complete all assignments on time"
