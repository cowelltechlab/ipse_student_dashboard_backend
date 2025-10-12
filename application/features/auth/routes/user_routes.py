from typing import Dict, Optional
from fastapi import HTTPException, APIRouter, Depends, File, Form, UploadFile
from application.features.auth.schemas import (
    StudentProfile,
    UserResponse,
    UpdateOwnEmailRequest,
    ResetOwnPasswordRequest,
    UpdateProfilePictureRequest,
    UpdateOwnNameRequest
)
from application.features.auth.permissions import require_user_access
from application.features.users.crud.user_queries import (
    get_user_with_roles_by_id,
    update_user_email,
    update_own_password
)
from application.utils.blob_upload import upload_profile_picture
from application.features.student_profile.crud import update_user_profile_picture

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
    
    print(user["gt_email"])

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

    print(email_data.gt_email)


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
    profile_picture: Optional[UploadFile] = File(None),
    existing_blob_url: Optional[str] = Form(None),
    user_data: Dict = Depends(require_user_access)
):
    """
    Update the current user's profile picture.
    Accepts either a file upload or an existing blob URL.

    Args:
        profile_picture: Optional uploaded image file
        existing_blob_url: Optional existing blob URL (if no file uploaded)
        user_data: JWT token data from require_user_access dependency

    Returns:
        Success message with profile picture URL

    Raises:
        HTTPException: 400 if no picture provided, 404 if user not found
    """
    user_id = user_data.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload: missing user_id."
        )

    # Handle file upload or existing URL
    if profile_picture:
        try:
            blob_url = await upload_profile_picture(user_id, profile_picture)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif existing_blob_url:
        blob_url = existing_blob_url
    else:
        raise HTTPException(status_code=400, detail="No profile picture provided")

    # Update the user's profile picture in the database
    update_user_profile_picture(user_id, blob_url)

    return {
        "success": True,
        "message": "Profile picture updated successfully",
        "profile_picture_url": blob_url
    }


@router.patch("/name")
async def update_own_name(
    name_data: UpdateOwnNameRequest,
    user_data: Dict = Depends(require_user_access)
):
    """
    Update the current user's first and/or last name.

    Args:
        name_data: UpdateOwnNameRequest with optional first_name and/or last_name
        user_data: JWT token data from require_user_access dependency

    Returns:
        Success message with updated name fields

    Raises:
        HTTPException: 400 if no name provided, 404 if user not found, 500 on database error
    """
    from application.database.mssql_connection import get_sql_db_connection
    import pyodbc

    user_id = user_data.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload: missing user_id."
        )

    # Build dynamic update query
    update_fields = []
    update_values = []

    if name_data.first_name is not None:
        update_fields.append("first_name = ?")
        update_values.append(name_data.first_name)

    if name_data.last_name is not None:
        update_fields.append("last_name = ?")
        update_values.append(name_data.last_name)

    if not update_fields:
        raise HTTPException(status_code=400, detail="At least one name field must be provided")

    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Update name fields
            update_query = f"UPDATE Users SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(user_id)
            cursor.execute(update_query, update_values)
            conn.commit()

            # Verify update
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")

            return {
                "success": True,
                "message": "Name updated successfully",
                "first_name": name_data.first_name,
                "last_name": name_data.last_name
            }

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")