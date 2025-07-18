"""
Source: This code is initially seeded by Google Gemini, then modified by devs
"""
import os
from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT
from saml2.saml import NAMEID_FORMAT_UNSPECIFIED
from saml2.sigver import get_xmlsec_binary
from dotenv import load_dotenv

load_dotenv()

# --- Configuration for your Service Provider (SP) ---

# Base URL of your application running locally
# Since you're running locally on port 8000
BASE_URL = str(os.getenv("SAML2_BASE_URL")) # "http://localhost:8000" 

if not BASE_URL:
    raise ValueError("SAML2_BASE_URL environment variable is not set.")

# TODO: Read below. Here, IdP means identity provider, which would be GA Tech
# IMPORTANT: If you use ngrok/serveo for testing with an external IdP (like Gatech)
# you MUST update this BASE_URL to the public URL provided by ngrok/serveo.
# For example: BASE_URL = "https://your-ngrok-subdomain.ngrok-free.app"

# Path to your generated private key and public certificate
CERT_DIR = os.path.join(os.path.dirname(__file__), "saml_certs")
PRIVATE_KEY_FILE = os.path.join(CERT_DIR, "sp_private.key")
PUBLIC_CERT_FILE = os.path.join(CERT_DIR, "sp_public.crt")

# XMLSEC binary path (ensure xmlsec1 is installed and accessible)
XMLSEC_PATH = get_xmlsec_binary(["/opt/local/bin", "/usr/local/bin", "/usr/bin", "/bin"])
if not XMLSEC_PATH:
    raise RuntimeError("xmlsec1 binary not found. Please install it (e.g., brew install xmlsec1 on macOS, apt-get install xmlsec1 on Linux).")


SP_CONFIG = {
    "entityid": f"{BASE_URL}/auth/gatech/saml2/metadata",  # Unique identifier for your SP
    "name": "AI for Higher Learning - Dev SP",  # Display name for your SP
    "description": "SAML2 Service Provider for AI for Higher Learning Application",

    "service": {
        "sp": {
            "endpoints": {
                # Assertion Consumer Service (ACS) endpoint:
                # Where the IdP sends the SAML response after successful authentication.
                # Must be an absolute URL. This MUST match the actual route in routes.py
                "assertion_consumer_service": [
                    (f"{BASE_URL}/auth/gatech/saml2/acs", BINDING_HTTP_POST), # Endpoints must exist in routes.py
                ]
            },
            # Require the IdP to sign assertions. This is a crucial security setting.
            "want_assertions_signed": True,
            # Require the IdP to sign responses. Also a good security practice.
            "want_response_signed": True,
            # Sign outgoing authentication requests (AuthnRequests). Recommended.
            "authn_requests_signed": True,
            # Allow IdP-initiated SSO. If the IdP can directly initiate login without your SP sending an AuthnRequest.
            "allow_unsolicited": True, 
        },
    },

    # Paths to your SP's private key and public certificate
    "key_file": PRIVATE_KEY_FILE,
    "cert_file": PUBLIC_CERT_FILE,

    # Path to the xmlsec1 binary
    "xmlsec_binary": XMLSEC_PATH,

    # Metadata for the Identity Provider (IdP).
    # THIS IS WHERE YOU'LL ADD THE GATECH IDP METADATA LATER!
    # For now, it remains empty or placeholder.
    "metadata": {
        "local": [], # Will be a list of paths to IdP metadata XML files (e.g., ["./saml_certs/gatech_idp_metadata.xml"])
    },

    # Define acceptable NameID formats from the IdP.
    # URN: Oasis:names:tc:SAML:2.0:nameid-format:emailAddress is common
    # or you might start with UNSPECIFIED if you don't know yet.
    "nameid_format": NAMEID_FORMAT_UNSPECIFIED, # Start with UNSPECIFIED, can refine later

    # Optional TODO: Add organization details for your metadata
    # "organization": {
    #     "name": ("cowelltechlab", "en"),
    #     "display_name": ("Cowell Tech Lab", "en"),
    #     "url": ("https://cowelltechlab.com", "en"), # Replace with your actual org website
    # },

    # Optional: Contact persons for your metadata
    # TODO: Determine if this is to be kept on the backend. We already have to input this info on the SSO request form
    # "contact_person": [
    #     {
    #         "givenname": "Your Name",
    #         "surname": "Your Surname",
    #         "company": "Cowell Tech Lab",
    #         "email_address": "your.email@cowelltechlab.com",
    #         "contact_type": "technical",
    #     },
    # ],

    "debug": 1, # Set to 1 for more verbose logging during development
                # TODO: Set to 0 for production if not using verbose logging then
}