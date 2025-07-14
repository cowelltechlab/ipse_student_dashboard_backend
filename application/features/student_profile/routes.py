from fastapi import APIRouter, HTTPException, status, Body, Depends
from typing import List
from application.features.student_profile.crud import (
    create_or_update_profile, get_complete_profile, get_profile, update_profile, delete_profile, update_student_profile
)
from application.features.student_profile.schemas import (
    StudentProfileCreate, StudentProfileResponse, StudentProfileUpdate
)
from application.features.auth.permissions import require_user_access

router = APIRouter()

@router.post("/{user_id}", status_code=status.HTTP_201_CREATED)
def upsert_student_profile(
    user_id: int,
    payload: StudentProfileCreate,
    _user=Depends(require_user_access),  
):
    if user_id != payload.user_id:
        raise HTTPException(
            status_code=400, detail="user_id mismatch between path and body"
        )
    return create_or_update_profile(payload)


@router.get("/{student_id}", response_model=StudentProfileResponse)
def get_student_profile(
    student_id: int,
    _user=Depends(require_user_access),
):
    profile = get_complete_profile(student_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile



@router.put("/{student_id}", response_model=StudentProfileResponse)
def patch_student_profile(
    student_id: int,
    payload: StudentProfileUpdate,
    _=Depends(require_user_access),
):
    updated = update_student_profile(student_id, payload)
    return updated



# @router.delete("/{student_id}")
# def delete_student_profile(
#     student_id: int,
#     user_data: dict = Depends(require_user_access)
# ):
#     result = delete_profile(student_id)
#     if not result:
#         raise HTTPException(status_code=404, detail="Profile not found")
#     return {"message": "Profile deleted successfully"}
