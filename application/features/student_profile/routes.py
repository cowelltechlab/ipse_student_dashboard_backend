from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status, Depends
from typing import List, Optional

from requests import Session
from application.features.student_profile.crud import (
    create_or_update_profile, get_complete_profile, get_user_id_from_student, update_student_profile, update_user_profile_picture
)
from application.features.student_profile.schemas import (
    StudentProfileCreate, StudentProfileResponse, StudentProfileUpdate
)
from application.features.auth.permissions import require_user_access
from application.utils.blob_upload import upload_profile_picture

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


@router.post("/profile-picture/{student_id}")
async def upsert_profile_picture(
    student_id: int,
    profile_picture: Optional[UploadFile] = File(None),
    existing_blob_url: Optional[str] = Form(None),
    _user=Depends(require_user_access),
):
    user_id = get_user_id_from_student(student_id)

    if profile_picture:
        try:
            blob_url = await upload_profile_picture(user_id, profile_picture)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif existing_blob_url:
        blob_url = existing_blob_url
    else:
        raise HTTPException(status_code=400, detail="No profile picture provided")

    update_user_profile_picture(user_id, blob_url)

    return {
        "success": True,
        "user_id": user_id,
        "profile_picture_url": blob_url
    }


@router.get("/{student_id}", response_model=StudentProfileResponse)
def get_student_profile(
    student_id: int,
    _user=Depends(require_user_access),
):
    profile = get_complete_profile(student_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile



@router.put("/{user_id}", status_code=status.HTTP_200_OK)
def partial_update_student_profile(
    user_id: int,
    payload: StudentProfileUpdate,
    _user=Depends(require_user_access)
):
    return update_student_profile(user_id, payload)


# @router.delete("/{student_id}")
# def delete_student_profile(
#     student_id: int,
#     user_data: dict = Depends(require_user_access)
# ):
#     result = delete_profile(student_id)
#     if not result:
#         raise HTTPException(status_code=404, detail="Profile not found")
#     return {"message": "Profile deleted successfully"}
