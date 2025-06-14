"""
Sources: 
- https://medium.com/@vivekpemawat/enabling-googleauth-for-fast-api-1c39415075ea
- Google Gemini
"""
import requests
from config import CONFIG
from fastapi import HTTPException
from typing import Any, Dict, List


def get_google_oauth_url(
        frontend_redirect_uri: str = "http://localhost:8000") -> str:
    """
    Generate Google SSO OAuth URL based on config file. This is the first step 
    in the OAuth 2.0 Authorization Code flow. 

    :param frontend_redirect_uri: The URI where Google redirects after 
                                  authentication. Must be a registered URI.
    :type frontend_redirect_uri: str
    :returns: Google OAuth URL
    :rtype: str
    :raises HTTPException: 400 if the provided frontend_redirect_uri is not 
                           allowed.
    """
    allowed_redirect_uris: List[str] = CONFIG["google"]["redirect_uris"]

    if frontend_redirect_uri not in allowed_redirect_uris:
        raise HTTPException(
            status_code=400,
            detail="Invalid redirect URI provided."
        )

    return (
        f"{CONFIG["google"]["auth_uri"]}" # "https://accounts.google.com/o/oauth2/auth"
        f"?client_id={CONFIG["google"]['client_id']}"
        f"&redirect_uri={frontend_redirect_uri}"
        f"&response_type=code"
        f"&scope=email profile openid"
        f"&access_type=offline"
    )


def exchange_code_for_token(
        code: str,
        frontend_redirect_uri: str = "http://localhost:8000"
    ) -> Dict[str, Any]:
    """
    Exchange authorization codes for access tokens from Google's OAuth 2.0 
    endpoint. 
    
    This function represents the second step in the OAuth 2.0 Authorization 
    Code flow. It's called after a user grants your application permission 
    through Google's SSO, and Google redirects back with a temporary 
    authorization code.

    :param code: OAuth 2.0 authorization code. It is a temporary code issued by
                 Google identifying signed-in individual users.
    :type code: str
    :param frontend_redirect_uri: The URI where Google redirects after 
                                  authentication. Must be a registered URI.
    :type frontend_redirect_uri: str
    :return: Dictionary representing JSON response from Google's token 
             endpoint. This typically includes 'access_token' (used to access 
             Google APIs), 'expires_in', 'token_type', and often 'id_token' (a 
             JWT containing user identity information) and a 'refresh_token'.
    :rtype: Dict[str, Any]
    :raises requests.exceptions.RequestException: If Google returns an error 
                                                  response, returns its status 
                                                  code. Typically a network or
                                                  invalid response.
    """
    allowed_redirect_uris: List[str] = CONFIG["google"]["redirect_uris"]

    if frontend_redirect_uri not in allowed_redirect_uris:
        raise HTTPException(
            status_code=400,
            detail="Invalid redirect URI provided."
        )

    token_url = CONFIG["google"]["token_uri"] # "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": CONFIG["google"]["client_id"],
        "client_secret": CONFIG["google"]["client_secret"],
        "redirect_uri": frontend_redirect_uri,
        "grant_type": "authorization_code",
    }

    response = requests.post(token_url, data=token_data)
    response.raise_for_status()
    return response.json()


def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """
    Retrieves authenticated Google user's profile information.
    
    The Google API's the /userinfo endpoint returns basic profile data for user
    associated with an access token. This function can be called after 
    successful exchange of an authorization code for an access token.

    :param access_token: OAuth 2.0 access token obtained from Google's API. It 
                         grants app permission to access specific user data.
    :type access_token: str
    :return: A dictionary representing the JSON response from Google's userinfo
             endpoint. Common keys include 'id', 'email', 'verified_email',
             'name', 'given_name', 'family_name', and 'picture'.
    :rtype: Dict[str, Any]
    :raises requests.exceptions.RequestException: If Google returns an error 
                                                  response, returns its status 
                                                  code. Typically a network or
                                                  invalid response.
    """
    response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response.raise_for_status()
    return response.json()