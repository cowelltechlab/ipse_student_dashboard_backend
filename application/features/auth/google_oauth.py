import requests
from config import CONFIG
from typing import Any, Dict


# ✅ Generate Google OAuth URL
def get_google_oauth_url() -> str:
    """
    Generate Google SSO OAuth URL based on config file.

    :returns: Google OAuth URL
    :rtype: str
    """
    return (
        f"https://accounts.google.com/o/oauth2/auth"
        f"?client_id={CONFIG["google"]['GOOGLE_CLIENT_ID']}"
        f"&redirect_uri={CONFIG["google"]['GOOGLE_REDIRECT_URI']}"
        f"&response_type=code"
        f"&scope=email profile openid"
        f"&access_type=offline"
    )


def exchange_code_for_token(code: str) -> Dict[str, Any]:
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
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": CONFIG["google"]["GOOGLE_CLIENT_ID"],
        "client_secret": CONFIG["google"]["GOOGLE_CLIENT_SECRET"],
        "redirect_uri": CONFIG["google"]["GOOGLE_REDIRECT_URI"],
        "grant_type": "authorization_code",
    }

    response = requests.post(token_url, data=token_data)
    response.raise_for_status()
    return response.json()


# ✅ Get User Info from Google
def get_google_user_info(access_token: str):
    response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    return response.json()