import pytest
from application.features.students.crud import fetch_all_students_with_names


def test_fetch_all_students_with_names_returns_data():
    # Call the function
    result = fetch_all_students_with_names()
    
    # Check it's a list
    assert isinstance(result, list)
    
    # If there is at least one record, check keys
    if result:
        student = result[0]
        assert "id" in student
        assert "first_name" in student
        assert "last_name" in student
        assert "reading_level" in student
        assert "writing_level" in student
