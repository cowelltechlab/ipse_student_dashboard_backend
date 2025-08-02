"""
Sources: 
- https://medium.com/@vivekpemawat/enabling-googleauth-for-fast-api-1c39415075ea
- Google Gemini
"""
import requests
from fastapi import HTTPException
from typing import Any, Dict, List
from dotenv import load_dotenv
import os 
import json
import httpx

from urllib.parse import urlencode


load_dotenv()
google_auth_str = os.getenv("GOOGLE_OAUTH")
google_callback_uri = os.getenv("GOOGLE_CALLBACK_URI")
CONFIG: Dict[str, Any] = {}

if google_auth_str:
    try:
        CONFIG = json.loads(google_auth_str)
    except json.JSONDecodeError as e:
        CONFIG = { "error": str(e) }
else:
    CONFIG = { "error": "GOOGLE_OAUTH not present in environment variables." }



def get_google_oauth_url(
    backend_callback_uri: str = google_callback_uri
) -> str:
    allowed_redirect_uris: List[str] = CONFIG["redirect_uris"]

    if backend_callback_uri not in allowed_redirect_uris:
        raise HTTPException(
            status_code=400,
            detail="Invalid redirect URI provided."
        )

    query_params = {
        "client_id": CONFIG["client_id"],
        "redirect_uri": backend_callback_uri,
        "response_type": "code",
        "scope": "email profile openid",
        "access_type": "offline"
    }

    return f"{CONFIG['auth_uri']}?{urlencode(query_params)}"


async def exchange_code_for_token(
    code: str,
    backend_redirect_uri: str = google_callback_uri
    ) -> Dict[str, Any]:
    """
    Exchange authorization codes for access tokens from Google's OAuth 2.0 
    endpoint. 
    """
    allowed_redirect_uris: List[str] = CONFIG["redirect_uris"]

    if backend_redirect_uri not in allowed_redirect_uris:
        raise HTTPException(
            status_code=400,
            detail="Invalid redirect URI provided."
        )

    token_url = CONFIG["token_uri"] # "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": CONFIG["client_id"],
        "client_secret": CONFIG["client_secret"],
        "redirect_uri": backend_redirect_uri,
        "grant_type": "authorization_code",
    }

    # response = requests.post(token_url, data=token_data)
    # response.raise_for_status()
    # return response.json()
    ### Borrowed from Google Gemini ###
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(token_url, data=token_data)
            response.raise_for_status() # Raises an exception for 4xx/5xx responses
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error exchanging code for token: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Google token exchange failed: {e.response.text}")
        except httpx.RequestError as e:
            print(f"Network error during token exchange: {e}")
            raise HTTPException(status_code=500, detail="Network error during Google token exchange.")
    ### End borrowed code. ###


def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """
    Retrieves authenticated Google user's profile information.
    """
    response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response.raise_for_status()
    return response.json()