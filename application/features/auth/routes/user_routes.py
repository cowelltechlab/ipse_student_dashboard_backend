from typing import Dict
from fastapi import HTTPException, APIRouter, Depends
from application.features.auth.schemas import (
    StudentProfile,
    UserResponse,
    UpdateOwnEmailRequest,
    ResetOwnPasswordRequest,
    UpdateProfilePictureRequest
)
from application.features.auth.permissions import require_user_access
from application.features.users.crud.user_queries import (
    get_user_with_roles_by_id,
    update_user_email,
    update_own_password
)

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


@router.patch("/email")
async def update_own_email(
    email_data: UpdateOwnEmailRequest,
    user_data: Dict = Depends(require_user_access)
):
    """
    Update the current user's email address(es).
    User must be authenticated via JWT token.

    Args:
        email_data: UpdateOwnEmailRequest with optional email and/or gt_email
        user_data: JWT token data from require_user_access dependency

    Returns:
        Updated user details

    Raises:
        HTTPException: 400 if no email provided, 409 if email already exists, 404 if user not found
    """
    user_id = user_data.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload: missing user_id."
        )

    # Call existing update_user_email function
    updated_user = update_user_email(
        user_id=user_id,
        email=email_data.email,
        gt_email=email_data.gt_email
    )

    return updated_user


@router.post("/reset-password")
async def reset_own_password(
    password_data: ResetOwnPasswordRequest,
    user_data: Dict = Depends(require_user_access)
):
    """
    Reset the current user's password.
    Requires the user's current password for verification.

    Args:
        password_data: ResetOwnPasswordRequest with current and new passwords
        user_data: JWT token data from require_user_access dependency

    Returns:
        Success message

    Raises:
        HTTPException: 401 if current password incorrect, 404 if user not found
    """
    user_id = user_data.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload: missing user_id."
        )

    result = update_own_password(
        user_id=user_id,
        current_password=password_data.current_password,
        new_password=password_data.new_password
    )

    return result


@router.post("/profile-picture")
async def update_own_profile_picture(
    picture_data: UpdateProfilePictureRequest,
    user_data: Dict = Depends(require_user_access)
):
    """
    Update the current user's profile picture URL.

    Args:
        picture_data: UpdateProfilePictureRequest with profile_picture_url
        user_data: JWT token data from require_user_access dependency

    Returns:
        Success message with updated profile picture URL

    Raises:
        HTTPException: 404 if user not found, 500 on database error
    """
    from application.database.mssql_connection import get_sql_db_connection
    import pyodbc

    user_id = user_data.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload: missing user_id."
        )

    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Update profile picture URL
            cursor.execute(
                "UPDATE Users SET profile_picture_url = ? WHERE id = ?",
                (picture_data.profile_picture_url, user_id)
            )
            conn.commit()

            # Verify update
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")

            return {
                "success": True,
                "message": "Profile picture updated successfully",
                "profile_picture_url": picture_data.profile_picture_url
            }

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")