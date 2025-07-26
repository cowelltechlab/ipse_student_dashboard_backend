from google_auth_oauthlib.flow import InstalledAppFlow
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
google_oauth = os.getenv("GOOGLE_OAUTH")

if not google_oauth:
    raise ValueError("Environment variable GOOGLE_OAUTH is not set or empty.")

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
config = json.loads(google_oauth)

flow = InstalledAppFlow.from_client_config({"installed": config}, SCOPES)

creds = flow.run_local_server(
    port=8000,
    access_type='offline',
    prompt='consent'
)

# Build credentials JSON
token_json = {
    "refresh_token": creds.refresh_token,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
    "token_uri": creds.token_uri
}

# Resolve .env path
env_file = Path(__file__).resolve().parent.parent / ".env"

# Read existing lines
lines = []
if env_file.exists():
    with open(env_file, "r") as f:
        lines = f.readlines()

# Write back with updated/added GMAIL_CREDENTIALS as JSON string
with open(env_file, "w") as f:
    found = False
    for line in lines:
        if line.startswith("GMAIL_CREDENTIALS="):
            f.write(f'GMAIL_CREDENTIALS=\'{json.dumps(token_json)}\'\n')
            found = True
        else:
            f.write(line)
    if not found:
        f.write(f"\nGMAIL_CREDENTIALS='{json.dumps(token_json)}'\n")

print("✅ Gmail credentials saved to .env")
