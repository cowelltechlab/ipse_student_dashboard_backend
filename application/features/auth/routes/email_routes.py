import os
from fastapi import HTTPException, APIRouter, Depends
from application.features.users.crud.user_queries import get_user_with_roles_by_id
from application.features.auth.permissions import require_admin_access
from application.features.auth.schemas import UserLogin, TokenResponse, ForgotPasswordRequest, ResetPasswordRequest, AdminResetPasswordRequest
from application.features.auth.auth_helpers import validate_user_email_login, hash_password
from application.features.auth.token_service import create_token_response
from application.features.auth.crud import (
    get_user_by_email,
    create_password_reset_token,
    validate_password_reset_token,
    update_user_password,
    mark_password_reset_token_used,
    get_user_email_by_id,
    
)
from application.services.email_sender import send_password_reset_email

router = APIRouter()


@router.post("/login/email")
async def email_login(user_credentials: UserLogin) -> TokenResponse:
    """
    Log user in via email and password without SSO.
    """
    user_id = -1

    try:
        user_id = validate_user_email_login(
            user_credentials.email, 
            user_credentials.password
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error during email login: {e}")
        raise HTTPException(
            status_code=500, 
            detail="An internal server error occurred."
        )

    return create_token_response(user_id)


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Initiates password reset process. Sends reset email if user exists.
    Always returns success for security (doesn't reveal if email exists).
    """
    try:
        user = get_user_by_email(request.email)
        
        if user:
            user_id = user["id"]
            reset_token = create_password_reset_token(user_id)
            
            if reset_token:
                frontend_base_url = os.getenv("FRONTEND_BASE_URL")
                if not frontend_base_url:
                    raise RuntimeError("FRONTEND_BASE_URL not configured")
                
                reset_url = f"{frontend_base_url}/reset-password?token={reset_token}"
                send_password_reset_email(request.email, reset_url)
    
    except Exception as e:
        print(f"Error in forgot password process: {e}")
    
    return {"message": "If the email address exists in our system, you will receive a password reset link."}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Resets user password using a valid reset token.
    Requires email verification for additional security.
    """
    user_id = validate_password_reset_token(request.token)
    
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token."
        )
    
    # Verify email matches the user associated with the token
    stored_email = get_user_email_by_id(user_id)
    
    if not stored_email:
        raise HTTPException(
            status_code=400,
            detail="User not found."
        )
    
    # Check if provided email matches (case-insensitive)
    if stored_email.lower() != request.email.lower():
        raise HTTPException(
            status_code=400,
            detail="Email does not match the account associated with this reset token."
        )
    
    hashed_password = hash_password(request.new_password)
    
    success = update_user_password(user_id, hashed_password)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to update password. Please try again."
        )
    
    mark_password_reset_token_used(request.token)

    return {"message": "Password has been successfully reset."}


@router.post("/admin-reset-password")
async def admin_reset_password(
    request: AdminResetPasswordRequest,
    admin_data: dict = Depends(require_admin_access)
):
    """
    Admin-only endpoint to reset a user's password by user ID.
    Does not require email verification or reset tokens.
    """
    # Get user information from user ID
    user = get_user_with_roles_by_id(request.user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {request.user_id} not found."
        )

    hashed_password = hash_password(request.new_password)

    # Update the password
    success = update_user_password(request.user_id, hashed_password)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to update password. Please try again."
        )

    return {
        "message": f"Password successfully reset for user {request.user_id} ({user['first_name']} {user['last_name']})."
    }