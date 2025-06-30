# For oauth2 email sending / google login help.

import os
import pickle
import google.auth.transport.requests
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def authenticate():
    creds = None
    token_path = 'token.pickle'
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token_file:
            creds = pickle.load(token_file)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('google_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token_file:
            pickle.dump(creds, token_file)
    return creds