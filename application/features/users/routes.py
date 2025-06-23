from fastapi import APIRouter, Depends, Query
from typing import List, Optional, Dict
from application.features.auth.permissions import require_teacher_access
from application.features.auth.schemas import UserResponse
from application.features.users.crud import get_all_users_with_roles

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
