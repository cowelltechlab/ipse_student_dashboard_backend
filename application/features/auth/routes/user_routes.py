from typing import Dict
from fastapi import HTTPException, APIRouter, Depends
from application.features.auth.schemas import StudentProfile, UserResponse
from application.features.auth.permissions import require_user_access
from application.features.users.crud.user_queries import get_user_with_roles_by_id

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_data: Dict = Depends(require_user_access)
) -> UserResponse:
    """
    Retrieve identifying and access data for current user. 
    """
    user_id = user_data.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401, 
            detail="Invalid token payload: missing user_id."
        )
    
    user = get_user_with_roles_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=404, 
            detail="User found in token but not in database"
        )

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
        invite_url=user.get("invite_url"),
        
        student_profile = StudentProfile(
            student_id = user["student_id"],
            year_name =  user["year_name"]
        ) if "student_id" in user and "year_name" in user else None
    )