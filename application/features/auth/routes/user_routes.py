from typing import Dict
from fastapi import HTTPException, APIRouter, Depends
from application.features.auth.crud import get_user_by_email
from application.features.auth.schemas import UserResponse
from application.features.auth.permissions import require_user_access

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_data: Dict = Depends(require_user_access)
) -> UserResponse:
    """
    Retrieve identifying and access data for current user. 
    """
    email = user_data.get("email")
    id = user_data.get("user_id")
    roles = user_data.get("role_names")
    role_ids = user_data.get("role_ids")
    profile_picture_url = user_data.get("profile_picture_url")

    if not email or not id or not roles:
        raise HTTPException(
            status_code=401, 
            detail="Invalid token payload: missing email, user_id, or roles."
        )
    
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=404, 
            detail="User found in token but not in database"
        )

    return UserResponse(
        id=id,
        email=email,
        roles=roles,
        role_ids=role_ids,
        first_name=user["first_name"],
        last_name=user["last_name"],
        school_email=email,
        profile_picture_url=profile_picture_url
    )