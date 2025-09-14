import os
from urllib.parse import quote, urlencode
from fastapi import HTTPException, APIRouter, Request, Form, Response
from fastapi.responses import RedirectResponse
from application.features.auth.gatech_saml import (
    init_saml_auth,
    extract_user_attributes, 
    validate_saml_response,
)
from application.features.auth.crud import get_user_by_email
from application.features.auth.token_service import create_token_response_with_saml_data

router = APIRouter()


@router.get("/login/gatech")
async def gatech_sso_login(request: Request):
    auth = init_saml_auth(request)
    url = auth.login()  
    return RedirectResponse(url, status_code=302)


@router.post("/gatech/saml2/acs")
async def gatech_saml_callback(
    request: Request,
    SAMLResponse: str = Form(...)
):
    try:
        auth = init_saml_auth(request, post_data={"SAMLResponse": SAMLResponse})
        auth.process_response()

        validate_saml_response(auth)
        user_attributes = extract_user_attributes(auth)

        email = user_attributes["email"]
        user = get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=403, detail="User does not exist in system. Please contact administrator.")

        user_id = user["id"]
        token_response = create_token_response_with_saml_data(user_id, user_attributes)

        frontend = os.getenv("FRONTEND_BASE_URL")
        if not frontend:
            raise RuntimeError("FRONTEND_BASE_URL not configured")

        params = {"sso": "gatech", "access_token": token_response.access_token}
        redirect_url = f"{frontend}/auth/callback?{urlencode(params)}"


        return RedirectResponse(redirect_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        try:
            print("SAML last_error_reason:", auth.get_last_error_reason())
        except Exception:
            pass
        print(f"Georgia Tech SAML callback failed: {e!r}")
        raise HTTPException(status_code=500, detail="Georgia Tech SSO authentication failed.")



@router.get("/gatech/saml2/metadata")
async def metadata_xtml():
    """
    Returns SSO metadata file
    """
    with open("saml_metadata.xml", "r", encoding="utf-8") as f:
        metadata = f.read()

    return Response(content=metadata, media_type="application/xml")