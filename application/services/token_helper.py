from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv
import os
import json

load_dotenv()

def authenticate():
    creds_json = os.getenv("GMAIL_CREDENTIALS")
    if not creds_json:
        raise ValueError("GMAIL_CREDENTIALS is not set in .env")

    token_data = json.loads(creds_json)

    creds = Credentials(
        None,
        refresh_token=token_data["refresh_token"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        token_uri=token_data["token_uri"]
    )
    creds.refresh(Request())
    return creds
