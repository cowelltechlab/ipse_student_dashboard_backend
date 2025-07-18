"""
Source: This code is initially seeded by Google Gemini, then modified by devs
"""
import os
from saml2.client import Saml2Client
from saml2.config import Config
from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT # Keep these if you use them for prepare_for_authenticate, etc.
from saml2.metadata import create_metadata_string

# Import your SP configuration
from application.features.auth.gatech_saml2_config import SP_CONFIG, CERT_DIR # CERT_DIR might be useful here

# Global SAML client instance
saml_client: Saml2Client = None

def init_saml_client():
    """
    Initializes the global SAML2 client instance.
    This should be called once on application startup.
    """
    global saml_client
    if saml_client is None:
        try:
            sp_config = Config()
            sp_config.load(SP_CONFIG)

            # TODO: --- CRITICAL: Load IdP Metadata Here ---
            # This is placeholder. Once you get the IdP metadata XML from Georgia Tech,
            # save it in `application/features/auth/saml_certs/gatech_idp_metadata.xml`
            # and uncomment/update the line below in gatech_saml2_config.py.
            
            # Example (already in gatech_saml2_config.py, but shown here for context)
            # sp_config.metadata = {"local": [os.path.join(CERT_DIR, "gatech_idp_metadata.xml")]}
            
            saml_client = Saml2Client(config=sp_config)

        except Exception as e:
            raise RuntimeError(f"Failed to initialize SAML2 client: {e}")
    return saml_client

def get_saml_client() -> Saml2Client:
    """
    Returns the initialized SAML2 client. Raises an error if not initialized.
    """
    if saml_client is None:
        raise RuntimeError("SAML2 client has not been initialized. Call init_saml_client() on startup.")
    return saml_client

def prepare_saml_authn_request(relay_state: str = None):
    """
    Prepares a SAML authentication request to send to the IdP.
    """
    _saml_client = get_saml_client()
    try:
        reqid, binding, http_args = _saml_client.prepare_for_authenticate(relay_state=relay_state)
        redirect_url = dict(http_args["headers"])["Location"]
        # print(f"SAML2 Helper: Prepared AuthNRequest with redirect URL: {redirect_url}") # Optional: print debug
        return redirect_url, reqid
    except Exception as e:
        # print(f"SAML2 Helper: Error preparing SAML authentication request: {e}") # Optional: print error
        raise

def process_saml_response(saml_response_b64: str, binding: str = BINDING_HTTP_POST):
    """
    Processes the incoming SAML response from the IdP.
    Returns the parsed authentication response object.
    """
    _saml_client = get_saml_client()
    try:
        authn_response = _saml_client.parse_authn_request_response(
            saml_response_b64, binding
        )
        return authn_response
    except Exception as e:
        raise e

def generate_sp_metadata_xml() -> str:
    """
    Generates the SP metadata XML string using the initialized SAML client config.
    """
    _saml_client = get_saml_client()
    try:
        metadata_xml = create_metadata_string(
            None,
            config=_saml_client.config,
            sign=True,
            keyfile=_saml_client.config.key_file,
            cert=_saml_client.config.cert_file
        )
        # print("SAML2 Helper: Generated SP metadata XML.") # Optional: print debug
        return metadata_xml
    except Exception as e:
        # print(f"SAML2 Helper: Error generating SP metadata XML: {e}") # Optional: print error
        raise