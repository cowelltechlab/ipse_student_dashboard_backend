

from fastapi import APIRouter, Depends, Query, status, HTTPException
from typing import List, Optional, Dict
from application.features.auth.auth_helpers import hash_password
from application.features.auth.crud import create_user, get_all_role_ids, get_user_by_email, get_user_role_names
from application.features.auth.permissions import require_admin_access, require_teacher_access
from application.features.auth.schemas import RegisterUserRequest, UserResponse
from application.features.users.crud import complete_user_invite, create_invited_user, get_all_users_with_roles

import re

from application.features.users.schemas import CompleteInviteRequest, InviteUserRequest

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
            role_ids=user.get("role_ids")
        )
        for user in users
    ]




# @router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
# async def register_new_user(
#     request_data: RegisterUserRequest,
#     user_data: dict = Depends(require_admin_access)
# ):
#     """
#     Add a user to the database. Must include identifying information and a 
#     password. All information is expected to be inputted by an administrator. 
#     The password is hashed before being added to the database. Roles associated
#     with the new user must be passed in as IDs.
#     """
#     # Ensure role_ids all exist in database
#     all_roles = set(get_all_role_ids())
#     if not set(request_data.role_ids).issubset(all_roles):
#         bad_ids = set(request_data.role_ids).difference(all_roles)
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Invalid role IDs: {bad_ids}"
#         )

#     # Check email formatting 
#     EMAIL_REGEX = re.compile(
#         r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
#     )

#     if not request_data.school_email.endswith(".edu") or \
#         not EMAIL_REGEX.fullmatch(request_data.school_email):
#         raise HTTPException(
#             status_code=400,
#             detail=f"Invalid School email format."
#         )

#     if request_data.google_email and \
#         (not request_data.google_email.endswith("@gmail.com") or \
#          not EMAIL_REGEX.fullmatch(request_data.google_email)):
#         raise HTTPException(
#             status_code=400,
#             detail=f"Invalid Google email format."
#         )
    
#     # Hash password
#     hashed_password = hash_password(request_data.password)

#     # Create user and retrieve ID
#     new_user = create_user(
#         request_data.first_name,
#         request_data.last_name,
#         request_data.school_email,
#         hashed_password,
#         request_data.role_ids,
#         request_data.google_email
#     )
    
#     if not new_user:
#         raise HTTPException(
#             status_code=400,
#             detail="Error creating new user"
#         )
    
#     return UserResponse(
#         id=new_user["id"],
#         email=new_user["email"],
#         school_email=new_user["school_email"],
#         first_name=new_user["first_name"],
#         last_name=new_user["last_name"],
#         roles=get_user_role_names(new_user["id"]),
#         role_ids=new_user["role_ids"] if "role_ids" in new_user else None
#     )


router = APIRouter()

@router.post("/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    request_data: InviteUserRequest,
    admin_data: dict = Depends(require_admin_access)
):
    """
    Admin invites a new user to complete their account setup.
    """
    email = request_data.google_email or request_data.school_email

    if get_user_by_email(email):
        raise HTTPException(409, "A user with this email already exists.")

    result = create_invited_user(email, request_data.school_email, request_data.role_ids)

    if not result or "token" not in result:
        raise HTTPException(500, "Failed to create invited user")

    token = result["token"]
    invite_url = f"https://your-frontend.com/complete-invite?token={token}"

    send_email(
        to=email,
        subject="You're Invited!",
        body=f"Welcome! Complete your setup here: {invite_url}"
    )

    return {"message": f"Invite sent to {email}"}


@router.post("/complete-invite", status_code=200)
async def complete_invite(data: CompleteInviteRequest):
    """
    Endpoint for invited user to complete account setup.
    """
    hashed_pw = hash_password(data.password)

    success = complete_user_invite(
        token=data.token,
        first_name=data.first_name,
        last_name=data.last_name,
        password_hash=hashed_pw,
        profile_picture_url=data.profile_picture_url
    )

    if not success:
        raise HTTPException(400, "Invalid or expired token")

    return {"message": "Account setup complete"}
