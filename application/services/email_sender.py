import base64
import os
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from dotenv import load_dotenv
from application.services.token_helper import authenticate

# Load environment variables
load_dotenv()
SENDER_EMAIL = os.getenv("EMAIL_SENDER")


def send_invite_email(to_email: str, invite_url: str):
    """Send an HTML + Plain Text invite email via Gmail API."""

    # Authenticate Gmail API
    creds = authenticate()
    service = build("gmail", "v1", credentials=creds)

    # Create message container
    msg = MIMEMultipart("related")
    msg_alt = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = "You're Invited! Complete Your Setup"

    # Plain text fallback (improves spam filter score)
    plain_body = f"""Welcome!

You have been invited to join our platform.

Complete your account setup here: {invite_url}

If you did not request this invitation, you can ignore this email.
"""

    # HTML version
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <img src="https://ipseportalstorage.blob.core.windows.net/app-assets/Create Profile.svg"
             alt="Logo" style="width:150px; margin-bottom:10px;"/>
        <h2>Welcome!</h2>
        <p>You have been invited to join our platform.</p>
        <p>
            <a href="{invite_url}"
               style="padding: 10px 20px; color: white; background-color: #007bff;
                      text-decoration: none; border-radius: 4px;">
               Complete Setup
            </a>
        </p>
        <p>If you did not request this invitation, you can safely ignore this email.</p>
    </body>
    </html>
    """

    # Attach both plain and HTML versions
    msg_alt.attach(MIMEText(plain_body, "plain"))
    msg_alt.attach(MIMEText(html_body, "html"))
    msg.attach(msg_alt)

    # Optional: attach inline logo (if you prefer CID embedding instead of URL)
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as img_file:
                img = MIMEImage(img_file.read())
                img.add_header("Content-ID", "<logoimage>")
                img.add_header("Content-Disposition", "inline", filename="logo.png")
                msg.attach(img)
        except Exception as e:
            print(f"Warning: Could not attach logo image. {e}")

    # Encode message
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    message = {"raw": raw_message}

    # Send email via Gmail API
    try:
        service.users().messages().send(userId="me", body=message).execute()
        print(f"Invite email sent successfully to {to_email}")
    except Exception as e:
        print(f"Error sending invite email: {e}")
