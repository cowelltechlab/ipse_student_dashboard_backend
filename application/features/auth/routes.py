"""
Sources:
- https://developers.google.com/identity/oauth2/web/guides/how-user-authz-works
- https://medium.com/@vivekpemawat/enabling-googleauth-for-fast-api-1c39415075ea
- Google Gemini
"""
from fastapi import HTTPException, APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from application.features.auth.google_oauth import *
from application.features.auth.jwt_handler import (create_jwt_token, verify_jwt_token)
from application.features.auth.db_crud import (
    get_user_email_by_id, 
    get_refresh_token_details, 
    get_user_role_names, 
    get_user_by_email,
    store_refresh_token,
    delete_refresh_token,
)
from typing import Dict
from application.features.auth.auth_helpers import validate_user_email_login
from datetime import datetime
from application.features.auth.schemas import UserLogin, TokenResponse, UserResponse


# This should include a way to log in through Google and generic username/password
''' 
Prepend all student routes with /students and collect all student-relevant 
endpoints under Students tag in SwaggerUI
'''
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.post("/login/email")
async def email_login(user_credentials: UserLogin) -> TokenResponse:
    """
    Log user in via email and password without SSO.

    TODO: implement. Authenticate email and password, handle access tokens.
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
    
    # Get user roles to generate new access roles
    roles: List[str] = get_user_role_names(user_id)

    # Generate access token
    email = get_user_email_by_id(user_id)
    if not email:
        raise HTTPException(
            status_code=500, 
            detail="User email could not be retrieved after authentication."
        )
    
    access_token = create_jwt_token(
        {
            "user_id": user_id,
            "email": email,
            "roles": roles
        },
        expires_delta=15
    )

    # Generate refresh token
    refresh_token = store_refresh_token(user_id) 

    return TokenResponse( 
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get("/login/google")
async def google_login():
    """
    Retrieve Google SSO OAuth URL. Use to log user in with Google account.
    """
    backend_callback_uri = CONFIG["redirect_uris"][0]
    return { "google_auth_url": get_google_oauth_url(backend_callback_uri) }


@router.post("/logout")
async def logout(refresh_token: str) -> Dict[str, str]:
    """
    Logs user out of app by deleting refresh token from DB.

    :param refresh_token: long-lived per user credential securely stored in 
                          database.
    :type refresh_token: str
    :return: log-out message
    :rtype: Dict[str, str]
    """
    delete_refresh_token(refresh_token)
    return {"message": "Log-out successful."}


@router.post("/refresh_token")
async def refresh_access_token(refresh_token: str) -> TokenResponse:
    """
    Retrieves current refresh token and generates a new access token (JWT) with
    new expiration date.

    :param refresh_token: encoded refresh token
    :type refresh_token: str
    :return: Dictionary containing new access token in format {"access_token": 
             new_access_token, "token_type": "bearer"}
    :rtype: TokenResponse
    :raises HTTPException: if User is not found or current refresh token is 
                           either invalid or expired.
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
    
    email = get_user_email_by_id(user_id)
    if not email:
        raise HTTPException(status_code=401, detail="User not found")
    
    roles = get_user_role_names(user_id)

    new_access_token = create_jwt_token(
        {
            "user_id": user_id,
            "email": email,
            "roles": roles
        }
    )

    new_refresh_token = store_refresh_token(user_id)
    delete_refresh_token(refresh_token)

    return TokenResponse( 
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.get("/google/callback") # TODO: This URI must be registered in Google Cloud Console
async def google_auth_callback(code: str) -> TokenResponse: # Dict[str, str]:
    """
    Handles callback from Google OAuth that redirects back to current app. 
    Order of events: 
    1. Encoded auth code is exchanged for a token.
    2. Token is sent to Google for verification.
    3. Google returns an access token and refresh token. 
    4. Use access token to get Google profile info
    5. Update user info in DB, including newly issued JWT

    Code in this function includes heavy borrowing from Google Gemini. 

    :param code: OAuth 2.0 authorization code. It is a temporary code issued by
                 Google identifying signed-in individual users.
    :type code: str
    :return: Access and refresh tokens stored in dictionary.
    :rtype: Dict[str, str]
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
        
        # TODO: Add ability to create a user.
        # TODO: double-check status code
        user = get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=403, 
                detail="User does not exist in system."
            )
        
        user_id = user["id"]
        roles = get_user_role_names(user_id)
        access_token = create_jwt_token(
            {
                "user_id": user_id,
                "email": email,
                "roles": roles
            }
        )
        
        refresh_token = store_refresh_token(user_id)

        return TokenResponse( 
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
    except ValueError as ve:
        print(f"Google ID token verification failed: {ve}")
        raise HTTPException(
            status_code=401, 
            detail="Invalid Google ID token. Please try logging in again."
        )


@router.get("/me")
async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    """
    Retrieve identifying and access data for current user. Expects token to be 
    passed in by front-end, then uses that to determine who is logged in.

    :param token: Encoded JSON Web Token (JWT)
    :type token: str
    :returns: Current user's ID, email, name, and access roles
    :rtype: Dict[str, str]
    :raises HTTPException: When user not found, token is invalid or expired, or
                           token payload (from decoded JWT) is invalid.
    """
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    email = payload.get("email")
    id = payload.get("user_id")
    roles = payload.get("roles")
    if not email or not id or not roles:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": id,
        "email": email,
        "roles": roles,
        "first_name": user["first_name"],
        "last_name": user["last_name"]
    }

'''
TODO: Incorporate user creation into a later deliverable. 

Suggested code from Google Gemini:
from google.oauth2 import id_token
from google.auth.transport import requests as google_auth_requests 

# --- 3. Google OAuth Callback Endpoint ---
@router.get("/google/callback") # This URI must be registered in Google Cloud Console
async def google_auth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: Optional[str] = Query(None, description="CSRF protection state parameter"),
    response: Response = None, # For redirecting the browser
    request: Request = None # For accessing session if you store state there
):
    """
    Handles callback from Google OAuth.
    1. Exchanges auth code for Google tokens.
    2. Verifies Google's ID Token to get user info.
    3. Authenticates/Registers user in your system.
    4. Issues your app's access and refresh tokens.
    5. Redirects to frontend with tokens (or returns JSON).
    """
    # 0. Validate state parameter (CRITICAL for CSRF protection)
    # stored_state = request.session.get("oauth_state") # Example if using session middleware
    # if not state or state != stored_state:
    #     # Clear session state to prevent replay
    #     # request.session.pop("oauth_state", None)
    #     raise HTTPException(status_code=400, detail="Invalid or missing state parameter. Possible CSRF attack.")
    # # request.session.pop("oauth_state", None) # Clear after use

    # Use the same backend redirect URI as in the initial request
    backend_callback_uri = CONFIG["redirect_uris"][0]

    try:
        # 1. Exchange authorization code for Google's tokens
        token_response_json = await exchange_code_for_token_async(code, backend_redirect_uri)
        
        google_id_token_str = token_response_json.get("id_token")
        google_access_token_str = token_response_json.get("access_token")
        google_refresh_token_str = token_response_json.get("refresh_token") # Google's long-lived refresh token

        if not google_id_token_str:
            raise HTTPException(status_code=400, detail="No ID token received from Google.")

        # 2. Verify Google's ID Token (CRITICAL for security)
        try:
            # Use google-auth library for robust verification
            id_info = id_token.verify_oauth2_token(
                google_id_token_str,
                google_auth_requests.Request(), # Uses google-auth's http client
                CONFIG["client_id"]
            )
            # id_info will contain claims like 'sub' (Google ID), 'email', 'name', 'picture'
        except ValueError as ve:
            print(f"Google ID token verification failed: {ve}")
            raise HTTPException(status_code=401, detail="Invalid Google ID token. Please try logging in again.")

        google_user_id = id_info["sub"] # Google's unique ID for the user
        user_email = id_info.get("email")
        user_name = id_info.get("name")
        # You might also want id_info.get("picture")

        if not user_email: # Email is crucial for your user identification
             raise HTTPException(status_code=403, detail="No email provided by Google. Cannot log in.")

        # 3. User Management (Get or Create User in Your DB)
        app_user = get_user_by_google_id(google_user_id) # Try to find user by Google ID first

        if app_user:
            app_user_id = app_user["id"]
            # Optionally update user's email/name/picture in your DB if it changed in Google
        else:
            # User does not exist in your system yet - create them (Just-In-Time Provisioning)
            app_user_id = create_user_from_google_profile(
                google_user_id=google_user_id,
                email=user_email,
                name=user_name # Pass name if you want to store it
                # picture=id_info.get("picture")
            )
            # Handle potential errors during user creation
            if not app_user_id:
                raise HTTPException(status_code=500, detail="Failed to create user account.")
        
        # 4. Store Google's Refresh Token (if you need to make future Google API calls)
        # This is Google's refresh token, NOT your app's refresh token.
        if google_refresh_token_str:
            store_google_refresh_token(app_user_id, google_refresh_token_str)
            
        # 5. Generate Your Application's Tokens (Access and Refresh)
        roles = get_user_role_names(app_user_id) # Get roles for your app's JWT
        
        app_access_token = create_jwt_token({
            "user_id": app_user_id,
            "email": user_email,
            "roles": roles
        })

        app_refresh_token = store_refresh_token(app_user_id) # Your app's long-lived token

        # 6. Redirect to Frontend with your app's tokens (Recommended for initial OAuth flow)
        # Or you can return JSON if your frontend makes an AJAX call to this endpoint
        
        # Option A: Redirect (common for server-side OAuth callback)
        # This is more robust as it doesn't expose tokens in the URL fragment directly to Google's redirect
        # Your frontend will need to read these from the URL upon redirection.
        redirect_url = (
            f"{CONFIG['frontend_login_success_url']}"
            f"?access_token={app_access_token}"
            f"&refresh_token={app_refresh_token}"
            f"&token_type=bearer"
        )
        response.headers["Location"] = redirect_url
        return Response(status_code=302) # HTTP 302 Found for redirection

        # Option B: Return JSON (if your frontend makes an AJAX call to /google/callback)
        # return {
        #     "access_token": app_access_token,
        #     "refresh_token": app_refresh_token,
        #     "token_type": "bearer",
        #     "message": "Google login successful."
        # }

    except HTTPException as e:
        # If an HTTPException was raised, propagate it.
        # For redirects, you might redirect to a failure page instead.
        # response.headers["Location"] = f"{CONFIG['frontend_login_failure_url']}?error={e.detail}"
        # return Response(status_code=302)
        raise e
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred during Google OAuth callback: {e}")
        # Consider redirecting to an error page with a generic message for the user
        # response.headers["Location"] = f"{CONFIG['frontend_login_failure_url']}?error=internal_server_error"
        # return Response(status_code=302)
        raise HTTPException(status_code=500, detail="Google authentication failed due to an internal server error.")
'''