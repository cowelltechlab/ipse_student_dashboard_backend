import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status, HTTPException
from typing import List, Optional, Dict
from application.database.mssql_crud_helpers import fetch_all
from application.features.auth.auth_helpers import hash_password
from application.features.auth.crud import get_user_by_email
from application.features.auth.permissions import require_admin_access, require_teacher_access
from application.features.auth.schemas import StudentProfile, UserResponse
from application.features.users.crud import complete_user_invite, create_invited_user, delete_user_db, get_all_users_with_roles, get_user_id_from_invite_token, get_user_with_roles_by_id

from application.features.users.schemas import DefaultProfilePicture, InviteUserRequest
from application.services.email_sender import send_invite_email

load_dotenv()

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def get_users(
    role_id: Optional[int] = Query(None), 
    user_data: Dict = Depends(require_teacher_access)
):
    """
    Retrieves all users with their roles. Optional role_id filter.
    """
    users = get_all_users_with_roles(role_id)

    

    return [
        UserResponse(
            id=user["id"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            email=user["email"],
            school_email=user["gt_email"],
            roles=user.get("roles"),
            role_ids=user.get("role_ids"),
            profile_picture_url=user.get("profile_picture_url"),
            is_active=user.get("is_active", True),
            profile_tag=user.get("profile_tag"),
            
            student_profile = StudentProfile(
                student_id = user["student_id"],
                year_name =  user["year_name"]
            ) if "student_id" in user and "year_name" in user else None
        )
        for user in users
    ]

@router.get("/profile-picture-defaults", response_model=List[DefaultProfilePicture])
async def get_profile_picture_defaults():

   default_profile_pictures = fetch_all("ProfilePictureDefaults")

   return [
       DefaultProfilePicture(id=p["id"], url=p["profile_picture_url"])
       for p in default_profile_pictures
   ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: int, user_data: dict = Depends(require_teacher_access)):
    """
    Retrieves a user by ID
    """
    user = get_user_with_roles_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user["id"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        email=user["email"],
        school_email=user["gt_email"],
        roles=user.get("roles"),
        role_ids=user.get("role_ids"),
        profile_picture_url=user.get("profile_picture_url"),
        is_active=user.get("is_active", True),
        profile_tag=user.get("profile_tag"),
        student_profile=StudentProfile(
            student_id=user["student_id"],
            year_name=user["year_name"]
        ) if "student_id" in user and "year_name" in user else None
    )


@router.post("/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    request_data: InviteUserRequest,
    admin_data: dict = Depends(require_admin_access)
):
    """
    Admin invites a new user to complete their account setup.
    """
    email = request_data.google_email

    if get_user_by_email(email):
        raise HTTPException(409, "A user with this email already exists.")

    result = create_invited_user(email, request_data.school_email, request_data.role_ids, request_data.student_type)

    if not result or "token" not in result:
        raise HTTPException(500, "Failed to create invited user")

    token = result["token"]
    invite_url = f"{os.getenv('FRONTEND_BASE_URL')}/complete-invite?token={token}"

    send_invite_email(
        to_email=email,
        invite_url=invite_url
    )

    return {"message": f"Invite sent to {email}"}


@router.post("/complete-invite", status_code=200)
async def complete_invite(
    token: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    password: str = Form(...),
    profile_picture: Optional[UploadFile] = File(None),
    existing_blob_url: Optional[str] = Form(None),
):
    from application.utils.blob_upload import upload_profile_picture
    hashed_pw = hash_password(password)

    user_id = get_user_id_from_invite_token(token)
    if not user_id:
        raise HTTPException(400, "Invalid or expired token")

    # Handle profile picture upload or use provided URL
    if profile_picture:
        blob_url = await upload_profile_picture(user_id, profile_picture)
    elif existing_blob_url:
        blob_url = existing_blob_url
    else:
        blob_url = None 

    success = complete_user_invite(
        token=token,
        first_name=first_name,
        last_name=last_name,
        password_hash=hashed_pw,
        profile_picture_url=blob_url,
    )

    if not success:
        raise HTTPException(400, "Failed to complete invite")

    return {"message": "Account setup complete"}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    user_data: dict = Depends(require_admin_access)
):
    """
    Deletes a user by ID. Only accessible to admins.
    """
    
    result = delete_user_db(user_id)

    if not result:
        raise HTTPException(
            status_code=404, 
            detail=f"User with ID {user_id} not found."
        )
    
    return {"message": f"User with ID {user_id} deleted successfully."}


