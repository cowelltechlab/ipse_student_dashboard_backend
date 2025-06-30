

import base64
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import os
from googleapiclient.discovery import build

from dotenv import load_dotenv

from application.services.token_helper import authenticate

# Load environment variables
load_dotenv()

sender_email = os.getenv("EMAIL_SENDER")


def send_invite_email(to_email: str, invite_url: str):

    creds = authenticate()
    service = build("gmail", "v1", credentials=creds)

    msg = MIMEMultipart("related")
    msg_alt = MIMEMultipart("alternative")
    sender_email = os.getenv("EMAIL_SENDER")
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = "You're Invited! Complete Your Setup"

    image_url = "https://ipseportalstorage.blob.core.windows.net/app-assets/Create Profile.svg"

    html_body = f"""
    <html>
    <body>
        <img src="{image_url}" alt="Logo" style="width:150px;"/>
        <h2>Welcome!</h2>
        <p>You have been invited to join our platform. Click the button below to complete your account setup:</p>
        <p><a href="{invite_url}" style="padding: 10px 20px; color: white; background-color: #007bff; text-decoration: none; border-radius: 4px;">Complete Setup</a></p>
        <p>If you did not request this invitation, you can ignore this email.</p>
    </body>
    </html>
    """


    msg_alt.attach(MIMEText(html_body, "html"))
    msg.attach(msg_alt)

    # Add logo image (assumes logo.png is in project root or adjust path)
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    try:
        with open(logo_path, "rb") as img_file:
            img = MIMEImage(img_file.read())
            img.add_header("Content-ID", "<logoimage>")
            img.add_header("Content-Disposition", "inline", filename="logo.png")
            msg.attach(img)
    except Exception as e:
        print(f"Warning: Could not attach image. {e}")

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    message = {"raw": raw_message}

    try:
        service.users().messages().send(userId="me", body=message).execute()
        print("Invite email sent successfully!")
    except Exception as e:
        print(f"Error sending invite email: {e}")
