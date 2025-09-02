from fastapi import HTTPException, APIRouter
from application.features.auth.google_oauth import CONFIG, get_google_oauth_url, exchange_code_for_token, get_google_user_info
from application.features.auth.crud import get_user_by_email
from application.features.auth.schemas import TokenResponse
from application.features.auth.token_service import create_token_response

router = APIRouter()


@router.get("/login/google")
async def google_login():
    """
    Retrieve Google SSO OAuth URL. Use to log user in with Google account.
    """
    backend_callback_uri = CONFIG["redirect_uris"][0]
    return { "google_auth_url": get_google_oauth_url(backend_callback_uri) }


@router.get("/google/callback")
async def google_auth_callback(code: str) -> TokenResponse: 
    """
    Handles callback from Google OAuth that redirects back to current app. 
    TODO: add in 400 status error for bad request, such as reusing old one-time token
    """
    backend_callback_uri = CONFIG["redirect_uris"][0]

    try:
        token_response_json = await exchange_code_for_token(
            code, backend_callback_uri)
        
        user_info = get_google_user_info(token_response_json["access_token"])

        email = user_info.get("email")

        if not email:
            raise HTTPException(
                status_code=403, 
                detail="No email passed back. Error from Google servers."
            )
        
        user = get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=403, 
                detail="User does not exist in system."
            )
        
        user_id = user["id"]
        return create_token_response(user_id)
        
    except ValueError as ve:
        print(f"Google ID token verification failed: {ve}")
        raise HTTPException(
            status_code=401, 
            detail="Invalid Google ID token. Please try logging in again."
        )