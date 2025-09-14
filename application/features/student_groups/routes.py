from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict

from application.features.auth.permissions import require_admin_access, require_peer_tutor_access, require_teacher_access
from application.features.student_groups.crud import get_students_with_details, update_student_group_type, update_student_ppt_urls
from application.features.student_groups.schemas import StudentDetailsResponse, StudentGroupTypeUpdate, StudentPptUrlsUpdate

router = APIRouter()


@router.get("/", response_model=List[StudentDetailsResponse])
async def get_students(
    user_data: Dict = Depends(require_admin_access)
):
    """
    Retrieve students with their details (first_name, last_name, profile_picture_url, group_type, ppt_embed_url, ppt_edit_url).
    If user is a Peer Tutor, filter to only their assigned students.
    """
    caller_roles = user_data.get("role_names", [])
    tutor_user_id = None

    if "Peer Tutor" in caller_roles:
        tutor_user_id = user_data.get("user_id")

    students = get_students_with_details(tutor_user_id=tutor_user_id)
    return students


@router.patch("/{student_id}/group-type", response_model=StudentDetailsResponse)
async def update_student_group_type_route(
    student_id: int,
    data: StudentGroupTypeUpdate,
    user_data: Dict = Depends(require_admin_access)
):
    """Update a student's group type."""
    if data.group_type is None:
        raise HTTPException(status_code=400, detail="group_type is required")

    updated_student = update_student_group_type(student_id, data.group_type)
    return updated_student


@router.patch("/{student_id}/ppt-urls", response_model=StudentDetailsResponse)
async def update_student_ppt_urls_route(
    student_id: int,
    data: StudentPptUrlsUpdate,
    user_data: Dict = Depends(require_admin_access)
):
    """Update a student's PowerPoint embed and/or edit URLs."""
    if data.ppt_embed_url is None and data.ppt_edit_url is None:
        raise HTTPException(status_code=400, detail="At least one URL must be provided")

    updated_student = update_student_ppt_urls(
        student_id,
        ppt_embed_url=data.ppt_embed_url,
        ppt_edit_url=data.ppt_edit_url
    )
    return updated_student
