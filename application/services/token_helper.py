from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import json

def authenticate():
    with open("gmail_refresh_token.json") as f:
        token_data = json.load(f)

    creds = Credentials(
        None,
        refresh_token=token_data["refresh_token"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        token_uri=token_data["token_uri"]
    )
    creds.refresh(Request())
    return creds
