import os
from dotenv import load_dotenv
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

# Load environment variables
load_dotenv()
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")


def send_email_sendgrid(to_email: str, subject: str, html_body: str, plain_body: str = None):
    """Send email using SendGrid API."""
    
    if not SENDGRID_API_KEY:
        raise ValueError("SENDGRID_API_KEY is not set in .env")
    
    if not SENDER_EMAIL:
        raise ValueError("EMAIL_SENDER is not set in .env")
    
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    
    from_email = Email(SENDER_EMAIL)
    to_email_obj = To(to_email)
    
    # Create mail object
    mail = Mail(from_email, to_email_obj, subject)
    
    # Add content (plain text first, then HTML)
    if plain_body:
        mail.add_content(Content("text/plain", plain_body))
    mail.add_content(Content("text/html", html_body))
    
    try:
        response = sg.send(mail)
        print(f"Email sent successfully to {to_email}. Status: {response.status_code}")
        return response
    except Exception as e:
        print(f"Error sending email via SendGrid: {e}")
        raise


def send_invite_email(to_email: str, invite_url: str):
    """Send an HTML + Plain Text invite email via SendGrid."""
    
    subject = "You're Invited! Complete Your Setup"
    
    # Plain text fallback (improves spam filter score)
    plain_body = f"""Welcome!

You have been invited to join MyChoice.

Complete your account setup here: {invite_url}

If you did not request this invitation, you can ignore this email.
"""
    html_body = f"""
    <html>
      <body style="margin:0; padding:24px; background:#f6f9fc; font-family: Arial, sans-serif; color:#333;">
        <div style="max-width:600px; margin:0 auto; background:#ffffff; padding:24px; border-radius:8px; text-align:center;">
          <h2 style="margin:0 0 12px;">Welcome!</h2>
          <p style="margin:0 0 16px;">You have been invited to join MyChoice.</p>
          <p style="margin:24px 0;">
            <a href="{invite_url}"
               style="display:inline-block; padding:12px 20px; color:#ffffff; background-color:#007bff; text-decoration:none; border-radius:6px; font-weight:600;">
              Complete Setup
            </a>
          </p>
          <p style="margin-top:24px; color:#6b7280; font-size:12px;">
            If you did not request this invitation, you can safely ignore this email.
          </p>
        </div>
      </body>
    </html>
    """

    send_email_sendgrid(to_email, subject, html_body, plain_body)


def send_password_reset_email(to_email: str, reset_url: str):
    """Send a password reset email via SendGrid."""
    
    subject = "Reset Your Password"
    
    # Plain text fallback
    plain_body = f"""Password Reset Request

Someone (hopefully you) has requested a password reset for your account.

Reset your password here: {reset_url}

This link will expire in 1 hour.

If you did not request this password reset, you can safely ignore this email.
"""
    html_body = f"""
    <html>
      <body style="margin:0; padding:24px; background:#f6f9fc; font-family: Arial, sans-serif; color:#333;">
        <div style="max-width:600px; margin:0 auto; background:#ffffff; padding:24px; border-radius:8px; text-align:center;">
          <h2 style="margin:0 0 12px;">Password Reset Request</h2>
          <p style="margin:0 0 16px;">Someone (hopefully you) has requested a password reset for your account.</p>
          <p style="margin:24px 0;">
            <a href="{reset_url}"
               style="display:inline-block; padding:12px 20px; color:#ffffff; background-color:#007bff; text-decoration:none; border-radius:6px; font-weight:600;">
              Reset Your Password
            </a>
          </p>
          <p style="margin:0 0 8px; font-weight:700;">This link will expire in 1 hour.</p>
          <p style="margin-top:8px; color:#6b7280; font-size:12px;">
            If you did not request this password reset, you can safely ignore this email.
          </p>
        </div>
      </body>
    </html>
    """

    send_email_sendgrid(to_email, subject, html_body, plain_body)