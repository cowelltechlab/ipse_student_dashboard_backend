from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Load your OAuth2 client secret JSON (downloaded from Google Cloud Console)
with open("google_secret.json") as f:
    config = json.load(f)

flow = InstalledAppFlow.from_client_config({"installed": config}, SCOPES)

# Force the flow to return a refresh token
creds = flow.run_local_server(
    port=8000,
    access_type='offline',
    prompt='consent'
)

# Save the refresh token and other required fields
with open("gmail_refresh_token.json", "w") as f:
    json.dump({
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "token_uri": creds.token_uri,
    }, f)

print("✅ Refresh token saved.")
