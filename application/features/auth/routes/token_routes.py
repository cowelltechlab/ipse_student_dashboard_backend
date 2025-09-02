from typing import Dict
from datetime import datetime
from fastapi import HTTPException, APIRouter, Depends
from application.features.auth.crud import (
    get_refresh_token_details,
    delete_refresh_token,
)
from application.features.auth.schemas import TokenResponse
from application.features.auth.permissions import require_user_access
from application.features.auth.token_service import create_token_response

router = APIRouter()


@router.post("/logout")
async def logout(
    refresh_token: str, 
    user_data: Dict = Depends(require_user_access)
) -> Dict[str, str]:
    """
    Logs user out of app by deleting refresh token from DB.
    """
    delete_refresh_token(refresh_token)
    return {"message": "Log-out successful."}


@router.post("/refresh_token")
async def refresh_access_token(refresh_token: str) -> TokenResponse:
    """
    Retrieves current refresh token and generates a new access token (JWT) with
    new expiration date.
    """
    token_details = get_refresh_token_details(refresh_token)
    if not token_details:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    user_id = token_details["user_id"]
    expires_at = token_details["expires_at"]

    if expires_at < datetime.now():
        delete_refresh_token(refresh_token)
        raise HTTPException(
            status_code=401, 
            detail="Invalid or expired refresh token. Please log in again."
            )
    
    new_token_response = create_token_response(user_id)
    delete_refresh_token(refresh_token)

    return new_token_response