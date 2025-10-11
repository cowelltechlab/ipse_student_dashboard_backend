import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, logger, status, HTTPException
from typing import List, Optional, Dict, Set
from application.database.mssql_crud_helpers import fetch_all
from application.features.auth.auth_helpers import hash_password
from application.features.auth.crud import get_user_by_email
from application.features.auth.permissions import _expand_roles, require_admin_access, require_peer_tutor_access, require_teacher_access
from application.features.auth.schemas import StudentProfile, UserResponse
from application.features.roles.crud import get_multiple_role_names_from_ids
from application.features.users.crud.user_queries import get_all_users_with_roles_allowed, get_user_with_roles_by_id, update_user_email
from application.features.users.crud.user_invitations import complete_user_invite, create_invited_user, get_user_id_from_invite_token
from application.features.users.crud.user_management import delete_user_db

from application.features.users.schemas import DefaultProfilePicture, InviteUserRequest, UserEmailUpdateData, UserDetailsResponse
from application.services.email_sender import send_invite_email

from collections import defaultdict
from application.features.tutor_students.crud import get_all_tutor_students

load_dotenv()

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def get_users(
    role_id: Optional[int] = Query(None), 
    user_data: Dict = Depends(require_peer_tutor_access)
):
    """
    Retrieves users with their roles, but filters to only those whose roles are
    at/below the caller’s role hierarchy. Optional role_id filter is allowed
    only if it maps to a role within the caller’s allowed set.
    """

    caller_roles = user_data.get("role_names")
    if not isinstance(caller_roles, list) or not caller_roles:
        raise HTTPException(status_code=403, detail="Role information missing from token.")

    # Expand roles per hierarchy (e.g., 'Peer Tutor' -> {'Peer Tutor','Student'})
    allowed_role_names: Set[str] = _expand_roles(set(caller_roles))

   
    # If role_id provided, ensure it resolves to an allowed role
    if role_id is not None:
        names = get_multiple_role_names_from_ids([role_id]) or []
        if not names:
            raise HTTPException(status_code=400, detail=f"Invalid role_id: {role_id}")
        if names[0] not in allowed_role_names:
            raise HTTPException(
                status_code=403,
                detail=f"You cannot filter by role '{names[0]}'.",
            )

    # Check if the caller is a Peer Tutor. If so, only show their assigned students
    tutor_user_id = None
    if "Peer Tutor" in caller_roles:
        tutor_user_id = user_data.get("user_id")
    
    users = get_all_users_with_roles_allowed(
        allowed_role_names=allowed_role_names,
        role_id=role_id,
        tutor_user_id=tutor_user_id
    )

    # Build a map of tutor_id -> [{ student_id, code, name }]
    tutored_map = defaultdict(list)
    try:
        flat = get_all_tutor_students()
        for r in flat:
            # r has: tutor_id, student_id, student_year, etc.
            year_name = r.get("student_year")
            tutored_map[r["tutor_id"]].append(
                {
                    "student_id": r["student_id"],
                    "name": year_name,
                }
            )
    except Exception as e:
        logger.error(f"Error building tutored_map: {e}")
    

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
            invite_url=user.get("invite_url"),
            
            student_profile = StudentProfile(
                student_id = user["student_id"],
                year_name =  user["year_name"]
            ) if "student_id" in user and "year_name" in user else None,
            tutored_students = tutored_map.get(user["id"], [])
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
    admin_data: dict = Depends(require_peer_tutor_access)
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


@router.patch("/{user_id}/email", response_model=UserDetailsResponse)
async def update_user_email_route(
    user_id: int,
    data: UserEmailUpdateData,
    user_data: Dict = Depends(require_admin_access)
):
    """Update a user's email."""
    if data.email is None and data.gt_email is None:
        raise HTTPException(status_code=400, detail="At least one email must be provided")

    updated_user = update_user_email(user_id, data.email, data.gt_email)
    return updated_user