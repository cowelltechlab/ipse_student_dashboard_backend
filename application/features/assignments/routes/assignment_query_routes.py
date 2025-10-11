"""
Assignment query routes - GET operations for fetching assignments
"""
from typing import List
from fastapi import Depends, HTTPException, APIRouter

from application.features.assignments.schemas import (
    AssignmentListResponse,
    AssignmentDetailResponse,
    AssignmentTypeListResponse,
)
from application.features.assignments.crud import (
    get_all_assignment_types,
    get_all_assignments_by_student_id,
    get_assignment_by_id,
    get_all_assignments,
)
from application.features.auth.permissions import require_user_access

router = APIRouter()


@router.get("/", response_model=List[AssignmentListResponse])
def fetch_assignments(
    user_data = Depends(require_user_access)
):
    """Retrieve all assignments"""
    # If user is a Peer Tutor, filter assignments to only those of their assigned students
    caller_roles = user_data.get("role_names")

    tutor_user_id = None
    if "Peer Tutor" in caller_roles:
        tutor_user_id = user_data.get("user_id")

    assignments = get_all_assignments(tutor_user_id=tutor_user_id)

    return assignments


@router.get("/id/{assignment_id}", response_model=AssignmentDetailResponse)
def fetch_assignment_by_id(
    assignment_id: int,
    _user = Depends(require_user_access)
):
    """Retrieve a single assignment by ID"""
    raw_data = get_assignment_by_id(assignment_id)
    if not raw_data:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment_response = {
        "assignment_id": raw_data["assignment_id"],
        "title": raw_data["assignment_title"],
        "content": raw_data["assignment_content"],
        "date_created": raw_data["assignment_date_created"],
        "blob_url": raw_data.get("assignment_blob_url"),
        "source_format": raw_data.get("assignment_source_format"),
        "html_content": raw_data.get("assignment_html_content"),
        "assignment_type": raw_data.get("assignment_type"),
        "assignment_type_id": raw_data.get("assignment_type_id"),

        # Nested Student
        "student": {
            "id": raw_data["student_internal_id"],
            "first_name": raw_data["student_first_name"],
            "last_name": raw_data["student_last_name"]
        },

        # Nested Class Info
        "class_info": {
            "id": raw_data.get("class_id"),
            "name": raw_data.get("class_name"),
            "course_code": raw_data.get("class_course_code")
        } if raw_data.get("class_id") else None,

        # NoSQL metadata
        "finalized": raw_data.get("finalized"),
        "final_version_id": raw_data.get("final_version_id"),
        "rating_status": raw_data.get("rating_status"),
        "date_modified": raw_data.get("date_modified"),
        "versions": raw_data.get("versions", []),
    }

    return assignment_response


@router.get(path="/types", response_model=List[AssignmentTypeListResponse])
def fetch_assignment_types(
    _user = Depends(require_user_access)
):
    """Retrieve all assignment types"""
    return get_all_assignment_types()


@router.get("/{student_id}", response_model=List[AssignmentListResponse])
def fetch_assignments_by_student(
    student_id: int,
    _user = Depends(require_user_access)
):
    """Retrieve all assignments by student ID"""
    return get_all_assignments_by_student_id(student_id)
