from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile, status, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
import io

from requests import Session
from application.features.student_profile.crud import (
    create_or_update_profile, export_profiles_to_csv, export_profiles_to_json, get_all_complete_profiles, get_complete_profile, get_prefill_profile, get_user_id_from_student, handle_post_ppt_urls, update_student_profile, update_user_profile_picture
)
from application.features.student_profile.schemas import (
    PPtUrlsPayload, StudentProfileCreate, StudentProfilePrefillResponse, StudentProfileResponse, StudentProfileUpdate
)
from application.features.auth.permissions import require_admin_access, require_user_access
from application.utils.blob_upload import upload_profile_picture

router = APIRouter()

@router.get("/", response_model=List[StudentProfileResponse])
def get_student_profiles(
    _user=Depends(require_admin_access),
):
    all_profiles = get_all_complete_profiles()
    return all_profiles


@router.get("/export")
def export_student_profiles(
    format: str = Query(default="csv", regex="^(csv|json)$"),
    # _user=Depends(require_admin_access),
):
    """
    Export all student profiles in the specified format (csv or json).
    Returns a downloadable file.
    """
    if format.lower() == "csv":
        content = export_profiles_to_csv()
        media_type = "text/csv"
        filename = "student_profiles.csv"
    elif format.lower() == "json":
        content = export_profiles_to_json()
        media_type = "application/json"
        filename = "student_profiles.json"
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'csv' or 'json'.")

    if not content:
        raise HTTPException(status_code=404, detail="No student profiles found to export.")

    # Create file-like object from string content
    file_obj = io.StringIO(content)

    return StreamingResponse(
        io.BytesIO(content.encode('utf-8')),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

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



@router.post("/achievements-urls/{student_id}", response_model=str)
def post_embed_url(
    student_id: int,
    payload: PPtUrlsPayload,
    _user=Depends(require_user_access),
):
    return handle_post_ppt_urls(student_id, payload.embed_url, payload.edit_url)

# For pre-filling student profile in register form, in case of existing partial profile
@router.get("/by-user/{user_id}", response_model=StudentProfilePrefillResponse)
def get_student_profile_by_user_id(
    user_id: int,
    _user=Depends(require_user_access),
):
    profile = get_prefill_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile



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
