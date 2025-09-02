"""
Georgia Tech SAML2 SSO Integration

This module handles SAML2 authentication with Georgia Tech's Identity Provider.
It processes SAML assertions and extracts user attributes for authentication.
"""

import os
from typing import Dict, Any
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from fastapi import Request, HTTPException
from dotenv import load_dotenv

load_dotenv()

# Georgia Tech IdP Metadata URL (redirects to sso.gatech.edu)
GT_IDP_METADATA_URL = "https://sso.gatech.edu/idp/profile/Metadata/SAML"

# SAML attribute mappings from Georgia Tech
GT_ATTRIBUTE_MAPPING = {
    "eduPersonPrincipalName": "urn:oid:1.3.6.1.4.1.5923.1.1.1.6",
    "uid": "urn:oid:0.9.2342.19200300.100.1.1", 
    "givenname": "urn:oid:2.5.4.42",
    "sn": "urn:oid:2.5.4.4"
}

def get_saml_settings() -> dict:
    base_url = os.getenv("BASE_URL")
    if not base_url or not base_url.startswith("https://"):
        raise RuntimeError("BASE_URL must be your public HTTPS backend URL")

    return {
        "strict": True,
        "debug": bool(int(os.getenv("SAML_DEBUG", "0"))),
        "sp": {
            "entityId": f"{base_url}/auth/gatech/saml2/metadata",
            "assertionConsumerService": {
                "url": f"{base_url}/auth/gatech/saml2/acs",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": f"{base_url}/auth/gatech/saml2/sls",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
            # Required because AuthnRequestsSigned=true on GT side:
            "x509cert": os.getenv("SP_PUBLIC_CERT", "").strip(),
            "privateKey": os.getenv("SP_PRIVATE_KEY", "").strip(),
        },
        "idp": {
            "entityId": "https://idp.gatech.edu/idp/shibboleth",
            "singleSignOnService": {
                "url": "https://sso.gatech.edu/idp/profile/SAML2/Redirect/SSO",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "singleLogoutService": {
                "url": "https://sso.gatech.edu/idp/profile/SAML2/Redirect/SLO",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": os.getenv("GT_IDP_CERT", "").strip(),
        },
        "security": {
            "authnRequestsSigned": True,     # GT requires this
            "wantAssertionsSigned": True,    # GT will sign assertions
            "wantMessagesSigned": False,     # keep False unless GT requires it
            "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
            "wantAttributeStatement": True,
        },
    }


def _prepare_request_data(request: Request, post_data: dict | None = None) -> dict:
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    https_on = "on" if scheme == "https" else "off"
    return {
        "https": https_on,
        "http_host": request.headers.get("x-forwarded-host", request.headers.get("host", "")),
        "server_port": request.url.port or (443 if scheme == "https" else 80),
        "script_name": request.url.path,
        "get_data": dict(request.query_params),
        "post_data": post_data or {},
    }

def init_saml_auth(request: Request, post_data: dict | None = None) -> OneLogin_Saml2_Auth:
    return OneLogin_Saml2_Auth(_prepare_request_data(request, post_data), get_saml_settings())


def extract_user_attributes(saml_auth: OneLogin_Saml2_Auth) -> Dict[str, Any]:
    """
    Extract user attributes from SAML assertion.
    
    Args:
        saml_auth: Authenticated SAML auth object
        
    Returns:
        Dict containing extracted user attributes
        
    Raises:
        HTTPException: If required attributes are missing
    """
    attributes = saml_auth.get_attributes()
    
    # Extract GT-specific attributes using their OID mappings
    user_data = {}
    
    # eduPersonPrincipalName (GT username)
    if GT_ATTRIBUTE_MAPPING["eduPersonPrincipalName"] in attributes:
        principal_name = attributes[GT_ATTRIBUTE_MAPPING["eduPersonPrincipalName"]][0]
        user_data["principal_name"] = principal_name
        # Convert to email format if not already
        if "@" not in principal_name:
            user_data["email"] = f"{principal_name}@gatech.edu"
        else:
            user_data["email"] = principal_name
    else:
        raise HTTPException(
            status_code=400,
            detail="Missing eduPersonPrincipalName attribute from Georgia Tech"
        )
    
    # UID (user identifier)
    if GT_ATTRIBUTE_MAPPING["uid"] in attributes:
        user_data["uid"] = attributes[GT_ATTRIBUTE_MAPPING["uid"]][0]
    
    # Given name (first name)
    if GT_ATTRIBUTE_MAPPING["givenname"] in attributes:
        user_data["first_name"] = attributes[GT_ATTRIBUTE_MAPPING["givenname"]][0]
    else:
        user_data["first_name"] = ""
    
    # Surname (last name)
    if GT_ATTRIBUTE_MAPPING["sn"] in attributes:
        user_data["last_name"] = attributes[GT_ATTRIBUTE_MAPPING["sn"]][0]
    else:
        user_data["last_name"] = ""
    
    # Set school email same as regular email for GT users
    user_data["school_email"] = user_data["email"]
    
    return user_data

def validate_saml_response(saml_auth: OneLogin_Saml2_Auth) -> None:
    """
    Validate SAML response and handle any errors.
    
    Args:
        saml_auth: SAML auth object to validate
        
    Raises:
        HTTPException: If SAML response is invalid
    """
    errors = saml_auth.get_errors()
    
    if errors:
        error_msg = f"SAML authentication failed: {', '.join(errors)}"
        last_error_reason = saml_auth.get_last_error_reason()
        if last_error_reason:
            error_msg += f" - {last_error_reason}"
        
        raise HTTPException(
            status_code=401,
            detail=error_msg
        )
    
    if not saml_auth.is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="SAML authentication failed: User not authenticated"
        )

def get_sso_url(request: Request) -> str:
    """
    Generate Georgia Tech SSO login URL.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: SSO login URL
    """
    auth = init_saml_auth(request)
    return auth.login()