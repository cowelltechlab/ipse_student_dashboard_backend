"""
Sources:
- https://developers.google.com/identity/oauth2/web/guides/how-user-authz-works
- https://medium.com/@vivekpemawat/enabling-googleauth-for-fast-api-1c39415075ea
- Google Gemini
"""
from fastapi import HTTPException, APIRouter, Depends, status, Query
from fastapi.security import OAuth2PasswordBearer
from application.features.auth.google_oauth import *
from application.features.auth.jwt_handler import *
from application.features.auth.db_crud import (
    get_user_email_by_id, 
    get_user_id_from_refresh_token, 
    get_user_role_names, 
    get_user_by_email,
    store_refresh_token,
    delete_refresh_token
)
from typing import Dict


# This should include a way to log in through Google and generic username/password
''' 
Prepend all student routes with /students and collect all student-relevant 
endpoints under Students tag in SwaggerUI
'''
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.get("login/email")
def email_login():
    """
    Log user in via email and password without SSO.

    TODO: implement
    """
    return { "email_auth": "Email log-in functionality not yet implemented." }


@router.get("/login/google")
def google_login():
    """
    Retrieve Google SSO OAuth URL. Use to log user in with Google account.
    """
    return { "google_auth_url": get_google_oauth_url() }


@router.post("/logout")
def logout(refresh_token: str) -> Dict[str, str]:
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


@router.get("/refresh_token")
def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """
    Retrieves current refresh token and generates a new JWT with new 
    expiration date.

    TODO: Implement. Add ability to update token in DB

    :param refresh_token: encoded refresh token
    :type refresh_token: str
    :return: Dictionary containing new access token in format {"access_token": 
             new_access_token, "token_type": "bearer"}
    :rtype: Dict[str, Any]
    :raises HTTPException: if User is not found or current refresh token is 
                           either invalid or expired.
    """
    user_id = get_user_id_from_refresh_token(refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
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

    return {"access_token": new_access_token, "token_type": "bearer"}


@router.get("/google/callback")
def google_auth_callback(code: str) -> Dict[str, str]:
    """
    Handles callback from Google OAuth that redirects back to current app. 
    Order of events: 
    1. Encoded auth code is exchanged for a token.
    2. Token is sent to Google for verification.
    3. Google returns an access token and refresh token. 
    4. Use access token to get Google profile info
    5. Update user info in DB, including newly issued JWT 

    :param code: OAuth 2.0 authorization code. It is a temporary code issued by
                 Google identifying signed-in individual users.
    :type code: str
    :return: Access and refresh tokens stored in dictionary.
    :rtype: Dict[str, str]
    """
    token_response_json: Dict = exchange_code_for_token(code)
    user_info = get_google_user_info(token_response_json["access_token"])

    email = user_info.get("email")
    name = user_info.get("name")

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

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/me")
def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, str]:
    """
    Retrieve identifying and access data for current user. 

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