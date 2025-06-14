"""
Sources:
- https://developers.google.com/identity/oauth2/web/guides/how-user-authz-works
- https://medium.com/@vivekpemawat/enabling-googleauth-for-fast-api-1c39415075ea
"""
from fastapi import HTTPException, APIRouter, Depends, status, Query
from fastapi.security import OAuth2PasswordBearer
from auth.google_oauth import *
from auth.jwt_handler import *
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

    TODO: Implement

    :param refresh_token: long-lived per user credential securely stored in 
                          database.
    :type refresh_token: str
    :return: log-out message
    :rtype: Dict[str, str]
    """
    return {"message": "Log-out functionality not yet implemented."}


@router.get("/refresh_token")
def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """
    Retrieves current refresh token and generates a new JWT with new 
    expiration date.

    TODO: Implement

    :param refresh_token: encoded refresh token
    :type refresh_token: str
    :return: Dictionary containing new access token in format {"access_token": 
             new_access_token, "token_type": "bearer"}
    :rtype: Dict[str, Any]
    :raises HTTPException: if User is not found or current refresh token is 
                           either invalid or expired.
    """
    return {}


@router.get("/me")
def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, str]:
    """
    Retrieve identifying and access data for current user. 

    TODO: Implement

    :param token: Encoded JSON Web Token (JWT)
    :type token: str
    :returns: Current user's ID, email, name, and apps they can access
    :rtype: Dict[str, str]
    :raises HTTPException: When user not found, token is invalid or expired, or
                           token payload (from decoded JWT) is invalid.
    """
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return {}
    # user = get_user_with_apps(email)
    # if not user:
    #     raise HTTPException(status_code=404, detail="User not found")

    # return {
    #     "id": user["id"],
    #     "email": user["email"],
    #     "name": user.get("name", ""),
    #     "apps": user["apps"],
    # }